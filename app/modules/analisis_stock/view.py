"""
Vista de Análisis de Stock — KS Talca
Muestra la tabla cruzada de inventario vs ventas con rotación y estado del stock.
"""

import streamlit as st
import pandas as pd

from app.modules.analisis_stock import service

# ── Configuración visual ──────────────────────────────────────────────────────

_ICONO_ESTADO = {
    'Falta de stock': '🔴',
    'Stock óptimo':   '🟢',
    'Sobrestock':     '🟡',
}

_ICONO_ROTACION = {
    'Alta rotación':  '🔥',
    'Rotación media': '🔄',
    'Baja rotación':  '❄️',
}

_ORDEN_OPCIONES = {
    'ventas_mes_actual_anio_anterior':    '📦 Ventas mes actual (año ant.)',
    'ventas_mes_siguiente_anio_anterior': '📦 Ventas mes siguiente (año ant.)',
    'stock_actual':                       '📊 Stock actual',
    'stock_objetivo':                     '🎯 Stock objetivo',
    'meses_con_venta':                    '📅 Meses con venta',
    'codprod':                            '🔤 Código producto',
}


# ── Funciones auxiliares ──────────────────────────────────────────────────────

def _metricas_resumen(df: pd.DataFrame) -> None:
    """Muestra las métricas de resumen en la parte superior."""
    total   = len(df)
    falta   = (df['estado_stock'] == 'Falta de stock').sum()
    optimo  = (df['estado_stock'] == 'Stock óptimo').sum()
    sobre   = (df['estado_stock'] == 'Sobrestock').sum()
    alta    = (df['rotacion'] == 'Alta rotación').sum()
    media   = (df['rotacion'] == 'Rotación media').sum()
    baja    = (df['rotacion'] == 'Baja rotación').sum()

    st.markdown("**Estado de stock**")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total productos",  total)
    c2.metric("🔴 Falta de stock", falta)
    c3.metric("🟢 Stock óptimo",   optimo)
    c4.metric("🟡 Sobrestock",     sobre)

    st.markdown("**Rotación de productos**")
    r1, r2, r3, _ = st.columns(4)
    r1.metric("🔥 Alta rotación",  alta)
    r2.metric("🔄 Rotación media", media)
    r3.metric("❄️ Baja rotación",  baja)


# ── Función principal de renderizado ─────────────────────────────────────────

