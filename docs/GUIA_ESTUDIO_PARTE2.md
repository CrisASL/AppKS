# Guia de Estudio del Codigo - Parte 2

## Capa de Datos: Base de Datos, Servicios y Cache

> Cubre el esquema SQLite, los servicios de carga de cubos, el sistema de cache
> y la logica de negocio central del sistema.

---

## Tabla de contenidos

1. [Tablas principales en SQLite](#1-tablas-principales-en-sqlite)
2. [Archivos clave de la capa de datos](#2-archivos-clave-de-la-capa-de-datos)
3. [Funciones importantes de la capa de datos](#3-funciones-importantes-de-la-capa-de-datos)
4. [Logica de negocio](#4-logica-de-negocio)

---

## 1. Tablas principales en SQLite

La base de datos se almacena en `data/ks_requisiciones.db`. Todas las tablas se crean
en `database.py:inicializar_base_datos()`. El sistema tiene 10 tablas en total.

### `requisiciones`

Tabla central del sistema. Cada fila es una linea de una requisicion (un producto de un
documento de requisicion).

| Columna | Tipo | Descripcion |
|---------|------|-------------|
| `id` | INTEGER PK | Autoincremental interno |
| `numreq` | TEXT | Numero del documento de requisicion (ej. "REQ-001") |
| `codprod` | TEXT | Codigo de producto |
| `desprod` | TEXT | Descripcion del producto |
| `cantidad` | INTEGER | Cantidad solicitada (inmutable tras carga) |
| `fecha_requisicion` | DATE | Fecha de emision de la requisicion |
| `sucursal_destino` | TEXT | Sucursal que solicito (default 'KS TALCA') |
| `proveedor` | TEXT | Editable desde UI |
| `oc` | TEXT | Numero de OC asignada manualmente |
| `n_guia` | TEXT | Numero de guia de despacho |
| `fecha_oc` | DATE | Fecha de la OC |
| `observacion` | TEXT | Observaciones generales |
| `detalle` | TEXT | Detalle adicional |
| `cant_recibida` | INTEGER | Cantidad recibida a la fecha |
| `estado_oc` | TEXT | Estado de la OC (ESTADOS_OC: 8 valores posibles) |
| `estado_envio` | TEXT | 'No Enviado' / 'Enviado' |
| `estado_req` | TEXT | Estado operativo manual (ESTADOS_REQ: 4 valores) |
| `saldo_pendiente` | INTEGER | Calculado por trigger: cantidad - cant_recibida |
| `fecha_creacion` | TIMESTAMP | Automatico al insertar |
| `fecha_modificacion` | TIMESTAMP | Actualizado por trigger en cada UPDATE |

**Clave unica:** `UNIQUE(numreq, codprod)` — no puede haber dos filas para el mismo
producto en la misma requisicion.

**Triggers asociados:**
- `calcular_saldo_pendiente_insert/update` — recalcula `saldo_pendiente`.
- `actualizar_fecha_modificacion` — actualiza `fecha_modificacion` en cada UPDATE.
- `registrar_cambio_estado/proveedor/oc/cant_recibida` — insertan fila en
  `historial_cambios` al detectar cambio en esos campos.

---

### `compras`

Cada fila es una linea de una orden de compra exportada desde Softland.

| Columna | Tipo | Descripcion |
|---------|------|-------------|
| `num_oc` | TEXT | Numero de la OC |
| `codprod` | TEXT | Codigo de producto |
| `desprod` | TEXT | Descripcion del producto |
| `proveedor` | TEXT | Nombre del proveedor |
| `cantidad_solicitada` | REAL | Cantidad en la OC |
| `cantidad_recibida` | REAL | Cantidad recibida segun Softland |
| `cantidad_manual` | REAL | Ajuste manual de recepcion |
| `precio_compra` | REAL | Precio unitario |
| `total_linea` | REAL | Calculado por trigger: (recibida + manual) x precio |
| `fecha_oc` | TEXT | Fecha de emision |
| `fecha_recepcion` | TEXT | Fecha de recepcion |
| `estado_linea` | TEXT | Estado en Softland ('Pendiente', 'Recepcion Completa', etc.) |
| `bodega_nombre` | TEXT | Bodega destino de recepcion |
| `fecha_carga` | TEXT | Timestamp de la ultima carga desde cubo |

**Clave unica:** `UNIQUE(num_oc, codprod)` — permite UPSERT sin duplicar lineas.

**Relacion logica con requisiciones:** no hay FK declarada, pero la sincronizacion
`actualizar_requisiciones_desde_compras` une ambas tablas por
`requisiciones.oc = compras.num_oc` y `requisiciones.codprod = compras.codprod`.

---

### `ventas`

Tabla creada dinamicamente por `df.to_sql("ventas", ...)`. Su esquema depende del cubo
exportado desde Softland.

Columnas tipicas: `CodProd`, `DesProd`, `ene`, `feb`, ..., `dic`.
- Una fila por producto.
- Los meses contienen unidades vendidas en el anio anterior.
- Se reemplaza completamente en cada carga (no hay UPSERT).

---

### `inventario`

Tabla creada dinamicamente por `df.to_sql("inventario", ...)`.

Columnas tipicas: `CodProd`, `CostoUnitario`, `KS TALCA`, `KS BODEGA CENTRAL`,
`Total general`, etc.
- Una fila por producto.
- Se reemplaza completamente en cada carga.

---

### `historial_cambios`

Registro de auditoria. Cada fila es un cambio de campo en una requisicion.

| Columna | Tipo |
|---------|------|
| `requisicion_id` | INTEGER |
| `campo_modificado` | TEXT |
| `valor_anterior` | TEXT |
| `valor_nuevo` | TEXT |
| `usuario` | TEXT |
| `fecha_cambio` | TIMESTAMP |

Poblada exclusivamente por triggers SQL, sin intervencion de codigo Python.

---

### `archivos_cargados`

Control de versiones para cubos de ventas e inventario.

| Columna | Tipo | Descripcion |
|---------|------|-------------|
| `nombre_cubo` | TEXT PK | 'ventas' o 'inventario' |
| `hash_archivo` | TEXT | Hash MD5 del ultimo archivo procesado |
| `fecha_carga` | DATETIME | Timestamp de la ultima carga |

---

### `configuracion`

Par clave-valor para configuracion del sistema. Almacena hashes de cubos raw
(`hash_cubo_ventas`, `hash_cubo_compras`, etc.) y la hoja seleccionada por el
usuario para cada cubo (`hoja_cubo_ventas`, `hoja_cubo_inventario`, etc.).

---

### `cargas_diarias`

Registra cada operacion de carga de cubos con estadisticas (filas insertadas,
actualizadas, errores, timestamp).

---

### Tablas raw (`cubo_*_raw`)

Cuatro tablas (`cubo_ventas_raw`, `cubo_inventario_raw`, `cubo_compras_raw`,
`cubo_requisiciones_raw`) persisten el DataFrame completo de cada cubo como JSON
en la columna `data`. Permiten reconstruir el DataFrame original sin necesidad de
que el usuario vuelva a subir el archivo (util para recargas de pagina en Streamlit).

---

### Tablas auxiliares

- **`log_eliminaciones`** — registro de requisiciones eliminadas (soft delete).
- **`backups_log`** — registro de backups automaticos realizados.

---

## 2. Archivos clave de la capa de datos

### `app/database.py` (~2443 lineas)

Es la capa de datos completa. Todo acceso a SQLite (lectura, escritura, esquema,
migraciones) pasa por este archivo.

**Estructura interna:**

```
database.py
|-- inicializar_base_datos()           -> CREATE TABLE + triggers + indices
|-- migrar_base_datos_existente()      -> migraciones idempotentes
|
|-- -- Cubos raw --
|-- guardar_cubo_raw()                 -> serializa DataFrame a JSON en cubo_*_raw
|-- cargar_cubo_raw()                  -> deserializa JSON a DataFrame
|-- get_or_load_cubo()                 -> centralizador: cache -> raw -> None
|
|-- -- Carga de cubos --
|-- cargar_requisiciones_desde_cubo()  -> INSERT OR IGNORE (2 fases: validar + insertar)
|-- actualizar_requisiciones_desde_compras() -> sincronizacion REQ <-> OC (3 fases)
|
|-- -- KPIs --
|-- obtener_kpis_dashboard()           -> agrupaciones con pandas sobre get_table()
|-- obtener_top_productos_ultimo_mes() -> Top productos por cantidad (60 dias)
|-- obtener_estadisticas_generales()   -> Estadisticas globales del sistema
|
|-- -- CRUD operativo --
|-- actualizar_requisicion_desde_ui()  -> UPDATE con whitelist de campos validos
|-- procesar_ediciones_batch_ui()      -> diff DataFrame original vs editado -> batch UPDATE
|-- registrar_recepcion()              -> actualiza cant_recibida + trigger recalcula saldo
|-- eliminar_requisicion()             -> soft delete con log
|
|-- -- Consultas --
|-- obtener_requisiciones()            -> query con filtros
|-- obtener_req_pendientes()           -> requisiciones pendientes
|-- obtener_historial()                -> historial de cambios
|
|-- -- Configuracion y limpieza --
|-- guardar_configuracion()            -> INSERT OR REPLACE clave-valor
|-- obtener_configuracion()            -> SELECT por clave
|-- limpiar_base_datos()               -> limpieza total
|-- limpiar_cubo_*()                   -> limpieza por tipo de cubo
|
|-- -- Helpers --
|-- get_db_connection()                -> context manager de conexion dedicada
|-- calcular_hash_archivo()            -> MD5 del contenido
```

**Conexiones: lectura vs escritura:**
- **Lectura:** usa `cache.py:get_connection()` (conexion compartida, `cache_resource`).
- **Escritura:** abre una conexion nueva y dedicada con `get_db_connection()` para cada
  operacion. Esto evita problemas de concurrencia y bloqueos en SQLite con WAL mode.

---

### `app/cache.py` (~119 lineas)

Abstraccion del cache con 4 funciones:

| Funcion | Decorador | Proposito |
|---------|-----------|-----------|
| `get_connection()` | `@cache_resource` | Conexion SQLite unica, persistente, con WAL mode. Solo lectura |
| `get_table(table_name)` | `@cache_data` | DataFrame completo de una tabla, cacheado entre renders |
| `invalidar_cache()` | — | Limpia el cache de `get_table`. Llamar tras toda escritura |
| `cargar_excel(_archivo, file_hash, tipo_cubo, hoja)` | `@cache_data` | Lee Excel cacheando por `file_hash`. Detecta pivot tables automaticamente |

El parametro `_archivo` de `cargar_excel` usa prefijo `_` para que Streamlit no lo
incluya en la clave de cache; `file_hash` es el identificador que determina cuando
se invalida el resultado.

---

### `app/services/compras_service.py` (~1010 lineas)

Carga el cubo de compras desde un DataFrame de Excel a la tabla `compras` en SQLite,
y gestiona la tabla con su esquema, indices y triggers propios.

**Funciones clave:**

| Funcion | Proposito |
|---------|-----------|
| `crear_tabla_compras()` | Crea tabla `compras` con esquema completo, indices y triggers de `total_linea`. Idempotente |
| `crear_indice_compras()` | Crea indices sobre columnas de busqueda frecuente |
| `migrar_tabla_compras_agregar_desprod()` | Migracion: agrega columna `desprod` a instalaciones antiguas |
| `cargar_compras_desde_dataframe(df)` | UPSERT principal con deduplicacion. Retorna conteo de insertados/actualizados/sin cambios |
| `obtener_estadisticas_compras()` | Estadisticas de la tabla compras |

**Notas importantes:**
- `cantidad_solicitada` nunca se actualiza en el UPSERT; solo campos operativos.
- El trigger `calcular_total_linea_update` recalcula `total_linea` automaticamente
  tras cada UPDATE.

---

### `app/services/ventas_inventario_service.py` (~239 lineas)

Persiste cubos de ventas e inventario en SQLite con control de versiones por hash MD5.

**Patron de uso:**

```python
hash_nuevo = calcular_hash_archivo(archivo_subido)
hash_anterior = obtener_hash_guardado("ventas")
if hash_nuevo != hash_anterior:
    guardar_ventas(df_procesado)
    actualizar_hash("ventas", hash_nuevo)
else:
    st.info("El archivo no cambio, no se reproceso")
```

Este patron evita reemplazar toda la tabla en cada recarga de pagina de Streamlit.

---

## 3. Funciones importantes de la capa de datos

### `inicializar_base_datos` — database.py

Crea todas las tablas, indices y triggers si no existen. Es el punto de arranque de
la capa de datos.

**Flujo:**
1. Abre conexion dedicada con `get_db_connection()`.
2. Ejecuta `CREATE TABLE IF NOT EXISTS` para: `requisiciones`, `historial_cambios`,
   `log_eliminaciones`, `configuracion`, `cargas_diarias`, `backups_log` y las 4
   tablas raw.
3. Crea indices sobre columnas de busqueda frecuente.
4. Crea todos los triggers de auditoria y calculo.
5. `conn.commit()`.

Se llama al inicio de `main.py` antes de cualquier operacion. Garantiza que la DB
tenga el esquema correcto incluso en una instalacion nueva.

---

### `migrar_base_datos_existente` — database.py

Agrega columnas nuevas a tablas existentes sin recrear la tabla ni perder datos.

**Flujo:**
1. Para cada columna nueva (ej. `estado_envio`, `n_guia`, `detalle`):
   - Ejecuta `PRAGMA table_info(requisiciones)` para obtener columnas actuales.
   - Si la columna no existe, ejecuta `ALTER TABLE ... ADD COLUMN ...`.
   - Si ya existe, no hace nada (idempotente).

Permite actualizar AppKS en una instalacion existente con datos reales sin borrar
la base de datos.

---

### `cargar_requisiciones_desde_cubo` — database.py

Toma el DataFrame del cubo de requisiciones (ya validado) y lo persiste con
`INSERT OR IGNORE`. Opera en 2 fases: primero valida, luego inserta.

**Flujo:**
1. Filtra las filas de la sucursal asignada (TALCA).
2. Renombra y normaliza columnas al esquema interno.
3. Para cada fila: `INSERT OR IGNORE INTO requisiciones (numreq, codprod, ...) VALUES (...)`.
4. Registra resultado en `cargas_diarias`.
5. Llama `invalidar_cache()`.

El `OR IGNORE` garantiza que datos operativos editados por el usuario (OC, proveedor,
notas) nunca se sobreescriben al recargar el cubo.

---

### `procesar_ediciones_batch_ui` — database.py

Recibe el DataFrame editado por el usuario en AG Grid, detecta que filas cambiaron
respecto al estado original en SQLite, y guarda solo esas filas.

**Flujo:**
1. Carga estado actual con `get_table("requisiciones")` como referencia.
2. Compara fila a fila el DataFrame editado contra el de referencia (mismo `id`).
3. Para cada fila con diferencias, llama `actualizar_requisicion_desde_ui(id, cambios)`.
4. Llama `invalidar_cache()`.
5. Retorna conteo de filas actualizadas y lista de errores.

Evita ejecutar un UPDATE por cada fila visible — solo toca las filas modificadas.

---

### `actualizar_requisicion_desde_ui` — database.py

Ejecuta un UPDATE sobre una requisicion especifica, aceptando solo campos de la
whitelist `CAMPOS_EDITABLES_UI` (9 campos).

**Flujo:**
1. Filtra el diccionario de cambios para conservar solo claves en `CAMPOS_EDITABLES_UI`.
2. Valida valores: `estado_envio` en `ESTADOS_ENVIO`, `estado_req` en `ESTADOS_REQ`.
3. Construye dinamicamente: `UPDATE requisiciones SET campo1=?, campo2=? WHERE id=?`.
4. Ejecuta con conexion propia.

La whitelist garantiza que campos inmutables (`numreq`, `codprod`, `cantidad`) nunca
sean alterados desde la UI.

---

### `obtener_kpis_dashboard` — database.py

Calcula todos los KPIs del dashboard usando pandas sobre el DataFrame cacheado.

**Flujo:**
1. Obtiene `df = get_table("requisiciones")` (desde cache, sin consulta SQL).
2. Calcula con pandas: `value_counts()` sobre `estado_oc`, filtros por fecha para
   alertas, `sum()` sobre `cantidad` y `cant_recibida`.
3. Retorna diccionario con todos los KPIs.

Usa el DataFrame cacheado en lugar de consultar SQLite en cada render.

---

### `cargar_compras_desde_dataframe` — compras_service.py

Persiste las lineas del cubo de compras mediante UPSERT con deduplicacion.

**Flujo:**
1. Normaliza el DataFrame (renombrar columnas, cast de tipos).
2. Para cada fila:
   a. Verifica si `(num_oc, codprod)` ya existe con `SELECT 1 ... LIMIT 1`.
   b. Ejecuta UPSERT con `ON CONFLICT DO UPDATE WHERE <cambios detectados>`.
   c. Clasifica: insertado / actualizado / sin cambios segun `cursor.rowcount`.
3. `conn.commit()` y `invalidar_cache()`.

La deteccion de cambios en el `WHERE` del UPSERT garantiza que los triggers no se
disparen para filas identicas.

---

### `actualizar_requisiciones_desde_compras` — database.py

Propaga el estado de las OC desde la tabla `compras` hacia las requisiciones.
Opera en 3 fases de cruce:

1. **Fallback proveedor:** si la requisicion no tiene proveedor pero tiene OC,
   lo toma de compras.
2. **Referencia explicita:** cruza por `oc = num_oc` y `codprod = codprod`.
3. **Auto-match:** busca coincidencias automaticas por codigo de producto.

**SQL principal (fase 2):**

```sql
UPDATE requisiciones
SET
    estado_oc      = c.estado_linea,
    fecha_oc       = c.fecha_oc,
    cant_recibida  = c.cantidad_recibida + c.cantidad_manual,
    bodega_ingreso = c.bodega_nombre
FROM compras c
WHERE c.num_oc  = requisiciones.oc
  AND c.codprod = requisiciones.codprod
  AND requisiciones.oc IS NOT NULL
  AND requisiciones.oc != ''
```

Despues del UPDATE, el trigger `calcular_saldo_pendiente_update` recalcula el saldo
automaticamente para cada fila afectada.

---

### `calcular_analisis_stock` — analisis_stock/service.py

Cruza inventario x ventas para calcular cobertura de stock y clasificar rotacion.

**Flujo:**
1. `_preparar_inventario(df)` — extrae `codprod`, `desprod`, `stock_actual` (KS TALCA).
2. `_preparar_ventas(df)` — normaliza meses como columnas numericas.
3. Extrae ventas del mes actual y del mes siguiente (del anio anterior).
4. Calcula `meses_con_venta = (df[meses] > 0).sum(axis=1)`.
5. Merge left: inventario <- ventas mes actual <- ventas mes siguiente <- meses con venta.
6. `stock_objetivo = ventas_mes_actual + ventas_mes_siguiente`.
7. Clasifica `estado_stock`: Falta de stock / Stock optimo / Sobrestock.
8. Clasifica `rotacion` con `np.select`: Alta (>=10), Media (7-9), Baja (<=6).

---

## 4. Logica de negocio

### Ciclo de vida de una requisicion

```
Softland emite REQ
      |
      v
cargar_requisiciones_desde_cubo()
      |  INSERT OR IGNORE -> la requisicion existe en AppKS
      v
Usuario asigna OC manualmente en la tabla
      |  actualizar_requisicion_desde_ui() -> UPDATE oc, proveedor, fecha_oc
      v
Usuario carga cubo de compras
      |  cargar_compras_desde_dataframe() -> UPSERT en tabla compras
      |  actualizar_requisiciones_desde_compras() -> propaga estado OC -> requisicion
      v
Trigger calcular_saldo_pendiente recalcula saldo
      |
      v
Usuario marca estado_envio = 'Enviado' en la tabla
      |
      v
Recepcion: usuario registra cant_recibida
      |  registrar_recepcion() -> UPDATE cant_recibida
      |  Trigger recalcula saldo_pendiente
      v
Requisicion con saldo_pendiente = 0 -> cerrada
```

### Sincronizacion REQ -> OC

Esta es la operacion de sincronizacion mas importante del sistema. Cuando el usuario
carga el cubo de compras, AppKS propaga automaticamente el estado de cada OC hacia
la requisicion correspondiente.

**Condicion de cruce:** la requisicion debe tener una OC asignada
(`oc IS NOT NULL AND oc != ''`). La relacion se establece por dos campos: numero de
OC y codigo de producto.

**Por que un JOIN en SQL y no un loop en Python:**
- Un solo `UPDATE ... FROM` visita la tabla compras una unica vez.
- SQLite usa el indice compuesto para el JOIN (O(n log m) vs O(n x m)).
- El trigger se dispara automaticamente para cada fila actualizada.
- Codigo mas conciso y auditable.

### Reglas de asignacion de OC

La asignacion de OC a una requisicion es **manual**: el usuario escribe el numero de OC
directamente en la celda de la tabla. No hay asignacion automatica.

Esto es intencional porque:
- Una OC puede cubrir varias requisiciones (o solo parte de una).
- El criterio de correspondencia requiere juicio operativo.
- Automatizarlo generaria errores silenciosos.

Una vez asignada la OC, la sincronizacion automatica se encarga de traer el estado
desde el cubo de compras.

### INSERT OR IGNORE para requisiciones

```sql
INSERT OR IGNORE INTO requisiciones (numreq, codprod, desprod, cantidad, ...)
VALUES (?, ?, ?, ?, ...)
```

SQLite descarta silenciosamente la insercion si ya existe una fila con la misma clave
unica `(numreq, codprod)`. Esto garantiza que:
- Los datos operativos editados por el usuario nunca se sobreescriben al recargar el cubo.
- La carga es idempotente: se puede ejecutar multiples veces sin efectos secundarios.
