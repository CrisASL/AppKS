"""
Servicio de Análisis de Stock — KS Talca
Cruza datos de inventario y ventas para calcular cobertura y rotación de stock.

Modelo de negocio:
- Estado de stock: comparación stock actual vs stock objetivo (2 meses de ventas
  del mismo mes del año anterior).
- Rotación: clasificación por cantidad de meses con ventas > 0 en el año.
"""

import numpy as np
import pandas as pd
from datetime import datetime

# ── Constantes ────────────────────────────────────────────────────────────────

BODEGA_ANALISIS = 'KS TALCA'

MESES_VENTAS = [
    'ene', 'feb', 'mar', 'abr', 'may', 'jun',
    'jul', 'ago', 'sept', 'oct', 'nov', 'dic'
]

# Mapeo número de mes → nombre de columna en el cubo de ventas
_MES_NUM_A_COL = {
    1: 'ene',  2: 'feb',  3: 'mar',  4: 'abr',
    5: 'may',  6: 'jun',  7: 'jul',  8: 'ago',
    9: 'sept', 10: 'oct', 11: 'nov', 12: 'dic',
}


# ── Lógica de negocio ────────────────────────────────────────────────────────

def _mes_actual_col() -> str:
    """Devuelve el nombre de columna del mes actual (ej. 'mar')."""
    return _MES_NUM_A_COL[datetime.now().month]


def _mes_siguiente_col() -> str:
    """Devuelve el nombre de columna del mes siguiente al actual (ej. 'abr')."""
    mes_siguiente = (datetime.now().month % 12) + 1
    return _MES_NUM_A_COL[mes_siguiente]


def _calcular_estado_stock(stock_actual: float, stock_objetivo: float) -> str:
    """Clasifica el estado del stock respecto al objetivo de cobertura."""
    if stock_actual < stock_objetivo:
        return 'Falta de stock'
    if stock_actual == stock_objetivo:
        return 'Stock óptimo'
    return 'Sobrestock'


# ── Transformaciones de cubos ────────────────────────────────────────────────

def _preparar_inventario(df_inventario: pd.DataFrame) -> pd.DataFrame:
    """
    Extrae el stock de KS TALCA del cubo de inventario.
    Retorna columnas: codprod, desprod, stock_actual.
    """
    if 'CodProd' not in df_inventario.columns:
        raise ValueError("La columna 'CodProd' no existe en el cubo de inventario.")
    if BODEGA_ANALISIS not in df_inventario.columns:
        raise ValueError(
            f"La columna '{BODEGA_ANALISIS}' no existe en el cubo de inventario. "
            "Verifica que sea el cubo correcto."
        )

    cols = ['CodProd', BODEGA_ANALISIS]
    if 'DesProd' in df_inventario.columns:
        cols.insert(1, 'DesProd')

    df = df_inventario[cols].copy()
    rename_map = {'CodProd': 'codprod', BODEGA_ANALISIS: 'stock_actual'}
    if 'DesProd' in cols:
        rename_map['DesProd'] = 'desprod'

    df = df.rename(columns=rename_map)
    df['stock_actual'] = pd.to_numeric(df['stock_actual'], errors='coerce').fillna(0)

    if 'desprod' not in df.columns:
        df['desprod'] = None

    return df[['codprod', 'desprod', 'stock_actual']].copy()


