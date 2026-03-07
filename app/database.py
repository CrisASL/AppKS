"""
Módulo de gestión de base de datos SQLite
Incluye esquema, funciones CRUD y triggers de auditoría
KS Seguridad Industrial - Sistema de Requisiciones
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import pandas as pd
from contextlib import contextmanager
from app import config


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
    conn.row_factory = sqlite3.Row  # Permite acceso por nombre de columna
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


# ============================================================================
# INICIALIZACIÓN DE BASE DE DATOS
# ============================================================================

def inicializar_base_datos():
    """
    Crea todas las tablas, índices y triggers necesarios.
    Se ejecuta al inicio de la aplicación.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # ========================================================================
        # TABLA: requisiciones
        # ========================================================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS requisiciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numreq TEXT NOT NULL,
                codprod TEXT NOT NULL,
                desprod TEXT,
                cantidad INTEGER NOT NULL,
                fecha_requisicion DATE,
                sucursal_destino TEXT DEFAULT 'KS TALCA',
                proveedor TEXT,
                oc TEXT,
                n_guia TEXT,
                fecha_oc DATE,
                observacion TEXT,
                detalle TEXT,
                cant_recibida INTEGER DEFAULT 0,
                estado_oc TEXT DEFAULT 'Pendiente',
                saldo_pendiente INTEGER,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- Validaciones
                CHECK(cantidad > 0),
                CHECK(cant_recibida >= 0),
                CHECK(saldo_pendiente >= 0),
                
                -- Clave única compuesta: numreq + codprod
                UNIQUE(numreq, codprod)
            )
        """)
        
        # Índices para optimizar consultas frecuentes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_requisiciones_numreq 
            ON requisiciones(numreq)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_requisiciones_codprod 
            ON requisiciones(codprod)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_requisiciones_estado 
            ON requisiciones(estado_oc)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_requisiciones_oc 
            ON requisiciones(oc)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_requisiciones_fecha_oc 
            ON requisiciones(fecha_oc)
        """)
        
        # ========================================================================
        # TABLA: historial_cambios
        # ========================================================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS historial_cambios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                requisicion_id INTEGER NOT NULL,
                campo_modificado TEXT NOT NULL,
                valor_anterior TEXT,
                valor_nuevo TEXT,
                usuario TEXT DEFAULT 'Cristian Salas',
                fecha_cambio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (requisicion_id) REFERENCES requisiciones(id) ON DELETE CASCADE
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_historial_requisicion 
            ON historial_cambios(requisicion_id)
        """)
        
        # ========================================================================
        # TABLA: log_eliminaciones
        # ========================================================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS log_eliminaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                requisicion_datos TEXT NOT NULL,
                usuario TEXT DEFAULT 'Cristian Salas',
                fecha_eliminacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # ========================================================================
        # TABLA: configuracion
        # ========================================================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS configuracion (
                clave TEXT PRIMARY KEY,
                valor TEXT,
                fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # ========================================================================
        # TABLA: cargas_diarias
        # ========================================================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cargas_diarias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha_carga TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                registros_leidos INTEGER NOT NULL,
                registros_insertados INTEGER NOT NULL,
                registros_omitidos INTEGER DEFAULT 0,
                errores INTEGER DEFAULT 0,
                detalles TEXT,
                usuario TEXT DEFAULT 'Cristian Salas'
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_cargas_fecha
            ON cargas_diarias(fecha_carga)
        """)
        
        # ========================================================================
        # TRIGGERS DE AUDITORÍA
        # ========================================================================
        
        # Trigger: Registrar cambio de estado
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS registrar_cambio_estado
            AFTER UPDATE ON requisiciones
            FOR EACH ROW
            WHEN OLD.estado_oc != NEW.estado_oc
            BEGIN
                INSERT INTO historial_cambios (requisicion_id, campo_modificado, valor_anterior, valor_nuevo)
                VALUES (NEW.id, 'estado_oc', OLD.estado_oc, NEW.estado_oc);
            END
        """)
        
        # Trigger: Registrar cambio de proveedor
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS registrar_cambio_proveedor
            AFTER UPDATE ON requisiciones
            FOR EACH ROW
            WHEN OLD.proveedor != NEW.proveedor
            BEGIN
                INSERT INTO historial_cambios (requisicion_id, campo_modificado, valor_anterior, valor_nuevo)
                VALUES (NEW.id, 'proveedor', OLD.proveedor, NEW.proveedor);
            END
        """)
        
        # Trigger: Registrar cambio de OC
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS registrar_cambio_oc
            AFTER UPDATE ON requisiciones
            FOR EACH ROW
            WHEN OLD.oc != NEW.oc OR (OLD.oc IS NULL AND NEW.oc IS NOT NULL)
            BEGIN
                INSERT INTO historial_cambios (requisicion_id, campo_modificado, valor_anterior, valor_nuevo)
                VALUES (NEW.id, 'oc', OLD.oc, NEW.oc);
            END
        """)
        
        # Trigger: Registrar cambio de cantidad recibida
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS registrar_cambio_cant_recibida
            AFTER UPDATE ON requisiciones
            FOR EACH ROW
            WHEN OLD.cant_recibida != NEW.cant_recibida
            BEGIN
                INSERT INTO historial_cambios (requisicion_id, campo_modificado, valor_anterior, valor_nuevo)
                VALUES (NEW.id, 'cant_recibida', OLD.cant_recibida, NEW.cant_recibida);
            END
        """)
        
        # Trigger: Actualizar fecha de modificación
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS actualizar_fecha_modificacion
            AFTER UPDATE ON requisiciones
            FOR EACH ROW
            BEGIN
                UPDATE requisiciones 
                SET fecha_modificacion = CURRENT_TIMESTAMP 
                WHERE id = NEW.id;
            END
        """)
        
        # Trigger: Calcular saldo pendiente automáticamente
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS calcular_saldo_pendiente_insert
            AFTER INSERT ON requisiciones
            FOR EACH ROW
            BEGIN
                UPDATE requisiciones 
                SET saldo_pendiente = cantidad - cant_recibida 
                WHERE id = NEW.id;
            END
        """)
        
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS calcular_saldo_pendiente_update
            AFTER UPDATE ON requisiciones
            FOR EACH ROW
            WHEN OLD.cantidad != NEW.cantidad OR OLD.cant_recibida != NEW.cant_recibida
            BEGIN
                UPDATE requisiciones 
                SET saldo_pendiente = NEW.cantidad - NEW.cant_recibida 
                WHERE id = NEW.id;
            END
        """)
        
        conn.commit()


def migrar_base_datos_existente():
    """
    Migra bases de datos existentes para agregar nuevos campos y constraints.
    Se ejecuta automáticamente al iniciar la aplicación.
    Es seguro ejecutar múltiples veces (idempotente).
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar si la columna fecha_requisicion ya existe
            cursor.execute("PRAGMA table_info(requisiciones)")
            columnas_existentes = [col[1] for col in cursor.fetchall()]
            
            if 'fecha_requisicion' not in columnas_existentes:
                print("⚙️ Migrando: Agregando campo fecha_requisicion...")
                cursor.execute("""
                    ALTER TABLE requisiciones 
                    ADD COLUMN fecha_requisicion DATE
                """)
                conn.commit()
                print("✅ Campo fecha_requisicion agregado exitosamente")
            
            # Verificar si existe constraint UNIQUE(numreq, codprod)
            cursor.execute("""
                SELECT sql FROM sqlite_master 
                WHERE type='table' AND name='requisiciones'
            """)
            
            tabla_sql = cursor.fetchone()
            
            if tabla_sql:
                tabla_sql = tabla_sql[0]
                
                # Verificar si tiene el constraint compuesto correcto
                if 'UNIQUE(numreq, codprod)' not in tabla_sql:
                    print("⚙️ Migrando: Actualizando constraint UNIQUE a (numreq, codprod)...")
                    
                    # Eliminar índice antiguo si existe
                    cursor.execute("""
                        DROP INDEX IF EXISTS idx_requisiciones_numreq_unique
                    """)
                    
                    # Verificar duplicados con la nueva clave compuesta
                    cursor.execute("""
                        SELECT numreq, codprod, COUNT(*) as cnt 
                        FROM requisiciones 
                        GROUP BY numreq, codprod 
                        HAVING cnt > 1
                    """)
                    
                    duplicados = cursor.fetchall()
                    
                    if duplicados:
                        print(f"⚠️ ADVERTENCIA: Se encontraron {len(duplicados)} combinaciones numreq+codprod duplicadas")
                        print("Se mantendrá el registro más reciente de cada duplicado")
                        
                        # Eliminar duplicados, manteniendo el más reciente
                        for numreq, codprod, cnt in duplicados:
                            cursor.execute("""
                                DELETE FROM requisiciones 
                                WHERE numreq = ? AND codprod = ?
                                AND id NOT IN (
                                    SELECT id FROM requisiciones 
                                    WHERE numreq = ? AND codprod = ?
                                    ORDER BY fecha_creacion DESC 
                                    LIMIT 1
                                )
                            """, (numreq, codprod, numreq, codprod))
                    
                    # Crear índice único compuesto
                    cursor.execute("""
                        CREATE UNIQUE INDEX IF NOT EXISTS idx_requisiciones_numreq_codprod_unique 
                        ON requisiciones(numreq, codprod)
                    """)
                    
                    conn.commit()
                    print("✅ Constraint UNIQUE(numreq, codprod) agregado exitosamente")
            
            print("✅ Migración completada exitosamente")
            
    except Exception as e:
        print(f"❌ Error durante la migración: {str(e)}")
        raise


