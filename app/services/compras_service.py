"""
Módulo de gestión de compras y cruce con gestión
Implementación idempotente y eficiente para sistema productivo
KS Seguridad Industrial - Sistema de Requisiciones
"""

import sqlite3
import pandas as pd
from datetime import datetime
from typing import Tuple, List, Dict, Optional
from contextlib import contextmanager
from app import config
from app.cache import invalidar_cache


# ============================================================================
# GESTIÓN DE CONEXIONES
# ============================================================================

@contextmanager
def get_db_connection():
    """
    Context manager para manejar conexiones a la base de datos.
    Asegura que las conexiones se cierren correctamente.
    """
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

def migrar_tabla_compras_agregar_desprod():
    """
    Migración: Agrega la columna desprod a tabla compras existente.
    Esta función es segura de ejecutar múltiples veces (idempotente).
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar si la tabla existe
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='compras'")
            if not cursor.fetchone():
                print("   ⚠️ Tabla 'compras' no existe, no se requiere migración")
                return False, "Tabla no existe"
            
            # Verificar si la columna ya existe
            cursor.execute("PRAGMA table_info(compras)")
            columnas_existentes = [col[1] for col in cursor.fetchall()]
            
            if 'desprod' in columnas_existentes:
                print("   ✓ Columna 'desprod' ya existe")
                return True, "Columna ya existe"
            
            # Agregar columna
            cursor.execute("ALTER TABLE compras ADD COLUMN desprod TEXT")
            conn.commit()
            print("   ✅ Columna 'desprod' agregada exitosamente")
            return True, "Migración exitosa"
            
    except Exception as e:
        print(f"   ❌ Error en migración: {str(e)}")
        return False, str(e)


def crear_tabla_compras():
    """
    Crea la tabla de compras si no existe.
    Diseño idempotente: puede ejecutarse múltiples veces sin efectos secundarios.
    
    Características:
    - Clave única compuesta (num_oc, codprod) para evitar duplicados
    - Índices optimizados para cruces frecuentes
    - Validaciones a nivel de base de datos (CHECK constraints)
    - Campos calculados automáticos (total_linea via trigger)
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Crear tabla principal
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS compras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                num_oc TEXT NOT NULL,
                codprod TEXT NOT NULL,
                desprod TEXT,
                proveedor TEXT,
                cantidad_solicitada REAL DEFAULT 0,
                cantidad_recibida REAL DEFAULT 0,
                cantidad_manual REAL DEFAULT 0,
                precio_compra REAL DEFAULT 0,
                total_linea REAL DEFAULT 0,
                fecha_oc TEXT,
                fecha_recepcion TEXT,
                estado_linea TEXT DEFAULT 'Pendiente',
                bodega_codigo TEXT,
                bodega_nombre TEXT,
                observacion TEXT,
                fecha_carga TEXT NOT NULL,
                
                -- Constraints de validación
                CHECK(cantidad_solicitada >= 0),
                CHECK(cantidad_recibida >= 0),
                CHECK(cantidad_manual >= 0),
                CHECK(precio_compra >= 0),
                
                -- Clave única de negocio: OC + Producto
                UNIQUE(num_oc, codprod)
            )
        """)
        
        # Ejecutar migración para agregar desprod si no existe
        migrar_tabla_compras_agregar_desprod()
        
        # Índices para optimizar consultas y cruces
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_compras_num_oc 
            ON compras(num_oc)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_compras_codprod 
            ON compras(codprod)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_compras_oc_codprod 
            ON compras(num_oc, codprod)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_compras_fecha_oc 
            ON compras(fecha_oc)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_compras_estado 
            ON compras(estado_linea)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_compras_proveedor 
            ON compras(proveedor)
        """)
        
        # Trigger para calcular total_linea automáticamente al insertar
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS calcular_total_linea_insert
            AFTER INSERT ON compras
            FOR EACH ROW
            BEGIN
                UPDATE compras 
                SET total_linea = (NEW.cantidad_recibida + NEW.cantidad_manual) * NEW.precio_compra
                WHERE id = NEW.id;
            END
        """)
        
        # Trigger para calcular total_linea automáticamente al actualizar
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS calcular_total_linea_update
            AFTER UPDATE ON compras
            FOR EACH ROW
            WHEN OLD.cantidad_recibida != NEW.cantidad_recibida 
                OR OLD.cantidad_manual != NEW.cantidad_manual
                OR OLD.precio_compra != NEW.precio_compra
            BEGIN
                UPDATE compras 
                SET total_linea = (NEW.cantidad_recibida + NEW.cantidad_manual) * NEW.precio_compra
                WHERE id = NEW.id;
            END
        """)
        
        conn.commit()