def render(cubo_inventario: pd.DataFrame, cubo_ventas: pd.DataFrame) -> None:
    """
    Renderiza la sección de Análisis de Stock en Streamlit.

    Args:
        cubo_inventario: DataFrame del cubo de inventario (desde session_state).
        cubo_ventas:     DataFrame del cubo de ventas (desde session_state).
    """
    from app.modules.analisis_stock.service import _mes_actual_col, _mes_siguiente_col
    mes_actual_label  = _mes_actual_col().upper()
    mes_sig_label     = _mes_siguiente_col().upper()

    st.subheader("📦 Inventario vs Ventas — KS Talca")
    st.caption(
        f"Bodega analizada: **KS TALCA** · "
        f"Stock objetivo = ventas **{mes_actual_label}** + ventas **{mes_sig_label}** (año anterior)"
    )

    # ── Calcular análisis ─────────────────────────────────────────────────────
    with st.spinner("Calculando análisis de stock..."):
        try:
            df = service.calcular_analisis_stock(cubo_inventario, cubo_ventas)
        except ValueError as exc:
            st.error(f"❌ No se pudo generar el análisis: {exc}")
            return
        except Exception as exc:
            st.error(f"❌ Error inesperado al calcular el análisis: {exc}")
            return

    if df.empty:
        st.warning(
            "No se encontraron datos para la bodega KS TALCA. "
            "Verifica que el cubo de inventario sea el correcto."
        )
        return

    # ── Métricas resumen ──────────────────────────────────────────────────────
    _metricas_resumen(df)
    st.markdown("---")

    # ── Filtro de búsqueda por descripción ──────────────────────────────────
    filtro_desc = st.text_input(
        "🔍 Buscar producto",
        placeholder="Escribe parte del nombre o descripción...",
        key="analisis_stock_buscar"
    )
    if filtro_desc:
        df = df[df['desprod'].astype(str).str.contains(filtro_desc, case=False, na=False)]

    # ── Controles de ordenamiento y filtro ────────────────────────────────────
    col_ord, col_filt_estado, col_filt_rot = st.columns([2, 3, 3])

    with col_ord:
        orden = st.selectbox(
            "Ordenar por",
            options=list(_ORDEN_OPCIONES.keys()),
            format_func=lambda x: _ORDEN_OPCIONES[x],
            key="analisis_stock_orden"
        )

    with col_filt_estado:
        estados_disponibles = sorted(df['estado_stock'].unique().tolist())
        estados_sel = st.multiselect(
            "Filtrar por estado de stock",
            options=estados_disponibles,
            default=estados_disponibles,
            key="analisis_stock_filtro_estado"
        )

    with col_filt_rot:
        rotaciones_disponibles = sorted(df['rotacion'].unique().tolist())
        rotaciones_sel = st.multiselect(
            "Filtrar por rotación",
            options=rotaciones_disponibles,
            default=rotaciones_disponibles,
            key="analisis_stock_filtro_rotacion"
        )

    # ── Aplicar filtros y ordenamiento ────────────────────────────────────────
    ascendente = (orden == 'codprod')    # Solo código se ordena A→Z
    df_vista = (
        df[
            df['estado_stock'].isin(estados_sel) &
            df['rotacion'].isin(rotaciones_sel)
        ]
        .sort_values(orden, ascending=ascendente)
        .reset_index(drop=True)
        .copy()
    )

    # Aplicar íconos para la visualización
    df_vista['estado_stock'] = df_vista['estado_stock'].map(
        lambda v: f"{_ICONO_ESTADO.get(v, '⚪')} {v}"
    )
    df_vista['rotacion'] = df_vista['rotacion'].map(
        lambda v: f"{_ICONO_ROTACION.get(v, '')} {v}"
    )

    # ── Tabla de resultados ───────────────────────────────────────────────────
    st.dataframe(
        df_vista,
        use_container_width=True,
        column_config={
            'codprod':                           st.column_config.TextColumn('Código',              width='small'),
            'desprod':                           st.column_config.TextColumn('Descripción',         width='large'),
            'ventas_mes_actual_anio_anterior':   st.column_config.NumberColumn(f'Vtas {mes_actual_label} ant.', format='%d'),
            'ventas_mes_siguiente_anio_anterior':st.column_config.NumberColumn(f'Vtas {mes_sig_label} ant.',    format='%d'),
            'stock_actual':                      st.column_config.NumberColumn('Stock Actual',      format='%d'),
            'stock_objetivo':                    st.column_config.NumberColumn('Stock Objetivo',    format='%d'),
            'estado_stock':                      st.column_config.TextColumn('Estado Stock',        width='medium'),
            'meses_con_venta':                   st.column_config.NumberColumn('Meses c/venta',    format='%d'),
            'rotacion':                          st.column_config.TextColumn('Rotación',            width='medium'),
        }
    )

    st.caption(f"Mostrando **{len(df_vista)}** de **{len(df)}** productos.")

    # ── Sección de ayuda ──────────────────────────────────────────────────────
    with st.expander("ℹ️ Cómo se calcula el análisis", expanded=False):
        st.markdown("""
        **Estado de stock** — comparación contra stock objetivo (cobertura 2 meses)

        | Estado           | Condición                                   |
        |------------------|---------------------------------------------|
        | 🔴 Falta de stock | Stock actual < Stock objetivo               |
        | 🟢 Stock óptimo   | Stock actual = Stock objetivo               |
        | 🟡 Sobrestock     | Stock actual > Stock objetivo               |

        **Stock objetivo** = Ventas mes actual (año ant.) + Ventas mes siguiente (año ant.)

        ---

        **Rotación** — basada en cuántos meses del año tuvo ventas > 0

        | Rotación         | Meses con ventas  |
        |------------------|-------------------|
        | 🔥 Alta rotación  | 10 a 12 meses     |
        | 🔄 Rotación media | 7 a 9 meses       |
        | ❄️ Baja rotación  | 0 a 6 meses       |

        - El stock se obtiene de la columna **KS TALCA** del cubo de inventario.
        - Solo se muestran productos presentes en el cubo de inventario para KS TALCA.
        """)
