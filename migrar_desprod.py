"""
Script de migración: Agrega columna desprod a tabla compras
Ejecutar desde terminal: streamlit run migrar_desprod.py
O: python migrar_desprod.py
"""

import streamlit as st
from app.services import compras_service

st.set_page_config(page_title="Migración Base de Datos", page_icon="🔧")

st.title("🔧 Migración de Base de Datos")
st.markdown("---")

st.info("""
### 📋 Migración: Agregar columna 'desprod' a tabla compras

Esta migración agrega la columna **Nombre del Producto (desprod)** a la tabla de compras existente.

**Es seguro ejecutar múltiples veces** - si la columna ya existe, no hace nada.
""")

if st.button("▶️ Ejecutar Migración", type="primary", use_container_width=True):
    with st.spinner("Ejecutando migración..."):
        exito, mensaje = compras_service.migrar_tabla_compras_agregar_desprod()
        
        if exito:
            if "ya existe" in mensaje:
                st.success(f"✅ {mensaje}")
                st.info("La columna desprod ya estaba presente. No se requieren cambios.")
            else:
                st.success(f"✅ {mensaje}")
                st.balloons()
                st.info("💡 Ahora puedes ir a Seguimiento OC y verás la columna 'Nombre Producto'")
        else:
            st.error(f"❌ Error en migración: {mensaje}")

st.markdown("---")
st.caption("Después de ejecutar la migración, puedes cerrar esta página y volver a la aplicación principal.")