def crear_tabla_gestion():
    """
    Crea la tabla de gestión si no existe.
    Esta tabla es una extensión de requisiciones para gestión diaria.
    
    Características:
    - Hereda estructura de requisiciones
    - Agrega campos específicos de seguimiento de compras
    - Mantiene relación lógica con compras vía (oc, codprod)
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS gestion (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numreq TEXT NOT NULL,
                codprod TEXT NOT NULL,
                desprod TEXT,
                cantidad REAL NOT NULL,
                fecha_requisicion TEXT,
                sucursal_destino TEXT DEFAULT 'KS TALCA',
                
                -- Campos de gestión de compras
                proveedor TEXT,
                oc TEXT,
                estado_oc TEXT DEFAULT 'Pendiente',
                fecha_oc TEXT,
                cant_recibida REAL DEFAULT 0,
                saldo_pendiente REAL,
                
                -- Campos adicionales de cruce con compras
                bodega_ingreso TEXT,
                observacion_oc TEXT,
                
                -- Auditoría
                fecha_creacion TEXT DEFAULT (datetime('now', 'localtime')),
                fecha_modificacion TEXT DEFAULT (datetime('now', 'localtime')),
                
                -- Constraints
                CHECK(cantidad > 0),
                CHECK(cant_recibida >= 0),
                CHECK(saldo_pendiente >= 0),
                
                -- Clave única de negocio
                UNIQUE(numreq, codprod)
            )
        """)
        
        # Índices
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_gestion_numreq 
            ON gestion(numreq)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_gestion_codprod 
            ON gestion(codprod)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_gestion_oc 
            ON gestion(oc)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_gestion_oc_codprod 
            ON gestion(oc, codprod)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_gestion_estado 
            ON gestion(estado_oc)
        """)
        
        # Trigger para calcular saldo pendiente automáticamente
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS calcular_saldo_gestion_insert
            AFTER INSERT ON gestion
            FOR EACH ROW
            BEGIN
                UPDATE gestion 
                SET saldo_pendiente = cantidad - cant_recibida 
                WHERE id = NEW.id;
            END
        """)
        
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS calcular_saldo_gestion_update
            AFTER UPDATE ON gestion
            FOR EACH ROW
            WHEN OLD.cantidad != NEW.cantidad OR OLD.cant_recibida != NEW.cant_recibida
            BEGIN
                UPDATE gestion 
                SET saldo_pendiente = NEW.cantidad - NEW.cant_recibida 
                WHERE id = NEW.id;
            END
        """)
        
        # Trigger para actualizar fecha de modificación
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS actualizar_fecha_mod_gestion
            AFTER UPDATE ON gestion
            FOR EACH ROW
            BEGIN
                UPDATE gestion 
                SET fecha_modificacion = datetime('now', 'localtime')
                WHERE id = NEW.id;
            END
        """)
        
        conn.commit()


def inicializar_modulo_compras():
    """
    Inicializa todas las estructuras necesarias para el módulo de compras.
    Es seguro ejecutar múltiples veces (idempotente).
    """
    try:
        crear_tabla_compras()
        crear_tabla_gestion()
        print("✅ Módulo de compras inicializado correctamente")
    except Exception as e:
        print(f"❌ Error al inicializar módulo de compras: {str(e)}")
        raise


# ============================================================================
# VALIDACIONES
# ============================================================================

