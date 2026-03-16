"""
Configuración y constantes del sistema de gestión de requisiciones
KS Seguridad Industrial - Sucursal Talca
"""

import os
from pathlib import Path


# Directorio base del proyecto (raíz de AppKS/)
BASE_DIR = Path(__file__).resolve().parent.parent

# ============================================================================
# CONFIGURACIÓN DE COLUMNAS DE CUBOS EXCEL
# ============================================================================

# Columnas esperadas en Cubo de Requisiciones
COLUMNAS_REQ = [
    "FEmision",  # Fecha de emisión
    "NumReq",  # Número de requisición
    "CodProd",  # Código del producto
    "DesProd",  # Descripción del producto
    # Columnas de Stock Actual (por bodega)
    "KS BODEGA CENTRAL",
    "VENTURA LAVALLE",
    "BODEGA ROPA VENTURA",
    "CD SAN BERNARDO",
    "KS TALCA",
    # Columnas de Cantidad Solicitada (por sucursal)
    "TALCA",  # ⭐ Cantidad solicitada por Talca
    "RANCAGUA",  # Cantidad solicitada por Rancagua
    "VIÑA2",  # Cantidad solicitada por Viña del Mar
    # Columnas adicionales
    "DESDE",
    "HASTA",
    "QTTY GUIA",
    "QTTY COMPRA",
    "COMPRA SUCURSAL DESTINO",
    "CONCT",
    "FORMULA_FOLIO",
]

# Columnas CRÍTICAS (mínimas obligatorias) para Cubo de Requisiciones
COLUMNAS_CRITICAS_REQ = [
    "FEmision",
    "NumReq",
    "CodProd",
    "DesProd",
    "TALCA",  # ⭐ TODO MAYÚSCULAS
]

# Columnas esperadas en Cubo de Compras
COLUMNAS_COMPRAS = [
    "NumOC",  # Número de orden de compra
    "RazonSocial",  # RUT del proveedor
    "Proveedor",  # Nombre del proveedor
    "CodProd",  # Código producto
    "DesProd",  # Descripción producto
    "Familia",  # Código familia
    "DescripcionFamilia",  # Descripción familia
    "CantidadSolicitada",  # Cantidad en la OC
    "CantidadRecibida",  # Cantidad recibida a la fecha
    "CantidadRecepManual",  # Ajustes manuales
    "PrecioCompra",  # Precio unitario
    "TotalLinea",  # Total de la línea
    "FechaOC",  # Fecha de emisión OC
    "CodEtapaCabecera",  # Código de etapa
    "DescEtapa",  # Descripción etapa
    "EstadoLinea",  # Estado (Recibido, Pendiente, etc.)
    "FechaRecepcionAlbaran",  # Fecha de recepción
    "Bodega",  # Código bodega destino
    "DesBode",  # Nombre bodega destino
    "Observacion",  # Observaciones/detalles
]

# Columnas CRÍTICAS para Cubo de Compras
COLUMNAS_CRITICAS_COMPRAS = ["NumOC", "Proveedor", "CodProd", "DesProd", "FechaOC"]

# Columnas esperadas en Cubo de Ventas
COLUMNAS_VENTAS = [
    "CodProd",  # Código producto
    "DesProd",  # Descripción producto
    "ene",  # Ventas enero
    "feb",  # Ventas febrero
    "mar",  # Ventas marzo
    "abr",  # Ventas abril
    "may",  # Ventas mayo
    "jun",  # Ventas junio
    "jul",  # Ventas julio
    "ago",  # Ventas agosto
    "sept",  # Ventas septiembre
    "oct",  # Ventas octubre
    "nov",  # Ventas noviembre
    "dic",  # Ventas diciembre
]

# Columnas CRÍTICAS para Cubo de Ventas
COLUMNAS_CRITICAS_VENTAS = [
    "CodProd",
    "DesProd",
    # Los meses son opcionales
]

# Columnas esperadas en Cubo de Inventario
COLUMNAS_INVENTARIO = [
    "CodProd",  # Código producto
    "CostoUnitario",  # Costo unitario en pesos
    "BODEGA ROPA VENTURA",  # Stock en bodega
    "CD SAN BERNARDO",  # Stock en bodega
    "KS BODEGA CENTRAL",  # Stock en bodega
    "KS CONCEPCION",  # Stock en bodega
    "KS COPIAPO",  # Stock en bodega
    "KS RANCAGUA",  # Stock en bodega
    "KS TALCA",  # Stock en bodega
    "VIÑA DEL MAR",  # Stock en bodega
    "Total general",  # Stock total todas las bodegas
]

# Columnas CRÍTICAS para Cubo de Inventario
COLUMNAS_CRITICAS_INVENTARIO = ["CodProd", "KS TALCA", "Total general"]