# ============================================================================
# FUNCIONES CRUD - CREATE
# ============================================================================

def crear_requisicion(datos: Dict) -> int:
    """
    Crea una nueva requisición en la base de datos.
    
    Args:
        datos (dict): Diccionario con los datos de la requisición
            Campos requeridos: numreq, codprod, cantidad
            Campos opcionales: desprod, sucursal_destino, proveedor, oc, 
                             n_guia, fecha_oc, observacion, detalle, 
                             cant_recibida, estado_oc
    
    Returns:
        int: ID de la requisición creada, o -1 si hubo error
    
    Raises:
        ValueError: Si faltan campos requeridos o datos inválidos
        sqlite3.Error: Si hay error en la base de datos
    """
    # Validar campos requeridos
    campos_requeridos = ['numreq', 'codprod', 'cantidad']
    for campo in campos_requeridos:
        if campo not in datos or datos[campo] is None or datos[campo] == '':
            raise ValueError(f"Campo requerido faltante: {campo}")
    
    # Validar cantidad
    if datos['cantidad'] <= 0:
        raise ValueError("La cantidad debe ser mayor a 0")
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Preparar datos con valores por defecto
            insert_data = {
                'numreq': datos['numreq'],
                'codprod': datos['codprod'],
                'desprod': datos.get('desprod', ''),
                'cantidad': datos['cantidad'],
                'sucursal_destino': datos.get('sucursal_destino', config.DEFAULT_SUCURSAL),
                'proveedor': datos.get('proveedor', ''),
                'oc': datos.get('oc', ''),
                'n_guia': datos.get('n_guia', ''),
                'fecha_oc': datos.get('fecha_oc', None),
                'observacion': datos.get('observacion', ''),
                'detalle': datos.get('detalle', ''),
                'cant_recibida': datos.get('cant_recibida', config.DEFAULT_CANT_RECIBIDA),
                'estado_oc': datos.get('estado_oc', config.DEFAULT_ESTADO)
            }
            
            cursor.execute("""
                INSERT INTO requisiciones (
                    numreq, codprod, desprod, cantidad, sucursal_destino,
                    proveedor, oc, n_guia, fecha_oc, observacion, detalle,
                    cant_recibida, estado_oc
                ) VALUES (
                    :numreq, :codprod, :desprod, :cantidad, :sucursal_destino,
                    :proveedor, :oc, :n_guia, :fecha_oc, :observacion, :detalle,
                    :cant_recibida, :estado_oc
                )
            """, insert_data)
            
            requisicion_id = cursor.lastrowid
            conn.commit()
            
            return requisicion_id
            
    except sqlite3.Error as e:
        raise