def validar_columnas_compras(df: pd.DataFrame) -> Tuple[bool, str, List[str]]:
    """
    Valida que el DataFrame de compras tenga las columnas necesarias.
    
    Args:
        df: DataFrame con datos de compras
        
    Returns:
        Tuple[bool, str, List[str]]: 
            - Es válido
            - Mensaje de error/éxito
            - Lista de columnas faltantes
    """
    columnas_requeridas = {
        'NumOC': 'num_oc',
        'CodProd': 'codprod',
        'DesProd': 'desprod',
        'Proveedor': 'proveedor',
        'CantidadSolicitada': 'cantidad_solicitada',
        'CantidadRecibida': 'cantidad_recibida',
        'PrecioCompra': 'precio_compra',
        'FechaOC': 'fecha_oc',
        'EstadoLinea': 'estado_linea'
    }
    
    columnas_opcionales = {
        'CantidadManual': 'cantidad_manual',
        'FechaRecepcion': 'fecha_recepcion',
        'BodegaCodigo': 'bodega_codigo',
        'BodegaNombre': 'bodega_nombre',
        'Observacion': 'observacion'
    }
    
    # Verificar columnas requeridas
    columnas_faltantes = []
    for col_excel in columnas_requeridas.keys():
        if col_excel not in df.columns:
            columnas_faltantes.append(col_excel)
    
    if columnas_faltantes:
        return False, f"Faltan columnas requeridas: {', '.join(columnas_faltantes)}", columnas_faltantes
    
    return True, "Columnas válidas", []


