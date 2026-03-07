"""
Ejemplo de implementación de tabla editable segura
Para usar en app.py - Sistema de Gestión de Requisiciones

Autor: Cristian Salas
Fecha: 4 de Febrero de 2026
"""

import streamlit as st
import pandas as pd
from app import database as db
from app import utils
from app import config


def tabla_requisiciones_editable():
    """
    Tabla de requisiciones con edición segura de campos administrativos.
    
    Permite editar: proveedor, oc, n_guia, fecha_oc, observacion, detalle
    Protege: id, numreq, codprod, cantidad, cant_recibida, estado_oc, etc.
    """
    st.subheader("📋 Listado de Requisiciones (Editable)")
    
    # ========================================================================
    # PASO 1: Obtener datos de la base de datos
    # ========================================================================
    
    # Obtener filtros si los hay (opcional)
    with st.expander("🔍 Filtros", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            filtro_estado = st.multiselect(
                "Estado",
                options=config.ESTADOS_OC,
                default=None
            )
        
        with col2:
            filtro_solo_pendientes = st.checkbox("Solo Pendientes", value=False)
    
    # Construir filtros
    filtros = {}
    if filtro_estado:
        filtros['estado_oc'] = filtro_estado
    if filtro_solo_pendientes:
        filtros['solo_pendientes'] = True
    
    # Obtener requisiciones
    df_requisiciones = db.obtener_requisiciones(filtros)
    
    if df_requisiciones.empty:
        st.info("No hay requisiciones para mostrar con los filtros aplicados")
        return
    
    # ========================================================================
    # PASO 2: Preparar DataFrame para edición segura
    # ========================================================================
    
    df_preparado = utils.preparar_df_para_edicion_segura(df_requisiciones)
    
    # Guardar estado original en session_state (solo la primera vez)
    if 'df_req_original' not in st.session_state or st.session_state.get('reload_data', False):
        st.session_state.df_req_original = df_preparado.copy()
        st.session_state.reload_data = False
    
    # ========================================================================
    # PASO 3: Obtener configuración de columnas editables
    # ========================================================================
    
    config_columnas = utils.obtener_config_columnas_editables()
    
    # ========================================================================
    # PASO 4: Mostrar información al usuario
    # ========================================================================
    
    st.info("""
    💡 **Instrucciones**:
    - Haz doble clic en una celda para editarla
    - **Campos editables**: Proveedor, OC, N° Guía, Fecha OC, Observaciones, Detalle
    - **Campos protegidos**: Cantidad, Estado, Saldo Pendiente (no se pueden modificar aquí)
    - Haz clic en "💾 Guardar Cambios" cuando termines de editar
    """)
    
    # Estadísticas
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Requisiciones", len(df_preparado))
    with col2:
        pendientes = len(df_preparado[df_preparado['saldo_pendiente'] > 0])
        st.metric("Con Saldo Pendiente", pendientes)
    with col3:
        completas = len(df_preparado[df_preparado['estado_oc'] == 'Recepción Completa'])
        st.metric("Completas", completas)
    
    st.markdown("---")
    
    # ========================================================================
    # PASO 5: Tabla editable (st.data_editor)
    # ========================================================================
    
    df_editado = st.data_editor(
        df_preparado,
        column_config=config_columnas,
        num_rows="fixed",  # No permitir agregar/eliminar filas
        use_container_width=True,
        key='editor_requisiciones',
        hide_index=True,
        height=600
    )
    
    # ========================================================================
    # PASO 6: Botones de acción
    # ========================================================================
    
    st.markdown("---")
    
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    
    with col1:
        if st.button("💾 Guardar Cambios", type="primary", use_container_width=True):
            
            # Validar ediciones (opcional pero recomendado)
            es_valido, errores = utils.validar_ediciones_antes_de_guardar(df_editado)
            
            if not es_valido:
                st.error("⚠️ Hay errores en las ediciones:")
                for error in errores:
                    st.warning(error)
                st.info("Corrige los errores y vuelve a intentar guardar")
                return
            
            # Procesar ediciones en batch
            with st.spinner("Guardando cambios en la base de datos..."):
                resultado = db.procesar_ediciones_batch_ui(
                    st.session_state.df_req_original, 
                    df_editado
                )
            
            # Mostrar resultados
            if resultado['success']:
                st.success(
                    f"✅ {resultado['exitosas']} requisiciones actualizadas correctamente"
                )
                
                if resultado['fallidas'] > 0:
                    st.warning(
                        f"⚠️ {resultado['fallidas']} actualizaciones fallaron"
                    )
                
                if resultado['sin_cambios'] > 0:
                    st.info(
                        f"ℹ️ {resultado['sin_cambios']} requisiciones sin cambios"
                    )
                
                # Actualizar estado original con los cambios guardados
                st.session_state.df_req_original = df_editado.copy()
                
                # Mostrar detalles
                with st.expander("📋 Ver detalles de las operaciones"):
                    for mensaje in resultado['mensajes']:
                        st.text(mensaje)
                
                # Recargar página para mostrar cambios
                st.balloons()
                st.rerun()
                
            else:
                st.error("❌ No se pudo guardar ningún cambio")
                st.error("Verifica los logs o contacta al administrador")
                
                # Mostrar mensajes de error
                with st.expander("⚠️ Ver errores"):
                    for mensaje in resultado['mensajes']:
                        st.text(mensaje)
    
    with col2:
        if st.button("🔄 Recargar Datos", use_container_width=True):
            st.session_state.reload_data = True
            st.rerun()
    
    with col3:
        if st.button("❌ Descartar Cambios", use_container_width=True):
            st.session_state.df_req_original = df_preparado.copy()
            st.success("Cambios descartados")
            st.rerun()
    
    with col4:
        if st.button("📥 Exportar", use_container_width=True):
            # Exportar a Excel
            try:
                import os
                nombre_archivo = utils.generar_nombre_exportacion("requisiciones", "xlsx")
                ruta_completa = os.path.join(config.EXPORT_PATH, nombre_archivo)
                
                # Preparar DataFrame para exportar
                df_export = utils.preparar_dataframe_para_exportar(df_editado)
                
                with pd.ExcelWriter(ruta_completa, engine='openpyxl') as writer:
                    df_export.to_excel(writer, sheet_name='Requisiciones', index=False)
                    utils.aplicar_formato_excel(writer, df_export, 'Requisiciones')
                
                st.success(f"✅ Exportado: {nombre_archivo}")
                
            except Exception as e:
                st.error(f"❌ Error al exportar: {str(e)}")


# ============================================================================
# EJEMPLO 2: Versión simplificada sin filtros
# ============================================================================

def tabla_requisiciones_editable_simple():
    """
    Versión simplificada de la tabla editable.
    Ideal para páginas donde no se necesitan filtros complejos.
    """
    st.subheader("📋 Requisiciones")
    
    # Obtener y preparar datos
    df = db.obtener_requisiciones()
    
    if df.empty:
        st.info("No hay requisiciones")
        return
    
    df_prep = utils.preparar_df_para_edicion_segura(df)
    
    # Guardar original
    if 'df_orig_simple' not in st.session_state:
        st.session_state.df_orig_simple = df_prep.copy()
    
    # Configuración de columnas
    config_cols = utils.obtener_config_columnas_editables()
    
    # Tabla editable
    df_edit = st.data_editor(
        df_prep,
        column_config=config_cols,
        key='editor_simple',
        hide_index=True
    )
    
    # Guardar
    if st.button("💾 Guardar"):
        resultado = db.procesar_ediciones_batch_ui(
            st.session_state.df_orig_simple,
            df_edit
        )
        
        if resultado['success']:
            st.success(f"✅ {resultado['exitosas']} actualizadas")
            st.session_state.df_orig_simple = df_edit.copy()
            st.rerun()
        else:
            st.error("Error al guardar")


# ============================================================================
# EJEMPLO 3: Edición de una sola requisición
# ============================================================================

def editar_requisicion_individual(requisicion_id: int):
    """
    Formulario para editar una sola requisición.
    Útil para páginas de detalle o modal de edición.
    """
    st.subheader(f"✏️ Editar Requisición #{requisicion_id}")
    
    # Obtener requisición actual
    req = db.obtener_requisicion_por_id(requisicion_id)
    
    if not req:
        st.error("Requisición no encontrada")
        return
    
    # Formulario con solo campos editables
    with st.form("form_editar_req"):
        col1, col2 = st.columns(2)
        
        with col1:
            proveedor = st.text_input(
                "Proveedor",
                value=req.get('proveedor', ''),
                max_chars=200
            )
            
            oc = st.text_input(
                "N° OC",
                value=req.get('oc', ''),
                max_chars=20
            )
            
            n_guia = st.text_input(
                "N° Guía",
                value=req.get('n_guia', ''),
                max_chars=50
            )
        
        with col2:
            fecha_oc = st.date_input(
                "Fecha OC",
                value=pd.to_datetime(req.get('fecha_oc')) if req.get('fecha_oc') else None
            )
        
        observacion = st.text_area(
            "Observaciones",
            value=req.get('observacion', ''),
            max_chars=500
        )
        
        detalle = st.text_area(
            "Detalle",
            value=req.get('detalle', ''),
            max_chars=500
        )
        
        submitted = st.form_submit_button("💾 Guardar Cambios", type="primary")
        
        if submitted:
            # Preparar cambios
            cambios = {
                'proveedor': proveedor,
                'oc': oc,
                'n_guia': n_guia,
                'fecha_oc': str(fecha_oc) if fecha_oc else None,
                'observacion': observacion,
                'detalle': detalle
            }
            
            # Actualizar
            exito, mensaje = db.actualizar_requisicion_desde_ui(requisicion_id, cambios)
            
            if exito:
                st.success(mensaje)
                st.balloons()
            else:
                st.error(mensaje)


# ============================================================================
# PARA USAR EN app.py
# ============================================================================

"""
# En app.py, reemplazar la función tabla_listado_requisiciones() por:

def pagina_gestion_requisiciones():
    st.title("📋 Gestión de Requisiciones")
    
    st.info("💡 Las requisiciones se cargan automáticamente al importar el cubo")
    
    # Tabla editable
    tabla_requisiciones_editable()
    
    # O la versión simple
    # tabla_requisiciones_editable_simple()
"""
