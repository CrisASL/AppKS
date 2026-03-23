# Guía de Estudio del Código — AppKS

> Documento orientado a que el desarrollador (Cristian Salas) comprenda rápidamente la
> arquitectura, flujo de datos y lógica principal del proyecto.
> No es documentación de usuario final.

---

## Tabla de contenidos

1. [Visión general del sistema](#1-visión-general-del-sistema)
2. [Flujo de datos del sistema](#2-flujo-de-datos-del-sistema)
3. [Estructura del proyecto](#3-estructura-del-proyecto)
4. [Explicación de archivos clave](#4-explicación-de-archivos-clave)
5. [Explicación de los servicios del sistema](#5-explicación-de-los-servicios-del-sistema)
6. [Explicación de las tablas principales en SQLite](#6-explicación-de-las-tablas-principales-en-sqlite)
7. [Lógica de negocio importante](#7-lógica-de-negocio-importante)
8. [Conceptos técnicos utilizados en el proyecto](#8-conceptos-técnicos-utilizados-en-el-proyecto)
9. [Funciones importantes del sistema](#9-funciones-importantes-del-sistema)
10. [Decisiones de diseño del sistema](#10-decisiones-de-diseño-del-sistema)

---

## 1. Visión general del sistema

### Qué problema resuelve

AppKS es un sistema de gestión operativa para **KS Seguridad Industrial, Sucursal Talca**.
El problema central que resuelve es la falta de visibilidad y trazabilidad en el proceso
de compras operativas de la sucursal:

- Los operadores generaban requisiciones de productos en Softland (ERP de la empresa), pero
  no tenían forma de saber qué había pasado con cada requisición una vez emitida.
- Las órdenes de compra existían en Softland, pero la relación entre una requisición y su
  OC correspondiente era manual, sin registro ni historial.
- Los datos de ventas, stock e inventario estaban dispersos en cubos de Excel exportados
  desde Softland, sin una vista consolidada.

AppKS centraliza toda esa información en una base de datos local (SQLite) y la presenta
mediante una interfaz web local (Streamlit) que permite gestionar el ciclo completo:
**requisición → asignación de OC → recepción → análisis de stock**.

### Módulos principales

| Módulo | Ruta en menú | Propósito |
|--------|-------------|-----------|
| **Dashboard** | `📊 Dashboard` | KPIs del estado actual de requisiciones y OC |
| **Gestión Requisiciones** | `📋 Gestión Requisiciones` | Tabla editable inline: asignar OC, proveedor, estado, notas |
| **Seguimiento OC** | `🛒 Seguimiento OC` | Vista consolidada de órdenes de compra sincronizadas desde Softland |
| **Análisis Stock** | `📈 Análisis Stock` | Cruce de inventario × ventas para detectar productos críticos |
| **Configuración** | `⚙️ Configuración` | Carga de cubos Excel, ajustes del sistema |

---

## 2. Flujo de datos del sistema

El sistema gira en torno a **cubos Excel** exportados desde Softland (ERP). Cada cubo
representa un conjunto de datos del negocio en un punto en el tiempo. El flujo completo es:

```
Excel (Softland)
      │
      ▼
  cache.py  ──── cargar_excel()  ────►  DataFrame en memoria
      │                                      │
      │                                      ▼
      │                           Validación de columnas
      │                           (config.COLUMNAS_CRITICAS_*)
      │                                      │
      ▼                                      ▼
  services/                         Transformación / normalización
  ├── compras_service.py             (pandas: fillna, rename, dtype cast)
  └── ventas_inventario_service.py         │
      │                                    ▼
      ▼                               database.py
  Carga a SQLite                      ├── INSERT OR IGNORE  (requisiciones)
  ├── UPSERT por NumOC+CodProd        ├── UPSERT por clave única (compras)
  ├── Hash MD5 (ventas/inventario)    └── Reemplazo total (ventas/inventario)
      │
      ▼
  SQLite  (data/ks_requisiciones.db)
  ├── tabla: requisiciones
  ├── tabla: compras
  ├── tabla: ventas
  └── tabla: inventario
      │
      ▼
  cache.py  ──── get_table()  ────►  DataFrame cacheado (st.cache_data)
      │
      ▼
  app/main.py  ──── Streamlit UI
  ├── Dashboard    (KPIs desde obtener_kpis_dashboard)
  ├── Gestión Req  (AG Grid editable inline)
  ├── Seguimiento  (tabla compras filtrada)
  └── Análisis     (analisis_stock/service.py → tabla calculada)
```

### Descripción de cada etapa

**Etapa 1 — Exportación desde Softland**
El usuario exporta manualmente los cubos desde Softland en formato `.xlsx`:
- Cubo de Requisiciones: lista de requisiciones emitidas por la sucursal.
- Cubo de Compras: órdenes de compra generadas por el departamento de compras central.
- Cubo de Ventas: histórico de ventas mensuales por producto.
- Cubo de Inventario: stock actual por bodega y costo unitario.

**Etapa 2 — Carga del archivo en la UI**
El usuario sube el archivo desde la sección Configuración. `cache.py:cargar_excel()` lee el
archivo con `pandas.read_excel`. Para los cubos de ventas e inventario (que son pivot tables
de Softland con encabezado desplazado), detecta automáticamente la fila del encabezado
buscando la celda `CodProd`.

**Etapa 3 — Validación de columnas críticas**
Antes de persistir cualquier dato, se valida que el DataFrame contenga las columnas
definidas en `config.COLUMNAS_CRITICAS_*`. Si faltan columnas obligatorias, se muestra un
error al usuario y se detiene la carga.

**Etapa 4 — Transformación y normalización**
Los servicios aplican transformaciones específicas por tipo de cubo:
- Renombrar columnas al esquema interno (ej. `"TALCA"` → `"cantidad"`).
- Cast de tipos (fechas, enteros, texto).
- Relleno de nulos con valores por defecto.
- Generación de hash MD5 (ventas e inventario) para control de cambios.

**Etapa 5 — Persistencia en SQLite**
Dependiendo del tipo de datos:
- Requisiciones: `INSERT OR IGNORE` (nunca sobreescribe datos editados manualmente).
- Compras: `INSERT OR REPLACE` con detección de cambios por campo.
- Ventas/Inventario: reemplazo total de la tabla si el hash MD5 cambió.

**Etapa 6 — Lectura con caché**
`cache.py:get_table()` consulta SQLite con `pd.read_sql` y cachea el resultado con
`st.cache_data`. Todas las pantallas leen desde este caché. Tras cualquier escritura,
`invalidar_cache()` fuerza una nueva lectura en el próximo render.

**Etapa 7 — Presentación en la UI**
`app/main.py` toma los DataFrames del caché y los presenta en la interfaz. La tabla de
Gestión de Requisiciones usa AG Grid con columnas editables inline. El Dashboard calcula
KPIs con `obtener_kpis_dashboard()`. El Análisis de Stock cruza inventario × ventas en
`analisis_stock/service.py`.

---

## 3. Estructura del proyecto

```
AppKS/
├── run.py                   # Punto de entrada para Streamlit (streamlit run run.py)
├── start_app.py             # Launcher para distribución como .exe (PyInstaller)
├── AppKS.exe                # Ejecutable generado por PyInstaller (no en git)
├── build.bat                # Script para regenerar AppKS.exe
├── requirements.txt         # Dependencias Python del proyecto
│
├── app/                     # Paquete principal de la aplicación
│   ├── __init__.py
│   ├── main.py              # Toda la interfaz Streamlit (~2229 líneas)
│   ├── database.py          # Esquema, CRUD, KPIs, migraciones (~2368 líneas)
│   ├── utils.py             # Preparación de datos para UI (~1119 líneas)
│   ├── config.py            # Constantes y configuración del sistema
│   ├── cache.py             # Caché de conexión y DataFrames (st.cache_*)
│   │
│   ├── services/            # Carga de datos desde cubos Excel a SQLite
│   │   ├── compras_service.py           # UPSERT de compras (~976 líneas)
│   │   └── ventas_inventario_service.py # Hash MD5 + carga ventas/inventario (~239 líneas)
│   │
│   └── modules/             # Módulos funcionales de la app
│       └── analisis_stock/
│           └── service.py   # Cálculo de análisis de stock (~229 líneas)
│
├── data/
│   └── ks_requisiciones.db  # Base de datos SQLite (no en git)
│
├── docs/                    # Documentación técnica del proyecto
│   ├── ARQUITECTURA.md
│   ├── CONTROL_DE_VERSIONES.md
│   ├── DECISIONES_TECNICAS.md
│   └── GUIA_ESTUDIO_CODIGO.md  ← este archivo
│
├── backups/                 # Backups automáticos de la DB
├── exports/                 # Archivos exportados desde la UI
├── logs/                    # Logs de operaciones
├── examples/                # Archivos de ejemplo para testing
└── migrar_db_simple.py      # Script de migración puntual (legacy)
```

### Responsabilidad de cada directorio/archivo clave

| Archivo / Carpeta | Responsabilidad |
|-------------------|----------------|
| `run.py` | Punto de entrada para Streamlit; agrega la raíz al `sys.path` y ejecuta `app.main` |
| `start_app.py` | Launcher independiente: detecta el venv, lanza Streamlit y abre el navegador |
| `app/main.py` | Toda la lógica de presentación: routing de páginas, renderizado de tablas y formularios |
| `app/database.py` | Única fuente de verdad para el esquema de la DB: crea tablas, triggers, índices, migraciones y todas las operaciones CRUD |
| `app/utils.py` | Funciones de preparación de datos para la UI: reordenamiento de columnas, normalización de tipos, configuración del AG Grid |
| `app/config.py` | Constantes del dominio: columnas de cubos, estados posibles, rutas, límites de campos |
| `app/cache.py` | Abstracción del caché: conexión SQLite persistente (`cache_resource`) y DataFrames cacheados (`cache_data`) |
| `app/services/` | Servicios de carga: traducen DataFrames de cubos Excel a filas en SQLite |
| `app/modules/analisis_stock/` | Módulo independiente de análisis: calcula alertas de stock y rotación |
| `data/` | Base de datos SQLite y archivos de datos locales (excluidos de git) |
| `docs/` | Documentación técnica del proyecto |

---

## 4. Explicación de archivos clave

### `run.py`

```python
# run.py — 14 líneas
import runpy
root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))
runpy.run_module('app.main', run_name='__main__')
```

**Propósito:** es el único archivo que Streamlit ejecuta directamente.
Su trabajo es garantizar que el paquete `app` sea importable desde cualquier directorio
de trabajo, agregando la raíz del proyecto al `sys.path`. Luego delega completamente la
ejecución a `app.main` usando `runpy.run_module` (que ejecuta el módulo como si fuera
el script principal, sin necesidad de imports relativos complicados).

**Cómo se usa:**

```bash
streamlit run run.py
```

No contiene lógica de aplicación. Es solo un adaptador de arranque.

---

### `start_app.py`

**Propósito:** launcher para usuarios finales que no tienen Streamlit instalado globalmente.
Funciona como el programa que ejecuta el usuario (o como el `.exe` generado con PyInstaller).

**Flujo de ejecución:**

```
1. Detectar si corre como .exe (sys.frozen) o como script Python
2. Establecer el directorio de trabajo (os.chdir) en la raíz del proyecto
3. Verificar que run.py existe en esa carpeta
4. Verificar que venv/Scripts/python.exe existe
5. Lanzar: venv\Scripts\python.exe -m streamlit run run.py
6. Esperar 4 segundos (tiempo de arranque de Streamlit)
7. Verificar que el proceso sigue corriendo
8. Abrir el navegador en http://localhost:8501
9. Esperar a que el proceso termine (proc.wait())
```

**Manejo de errores:** si el venv no existe o Streamlit no arranca, muestra un diálogo
de error con `tkinter.messagebox`. Esto es necesario porque el `.exe` se ejecuta sin
consola (`--noconsole` en PyInstaller), entonces no hay stdout donde mostrar errores.

**Cómo se genera el .exe:**

```bat
pyinstaller --onefile --noconsole start_app.py --name AppKS
```

O usando `build.bat` que automatiza ese comando.

---

### `app/main.py`

**Propósito:** es el núcleo de la interfaz. Contiene toda la lógica de presentación de
Streamlit: ~2229 líneas organizadas en funciones por página/sección.

**Estructura interna:**

```
main.py
├── Imports y configuración de página (st.set_page_config)
├── inicializar_base_datos()           → llamado al arranque para crear/migrar el schema
│
├── pagina_dashboard()                 → KPIs, gráfico de barras, tabla resumen
├── pagina_configuracion()             → Subir cubos Excel, ejecutar cargas
│
├── tabla_listado_requisiciones()      → ⭐ función central: AG Grid editable con filtros,
│                                         botones de acción masiva, guardado batch
├── pagina_requisiciones()             → wrapper de tabla_listado_requisiciones()
│
├── pagina_seguimiento_oc()            → tabla de compras filtrada y agrupada
├── pagina_analisis_stock()            → llama a calcular_analisis_stock() y renderiza
│
└── main() / if __name__ == "__main__" → routing: sidebar → página activa
```

**Patrón de re-render de Streamlit:**
Streamlit re-ejecuta todo `main.py` de arriba a abajo en cada interacción del usuario.
Cada función de página construye los widgets de su sección. El estado entre renders se
mantiene en `st.session_state` (diccionario persistente por sesión). Las escrituras a
SQLite siempre van seguidas de `invalidar_cache()` + `st.rerun()` para que la siguiente
ejecución lea datos frescos.

**Edición inline (AG Grid):**
La tabla de requisiciones usa `st_aggrid` con `GridOptionsBuilder`. Las columnas editables
se configuran en `utils.py:obtener_config_columnas_editables()`. Al presionar "Guardar",
se llama `database.py:procesar_ediciones_batch_ui()` que detecta qué filas cambiaron y
actualiza solo esas en SQLite.

---

### `app/database.py`

**Propósito:** es la capa de datos completa del sistema. Todo acceso a SQLite (lectura,
escritura, esquema, migraciones) pasa por este archivo.

**Estructura interna (~2368 líneas):**

```
database.py
├── inicializar_base_datos()          → CREATE TABLE IF NOT EXISTS + triggers + índices
├── migrar_base_datos_existente()     → migraciones idempotentes con PRAGMA table_info
│
├── ── Carga de cubos ──
├── cargar_requisiciones_desde_cubo() → INSERT OR IGNORE desde DataFrame del cubo REQ
├── (compras_service llama a su propio módulo)
│
├── ── KPIs ──
├── obtener_kpis_dashboard()          → agrupaciones con pandas sobre get_table()
│
├── ── CRUD operativo ──
├── actualizar_requisicion_desde_ui() → UPDATE con whitelist de campos válidos
├── procesar_ediciones_batch_ui()     → diff DataFrame original vs editado → batch UPDATE
├── registrar_recepcion()             → actualiza cant_recibida + dispara recálculo saldo
│
├── ── Sincronización REQ ↔ OC ──
├── actualizar_gestion_desde_compras() → JOIN SQL puro: OC → REQ por CodProd
│
└── ── Helpers ──
    └── _ejecutar_con_conexion_propia() → abre conexión dedicada para escrituras
```

**Por qué database.py es tan grande:**
Centralizar toda la lógica de datos en un solo archivo evita que la lógica de negocio
se disperse entre la UI (`main.py`) y los servicios. La UI llama funciones de alto nivel
y no sabe nada de SQL. Esta separación hace más fácil testear la lógica de datos de forma
independiente.

**Conexiones: lectura vs escritura:**
- Lectura: usa `cache.py:get_connection()` (conexión compartida, `cache_resource`).
- Escritura: abre una conexión nueva y dedicada para cada operación. Esto evita problemas
  de concurrencia y bloqueos en SQLite con WAL mode.

---

### `app/utils.py`

**Propósito:** funciones de preparación de datos para la capa de presentación. Actúa como
capa intermedia entre los DataFrames crudos de SQLite y el AG Grid de la UI.

**Funciones principales:**

```
utils.py
├── preparar_df_para_edicion_segura()
│   → Reordena columnas, normaliza tipos (fechas como str, bools como str),
│     aplica fillna específico por tipo de campo, garantiza que AG Grid
│     no encuentre tipos inesperados.
│
├── obtener_config_columnas_editables()
│   → Devuelve la configuración completa del AG Grid:
│     columnas visibles, anchos, editabilidad, SelectboxColumn para dropdowns.
│     Define estado_envio como agSelectCellEditor con opciones ESTADOS_ENVIO.
│
└── validar_ediciones_antes_de_guardar()
    → Recibe el DataFrame editado por el usuario y valida:
      - Que los campos editados estén en CAMPOS_EDITABLES_UI (whitelist).
      - Que los valores de estado_envio estén en ESTADOS_ENVIO.
      - Que los textos no superen LIMITES_CAMPOS_EDITABLES.
      Retorna lista de errores para mostrar en la UI antes de guardar.
```

**Por qué utils.py existe separado de main.py:**
La configuración del AG Grid y la normalización de tipos son operaciones de preparación
de datos, no de presentación. Separarlas de `main.py` permite reutilizarlas y testearlas
sin montar la UI completa. También mantiene `main.py` enfocado en el routing y la
estructura de páginas.

---
## 5. Explicación de los servicios del sistema
### `app/services/compras_service.py`
**Responsabilidad:** carga el cubo de compras desde un DataFrame de Excel a la tabla
`compras` en SQLite, y ejecuta la sincronización automática hacia la tabla `requisiciones`.
**Funciones clave:**
- `crear_tabla_compras()` — crea la tabla `compras` con su esquema completo, índices y
  triggers de `total_linea`. Idempotente.
- `normalizar_dataframe_compras(df)` — renombra columnas del cubo Excel al esquema
  interno, normaliza tipos (numéricos, fechas con detección de serial Excel), rellena nulos.
- `cargar_compras_desde_dataframe(df, conn)` — UPSERT principal. Para cada fila del cubo:
  verifica si ya existe por `(num_oc, codprod)`, ejecuta `INSERT ... ON CONFLICT DO UPDATE`
  solo si detecta cambios. Retorna conteo de insertados/actualizados/sin cambios.
- `actualizar_gestion_desde_compras(conn)` — ejecuta un único `UPDATE ... FROM compras`
  para propagar estado de OC, cantidades recibidas y bodega a las requisiciones que tengan
  OC asignada. Ver sección 7 para el SQL completo.
- `ejecutar_proceso_completo_compras(df)` — orquesta los dos pasos anteriores en secuencia
  y retorna un resumen estructurado del proceso.
**Notas importantes:**
- `cantidad_solicitada` nunca se actualiza en el UPSERT; solo campos operativos
  (`cantidad_recibida`, `estado_linea`, `precio_compra`, etc.).
- El trigger `calcular_total_linea_update` recalcula `total_linea` automáticamente tras
  cada UPDATE, sin necesidad de calcularlo en Python.
---
### `app/services/ventas_inventario_service.py`
**Responsabilidad:** persiste los cubos de ventas e inventario en SQLite con control de
versiones por hash MD5, evitando reprocesar archivos que no cambiaron.
**Funciones clave:**
- `calcular_hash_archivo(archivo)` — calcula el MD5 del contenido del `UploadedFile` de
  Streamlit (`archivo.getvalue()`). Retorna el hash hexadecimal como string.
- `obtener_hash_guardado(nombre_cubo)` — consulta la tabla `archivos_cargados` para
  obtener el último hash registrado del cubo (`'ventas'` o `'inventario'`).
- `actualizar_hash(nombre_cubo, hash_archivo)` — guarda o actualiza el hash en
  `archivos_cargados` usando `INSERT OR REPLACE`.
- `guardar_ventas(df)` — escribe el DataFrame a la tabla `ventas` con
  `df.to_sql(..., if_exists="replace")`. Llama `invalidar_cache()` al terminar.
- `guardar_inventario(df)` — igual que `guardar_ventas` pero para la tabla `inventario`.
**Patrón de uso en la UI:**
```python
hash_nuevo = calcular_hash_archivo(archivo_subido)
hash_anterior = obtener_hash_guardado("ventas")
if hash_nuevo != hash_anterior:
    guardar_ventas(df_procesado)
    actualizar_hash("ventas", hash_nuevo)
    st.success("Ventas actualizadas")
else:
    st.info("El archivo no cambió, no se reprocesó")
Este patrón evita reemplazar toda la tabla en cada recarga de página de Streamlit, que
de otro modo ocurriría porque Streamlit re-ejecuta todo el script en cada interacción.
---
app/modules/analisis_stock/service.py
Responsabilidad: calcula el análisis de cobertura y rotación de stock cruzando el
cubo de inventario (stock actual en KS TALCA) con el cubo de ventas (histórico mensual).
Funciones clave:
- _preparar_inventario(df_inventario) — extrae las columnas CodProd, DesProd y
  KS TALCA del cubo de inventario. Renombra a codprod, desprod, stock_actual.
- _preparar_ventas(df_ventas) — normaliza el cubo de ventas: mantiene codprod,
  desprod y los meses presentes como columnas numéricas.
- calcular_analisis_stock(df_inventario, df_ventas) — función principal. Ver sección 9
  para el flujo completo.
---
6. Explicación de las tablas principales en SQLite
La base de datos se almacena en data/ks_requisiciones.db. Todas las tablas se crean
en database.py:inicializar_base_datos().
requisiciones
Tabla central del sistema. Cada fila es una línea de una requisición (un producto de un
documento de requisición).
Columna	Tipo	Descripción
id	INTEGER PK	Autoincremental interno
numreq	TEXT	Número del documento de requisición (ej. "REQ-001")
codprod	TEXT	Código de producto
desprod	TEXT	Descripción del producto
cantidad	INTEGER	Cantidad solicitada (inmutable tras carga)
fecha_requisicion	DATE	Fecha de emisión de la requisición
sucursal_destino	TEXT	Sucursal que solicitó (default 'KS TALCA')
proveedor	TEXT	Editable desde UI
oc	TEXT	Número de OC asignada manualmente
n_guia	TEXT	Número de guía de despacho
fecha_oc	DATE	Fecha de la OC
observacion	TEXT	Observaciones generales
detalle	TEXT	Detalle adicional
cant_recibida	INTEGER	Cantidad recibida a la fecha
estado_oc	TEXT	Estado de la OC (ESTADOS_OC)
estado_envio	TEXT	'No Enviado' / 'Enviado' (v1.8.0)
estado_req	TEXT	Estado operativo manual (ESTADOS_REQ)
saldo_pendiente	INTEGER	Calculado por trigger: cantidad - cant_recibida
fecha_creacion	TIMESTAMP	Automático al insertar
fecha_modificacion	TIMESTAMP	Actualizado por trigger en cada UPDATE
Clave única: UNIQUE(numreq, codprod) — garantiza que no haya dos filas para el
mismo producto en la misma requisición.
Triggers:
- calcular_saldo_pendiente_insert/update — recalcula saldo_pendiente.
- actualizar_fecha_modificacion — actualiza fecha_modificacion en cada UPDATE.
- registrar_cambio_estado/proveedor/oc/cant_recibida — insertan fila en
  historial_cambios al detectar cambio en esos campos.
---
compras
Cada fila es una línea de una orden de compra exportada desde Softland.
Columna	Tipo	Descripción
num_oc	TEXT	Número de la OC
codprod	TEXT	Código de producto
desprod	TEXT	Descripción del producto
proveedor	TEXT	Nombre del proveedor
cantidad_solicitada	REAL	Cantidad en la OC
cantidad_recibida	REAL	Cantidad recibida según Softland
cantidad_manual	REAL	Ajuste manual de recepción
precio_compra	REAL	Precio unitario
total_linea	REAL	Calculado por trigger: (recibida + manual) × precio
fecha_oc	TEXT	Fecha de emisión
fecha_recepcion	TEXT	Fecha de recepción
estado_linea	TEXT	Estado en Softland ('Pendiente', 'Recepción Completa', etc.)
bodega_nombre	TEXT	Bodega destino de recepción
fecha_carga	TEXT	Timestamp de la última carga desde cubo
Clave única: UNIQUE(num_oc, codprod) — permite UPSERT sin duplicar líneas.
Relación lógica con requisiciones: no hay FK declarada, pero la sincronización
actualizar_gestion_desde_compras une ambas tablas por requisiciones.oc = compras.num_oc
y requisiciones.codprod = compras.codprod.
---
ventas
Tabla creada dinámicamente por df.to_sql("ventas", ...). Su esquema depende del cubo
exportado desde Softland. Columnas típicas: CodProd, DesProd, ene, feb, ..., dic.
- Una fila por producto.
- Los meses contienen unidades vendidas en el año anterior.
- Se reemplaza completamente en cada carga (no hay UPSERT).
---
inventario
Tabla creada dinámicamente por df.to_sql("inventario", ...). Columnas típicas:
CodProd, CostoUnitario, KS TALCA, KS BODEGA CENTRAL, Total general, etc.
- Una fila por producto.
- Se reemplaza completamente en cada carga.
---
historial_cambios
Registro de auditoría. Cada fila es un cambio de campo en una requisición.
Columna	Tipo
requisicion_id	INTEGER
campo_modificado	TEXT
valor_anterior	TEXT
valor_nuevo	TEXT
usuario	TEXT
fecha_cambio	TIMESTAMP
Poblada exclusivamente por triggers SQL, sin intervención de código Python.
---
archivos_cargados
Tabla de control de versiones para los cubos de ventas e inventario.
Columna	Tipo	Descripción
nombre_cubo	TEXT PK	'ventas' o 'inventario'
hash_archivo	TEXT	Hash MD5 del último archivo procesado
fecha_carga	DATETIME	Timestamp de la última carga
---
### `configuracion`
Par clave-valor para configuración del sistema. También almacena los hashes de los cubos
raw (`hash_cubo_ventas`, `hash_cubo_compras`, etc.).
---
Tablas raw (cubo_*_raw)
Cuatro tablas (cubo_ventas_raw, cubo_inventario_raw, cubo_compras_raw,
cubo_requisiciones_raw) persisten el DataFrame completo de cada cubo como JSON en la
columna data. Permiten reconstruir el DataFrame original sin necesidad de que el usuario
vuelva a subir el archivo (útil para recargas de página).
---
7. Lógica de negocio importante
Ciclo de vida de una requisición
Softland emite REQ
      │
      ▼
cargar_requisiciones_desde_cubo()
      │  INSERT OR IGNORE → la requisición existe en AppKS
      ▼
Usuario asigna OC manualmente en la tabla
      │  actualizar_requisicion_desde_ui() → UPDATE oc, proveedor, fecha_oc
      ▼
Usuario carga cubo de compras
      │  cargar_compras_desde_dataframe() → UPSERT en tabla compras
      │  actualizar_gestion_desde_compras() → propaga estado OC → requisición
      ▼
Trigger calcular_saldo_pendiente recalcula saldo
      │
      ▼
Usuario marca estado_envio = 'Enviado' en la tabla
      │
      ▼
Recepción: usuario registra cant_recibida
      │  registrar_recepcion() → UPDATE cant_recibida
      │  Trigger recalcula saldo_pendiente
      ▼
Requisición con saldo_pendiente = 0 → cerrada
---
Sincronización REQ → OC (actualizar_gestion_desde_compras)
Esta es la operación de sincronización más importante del sistema. Cuando el usuario carga
el cubo de compras, AppKS no solo guarda las OC — también propaga automáticamente el estado
de cada OC de vuelta a la requisición correspondiente.
Condición de cruce: la requisición debe tener una OC asignada (oc IS NOT NULL AND oc != '').
La relación se establece por dos campos: número de OC y código de producto.
SQL ejecutado:
UPDATE requisiciones
SET
    estado_oc      = c.estado_linea,
    fecha_oc       = c.fecha_oc,
    cant_recibida  = c.cantidad_recibida + c.cantidad_manual,
    bodega_ingreso = c.bodega_nombre,
    observacion_oc = c.observacion
FROM compras c
WHERE c.num_oc  = requisiciones.oc
  AND c.codprod = requisiciones.codprod
  AND requisiciones.oc IS NOT NULL
  AND requisiciones.oc != ''
Por qué un JOIN en SQL y no un loop en Python:
- Un solo UPDATE ... FROM visita la tabla compras una única vez en lugar de ejecutar
  una subquery por cada requisición.
- SQLite puede usar el índice compuesto idx_compras_oc_codprod para el JOIN, logrando
  complejidad O(n log m) en lugar de O(n×m).
- Después del UPDATE, el trigger calcular_saldo_pendiente_update recalcula
  saldo_pendiente = cantidad - cant_recibida automáticamente para cada fila afectada.
---
Reglas de asignación de OC
La asignación de OC a una requisición es manual: el usuario escribe el número de OC
directamente en la celda de la tabla en la UI. No hay asignación automática por ninguna
regla de negocio.
Esto es intencional porque:
- Una OC puede cubrir varias requisiciones (o solo parte de una).
- El criterio de qué OC corresponde a qué requisición requiere juicio operativo.
- Automatizarlo requeriría lógica de matching compleja que podría generar errores silenciosos.
Una vez asignada la OC, la sincronización automática (actualizar_gestion_desde_compras)
se encarga de traer el estado desde el cubo de compras.
---
INSERT OR IGNORE para requisiciones
INSERT OR IGNORE INTO requisiciones (numreq, codprod, desprod, cantidad, ...)
VALUES (?, ?, ?, ?, ...)
La cláusula OR IGNORE hace que SQLite descarte silenciosamente la inserción si ya existe
una fila con la misma clave única (numreq, codprod). Esto garantiza que:
- Los datos operativos editados por el usuario (proveedor, OC, notas) nunca se sobreescriben
  al recargar el cubo de requisiciones.
- La carga del cubo es idempotente: se puede ejecutar múltiples veces sin efectos secundarios.
---
8. Conceptos técnicos utilizados en el proyecto
Arquitectura en capas
El sistema está organizado en capas con responsabilidades bien definidas:
┌─────────────────────────────────┐
│  Presentación  (app/main.py)    │  widgets, routing, eventos UI
├─────────────────────────────────┤
│  Preparación   (app/utils.py)   │  normalización, config AG Grid
├─────────────────────────────────┤
│  Lógica/CRUD   (app/database.py)│  SQL, triggers, migraciones
├─────────────────────────────────┤
│  Servicios     (app/services/)  │  carga de cubos, UPSERT, hash
├─────────────────────────────────┤
│  Caché         (app/cache.py)   │  st.cache_resource / cache_data
├─────────────────────────────────┤
│  Persistencia  (SQLite)         │  tablas, índices, triggers
└─────────────────────────────────┘
Cada capa solo conoce a la capa inmediatamente inferior. main.py nunca escribe SQL
directamente; siempre llama funciones de database.py o los servicios.
---
Carga idempotente
Una operación es idempotente si ejecutarla múltiples veces produce el mismo resultado
que ejecutarla una sola vez. En AppKS:
- inicializar_base_datos() usa CREATE TABLE IF NOT EXISTS — siempre seguro de ejecutar.
- migrar_base_datos_existente() verifica con PRAGMA table_info si la columna existe
  antes de intentar ALTER TABLE.
- cargar_requisiciones_desde_cubo() usa INSERT OR IGNORE — no sobreescribe nada.
- cargar_compras_desde_dataframe() usa INSERT ... ON CONFLICT DO UPDATE WHERE ... —
  solo modifica filas que realmente cambiaron.
Esto permite ejecutar estas operaciones al arrancar la app sin temor a corromper datos.
---
UPSERT
UPSERT (UPDATE + INSERT) es una operación que inserta una fila si no existe, o la
actualiza si ya existe, en una sola sentencia SQL atómica.
En AppKS se usa para la tabla compras:
INSERT INTO compras (num_oc, codprod, ...)
VALUES (?, ?, ...)
ON CONFLICT(num_oc, codprod) DO UPDATE SET
    cantidad_recibida = excluded.cantidad_recibida,
    estado_linea      = excluded.estado_linea,
    ...
WHERE
    compras.cantidad_recibida != excluded.cantidad_recibida OR
    compras.estado_linea      != excluded.estado_linea     OR
    ...
La cláusula WHERE en el DO UPDATE es crítica: si todos los campos son idénticos,
SQLite no ejecuta el UPDATE (rowcount = 0). Esto evita disparar triggers y tocar
fecha_modificacion innecesariamente.
---
Control de versiones por hash MD5
Para los cubos de ventas e inventario, que son reemplazos totales de la tabla, el sistema
calcula el hash MD5 del contenido binario del archivo Excel:
hashlib.md5(archivo.getvalue()).hexdigest()
Este hash se compara con el hash guardado en la tabla archivos_cargados. Si son iguales,
el archivo no cambió y se omite el procesamiento. Si difieren, se reemplaza la tabla y se
actualiza el hash guardado.
Ventaja: en Streamlit, cualquier interacción del usuario puede re-ejecutar el código de
carga. Sin control de hash, la tabla se reemplazaría en cada render aunque el archivo
fuera el mismo.
---
Triggers SQL
Los triggers son procedimientos almacenados en SQLite que se ejecutan automáticamente
al ocurrir un evento (AFTER INSERT, AFTER UPDATE) en una tabla.
AppKS usa triggers para:
Trigger	Tabla	Evento	Efecto
calcular_saldo_pendiente_insert/update	requisiciones	INSERT / UPDATE	Recalcula saldo_pendiente = cantidad - cant_recibida
actualizar_fecha_modificacion	requisiciones	UPDATE	Actualiza fecha_modificacion = CURRENT_TIMESTAMP
registrar_cambio_estado	requisiciones	UPDATE	Inserta fila en historial_cambios si estado_oc cambió
registrar_cambio_proveedor	requisiciones	UPDATE	Ídem para proveedor
registrar_cambio_oc	requisiciones	UPDATE	Ídem para oc
registrar_cambio_cant_recibida	requisiciones	UPDATE	Ídem para cant_recibida
calcular_total_linea_insert/update	compras	INSERT / UPDATE	Recalcula total_linea = (recibida + manual) × precio
calcular_saldo_gestion_insert/update	gestion	INSERT / UPDATE	Recalcula saldo_pendiente
Ventaja: los cálculos derivados y la auditoría ocurren en la base de datos, no en Python.
No hay riesgo de que un UPDATE desde la UI omita actualizar el saldo por olvido.
---
Procesamiento de datos con pandas
pandas es la librería central de transformación de datos. En AppKS se usa para:
- Lectura de Excel: pd.read_excel() con detección automática de fila de encabezado
  para cubos con pivot tables (ventas, inventario).
- Normalización de tipos: pd.to_numeric(..., errors='coerce'), pd.to_datetime(...),
  .fillna(), .astype(str).
- Detección de cambios en batch edit: comparar el DataFrame original con el editado
  por el usuario usando df_original.equals(df_editado) fila por fila.
- KPIs: agrupaciones con .groupby(), .value_counts(), .sum() sobre el DataFrame
  cacheado de requisiciones.
- Análisis de stock: merge de inventario × ventas con df.merge(..., how='left'),
  cálculo vectorizado de stock_objetivo y clasificación con np.select.
- Serialización a SQLite: df.to_sql(...) para ventas e inventario.
---
9. Funciones importantes del sistema
inicializar_base_datos — app/database.py
Responsabilidad: crea todas las tablas, índices y triggers de la base de datos si no
existen. Es el punto de arranque de la capa de datos.
Flujo simplificado:
1. Abre una conexión dedicada (get_db_connection()).
2. Ejecuta CREATE TABLE IF NOT EXISTS para requisiciones, historial_cambios,
   log_eliminaciones, configuracion, cargas_diarias, backups_log y las cuatro
   tablas raw.
3. Crea índices sobre columnas de búsqueda frecuente (numreq, codprod, estado_oc,
   oc, fecha_oc).
4. Crea todos los triggers de auditoría y cálculo.
5. Hace conn.commit().
Por qué es importante: se llama al inicio de main.py antes de cualquier operación.
Garantiza que la DB siempre tenga el esquema correcto, incluso en una instalación nueva.
Conceptos: CREATE TABLE IF NOT EXISTS, triggers SQL, índices compuestos.
---
migrar_base_datos_existente — app/database.py
Responsabilidad: agrega columnas nuevas a tablas existentes en instalaciones previas,
sin recrear la tabla ni perder datos.
Flujo simplificado:
1. Para cada columna nueva (ej. estado_envio, n_guia, detalle):
   - Ejecuta PRAGMA table_info(requisiciones) para obtener las columnas actuales.
   - Si la columna no existe, ejecuta ALTER TABLE requisiciones ADD COLUMN ....
   - Si ya existe, no hace nada (idempotente).
2. Hace lo mismo para otras tablas si aplica.
Por qué es importante: permite actualizar AppKS en una instalación existente con datos
reales sin necesidad de borrar y recrear la base de datos. Sin esta función, cada versión
nueva requeriría un script de migración manual.
Conceptos: PRAGMA table_info, ALTER TABLE, migraciones idempotentes.
---
cargar_requisiciones_desde_cubo — app/database.py
Responsabilidad: toma el DataFrame del cubo de requisiciones (ya validado) y lo persiste
en la tabla requisiciones usando INSERT OR IGNORE.
Flujo simplificado:
1. Filtra las filas de la sucursal asignada (TALCA).
2. Renombra y normaliza columnas al esquema interno.
3. Para cada fila ejecuta:
      INSERT OR IGNORE INTO requisiciones (numreq, codprod, cantidad, ...)
   VALUES (?, ?, ?, ...)
   4. Registra el resultado en cargas_diarias.
5. Llama invalidar_cache().
Por qué es importante: es la puerta de entrada de requisiciones al sistema. El
OR IGNORE es la garantía de que los datos operativos editados por el usuario (OC,
proveedor, notas) nunca se sobreescriben al recargar el cubo.
Conceptos: INSERT OR IGNORE, clave única (numreq, codprod), carga idempotente.
---
procesar_ediciones_batch_ui — app/database.py
Responsabilidad: recibe el DataFrame editado por el usuario en el AG Grid, detecta qué
filas cambiaron respecto al estado original en SQLite, y guarda solo esas filas.
Flujo simplificado:
1. Carga el estado actual desde get_table("requisiciones") como DataFrame de referencia.
2. Compara fila a fila el DataFrame editado contra el de referencia (mismo id).
3. Para cada fila con diferencias, llama actualizar_requisicion_desde_ui(id, cambios).
4. Llama invalidar_cache() al final.
5. Retorna conteo de filas actualizadas y lista de errores.
Por qué es importante: evita ejecutar un UPDATE por cada fila visible en la tabla
(que pueden ser cientos). Solo toca las filas que el usuario realmente modificó.
Conceptos: diff de DataFrames, UPDATE selectivo, whitelist de campos editables.
---
actualizar_requisicion_desde_ui — app/database.py
Responsabilidad: ejecuta un UPDATE sobre una requisición específica, aceptando solo
campos que están en la whitelist CAMPOS_EDITABLES_UI.
Flujo simplificado:
1. Filtra el diccionario de cambios para conservar solo claves en CAMPOS_EDITABLES_UI.
2. Valida valores específicos: estado_envio debe estar en ESTADOS_ENVIO;
   estado_req en ESTADOS_REQ.
3. Construye dinámicamente la parte SET del SQL:
      UPDATE requisiciones SET campo1 = ?, campo2 = ? WHERE id = ?
   4. Ejecuta con conexión propia (no la compartida del caché).
Por qué es importante: es la única función que puede modificar requisiciones desde la
UI. La whitelist garantiza que campos inmutables (numreq, codprod, cantidad) nunca
sean alterados por un usuario, aunque manipule el AG Grid directamente.
Conceptos: whitelist de campos, UPDATE dinámico, validación de dominio.
---
obtener_kpis_dashboard — app/database.py
Responsabilidad: calcula todos los KPIs del dashboard (conteos por estado, alertas,
totales) usando pandas sobre el DataFrame cacheado de requisiciones.
Flujo simplificado:
1. Obtiene df = get_table("requisiciones") (desde caché, sin consulta SQL adicional).
2. Calcula con pandas:
   - value_counts() sobre estado_oc para distribución de estados.
   - Filtros por fecha para alertas (DIAS_ALERTA_*).
   - sum() sobre cantidad y cant_recibida.
3. Retorna diccionario con todos los KPIs.
Por qué es importante: el dashboard se re-renderiza en cada interacción de Streamlit.
Usar el DataFrame cacheado en lugar de consultar SQLite en cada render evita decenas de
consultas innecesarias por sesión.
Conceptos: st.cache_data, agrupaciones con pandas, cálculo en memoria.
---
cargar_compras_desde_dataframe — app/services/compras_service.py
Responsabilidad: persiste las líneas del cubo de compras en SQLite mediante UPSERT,
sin borrar datos existentes ni duplicar registros.
Flujo simplificado:
1. Valida columnas con validar_columnas_compras(df).
2. Normaliza el DataFrame con normalizar_dataframe_compras(df).
3. Para cada fila:
   a. Verifica si (num_oc, codprod) ya existe con SELECT 1 ... LIMIT 1 (O(log n)).
   b. Ejecuta el UPSERT con ON CONFLICT DO UPDATE WHERE <cambios detectados>.
   c. Clasifica el resultado: insertado / actualizado / sin cambios según cursor.rowcount.
4. Hace conn.commit() y llama invalidar_cache().
Por qué es importante: es la función que mantiene la tabla compras actualizada con
cada exportación de Softland. La detección de cambios en la cláusula WHERE del UPSERT
garantiza que los triggers y los timestamps no se disparen para filas idénticas.
Conceptos: UPSERT, ON CONFLICT DO UPDATE WHERE, O(log n) lookup por índice único.
---
actualizar_gestion_desde_compras — app/services/compras_service.py
Responsabilidad: propaga el estado de las OC desde la tabla compras hacia las
requisiciones que tienen OC asignada, en una sola pasada SQL.
Flujo simplificado:
1. Verifica que existan las tablas gestion y compras.
2. Cuenta los candidatos al cruce con un SELECT COUNT ... INNER JOIN.
3. Ejecuta el UPDATE ... FROM compras WHERE oc = num_oc AND codprod = codprod.
4. El trigger calcular_saldo_pendiente_update recalcula saldo_pendiente por cada
   fila actualizada.
5. Retorna el conteo de filas actualizadas.
Por qué es importante: esta función cierra el ciclo REQ → OC → estado actualizado.
Sin ella, el usuario tendría que actualizar manualmente el estado de cada requisición
después de cargar el cubo de compras.
Conceptos: UPDATE ... FROM, JOIN implícito en UPDATE, triggers en cascada.
---
calcular_analisis_stock — app/modules/analisis_stock/service.py
Responsabilidad: cruza inventario × ventas para calcular cobertura de stock y
clasificar la rotación de cada producto.
Flujo simplificado:
1. Llama _preparar_inventario(df_inventario) → extrae codprod, desprod, stock_actual.
2. Llama _preparar_ventas(df_ventas) → normaliza meses como columnas numéricas.
3. Extrae ventas del mes actual y del mes siguiente (del año anterior) como columnas
   separadas usando groupby + sum.
4. Calcula meses_con_venta = (df[meses] > 0).sum(axis=1) para todos los meses.
5. Hace tres merge(..., how='left'): inventario ← ventas mes actual ← ventas mes
   siguiente ← meses con venta.
6. Calcula stock_objetivo = ventas_mes_actual + ventas_mes_siguiente.
7. Clasifica estado_stock (Falta de stock / Stock óptimo / Sobrestock) comparando
   stock_actual vs stock_objetivo.
8. Clasifica rotacion con np.select: Alta (≥10 meses), Media (7-9), Baja (≤6).
Por qué es importante: es el único módulo analítico del sistema. Convierte datos crudos
de Softland en inteligencia operativa accionable (qué productos pedir, cuáles tienen
sobrestock).
Conceptos: merge left, operaciones vectorizadas en pandas, np.select, modelo de
cobertura de 2 meses.
---
preparar_df_para_edicion_segura — app/utils.py
Responsabilidad: toma el DataFrame crudo de SQLite y lo transforma al formato exacto
que espera el AG Grid: tipos correctos, columnas en orden, valores nulos reemplazados.
Flujo simplificado:
1. Reordena columnas: primero las visibles en la UI, al final las ocultas.
2. Normaliza tipos:
   - Fechas: convierte a string con formato YYYY-MM-DD (AG Grid no maneja objetos
     datetime de pandas directamente).
   - Booleanos legacy: convierte a string para evitar conflictos con AG Grid.
   - estado_envio: fillna("No Enviado").astype(str).
   - Campos de texto: fillna("").
3. Retorna el DataFrame listo para pasarlo al st.data_editor o AgGrid.
Por qué es importante: AG Grid y st.data_editor son estrictos con los tipos de datos.
Un NaN en una columna de texto, o un Timestamp donde se espera string, genera errores
de render difíciles de depurar. Esta función es el colchón entre SQLite y la UI.
Conceptos: normalización de tipos, fillna, compatibilidad pandas ↔ AG Grid.
---
10. Decisiones de diseño del sistema
Por qué SQLite en lugar de otro motor
Problema: la aplicación necesita persistir datos estructurados con relaciones, soporte
para transacciones y capacidad de consulta con SQL, pero se distribuye como una aplicación
de escritorio local sin infraestructura de servidor.
Solución elegida: SQLite como motor de base de datos embebido.
Alternativas consideradas:
- PostgreSQL / MySQL: requieren servidor separado, configuración de red, credenciales.
  Inviable para distribución local sin soporte IT.
- CSV o Excel como persistencia: no tienen transacciones, no soportan concurrent access,
  no permiten triggers ni constraints.
- JSON en disco: similar a CSV, sin capacidad de consulta eficiente.
Ventajas de SQLite:
- Un solo archivo (ks_requisiciones.db) — fácil de respaldar, mover y versionar.
- Transacciones ACID, triggers, constraints, índices — todas las garantías de una DB relacional.
- Sin instalación: incluida en Python estándar (import sqlite3).
- WAL mode permite lecturas concurrentes sin bloquear escrituras.
- Rendimiento suficiente para el volumen de datos esperado (miles de requisiciones, no millones).
---
Por qué Streamlit como interfaz
Problema: se necesita una interfaz web con tablas editables, filtros, gráficos y
formularios, pero el desarrollador no tiene experiencia en frameworks web tradicionales
(React, Django, etc.) y el tiempo de desarrollo es limitado.
Solución elegida: Streamlit como framework de UI.
Alternativas consideradas:
- Flask + HTML/CSS/JS: mayor control, pero requiere desarrollar el frontend completo.
  Semanas de trabajo adicional para llegar al mismo resultado visual.
- PyQt / tkinter: interfaces de escritorio nativas, sin capacidad web, menos atractivas
  visualmente y más complejas de distribuir.
- Excel con macros VBA: sin capacidad de base de datos relacional ni lógica compleja.
Ventajas de Streamlit:
- Interfaz web completa escribiendo solo Python.
- Componentes listos: tablas, gráficos (Altair/Plotly), filtros, uploads de archivos.
- st.session_state para manejar estado entre interacciones.
- Compatible con AG Grid (streamlit-aggrid) para tablas editables avanzadas.
- Distribución simple: streamlit run run.py desde el venv, empaquetable con PyInstaller.
Desventaja asumida: el modelo de re-ejecución completa del script en cada interacción
requiere diseñar con cuidado el caché (st.cache_data, st.cache_resource) para evitar
consultas repetidas a SQLite en cada render.
---
Por qué estados TEXT en lugar de booleanos
Problema: el campo oc_enviada original era INTEGER (0/1), pero al interactuar con
AG Grid, pandas y SQLite al mismo tiempo surgían conflictos de tipo: AG Grid lo renderizaba
como checkbox, pandas lo leía como float64 si había nulos, y SQLite lo guardaba como
entero. Cambiar cualquier parte del stack requería normalizar en todas las capas.
Solución elegida: reemplazar oc_enviada INTEGER por estado_envio TEXT DEFAULT 'No Enviado'
con valores del catálogo ESTADOS_ENVIO = ["No Enviado", "Enviado"].
Alternativas consideradas:
- Mantener INTEGER y agregar conversión explícita en cada capa: agrega complejidad sin
  resolver el problema de fondo.
- BOOLEAN nativo de SQLite: SQLite no tiene tipo BOOLEAN real; internamente es INTEGER 0/1,
  con el mismo problema.
Ventajas de TEXT:
- Un string "No Enviado" es el mismo tipo en SQLite, pandas y AG Grid: sin conversiones.
- El AG Grid puede renderizarlo como agSelectCellEditor con las opciones del catálogo.
- Extensible: agregar un tercer estado ("Error", "Cancelado") solo requiere agregar
  una entrada al catálogo ESTADOS_ENVIO en config.py.
- El valor DEFAULT 'No Enviado' es legible en SQL sin necesidad de lookups.
---
Por qué cargas idempotentes
Problema: el usuario recarga el mismo cubo de requisiciones varias veces (olvida que
ya lo subió, o quiere verificar que cargó correctamente). Si cada carga sobreescribiera
los datos, se perderían las ediciones manuales del usuario (OC asignadas, proveedores,
notas).
Solución elegida: INSERT OR IGNORE para requisiciones. Si la clave única
(numreq, codprod) ya existe, SQLite descarta la inserción silenciosamente.
Alternativas consideradas:
- INSERT OR REPLACE: sobreescribiría toda la fila, borrando los datos operativos editados.
- Verificar antes de insertar (SELECT + INSERT en Python): dos operaciones por fila,
  más lento y no atómico.
Ventajas:
- El usuario puede subir el cubo tantas veces como quiera sin consecuencias.
- Una sola sentencia SQL por fila — atómico y eficiente.
- Los datos operativos (OC, proveedor, notas) son inmunes a las recargas del cubo.
---
Por qué sincronizaciones SQL en lugar de loops Python
Problema: al cargar el cubo de compras, hay que actualizar el estado de OC en cada
requisición que tenga una OC asignada. La implementación obvia sería iterar sobre las
requisiciones en Python y ejecutar un UPDATE por cada una.
Solución elegida: un único UPDATE ... FROM compras WHERE oc = num_oc AND codprod = codprod.
Alternativas consideradas:
- Loop Python + UPDATE individual: N queries para N requisiciones. Con 500 requisiciones
  activas, son 500 roundtrips a SQLite.
- Subqueries correlacionadas: UPDATE requisiciones SET estado_oc = (SELECT estado_linea FROM compras WHERE ...) —
  SQLite ejecuta la subquery una vez por cada fila candidata, menos eficiente que UPDATE ... FROM.
Ventajas del JOIN en UPDATE:
- Una sola pasada sobre ambas tablas usando los índices compuestos.
- SQLite puede optimizar el plan de ejecución globalmente.
- El trigger calcular_saldo_pendiente_update se dispara automáticamente para cada fila
  actualizada, sin código Python adicional.
- Código más conciso y fácil de auditar.
---
Por qué control de hash MD5 para cubos
Problema: Streamlit re-ejecuta todo el script Python en cada interacción del usuario.
Si el código de carga de ventas/inventario no tiene control de cambios, reemplazaría la
tabla en cada click del usuario, aunque el archivo Excel fuera el mismo.
Solución elegida: calcular el MD5 del contenido binario del archivo al subirlo,
compararlo con el hash guardado en archivos_cargados, y solo procesar si difieren.
Alternativas consideradas:
- Comparar por nombre de archivo: insuficiente — un archivo puede cambiar de contenido
  sin cambiar de nombre.
- Comparar por tamaño: insuficiente — dos archivos distintos pueden tener el mismo tamaño.
- st.session_state para recordar qué se procesó: se pierde al recargar la página o
  abrir una nueva pestaña.
Ventajas del hash MD5:
- Garantiza que el procesamiento ocurre si y solo si el contenido cambió.
- El hash se persiste en SQLite — sobrevive recargas de página y reinicios de la app.
- MD5 es suficientemente rápido para archivos Excel de tamaño típico (< 10 MB).
- El mismo patrón funciona para cualquier cubo futuro que se agregue al sistema.