def normalizar_dataframe_compras(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza el DataFrame de compras al formato esperado por la base de datos.
    
    Args:
        df: DataFrame original del cubo de compras
        
    Returns:
        DataFrame normalizado con nombres de columnas de la BD
    """
    # Mapeo de columnas Excel -> BD
    mapeo_columnas = {
        'NumOC': 'num_oc',
        'CodProd': 'codprod',
        'DesProd': 'desprod',
        'Proveedor': 'proveedor',
        'CantidadSolicitada': 'cantidad_solicitada',
        'CantidadRecibida': 'cantidad_recibida',
        'CantidadManual': 'cantidad_manual',
        'PrecioCompra': 'precio_compra',
        'FechaOC': 'fecha_oc',
        'FechaRecepcion': 'fecha_recepcion',
        'EstadoLinea': 'estado_linea',
        'BodegaCodigo': 'bodega_codigo',
        'BodegaNombre': 'bodega_nombre',
        'Observacion': 'observacion'
    }
    
    # Crear copia del DataFrame
    df_norm = df.copy()
    
    # Renombrar columnas que existan
    columnas_existentes = {k: v for k, v in mapeo_columnas.items() if k in df_norm.columns}
    df_norm = df_norm.rename(columns=columnas_existentes)
    
    # Agregar columnas opcionales con valores por defecto si no existen
    if 'cantidad_manual' not in df_norm.columns:
        df_norm['cantidad_manual'] = 0
    
    # Normalizar tipos de datos
    df_norm['num_oc'] = df_norm['num_oc'].astype(str).str.strip()
    df_norm['codprod'] = df_norm['codprod'].astype(str).str.strip()
    
    # Asegurar campos numéricos
    campos_numericos = ['cantidad_solicitada', 'cantidad_recibida', 'cantidad_manual', 'precio_compra']
    for campo in campos_numericos:
        if campo in df_norm.columns:
            df_norm[campo] = pd.to_numeric(df_norm[campo], errors='coerce').fillna(0)
    
    # Normalizar fechas (manejar números seriales de Excel)
    for campo_fecha in ['fecha_oc', 'fecha_recepcion']:
        if campo_fecha in df_norm.columns:
            print(f"\n   🔍 DIAGNÓSTICO {campo_fecha.upper()}:")
            print(f"      Tipo de dato: {df_norm[campo_fecha].dtype}")
            print(f"      Primeros 5 valores: {df_norm[campo_fecha].head().tolist()}")
            print(f"      Valores únicos (muestra): {df_norm[campo_fecha].nunique()}")
            
            # Si el campo es numérico, intentar convertir desde serial de Excel
            if pd.api.types.is_numeric_dtype(df_norm[campo_fecha]):
                print(f"      ✓ Detectado como numérico (serial de Excel)")
                # Excel guarda fechas como días desde 1900-01-01
                # Pandas puede convertirlo usando origin='1899-12-30' (ajuste por bug de Excel)
                try:
                    # Filtrar valores que parecen fechas (típicamente entre 1 y 100000)
                    # Valores fuera de rango se consideran inválidos
                    mask_validos = (df_norm[campo_fecha] > 1) & (df_norm[campo_fecha] < 100000)
                    
                    # Convertir valores válidos
                    df_norm.loc[mask_validos, campo_fecha] = pd.to_datetime(
                        df_norm.loc[mask_validos, campo_fecha], 
                        unit='D', 
                        origin='1899-12-30',
                        errors='coerce'
                    )
                    
                    # Marcar inválidos como NaT
                    df_norm.loc[~mask_validos, campo_fecha] = pd.NaT
                    
                    print(f"      ✓ Conversión desde serial Excel completada")
                    
                except Exception as e:
                    print(f"      ⚠️ Error en conversión serial: {str(e)}")
                    # Si falla, intentar conversión normal
                    df_norm[campo_fecha] = pd.to_datetime(df_norm[campo_fecha], errors='coerce')
            else:
                print(f"      ℹ️ Detectado como texto, conversión normal")
                # Si no es numérico, intentar conversión normal
                df_norm[campo_fecha] = pd.to_datetime(df_norm[campo_fecha], errors='coerce')
            
            # Contar fechas válidas después de conversión
            fechas_validas = df_norm[campo_fecha].notna().sum()
            total_registros = len(df_norm)
            print(f"      📅 Resultado: {fechas_validas}/{total_registros} fechas válidas")
            
            if fechas_validas > 0:
                # Mostrar muestra de fechas convertidas
                muestra = df_norm[df_norm[campo_fecha].notna()][campo_fecha].head(3)
                print(f"      📋 Muestra de fechas convertidas:")
                for idx, fecha in enumerate(muestra, 1):
                    print(f"         {idx}. {fecha}")
            
            # Aplicar formato solo a valores válidos, dejar None en valores inválidos
            df_norm[campo_fecha] = df_norm[campo_fecha].apply(
                lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else None
            )
    
    # Limpiar valores nulos en campos de texto
    campos_texto = ['proveedor', 'estado_linea', 'bodega_codigo', 'bodega_nombre', 'observacion']
    for campo in campos_texto:
        if campo in df_norm.columns:
            df_norm[campo] = df_norm[campo].fillna('').astype(str).str.strip()
    
    return df_norm


# ============================================================================
# CARGA DE DATOS
# ============================================================================

def cargar_compras_desde_dataframe(df: pd.DataFrame, conn: sqlite3.Connection) -> Tuple[int, int, int, List[str]]:
    """
    Carga datos de compras desde un DataFrame usando UPSERT (INSERT + UPDATE).
    
    Características de producción:
    - NUNCA borra datos existentes
    - NUNCA duplica registros (clave única: num_oc + codprod)
    - INSERTA registros nuevos
    - ACTUALIZA registros existentes cuando detecta cambios
    - NO modifica registros si los datos son idénticos
    - Valida datos antes de insertar/actualizar
    - Preserva id y fecha_carga original en UPDATEs
    - Triggers recalculan total_linea automáticamente
    - Maneja errores sin detener el proceso completo
    - Retorna estadísticas detalladas
    
    Campos actualizables en registros existentes:
    - cantidad_recibida, cantidad_manual, precio_compra
    - estado_linea, fecha_recepcion
    - proveedor, bodega_codigo, bodega_nombre, observacion
    
    Args:
        df: DataFrame con datos de compras (formato Excel del cubo)
        conn: Conexión a la base de datos
        
    Returns:
        Tuple[int, int, int, List[str]]: 
            - Cantidad de registros insertados (nuevos)
            - Cantidad de registros actualizados (existentes con cambios)
            - Cantidad sin cambios (existentes idénticos)
            - Lista de mensajes de error
    """
    # Validar estructura del DataFrame
    es_valido, mensaje, _ = validar_columnas_compras(df)
    if not es_valido:
        raise ValueError(mensaje)
    
    # Normalizar DataFrame
    df_norm = normalizar_dataframe_compras(df)
    
    insertados = 0
    actualizados = 0
    sin_cambios = 0
    mensajes_error = []
    registros_totales = len(df_norm)
    
    fecha_carga = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor = conn.cursor()
    
    # Obtener claves existentes para clasificar INSERT vs UPDATE
    cursor.execute("SELECT num_oc, codprod FROM compras")
    claves_existentes = {(row[0], row[1]) for row in cursor.fetchall()}
    
    print(f"📦 Iniciando carga de {registros_totales} registros de compras (UPSERT)...")
    print(f"   Registros existentes en BD: {len(claves_existentes)}")
    
    # Procesar cada registro
    for index, row in df_norm.iterrows():
        try:
            num_oc = row['num_oc']
            codprod = row['codprod']
            
            # Validar campos obligatorios
            if not num_oc or num_oc == '' or num_oc == 'nan':
                sin_cambios += 1
                mensajes_error.append(f"Fila {index + 1}: Falta NumOC")
                continue
            
            if not codprod or codprod == '' or codprod == 'nan':
                sin_cambios += 1
                mensajes_error.append(f"Fila {index + 1}: Falta CodProd (OC: {num_oc})")
                continue
            
            # Verificar si existe (para clasificar resultado)
            existe_previamente = (num_oc, codprod) in claves_existentes
            
            # Preparar datos para UPSERT
            datos = {
                'num_oc': num_oc,
                'codprod': codprod,
                'desprod': row.get('desprod', ''),
                'proveedor': row.get('proveedor', ''),
                'cantidad_solicitada': row.get('cantidad_solicitada', 0),
                'cantidad_recibida': row.get('cantidad_recibida', 0),
                'cantidad_manual': row.get('cantidad_manual', 0),
                'precio_compra': row.get('precio_compra', 0),
                'fecha_oc': row.get('fecha_oc', None),
                'fecha_recepcion': row.get('fecha_recepcion', None),
                'estado_linea': row.get('estado_linea', 'Pendiente'),
                'bodega_codigo': row.get('bodega_codigo', ''),
                'bodega_nombre': row.get('bodega_nombre', ''),
                'observacion': row.get('observacion', ''),
                'fecha_carga': fecha_carga
            }
            
            # UPSERT: INSERT con ON CONFLICT DO UPDATE
            # Solo actualiza si detecta cambios en campos actualizables
            cursor.execute("""
                INSERT INTO compras (
                    num_oc, codprod, desprod, proveedor,
                    cantidad_solicitada, cantidad_recibida, cantidad_manual,
                    precio_compra, fecha_oc, fecha_recepcion,
                    estado_linea, bodega_codigo, bodega_nombre,
                    observacion, fecha_carga
                ) VALUES (
                    :num_oc, :codprod, :desprod, :proveedor,
                    :cantidad_solicitada, :cantidad_recibida, :cantidad_manual,
                    :precio_compra, :fecha_oc, :fecha_recepcion,
                    :estado_linea, :bodega_codigo, :bodega_nombre,
                    :observacion, :fecha_carga
                )
                ON CONFLICT(num_oc, codprod) DO UPDATE SET
                    desprod = excluded.desprod,
                    cantidad_recibida = excluded.cantidad_recibida,
                    cantidad_manual = excluded.cantidad_manual,
                    precio_compra = excluded.precio_compra,
                    estado_linea = excluded.estado_linea,
                    fecha_recepcion = excluded.fecha_recepcion,
                    proveedor = excluded.proveedor,
                    bodega_codigo = excluded.bodega_codigo,
                    bodega_nombre = excluded.bodega_nombre,
                    observacion = excluded.observacion
                WHERE
                    COALESCE(compras.desprod, '') != COALESCE(excluded.desprod, '') OR
                    compras.cantidad_recibida != excluded.cantidad_recibida OR
                    compras.cantidad_manual != excluded.cantidad_manual OR
                    compras.precio_compra != excluded.precio_compra OR
                    compras.estado_linea != excluded.estado_linea OR
                    COALESCE(compras.fecha_recepcion, '') != COALESCE(excluded.fecha_recepcion, '') OR
                    compras.proveedor != excluded.proveedor OR
                    compras.bodega_codigo != excluded.bodega_codigo OR
                    compras.bodega_nombre != excluded.bodega_nombre OR
                    compras.observacion != excluded.observacion
            """, datos)
            
            # Clasificar resultado: INSERT nuevo, UPDATE con cambios, o sin cambios
            if cursor.rowcount > 0:
                if existe_previamente:
                    actualizados += 1
                else:
                    insertados += 1
                    claves_existentes.add((num_oc, codprod))
            else:
                # No hubo cambios (registro ya existe con datos idénticos)
                sin_cambios += 1
                
        except Exception as e:
            sin_cambios += 1
            mensajes_error.append(f"Fila {index + 1}: {str(e)}")
    
    # Commit final
    conn.commit()
    
    invalidar_cache()
    print(f"✅ Carga completada: {insertados} insertados, {actualizados} actualizados, {sin_cambios} sin cambios")
    
    return insertados, actualizados, sin_cambios, mensajes_error


# ============================================================================
# CRUCE CON GESTIÓN
# ============================================================================

def actualizar_gestion_desde_compras(conn: sqlite3.Connection) -> Tuple[int, List[str]]:
    """
    Actualiza la tabla de gestión con datos de compras mediante cruce automático.
    
    Lógica de cruce:
    - Relaciona gestion.oc = compras.num_oc
    - Relaciona gestion.codprod = compras.codprod
    - Actualiza solo registros con OC asignada (no afecta pendientes)
    - Recalcula automáticamente saldo_pendiente
    - Es idempotente: puede ejecutarse múltiples veces
    
    Campos actualizados en gestión:
    - estado_oc: del campo estado_linea de compras
    - fecha_oc: fecha de la orden de compra
    - cant_recibida: suma de cantidad_recibida + cantidad_manual
    - bodega_ingreso: nombre de la bodega de recepción
    - observacion_oc: observaciones de la línea de compra
    - saldo_pendiente: recalculado automáticamente por trigger
    
    Args:
        conn: Conexión a la base de datos
        
    Returns:
        Tuple[int, List[str]]: 
            - Cantidad de registros actualizados
            - Lista de mensajes informativos
    """
    cursor = conn.cursor()
    mensajes = []
    
    print("🔄 Iniciando actualización de gestión desde compras...")
    
    # Verificar que existan ambas tablas
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name IN ('gestion', 'compras')
    """)
    tablas_existentes = {row[0] for row in cursor.fetchall()}
    
    if 'gestion' not in tablas_existentes:
        mensajes.append("⚠️ La tabla 'gestion' no existe. Créala primero con crear_tabla_gestion()")
        return 0, mensajes
    
    if 'compras' not in tablas_existentes:
        mensajes.append("⚠️ La tabla 'compras' no existe. Créala primero con crear_tabla_compras()")
        return 0, mensajes
    
    # Contar registros candidatos para el cruce
    cursor.execute("""
        SELECT COUNT(*) 
        FROM gestion g
        INNER JOIN compras c ON g.oc = c.num_oc AND g.codprod = c.codprod
        WHERE g.oc IS NOT NULL AND g.oc != ''
    """)
    registros_para_actualizar = cursor.fetchone()[0]
    
    if registros_para_actualizar == 0:
        mensajes.append("ℹ️ No hay registros para actualizar (sin coincidencias entre gestión y compras)")
        return 0, mensajes
    
    mensajes.append(f"📊 Se encontraron {registros_para_actualizar} registros para actualizar")
    
    # Actualización masiva optimizada con SQL
    # Usa INNER JOIN para cruzar y UPDATE para actualizar en una sola operación
    cursor.execute("""
        UPDATE gestion
        SET 
            estado_oc = (
                SELECT c.estado_linea 
                FROM compras c 
                WHERE c.num_oc = gestion.oc AND c.codprod = gestion.codprod
            ),
            fecha_oc = (
                SELECT c.fecha_oc 
                FROM compras c 
                WHERE c.num_oc = gestion.oc AND c.codprod = gestion.codprod
            ),
            cant_recibida = (
                SELECT (c.cantidad_recibida + c.cantidad_manual)
                FROM compras c 
                WHERE c.num_oc = gestion.oc AND c.codprod = gestion.codprod
            ),
            bodega_ingreso = (
                SELECT c.bodega_nombre
                FROM compras c 
                WHERE c.num_oc = gestion.oc AND c.codprod = gestion.codprod
            ),
            observacion_oc = (
                SELECT c.observacion
                FROM compras c 
                WHERE c.num_oc = gestion.oc AND c.codprod = gestion.codprod
            )
        WHERE 
            gestion.oc IS NOT NULL 
            AND gestion.oc != ''
            AND EXISTS (
                SELECT 1 FROM compras c 
                WHERE c.num_oc = gestion.oc AND c.codprod = gestion.codprod
            )
    """)
    
    registros_actualizados = cursor.rowcount
    
    # Commit de la transacción
    conn.commit()
    
    mensajes.append(f"✅ Actualización completada: {registros_actualizados} registros actualizados")
    mensajes.append("ℹ️ El saldo_pendiente se recalculó automáticamente mediante triggers")
    
    print(f"✅ Gestión actualizada: {registros_actualizados} registros procesados")
    
    return registros_actualizados, mensajes


