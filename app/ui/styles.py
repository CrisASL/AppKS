"""
Sistema de estilos global para AppKS.
Inyecta CSS una vez al arrancar la app; provee helpers de HTML para componentes visuales.
"""

import streamlit as st


# ── Paleta ────────────────────────────────────────────────────────────────────
_BG_PAGE = "#0e1117"
_BG_CARD = "#161f2e"
_BG_CARD_HOVER = "#1c2840"
_BORDER_CARD = "rgba(255,255,255,0.06)"
_TEXT_PRIMARY = "#f0f2f6"
_TEXT_MUTED = "#8b95a8"
_TEXT_LABEL = "#6b7280"
_TEAL = "#10b981"
_TEAL_DARK = "#059669"
_RADIUS = "14px"


_CSS = """
<style>

/* ── Reset sidebar ─────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background-color: #111827 !important;
    border-right: 1px solid rgba(255,255,255,0.06) !important;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    font-size: 0.82rem;
    color: #8b95a8;
}

/* Ocultar decoración por defecto del sidebar */
[data-testid="stSidebarHeader"] { display: none !important; }

/* ── Logo / header del sidebar ─────────────────────────────── */
.ks-sidebar-logo {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 20px 16px 12px;
}
.ks-sidebar-logo-icon {
    width: 36px;
    height: 36px;
    background: linear-gradient(135deg, #10b981, #059669);
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    flex-shrink: 0;
}
.ks-sidebar-logo-text { line-height: 1.2; }
.ks-sidebar-logo-title {
    font-size: 0.92rem;
    font-weight: 700;
    color: #f0f2f6;
    letter-spacing: -0.01em;
}
.ks-sidebar-logo-sub {
    font-size: 0.70rem;
    color: #6b7280;
}

/* ── Info de usuario en sidebar ────────────────────────────── */
.ks-sidebar-user {
    padding: 10px 16px 14px;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    margin-bottom: 8px;
}
.ks-sidebar-user-row {
    display: flex;
    align-items: center;
    gap: 7px;
    margin-bottom: 3px;
}
.ks-sidebar-user-icon { font-size: 13px; opacity: 0.6; }
.ks-sidebar-user-text { font-size: 0.78rem; color: #8b95a8; }
.ks-sidebar-user-text b { color: #d1d5db; font-weight: 600; }

/* ── Section labels ────────────────────────────────────────── */
.ks-section-label {
    padding: 12px 16px 4px;
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.10em;
    color: #4b5563;
    text-transform: uppercase;
}

/* ── Nav buttons del sidebar ───────────────────────────────── */
[data-testid="stSidebar"] .stButton > button {
    background: transparent !important;
    border: none !important;
    color: #9ca3af !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
    text-align: left !important;
    padding: 7px 16px !important;
    border-radius: 8px !important;
    width: 100% !important;
    transition: background 0.15s, color 0.15s !important;
    box-shadow: none !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(16,185,129,0.08) !important;
    color: #f0f2f6 !important;
}
[data-testid="stSidebar"] .stButton > button[data-active="true"],
[data-testid="stSidebar"] .ks-nav-active button {
    background: rgba(16,185,129,0.15) !important;
    color: #10b981 !important;
    font-weight: 600 !important;
}

/* ── KPI cards ─────────────────────────────────────────────── */
.ks-kpi-grid {
    display: grid;
    grid-template-columns: 2fr 1fr 1fr 1fr;
    gap: 16px;
    margin: 8px 0 24px;
}
.ks-kpi-hero {
    background: linear-gradient(135deg, #064e3b 0%, #065f46 50%, #047857 100%);
    border: 1px solid rgba(16,185,129,0.25);
    border-radius: 14px;
    padding: 24px 28px;
    position: relative;
    overflow: hidden;
}
.ks-kpi-hero::before {
    content: "";
    position: absolute;
    top: -40px; right: -40px;
    width: 140px; height: 140px;
    background: radial-gradient(circle, rgba(16,185,129,0.18) 0%, transparent 70%);
    border-radius: 50%;
}
.ks-kpi-hero .ks-kpi-label {
    font-size: 0.70rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: rgba(167,243,208,0.80);
    margin-bottom: 8px;
}
.ks-kpi-hero .ks-kpi-value {
    font-size: 3rem;
    font-weight: 800;
    color: #ffffff;
    line-height: 1;
    letter-spacing: -0.03em;
}
.ks-kpi-hero .ks-kpi-help {
    font-size: 0.70rem;
    color: rgba(167,243,208,0.60);
    margin-top: 6px;
}
.ks-kpi-hero .ks-kpi-icon {
    position: absolute;
    top: 20px; right: 24px;
    font-size: 28px;
    opacity: 0.5;
}

.ks-kpi-flat {
    background: #161f2e;
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 14px;
    padding: 20px 22px;
    position: relative;
}
.ks-kpi-flat .ks-kpi-icon {
    font-size: 20px;
    margin-bottom: 12px;
    opacity: 0.55;
}
.ks-kpi-flat .ks-kpi-label {
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: #6b7280;
    margin-bottom: 4px;
}
.ks-kpi-flat .ks-kpi-value {
    font-size: 2rem;
    font-weight: 800;
    color: #f0f2f6;
    line-height: 1;
    letter-spacing: -0.02em;
}
.ks-kpi-flat .ks-kpi-help {
    font-size: 0.68rem;
    color: #4b5563;
    margin-top: 6px;
}

/* ── Card contenedor genérico ──────────────────────────────── */
.ks-card {
    background: #161f2e;
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 14px;
    padding: 20px 22px;
    margin-bottom: 16px;
}

/* ── Empty state ───────────────────────────────────────────── */
.ks-empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 40px 20px;
    text-align: center;
}
.ks-empty-icon {
    font-size: 36px;
    opacity: 0.25;
    margin-bottom: 12px;
}
.ks-empty-title {
    font-size: 0.85rem;
    color: #6b7280;
    font-weight: 500;
    margin-bottom: 4px;
}
.ks-empty-sub {
    font-size: 0.75rem;
    color: #4b5563;
}

/* ── Ajustes generales ─────────────────────────────────────── */
/* Quitar padding excesivo del main content */
[data-testid="stMainBlockContainer"] {
    padding-top: 28px !important;
}
/* Título de página más limpio */
[data-testid="stMainBlockContainer"] h1 {
    font-size: 1.55rem !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em !important;
    margin-bottom: 2px !important;
}
/* Métricas nativas de Streamlit — ocultar si usamos las propias */
/* (dejarlas por si hay pages que no migramos aún) */

</style>
"""


