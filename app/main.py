"""
Aplicación principal - Sistema de Gestión de Requisiciones
KS Seguridad Industrial - Sucursal Talca
Autor: Cristian Salas
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os

# Importar módulos del proyecto
from app import config
from app import database as db
from app import utils
from app.cache import get_table, invalidar_cache
from app.services import compras_service
from app.modules.analisis_stock import view as analisis_stock_view


# ============================================================================
# INICIALIZACIÓN DEL SISTEMA
# ============================================================================

# Crear carpetas necesarias
os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
os.makedirs(config.BACKUP_PATH, exist_ok=True)
os.makedirs(config.EXPORT_PATH, exist_ok=True)
os.makedirs(config.LOG_PATH, exist_ok=True)

# Inicializar base de datos (crea tablas si no existen)
try:
    db.inicializar_base_datos()
except Exception as e:
    st.error(f"Error al inicializar base de datos: {str(e)}")

# Ejecutar migración (agrega campos nuevos si es BD existente)
try:
    db.migrar_base_datos_existente()
except Exception as e:
    st.warning(f"Advertencia durante migración: {str(e)}")


# ============================================================================
# CONFIGURACIÓN DE PÁGINA
# ============================================================================

st.set_page_config(**config.PAGE_CONFIG)


# ============================================================================
# INICIALIZACIÓN DE SESSION STATE
# ============================================================================


def inicializar_session_state():
    """Inicializa variables de sesión de Streamlit."""
    if "cubo_requisiciones" not in st.session_state:
        st.session_state.cubo_requisiciones = db.cargar_cubo_raw("requisiciones")

    if "cubo_compras" not in st.session_state:
        st.session_state.cubo_compras = db.cargar_cubo_raw("compras")

    if "cubo_ventas" not in st.session_state:
        st.session_state.cubo_ventas = db.cargar_cubo_raw("ventas")

    if "cubo_inventario" not in st.session_state:
        st.session_state.cubo_inventario = db.cargar_cubo_raw("inventario")

    if "pagina_actual" not in st.session_state:
        st.session_state.pagina_actual = "📊 Dashboard"

    if "datos_cargados" not in st.session_state:
        st.session_state.datos_cargados = False


inicializar_session_state()


# ============================================================================
# SIDEBAR - NAVEGACIÓN
# ============================================================================


def crear_sidebar():
    """Crea el sidebar con navegación y información del usuario."""
    with st.sidebar:
        st.title(config.APP_TITLE)
        st.divider()

        # Información del usuario
        st.markdown(f"**👤 Usuario:** {config.USUARIO_ACTUAL}")
        st.markdown(f"**🏢 Sucursal:** {config.SUCURSAL_ASIGNADA}")
        st.markdown(f"**📅 Fecha:** {datetime.now().strftime('%A, %d %B %Y')}")

        st.divider()

        # Menú de navegación
        st.markdown("### 📋 Navegación")

        for opcion in config.MENU_OPTIONS:
            if st.button(opcion, width="stretch"):
                st.session_state.pagina_actual = opcion
                st.rerun()

        st.divider()

        # Indicadores de cubos cargados
        st.markdown("### 📦 Estado de Cubos")

        estado_cubos = [
            ("Requisiciones", st.session_state.cubo_requisiciones),
            ("Compras", st.session_state.cubo_compras),
            ("Ventas", st.session_state.cubo_ventas),
            ("Inventario", st.session_state.cubo_inventario),
        ]

        for nombre, cubo in estado_cubos:
            if cubo is not None and not cubo.empty:
                st.success(f"✅ {nombre}")
            else:
                st.warning(f"⚠️ {nombre}")


# ============================================================================
# PÁGINA: CARGA DE CUBOS
# ============================================================================


def cargar_cubo_excel(archivo, tipo_cubo: str, key_prefix: str = ""):
    """
    Carga y valida un cubo Excel con selector de hojas.

    Args:
        archivo: Archivo subido por st.file_uploader
        tipo_cubo: Tipo de cubo ('requisiciones', 'compras', 'ventas', 'inventario')
        key_prefix: Prefijo único para widgets de Streamlit

    Returns:
        pd.DataFrame: DataFrame cargado o None si hay error
    """
    # Cargar Excel con selector de hojas
    df = utils.cargar_excel_con_selector_hoja(archivo, tipo_cubo, key_prefix)

    if df is None:
        return None

    # Validar según tipo de cubo
    validaciones = {
        "requisiciones": utils.validar_cubo_requisiciones,
        "compras": utils.validar_cubo_compras,
        "ventas": utils.validar_cubo_ventas,
        "inventario": utils.validar_cubo_inventario,
    }

    validador = validaciones.get(tipo_cubo)
    if validador:
        es_valido, mensaje, columnas_faltantes = validador(df)

        if es_valido and not columnas_faltantes:
            # Todo perfecto
            st.success(mensaje)
        elif es_valido and columnas_faltantes:
            # Válido pero con columnas opcionales faltantes
            st.success(mensaje)
            with st.expander("📋 Columnas opcionales faltantes", expanded=False):
                st.warning(
                    f"Las siguientes {len(columnas_faltantes)} columnas no están presentes:"
                )
                for col in columnas_faltantes[:10]:  # Mostrar máximo 10
                    st.write(f"• {col}")
                if len(columnas_faltantes) > 10:
                    st.write(f"... y {len(columnas_faltantes) - 10} más")
                st.info(
                    "ℹ️ El cubo es funcional, pero algunas características pueden estar limitadas."
                )
        else:
            # Error crítico
            st.error(mensaje)
            with st.expander("❌ Columnas críticas faltantes", expanded=True):
                st.error("El cubo no se puede usar sin estas columnas:")
                for col in columnas_faltantes:
                    st.write(f"• **{col}**")
                st.warning("Por favor, verifica que el archivo Excel sea el correcto.")
            return None

        return df

    return df


def _contar_registros_db(tabla: str) -> int:
    """Consulta conteo real de registros en la tabla, cacheado 30 segundos."""
    return _contar_registros_db_cached(tabla)


@st.cache_data(ttl=30)
def _contar_registros_db_cached(tabla: str) -> int:
    """Implementación cacheada del conteo de registros."""
    try:
        import sqlite3

        conn = sqlite3.connect(config.DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (tabla,)
        )
        if cursor.fetchone() is None:
            conn.close()
            return 0
        cursor.execute(f"SELECT COUNT(*) FROM {tabla}")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except Exception:
        return 0


def _widget_cubo_uploader(
    tipo,
    subheader,
    uploader_key,
    uploader_help,
    session_key,
    spinner_msg,
    warning_msg,
    info_msg_prefix,
    excel_key_prefix,
    post_save_fn=None,
):
    """Widget reutilizable para cargar un cubo Excel.

    Muestra el file_uploader, verifica el hash del archivo, carga desde SQLite
    si no hay cambios, o guarda y llama a ``post_save_fn(df)`` si el archivo es nuevo.

    ``post_save_fn`` recibe el DataFrame cargado y debe devolver
    ``(insertadas, errores, mensajes)`` cuando se utiliza (p. ej. Requisiciones).
    Para los demás cubos se omite y el éxito se reporta directamente.
    """
    st.subheader(subheader)
    archivo = st.file_uploader(
        "Selecciona el archivo",
        type=["xlsx", "xls", "xlsb"],
        key=uploader_key,
        help=uploader_help,
    )

    # Indicador de estado persistido
    if getattr(st.session_state, session_key) is not None and archivo is None:
        _count = _contar_registros_db(tipo)
        if _count == 0:
            setattr(st.session_state, session_key, None)
            st.warning(warning_msg)
        else:
            st.info(
                f"🗄️ {info_msg_prefix} cargados desde base de datos ({_count} registros). Sube un nuevo archivo para actualizar."
            )

    if archivo:
        hash_nuevo = db.calcular_hash_archivo(archivo)
        hash_guardado = db.obtener_configuracion(f"hash_cubo_{tipo}")

        def _guardar_y_notificar(df, es_nuevo):
            insertadas = errores = 0
            mensajes = []
            with st.spinner(spinner_msg):
                db.guardar_cubo_raw(tipo, df, hash_nuevo)
                if post_save_fn is not None:
                    insertadas, errores, mensajes = post_save_fn(df)
            if post_save_fn is not None:
                if insertadas > 0:
                    label = "cargadas" if es_nuevo else "cargadas — cubo actualizado"
                    st.success(f"✅ {insertadas} {info_msg_prefix.lower()} {label}")
                if errores > 0:
                    with st.expander(f"⚠️ {errores} errores durante la carga"):
                        for msg in mensajes[:10]:
                            st.warning(msg)
                        if len(mensajes) > 10:
                            st.info(f"... y {len(mensajes) - 10} errores más")
            else:
                verb = "guardados" if es_nuevo else "actualizados y guardados"
                st.success(
                    f"✅ {info_msg_prefix} {verb} en base de datos ({len(df)} registros)"
                )

        if hash_nuevo == hash_guardado:
            df_sqlite = db.cargar_cubo_raw(tipo)
            if df_sqlite is not None:
                setattr(st.session_state, session_key, df_sqlite)
                st.info(
                    f"ℹ️ Archivo sin cambios — datos cargados desde base de datos ({len(df_sqlite)} registros)"
                )
            else:
                df = cargar_cubo_excel(archivo, tipo, excel_key_prefix)
                if df is not None:
                    setattr(st.session_state, session_key, df)
                    _guardar_y_notificar(df, es_nuevo=True)
        else:
            df = cargar_cubo_excel(archivo, tipo, excel_key_prefix)
            if df is not None:
                setattr(st.session_state, session_key, df)
                _guardar_y_notificar(df, es_nuevo=False)

    return archivo


def seccion_carga_cubos():
    """Sección para cargar los 4 cubos Excel."""
    st.header("📥 Cargar Cubos Excel")
    st.markdown("Carga los archivos Excel exportados desde Power Query.")

    col1, col2 = st.columns(2)

    with col1:
        _widget_cubo_uploader(
            tipo="requisiciones",
            subheader="📋 Cubo de Requisiciones",
            uploader_key="upload_req",
            uploader_help="Cubo con requisiciones y stock por bodega",
            session_key="cubo_requisiciones",
            spinner_msg="Guardando requisiciones en base de datos...",
            warning_msg="No hay requisiciones cargadas. Sube un archivo para iniciar.",
            info_msg_prefix="Requisiciones",
            excel_key_prefix="req",
            post_save_fn=db.cargar_requisiciones_desde_cubo,
        )

        st.markdown("---")

        _widget_cubo_uploader(
            tipo="ventas",
            subheader="📊 Cubo de Ventas",
            uploader_key="upload_ventas",
            uploader_help="Cubo con histórico de ventas mensuales",
            session_key="cubo_ventas",
            spinner_msg="Guardando ventas en base de datos...",
            warning_msg="No hay ventas cargadas. Sube un archivo para iniciar.",
            info_msg_prefix="Ventas",
            excel_key_prefix="ventas",
        )

    with col2:
        archivo_compras = _widget_cubo_uploader(
            tipo="compras",
            subheader="🛒 Cubo de Compras",
            uploader_key="upload_compras",
            uploader_help="Cubo con órdenes de compra",
            session_key="cubo_compras",
            spinner_msg="Guardando compras en base de datos...",
            warning_msg="No hay compras cargadas. Sube un archivo para iniciar.",
            info_msg_prefix="Compras",
            excel_key_prefix="compras",
        )

        df = st.session_state.cubo_compras
        if df is not None:
            # Diagnóstico de fechas
            with st.expander("🔍 Diagnóstico de Columnas de Fecha", expanded=False):
                st.markdown("**Verificación de columnas FechaOC y FechaRecepcion:**")

                # Verificar FechaOC
                if "FechaOC" in df.columns:
                    st.write(f"**FechaOC:**")
                    st.write(f"- Tipo de dato: `{df['FechaOC'].dtype}`")
                    st.write(
                        f"- Valores no nulos: {df['FechaOC'].notna().sum()}/{len(df)}"
                    )
                    st.write(f"- Primeros 3 valores:")
                    st.code(df["FechaOC"].head(3).tolist())

                    # Verificar si son números (seriales de Excel)
                    if pd.api.types.is_numeric_dtype(df["FechaOC"]):
                        st.warning(
                            "⚠️ FechaOC está como número (serial de Excel). Se convertirá al cargar."
                        )
                        # Mostrar ejemplo de conversión
                        ejemplo_serial = (
                            df["FechaOC"].dropna().iloc[0]
                            if len(df["FechaOC"].dropna()) > 0
                            else None
                        )
                        if ejemplo_serial:
                            try:
                                fecha_convertida = pd.to_datetime(
                                    ejemplo_serial, unit="D", origin="1899-12-30"
                                )
                                st.info(
                                    f"Ejemplo: {ejemplo_serial} → {fecha_convertida.strftime('%Y-%m-%d')}"
                                )
                            except:
                                st.error("No se pudo convertir el valor de ejemplo")
                    else:
                        st.success("✓ FechaOC está como texto/fecha")
                else:
                    st.error("❌ No se encontró la columna 'FechaOC'")

                st.markdown("---")

                # Verificar FechaRecepcion (opcional)
                if "FechaRecepcion" in df.columns:
                    st.write(f"**FechaRecepcion:**")
                    st.write(f"- Tipo de dato: `{df['FechaRecepcion'].dtype}`")
                    st.write(
                        f"- Valores no nulos: {df['FechaRecepcion'].notna().sum()}/{len(df)}"
                    )
                    if pd.api.types.is_numeric_dtype(df["FechaRecepcion"]):
                        st.warning(
                            "⚠️ FechaRecepcion está como número (serial de Excel). Se convertirá al cargar."
                        )

            # Botón para insertar en base de datos (idempotente)
            if st.button(
                "💾 Cargar a Base de Datos",
                key="btn_cargar_compras",
                type="primary",
            ):
                with st.spinner("Preparando base de datos..."):
                    try:
                        # Crear tabla si no existe y ejecutar migraciones
                        compras_service.crear_tabla_compras()

                        with st.spinner("Insertando datos en base de datos..."):
                            # Cargar datos de forma idempotente con UPSERT
                            with compras_service.get_db_connection() as conn:
                                insertados, actualizados, sin_cambios, errores = (
                                    compras_service.cargar_compras_desde_dataframe(
                                        st.session_state.cubo_compras, conn
                                    )
                                )

                            # Mostrar resultados
                            col_ins, col_act, col_sin = st.columns(3)
                            with col_ins:
                                st.metric(
                                    "📥 Insertados",
                                    insertados,
                                    help="Registros nuevos insertados",
                                )
                            with col_act:
                                st.metric(
                                    "🔄 Actualizados",
                                    actualizados,
                                    help="Registros existentes actualizados",
                                )
                            with col_sin:
                                st.metric(
                                    "✓ Sin cambios",
                                    sin_cambios,
                                    help="Registros que ya existían sin diferencias",
                                )

                            if errores:
                                with st.expander(
                                    f"⚠️ Errores ({len(errores)})", expanded=False
                                ):
                                    for error in errores[
                                        :10
                                    ]:  # Mostrar máximo 10 errores
                                        st.error(error)
                                    if len(errores) > 10:
                                        st.warning(
                                            f"... y {len(errores) - 10} errores más"
                                        )
                            else:
                                st.success("🎉 Carga completada sin errores")

                            # Actualizar automáticamente las requisiciones con datos de compras
                            st.info(
                                "🔄 Actualizando requisiciones con datos de compras..."
                            )
                            with st.spinner(
                                "Sincronizando requisiciones con seguimiento OC..."
                            ):
                                exito_sync, mensaje_sync, actualizados_sync = (
                                    db.actualizar_requisiciones_desde_compras()
                                )

                                if exito_sync:
                                    st.success(
                                        f"✅ {actualizados_sync} requisiciones actualizadas con datos de compras"
                                    )
                                else:
                                    # Si falla pero no es crítico, mostrar como info
                                    if "no existe" in mensaje_sync.lower():
                                        st.info(mensaje_sync)
                                    else:
                                        st.warning(mensaje_sync)

                    except Exception as e:
                        st.error(f"❌ Error al cargar datos: {str(e)}")

            st.info(
                "💡 **Carga Idempotente con UPSERT**: Puedes cargar el mismo cubo múltiples veces. Los registros nuevos se insertarán, los existentes se actualizarán si hay cambios, o se mantendrán sin cambios si son idénticos."
            )

        st.markdown("---")

        _widget_cubo_uploader(
            tipo="inventario",
            subheader="📦 Cubo de Inventario",
            uploader_key="upload_inventario",
            uploader_help="Cubo con stock por bodega",
            session_key="cubo_inventario",
            spinner_msg="Guardando inventario en base de datos...",
            warning_msg="No hay inventario cargado. Sube un archivo para iniciar.",
            info_msg_prefix="Inventario",
            excel_key_prefix="inventario",
        )

    # Actualizar estado de carga
    cubos_cargados = [
        st.session_state.cubo_requisiciones,
        st.session_state.cubo_compras,
        st.session_state.cubo_inventario,
    ]

    st.session_state.datos_cargados = all(c is not None for c in cubos_cargados)


# ============================================================================
# PÁGINA: DASHBOARD
# ============================================================================


def pagina_dashboard():
    """Página principal con KPIs y gráficos."""
    st.title("📊 Dashboard - Gestión de Requisiciones")

    # Sección de carga de cubos
    seccion_carga_cubos()

    st.markdown("---")

    # Si no hay datos, mostrar mensaje
    if not st.session_state.datos_cargados:
        st.info("ℹ️ Carga los cubos Excel para ver el dashboard completo")

        # Mostrar datos dummy/simulados
        st.subheader("📈 Vista Previa (Datos Simulados)")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("REQ Pendientes", "15", "+3")
        with col2:
            st.metric("OC en Tránsito", "8", "-2")
        with col3:
            st.metric("Productos Críticos", "23", "+5")
        with col4:
            st.metric("Valor Total OC", "$12.5M", "+8%")

        return

    # KPIs principales
    st.subheader("📊 Indicadores Principales")

    stats = db.obtener_estadisticas_generales()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "REQ Pendientes",
            stats["req_pendientes"],
            help="Requisiciones con saldo pendiente > 0",
        )

    with col2:
        st.metric(
            "OC en Tránsito",
            stats["oc_transito"],
            help="OC en estado: En Tránsito, Guía de Despacho o Recepción Parcial",
        )

    with col3:
        st.metric(
            "Productos Pendientes",
            stats["productos_pendientes"],
            help="Productos únicos con requisiciones pendientes",
        )

    with col4:
        valor_formateado = utils.formatear_numero(
            stats["valor_total_oc"], simbolo_moneda="$"
        )
        st.metric(
            "Valor Total OC",
            valor_formateado,
            help="Valor total de órdenes de compra activas",
        )

    st.markdown("---")

    # Gráficos
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("📊 Requisiciones por Estado")

        df_estados = db.obtener_distribucion_estados()

        if not df_estados.empty:
            fig = px.pie(
                df_estados,
                values="cantidad",
                names="estado_oc",
                color="estado_oc",
                color_discrete_map=config.COLORES_ESTADO,
                hole=0.4,
            )
            fig.update_traces(textposition="inside", textinfo="percent+label")
            fig.update_layout(showlegend=True, height=400)
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("No hay datos de requisiciones aún")

    with col_right:
        st.subheader("🏆 Top 10 Productos Solicitados")

        df_productos = db.obtener_productos_mas_solicitados(10)

        if not df_productos.empty:
            fig = px.bar(
                df_productos,
                x="cantidad_total",
                y="codprod",
                orientation="h",
                color="cantidad_total",
                color_continuous_scale="Blues",
                labels={"cantidad_total": "Cantidad", "codprod": "Producto"},
            )
            fig.update_layout(showlegend=False, height=400)
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("No hay datos de productos aún")

    st.markdown("---")

    # Tabla de productos críticos
    if st.session_state.cubo_inventario is not None:
        st.subheader("⚠️ Productos con Stock Crítico")

        df_criticos = utils.obtener_productos_criticos(st.session_state.cubo_inventario)

        if not df_criticos.empty:
            st.dataframe(
                df_criticos,
                width="stretch",
                column_config={
                    "CodProd": "Código Producto",
                    "KS TALCA": "Stock Talca",
                    "Total general": "Stock Total",
                    "CostoUnitario": st.column_config.NumberColumn(
                        "Costo Unitario", format="$%d"
                    ),
                },
            )
        else:
            st.success("✅ No hay productos con stock crítico")


# ============================================================================
# PÁGINA: GESTIÓN REQUISICIONES
# ============================================================================


def pagina_gestion_requisiciones():
    """Página para listar y filtrar requisiciones."""
    st.title("📋 Gestión de Requisiciones")

    # Mensaje informativo
    st.info(
        "💡 Las requisiciones se cargan automáticamente al importar el cubo de requisiciones en el Dashboard"
    )

    # Panel de herramientas
    with st.expander("🔧 Herramientas", expanded=False):
        st.markdown("""
        ### 🔄 Actualizar desde Cubo de Compras
        
        Esta acción busca automáticamente en la tabla de **Seguimiento OC** los datos más recientes 
        de cada producto y los actualiza en las requisiciones:
        
        - **Proveedor**: Último proveedor registrado para el producto
        - **N° OC**: Número de orden de compra más reciente
        - **Fecha OC**: Fecha de emisión de la OC más reciente  
        - **Estado OC**: Estado actual de la OC
        
        💡 Útil después de cargar o actualizar el cubo de compras.
        """)

        col_btn, col_space = st.columns([1, 3])

        with col_btn:
            if st.button(
                "🔄 Actualizar desde Compras", type="primary", use_container_width=True
            ):
                with st.spinner("Actualizando requisiciones desde compras..."):
                    exito, mensaje, actualizados = (
                        db.actualizar_requisiciones_desde_compras()
                    )

                    if exito:
                        st.success(mensaje)
                        st.balloons()
                        # Forzar recarga de datos
                        st.session_state.reload_req_data = True
                        st.rerun()
                    else:
                        st.warning(mensaje)

    st.markdown("---")

    # Mostrar directamente el listado
    tabla_listado_requisiciones()


def tabla_listado_requisiciones():
    """Tabla EDITABLE con listado de requisiciones y filtros."""
    st.subheader("📋 Listado de Requisiciones (Editable)")

    # Inicializar filtros en session_state si no existen
    if "filtro_req_estado" not in st.session_state:
        st.session_state.filtro_req_estado = []
    if "filtro_req_fecha_desde" not in st.session_state:
        st.session_state.filtro_req_fecha_desde = None
    if "filtro_req_fecha_hasta" not in st.session_state:
        st.session_state.filtro_req_fecha_hasta = None
    if "filtro_req_solo_pendientes" not in st.session_state:
        st.session_state.filtro_req_solo_pendientes = False
    if "filtro_req_numreq" not in st.session_state:
        st.session_state.filtro_req_numreq = ""
    if "filtro_req_codprod" not in st.session_state:
        st.session_state.filtro_req_codprod = ""

    # Filtros
    with st.expander("🔍 Filtros", expanded=False):
        st.caption(
            "💡 Los filtros de fecha aplican sobre la **Fecha de Requisición** (FEmision del cubo)"
        )

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            filtro_estado = st.multiselect(
                "Estado",
                options=config.ESTADOS_OC,
                default=st.session_state.filtro_req_estado,
                key="multi_estado_req",
            )
            st.session_state.filtro_req_estado = filtro_estado

        with col2:
            filtro_fecha_desde = st.date_input(
                "Fecha REQ Desde",
                value=st.session_state.filtro_req_fecha_desde,
                key="date_desde_req",
            )
            st.session_state.filtro_req_fecha_desde = filtro_fecha_desde

        with col3:
            filtro_fecha_hasta = st.date_input(
                "Fecha REQ Hasta",
                value=st.session_state.filtro_req_fecha_hasta,
                key="date_hasta_req",
            )
            st.session_state.filtro_req_fecha_hasta = filtro_fecha_hasta

        with col4:
            filtro_solo_pendientes = st.checkbox(
                "Solo Pendientes",
                value=st.session_state.filtro_req_solo_pendientes,
                key="chk_pendientes_req",
            )
            st.session_state.filtro_req_solo_pendientes = filtro_solo_pendientes

        filtro_numreq = st.text_input(
            "Buscar N° Requisición",
            value=st.session_state.filtro_req_numreq,
            key="txt_numreq",
        )
        st.session_state.filtro_req_numreq = filtro_numreq

        filtro_codprod = st.text_input(
            "Buscar Código Producto",
            value=st.session_state.filtro_req_codprod,
            key="txt_codprod_req",
        )
        st.session_state.filtro_req_codprod = filtro_codprod

        # Botón para limpiar filtros
        if st.button(
            "🔄 Limpiar Filtros", type="secondary", key="btn_limpiar_filtros_req"
        ):
            st.session_state.filtro_req_estado = []
            st.session_state.filtro_req_fecha_desde = None
            st.session_state.filtro_req_fecha_hasta = None
            st.session_state.filtro_req_solo_pendientes = False
            st.session_state.filtro_req_numreq = ""
            st.session_state.filtro_req_codprod = ""
            st.rerun()

    # Construir filtros para consulta
    filtros = {}

    if filtro_estado:
        filtros["estado_oc"] = filtro_estado

    if filtro_fecha_desde:
        filtros["fecha_desde"] = str(filtro_fecha_desde)

    if filtro_fecha_hasta:
        filtros["fecha_hasta"] = str(filtro_fecha_hasta)

    if filtro_solo_pendientes:
        filtros["solo_pendientes"] = True

    if filtro_numreq:
        filtros["numreq"] = filtro_numreq

    if filtro_codprod:
        filtros["codprod"] = filtro_codprod

    # Obtener datos
    df_requisiciones = db.obtener_requisiciones(filtros)

    if df_requisiciones.empty:
        st.info("No se encontraron requisiciones con los filtros aplicados")
        return

    # Preparar DataFrame para edición segura
    df_preparado = utils.preparar_df_para_edicion_segura(df_requisiciones)

    # Guardar estado original en session_state (solo la primera vez o cuando hay recarga)
    if "df_req_original" not in st.session_state or st.session_state.get(
        "reload_req_data", False
    ):
        st.session_state.df_req_original = df_preparado.copy()
        st.session_state.reload_req_data = False

    # Mostrar estadísticas
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Requisiciones", len(df_preparado))
    with col2:
        pendientes = len(df_preparado[df_preparado["saldo_pendiente"] > 0])
        st.metric("Con Saldo Pendiente", pendientes)
    with col3:
        completas = len(df_preparado[df_preparado["estado_oc"] == "Recepción Completa"])
        st.metric("Completas", completas)

    st.markdown("---")

    # Información para el usuario sobre campos editables
    st.info("""
    💡 **Tabla Editable**: Haz doble clic en una celda para editarla
    
    ✅ **Campos editables**: Proveedor, N° OC, N° Guía, Fecha OC, Observaciones, Detalle
    
    🔒 **Campos protegidos**: ID, N° REQ, Código, Cantidad, Estado, Cant. Recibida, Saldo Pendiente
    
    Después de editar, haz clic en "💾 Guardar Cambios"
    """)

    # Obtener configuración de columnas editables
    config_columnas = utils.obtener_config_columnas_editables()

    # TABLA EDITABLE usando st.data_editor
    df_editado = st.data_editor(
        df_preparado,
        column_config=config_columnas,
        num_rows="fixed",  # No permitir agregar/eliminar filas
        use_container_width=True,
        key="editor_requisiciones",
        hide_index=True,
        height=500,
    )

    st.markdown("---")

    # Botones de acción
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

    with col1:
        if st.button("💾 Guardar Cambios", type="primary", use_container_width=True):
            try:
                # Validar ediciones antes de guardar
                es_valido, errores = utils.validar_ediciones_antes_de_guardar(
                    df_editado
                )

                if not es_valido:
                    st.error("⚠️ Hay errores en las ediciones:")
                    for error in errores:
                        st.warning(error)
                    st.stop()

                # Procesar ediciones en batch
                with st.spinner("Guardando cambios en la base de datos..."):
                    resultado = db.procesar_ediciones_batch_ui(
                        st.session_state.df_req_original, df_editado
                    )

                # Mostrar resultados
                if resultado["success"]:
                    st.success(
                        f"✅ {resultado['exitosas']} requisiciones actualizadas correctamente"
                    )

                    if resultado["fallidas"] > 0:
                        st.warning(
                            f"⚠️ {resultado['fallidas']} actualizaciones fallaron"
                        )

                    if resultado["sin_cambios"] > 0:
                        st.info(
                            f"ℹ️ {resultado['sin_cambios']} requisiciones sin cambios"
                        )

                    # Actualizar estado original con los cambios guardados
                    st.session_state.df_req_original = df_editado.copy()

                    # Mostrar detalles
                    if resultado["mensajes"]:
                        with st.expander("📋 Ver detalles de las operaciones"):
                            for mensaje in resultado["mensajes"]:
                                st.text(mensaje)

                    # Recargar página
                    st.balloons()
                    st.rerun()

                else:
                    st.error("❌ No se pudo guardar ningún cambio")

                    # Mostrar mensajes de error
                    if resultado["mensajes"]:
                        with st.expander("⚠️ Ver errores"):
                            for mensaje in resultado["mensajes"]:
                                st.text(mensaje)

            except Exception as e:
                st.error(f"❌ Error inesperado al guardar cambios: {str(e)}")
                st.exception(e)  # Mostrar traceback completo para debugging

    with col2:
        if st.button("🔄 Recargar Datos", use_container_width=True):
            st.session_state.reload_req_data = True
            st.rerun()

    with col3:
        if st.button("❌ Descartar Cambios", use_container_width=True):
            st.session_state.df_req_original = df_preparado.copy()
            st.success("Cambios descartados")
            st.rerun()

    with col4:
        if st.button("📥 Exportar", use_container_width=True):
            try:
                nombre_archivo = utils.generar_nombre_exportacion(
                    "requisiciones", "xlsx"
                )
                ruta_completa = os.path.join(config.EXPORT_PATH, nombre_archivo)

                df_export = utils.preparar_dataframe_para_exportar(df_editado)

                with pd.ExcelWriter(ruta_completa, engine="openpyxl") as writer:
                    df_export.to_excel(writer, sheet_name="Requisiciones", index=False)
                    utils.aplicar_formato_excel(writer, df_export, "Requisiciones")

                st.success(f"✅ Exportado: {nombre_archivo}")

            except Exception as e:
                st.error(f"❌ Error al exportar: {str(e)}")


# ============================================================================
# PÁGINA: SEGUIMIENTO OC
# ============================================================================


def pagina_seguimiento_oc():
    """Página para seguimiento de órdenes de compra."""
    st.title("🛒 Seguimiento de Órdenes de Compra")

    # Inicializar filtros en session_state si no existen
    if "filtro_oc_seleccionada" not in st.session_state:
        st.session_state.filtro_oc_seleccionada = "Todas"
    if "filtro_estado_seleccionado" not in st.session_state:
        st.session_state.filtro_estado_seleccionado = "Todos"
    if "filtro_buscar_producto" not in st.session_state:
        st.session_state.filtro_buscar_producto = ""
    if "filtro_observacion" not in st.session_state:
        st.session_state.filtro_observacion = ""

    # Verificar si existe la tabla de compras
    try:
        # Ejecutar migración para asegurar que desprod existe
        compras_service.migrar_tabla_compras_agregar_desprod()

        with compras_service.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='compras'"
            )
            tabla_existe = cursor.fetchone() is not None

            if not tabla_existe:
                st.warning(
                    "⚠️ La tabla de compras no existe. Carga primero el Cubo de Compras."
                )
                return

            # Obtener estadísticas
            stats = compras_service.obtener_estadisticas_compras(conn)

            # Mostrar estadísticas generales
            st.subheader("📊 Resumen General")
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("📦 Total Líneas", stats["total_registros"])
            with col2:
                st.metric("🛒 OCs Únicas", stats["total_ocs"])
            with col3:
                st.metric("🏷️ Productos", stats["total_productos"])
            with col4:
                st.metric("💰 Valor Total", f"${stats['valor_total']:,.0f}")

            # Mostrar distribución por estado si hay datos
            if stats["por_estado"]:
                st.markdown("---")
                st.subheader("📈 Distribución por Estado")
                cols_estado = st.columns(len(stats["por_estado"]))
                for idx, (estado, cantidad) in enumerate(stats["por_estado"].items()):
                    with cols_estado[idx]:
                        st.metric(estado, cantidad)

            st.markdown("---")

            # Filtros y búsqueda
            st.subheader("🔍 Filtros y Búsqueda")

            col_filtro1, col_filtro2 = st.columns(2)

            with col_filtro1:
                # Obtener lista de OCs para el filtro
                cursor.execute("SELECT DISTINCT num_oc FROM compras ORDER BY num_oc")
                lista_ocs = [row[0] for row in cursor.fetchall()]

                # Encontrar el índice del valor guardado
                index_oc = 0
                if st.session_state.filtro_oc_seleccionada in lista_ocs:
                    index_oc = (
                        lista_ocs.index(st.session_state.filtro_oc_seleccionada) + 1
                    )

                oc_seleccionada = st.selectbox(
                    "Filtrar por OC:",
                    options=["Todas"] + lista_ocs,
                    index=index_oc
                    if st.session_state.filtro_oc_seleccionada != "Todas"
                    else 0,
                    help="Selecciona una OC específica para ver sus detalles",
                    key="select_oc",
                )
                st.session_state.filtro_oc_seleccionada = oc_seleccionada

            with col_filtro2:
                # Filtro por estado
                estados_disponibles = (
                    list(stats["por_estado"].keys()) if stats["por_estado"] else []
                )

                # Encontrar el índice del valor guardado
                index_estado = 0
                if st.session_state.filtro_estado_seleccionado in estados_disponibles:
                    index_estado = (
                        estados_disponibles.index(
                            st.session_state.filtro_estado_seleccionado
                        )
                        + 1
                    )

                estado_seleccionado = st.selectbox(
                    "Filtrar por Estado:",
                    options=["Todos"] + estados_disponibles,
                    index=index_estado
                    if st.session_state.filtro_estado_seleccionado != "Todos"
                    else 0,
                    help="Filtra las líneas por su estado",
                    key="select_estado",
                )
                st.session_state.filtro_estado_seleccionado = estado_seleccionado

            # Filtros de texto en una sola fila
            col_txt1, col_txt2 = st.columns(2)

            with col_txt1:
                # Búsqueda por código de producto
                buscar_producto = st.text_input(
                    "🔎 Buscar por código:",
                    value=st.session_state.filtro_buscar_producto,
                    help="Ingresa el código del producto para buscarlo",
                    key="txt_buscar_producto",
                )
                st.session_state.filtro_buscar_producto = buscar_producto

            with col_txt2:
                # Búsqueda por observación (case-insensitive, null-safe, "comienza con")
                buscar_observacion = st.text_input(
                    "💬 Observación comienza con:",
                    value=st.session_state.filtro_observacion,
                    help="Filtra registros cuya observación comience con este texto (equivalente a LIKE 'texto%')",
                    key="txt_observacion",
                )
                st.session_state.filtro_observacion = buscar_observacion

            # Botón para limpiar filtros
            if st.button("🔄 Limpiar Filtros", type="secondary"):
                st.session_state.filtro_oc_seleccionada = "Todas"
                st.session_state.filtro_estado_seleccionado = "Todos"
                st.session_state.filtro_buscar_producto = ""
                st.session_state.filtro_observacion = ""
                st.rerun()

            st.markdown("---")

            # Construir query con filtros
            query = """
                SELECT 
                    num_oc as 'OC',
                    codprod as 'Código Producto',
                    desprod as 'Nombre Producto',
                    proveedor as 'Proveedor',
                    cantidad_solicitada as 'Cant. Solicitada',
                    cantidad_recibida as 'Cant. Recibida',
                    cantidad_manual as 'Cant. Manual',
                    (cantidad_recibida + cantidad_manual) as 'Total Recibido',
                    (cantidad_solicitada - cantidad_recibida - cantidad_manual) as 'Saldo Pendiente',
                    precio_compra as 'Precio Unit.',
                    total_linea as 'Total Línea',
                    fecha_oc as 'Fecha OC',
                    fecha_recepcion as 'Fecha Recepción',
                    estado_linea as 'Estado',
                    bodega_nombre as 'Bodega',
                    observacion as 'Observación'
                FROM compras
                WHERE 1=1
            """

            params = []

            # Aplicar filtro de OC
            if oc_seleccionada != "Todas":
                query += " AND num_oc = ?"
                params.append(oc_seleccionada)

            # Aplicar filtro de estado
            if estado_seleccionado != "Todos":
                query += " AND estado_linea = ?"
                params.append(estado_seleccionado)

            # Aplicar búsqueda de código de producto
            if buscar_producto:
                query += " AND codprod LIKE ?"
                params.append(f"%{buscar_producto}%")

            query += " ORDER BY num_oc, codprod"

            # Ejecutar query y obtener datos
            df_compras = pd.read_sql_query(query, conn, params=params)

            # Filtro por observación (pandas, case-insensitive, null-safe, "comienza con")
            if buscar_observacion:
                df_compras = df_compras[
                    df_compras["Observación"]
                    .str.lower()
                    .str.startswith(buscar_observacion.lower(), na=False)
                ]

            # Mostrar título de resultados
            st.subheader(f"📋 Detalle de Órdenes de Compra ({len(df_compras)} líneas)")

            if len(df_compras) == 0:
                st.info("No hay registros que coincidan con los filtros seleccionados")
            else:
                # Configurar opciones de visualización
                st.dataframe(
                    df_compras,
                    use_container_width=True,
                    height=400,
                    column_config={
                        "Precio Unit.": st.column_config.NumberColumn(
                            "Precio Unit.", format="$%.2f"
                        ),
                        "Total Línea": st.column_config.NumberColumn(
                            "Total Línea", format="$%.2f"
                        ),
                        "Cant. Solicitada": st.column_config.NumberColumn(
                            "Cant. Solicitada", format="%.2f"
                        ),
                        "Cant. Recibida": st.column_config.NumberColumn(
                            "Cant. Recibida", format="%.2f"
                        ),
                        "Cant. Manual": st.column_config.NumberColumn(
                            "Cant. Manual", format="%.2f"
                        ),
                        "Total Recibido": st.column_config.NumberColumn(
                            "Total Recibido", format="%.2f"
                        ),
                        "Saldo Pendiente": st.column_config.NumberColumn(
                            "Saldo Pendiente", format="%.2f"
                        ),
                    },
                )

                # Resumen de resultados filtrados
                st.markdown("---")
                st.subheader("📊 Resumen de Resultados")
                col_res1, col_res2, col_res3, col_res4 = st.columns(4)

                with col_res1:
                    st.metric("Total Líneas", len(df_compras))
                with col_res2:
                    total_solicitado = df_compras["Cant. Solicitada"].sum()
                    st.metric("Cant. Solicitada Total", f"{total_solicitado:,.2f}")
                with col_res3:
                    total_recibido = df_compras["Total Recibido"].sum()
                    st.metric("Cant. Recibida Total", f"{total_recibido:,.2f}")
                with col_res4:
                    valor_total_filtrado = df_compras["Total Línea"].sum()
                    st.metric("Valor Total Filtrado", f"${valor_total_filtrado:,.0f}")

                # Botón para descargar Excel
                st.markdown("---")
                col_export1, col_export2 = st.columns([3, 1])
                with col_export2:
                    # Convertir a Excel en memoria
                    from io import BytesIO

                    buffer = BytesIO()
                    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                        df_compras.to_excel(writer, index=False, sheet_name="Compras")

                    st.download_button(
                        label="📥 Descargar Excel",
                        data=buffer.getvalue(),
                        file_name=f"seguimiento_oc_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )

    except Exception as e:
        st.error(f"❌ Error al cargar datos: {str(e)}")


# ============================================================================
# PÁGINA: ANÁLISIS STOCK
# ============================================================================


def pagina_analisis_stock():
    """Página para análisis de stock vs ventas — KS Talca."""
    st.title("📈 Análisis de Stock")

    cubos_faltantes = []
    if st.session_state.cubo_inventario is None:
        cubos_faltantes.append("📦 Cubo de Inventario")
    if st.session_state.cubo_ventas is None:
        cubos_faltantes.append("📊 Cubo de Ventas")

    if cubos_faltantes:
        st.warning(
            "⚠️ Para ver este análisis debes cargar los siguientes cubos en el Dashboard:\n\n"
            + "\n".join(f"- {c}" for c in cubos_faltantes)
        )
        return

    analisis_stock_view.render(
        cubo_inventario=st.session_state.cubo_inventario,
        cubo_ventas=st.session_state.cubo_ventas,
    )


# ============================================================================
# PÁGINA: CONFIGURACIÓN
# ============================================================================


def pagina_configuracion():
    """Página de configuración y utilidades."""
    st.title("⚙️ Configuración")

    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "💾 Backup",
            "📊 Información del Sistema",
            "📋 Historial de Cargas",
            "🗑️ Limpiar Datos",
        ]
    )

    with tab1:
        st.subheader("💾 Backup de Base de Datos")

        st.markdown("""
        Crea una copia de seguridad de la base de datos actual.
        El archivo se guardará en la carpeta `backups/`.
        """)

        if st.button("🔒 Crear Backup Ahora", width="stretch"):
            try:
                import shutil

                nombre_backup = utils.generar_nombre_backup()
                ruta_origen = config.DB_PATH
                ruta_destino = os.path.join(config.BACKUP_PATH, nombre_backup)

                # Verificar que existe la carpeta de backups
                os.makedirs(config.BACKUP_PATH, exist_ok=True)

                # Copiar archivo
                shutil.copy2(ruta_origen, ruta_destino)

                st.success(f"{config.MSG_EXITO_BACKUP}: {nombre_backup}")

            except Exception as e:
                st.error(f"{config.MSG_ERROR_BACKUP}: {str(e)}")

        st.markdown("---")

        # Listar backups existentes
        st.subheader("📂 Backups Disponibles")

        try:
            if os.path.exists(config.BACKUP_PATH):
                backups = [
                    f for f in os.listdir(config.BACKUP_PATH) if f.endswith(".db")
                ]

                if backups:
                    backups.sort(reverse=True)

                    for backup in backups[:10]:  # Mostrar últimos 10
                        ruta_backup = os.path.join(config.BACKUP_PATH, backup)
                        tamanio = os.path.getsize(ruta_backup) / 1024  # KB
                        fecha_mod = datetime.fromtimestamp(
                            os.path.getmtime(ruta_backup)
                        )

                        st.text(
                            f"📄 {backup} - {tamanio:.1f} KB - {fecha_mod.strftime('%d/%m/%Y %H:%M')}"
                        )
                else:
                    st.info("No hay backups disponibles")
            else:
                st.info("Carpeta de backups no existe aún")
        except Exception as e:
            st.error(f"Error al listar backups: {str(e)}")

    with tab2:
        st.subheader("📊 Información del Sistema")

        info_sistema = {
            "Usuario": config.USUARIO_ACTUAL,
            "Sucursal": config.SUCURSAL_ASIGNADA,
            "Bodega": config.BODEGA_ASIGNADA,
            "Ruta Base de Datos": config.DB_PATH,
            "Versión Python": "3.9+",
            "Framework": "Streamlit",
        }

        for clave, valor in info_sistema.items():
            st.text(f"{clave}: {valor}")

        st.markdown("---")

        # Estadísticas de la base de datos (usando caché)
        st.subheader("📈 Estadísticas de Datos")

        df_req = get_table("requisiciones")
        stats = db.obtener_estadisticas_generales()

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Requisiciones", len(df_req))
        with col2:
            st.metric("Productos Únicos", stats["productos_pendientes"])
        with col3:
            st.metric("REQ Pendientes", stats["req_pendientes"])
        with col4:
            st.metric("OC en Tránsito", stats["oc_transito"])

    with tab3:
        st.subheader("📋 Historial de Cargas de Datos")

        st.markdown("""
        Registro de auditoría de todas las cargas de datos desde cubos Excel.
        Muestra estadísticas de cada carga: registros leídos, insertados, omitidos y errores.
        """)

        # Mostrar información de la última carga
        ultima_carga = db.obtener_ultima_carga()

        if ultima_carga:
            st.info(f"""
            **📅 Última Carga:** {ultima_carga["fecha_carga"]}  
            ✅ **Insertados:** {ultima_carga["registros_insertados"]} | 
            ⚠️ **Omitidos:** {ultima_carga["registros_omitidos"]} | 
            ❌ **Errores:** {ultima_carga["errores"]}
            """)
        else:
            st.warning("No hay registros de cargas previas")

        st.markdown("---")

        # Tabla con historial completo
        st.subheader("📊 Historial Completo")

        # Selector de límite de registros
        limite = st.selectbox(
            "Cantidad de registros a mostrar", options=[10, 25, 50, 100], index=1
        )

        df_historial = db.obtener_historial_cargas(limite=limite)

        if not df_historial.empty:
            # Formatear columnas para visualización
            df_display = df_historial[
                [
                    "fecha_carga",
                    "registros_leidos",
                    "registros_insertados",
                    "registros_omitidos",
                    "errores",
                    "usuario",
                ]
            ].copy()

            df_display.columns = [
                "Fecha",
                "Leídos",
                "Insertados",
                "Omitidos",
                "Errores",
                "Usuario",
            ]

            # Aplicar formato condicional con colores
            st.dataframe(df_display, use_container_width=True, height=400)

            # Botón para exportar historial
            if st.button("📥 Exportar Historial a Excel"):
                try:
                    nombre_export = f"historial_cargas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                    ruta_export = os.path.join(config.EXPORT_PATH, nombre_export)

                    df_display.to_excel(ruta_export, index=False, engine="openpyxl")

                    st.success(f"✅ Historial exportado: {nombre_export}")
                except Exception as e:
                    st.error(f"Error al exportar: {str(e)}")
        else:
            st.info("No hay historial de cargas disponible")

    with tab4:
        st.subheader("🗑️ Limpiar Base de Datos")

        st.markdown("""
        ### ⚠️ ADVERTENCIA - ACCIÓN IRREVERSIBLE ⚠️
        
        Puedes limpiar cubos individuales o toda la base de datos.
        
        ### 📌 Recomendaciones
        
        ✅ **SIEMPRE** crea un backup ANTES de limpiar  
        ✅ Verifica que tienes los cubos Excel originales para recargar  
        ✅ Asegúrate de que no hay otros usuarios trabajando  
        
        ---
        """)

        # Mostrar estadísticas actuales
        stats = db.obtener_estadisticas_generales()

        st.subheader("📊 Datos Actuales")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Total Requisiciones", stats["req_pendientes"] + stats["oc_transito"]
            )

        with col2:
            st.metric("REQ Pendientes", stats["req_pendientes"])

        with col3:
            st.metric("OC en Tránsito", stats["oc_transito"])

        with col4:
            st.metric("Productos Únicos", stats["productos_pendientes"])

        st.markdown("---")

        # ========== LIMPIAR CUBOS INDIVIDUALES ==========
        st.subheader("🗂️ Limpiar Cubos Individuales")

        col_c1, col_c2, col_c3, col_c4 = st.columns(4)

        # CUBO DE REQUISICIONES
        with col_c1:
            with st.expander("📋 Requisiciones", expanded=False):
                st.markdown("**Elimina:** requisiciones, historial y cargas.")
                confirm_req = st.checkbox("Confirmar limpieza", key="confirm_req")
                if st.button(
                    "🗑️ Limpiar",
                    type="secondary",
                    disabled=not confirm_req,
                    use_container_width=True,
                    key="btn_limpiar_req",
                ):
                    with st.spinner("Limpiando..."):
                        exito, mensaje = db.limpiar_cubo_requisiciones()
                        if exito:
                            st.success(mensaje)
                            st.session_state.pop("cubo_requisiciones", None)
                            for _k in list(st.session_state.keys()):
                                if _k.startswith("df_") or _k.startswith("cube_"):
                                    del st.session_state[_k]
                            invalidar_cache()
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error(mensaje)

        # CUBO DE COMPRAS
        with col_c2:
            with st.expander("🛒 Compras", expanded=False):
                st.markdown("**Elimina:** órdenes de compra y seguimiento OC.")
                confirm_compras = st.checkbox(
                    "Confirmar limpieza", key="confirm_compras"
                )
                if st.button(
                    "🗑️ Limpiar",
                    type="secondary",
                    disabled=not confirm_compras,
                    use_container_width=True,
                    key="btn_limpiar_compras",
                ):
                    with st.spinner("Limpiando..."):
                        exito, mensaje = db.limpiar_cubo_compras()
                        if exito:
                            st.success(mensaje)
                            st.session_state.pop("cubo_compras", None)
                            for _k in list(st.session_state.keys()):
                                if _k.startswith("df_") or _k.startswith("cube_"):
                                    del st.session_state[_k]
                            invalidar_cache()
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error(mensaje)

        # CUBO DE VENTAS
        with col_c3:
            with st.expander("📊 Ventas", expanded=False):
                st.markdown("**Elimina:** datos del cubo de ventas.")
                confirm_ventas = st.checkbox("Confirmar limpieza", key="confirm_ventas")
                if st.button(
                    "🗑️ Limpiar",
                    type="secondary",
                    disabled=not confirm_ventas,
                    use_container_width=True,
                    key="btn_limpiar_ventas",
                ):
                    with st.spinner("Limpiando..."):
                        exito, mensaje = db.limpiar_cubo_ventas()
                        if exito:
                            st.success(mensaje)
                            st.session_state.pop("cubo_ventas", None)
                            for _k in list(st.session_state.keys()):
                                if _k.startswith("df_") or _k.startswith("cube_"):
                                    del st.session_state[_k]
                            invalidar_cache()
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error(mensaje)

        # CUBO DE INVENTARIO
        with col_c4:
            with st.expander("📦 Inventario", expanded=False):
                st.markdown("**Elimina:** datos del cubo de inventario.")
                confirm_inventario = st.checkbox(
                    "Confirmar limpieza", key="confirm_inventario"
                )
                if st.button(
                    "🗑️ Limpiar",
                    type="secondary",
                    disabled=not confirm_inventario,
                    use_container_width=True,
                    key="btn_limpiar_inventario",
                ):
                    with st.spinner("Limpiando..."):
                        exito, mensaje = db.limpiar_cubo_inventario()
                        if exito:
                            st.success(mensaje)
                            st.session_state.pop("cubo_inventario", None)
                            for _k in list(st.session_state.keys()):
                                if _k.startswith("df_") or _k.startswith("cube_"):
                                    del st.session_state[_k]
                            invalidar_cache()
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error(mensaje)

        st.markdown("---")

        # ========== LIMPIAR TODO ==========
        st.subheader("🔐 Limpiar TODA la Base de Datos")

        st.markdown("""
        ### ⚠️ LIMPIEZA COMPLETA
        
        Esta opción eliminará **TODOS** los datos:
        - 📋 Requisiciones y su historial
        - 📦 Compras y órdenes
        - 📊 Gestión y cruces
        - 📝 Auditoría completa
        
        **Úsala solo si quieres empezar completamente desde cero.**
        """)

        # Crear dos columnas: una para el checkbox y otra para el botón
        col_check, col_btn = st.columns([3, 1])

        with col_check:
            confirmacion = st.checkbox(
                "✅ Entiendo que esta acción es IRREVERSIBLE y he creado un backup",
                key="confirmar_limpieza_total",
            )

        with col_btn:
            if st.button(
                "🗑️ LIMPIAR TODO",
                type="primary",
                disabled=not confirmacion,
                use_container_width=True,
            ):
                with st.spinner("Limpiando toda la base de datos..."):
                    exito, mensaje = db.limpiar_base_datos()

                    if exito:
                        st.success(mensaje)
                        st.balloons()

                        # Limpiar session state y caché
                        st.session_state.datos_cargados = False
                        for key in (
                            "cubo_requisiciones",
                            "cubo_compras",
                            "cubo_ventas",
                            "cubo_inventario",
                        ):
                            st.session_state.pop(key, None)
                        for _k in list(st.session_state.keys()):
                            if _k.startswith("df_") or _k.startswith("cube_"):
                                del st.session_state[_k]
                        invalidar_cache()
                        st.cache_data.clear()

                        st.info(
                            "💡 **Próximo paso:** Ve al Dashboard y carga tus cubos de datos"
                        )
                        st.rerun()
                    else:
                        st.error(mensaje)

        if not confirmacion:
            st.warning(
                "⚠️ Marca la casilla de confirmación para habilitar el botón de limpieza total"
            )


# ============================================================================
# ENRUTAMIENTO DE PÁGINAS
# ============================================================================


def main():
    """Función principal que maneja el enrutamiento de páginas."""

    # Crear sidebar
    crear_sidebar()

    # Enrutar a la página correspondiente
    pagina = st.session_state.pagina_actual

    if pagina == "📊 Dashboard":
        pagina_dashboard()

    elif pagina == "📋 Gestión Requisiciones":
        pagina_gestion_requisiciones()

    elif pagina == "🛒 Seguimiento OC":
        pagina_seguimiento_oc()

    elif pagina == "📈 Análisis Stock":
        pagina_analisis_stock()

    elif pagina == "⚙️ Configuración":
        pagina_configuracion()

    else:
        st.error(f"Página no encontrada: {pagina}")


# ============================================================================
# PUNTO DE ENTRADA
# ============================================================================

if __name__ == "__main__":
    main()