# ============================================================================
# CONSULTAS Y REPORTES
# ============================================================================

def obtener_estadisticas_compras(conn: sqlite3.Connection) -> Dict:
    """
    Obtiene estadísticas generales de la tabla de compras.
    
    Returns:
        Diccionario con estadísticas clave
    """
    cursor = conn.cursor()
    
    # Total de registros
    cursor.execute("SELECT COUNT(*) FROM compras")
    total_registros = cursor.fetchone()[0]
    
    # Total de OCs únicas
    cursor.execute("SELECT COUNT(DISTINCT num_oc) FROM compras")
    total_ocs = cursor.fetchone()[0]
    
    # Total de productos únicos
    cursor.execute("SELECT COUNT(DISTINCT codprod) FROM compras")
    total_productos = cursor.fetchone()[0]
    
    # Estadísticas por estado
    cursor.execute("""
        SELECT estado_linea, COUNT(*) as cantidad
        FROM compras
        GROUP BY estado_linea
        ORDER BY cantidad DESC
    """)
    por_estado = {row[0]: row[1] for row in cursor.fetchall()}
    
    # Valor total de compras
    cursor.execute("""
        SELECT SUM((cantidad_recibida + cantidad_manual) * precio_compra) as total
        FROM compras
    """)
    valor_total = cursor.fetchone()[0] or 0
    
    # Fecha de última carga
    cursor.execute("SELECT MAX(fecha_carga) FROM compras")
    ultima_carga = cursor.fetchone()[0]
    
    return {
        'total_registros': total_registros,
        'total_ocs': total_ocs,
        'total_productos': total_productos,
        'por_estado': por_estado,
        'valor_total': round(valor_total, 2),
        'ultima_carga': ultima_carga
    }


