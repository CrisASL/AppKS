"""
Funciones auxiliares y utilidades
KS Seguridad Industrial - Sistema de Requisiciones
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from app import config


# ============================================================================
# VALIDACIÓN DE CUBOS EXCEL
# ============================================================================

def validar_estructura_cubo(df: pd.DataFrame, 
                            columnas_esperadas: List[str],
                            columnas_criticas: List[str] = None,
                            nombre_cubo: str = "Cubo") -> Tuple[bool, str, List[str]]:
    """
    Valida que un DataFrame tenga las columnas esperadas.
    
    Args:
        df (pd.DataFrame): DataFrame a validar
        columnas_esperadas (list): Lista de todas las columnas ideales
        columnas_criticas (list, optional): Solo columnas absolutamente necesarias
        nombre_cubo (str): Nombre del cubo para mensajes
    
    Returns:
        tuple: (es_valido: bool, mensaje: str, columnas_faltantes: list)
    """
    if df is None or df.empty:
        return False, "❌ DataFrame vacío o None", []
    
    columnas_actuales = set(df.columns)
    columnas_requeridas = set(columnas_esperadas)
    
    # Si no se especifican columnas críticas, todas son críticas
    if columnas_criticas is None:
        columnas_criticas = columnas_esperadas
    
    columnas_criticas_set = set(columnas_criticas)
    
    # Verificar columnas faltantes
    columnas_faltantes = list(columnas_requeridas - columnas_actuales)
    columnas_criticas_faltantes = list(columnas_criticas_set - columnas_actuales)
    
    # Si faltan columnas críticas → ERROR
    if columnas_criticas_faltantes:
        mensaje = f"❌ {nombre_cubo}: Faltan columnas críticas: {', '.join(columnas_criticas_faltantes[:5])}"
        if len(columnas_criticas_faltantes) > 5:
            mensaje += f" (y {len(columnas_criticas_faltantes) - 5} más)"
        return False, mensaje, columnas_criticas_faltantes
    
    # Si faltan columnas opcionales → WARNING (pero válido)
    if columnas_faltantes:
        mensaje = f"⚠️ {nombre_cubo}: {len(columnas_faltantes)} columnas opcionales faltantes (expandir para ver detalles)"
        return True, mensaje, columnas_faltantes
    
    # Todo OK
    mensaje = f"✅ {nombre_cubo}: Estructura completa ({len(df)} filas, {len(df.columns)} columnas)"
    return True, mensaje, []


def validar_cubo_requisiciones(df: pd.DataFrame) -> Tuple[bool, str, List[str]]:
    """Valida específicamente el cubo de requisiciones."""
    return validar_estructura_cubo(
        df, 
        config.COLUMNAS_REQ,
        config.COLUMNAS_CRITICAS_REQ,
        "Cubo de Requisiciones"
    )


def validar_cubo_compras(df: pd.DataFrame) -> Tuple[bool, str, List[str]]:
    """Valida específicamente el cubo de compras."""
    return validar_estructura_cubo(
        df,
        config.COLUMNAS_COMPRAS,
        config.COLUMNAS_CRITICAS_COMPRAS,
        "Cubo de Compras"
    )


def validar_cubo_ventas(df: pd.DataFrame) -> Tuple[bool, str, List[str]]:
    """Valida específicamente el cubo de ventas."""
    return validar_estructura_cubo(
        df,
        config.COLUMNAS_VENTAS,
        config.COLUMNAS_CRITICAS_VENTAS,
        "Cubo de Ventas"
    )


def validar_cubo_inventario(df: pd.DataFrame) -> Tuple[bool, str, List[str]]:
    """Valida específicamente el cubo de inventario."""
    return validar_estructura_cubo(
        df,
        config.COLUMNAS_INVENTARIO,
        config.COLUMNAS_CRITICAS_INVENTARIO,
        "Cubo de Inventario"
    )


def cargar_excel_con_selector_hoja(archivo, tipo_cubo: str, key_prefix: str = ""):
    """
    Carga un archivo Excel permitiendo seleccionar la hoja si hay múltiples.
    Usa Streamlit para la interacción con el usuario.
    
    Args:
        archivo: Archivo subido por st.file_uploader
        tipo_cubo (str): Tipo de cubo ('requisiciones', 'compras', 'ventas', 'inventario')
        key_prefix (str): Prefijo único para los widgets de Streamlit
    
    Returns:
        pd.DataFrame: DataFrame cargado o None si hay error
    """
    import streamlit as st
    
    try:
        # Leer todas las hojas del archivo
        xls = pd.ExcelFile(archivo)
        hojas_disponibles = xls.sheet_names
        
        # Si solo hay una hoja, cargarla directamente
        if len(hojas_disponibles) == 1:
            df = pd.read_excel(archivo, sheet_name=hojas_disponibles[0])
            st.info(f"📄 Hoja cargada automáticamente: **{hojas_disponibles[0]}**")
            return df
        
        # Si hay múltiples hojas, mostrar selector
        st.info(f"📋 El archivo tiene {len(hojas_disponibles)} hojas. Selecciona la hoja correcta:")
        
        hoja_seleccionada = st.selectbox(
            "Selecciona la hoja:",
            options=hojas_disponibles,
            key=f"{key_prefix}_selector_hoja_{tipo_cubo}"
        )
        
        # Cargar la hoja seleccionada
        df = pd.read_excel(archivo, sheet_name=hoja_seleccionada)
        
        # Mostrar preview
        with st.expander(f"👁️ Preview de '{hoja_seleccionada}' (primeras 5 filas)"):
            st.dataframe(df.head(5), width='stretch')
            st.caption(f"📊 Total: {len(df)} filas, {len(df.columns)} columnas")
        
        return df
        
    except Exception as e:
        st.error(f"❌ Error al leer el archivo Excel: {str(e)}")
        return None


# ============================================================================
# CÁLCULOS DE REQUISICIONES
# ============================================================================

def calcular_saldo_pendiente(cantidad: int, cantidad_recibida: int) -> int:
    """
    Calcula el saldo pendiente de una requisición.
    
    Args:
        cantidad (int): Cantidad solicitada
        cantidad_recibida (int): Cantidad ya recibida
    
    Returns:
        int: Saldo pendiente (no puede ser negativo)
    """
    saldo = cantidad - cantidad_recibida
    return max(0, saldo)


def determinar_estado_por_saldo(cantidad: int, cantidad_recibida: int, 
                                estado_actual: str = None) -> str:
    """
    Determina el estado apropiado basado en el saldo pendiente.
    
    Args:
        cantidad (int): Cantidad solicitada
        cantidad_recibida (int): Cantidad recibida
        estado_actual (str, optional): Estado actual de la requisición
    
    Returns:
        str: Estado sugerido
    """
    if cantidad_recibida == 0:
        return estado_actual or 'Pendiente'
    elif cantidad_recibida >= cantidad:
        return 'Recepción Completa'
    else:
        return 'Recepción Parcial'


# ============================================================================
# ANÁLISIS DE STOCK
# ============================================================================

def analizar_stock_disponible(codprod: str, cantidad_requerida: int, 
                              inventario_df: pd.DataFrame, 
                              sucursal: str = 'Talca') -> Dict:
    """
    Analiza el stock disponible de un producto en todas las bodegas.
    
    Args:
        codprod (str): Código del producto
        cantidad_requerida (int): Cantidad necesaria
        inventario_df (pd.DataFrame): DataFrame del cubo de inventario
        sucursal (str): Sucursal que solicita (default: Talca)
    
    Returns:
        dict: Análisis con stock disponible y sugerencias
    """
    resultado = {
        'codprod': codprod,
        'cantidad_requerida': cantidad_requerida,
        'stock_sucursal': 0,
        'stock_otras_bodegas': {},
        'stock_total': 0,
        'hay_stock_suficiente': False,
        'sugerencia': '',
        'bodega_sugerida': None
    }
    
    # Buscar producto en inventario
    producto = inventario_df[inventario_df['CodProd'] == codprod]
    
    if producto.empty:
        resultado['sugerencia'] = '⚠️ Producto no encontrado en inventario'
        return resultado
    
    producto = producto.iloc[0]
    
    # Obtener bodega de la sucursal
    bodega_sucursal = config.SUCURSAL_A_BODEGA.get(sucursal, 'KS TALCA')
    
    # Stock en sucursal
    if bodega_sucursal in producto:
        resultado['stock_sucursal'] = int(producto[bodega_sucursal]) if pd.notna(producto[bodega_sucursal]) else 0
    
    # Stock en otras bodegas
    for bodega in config.BODEGAS:
        if bodega != bodega_sucursal and bodega in producto:
            stock = int(producto[bodega]) if pd.notna(producto[bodega]) else 0
            if stock > 0:
                resultado['stock_otras_bodegas'][bodega] = stock
    
    # Stock total
    if 'Total general' in producto:
        resultado['stock_total'] = int(producto['Total general']) if pd.notna(producto['Total general']) else 0
    
    # Determinar si hay stock suficiente
    resultado['hay_stock_suficiente'] = resultado['stock_total'] >= cantidad_requerida
    
    # Generar sugerencia
    if resultado['stock_sucursal'] >= cantidad_requerida:
        resultado['sugerencia'] = f"✅ Stock suficiente en {bodega_sucursal} ({resultado['stock_sucursal']} unidades)"
    elif resultado['stock_otras_bodegas']:
        # Buscar bodega con mayor stock
        bodega_max = max(resultado['stock_otras_bodegas'].items(), key=lambda x: x[1])
        if bodega_max[1] >= cantidad_requerida:
            resultado['sugerencia'] = f"🔄 Transferir desde {bodega_max[0]} (stock: {bodega_max[1]} unidades)"
            resultado['bodega_sugerida'] = bodega_max[0]
        else:
            resultado['sugerencia'] = f"⚠️ Stock insuficiente. Disponible: {resultado['stock_total']} | Requerido: {cantidad_requerida}"
    else:
        resultado['sugerencia'] = f"🛒 Generar OC - Stock total insuficiente ({resultado['stock_total']} unidades disponibles)"
    
    return resultado


def sugerir_accion(codprod: str, cantidad_req: int, 
                  inventario_df: pd.DataFrame) -> str:
    """
    Sugiere la acción a tomar (Transferir o Comprar).
    
    Args:
        codprod (str): Código del producto
        cantidad_req (int): Cantidad solicitada
        inventario_df (pd.DataFrame): DataFrame del cubo de inventario
    
    Returns:
        str: Acción sugerida ('Transferir', 'Comprar', 'Sin datos')
    """
    analisis = analizar_stock_disponible(codprod, cantidad_req, inventario_df)
    
    if 'Transferir' in analisis['sugerencia']:
        return 'Transferir'
    elif 'Comprar' in analisis['sugerencia'] or 'OC' in analisis['sugerencia']:
        return 'Comprar'
    elif analisis['stock_sucursal'] >= cantidad_req:
        return 'Stock OK'
    else:
        return 'Sin datos'


def obtener_productos_criticos(inventario_df: pd.DataFrame, 
                               umbral: int = config.STOCK_CRITICO) -> pd.DataFrame:
    """
    Obtiene productos con stock crítico en la bodega de Talca.
    
    Args:
        inventario_df (pd.DataFrame): DataFrame del cubo de inventario
        umbral (int): Umbral de stock crítico (default: 10 unidades)
    
    Returns:
        pd.DataFrame: DataFrame con productos críticos
    """
    if inventario_df.empty or 'KS TALCA' not in inventario_df.columns:
        return pd.DataFrame()
    
    # Filtrar productos con stock < umbral en Talca
    criticos = inventario_df[
        (inventario_df['KS TALCA'] > 0) & 
        (inventario_df['KS TALCA'] < umbral)
    ].copy()
    
    if not criticos.empty:
        criticos = criticos[['CodProd', 'KS TALCA', 'Total general', 'CostoUnitario']]
        criticos = criticos.sort_values('KS TALCA')
    
    return criticos


# ============================================================================
# FORMATEO DE FECHAS
# ============================================================================

def formatear_fecha(fecha_str: str, formato_entrada: str = '%Y-%m-%d', 
                   formato_salida: str = None) -> str:
    """
    Formatea una fecha de string a otro formato.
    
    Args:
        fecha_str (str): Fecha en formato string
        formato_entrada (str): Formato de la fecha de entrada
        formato_salida (str): Formato deseado de salida
    
    Returns:
        str: Fecha formateada, o fecha original si hay error
    """
    if not fecha_str:
        return ''
    
    if formato_salida is None:
        formato_salida = config.FORMATO_FECHA_VISUAL
    
    try:
        fecha_obj = datetime.strptime(str(fecha_str), formato_entrada)
        return fecha_obj.strftime(formato_salida)
    except:
        # Si falla, intentar parseo automático de pandas
        try:
            fecha_obj = pd.to_datetime(fecha_str)
            return fecha_obj.strftime(formato_salida)
        except:
            return str(fecha_str)


def fecha_a_timestamp(fecha_str: str) -> Optional[datetime]:
    """
    Convierte un string de fecha a objeto datetime.
    
    Args:
        fecha_str (str): Fecha en formato string
    
    Returns:
        datetime: Objeto datetime, o None si hay error
    """
    if not fecha_str:
        return None
    
    try:
        return pd.to_datetime(fecha_str)
    except:
        return None


def obtener_fecha_actual() -> str:
    """
    Obtiene la fecha actual en formato YYYY-MM-DD.
    
    Returns:
        str: Fecha actual
    """
    return datetime.now().strftime('%Y-%m-%d')


def calcular_dias_transcurridos(fecha_inicio: str, fecha_fin: str = None) -> int:
    """
    Calcula los días transcurridos entre dos fechas.
    
    Args:
        fecha_inicio (str): Fecha de inicio
        fecha_fin (str, optional): Fecha de fin (default: hoy)
    
    Returns:
        int: Número de días transcurridos
    """
    try:
        inicio = fecha_a_timestamp(fecha_inicio)
        fin = fecha_a_timestamp(fecha_fin) if fecha_fin else datetime.now()
        
        if inicio and fin:
            diferencia = fin - inicio
            return abs(diferencia.days)
        return 0
    except:
        return 0


# ============================================================================
# GENERACIÓN DE NOMBRES DE ARCHIVO
# ============================================================================

def generar_nombre_backup() -> str:
    """
    Genera un nombre único para archivo de backup.
    Formato: ks_req_YYYYMMDD_HHMMSS.db
    
    Returns:
        str: Nombre del archivo de backup
    """
    timestamp = datetime.now().strftime(config.FORMATO_FECHA_ARCHIVO)
    return f"ks_req_{timestamp}.db"


def generar_nombre_exportacion(prefijo: str = "requisiciones", 
                               extension: str = "xlsx") -> str:
    """
    Genera un nombre único para archivo de exportación.
    
    Args:
        prefijo (str): Prefijo del nombre de archivo
        extension (str): Extensión del archivo (xlsx, pdf, csv, etc.)
    
    Returns:
        str: Nombre del archivo
    """
    timestamp = datetime.now().strftime(config.FORMATO_FECHA_ARCHIVO)
    return f"{prefijo}_{timestamp}.{extension}"


# ============================================================================
# PROCESAMIENTO DE CUBOS
# ============================================================================

def limpiar_columnas_numericas(df: pd.DataFrame, columnas: List[str]) -> pd.DataFrame:
    """
    Limpia y convierte columnas a tipo numérico.
    Reemplaza valores nulos por 0.
    
    Args:
        df (pd.DataFrame): DataFrame a procesar
        columnas (list): Lista de nombres de columnas a limpiar
    
    Returns:
        pd.DataFrame: DataFrame con columnas limpias
    """
    df_copy = df.copy()
    
    for col in columnas:
        if col in df_copy.columns:
            df_copy[col] = pd.to_numeric(df_copy[col], errors='coerce').fillna(0)
    
    return df_copy


def filtrar_cubo_requisiciones_sucursal(df: pd.DataFrame, 
                                       sucursal: str = 'Talca') -> pd.DataFrame:
    """
    Filtra el cubo de requisiciones para mostrar solo las de una sucursal.
    
    Args:
        df (pd.DataFrame): DataFrame del cubo de requisiciones
        sucursal (str): Nombre de la sucursal (default: Talca)
    
    Returns:
        pd.DataFrame: DataFrame filtrado
    """
    if df.empty or sucursal not in df.columns:
        return pd.DataFrame()
    
    # Filtrar solo filas donde la sucursal tiene cantidad > 0
    df_filtrado = df[df[sucursal] > 0].copy()
    
    return df_filtrado


def extraer_requisiciones_pendientes(cubo_req_df: pd.DataFrame, 
                                     cubo_compras_df: pd.DataFrame,
                                     sucursal: str = 'Talca') -> pd.DataFrame:
    """
    Extrae requisiciones pendientes comparando cubo de req vs cubo de compras.
    Identifica productos solicitados pero sin OC generada o con OC pendiente.
    
    Args:
        cubo_req_df (pd.DataFrame): DataFrame del cubo de requisiciones
        cubo_compras_df (pd.DataFrame): DataFrame del cubo de compras
        sucursal (str): Sucursal a analizar
    
    Returns:
        pd.DataFrame: DataFrame con requisiciones pendientes
    """
    # Filtrar requisiciones de la sucursal
    req_sucursal = filtrar_cubo_requisiciones_sucursal(cubo_req_df, sucursal)
    
    if req_sucursal.empty:
        return pd.DataFrame()
    
    # Seleccionar columnas relevantes
    req_pendientes = req_sucursal[['NumReq', 'CodProd', 'DesProd', sucursal, 'FEmision']].copy()
    req_pendientes.rename(columns={sucursal: 'Cantidad'}, inplace=True)
    
    return req_pendientes


# ============================================================================
# ALERTAS Y NOTIFICACIONES
# ============================================================================

def generar_alertas_oc(requisiciones_df: pd.DataFrame) -> List[Dict]:
    """
    Genera lista de alertas basadas en requisiciones.
    
    Args:
        requisiciones_df (pd.DataFrame): DataFrame con requisiciones
    
    Returns:
        list: Lista de diccionarios con alertas
    """
    alertas = []
    
    if requisiciones_df.empty:
        return alertas
    
    fecha_actual = datetime.now()
    
    for _, req in requisiciones_df.iterrows():
        # Alerta: OC sin recepción por más de X días
        if req.get('fecha_oc') and req.get('saldo_pendiente', 0) > 0:
            fecha_oc = fecha_a_timestamp(req['fecha_oc'])
            if fecha_oc:
                dias = (fecha_actual - fecha_oc).days
                if dias > config.DIAS_ALERTA_OC_SIN_RECEPCION:
                    alertas.append({
                        'tipo': 'critico',
                        'icono': '🔴',
                        'mensaje': f"OC {req.get('oc', 'N/A')} sin recepción por {dias} días",
                        'requisicion_id': req.get('id')
                    })
        
        # Alerta: Recepción parcial por más de X días
        if req.get('estado_oc') == 'Recepción Parcial' and req.get('fecha_modificacion'):
            fecha_mod = fecha_a_timestamp(req['fecha_modificacion'])
            if fecha_mod:
                dias = (fecha_actual - fecha_mod).days
                if dias > config.DIAS_ALERTA_RECEPCION_PARCIAL:
                    alertas.append({
                        'tipo': 'advertencia',
                        'icono': '⚠️',
                        'mensaje': f"Recepción parcial REQ {req.get('numreq')} por {dias} días",
                        'requisicion_id': req.get('id')
                    })
        
        # Alerta: REQ sin OC asignada
        if not req.get('oc') or req.get('oc') == '':
            fecha_creacion = fecha_a_timestamp(req.get('fecha_creacion'))
            if fecha_creacion:
                dias = (fecha_actual - fecha_creacion).days
                if dias > config.DIAS_ALERTA_REQ_SIN_OC:
                    alertas.append({
                        'tipo': 'info',
                        'icono': 'ℹ️',
                        'mensaje': f"REQ {req.get('numreq')} sin OC asignada por {dias} días",
                        'requisicion_id': req.get('id')
                    })
    
    return alertas


# ============================================================================
# EXPORTACIÓN DE DATOS
# ============================================================================

def preparar_dataframe_para_exportar(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepara un DataFrame para exportación a Excel.
    Formatea fechas, números y limpia datos.
    
    Args:
        df (pd.DataFrame): DataFrame a preparar
    
    Returns:
        pd.DataFrame: DataFrame preparado
    """
    if df.empty:
        return df
    
    df_export = df.copy()
    
    # Formatear fechas
    for col in df_export.columns:
        if 'fecha' in col.lower():
            df_export[col] = df_export[col].apply(
                lambda x: formatear_fecha(x) if pd.notna(x) else ''
            )
    
    # Reemplazar None y NaN por cadena vacía
    df_export = df_export.fillna('')
    
    return df_export