def cargar_requisiciones_desde_cubo(df_cubo: pd.DataFrame) -> Tuple[int, int, List[str]]:
    """
    Carga requisiciones desde el cubo Excel a la base de datos de forma IDEMPOTENTE.
    
    Características:
    - NUNCA borra registros existentes
    - NUNCA duplica requisiciones (usa numreq como clave única)
    - Solo inserta requisiciones nuevas que no existen en la BD
    - Mapea FEmision -> fecha_requisicion
    - Registra estadísticas de la carga en tabla cargas_diarias
    
    Args:
        df_cubo (pd.DataFrame): DataFrame con el cubo de requisiciones
    
    Returns:
        Tuple[int, int, List[str]]: 
            - Cantidad de requisiciones insertadas exitosamente
            - Cantidad de errores
            - Lista de mensajes de error
    """
    insertadas = 0
    errores = 0
    omitidas = 0
    mensajes_error = []
    registros_leidos = len(df_cubo)
    
    inicio_carga = datetime.now()
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Obtener lista de combinaciones (numreq, codprod) existentes para validación previa
            cursor.execute("SELECT numreq, codprod FROM requisiciones")
            claves_existentes = {(row[0], row[1]) for row in cursor.fetchall()}
            
            # Iterar sobre cada fila del cubo
            for index, row in df_cubo.iterrows():
                try:
                    # Obtener cantidad solicitada para TALCA
                    cantidad = row.get('TALCA', 0)
                    
                    # Si no hay cantidad solicitada, saltar esta fila
                    if pd.isna(cantidad) or cantidad == 0:
                        continue
                    
                    # Convertir cantidad a entero
                    cantidad = int(cantidad)
                    
                    # Obtener NumReq y CodProd - clave de negocio compuesta
                    numreq = str(row.get('NumReq', '')).strip()
                    
                    # Validar campos críticos
                    if not numreq:
                        errores += 1
                        mensajes_error.append(f"Fila {index + 1}: Falta NumReq")
                        continue
                    
                    codprod = str(row.get('CodProd', '')).strip()
                    if not codprod:
                        errores += 1
                        mensajes_error.append(f"Fila {index + 1}: Falta CodProd (NumReq: {numreq})")
                        continue
                    
                    # Verificar si ya existe - REGLA DE IDEMPOTENCIA
                    # Usa clave compuesta (numreq, codprod)
                    if (numreq, codprod) in claves_existentes:
                        omitidas += 1
                        continue  # Ignorar silenciosamente, no actualizar                    \n                    # Obtener y normalizar FEmision -> fecha_requisicion
                    fecha_requisicion = None
                    femision = row.get('FEmision')
                    
                    if pd.notna(femision):
                        try:
                            # Intentar convertir a fecha estándar
                            if isinstance(femision, str):
                                fecha_requisicion = pd.to_datetime(femision, errors='coerce').strftime('%Y-%m-%d')
                            elif isinstance(femision, (pd.Timestamp, datetime)):
                                fecha_requisicion = femision.strftime('%Y-%m-%d')
                            else:
                                # Puede ser un número de serie de Excel
                                fecha_requisicion = pd.to_datetime(femision, origin='1899-12-30', unit='D', errors='coerce')
                                if pd.notna(fecha_requisicion):
                                    fecha_requisicion = fecha_requisicion.strftime('%Y-%m-%d')
                        except:
                            pass  # Si falla la conversión, fecha_requisicion queda como None
                    
                    # Preparar datos de la requisición
                    datos_requisicion = {
                        'numreq': numreq,
                        'codprod': codprod,
                        'desprod': str(row.get('DesProd', '')),
                        'cantidad': cantidad,
                        'fecha_requisicion': fecha_requisicion,
                        'sucursal_destino': config.DEFAULT_SUCURSAL,
                        'proveedor': '',
                        'oc': '',
                        'n_guia': '',
                        'fecha_oc': None,
                        'observacion': '',
                        'detalle': f"Cargado desde cubo - Stock Talca: {row.get('KS TALCA', 0)}",
                        'cant_recibida': 0,
                        'estado_oc': config.DEFAULT_ESTADO
                    }
                    
                    # Insertar SOLO si no existe (INSERT OR IGNORE garantiza idempotencia)
                    cursor.execute("""
                        INSERT OR IGNORE INTO requisiciones (
                            numreq, codprod, desprod, cantidad, fecha_requisicion,
                            sucursal_destino, proveedor, oc, n_guia, fecha_oc, 
                            observacion, detalle, cant_recibida, estado_oc
                        ) VALUES (
                            :numreq, :codprod, :desprod, :cantidad, :fecha_requisicion,
                            :sucursal_destino, :proveedor, :oc, :n_guia, :fecha_oc,
                            :observacion, :detalle, :cant_recibida, :estado_oc
                        )
                    """, datos_requisicion)
                    
                    # Verificar si realmente se insertó
                    if cursor.rowcount > 0:
                        insertadas += 1
                        claves_existentes.add((numreq, codprod))  # Actualizar caché local
                    else:
                        omitidas += 1
                    
                except Exception as e:
                    errores += 1
                    mensajes_error.append(f"Fila {index + 1}: {str(e)}")
                    continue
            
            # Registrar estadísticas de la carga en tabla de auditoría
            detalles = {
                'registros_leidos': registros_leidos,
                'insertadas': insertadas,
                'omitidas': omitidas,
                'errores': errores,
                'duracion_segundos': (datetime.now() - inicio_carga).total_seconds(),
                'mensajes_error': mensajes_error[:10] if mensajes_error else []  # Solo primeros 10 errores
            }
            
            cursor.execute("""
                INSERT INTO cargas_diarias (
                    fecha_carga, registros_leidos, registros_insertados, 
                    registros_omitidos, errores, detalles
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                registros_leidos,
                insertadas,
                omitidas,
                errores,
                json.dumps(detalles, ensure_ascii=False)
            ))
            
            conn.commit()
            
    except Exception as e:
        mensajes_error.append(f"Error general: {str(e)}")
        return 0, 0, mensajes_error
    
    return insertadas, errores, mensajes_error


# ============================================================================
# FUNCIONES CRUD - READ
# ============================================================================

def obtener_requisiciones(filtros: Optional[Dict] = None) -> pd.DataFrame:
    """
    Obtiene requisiciones con filtros opcionales.
    
    Args:
        filtros (dict, optional): Diccionario con filtros
            - estado_oc: str o list - Estado(s) de la OC
            - fecha_desde: str - Fecha inicio requisición (YYYY-MM-DD)
            - fecha_hasta: str - Fecha fin requisición (YYYY-MM-DD)
            - proveedor: str o list - Proveedor(es)
            - numreq: str - Número de requisición (búsqueda parcial)
            - codprod: str - Código de producto (búsqueda parcial)
            - oc: str - Número de OC
            - solo_pendientes: bool - Solo con saldo pendiente > 0
    
    Returns:
        pd.DataFrame: DataFrame con las requisiciones encontradas
    """
    query = "SELECT * FROM requisiciones WHERE 1=1"
    params = []
    
    if filtros:
        # Filtro por estado
        if 'estado_oc' in filtros and filtros['estado_oc']:
            if isinstance(filtros['estado_oc'], list):
                placeholders = ','.join(['?' for _ in filtros['estado_oc']])
                query += f" AND estado_oc IN ({placeholders})"
                params.extend(filtros['estado_oc'])
            else:
                query += " AND estado_oc = ?"
                params.append(filtros['estado_oc'])
        
        # Filtro por rango de fechas
        if 'fecha_desde' in filtros and filtros['fecha_desde']:
            query += " AND fecha_requisicion >= ?"
            params.append(filtros['fecha_desde'])
        
        if 'fecha_hasta' in filtros and filtros['fecha_hasta']:
            query += " AND fecha_requisicion <= ?"
            params.append(filtros['fecha_hasta'])
        
        # Filtro por proveedor
        if 'proveedor' in filtros and filtros['proveedor']:
            if isinstance(filtros['proveedor'], list):
                placeholders = ','.join(['?' for _ in filtros['proveedor']])
                query += f" AND proveedor IN ({placeholders})"
                params.extend(filtros['proveedor'])
            else:
                query += " AND proveedor LIKE ?"
                params.append(f"%{filtros['proveedor']}%")
        
        # Filtro por número de requisición
        if 'numreq' in filtros and filtros['numreq']:
            query += " AND numreq LIKE ?"
            params.append(f"%{filtros['numreq']}%")
        
        # Filtro por código de producto
        if 'codprod' in filtros and filtros['codprod']:
            query += " AND codprod LIKE ?"
            params.append(f"%{filtros['codprod']}%")
        
        # Filtro por OC
        if 'oc' in filtros and filtros['oc']:
            query += " AND oc = ?"
            params.append(filtros['oc'])
        
        # Filtro solo pendientes
        if 'solo_pendientes' in filtros and filtros['solo_pendientes']:
            query += " AND saldo_pendiente > 0"
    
    # Ordenar por fecha de creación descendente
    query += " ORDER BY fecha_creacion DESC"
    
    try:
        with get_db_connection() as conn:
            df = pd.read_sql_query(query, conn, params=params)
            return df
    except Exception as e:
        return pd.DataFrame()


def obtener_requisicion_por_id(requisicion_id: int) -> Optional[Dict]:
    """
    Obtiene una requisición específica por su ID.
    
    Args:
        requisicion_id (int): ID de la requisición
    
    Returns:
        dict: Diccionario con los datos de la requisición, o None si no existe
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM requisiciones WHERE id = ?", (requisicion_id,))
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            return None
            
    except Exception as e:
        return None


def obtener_req_pendientes() -> pd.DataFrame:
    """
    Obtiene todas las requisiciones con saldo pendiente > 0.
    
    Returns:
        pd.DataFrame: DataFrame con requisiciones pendientes
    """
    return obtener_requisiciones({'solo_pendientes': True})


def obtener_estadisticas_generales() -> Dict:
    """
    Calcula estadísticas generales para el dashboard.
    
    Returns:
        dict: Diccionario con métricas principales
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Total de requisiciones pendientes (saldo > 0)
            cursor.execute("SELECT COUNT(*) FROM requisiciones WHERE saldo_pendiente > 0")
            req_pendientes = cursor.fetchone()[0]
            
            # OC en tránsito
            cursor.execute("""
                SELECT COUNT(*) FROM requisiciones 
                WHERE estado_oc IN ('En Tránsito', 'Guía de Despacho', 'Recepción Parcial')
            """)
            oc_transito = cursor.fetchone()[0]
            
            # Productos únicos con requisiciones pendientes
            cursor.execute("""
                SELECT COUNT(DISTINCT codprod) FROM requisiciones 
                WHERE saldo_pendiente > 0
            """)
            productos_pendientes = cursor.fetchone()[0]
            
            # Valor total de OC (simulado - requiere cubo de compras)
            # Por ahora retornamos 0
            valor_total_oc = 0
            
            return {
                'req_pendientes': req_pendientes,
                'oc_transito': oc_transito,
                'productos_pendientes': productos_pendientes,
                'valor_total_oc': valor_total_oc
            }
            
    except Exception as e:
        return {
            'req_pendientes': 0,
            'oc_transito': 0,
            'productos_pendientes': 0,
            'valor_total_oc': 0
        }


def obtener_historial_cargas(limite: int = 50) -> pd.DataFrame:
    """
    Obtiene el historial de cargas diarias desde la tabla de auditoría.
    
    Args:
        limite (int): Número máximo de registros a retornar (por defecto 50)
    
    Returns:
        pd.DataFrame: DataFrame con el historial de cargas
    """
    try:
        with get_db_connection() as conn:
            query = """
                SELECT 
                    id,
                    fecha_carga,
                    registros_leidos,
                    registros_insertados,
                    registros_omitidos,
                    errores,
                    usuario,
                    detalles
                FROM cargas_diarias
                ORDER BY fecha_carga DESC
                LIMIT ?
            """
            df = pd.read_sql_query(query, conn, params=(limite,))
            
            # Parsear detalles JSON si existe
            if 'detalles' in df.columns and not df.empty:
                try:
                    df['detalles_json'] = df['detalles'].apply(
                        lambda x: json.loads(x) if pd.notna(x) else {}
                    )
                except:
                    pass
            
            return df
            
    except Exception as e:
        print(f"Error al obtener historial de cargas: {str(e)}")
        return pd.DataFrame()


def obtener_ultima_carga() -> Dict:
    """
    Obtiene información de la última carga realizada.
    
    Returns:
        dict: Diccionario con información de la última carga, o None si no hay cargas
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    fecha_carga,
                    registros_leidos,
                    registros_insertados,
                    registros_omitidos,
                    errores
                FROM cargas_diarias
                ORDER BY fecha_carga DESC
                LIMIT 1
            """)
            
            row = cursor.fetchone()
            if row:
                return {
                    'fecha_carga': row[0],
                    'registros_leidos': row[1],
                    'registros_insertados': row[2],
                    'registros_omitidos': row[3],
                    'errores': row[4]
                }
            return None
            
    except Exception as e:
        print(f"Error al obtener última carga: {str(e)}")
        return None


# ============================================================================
# FUNCIONES CRUD - UPDATE
# ============================================================================

def actualizar_requisicion(requisicion_id: int, datos: Dict) -> bool:
    """
    Actualiza una requisición existente.
    
    Args:
        requisicion_id (int): ID de la requisición a actualizar
        datos (dict): Diccionario con los campos a actualizar
    
    Returns:
        bool: True si se actualizó correctamente, False en caso contrario
    """
    # Campos permitidos para actualizar
    campos_permitidos = [
        'numreq', 'codprod', 'desprod', 'cantidad', 'sucursal_destino',
        'proveedor', 'oc', 'n_guia', 'fecha_oc', 'observacion', 'detalle',
        'cant_recibida', 'estado_oc'
    ]
    
    # Filtrar solo campos válidos
    datos_filtrados = {k: v for k, v in datos.items() if k in campos_permitidos}
    
    if not datos_filtrados:
        return False
    
    # Construir query dinámicamente
    set_clause = ', '.join([f"{campo} = ?" for campo in datos_filtrados.keys()])
    query = f"UPDATE requisiciones SET {set_clause} WHERE id = ?"
    params = list(datos_filtrados.values()) + [requisicion_id]
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            if cursor.rowcount > 0:
                return True
            else:
                return False
                
    except Exception as e:
        return False


def actualizar_estado(requisicion_id: int, nuevo_estado: str) -> bool:
    """
    Actualiza solo el estado de una requisición.
    
    Args:
        requisicion_id (int): ID de la requisición
        nuevo_estado (str): Nuevo estado de la OC
    
    Returns:
        bool: True si se actualizó correctamente
    """
    if nuevo_estado not in config.ESTADOS_OC:
        return False
    
    return actualizar_requisicion(requisicion_id, {'estado_oc': nuevo_estado})


def actualizar_requisicion_desde_ui(requisicion_id: int, datos_editados: Dict) -> Tuple[bool, str]:
    """
    Actualiza una requisición con datos provenientes de la UI (st.data_editor).
    
    SEGURIDAD: Solo permite actualizar campos administrativos/manuales definidos
    en config.CAMPOS_EDITABLES_UI. Cualquier intento de modificar campos protegidos
    será ignorado automáticamente.
    
    Args:
        requisicion_id (int): ID de la requisición a actualizar
        datos_editados (dict): Diccionario con los campos editados desde la UI
            Solo se procesarán los campos en CAMPOS_EDITABLES_UI:
            - proveedor
            - oc
            - n_guia
            - fecha_oc
            - observacion
            - detalle
    
    Returns:
        Tuple[bool, str]: 
            - bool: True si se actualizó correctamente, False en caso contrario
            - str: Mensaje descriptivo del resultado
    
    Ejemplos:
        >>> actualizar_requisicion_desde_ui(1, {'proveedor': 'ACME Corp', 'oc': '12345'})
        (True, 'Actualización exitosa: 2 campos modificados')
        
        >>> actualizar_requisicion_desde_ui(999, {'proveedor': 'Test'})
        (False, 'Requisición no encontrada')
        
        >>> actualizar_requisicion_desde_ui(1, {'cantidad': 999, 'proveedor': 'OK'})
        (True, 'Actualización exitosa: 1 campos modificados (1 campos ignorados por seguridad)')
    
    Notas:
        - Los campos protegidos (id, cantidad, cant_recibida, estado_oc, etc.) 
          son filtrados automáticamente y no generan error
        - Los campos numéricos/fechas se validan antes de actualizar
        - Los campos de texto se truncan según límites en config.LIMITES_CAMPOS_EDITABLES
        - Los triggers de auditoría se ejecutan automáticamente
    """
    # Validar que la requisición existe
    req_actual = obtener_requisicion_por_id(requisicion_id)
    if not req_actual:
        return False, 'Requisición no encontrada'
    
    # Filtrar solo campos editables permitidos
    campos_editables = config.CAMPOS_EDITABLES_UI
    datos_seguros = {}
    campos_ignorados = 0
    
    for campo, valor in datos_editados.items():
        if campo in campos_editables:
            # Aplicar límites de caracteres si aplica
            if campo in config.LIMITES_CAMPOS_EDITABLES:
                limite = config.LIMITES_CAMPOS_EDITABLES[campo]
                if isinstance(valor, str) and len(valor) > limite:
                    valor = valor[:limite]
            
            # Convertir valores None/NaN a string vacío para campos de texto
            if campo in ['proveedor', 'oc', 'n_guia', 'observacion', 'detalle']:
                if valor is None or (isinstance(valor, float) and pd.isna(valor)):
                    valor = ''
            
            # Validar fecha_oc si se proporciona
            if campo == 'fecha_oc' and valor:
                if isinstance(valor, str):
                    try:
                        # Intentar parsear la fecha
                        pd.to_datetime(valor)
                    except:
                        continue  # Ignorar fecha inválida
            
            datos_seguros[campo] = valor
        else:
            # Campo no permitido, contabilizar pero ignorar silenciosamente
            campos_ignorados += 1
    
    # Si no hay campos válidos para actualizar
    if not datos_seguros:
        if campos_ignorados > 0:
            return False, f'No se actualizó nada. {campos_ignorados} campo(s) protegido(s) ignorado(s)'
        else:
            return False, 'No hay campos válidos para actualizar'
    
    # Construir query dinámicamente solo con campos seguros
    set_clause = ', '.join([f"{campo} = ?" for campo in datos_seguros.keys()])
    query = f"UPDATE requisiciones SET {set_clause} WHERE id = ?"
    params = list(datos_seguros.values()) + [requisicion_id]
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()  # Commit explícito para asegurar persistencia
            
            if cursor.rowcount > 0:
                campos_actualizados = len(datos_seguros)
                mensaje = f'Actualización exitosa: {campos_actualizados} campo(s) modificado(s)'
                
                if campos_ignorados > 0:
                    mensaje += f' ({campos_ignorados} campo(s) ignorado(s) por seguridad)'
                
                return True, mensaje
            else:
                return False, 'No se pudo actualizar la requisición'
                
    except sqlite3.Error as e:
        return False, f'Error de base de datos: {str(e)}'
    except Exception as e:
        return False, f'Error inesperado: {str(e)}'


def registrar_recepcion(requisicion_id: int, cantidad_recibida: int, n_guia: str = None) -> bool:
    """
    Registra la recepción de mercadería para una requisición.
    Actualiza cantidad recibida, guía de despacho y estado si corresponde.
    
    Args:
        requisicion_id (int): ID de la requisición
        cantidad_recibida (int): Cantidad recibida en esta recepción
        n_guia (str, optional): Número de guía de despacho
    
    Returns:
        bool: True si se registró correctamente
    """
    try:
        # Obtener requisición actual
        req = obtener_requisicion_por_id(requisicion_id)
        if not req:
            return False
        
        # Calcular nueva cantidad recibida
        nueva_cant_recibida = req['cant_recibida'] + cantidad_recibida
        
        # Validar que no exceda la cantidad solicitada
        if nueva_cant_recibida > req['cantidad']:
            return False
        
        # Determinar nuevo estado
        if nueva_cant_recibida == req['cantidad']:
            nuevo_estado = 'Recepción Completa'
        elif nueva_cant_recibida > 0:
            nuevo_estado = 'Recepción Parcial'
        else:
            nuevo_estado = req['estado_oc']
        
        # Preparar datos de actualización
        datos_actualizacion = {
            'cant_recibida': nueva_cant_recibida,
            'estado_oc': nuevo_estado
        }
        
        if n_guia:
            datos_actualizacion['n_guia'] = n_guia
        
        # Actualizar requisición
        return actualizar_requisicion(requisicion_id, datos_actualizacion)
        
    except Exception as e:
        return False


def procesar_ediciones_batch_ui(df_original: pd.DataFrame, df_editado: pd.DataFrame) -> Dict[str, any]:
    """
    Procesa múltiples ediciones realizadas en st.data_editor de forma batch.
    
    Compara el DataFrame original con el editado, identifica las filas modificadas
    y actualiza solo los campos permitidos en la base de datos.
    
    Args:
        df_original (pd.DataFrame): DataFrame original antes de editar
        df_editado (pd.DataFrame): DataFrame después de las ediciones del usuario
    
    Returns:
        Dict con resumen de la operación:
            - 'exitosas': int - Cantidad de actualizaciones exitosas
            - 'fallidas': int - Cantidad de actualizaciones fallidas
            - 'sin_cambios': int - Filas sin cambios
            - 'mensajes': List[str] - Mensajes detallados de cada operación
            - 'success': bool - True si al menos una actualización fue exitosa
    
    Ejemplos:
        >>> resultado = procesar_ediciones_batch_ui(df_antes, df_despues)
        >>> st.success(f"✅ {resultado['exitosas']} requisiciones actualizadas")
        >>> if resultado['fallidas'] > 0:
        >>>     st.warning(f"⚠️ {resultado['fallidas']} fallos")
    
    Notas:
        - Requiere que ambos DataFrames tengan columna 'id'
        - Solo procesa filas que existen en ambos DataFrames
        - Ignora automáticamente campos no editables (seguridad)
        - Maneja valores NaN/None correctamente
    """
    resultado = {
        'exitosas': 0,
        'fallidas': 0,
        'sin_cambios': 0,
        'mensajes': [],
        'success': False
    }
    
    # Validar que ambos DataFrames tengan la columna 'id'
    if 'id' not in df_original.columns or 'id' not in df_editado.columns:
        resultado['mensajes'].append('Error: DataFrames deben tener columna "id"')
        return resultado
    
    # Convertir a diccionarios indexados por 'id' para comparación eficiente
    dict_original = df_original.set_index('id').to_dict('index')
    dict_editado = df_editado.set_index('id').to_dict('index')
    
    # Procesar cada fila editada
    for req_id, fila_editada in dict_editado.items():
        # Verificar que la fila existe en el original
        if req_id not in dict_original:
            resultado['mensajes'].append(f"ID {req_id}: No existe en datos originales (omitido)")
            continue
        
        fila_original = dict_original[req_id]
        
        # Detectar campos modificados (solo campos editables)
        cambios = {}
        for campo in config.CAMPOS_EDITABLES_UI:
            if campo in fila_editada and campo in fila_original:
                valor_nuevo = fila_editada[campo]
                valor_original = fila_original[campo]
                
                # Normalizar valores vacíos/None/NaN a string vacío para comparación
                def normalizar_valor(val):
                    if val is None or (isinstance(val, float) and pd.isna(val)):
                        return ''
                    if isinstance(val, str) and val == 'nan':
                        return ''
                    return str(val).strip() if val != '' else ''
                
                val_nuevo_norm = normalizar_valor(valor_nuevo)
                val_orig_norm = normalizar_valor(valor_original)
                
                # Comparar valores normalizados
                if val_nuevo_norm != val_orig_norm:
                    # Guardar el valor original (no normalizado) para la BD
                    cambios[campo] = valor_nuevo
        
        # Si hay cambios, actualizar
        if cambios:
            exito, mensaje = actualizar_requisicion_desde_ui(req_id, cambios)
            
            if exito:
                resultado['exitosas'] += 1
                resultado['mensajes'].append(f"ID {req_id}: {mensaje}")
            else:
                resultado['fallidas'] += 1
                resultado['mensajes'].append(f"ID {req_id}: Error - {mensaje}")
        else:
            resultado['sin_cambios'] += 1
    
    # Marcar como exitoso si al menos una actualización funcionó
    # O si no hubo cambios pero tampoco errores (operación válida)
    resultado['success'] = resultado['exitosas'] > 0 or (resultado['fallidas'] == 0 and len(dict_editado) > 0)
    
    return resultado


# ============================================================================
# FUNCIONES CRUD - DELETE
# ============================================================================

def eliminar_requisicion(requisicion_id: int) -> bool:
    """
    Elimina una requisición (soft delete).
    Registra los datos en log_eliminaciones antes de eliminar.
    
    Args:
        requisicion_id (int): ID de la requisición a eliminar
    
    Returns:
        bool: True si se eliminó correctamente
    """
    try:
        # Obtener datos de la requisición antes de eliminar
        req = obtener_requisicion_por_id(requisicion_id)
        if not req:
            return False
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Registrar en log de eliminaciones
            cursor.execute("""
                INSERT INTO log_eliminaciones (requisicion_datos)
                VALUES (?)
            """, (json.dumps(req, default=str),))
            
            # Eliminar requisición
            cursor.execute("DELETE FROM requisiciones WHERE id = ?", (requisicion_id,))
            
            conn.commit()
            return True
            
    except Exception as e:
        return False


# ============================================================================
# FUNCIONES DE HISTORIAL
# ============================================================================

def obtener_historial(requisicion_id: int) -> pd.DataFrame:
    """
    Obtiene el historial completo de cambios de una requisición.
    
    Args:
        requisicion_id (int): ID de la requisición
    
    Returns:
        pd.DataFrame: DataFrame con el historial de cambios
    """
    query = """
        SELECT 
            campo_modificado,
            valor_anterior,
            valor_nuevo,
            usuario,
            fecha_cambio
        FROM historial_cambios
        WHERE requisicion_id = ?
        ORDER BY fecha_cambio DESC
    """
    
    try:
        with get_db_connection() as conn:
            df = pd.read_sql_query(query, conn, params=(requisicion_id,))
            return df
    except Exception as e:
        return pd.DataFrame()


# ============================================================================
# FUNCIONES DE CONFIGURACIÓN
# ============================================================================

def guardar_configuracion(clave: str, valor: str) -> bool:
    """
    Guarda una configuración en la base de datos.
    
    Args:
        clave (str): Clave de configuración
        valor (str): Valor a guardar
    
    Returns:
        bool: True si se guardó correctamente
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO configuracion (clave, valor, fecha_actualizacion)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (clave, valor))
            conn.commit()
            return True
    except Exception as e:
        return False


