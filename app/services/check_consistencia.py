"""
Servicio de diagnóstico de consistencia de datos
Detecta inconsistencias entre tablas requisiciones y compras
KS Seguridad Industrial - Sistema de Requisiciones
"""

import pandas as pd
from datetime import datetime
from typing import Dict, Tuple

from app.database import get_db_connection


# Días sin OC para considerar una REQ como "sin gestión esperada"
DIAS_UMBRAL_SIN_OC = 14


def _tablas_disponibles(cursor) -> Tuple[bool, bool]:
    """Retorna (tiene_requisiciones, tiene_compras)."""
    cursor.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='table' AND name IN ('requisiciones','compras')"
    )
    tablas = {row[0] for row in cursor.fetchall()}
    return "requisiciones" in tablas, "compras" in tablas


def _check_oc_sin_req(conn) -> pd.DataFrame:
    """
    OC en compras cuyo num_oc no aparece en ninguna requisicion.oc.
    Indica compras generadas sin requisición documentada.
    """
    query = """
        SELECT
            c.num_oc                        AS "N° OC",
            c.proveedor                     AS "Proveedor",
            COUNT(*)                        AS "Líneas",
            ROUND(SUM(c.total_linea), 0)    AS "Monto Total ($)",
            MIN(c.fecha_oc)                 AS "Fecha OC"
        FROM compras c
        WHERE c.num_oc NOT IN (
            SELECT DISTINCT r.oc
            FROM requisiciones r
            WHERE r.oc IS NOT NULL AND r.oc != ''
        )
        GROUP BY c.num_oc, c.proveedor
        ORDER BY c.fecha_oc DESC
    """
    try:
        return pd.read_sql_query(query, conn)
    except Exception:
        return pd.DataFrame()


def _check_req_sin_oc(conn) -> pd.DataFrame:
    """
    REQ sin OC, sin guía y sin observación con más de DIAS_UMBRAL_SIN_OC días.
    Indica requisiciones posiblemente olvidadas o sin gestión.
    """
    query = f"""
        SELECT
            r.numreq            AS "N° REQ",
            r.codprod           AS "Código",
            r.desprod           AS "Descripción",
            r.cantidad          AS "Cantidad",
            r.fecha_requisicion AS "Fecha REQ",
            CAST(julianday('now') - julianday(r.fecha_requisicion) AS INTEGER)
                                AS "Días Pendiente"
        FROM requisiciones r
        WHERE (r.oc IS NULL OR r.oc = '')
          AND (r.n_guia IS NULL OR r.n_guia = '')
          AND (r.observacion IS NULL OR r.observacion = '')
          AND r.fecha_requisicion IS NOT NULL
          AND r.fecha_requisicion != ''
          AND julianday('now') - julianday(r.fecha_requisicion) > {DIAS_UMBRAL_SIN_OC}
        ORDER BY "Días Pendiente" DESC
    """
    try:
        return pd.read_sql_query(query, conn)
    except Exception:
        return pd.DataFrame()


def _check_montos_descuadrados(conn) -> pd.DataFrame:
    """
    Líneas donde total_linea != precio_compra * cantidad_solicitada (tolerancia $1).
    Indica posibles errores de importación o digitación.
    """
    query = """
        SELECT
            c.num_oc                                        AS "N° OC",
            c.codprod                                       AS "Código",
            c.desprod                                       AS "Descripción",
            c.proveedor                                     AS "Proveedor",
            c.cantidad_solicitada                           AS "Cantidad",
            c.precio_compra                                 AS "Precio Unit.",
            c.total_linea                                   AS "Total Línea (BD)",
            ROUND(c.precio_compra * c.cantidad_solicitada, 2)
                                                            AS "Total Calculado",
            ROUND(ABS(c.total_linea - c.precio_compra * c.cantidad_solicitada), 2)
                                                            AS "Diferencia $"
        FROM compras c
        WHERE c.precio_compra > 0
          AND c.cantidad_solicitada > 0
          AND ABS(c.total_linea - c.precio_compra * c.cantidad_solicitada) > 1
        ORDER BY ABS(c.total_linea - c.precio_compra * c.cantidad_solicitada) DESC
        LIMIT 200
    """
    try:
        return pd.read_sql_query(query, conn)
    except Exception:
        return pd.DataFrame()


def _check_recepciones_excedidas(conn) -> pd.DataFrame:
    """
    Líneas donde cantidad recibida + manual > cantidad solicitada.
    Indica posibles errores de recepción o datos inconsistentes.
    """
    query = """
        SELECT
            c.num_oc            AS "N° OC",
            c.codprod           AS "Código",
            c.desprod           AS "Descripción",
            c.proveedor         AS "Proveedor",
            c.cantidad_solicitada                               AS "Solicitada",
            c.cantidad_recibida                                 AS "Recibida",
            c.cantidad_manual                                   AS "Manual",
            ROUND(c.cantidad_recibida + c.cantidad_manual - c.cantidad_solicitada, 2)
                                AS "Exceso"
        FROM compras c
        WHERE c.cantidad_recibida + c.cantidad_manual > c.cantidad_solicitada + 0.01
        ORDER BY (c.cantidad_recibida + c.cantidad_manual - c.cantidad_solicitada) DESC
        LIMIT 100
    """
    try:
        return pd.read_sql_query(query, conn)
    except Exception:
        return pd.DataFrame()


def ejecutar_diagnostico() -> Dict:
    """
    Ejecuta los 4 checks de consistencia y retorna un dict con:
      - DataFrames de cada check
      - Resumen con conteos
      - Timestamp de ejecución
      - Banderas de disponibilidad de tablas

    Returns:
        dict con claves:
            timestamp, tiene_req, tiene_compras,
            oc_sin_req, req_sin_oc, montos_descuadrados, recepciones_excedidas,
            resumen, error (solo si falla)
    """
    resultado: Dict = {
        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "tiene_req": False,
        "tiene_compras": False,
        "oc_sin_req": pd.DataFrame(),
        "req_sin_oc": pd.DataFrame(),
        "montos_descuadrados": pd.DataFrame(),
        "recepciones_excedidas": pd.DataFrame(),
        "resumen": {
            "oc_sin_req": 0,
            "req_sin_oc": 0,
            "montos_descuadrados": 0,
            "recepciones_excedidas": 0,
            "total_alertas": 0,
        },
    }

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            tiene_req, tiene_compras = _tablas_disponibles(cursor)
            resultado["tiene_req"] = tiene_req
            resultado["tiene_compras"] = tiene_compras

            if tiene_req:
                resultado["req_sin_oc"] = _check_req_sin_oc(conn)

            if tiene_req and tiene_compras:
                resultado["oc_sin_req"] = _check_oc_sin_req(conn)
                resultado["montos_descuadrados"] = _check_montos_descuadrados(conn)
                resultado["recepciones_excedidas"] = _check_recepciones_excedidas(conn)

    except Exception as e:
        resultado["error"] = str(e)
        return resultado

    r = resultado["resumen"]
    r["oc_sin_req"] = len(resultado["oc_sin_req"])
    r["req_sin_oc"] = len(resultado["req_sin_oc"])
    r["montos_descuadrados"] = len(resultado["montos_descuadrados"])
    r["recepciones_excedidas"] = len(resultado["recepciones_excedidas"])
    r["total_alertas"] = (
        r["oc_sin_req"]
        + r["req_sin_oc"]
        + r["montos_descuadrados"]
        + r["recepciones_excedidas"]
    )

    return resultado