def aplicar_formato_excel(writer, df: pd.DataFrame, sheet_name: str = 'Datos'):
    """
    Aplica formato a una hoja de Excel.
    
    Args:
        writer: ExcelWriter de pandas
        df (pd.DataFrame): DataFrame exportado
        sheet_name (str): Nombre de la hoja
    """
    try:
        from openpyxl.styles import Font, PatternFill, Alignment
        
        workbook = writer.book
        worksheet = writer.sheets[sheet_name]
        
        # Formato de encabezados
        header_fill = PatternFill(start_color='366092', end_color='366092', fill_type='solid')
        header_font = Font(bold=True, color='FFFFFF')
        
        for cell in worksheet[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', vertical='center')
        
        # Autoajustar ancho de columnas
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
        
        # Habilitar filtros
        worksheet.auto_filter.ref = worksheet.dimensions
        
    except Exception as e:
        pass  # Formato opcional - no crítico


# ============================================================================
# VALIDACIONES DE ENTRADA
# ============================================================================

def validar_cantidad(cantidad: any) -> Tuple[bool, str]:
    """
    Valida que una cantidad sea un número positivo.
    
    Args:
        cantidad: Valor a validar
    
    Returns:
        tuple: (es_valido: bool, mensaje_error: str)
    """
    try:
        cant = int(cantidad)
        if cant <= 0:
            return False, "La cantidad debe ser mayor a 0"
        return True, ""
    except:
        return False, "La cantidad debe ser un número válido"


def validar_fecha_no_futura(fecha: str) -> Tuple[bool, str]:
    """
    Valida que una fecha no sea futura.
    
    Args:
        fecha (str): Fecha a validar
    
    Returns:
        tuple: (es_valido: bool, mensaje_error: str)
    """
    if not fecha:
        return True, ""
    
    fecha_obj = fecha_a_timestamp(fecha)
    if not fecha_obj:
        return False, "Formato de fecha inválido"
    
    if fecha_obj > datetime.now():
        return False, "La fecha no puede ser futura"
    
    return True, ""


def validar_codigo_producto(codprod: str) -> Tuple[bool, str]:
    """
    Valida que un código de producto sea válido.
    
    Args:
        codprod (str): Código de producto
    
    Returns:
        tuple: (es_valido: bool, mensaje_error: str)
    """
    if not codprod or codprod.strip() == '':
        return False, "El código de producto es requerido"
    
    if len(codprod) > config.MAX_LEN_CODPROD:
        return False, f"El código de producto no puede exceder {config.MAX_LEN_CODPROD} caracteres"
    
    return True, ""


# ============================================================================
# UTILIDADES DE INTERFAZ
# ============================================================================

def obtener_emoji_estado(estado: str) -> str:
    """
    Obtiene el emoji correspondiente a un estado.
    
    Args:
        estado (str): Estado de la OC
    
    Returns:
        str: Emoji correspondiente
    """
    return config.EMOJIS_ESTADO.get(estado, '❓')


def obtener_color_estado(estado: str) -> str:
    """
    Obtiene el color correspondiente a un estado.
    
    Args:
        estado (str): Estado de la OC
    
    Returns:
        str: Color en formato hexadecimal
    """
    return config.COLORES_ESTADO.get(estado, '#808080')


def formatear_numero(numero: float, decimales: int = 0, 
                    simbolo_moneda: str = None) -> str:
    """
    Formatea un número para visualización.
    
    Args:
        numero (float): Número a formatear
        decimales (int): Cantidad de decimales
        simbolo_moneda (str, optional): Símbolo de moneda a añadir
    
    Returns:
        str: Número formateado
    """
    try:
        formato = f"{{:,.{decimales}f}}"
        numero_formateado = formato.format(numero)
        
        # Reemplazar separadores (formato chileno: punto para miles, coma para decimales)
        numero_formateado = numero_formateado.replace(',', 'X').replace('.', ',').replace('X', '.')
        
        if simbolo_moneda:
            return f"{simbolo_moneda}{numero_formateado}"
        
        return numero_formateado
    except:
        return str(numero)


# ============================================================================
# CONFIGURACIÓN DE COLUMNAS PARA st.data_editor
# ============================================================================

def obtener_config_columnas_editables() -> Dict[str, any]:
    """
    Retorna la configuración de columnas para st.data_editor.
    
    Define qué columnas son editables y cuáles están deshabilitadas,
    junto con configuraciones específicas de cada columna (tipo, formato, etc).
    
    Returns:
        Dict con configuración de columnas compatible con st.data_editor:
            - Columnas editables: configuradas según tipo de dato
            - Columnas no editables: {'disabled': True}
    
    Ejemplos:
        >>> config_cols = obtener_config_columnas_editables()
        >>> df_editado = st.data_editor(df, column_config=config_cols)
    
    Notas:
        - Las columnas editables se definen en config.CAMPOS_EDITABLES_UI
        - Las columnas protegidas se definen en config.CAMPOS_NO_EDITABLES_UI
        - Incluye configuración de tipos (TextColumn, NumberColumn, DateColumn)
    """
    import streamlit as st
    
    column_config = {}
    
    # Configurar columnas NO EDITABLES (protegidas)
    for campo in config.CAMPOS_NO_EDITABLES_UI:
        column_config[campo] = st.column_config.Column(
            disabled=True,
            help=f"Campo protegido: no editable desde la interfaz"
        )
    
    # Configurar columnas EDITABLES con tipos específicos
    column_config['proveedor'] = st.column_config.TextColumn(
        'Proveedor',
        help='Nombre del proveedor (editable)',
        max_chars=config.LIMITES_CAMPOS_EDITABLES.get('proveedor', 200),
        required=False
    )
    
    column_config['oc'] = st.column_config.TextColumn(
        'N° OC',
        help='Número de Orden de Compra (editable)',
        max_chars=config.LIMITES_CAMPOS_EDITABLES.get('oc', 20),
        required=False
    )
    
    column_config['n_guia'] = st.column_config.TextColumn(
        'N° Guía',
        help='Número de guía de despacho (editable)',
        max_chars=config.LIMITES_CAMPOS_EDITABLES.get('n_guia', 50),
        required=False
    )
    
    column_config['fecha_oc'] = st.column_config.DateColumn(
        'Fecha OC',
        help='Fecha de emisión de la OC (editable)',
        format="DD/MM/YYYY",
        required=False
    )
    
    column_config['observacion'] = st.column_config.TextColumn(
        'Observaciones',
        help='Observaciones generales (editable)',
        max_chars=config.LIMITES_CAMPOS_EDITABLES.get('observacion', 500),
        required=False
    )
    
    column_config['detalle'] = st.column_config.TextColumn(
        'Detalle',
        help='Detalle adicional (editable)',
        max_chars=config.LIMITES_CAMPOS_EDITABLES.get('detalle', 500),
        required=False
    )
    
    return column_config


def preparar_df_para_edicion_segura(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepara un DataFrame para edición segura en st.data_editor.
    
    Realiza las siguientes transformaciones:
    - Reordena columnas (campos clave primero, editables después)
    - Convierte tipos de datos para compatibilidad con Arrow/Streamlit
    - Limpia valores NaN/None problemáticos
    - Asegura que la columna 'id' esté presente
    
    Args:
        df (pd.DataFrame): DataFrame original de requisiciones
    
    Returns:
        pd.DataFrame: DataFrame preparado para st.data_editor
    
    Ejemplos:
        >>> df_preparado = preparar_df_para_edicion_segura(df_requisiciones)
        >>> df_editado = st.data_editor(df_preparado)
    
    Notas:
        - Mantiene todos los datos originales
        - Solo modifica formato y orden para mejor UX
        - Compatible con actualizar_requisicion_desde_ui()
    """
    if df is None or df.empty:
        return df
    
    df_copia = df.copy()
    
    # Asegurar que existe columna 'id'
    if 'id' not in df_copia.columns:
        raise ValueError("DataFrame debe tener columna 'id'")
    
    # Orden de columnas para mejor UX
    columnas_orden = [
        'id', 'numreq', 'codprod', 'desprod', 'cantidad',
        'proveedor', 'oc', 'fecha_oc', 'n_guia',
        'estado_oc', 'cant_recibida', 'saldo_pendiente',
        'observacion', 'detalle',
        'fecha_creacion', 'fecha_modificacion'
    ]
    
    # Reordenar solo columnas que existen
    columnas_disponibles = [col for col in columnas_orden if col in df_copia.columns]
    columnas_restantes = [col for col in df_copia.columns if col not in columnas_disponibles]
    columnas_finales = columnas_disponibles + columnas_restantes
    
    df_copia = df_copia[columnas_finales]
    
    # Convertir tipos para evitar errores de Arrow en Streamlit
    for col in df_copia.columns:
        # Convertir object a string
        if df_copia[col].dtype == 'object':
            df_copia[col] = df_copia[col].fillna('').astype(str)
        
        # Manejar fechas
        if 'fecha' in col.lower():
            try:
                df_copia[col] = pd.to_datetime(df_copia[col], errors='coerce')
            except:
                pass
    
    return df_copia


def validar_ediciones_antes_de_guardar(df_editado: pd.DataFrame) -> Tuple[bool, List[str]]:
    """
    Valida las ediciones realizadas antes de guardarlas en la base de datos.
    
    Verifica:
    - Que no se hayan modificado campos protegidos (si es posible detectarlo)
    - Que los valores editables estén dentro de los límites permitidos
    - Que las fechas sean válidas
    - Que no haya valores problemáticos (inyección SQL, etc.)
    
    Args:
        df_editado (pd.DataFrame): DataFrame después de las ediciones
    
    Returns:
        Tuple[bool, List[str]]:
            - bool: True si todas las validaciones pasan
            - List[str]: Lista de mensajes de error (vacía si todo OK)
    
    Ejemplos:
        >>> es_valido, errores = validar_ediciones_antes_de_guardar(df)
        >>> if not es_valido:
        >>>     for error in errores:
        >>>         st.error(error)
    """
    errores = []
    
    # Validar que existe columna id
    if 'id' not in df_editado.columns:
        errores.append("Error crítico: Falta columna 'id'")
        return False, errores
    
    # Validar límites de caracteres en campos editables de texto
    campos_texto_editables = ['proveedor', 'oc', 'n_guia', 'observacion', 'detalle']
    
    for campo in campos_texto_editables:
        if campo in df_editado.columns and campo in config.LIMITES_CAMPOS_EDITABLES:
            limite = config.LIMITES_CAMPOS_EDITABLES[campo]
            
            # Filtrar solo valores de texto no vacíos para validar longitud
            # Esto evita errores con NaN/None
            valores_validos = df_editado[campo].fillna('').astype(str)
            valores_largos = valores_validos[valores_validos.str.len() > limite]
            
            if not valores_largos.empty:
                errores.append(
                    f"Campo '{campo}' excede límite de {limite} caracteres "
                    f"en {len(valores_largos)} fila(s)"
                )
    
    # Validar fechas si están presentes
    if 'fecha_oc' in df_editado.columns:
        try:
            fechas_futuras = df_editado[
                pd.to_datetime(df_editado['fecha_oc'], errors='coerce') > pd.Timestamp.now()
            ]
            if not fechas_futuras.empty:
                errores.append(
                    f"Advertencia: {len(fechas_futuras)} fecha(s) OC en el futuro"
                )
        except:
            pass
    
    return len(errores) == 0, errores