def obtener_configuracion(clave: str, default: str = None) -> Optional[str]:
    """
    Obtiene una configuración de la base de datos.
    
    Args:
        clave (str): Clave de configuración
        default (str, optional): Valor por defecto si no existe
    
    Returns:
        str: Valor de la configuración, o default si no existe
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT valor FROM configuracion WHERE clave = ?", (clave,))
            row = cursor.fetchone()
            
            if row:
                return row[0]
            return default
            
    except Exception as e:
        return default


# ============================================================================
# FUNCIONES DE ANÁLISIS
# ============================================================================

def obtener_productos_mas_solicitados(limite: int = 10) -> pd.DataFrame:
    """
    Obtiene los productos más solicitados.
    
    Args:
        limite (int): Número máximo de productos a retornar
    
    Returns:
        pd.DataFrame: DataFrame con productos y cantidad total solicitada
    """
    query = """
        SELECT 
            codprod,
            desprod,
            COUNT(*) as num_requisiciones,
            SUM(cantidad) as cantidad_total,
            SUM(saldo_pendiente) as saldo_pendiente_total
        FROM requisiciones
        GROUP BY codprod, desprod
        ORDER BY cantidad_total DESC
        LIMIT ?
    """
    
    try:
        with get_db_connection() as conn:
            df = pd.read_sql_query(query, conn, params=(limite,))
            return df
    except Exception as e:
        return pd.DataFrame()


def obtener_proveedores_mas_usados(limite: int = 10) -> pd.DataFrame:
    """
    Obtiene los proveedores más utilizados.
    
    Args:
        limite (int): Número máximo de proveedores a retornar
    
    Returns:
        pd.DataFrame: DataFrame con proveedores y número de OC
    """
    query = """
        SELECT 
            proveedor,
            COUNT(*) as num_oc,
            COUNT(DISTINCT codprod) as num_productos
        FROM requisiciones
        WHERE proveedor IS NOT NULL AND proveedor != ''
        GROUP BY proveedor
        ORDER BY num_oc DESC
        LIMIT ?
    """
    
    try:
        with get_db_connection() as conn:
            df = pd.read_sql_query(query, conn, params=(limite,))
            return df
    except Exception as e:
        return pd.DataFrame()


def obtener_distribucion_estados() -> pd.DataFrame:
    """
    Obtiene la distribución de requisiciones por estado.
    
    Returns:
        pd.DataFrame: DataFrame con estados y cantidad
    """
    query = """
        SELECT 
            estado_oc,
            COUNT(*) as cantidad
        FROM requisiciones
        GROUP BY estado_oc
        ORDER BY cantidad DESC
    """
    
    try:
        with get_db_connection() as conn:
            df = pd.read_sql_query(query, conn)
            return df
    except Exception as e:
        return pd.DataFrame()


def limpiar_base_datos() -> Tuple[bool, str]:
    """
    Limpia todos los datos de las tablas principales de la base de datos.
    ADVERTENCIA: Esta acción es IRREVERSIBLE.
    
    Limpia las siguientes tablas:
    - requisiciones: Todos los datos de requisiciones
    - historial_cambios: Todo el historial de auditoría
    - log_eliminaciones: Registro de eliminaciones
    - cargas_diarias: Historial de cargas
    
    NO limpia:
    - configuracion: Configuraciones del sistema
    
    Returns:
        Tuple[bool, str]: (éxito, mensaje)
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Deshabilitar foreign keys temporalmente
            cursor.execute("PRAGMA foreign_keys = OFF")
            
            # Contar registros antes de limpiar
            cursor.execute("SELECT COUNT(*) FROM requisiciones")
            count_requisiciones = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM historial_cambios")
            count_historial = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM log_eliminaciones")
            count_eliminaciones = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM cargas_diarias")
            count_cargas = cursor.fetchone()[0]
            
            # Limpiar todas las tablas
            cursor.execute("DELETE FROM requisiciones")
            cursor.execute("DELETE FROM historial_cambios")
            cursor.execute("DELETE FROM log_eliminaciones")
            cursor.execute("DELETE FROM cargas_diarias")
            
            # Resetear autoincrement
            cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('requisiciones', 'historial_cambios', 'log_eliminaciones', 'cargas_diarias')")
            
            # Reactivar foreign keys
            cursor.execute("PRAGMA foreign_keys = ON")
            
            # Hacer commit explícito
            conn.commit()
            
            mensaje = f"""
            ✅ Base de datos limpiada exitosamente
            
            Registros eliminados:
            - Requisiciones: {count_requisiciones}
            - Historial de cambios: {count_historial}
            - Log de eliminaciones: {count_eliminaciones}
            - Cargas diarias: {count_cargas}
            
            Total: {count_requisiciones + count_historial + count_eliminaciones + count_cargas} registros
            """
            
            return True, mensaje
            
    except Exception as e:
        return False, f"❌ Error al limpiar base de datos: {str(e)}"


