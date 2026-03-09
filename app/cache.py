"""
Sistema de caching para AppKS.
Centraliza el acceso a datos con st.cache_resource (conexión) y
st.cache_data (DataFrames y archivos Excel), reduciendo consultas
repetidas a SQLite durante re-renders de Streamlit.

KS Seguridad Industrial - Sistema de Gestión Operativa
"""

import sqlite3
import pandas as pd
import streamlit as st

from app import config


# ============================================================================
# CONEXIÓN PERSISTENTE
# ============================================================================

@st.cache_resource
def get_connection() -> sqlite3.Connection:
    """
    Retorna una conexión SQLite persistente y reutilizable (cache_resource).
    Se crea una sola vez por sesión de Streamlit y se comparte en todos los
    re-renders. Activa WAL para permitir lecturas concurrentes con escrituras.
    Usar exclusivamente en operaciones de LECTURA.
    """
    conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


# ============================================================================
# LECTURA DE TABLAS
# ============================================================================

@st.cache_data
def get_table(table_name: str) -> pd.DataFrame:
    """
    Consulta una tabla completa de SQLite y retorna un DataFrame cacheado
    (cache_data). El caché se invalida explícitamente llamando a
    invalidar_cache() tras cualquier operación de escritura.

    Args:
        table_name: Nombre de la tabla SQLite a leer.

    Returns:
        DataFrame con todos los registros, o DataFrame vacío si hay error.
    """
    conn = get_connection()
    try:
        return pd.read_sql(f"SELECT * FROM {table_name}", conn)
    except Exception:
        return pd.DataFrame()


def invalidar_cache() -> None:
    """
    Limpia el caché de get_table. Debe llamarse tras toda operación de
    escritura (INSERT, UPDATE, DELETE) para que la siguiente lectura
    obtenga datos frescos desde SQLite.
    """
    get_table.clear()


# ============================================================================
# LECTURA DE EXCEL
# ============================================================================

@st.cache_data
def cargar_excel(_archivo, file_hash: str, tipo_cubo: str, hoja: str) -> pd.DataFrame:
    """
    Lee una hoja de Excel y cachea el resultado por file_hash (cache_data).

    El parámetro _archivo usa prefijo _ para que Streamlit no lo incluya en
    la clave de caché; file_hash es el identificador único que determina
    cuándo se invalida el resultado (al cambiar el archivo).

    Maneja automáticamente las pivot tables de Softland (cubos de ventas e
    inventario) cuyo encabezado real no está en la primera fila.

    Args:
        _archivo:  Archivo Excel (UploadedFile de Streamlit). No se hashea.
        file_hash: Hash MD5 del contenido. Determina invalidación del caché.
        tipo_cubo: 'requisiciones', 'compras', 'ventas' o 'inventario'.
        hoja:      Nombre exacto de la hoja a leer.

    Returns:
        DataFrame con los datos de la hoja, limpio y listo para validación.
    """
    CUBOS_PIVOT = {'ventas', 'inventario'}

    if tipo_cubo not in CUBOS_PIVOT:
        return pd.read_excel(_archivo, sheet_name=hoja)

    # ── Detección automática del encabezado en pivot tables ──────────────────
    df_raw = pd.read_excel(_archivo, sheet_name=hoja, header=None)

    header_row = None
    for i, row in df_raw.iterrows():
        if 'CodProd' in row.astype(str).values:
            header_row = i
            break

    if header_row is None:
        df = pd.read_excel(_archivo, sheet_name=hoja)
    else:
        df = pd.read_excel(_archivo, sheet_name=hoja, header=header_row)

    # ── Limpieza de artefactos de tablas dinámicas ────────────────────────────
    df = df.replace("(en blanco)", None)

    if 'CodProd' in df.columns:
        df = df.dropna(subset=['CodProd'])
        df = df[~df['CodProd'].astype(str).str.contains('Total', na=False)]

    return df.reset_index(drop=True)