def inject_css() -> None:
    """Inyecta el CSS global. Llamar una vez en main(), después de set_page_config."""
    st.markdown(_CSS, unsafe_allow_html=True)


# ── Helpers de componentes ────────────────────────────────────────────────────

def kpi_hero(label: str, value, icon: str = "📋", help_text: str = "") -> None:
    """Card KPI grande con gradiente verde (el indicador principal)."""
    help_html = f'<div class="ks-kpi-help">{help_text}</div>' if help_text else ""
    st.markdown(
        f"""
        <div class="ks-kpi-hero">
            <span class="ks-kpi-icon">{icon}</span>
            <div class="ks-kpi-label">{label}</div>
            <div class="ks-kpi-value">{value}</div>
            {help_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def kpi_card(label: str, value, icon: str = "📊", help_text: str = "") -> None:
    """Card KPI flat (indicadores secundarios)."""
    help_html = f'<div class="ks-kpi-help">{help_text}</div>' if help_text else ""
    st.markdown(
        f"""
        <div class="ks-kpi-flat">
            <div class="ks-kpi-icon">{icon}</div>
            <div class="ks-kpi-label">{label}</div>
            <div class="ks-kpi-value">{value}</div>
            {help_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def empty_state(icon: str, title: str, subtitle: str = "") -> None:
    """Estado vacío elegante: ícono + título + subtítulo opcional."""
    sub_html = f'<div class="ks-empty-sub">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f"""
        <div class="ks-empty">
            <div class="ks-empty-icon">{icon}</div>
            <div class="ks-empty-title">{title}</div>
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_label(text: str) -> None:
    """Etiqueta de sección uppercase muted para el sidebar."""
    st.markdown(
        f'<div class="ks-section-label">{text}</div>',
        unsafe_allow_html=True,
    )


def open_card() -> None:
    """Abre un contenedor card genérico."""
    st.markdown('<div class="ks-card">', unsafe_allow_html=True)


def close_card() -> None:
    """Cierra el contenedor card genérico."""
    st.markdown("</div>", unsafe_allow_html=True)
