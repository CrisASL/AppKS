# Guia de Estudio del Codigo - Parte 3

## Capa de Presentacion: UI, Interactividad y Decisiones de Diseno

> Cubre la interfaz Streamlit, el sistema de componentes visuales, la preparacion
> de datos para la UI y las decisiones de diseno del sistema.

---

## Tabla de contenidos

1. [main.py: la interfaz completa](#1-mainpy-la-interfaz-completa)
2. [Sistema de componentes visuales (ui/)](#2-sistema-de-componentes-visuales-ui)
3. [Preparacion de datos para la UI (utils.py)](#3-preparacion-de-datos-para-la-ui-utilspy)
4. [Configuracion del sistema (config.py)](#4-configuracion-del-sistema-configpy)
5. [Modulo de Analisis de Stock (view.py)](#5-modulo-de-analisis-de-stock-viewpy)
6. [Archivos de arranque (run.py y start_app.py)](#6-archivos-de-arranque)
7. [Decisiones de diseno del sistema](#7-decisiones-de-diseno-del-sistema)

---

## 1. main.py: la interfaz completa

`app/main.py` (~2350 lineas) es el nucleo de la interfaz. Contiene toda la logica de
presentacion de Streamlit.

### Estructura interna

```
main.py
|-- Imports y configuracion de pagina (st.set_page_config)
|-- inject_css()                         -> inyecta CSS global del modulo ui/
|-- inicializar_session_state()          -> estado inicial de la sesion
|-- inicializar_base_datos()             -> crear/migrar el schema al arranque
|
|-- crear_sidebar()                      -> navegacion con botones estilizados + item activo
|
|-- pagina_dashboard()                   -> KPIs (kpi_hero + kpi_card), torta interactiva
|                                           con st.pills drill-down, Top 10 productos
|-- pagina_gestion_requisiciones()       -> wrapper de tabla_listado_requisiciones()
|-- tabla_listado_requisiciones()        -> AG Grid editable con filtros y acciones masivas
|
|-- pagina_seguimiento_oc()              -> tabla de compras filtrada con metricas
|-- pagina_analisis_stock()              -> delega a analisis_stock/view.py
|
|-- pagina_configuracion()               -> carga de cubos Excel con selector de hoja
|   |-- cargar_cubo_excel()              -> lectura con cache + selector de hoja
|   |-- _widget_cubo_uploader()          -> widget reutilizable de upload
|   |-- seccion_carga_cubos()            -> orquesta la carga de los 4 cubos
|
|-- main()                               -> routing: sidebar -> pagina activa
```

### Patron de re-render de Streamlit

Streamlit re-ejecuta todo `main.py` de arriba a abajo en cada interaccion. Cada funcion
de pagina construye los widgets de su seccion. El estado entre renders se mantiene en
`st.session_state`. Las escrituras a SQLite siempre van seguidas de
`invalidar_cache()` + `st.rerun()`.

### Dashboard interactivo

El dashboard usa una combinacion de componentes para crear una experiencia interactiva:

1. **KPIs superiores:** una fila de 4 cards usando `kpi_hero()` (indicador principal:
   Total Lineas) y `kpi_card()` (secundarios: Pendientes, OC Generadas, Completadas).
   Estos componentes vienen de `app/ui/styles.py`.

2. **Grafico de torta (Plotly):** muestra la distribucion de estados de OC. Usa
   `plotly.express.pie()` con colores definidos en `config.COLORES_ESTADO`.

3. **Drill-down con st.pills:** debajo de la torta, un selector `st.pills()` muestra
   los estados disponibles. Al seleccionar uno, la columna derecha muestra una tabla
   filtrada con las requisiciones de ese estado (N Req, Descripcion, Cant., N OC,
   Proveedor, Fecha OC, Recibido).

4. **Top 10 Productos:** seccion independiente centrada debajo, con grafico de barras
   horizontal (Plotly) mostrando los productos mas solicitados en los ultimos 60 dias.

### Edicion inline (AG Grid)

La tabla de requisiciones usa `st_aggrid` con `GridOptionsBuilder`:

- Las columnas editables se configuran en `utils.py:obtener_config_columnas_editables()`.
- Columnas de estado usan `agSelectCellEditor` con opciones del catalogo.
- Al presionar "Guardar", se llama `database.py:procesar_ediciones_batch_ui()` que
  detecta que filas cambiaron y actualiza solo esas en SQLite.
- Las filas tienen colores por estado usando `cellStyle` de AG Grid.

### Sidebar con navegacion estilizada

La navegacion usa botones estilizados via CSS (no el menu nativo de Streamlit):

- Logo con gradiente verde y nombre de la app.
- Info de usuario y sucursal.
- Botones de navegacion con hover effect.
- La pagina activa se resalta con un indicador visual (`ks-nav-active-item`):
  borde izquierdo verde + fondo semitransparente.

### Carga de cubos con selector de hoja

La funcion `cargar_cubo_excel()` implementa un flujo de 3 pasos:

1. El usuario sube el archivo Excel con `st.file_uploader`.
2. Se muestra un `st.selectbox` con las hojas disponibles del libro. La hoja elegida
   se persiste en `configuracion` con clave `hoja_cubo_{tipo}`.
3. La clave de cache combina hash del archivo + nombre de hoja, de modo que cambiar
   la hoja fuerza una nueva lectura.

---

## 2. Sistema de componentes visuales (ui/)

El modulo `app/ui/` (introducido en v1.8.0) centraliza el sistema de diseno visual.

### Arquitectura

```
app/ui/
|-- __init__.py    -> re-exporta las 7 funciones publicas
|-- styles.py      -> CSS global + helpers HTML (~333 lineas)
```

`__init__.py` exporta: `inject_css`, `kpi_hero`, `kpi_card`, `empty_state`,
`section_label`, `open_card`, `close_card`.

### Paleta de colores

El diseno usa un tema oscuro con acento verde (teal):

| Variable | Valor | Uso |
|----------|-------|-----|
| `_BG_PAGE` | `#0e1117` | Fondo de pagina (dark de Streamlit) |
| `_BG_CARD` | `#161f2e` | Fondo de cards y contenedores |
| `_BG_CARD_HOVER` | `#1c2840` | Hover en cards |
| `_BORDER_CARD` | `rgba(255,255,255,0.06)` | Bordes sutiles |
| `_TEXT_PRIMARY` | `#f0f2f6` | Texto principal |
| `_TEXT_MUTED` | `#8b95a8` | Texto secundario |
| `_TEXT_LABEL` | `#6b7280` | Labels y seccion headers |
| `_TEAL` | `#10b981` | Acento principal |
| `_TEAL_DARK` | `#059669` | Acento oscuro (gradientes) |

### Componentes disponibles

**`inject_css()`**
Inyecta el CSS global una vez al arrancar la app. Se llama despues de `st.set_page_config`.
El CSS cubre: sidebar (logo, usuario, navegacion, item activo), KPI cards (hero y flat),
cards genericas, empty states y ajustes generales del layout.

**`kpi_hero(label, value, icon, help_text)`**
Card KPI grande con gradiente verde. Pensada para el indicador principal del dashboard.
Ocupa mas espacio visual y tiene un efecto decorativo radial de fondo.

**`kpi_card(label, value, icon, help_text)`**
Card KPI flat (fondo oscuro sin gradiente). Para indicadores secundarios que acompanan
al hero. Tiene el mismo layout pero visualmente mas discreto.

**`empty_state(icon, title, subtitle)`**
Placeholder para secciones sin datos. Muestra un icono grande atenuado, un titulo y
un subtitulo opcional. Se usa cuando no hay cubos cargados o no hay resultados.

**`section_label(text)`**
Etiqueta de seccion en el sidebar. Texto en mayusculas, tamano reducido, color muted.
Separa visualmente los grupos de navegacion.

**`open_card()` / `close_card()`**
Abren y cierran un contenedor card generico (fondo `_BG_CARD`, borde sutil, bordes
redondeados). Se usan para agrupar contenido visualmente.

### Patron de inyeccion CSS

Todo el CSS se define como un string constante `_CSS` dentro de `styles.py`. Se inyecta
via `st.markdown(_CSS, unsafe_allow_html=True)`. Este patron permite:

- Definir estilos una sola vez en un lugar centralizado.
- Los helpers HTML (`kpi_hero`, etc.) usan clases CSS definidas en `_CSS`.
- No se necesitan archivos CSS externos ni temas de Streamlit.

---

## 3. Preparacion de datos para la UI (utils.py)

`app/utils.py` (~1289 lineas) actua como capa intermedia entre los DataFrames crudos
de SQLite y los componentes de la UI.

### Validacion de cubos Excel

Funciones que validan la estructura de cada cubo antes de persistir:

| Funcion | Cubo | Valida |
|---------|------|--------|
| `validar_cubo_requisiciones(df)` | Requisiciones | Columnas criticas + formato de datos |
| `validar_cubo_compras(df)` | Compras | Columnas criticas |
| `validar_cubo_ventas(df)` | Ventas | Columnas criticas |
| `validar_cubo_inventario(df)` | Inventario | Columnas criticas |
| `validar_filas_requisiciones(df)` | Requisiciones | Validacion a nivel de fila |
| `validar_estructura_cubo(df, cols)` | Generico | Verifica columnas presentes |

### Preparacion para AG Grid

**`preparar_df_para_edicion_segura(df)`**
Toma el DataFrame crudo de SQLite y lo transforma al formato exacto que espera AG Grid:

1. Reordena columnas: primero las visibles en la UI, al final las ocultas.
2. Normaliza tipos:
   - Fechas: convierte a string con formato YYYY-MM-DD (AG Grid no maneja `datetime`).
   - `estado_envio`: `fillna("No Enviado").astype(str)`.
   - Campos de texto: `fillna("")`.
3. Retorna el DataFrame listo para AG Grid.

**`obtener_config_columnas_editables()`**
Devuelve la configuracion completa del AG Grid: columnas visibles, anchos, editabilidad,
`SelectboxColumn` para dropdowns. Define `estado_envio` como `agSelectCellEditor` con
opciones `ESTADOS_ENVIO`.

**`validar_ediciones_antes_de_guardar(df_editado)`**
Valida el DataFrame editado por el usuario antes de guardar:
- Campos editados estan en `CAMPOS_EDITABLES_UI` (whitelist).
- Valores de `estado_envio` estan en `ESTADOS_ENVIO`.
- Textos no superan `LIMITES_CAMPOS_EDITABLES`.
- Retorna lista de errores para mostrar en la UI.

### Funciones auxiliares

| Funcion | Proposito |
|---------|-----------|
| `get_state(key, default)` | Lee `st.session_state` con fallback |
| `set_state(key, value)` | Escribe en `st.session_state` |
| `reset_filters(group)` | Resetea un grupo de filtros a defaults |
| `cargar_excel_con_selector_hoja(archivo, tipo)` | Lectura Excel con selector de hoja |
| `calcular_saldo_pendiente(cantidad, recibida)` | Calculo de saldo |
| `determinar_estado_por_saldo(saldo)` | Sugiere estado segun saldo |
| `formatear_fecha(fecha_str)` | Formatea fecha a visual |
| `formatear_numero(n, moneda)` | Formatea numero con separador de miles |
| `obtener_emoji_estado(estado)` | Emoji por estado |
| `obtener_color_estado(estado)` | Color hex por estado |
| `preparar_dataframe_para_exportar(df)` | Prepara DataFrame para exportacion Excel |
| `aplicar_formato_excel(writer, df)` | Aplica formato a Excel exportado |
| `generar_alertas_oc(df)` | Genera alertas por OC sin recepcion |
| `obtener_productos_criticos(df)` | Productos con stock critico |

---

## 4. Configuracion del sistema (config.py)

`app/config.py` (~383 lineas) centraliza todas las constantes del dominio.

### Columnas de cubos Excel

Para cada cubo se definen dos listas:
- `COLUMNAS_*` — todas las columnas esperadas (para referencia).
- `COLUMNAS_CRITICAS_*` — las minimas obligatorias (para validacion).

| Cubo | Total columnas | Criticas |
|------|---------------|----------|
| Requisiciones | 19 (`COLUMNAS_REQ`) | 5 (`FEmision, NumReq, CodProd, DesProd, TALCA`) |
| Compras | 20 (`COLUMNAS_COMPRAS`) | 5 (`NumOC, Proveedor, CodProd, DesProd, FechaOC`) |
| Ventas | 14 (`COLUMNAS_VENTAS`) | 2 (`CodProd, DesProd`) |
| Inventario | 11 (`COLUMNAS_INVENTARIO`) | 3 (`CodProd, KS TALCA, Total general`) |

### Catalogos de estados

| Catalogo | Valores | Uso |
|----------|---------|-----|
| `ESTADOS_OC` | 8 estados | Estado de la OC: Pendiente, OC Generada, En Transito, Guia de Despacho, Recepcion Parcial, Recepcion Completa, Cancelada, No se compra |
| `ESTADOS_REQ` | 4 estados | Estado manual de la requisicion: Pendiente, Recepcionada, Parcial, No se compra |
| `ESTADOS_ENVIO` | 2 estados | Estado de envio: No Enviado, Enviado |

### Sucursales y bodegas

- `BODEGAS` — 9 bodegas (como aparecen en cubos de stock).
- `COLUMNAS_CANTIDAD_SUCURSAL` — mapeo sucursal -> columna de cantidad en cubo REQ.
- `SUCURSAL_A_BODEGA` — mapeo sucursal -> bodega de stock (5 sucursales).
- `SUCURSALES_DISPONIBLES` — Talca, Rancagua, Vina del Mar.
- `SUCURSAL_ASIGNADA` — "Talca" (usuario actual).
- `BODEGA_ASIGNADA` — "KS TALCA".

### Edicion UI

- `CAMPOS_EDITABLES_UI` — 9 campos que el usuario puede modificar desde la tabla:
  `proveedor, oc, n_guia, fecha_oc, observacion, detalle, oc_enviada, estado_envio, estado_req`.
- `CAMPOS_NO_EDITABLES_UI` — 11 campos protegidos que solo se modifican via funciones
  backend: `id, numreq, codprod, desprod, cantidad, sucursal_destino, cant_recibida,
  saldo_pendiente, estado_oc, fecha_creacion, fecha_modificacion`.
- `LIMITES_CAMPOS_EDITABLES` — limites de caracteres para 5 campos de texto.

### Alertas y umbrales

| Constante | Valor | Descripcion |
|-----------|-------|-------------|
| `DIAS_ALERTA_OC_SIN_RECEPCION` | 45 | Dias sin recepcion para alerta |
| `DIAS_ALERTA_REQ_SIN_OC` | 15 | Dias sin OC asignada para alerta |
| `DIAS_ALERTA_RECEPCION_PARCIAL` | 30 | Dias con recepcion parcial para alerta |
| `STOCK_CRITICO` | 10 | Unidades minimas para alerta de stock |

### Interfaz y visualizacion

- `COLORES_ESTADO` — 12 colores hex para estados (incluye alias del ERP).
- `EMOJIS_ESTADO` — 8 emojis por estado.
- `PAGE_CONFIG` — configuracion de `st.set_page_config` (titulo, icono, layout wide).
- `MENU_OPTIONS` — 5 opciones del menu de navegacion.

---

## 5. Modulo de Analisis de Stock (view.py)

`app/modules/analisis_stock/view.py` (~232 lineas) renderiza la seccion de Analisis
de Stock separando la vista del calculo (que esta en `service.py`).

### Funcion principal: `render(cubo_inventario, cubo_ventas)`

**Flujo:**

1. **Validacion defensiva:** verifica que ambos cubos existan y no esten vacios.
   Si faltan, muestra un mensaje de error orientando al usuario a Configuracion.

2. **Metricas resumen:** `_metricas_resumen(df)` muestra 2 filas de metricas:
   - Estado de stock: Total productos, Falta de stock, Stock optimo, Sobrestock.
   - Rotacion: Alta rotacion, Rotacion media, Baja rotacion.

3. **Filtro de busqueda:** `st.text_input` para buscar por descripcion de producto.

4. **Controles de ordenamiento y filtro:** 3 columnas con:
   - Ordenar por: 6 opciones (ventas, stock, codigo, etc.).
   - Filtrar por estado de stock: multiselect.
   - Filtrar por rotacion: multiselect.

5. **Tabla de resultados:** `st.dataframe` con configuracion de columnas y emojis
   por estado y rotacion.

6. **Seccion de ayuda:** expander con la metodologia de calculo.

### Separacion service/view

- `service.py` calcula: recibe DataFrames crudos, retorna DataFrame con analisis.
- `view.py` renderiza: recibe DataFrames crudos, llama a service, muestra resultados.

Esta separacion permite testear el calculo sin montar la UI.

---

## 6. Archivos de arranque

### `run.py` (14 lineas)

Punto de entrada para Streamlit. Su trabajo es agregar la raiz del proyecto al
`sys.path` y delegar a `app.main` usando `runpy.run_module`:

```python
import runpy
root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))
runpy.run_module('app.main', run_name='__main__')
```

Se ejecuta con: `streamlit run run.py`. No contiene logica de aplicacion.

### `start_app.py` (506 lineas)

Launcher para usuarios finales. Funciona como el programa que ejecuta el usuario
(o como el `.exe` generado con PyInstaller).

**Flujo de ejecucion:**

1. Detectar si corre como `.exe` (`sys.frozen`) o como script Python.
2. Establecer el directorio de trabajo en la raiz del proyecto.
3. Verificar que `run.py` existe.
4. Buscar Python: primero en el venv local, luego en PATH, luego en rutas absolutas
   comunes de Windows.
5. Si no existe venv, lo crea e instala dependencias desde `requirements.txt`.
6. Lanzar: `venv\Scripts\python.exe -m streamlit run run.py`.
7. Esperar el arranque y abrir el navegador en `http://localhost:8501`.
8. Esperar a que el proceso termine (`proc.wait()`).

**Manejo de errores:** si el venv no existe o Streamlit no arranca, muestra un dialogo
con `tkinter.messagebox` (necesario porque el `.exe` se ejecuta sin consola).

**Generacion del .exe:** `pyinstaller --onefile --noconsole start_app.py --name AppKS`
o usando `build.bat`.

---

## 7. Decisiones de diseno del sistema

### Por que SQLite en lugar de otro motor

**Problema:** persistir datos estructurados con relaciones, transacciones y SQL, pero
distribuir como aplicacion de escritorio local sin infraestructura de servidor.

**Alternativas descartadas:**
- PostgreSQL / MySQL: requieren servidor, configuracion, credenciales. Inviable para
  distribucion local sin soporte IT.
- CSV/Excel/JSON: sin transacciones, sin constraints, sin triggers.

**Ventajas de SQLite:**
- Un solo archivo (`ks_requisiciones.db`).
- Transacciones ACID, triggers, constraints, indices.
- Sin instalacion (incluida en Python stdlib).
- WAL mode para lecturas concurrentes sin bloquear escrituras.
- Rendimiento suficiente para el volumen (miles, no millones de filas).

---

### Por que Streamlit como interfaz

**Problema:** interfaz web con tablas editables, filtros, graficos y formularios,
pero el tiempo de desarrollo es limitado y el desarrollador no tiene experiencia en
frameworks web frontend.

**Alternativas descartadas:**
- Flask + HTML/CSS/JS: mayor control, pero semanas de trabajo adicional.
- PyQt / tkinter: menos atractivas visualmente, mas complejas de distribuir.

**Ventajas de Streamlit:**
- Interfaz web completa escribiendo solo Python.
- Componentes listos: tablas, graficos, filtros, uploads.
- Compatible con AG Grid para tablas editables avanzadas.
- Distribucion simple: empaquetable con PyInstaller.

**Desventaja asumida:** el modelo de re-ejecucion completa requiere disenar con cuidado
el cache (`st.cache_data`, `st.cache_resource`).

---

### Por que estados TEXT en lugar de booleanos

**Problema:** el campo `oc_enviada` original era INTEGER (0/1), pero al interactuar
con AG Grid, pandas y SQLite al mismo tiempo surgen conflictos de tipo: AG Grid lo
renderiza como checkbox, pandas lo lee como `float64` si hay nulos, SQLite lo guarda
como entero.

**Solucion:** reemplazar `oc_enviada INTEGER` por `estado_envio TEXT DEFAULT 'No Enviado'`.

**Ventajas:**
- Un string es el mismo tipo en SQLite, pandas y AG Grid: sin conversiones.
- AG Grid puede renderizarlo como `agSelectCellEditor` con opciones del catalogo.
- Extensible: agregar un tercer estado solo requiere una entrada mas en `ESTADOS_ENVIO`.
- El valor DEFAULT es legible en SQL sin lookups.

---

### Por que sincronizaciones SQL en lugar de loops Python

**Problema:** al cargar el cubo de compras, hay que actualizar el estado de OC en cada
requisicion que tenga OC asignada. Un loop Python ejecutaria N queries para N requisiciones.

**Solucion:** un unico `UPDATE ... FROM compras WHERE oc = num_oc AND codprod = codprod`.

**Ventajas:**
- Una sola pasada sobre ambas tablas usando indices compuestos.
- SQLite optimiza el plan de ejecucion globalmente.
- El trigger se dispara automaticamente por cada fila actualizada.
- Codigo conciso y auditable.

---

### Por que un modulo ui/ separado

**Problema:** el CSS inline y los helpers HTML estaban dispersos en `main.py`, haciendo
dificil mantener consistencia visual y aumentando el tamano del archivo.

**Solucion:** centralizar todo el CSS y los componentes visuales en `app/ui/styles.py`.

**Ventajas:**
- Un solo lugar para la paleta de colores y el sistema de diseno.
- Los helpers (`kpi_hero`, `kpi_card`, etc.) son reutilizables en cualquier pagina.
- `main.py` se enfoca en logica de routing y datos, no en HTML/CSS.
- Cambiar el tema visual solo requiere modificar `styles.py`.

---

### Por que separar service.py y view.py en analisis_stock

**Problema:** la logica de calculo de stock y la visualizacion estaban acopladas en
una unica seccion de `main.py`.

**Solucion:** modulo independiente con `service.py` (calculo) y `view.py` (renderizado).

**Ventajas:**
- Se puede testear el calculo sin montar la UI completa.
- `view.py` puede cambiar la visualizacion sin tocar la logica de calculo.
- El modulo es auto-contenido: se puede mover o replicar facilmente.