def obtener_compras_por_oc(num_oc: str, conn: sqlite3.Connection) -> pd.DataFrame:
    """
    Obtiene todas las líneas de compra de una OC específica.
    
    Args:
        num_oc: Número de orden de compra
        conn: Conexión a la base de datos
        
    Returns:
        DataFrame con los detalles de la OC
    """
    query = """
        SELECT 
            num_oc,
            codprod,
            proveedor,
            cantidad_solicitada,
            cantidad_recibida,
            cantidad_manual,
            (cantidad_recibida + cantidad_manual) as cantidad_total_recibida,
            precio_compra,
            total_linea,
            fecha_oc,
            fecha_recepcion,
            estado_linea,
            bodega_nombre,
            observacion
        FROM compras
        WHERE num_oc = ?
        ORDER BY codprod
    """
    
    return pd.read_sql_query(query, conn, params=[num_oc])


def obtener_compras_pendientes(conn: sqlite3.Connection) -> pd.DataFrame:
    """
    Obtiene todas las líneas de compra con estado pendiente.
    
    Returns:
        DataFrame con compras pendientes
    """
    query = """
        SELECT 
            num_oc,
            codprod,
            proveedor,
            cantidad_solicitada,
            cantidad_recibida,
            cantidad_manual,
            (cantidad_solicitada - cantidad_recibida - cantidad_manual) as saldo_pendiente,
            fecha_oc,
            bodega_nombre
        FROM compras
        WHERE estado_linea = 'Pendiente'
           OR (cantidad_solicitada > (cantidad_recibida + cantidad_manual))
        ORDER BY fecha_oc ASC
    """
    
    return pd.read_sql_query(query, conn)