def _preparar_ventas(df_ventas: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza el cubo de ventas manteniendo los meses como columnas.
    Convierte todos los valores de mes a numérico y rellena nulos con 0.
    Retorna columnas: codprod, desprod (si existe), ene, feb, …, dic.
    """
    if 'CodProd' not in df_ventas.columns:
        raise ValueError("La columna 'CodProd' no existe en el cubo de ventas.")

    meses_presentes = [m for m in MESES_VENTAS if m in df_ventas.columns]

    base_cols = ['CodProd']
    if 'DesProd' in df_ventas.columns:
        base_cols.append('DesProd')

    df = df_ventas[base_cols + meses_presentes].copy()
    df = df.rename(columns={'CodProd': 'codprod', 'DesProd': 'desprod'})

    for mes in meses_presentes:
        df[mes] = pd.to_numeric(df[mes], errors='coerce').fillna(0)

    return df


# ── Función principal ────────────────────────────────────────────────────────

def calcular_analisis_stock(
    df_inventario: pd.DataFrame,
    df_ventas: pd.DataFrame
) -> pd.DataFrame:
    """
    Combina inventario (bodega KS TALCA) con ventas para calcular cobertura
    y rotación de stock.

    Lógica:
    - ventas_mes_actual_anio_anterior   : ventas del mismo mes del año anterior.
    - ventas_mes_siguiente_anio_anterior: ventas del mes siguiente del año anterior.
    - stock_objetivo : suma de ambos (cobertura de 2 meses consecutivos).
    - estado_stock   : Falta de stock / Stock óptimo / Sobrestock.
    - meses_con_venta: cantidad de meses con ventas > 0.
    - rotacion       : Alta (≥10 meses) / Rotación media (7-9) / Baja rotación (≤6).

    Args:
        df_inventario: DataFrame del cubo de inventario (bodegas como columnas).
        df_ventas:     DataFrame del cubo de ventas (meses como columnas).

    Returns:
        DataFrame con columnas:
            codprod, desprod, ventas_mes_actual_anio_anterior,
            ventas_mes_siguiente_anio_anterior, stock_actual,
            stock_objetivo, estado_stock, meses_con_venta, rotacion
    """
    inv = _preparar_inventario(df_inventario)
    ven = _preparar_ventas(df_ventas)

    mes_actual_col   = _mes_actual_col()    # ej. 'mar'
    mes_sig_col      = _mes_siguiente_col() # ej. 'abr'
    meses_presentes  = [m for m in MESES_VENTAS if m in ven.columns]

    # ── Ventas mes actual del año anterior ───────────────────────────────────
    if mes_actual_col in ven.columns:
        v_actual = ven[['codprod', mes_actual_col]].rename(
            columns={mes_actual_col: 'ventas_mes_actual_anio_anterior'}
        )
    else:
        v_actual = ven[['codprod']].copy()
        v_actual['ventas_mes_actual_anio_anterior'] = 0.0
    v_actual = v_actual.groupby('codprod', as_index=False)['ventas_mes_actual_anio_anterior'].sum()

    # ── Ventas mes siguiente del año anterior ────────────────────────────────
    if mes_sig_col in ven.columns:
        v_sig = ven[['codprod', mes_sig_col]].rename(
            columns={mes_sig_col: 'ventas_mes_siguiente_anio_anterior'}
        )
    else:
        v_sig = ven[['codprod']].copy()
        v_sig['ventas_mes_siguiente_anio_anterior'] = 0.0
    v_sig = v_sig.groupby('codprod', as_index=False)['ventas_mes_siguiente_anio_anterior'].sum()

    # ── Meses con venta (sobre todos los meses disponibles) ──────────────────
    if meses_presentes:
        ven['meses_con_venta'] = (ven[meses_presentes] > 0).sum(axis=1)
    else:
        ven['meses_con_venta'] = 0

    meses_venta_ref = ven[['codprod', 'meses_con_venta']].copy()

    # ── Merge inventario + ventas + meses con venta ──────────────────────────
    df = inv.merge(v_actual, on='codprod', how='left')
    df = df.merge(v_sig,    on='codprod', how='left')
    df = df.merge(meses_venta_ref, on='codprod', how='left')

    df['ventas_mes_actual_anio_anterior'] = pd.to_numeric(
        df['ventas_mes_actual_anio_anterior'], errors='coerce'
    ).fillna(0)
    df['ventas_mes_siguiente_anio_anterior'] = pd.to_numeric(
        df['ventas_mes_siguiente_anio_anterior'], errors='coerce'
    ).fillna(0)
    df['meses_con_venta'] = pd.to_numeric(
        df['meses_con_venta'], errors='coerce'
    ).fillna(0).astype(int)

    # ── Stock objetivo (mes actual + mes siguiente del año anterior) ──────────
    df['stock_objetivo'] = (
        df['ventas_mes_actual_anio_anterior'] + df['ventas_mes_siguiente_anio_anterior']
    )

    # ── Estado de stock ───────────────────────────────────────────────────────
    df['estado_stock'] = df.apply(
        lambda row: _calcular_estado_stock(row['stock_actual'], row['stock_objetivo']),
        axis=1
    )

    # ── Rotación por meses con ventas ─────────────────────────────────────────
    df['rotacion'] = np.select(
        [
            df['meses_con_venta'] >= 10,
            df['meses_con_venta'].between(7, 9),
        ],
        [
            'Alta rotación',
            'Rotación media',
        ],
        default='Baja rotación'
    )

    # ── Completar desprod vacías usando el cubo de ventas ────────────────────
    if df['desprod'].isnull().any() and 'desprod' in ven.columns:
        mapa_desc = (
            ven[['codprod', 'desprod']]
            .drop_duplicates(subset='codprod')
            .rename(columns={'desprod': '_desprod_fill'})
        )
        df = df.merge(mapa_desc, on='codprod', how='left')
        df['desprod'] = df['desprod'].fillna(df['_desprod_fill'])
        df.drop(columns=['_desprod_fill'], inplace=True)

    return df[
        ['codprod', 'desprod',
         'ventas_mes_actual_anio_anterior', 'ventas_mes_siguiente_anio_anterior',
         'stock_actual', 'stock_objetivo', 'estado_stock',
         'meses_con_venta', 'rotacion']
    ].copy()