# ============================================================================
# CATÁLOGOS Y OPCIONES
# ============================================================================

# Estados posibles de una Orden de Compra
ESTADOS_OC = [
    "Pendiente",
    "OC Generada",
    "En Tránsito",
    "Guía de Despacho",
    "Recepción Parcial",
    "Recepción Completa",
    "Cancelada",
    "No se compra",
]

# Estados posibles para el seguimiento manual de una requisición (panel operativo)
ESTADOS_REQ = [
    "Pendiente",
    "Recepcionada",
    "Parcial",
    "No se compra",
]

# Estados posibles para el campo de envío de OC al proveedor
ESTADOS_ENVIO = [
    "No Enviado",
    "Enviado",
]

# ============================================================================
# SUCURSALES Y BODEGAS
# ============================================================================

# Nombres de bodegas (como aparecen en columnas de STOCK)
BODEGAS = [
    "KS BODEGA CENTRAL",
    "VENTURA LAVALLE",
    "BODEGA ROPA VENTURA",
    "CD SAN BERNARDO",
    "KS TALCA",
    "KS CONCEPCION",
    "KS RANCAGUA",
    "KS COPIAPO",
    "VIÑA DEL MAR",
]

# Nombres de columnas de cantidad solicitada (en cubo de requisiciones)
COLUMNAS_CANTIDAD_SUCURSAL = {
    "Talca": "TALCA",
    "Rancagua": "RANCAGUA",
    "Viña del Mar": "VIÑA2",
}

# Mapeo de sucursal a bodega de stock
SUCURSAL_A_BODEGA = {
    "Talca": "KS TALCA",
    "Rancagua": "KS RANCAGUA",
    "Concepción": "KS CONCEPCION",
    "Copiapó": "KS COPIAPO",
    "Viña del Mar": "VIÑA DEL MAR",
}

# Sucursales disponibles en el sistema
SUCURSALES_DISPONIBLES = ["Talca", "Rancagua", "Viña del Mar"]

# ============================================================================
# CONFIGURACIÓN DE USUARIO Y SESIÓN
# ============================================================================

# Usuario actual (para futuro multiusuario)
USUARIO_ACTUAL = "Cristian Salas"

# Sucursal asignada al usuario
SUCURSAL_ASIGNADA = "Talca"

# Bodega correspondiente a la sucursal del usuario
BODEGA_ASIGNADA = "KS TALCA"

# Nombre de columna de cantidad solicitada para el usuario
COLUMNA_CANTIDAD_USUARIO = "TALCA"

# ============================================================================
# CONFIGURACIÓN DE ALERTAS Y NOTIFICACIONES
# ============================================================================

# Días para alertas de órdenes de compra sin recepción
DIAS_ALERTA_OC_SIN_RECEPCION = 45

# Días para alertas de requisiciones sin OC asignada
DIAS_ALERTA_REQ_SIN_OC = 15

# Días para alertas de recepción parcial
DIAS_ALERTA_RECEPCION_PARCIAL = 30

# Umbral de stock crítico (unidades)
STOCK_CRITICO = 10

# ============================================================================
# CONFIGURACIÓN DE BASE DE DATOS
# ============================================================================

# Ruta de la base de datos SQLite
DB_PATH = os.path.join(BASE_DIR, "data", "ks_requisiciones.db")

# Ruta para backups
BACKUP_PATH = os.path.join(BASE_DIR, "backups")

# Ruta para exportaciones
EXPORT_PATH = os.path.join(BASE_DIR, "exports")

# Ruta para logs
LOG_PATH = os.path.join(BASE_DIR, "logs")

# ============================================================================
# CONFIGURACIÓN DE INTERFAZ
# ============================================================================

# Título de la aplicación
APP_TITLE = "📦 KS Seguridad Industrial"

# Configuración de página Streamlit
PAGE_CONFIG = {
    "page_title": "KS Requisiciones - Talca",
    "page_icon": "📦",
    "layout": "wide",
    "initial_sidebar_state": "expanded",
}

# Menú de navegación
MENU_OPTIONS = [
    "📊 Dashboard",
    "📋 Gestión Requisiciones",
    "🛒 Seguimiento OC",
    "📈 Análisis Stock",
    "⚙️ Configuración",
]

# Colores para estados (formato hexadecimal)
COLORES_ESTADO = {
    "Pendiente": "#FFA500",  # Naranja
    "OC Generada": "#4169E1",  # Azul
    "En Tránsito": "#1E90FF",  # Azul claro
    "Guía de Despacho": "#FFD700",  # Amarillo
    "Recepción Parcial": "#FF8C00",  # Naranja oscuro
    "Recepción Completa": "#32CD32",  # Verde
    "Cancelada": "#DC143C",  # Rojo
    "No se compra": "#808080",  # Gris
}

