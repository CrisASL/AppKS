"""
Servicio de persistencia para cubos de Ventas e Inventario.

Implementa control de versiones mediante hash MD5 para evitar
reprocesar archivos Excel que no han cambiado, siguiendo la
misma arquitectura que compras_service.py.

KS Seguridad Industrial - Sistema de Gestión Operativa
"""

import hashlib
import sqlite3
import pandas as pd
from datetime import datetime
from typing import Optional
from contextlib import contextmanager

from app import config
from app.cache import get_table, invalidar_cache


# ============================================================================
# GESTIÓN DE CONEXIONES
# ============================================================================

@contextmanager
def get_db_connection():
    """Context manager para manejar conexiones a la base de datos."""
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


# ============================================================================
# INICIALIZACIÓN DE TABLAS
# ============================================================================

def crear_tablas():
    """
    Crea las tablas de control necesarias si no existen.
    Idempotente: puede ejecutarse múltiples veces sin efectos secundarios.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS archivos_cargados (
                nombre_cubo TEXT PRIMARY KEY,
                hash_archivo TEXT NOT NULL,
                fecha_carga  DATETIME NOT NULL
            )
        """)

        conn.commit()


# ============================================================================
# CONTROL DE HASH
# ============================================================================

def calcular_hash_archivo(archivo) -> str:
    """
    Calcula el hash MD5 del contenido de un archivo subido (UploadedFile).

    Args:
        archivo: Objeto retornado por st.file_uploader

    Returns:
        str: Hash MD5 hexadecimal del contenido
    """
    contenido = archivo.getvalue()
    return hashlib.md5(contenido).hexdigest()


def obtener_hash_guardado(nombre_cubo: str) -> Optional[str]:
    """
    Obtiene el hash almacenado para un cubo.

    Args:
        nombre_cubo: 'ventas' o 'inventario'

    Returns:
        str con el hash, o None si no existe registro previo
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT hash_archivo FROM archivos_cargados WHERE nombre_cubo = ?",
                (nombre_cubo,)
            )
            row = cursor.fetchone()
            return row["hash_archivo"] if row else None
    except Exception:
        return None


def actualizar_hash(nombre_cubo: str, hash_archivo: str) -> None:
    """
    Inserta o actualiza el hash de un cubo en la tabla de control.

    Args:
        nombre_cubo:  'ventas' o 'inventario'
        hash_archivo: Hash MD5 del archivo procesado
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO archivos_cargados (nombre_cubo, hash_archivo, fecha_carga)
            VALUES (?, ?, ?)
            ON CONFLICT(nombre_cubo) DO UPDATE SET
                hash_archivo = excluded.hash_archivo,
                fecha_carga  = excluded.fecha_carga
        """, (nombre_cubo, hash_archivo, datetime.now().isoformat()))


# ============================================================================
# PERSISTENCIA DE DATOS
# ============================================================================

def guardar_ventas(df: pd.DataFrame) -> None:
    """
    Guarda el DataFrame de ventas en SQLite, reemplazando datos previos.

    Args:
        df: DataFrame procesado del cubo de ventas
    """
    with get_db_connection() as conn:
        df.to_sql("ventas", conn, if_exists="replace", index=False)
    invalidar_cache()


def guardar_inventario(df: pd.DataFrame) -> None:
    """
    Guarda el DataFrame de inventario en SQLite, reemplazando datos previos.

    Args:
        df: DataFrame procesado del cubo de inventario
    """
    with get_db_connection() as conn:
        df.to_sql("inventario", conn, if_exists="replace", index=False)
    invalidar_cache()


# ============================================================================
# LECTURA DESDE SQLITE
# ============================================================================

def cargar_ventas_desde_sqlite() -> Optional[pd.DataFrame]:
    """
    Carga el cubo de ventas desde SQLite usando el DataFrame cacheado.

    Returns:
        DataFrame con los datos, o None si la tabla no existe o está vacía
    """
    df = get_table("ventas")
    return df if not df.empty else None


def cargar_inventario_desde_sqlite() -> Optional[pd.DataFrame]:
    """
    Carga el cubo de inventario desde SQLite usando el DataFrame cacheado.

    Returns:
        DataFrame con los datos, o None si la tabla no existe o está vacía
    """
    df = get_table("inventario")
    return df if not df.empty else None


def guardar_compras_raw(df: pd.DataFrame) -> None:
    """
    Guarda el DataFrame crudo de compras en SQLite (tabla compras_raw).

    Args:
        df: DataFrame procesado del cubo de compras (Excel sin normalizar)
    """
    with get_db_connection() as conn:
        df.to_sql("compras_raw", conn, if_exists="replace", index=False)


def cargar_compras_raw_desde_sqlite() -> Optional[pd.DataFrame]:
    """
    Carga el cubo crudo de compras desde SQLite.

    Returns:
        DataFrame con los datos, o None si la tabla no existe o está vacía
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='compras_raw'"
            )
            if not cursor.fetchone():
                return None
            df = pd.read_sql("SELECT * FROM compras_raw", conn)
            return df if not df.empty else None
    except Exception:
        return None


def guardar_requisiciones_raw(df: pd.DataFrame) -> None:
    """
    Guarda el DataFrame crudo de requisiciones en SQLite (tabla requisiciones_raw).

    Args:
        df: DataFrame procesado del cubo de requisiciones (Excel sin normalizar)
    """
    with get_db_connection() as conn:
        df.to_sql("requisiciones_raw", conn, if_exists="replace", index=False)


def cargar_requisiciones_raw_desde_sqlite() -> Optional[pd.DataFrame]:
    """
    Carga el cubo crudo de requisiciones desde SQLite.

    Returns:
        DataFrame con los datos, o None si la tabla no existe o está vacía
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='requisiciones_raw'"
            )
            if not cursor.fetchone():
                return None
            df = pd.read_sql("SELECT * FROM requisiciones_raw", conn)
            return df if not df.empty else None
    except Exception:
        return None