def limpiar_cubo_requisiciones() -> Tuple[bool, str]:
    """
    Limpia únicamente los datos del cubo de requisiciones.
    ADVERTENCIA: Esta acción es IRREVERSIBLE.
    
    Limpia:
    - requisiciones: Todos los datos de requisiciones
    - historial_cambios: Historial relacionado
    - log_eliminaciones: Registros relacionados
    - cargas_diarias: Historial de cargas
    
    Returns:
        Tuple[bool, str]: (éxito, mensaje)
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("PRAGMA foreign_keys = OFF")
            
            # Contar registros antes
            cursor.execute("SELECT COUNT(*) FROM requisiciones")
            count = cursor.fetchone()[0]
            
            # Limpiar tablas relacionadas
            cursor.execute("DELETE FROM requisiciones")
            cursor.execute("DELETE FROM historial_cambios")
            cursor.execute("DELETE FROM log_eliminaciones")
            cursor.execute("DELETE FROM cargas_diarias")
            
            # Resetear autoincrement
            cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('requisiciones', 'historial_cambios', 'log_eliminaciones', 'cargas_diarias')")
            
            cursor.execute("PRAGMA foreign_keys = ON")
            conn.commit()
            
            return True, f"✅ Cubo de Requisiciones limpiado: {count} registros eliminados"
            
    except Exception as e:
        return False, f"❌ Error al limpiar cubo de requisiciones: {str(e)}"


def limpiar_cubo_compras() -> Tuple[bool, str]:
    """
    Limpia únicamente los datos del cubo de compras.
    ADVERTENCIA: Esta acción es IRREVERSIBLE.
    
    Limpia:
    - compras: Todos los datos de órdenes de compra
    
    Returns:
        Tuple[bool, str]: (éxito, mensaje)
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar si la tabla existe
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='compras'")
            if not cursor.fetchone():
                return False, "⚠️ La tabla de compras no existe aún"
            
            cursor.execute("PRAGMA foreign_keys = OFF")
            
            # Contar registros antes
            cursor.execute("SELECT COUNT(*) FROM compras")
            count = cursor.fetchone()[0]
            
            # Limpiar tabla
            cursor.execute("DELETE FROM compras")
            
            # Resetear autoincrement
            cursor.execute("DELETE FROM sqlite_sequence WHERE name = 'compras'")
            
            cursor.execute("PRAGMA foreign_keys = ON")
            conn.commit()
            
            return True, f"✅ Cubo de Compras limpiado: {count} registros eliminados"
            
    except Exception as e:
        return False, f"❌ Error al limpiar cubo de compras: {str(e)}"