# Emojis para estados
EMOJIS_ESTADO = {
    "Pendiente": "⏳",
    "OC Generada": "📄",
    "En Tránsito": "🚚",
    "Guía de Despacho": "📋",
    "Recepción Parcial": "📦",
    "Recepción Completa": "✅",
    "Cancelada": "❌",
    "No se compra": "🚫",
}

# ============================================================================
# CONFIGURACIÓN DE EXPORTACIÓN
# ============================================================================

# Formato de fecha para nombres de archivo
FORMATO_FECHA_ARCHIVO = "%Y%m%d_%H%M%S"

# Formato de fecha para visualización
FORMATO_FECHA_VISUAL = "%d/%m/%Y"

# ============================================================================
# MENSAJES DEL SISTEMA
# ============================================================================

# Mensajes de éxito
MSG_EXITO_CREAR = "✅ Requisición creada exitosamente"
MSG_EXITO_ACTUALIZAR = "✅ Requisición actualizada exitosamente"
MSG_EXITO_ELIMINAR = "✅ Requisición eliminada exitosamente"
MSG_EXITO_EXPORTAR = "✅ Archivo exportado exitosamente"
MSG_EXITO_BACKUP = "💾 Backup creado exitosamente"

# Mensajes de error
MSG_ERROR_CREAR = "❌ Error al crear requisición"
MSG_ERROR_ACTUALIZAR = "❌ Error al actualizar requisición"
MSG_ERROR_ELIMINAR = "❌ Error al eliminar requisición"
MSG_ERROR_EXPORTAR = "❌ Error al exportar archivo"
MSG_ERROR_BACKUP = "❌ Error al crear backup"
MSG_ERROR_CUBO = "❌ Error al cargar cubo. Verifica la estructura del archivo"

# Mensajes de advertencia
MSG_WARN_CAMPOS_REQUERIDOS = "⚠️ Completa todos los campos requeridos"
MSG_WARN_CANTIDAD_INVALIDA = "⚠️ La cantidad debe ser mayor a 0"
MSG_WARN_FECHA_INVALIDA = "⚠️ La fecha no puede ser futura"
MSG_WARN_STOCK_INSUFICIENTE = "⚠️ Stock insuficiente en bodega"

# ============================================================================
# CONFIGURACIÓN DE VALIDACIÓN
# ============================================================================

# Longitud máxima para campos de texto
MAX_LEN_OBSERVACION = 500
MAX_LEN_DETALLE = 500
MAX_LEN_CODPROD = 50
MAX_LEN_NUMREQ = 20
MAX_LEN_NUMOC = 20

# Valores por defecto
DEFAULT_ESTADO = "Pendiente"
DEFAULT_CANT_RECIBIDA = 0
DEFAULT_SUCURSAL = "KS TALCA"

# ============================================================================
# CONFIGURACIÓN DE EDICIÓN UI
# ============================================================================

# Campos EDITABLES desde la interfaz de usuario (st.data_editor)
# Solo campos administrativos/manuales que no afectan lógica de negocio
CAMPOS_EDITABLES_UI = [
    "proveedor",  # Nombre del proveedor
    "oc",  # Número de OC
    "n_guia",  # Número de guía de despacho
    "fecha_oc",  # Fecha de emisión de la OC
    "observacion",  # Observaciones generales
    "detalle",  # Detalle adicional
    "oc_enviada",  # Legado: mantenido por compatibilidad con DBs antiguas
    "estado_envio",  # Estado de envío de OC al proveedor (dropdown: No Enviado/Enviado)
    "estado_req",  # Estado manual de la requisición (dropdown operativo)
]

# Campos NO EDITABLES desde la interfaz (protegidos)
# Estos campos solo pueden modificarse mediante funciones backend específicas
CAMPOS_NO_EDITABLES_UI = [
    "id",  # ID de la base de datos
    "numreq",  # Número de requisición (inmutable)
    "codprod",  # Código de producto (inmutable)
    "desprod",  # Descripción producto (inmutable)
    "cantidad",  # Cantidad solicitada (inmutable)
    "sucursal_destino",  # Sucursal destino (inmutable)
    "cant_recibida",  # Solo vía registrar_recepcion()
    "saldo_pendiente",  # Calculado automáticamente por trigger
    "estado_oc",  # Solo vía actualizar_estado()
    "fecha_creacion",  # Timestamp automático
    "fecha_modificacion",  # Timestamp automático
]

# Límites de caracteres para campos editables
LIMITES_CAMPOS_EDITABLES = {
    "proveedor": 200,
    "oc": MAX_LEN_NUMOC,
    "n_guia": 50,
    "observacion": MAX_LEN_OBSERVACION,
    "detalle": MAX_LEN_DETALLE,
}