# ============================================================================
# FUNCIONES DE UTILIDAD PARA INTEGRACIÓN
# ============================================================================

def cargar_compras_desde_archivo_excel(ruta_archivo: str) -> Tuple[int, int, int, List[str]]:
    """
    Carga compras directamente desde un archivo Excel.
    Función de alto nivel para facilitar integración.
    
    Args:
        ruta_archivo: Ruta al archivo Excel con datos de compras
        
    Returns:
        Tuple[int, int, int, List[str]]: insertados, actualizados, sin_cambios, errores
    """
    try:
        # Leer archivo Excel
        df = pd.read_excel(ruta_archivo)
        
        # Cargar a base de datos
        with get_db_connection() as conn:
            return cargar_compras_desde_dataframe(df, conn)
            
    except Exception as e:
        return 0, 0, 0, [f"Error al procesar archivo: {str(e)}"]


def ejecutar_proceso_completo_compras(df_compras: pd.DataFrame) -> Dict:
    """
    Ejecuta el proceso completo: carga de compras + actualización de gestión.
    Función de alto nivel para ejecución en un solo paso.
    
    Args:
        df_compras: DataFrame con datos del cubo de compras
        
    Returns:
        Diccionario con resumen completo del proceso
    """
    resultado = {
        'exito': False,
        'carga_compras': {
            'insertados': 0,
            'actualizados': 0,
            'sin_cambios': 0,
            'errores': []
        },
        'actualizacion_gestion': {
            'actualizados': 0,
            'mensajes': []
        },
        'mensaje_general': ''
    }
    
    try:
        with get_db_connection() as conn:
            # Paso 1: Cargar compras
            print("📦 Paso 1/2: Cargando datos de compras...")
            insertados, actualizados, sin_cambios, errores = cargar_compras_desde_dataframe(df_compras, conn)
            
            resultado['carga_compras']['insertados'] = insertados
            resultado['carga_compras']['actualizados'] = actualizados
            resultado['carga_compras']['sin_cambios'] = sin_cambios
            resultado['carga_compras']['errores'] = errores
            
            # Paso 2: Actualizar gestión
            print("🔄 Paso 2/2: Actualizando gestión desde compras...")
            actualizados_gestion, mensajes = actualizar_gestion_desde_compras(conn)
            
            resultado['actualizacion_gestion']['actualizados'] = actualizados_gestion
            resultado['actualizacion_gestion']['mensajes'] = mensajes
            
            # Resumen
            resultado['exito'] = True
            resultado['mensaje_general'] = (
                f"✅ Proceso completado exitosamente. "
                f"Compras: {insertados} nuevas, {actualizados} actualizadas, {sin_cambios} sin cambios. "
                f"Gestión: {actualizados_gestion} registros actualizados."
            )
            
    except Exception as e:
        resultado['mensaje_general'] = f"❌ Error en el proceso: {str(e)}"
    
    return resultado


# ============================================================================
# BLOQUE DE EJECUCIÓN PRINCIPAL (PARA TESTING)
# ============================================================================

if __name__ == "__main__":
    """
    Bloque de prueba para verificar la inicialización del módulo.
    """
    print("=" * 70)
    print("MÓDULO DE COMPRAS - KS SEGURIDAD INDUSTRIAL")
    print("=" * 70)
    
    try:
        # Inicializar tablas
        inicializar_modulo_compras()
        
        # Mostrar estadísticas
        with get_db_connection() as conn:
            stats = obtener_estadisticas_compras(conn)
            print("\n📊 Estadísticas actuales:")
            print(f"   Total de registros: {stats['total_registros']}")
            print(f"   OCs únicas: {stats['total_ocs']}")
            print(f"   Productos únicos: {stats['total_productos']}")
            print(f"   Valor total: ${stats['valor_total']:,.2f}")
            if stats['ultima_carga']:
                print(f"   Última carga: {stats['ultima_carga']}")
            
            if stats['por_estado']:
                print("\n   Estados:")
                for estado, cantidad in stats['por_estado'].items():
                    print(f"   - {estado}: {cantidad}")
        
        print("\n✅ Módulo listo para producción")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        raise