def limpiar_cubo_gestion() -> Tuple[bool, str]:
    """
    Limpia únicamente los datos del cubo de gestión.
    ADVERTENCIA: Esta acción es IRREVERSIBLE.
    
    Limpia:
    - gestion: Todos los datos de gestión de compras
    
    Returns:
        Tuple[bool, str]: (éxito, mensaje)
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar si la tabla existe
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='gestion'")
            if not cursor.fetchone():
                return False, "⚠️ La tabla de gestión no existe aún"
            
            cursor.execute("PRAGMA foreign_keys = OFF")
            
            # Contar registros antes
            cursor.execute("SELECT COUNT(*) FROM gestion")
            count = cursor.fetchone()[0]
            
            # Limpiar tabla
            cursor.execute("DELETE FROM gestion")
            
            # Resetear autoincrement
            cursor.execute("DELETE FROM sqlite_sequence WHERE name = 'gestion'")
            
            cursor.execute("PRAGMA foreign_keys = ON")
            conn.commit()
            
            return True, f"✅ Cubo de Gestión limpiado: {count} registros eliminados"
            
    except Exception as e:
        return False, f"❌ Error al limpiar cubo de gestión: {str(e)}"


def actualizar_requisiciones_desde_compras() -> Tuple[bool, str, int]:
    """
    Actualiza la tabla de requisiciones con datos de la última OC de cada producto
    desde la tabla de seguimiento OC (compras).
    
    Para cada código de producto en requisiciones:
    - Busca el registro más reciente en la tabla compras (por fecha_oc DESC)
    - Actualiza: proveedor, fecha_oc, estado_oc
    - Solo actualiza si encuentra datos en compras para ese producto
    
    Returns:
        Tuple[bool, str, int]: (éxito, mensaje, cantidad_actualizados)
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar que existan ambas tablas
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN ('requisiciones', 'compras')
            """)
            tablas_existentes = {row[0] for row in cursor.fetchall()}
            
            if 'requisiciones' not in tablas_existentes:
                return False, "⚠️ La tabla de requisiciones no existe", 0
            
            if 'compras' not in tablas_existentes:
                return False, "⚠️ La tabla de compras no existe. Carga primero el cubo de compras.", 0
            
            # Contar productos que tienen datos en compras
            cursor.execute("""
                SELECT COUNT(DISTINCT r.codprod)
                FROM requisiciones r
                INNER JOIN compras c ON r.codprod = c.codprod
            """)
            productos_con_datos = cursor.fetchone()[0]
            
            if productos_con_datos == 0:
                return False, "ℹ️ No hay productos en común entre requisiciones y compras", 0
            
            # Actualizar requisiciones con datos del registro más reciente de cada producto
            # Usamos una subconsulta para obtener el registro más reciente por producto
            cursor.execute("""
                UPDATE requisiciones
                SET 
                    proveedor = (
                        SELECT c.proveedor
                        FROM compras c
                        WHERE c.codprod = requisiciones.codprod
                        ORDER BY 
                            CASE WHEN c.fecha_oc IS NOT NULL THEN c.fecha_oc ELSE '1900-01-01' END DESC,
                            c.id DESC
                        LIMIT 1
                    ),
                    fecha_oc = (
                        SELECT c.fecha_oc
                        FROM compras c
                        WHERE c.codprod = requisiciones.codprod
                        ORDER BY 
                            CASE WHEN c.fecha_oc IS NOT NULL THEN c.fecha_oc ELSE '1900-01-01' END DESC,
                            c.id DESC
                        LIMIT 1
                    ),
                    estado_oc = (
                        SELECT c.estado_linea
                        FROM compras c
                        WHERE c.codprod = requisiciones.codprod
                        ORDER BY 
                            CASE WHEN c.fecha_oc IS NOT NULL THEN c.fecha_oc ELSE '1900-01-01' END DESC,
                            c.id DESC
                        LIMIT 1
                    ),
                    oc = (
                        SELECT c.num_oc
                        FROM compras c
                        WHERE c.codprod = requisiciones.codprod
                        ORDER BY 
                            CASE WHEN c.fecha_oc IS NOT NULL THEN c.fecha_oc ELSE '1900-01-01' END DESC,
                            c.id DESC
                        LIMIT 1
                    )
                WHERE EXISTS (
                    SELECT 1 FROM compras c 
                    WHERE c.codprod = requisiciones.codprod
                )
            """)
            
            registros_actualizados = cursor.rowcount
            conn.commit()
            
            mensaje = f"""✅ Actualización completada exitosamente

📊 **Resultados:**
- {registros_actualizados} requisiciones actualizadas
- {productos_con_datos} productos con datos de compras

**Campos actualizados:**
- ✓ Proveedor (último de cada producto)
- ✓ N° OC (más reciente)
- ✓ Fecha OC (más reciente)
- ✓ Estado OC (más reciente)
"""
            
            return True, mensaje, registros_actualizados
            
    except Exception as e:
        return False, f"❌ Error al actualizar requisiciones: {str(e)}", 0


# ============================================================================
# INICIALIZACIÓN AUTOMÁTICA
# ============================================================================

# Crear base de datos al importar el módulo
try:
    inicializar_base_datos()
except Exception as e:
    pass  # Silencioso - los errores se manejan en la interfaz
