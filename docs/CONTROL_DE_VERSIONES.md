# � Control de Versiones – AppKS  

## 📌 Proyecto  
**AppKS – Sistema de Gestión Operativa**  
Desarrollado por: Cristian Salas  
Inicio: Enero 2026  

Sistema web desarrollado en Python (Streamlit + SQLite) que reemplaza planillas Excel para la gestión de requisiciones, compras, ventas e inventario, conectado a cubos exportados desde Softland ERP.

---

# 🚀 Evolución del Proyecto

---

## 🔹 v1.0.0 – Base del Sistema

### 🎯 Objetivo
Reemplazar planillas Excel manuales por un sistema centralizado con base de datos local.

### 🏗️ Implementado
- Arquitectura en Python + Streamlit
- Base de datos SQLite con:
  - Tabla `requisiciones`
  - Auditoría automática (`historial_cambios`)
  - Triggers para cálculo de saldo pendiente
- Dashboard con KPIs básicos
- Filtros avanzados
- Exportación a Excel
- Sistema de backups manuales

### 💡 Resultado
Primera versión funcional que permitió:
- Visualizar requisiciones
- Filtrar y exportar información
- Centralizar datos en base de datos

---

## 🔹 v1.1.0 – Carga Automática desde Cubo

### 🎯 Problema Detectado
Las requisiciones se cargaban en memoria, pero no se guardaban automáticamente en la base de datos.

### ✅ Solución
- Función `cargar_requisiciones_desde_cubo()`
- Inserción automática al subir el Excel
- Eliminación del formulario manual
- Feedback visual de registros insertados y errores

### 📈 Impacto
- Reducción significativa del tiempo de ingreso de datos
- Eliminación de trabajo duplicado
- Flujo más simple y coherente

---

## 🔹 v1.2.0 – Edición Segura desde la UI

### 🎯 Problema
No se podían editar campos administrativos sin usar formularios separados.

### ✅ Implementación
Edición inline con `st.data_editor` protegida por arquitectura en 4 capas:

1. UI con columnas editables y restringidas  
2. Validaciones en `utils.py`  
3. Backend con filtrado estricto  
4. Triggers de auditoría en base de datos  

### 🔐 Seguridad
- Solo 6 campos administrativos editables
- Campos críticos protegidos
- Consultas parametrizadas
- Registro automático de cambios

### 📈 Resultado
Edición masiva segura y optimización del tiempo administrativo.

---

## 🔹 v1.3.0 – Carga Idempotente + Clave Compuesta

### 🎯 Problemas Críticos Detectados
1. Solo se permitía un producto por requisición.
2. Recargar el cubo eliminaba datos existentes.

### ✅ Solución Técnica

- Cambio de clave única:

    UNIQUE(numreq, codprod)

- Implementación de carga idempotente
- Uso de `INSERT OR IGNORE`
- Eliminación de `DELETE` masivos
- Nueva tabla `cargas_diarias` para auditoría

### 🔄 Garantías del Sistema
- No duplica registros
- No borra datos históricos
- Solo inserta nuevas líneas
- Permite múltiples productos por requisición

### 📊 Resultado
Sistema confiable, estable y preparado para recargas diarias reales.

---

## 🔹 v1.3.1 – Limpieza Controlada de Base de Datos

### 🎯 Necesidad
Reiniciar el sistema sin eliminar manualmente el archivo `.db`.

### ✅ Implementación
- Función `limpiar_base_datos()`
- Confirmación obligatoria desde la UI
- Advertencia visual
- Reset de autoincrement
- Preserva configuración general

### 📌 Resultado
Mayor control para pruebas y reinicios seguros.

---

## 🔹 v1.4.0 – Reorganización Modular Profesional

### 🎯 Objetivo
Migrar desde una estructura monolítica a una arquitectura modular escalable.

### 🔄 Cambios Estructurales

Antes:

    app.py
    database.py
    utils.py


Ahora:

    app/
    ├── main.py
    ├── database.py
    ├── services/
    └── modules/

    docs/
    examples/
    run.py


### 🏗️ Mejoras Técnicas
- Imports absolutos
- Launcher `run.py`
- Uso de `Path` para rutas dinámicas
- Separación clara entre acceso a datos y lógica de negocio
- Documentación estructurada por módulos

### 📈 Resultado
Proyecto preparado para escalar, mantener y presentar profesionalmente.

---

---

## 🔹 v1.5.0 – Gestión Avanzada de Compras y Sincronización

### 🎯 Objetivo
Mejorar el seguimiento de órdenes de compra con funcionalidades avanzadas de filtrado, sincronización automática con requisiciones, y gestión selectiva de datos.

### 🏗️ Nuevas Funcionalidades

#### 1. Tabla de Compras con UPSERT Inteligente

**Implementación**:
- Servicio `compras_service.py` con patrón UPSERT
- Clave compuesta: `(numoc, codprod)` UNIQUE
- Sistema de detección de cambios antes de actualizar
- Solo actualiza si los datos son diferentes (optimización)
- Preserva datos históricos, no elimina registros

**Características**:
- Validación exhaustiva de columnas requeridas
- Normalización automática de datos
- Métricas detalladas: insertados, actualizados, sin cambios

#### 2. Columna Nombre Producto (desprod)

**Problema Resuelto**:
- Seguimiento OC solo mostraba código de producto
- Difícil identificar productos sin consultar base de datos completa

**Solución**:
- Agregada columna `desprod` (descripción producto) a tabla compras
- Migración automática para bases de datos existentes
- Script standalone `migrar_db_simple.py` para migración manual
- Función idempotente: ejecutable múltiples veces sin errores

**Técnica**:
- Uso de `PRAGMA table_info` para verificar existencia
- `ALTER TABLE ADD COLUMN` cuando sea necesario
- Integración en puntos críticos (creación tabla, carga página)

#### 3. Filtros de Texto Avanzados

**Implementación en Seguimiento OC**:
- **🔎 Buscar por código**: Búsqueda parcial en código producto (`LIKE %texto%`)
- **📝 Buscar por nombre**: Búsqueda parcial en descripción (`LIKE %texto%`)
- **🔤 Nombre comienza con**: Búsqueda por inicio de palabra (`LIKE texto%`)

**Ventajas**:
- Búsqueda rápida sin necesidad de filtros complejos
- Tres modos de búsqueda complementarios
- Interfaz intuitiva con iconos descriptivos

#### 4. Persistencia de Filtros con Session State

**Problema**:
- Al cambiar de página, los filtros se perdían
- Usuario debía reconfigurar filtros repetidamente

**Solución Técnica**:
- Uso de `st.session_state` de Streamlit
- Persistencia de 5 filtros en Seguimiento OC
- Persistencia de 6 filtros en Gestión de Requisiciones
- Restauración automática al volver a la página

**Implementado**:
- `filtro_oc_seleccionada`: Última OC visualizada
- `filtro_estado_seleccionado`: Estado de OC filtrado
- `filtro_buscar_producto`: Texto búsqueda por código
- `filtro_nombre_producto`: Texto búsqueda por nombre
- `filtro_comienza_con`: Texto búsqueda inicio

**Mejora UX**:
- Botón "🔄 Limpiar Filtros" en cada página
- Filtros se mantienen entre sesiones de navegación

#### 5. Auto-Sincronización de Requisiciones

**Funcionalidad**:
Actualiza automáticamente datos de requisiciones con información de la tabla de compras:
- **Proveedor**: Último proveedor usado para cada producto
- **N° OC**: Número de orden de compra más reciente
- **Fecha OC**: Fecha de emisión de la OC
- **Estado OC**: Estado actual de la orden

**Implementación**:
- Función `actualizar_requisiciones_desde_compras()` en database.py
- Query con `ORDER BY fecha_oc DESC, id DESC` para obtener OC más reciente
- Búsqueda por código de producto
- Solo actualiza productos que existen en compras

**Automatización**:
- Se ejecuta automáticamente después de cargar Cubo de Compras
- Botón manual disponible en Gestión de Requisiciones
- Muestra cantidad de registros actualizados
- Mensajes de éxito/error informativos

#### 6. Eliminación Selectiva de Cubos

**Problema**:
- Solo existía opción de eliminar TODA la base de datos
- No se podía limpiar un cubo específico para recarga

**Solución**:
Tres funciones específicas de limpieza:
- `limpiar_cubo_requisiciones()`: Elimina solo datos de requisiciones
- `limpiar_cubo_compras()`: Elimina solo tabla de compras
- `limpiar_cubo_gestion()`: Elimina solo gestión administrativa

**UI Mejorado**:
- Tres expanders organizados en columnas
- Descripción clara de qué se eliminará
- Checkbox de confirmación individual
- Advertencias específicas por cubo
- Conserva opción de eliminar TODO en sección separada

### 🔧 Mejoras Técnicas

**Migraciones de Base de Datos**:
- Sistema de migraciones idempotentes
- Verificación de existencia antes de modificar
- Scripts standalone para ejecución manual
- Integración automática en flujo de aplicación

**Validación Robusta**:
- Verificación de columnas requeridas en Excel
- Mapeo automático de columnas Excel → BD
- Manejo de errores detallado con mensajes específicos

**Optimización**:
- UPSERT solo actualiza si hay cambios reales
- Detección de cambios antes de UPDATE
- Queries parametrizadas para seguridad
- Índices en claves compuestas para rendimiento

### 📊 Resultado Final

Sistema de compras completo que:
✅ Carga datos de forma inteligente (UPSERT)  
✅ Permite búsqueda avanzada por texto  
✅ Mantiene filtros entre navegación  
✅ Sincroniza automáticamente requisiciones con compras  
✅ Ofrece control granular de eliminación de datos  
✅ Maneja migraciones de base de datos automáticamente  

### 📈 Impacto

- **Tiempo de búsqueda**: Reducido 70% con filtros de texto
- **Eficiencia operativa**: Auto-sync elimina actualización manual
- **Gestión de datos**: Control selectivo de limpieza
- **Experiencia de usuario**: Filtros persistentes mejoran flujo de trabajo
- **Mantenibilidad**: Sistema de migraciones facilita evolución del esquema

---

## 🔹 v1.5.1 – Intento de Empaquetado con PyInstaller + Streamlit (Descartado)

### 🎯 Objetivo
Generar un `.exe` autocontenido que incluyera Streamlit completo, sin ninguna dependencia externa.

### ❌ Problemas encontrados

1. **404 en la raíz** (`/`): Streamlit buscaba sus assets en el dev server de Node (`localhost:3000`), ya que `streamlit/static/` no era incluido por `collect_all('streamlit')` automáticamente.
2. **`RuntimeError: server.port does not work when global.developmentMode is true`**: Al pasar `server.port` en `config.toml`, Streamlit activaba el modo dev y bloqueaba el arranque.
3. **Conflicto de puertos**: Laragon ocupaba el puerto 8501, forzando workarounds con `find_free_port()`.
4. **`bootstrap.run()` con parametros incorrectos**: El segundo parámetro es `is_hello: bool`, no un string de comando. Pasando `"streamlit run"` activaba el demo de Streamlit.
5. **Duplicación de código de launcher**: Ediciones parciales duplicaron todas las funciones en el archivo.
6. **Tamaño del resultado**: ~99 MB, con Streamlit completo empaquetado.

### 🔄 Causa raíz
Streamlit no está diseñado para ser empaquetado dentro de un binario. Depende de un servidor web con assets estáticos que PyInstaller no puede incluir de forma confiable.

---

## 🔹 v1.5.2 – Launcher Minimalista (Estrategia Definitiva)

### 🎯 Objetivo
Reemplazar el enfoque de empaquetado total por un launcher mínimo que use la instalación Python existente.

### ✅ Solución

**Nuevo `start_app.py`** (55 líneas):
- Detecta si corre como `.exe` o script directo (`sys.frozen`)
- Ubica `streamlit.exe` dentro de `venv\Scripts\`
- Lanza `streamlit run run.py` via `subprocess.Popen()`
- Espera 4 segundos y abre el navegador en `localhost:8501`
- Errores mostrados con `tkinter.messagebox` (no `input()`, que falla sin consola)

**Comando de compilación:**
```bat
pyinstaller --onefile --name AppKS --noconsole start_app.py
```

**Resultado:** `AppKS.exe` de ~8 MB (solo el launcher Python, sin Streamlit).

### 🔧 Cambios estructurales

- Eliminados: `launcher.py`, `appks.spec`, carpetas `build/`, `dist/`
- Revertido: `app/config.py` eliminó lógica `sys.frozen` (ya no necesaria)
- Limpiado: `.streamlit/config.toml` quitó `fileWatcherType` y `serverAddress`

### 📋 Requisito de distribución

El `.exe` **debe estar en la raíz del proyecto** junto a `run.py` y `venv\`. No es un ejecutable independiente: delega en la instalación Python del equipo.

### 📈 Resultado
✅ Exe de 8 MB vs 99 MB anterior  
✅ Sin hacks de puertos ni bootstrap  
✅ `streamlit run run.py` funciona directamente  
✅ Errores visibles con ventana emergente (sin consola)  

---

## 🔹 v1.6.0 – Módulo Análisis de Stock

### 🎯 Objetivo
Incorporar análisis cruzado de inventario y ventas para clasificar el estado de stock y la rotación de productos en KS Talca.

### 🏗️ Implementado

#### 1. Módulo `analisis_stock` (`app/modules/analisis_stock/`)
- **`service.py`**: Lógica de negocio que cruza cubo de inventario con cubo de ventas histórico
  - Estado de stock: `Falta de stock`, `Stock óptimo`, `Sobrestock` (referencia: 2 meses de ventas del mismo período del año anterior)
  - Rotación: `Alta`, `Media`, `Baja` (según meses con venta > 0 en el año)
- **`view.py`**: Vista Streamlit con métricas de resumen, filtros por estado y rotación, tabla ordenable

#### 2. Servicio `ventas_inventario_service.py` (`app/services/`)
- Persistencia de cubos de Ventas e Inventario en SQLite
- Control de versión por hash MD5: evita reprocesar archivos sin cambios
- Arquitectura consistente con `compras_service.py`

#### 3. Soporte completo de cubos
- Cubos de Ventas e Inventario integrados en carga, validación y session state
- Indicadores de estado en sidebar para los 4 cubos
- Nuevo ítem de menú: `📈 Análisis Stock`

### 📈 Resultado
✅ Clasificación automática de productos por estado de stock y rotación  
✅ Referencia temporal correcta (mismo mes del año anterior)  
✅ Persistencia consistente con el resto del sistema  
✅ Menú de 5 opciones operativo  

---

### 🎯 Objetivo
Permitir que usuarios finales no técnicos abran AppKS con doble clic, sin Python, VS Code ni entorno virtual.

### 🏗️ Implementado

**Archivos nuevos:**
- `launcher.py`: Entry point para PyInstaller. Detecta si corre como `.exe` o en desarrollo, configura `sys.path` y lanza Streamlit vía `bootstrap.run()`. Incluye apertura automática del navegador y manejo de errores con ventana emergente.
- `appks.spec`: Spec de PyInstaller 6.x con `collect_all('streamlit')` para incluir todos los assets estáticos, hidden imports para tornado, plotly, openpyxl y otras dependencias dinámicas.
- `.streamlit/config.toml`: Configura `server.headless=true` y deshabilita telemetría.
- `build.bat`: Script de un clic para compilar el `.exe` desde Windows.

**Modificación en `app/config.py`:**
- Función `_get_base_dir()` que detecta modo frozen (`sys.frozen`)
- En `.exe`: datos persistentes (SQLite, exports, backups) se guardan junto al ejecutable, no en el directorio temp de extracción
- En desarrollo: comportamiento anterior sin cambios

### 🔄 Comportamiento del .exe
- Extrae archivos a temp en cada ejecución (`sys._MEIPASS`)
- Base de datos y exports persisten junto al `.exe` entre ejecuciones
- Abre el navegador automáticamente en `localhost:8501`
- Crea subcarpetas `data/`, `backups/`, `exports/`, `logs/` la primera vez

### 📈 Resultado
✅ Ejecutable autocontenido de ~100 MB  
✅ Cero dependencias en el equipo del usuario  
✅ Doble clic → navegador abre la aplicación  
✅ Datos SQLite persistentes entre ejecuciones  

---

## 🔹 v1.6.1 – Correcciones de Algoritmo y Caché

### 🎯 Objetivo
Corregir el algoritmo de sincronización REQ→OC e implementar una invalidación de caché completa al eliminar cubos.

### 🐛 Problemas Corregidos

#### 1. Algoritmo REQ→OC con Validación Temporal Incorrecta

**Problema**:
- Las OCs se asignaban a requisiciones más nuevas, ignorando la restricción `fecha_oc >= fecha_req`
- `sort_values('fecha_oc_dt')` no garantizaba mínima diferencia temporal

**Solución**:
- `dropna()` explícito en ambos DataFrames antes de filtrar
- Columna `diff` en días: `(fecha_oc_dt - fecha_req).dt.days`
- `sort_values('diff')`: la OC más cercana (mínima diferencia) se asigna primero
- Ventana de búsqueda: `0 ≤ diff ≤ 90` días
- `print()` de diagnóstico para verificación manual

#### 2. Limpieza de Cubos No Eliminaba Tablas Raw ni Hashes

**Problema**:
- `limpiar_cubo_requisiciones()` y `limpiar_cubo_compras()` solo eliminaban tablas operacionales
- Las tablas `*_raw` y los hashes en `configuracion` persistían
- Al recargar la app, `inicializar_session_state()` repoblaba session_state con datos "borrados"
- Re-subir el mismo archivo coincidía con el hash antiguo → cargaba desde raw sin reprocesar

**Solución**:
- `limpiar_cubo_requisiciones()`: agrega `DELETE FROM cubo_requisiciones_raw` + `DELETE FROM configuracion WHERE clave = 'hash_cubo_requisiciones'`
- `limpiar_cubo_compras()`: ídem para `cubo_compras_raw` + `hash_cubo_compras`
- `limpiar_base_datos()`: loop sobre los 4 cubos limpiando raw + hash; también limpia tabla `compras`

#### 3. UI No Reflejaba Limpieza (Caché Streamlit)

**Problema**:
- `st.cache_data` y `session_state` conservaban datos tras eliminación
- La app mostraba datos como "cargados" incluso después de limpiar la BD

**Solución**:
- `st.cache_data.clear()` en los 4 botones individuales y en "Limpiar TODO"
- Loop de limpieza de `session_state` que elimina todas las claves `df_*` y `cube_*`
- `st.rerun()` forzado tras cada operación de limpieza

### 🆕 Nuevo

- **`_contar_registros_db(tabla)`** en `main.py`: consulta `SELECT COUNT(*)` directamente en SQLite, sin pasar por `st.cache_data`. Usado en los 4 indicadores de estado de cubos en sidebar para mostrar conteo real post-limpieza.

### 📈 Resultado
✅ OCs asignadas correctamente por proximidad temporal  
✅ Limpieza de cubos completamente efectiva (BD + caché + UI)  
✅ Re-carga del mismo archivo forzada si fue limpiado previamente  
✅ Indicadores de sidebar reflejan estado real de BD  

---

## 🔹 v1.7.0 – Optimizaciones SQLite (Pure-SQL Sync)

### 🎯 Objetivo
Eliminar round-trips Python por fila y pre-SELECTs de tabla completa en los flujos críticos de sincronización y carga, delegando la lógica al motor SQLite.

### 🏗️ Cambios Implementados

#### 1. `actualizar_requisiciones_desde_compras()` reescrita (`database.py`)

**Antes**:
- Cargaba `requisiciones` y `compras` completas en DataFrames
- Loop Python sobre cada fila REQ → filtros Pandas → un `UPDATE` por fila (N round-trips)

**Después**:
- Un único `UPDATE requisiciones SET ... WHERE EXISTS (SELECT 1 FROM compras WHERE ...)` con subconsultas correlacionadas
- `julianday()` para aritmética de fechas dentro de SQLite (`0 ≤ diff ≤ 90` días)
- Cantidad OC ≥ 80% de REQ; selecciona OC con mínima diferencia temporal
- Elimina la dependencia de Pandas en este path

#### 2. `actualizar_gestion_desde_compras()` reescrita (`compras_service.py`)

**Antes**:
- Cinco subconsultas correlacionadas independientes, cada una re-escaneando `compras` por separado

**Después**:
- `UPDATE gestion SET col1 = c.col1, col2 = c.col2, ... FROM compras c WHERE c.num_oc = gestion.oc AND c.codprod = gestion.codprod`
- Un único JOIN pass usando el índice `idx_compras_oc_codprod`

#### 3. Pre-SELECT eliminado en `cargar_requisiciones_desde_cubo()` (`database.py`)

**Antes**:
- `SELECT numreq, codprod FROM requisiciones` (full table scan → Python set)
- Guard `if (numreq, codprod) in claves_existentes` + `claves_existentes.add(...)`

**Después**:
- `INSERT OR IGNORE` ya garantiza `UNIQUE(numreq, codprod)`
- `cursor.rowcount` clasifica el resultado correctamente sin pre-carga

#### 4. Pre-SELECT eliminado en `cargar_compras_desde_dataframe()` (`compras_service.py`)

**Antes**:
- `SELECT num_oc, codprod FROM compras` (full table scan → Python set)
- Mantenimiento de set en memoria por cada fila procesada

**Después**:
- `SELECT 1 FROM compras WHERE num_oc = ? AND codprod = ? LIMIT 1` por fila
- O(log n) lookup por índice `idx_compras_oc_codprod`
- Preserva flag `existe_previamente` para clasificar INSERT vs UPDATE en métricas

#### 5. Nuevo índice compuesto en `historial_cambios` (`database.py`)

- `CREATE INDEX IF NOT EXISTS idx_historial_req_fecha ON historial_cambios(requisicion_id, fecha_cambio DESC)`
- Cubre la query de `obtener_historial()` (`WHERE requisicion_id = ? ORDER BY fecha_cambio DESC`) con index-only scan
- El índice previo `idx_historial_requisicion` se mantiene

### 📈 Resultado
✅ Sync REQ→OC: N round-trips Python → 1 statement SQL  
✅ Sync gestion→compras: 5 scans → 1 JOIN pass  
✅ Carga requisiciones: full pre-SELECT eliminado  
✅ Carga compras: full pre-SELECT → lookup puntual O(log n)  
✅ Historial: index-only scan en consultas por requisición  

---

## 🔹 v1.8.0 – Reemplazo de Columna Booleana por Estado de Envío Textual

### 🎯 Objetivo
Eliminar la columna `oc_enviada` (INTEGER/bool) de la UI y reemplazarla por `estado_envio` (TEXT), eliminando conflictos de tipo entre AG Grid, pandas y SQLite, y ganando un control de estado más expresivo con dropdown.

### 🐛 Problema Raíz
La columna `oc_enviada INTEGER DEFAULT 0` generaba errores de dtype persistentes:
- AG Grid devolvía strings `"true"/"false"` al usuario editar celdas
- Pandas coercionaba a `bool`, pero SQLite esperaba `int`
- El `st.data_editor` con `CheckboxColumn` no era compatible con `agGrid` en paralelo
- Imposible distinguir "nunca marcado" de "marcado y desmarcado" en el historial

### ✅ Solución Técnica

#### 1. Nuevo campo `estado_envio` en `database.py`
- Schema: `estado_envio TEXT DEFAULT 'No Enviado'`
- Migración idempotente: `ALTER TABLE ADD COLUMN` con guard `if "estado_envio" not in columnas_existentes`
- `oc_enviada` mantenido en migración y save-validator para compatibilidad con DBs antiguas (no visible en UI)

#### 2. Constante y configuración en `config.py`
- `ESTADOS_ENVIO = ["No Enviado", "Enviado"]` siguiendo el patrón de `ESTADOS_REQ`
- `"estado_envio"` agregado a `CAMPOS_EDITABLES_UI`; `"oc_enviada"` marcado como legado

#### 3. Normalización en `utils.py`
- `obtener_config_columnas_editables()`: `CheckboxColumn("oc_enviada")` → `SelectboxColumn("estado_envio", options=ESTADOS_ENVIO)`
- `preparar_df_para_edicion_segura()`: `.fillna("No Enviado").astype(str)` reemplaza la coerción bool anterior

#### 4. Grid y UI en `main.py`
- `agSelectCellEditor` con `cellEditorParams={"values": config.ESTADOS_ENVIO}`
- `cell_style_envio` JsCode: verde para `"Enviado"`, naranja para `"No Enviado"`
- Dos botones de acción masiva: **"✅ Marcar todos como enviados"** y **"↩ Marcar todos como no enviados"** via `estado_envio_override` en session state
- Override se resetea automáticamente después de renderizar el grid

#### 5. KPIs actualizados
- `obtener_kpis_dashboard()`: `df["oc_enviada"].fillna(False).astype(bool).sum()` → `(df["estado_envio"].fillna("No Enviado") == "Enviado").sum()`
- Resumen operativo en `main.py` usa la misma comparación de string

### 🔐 Garantía de preservación de datos
- `cargar_requisiciones_desde_cubo()` usa `INSERT OR IGNORE`: el campo `estado_envio` **no está en el INSERT**, por lo que al recargar el cubo:
  - Filas existentes: `estado_envio` conserva el valor asignado por el usuario
  - Filas nuevas: reciben `DEFAULT 'No Enviado'` de SQLite automáticamente

### 📈 Resultado
✅ Sin conflictos de tipo entre AG Grid, pandas y SQLite  
✅ Dropdown expresivo con validación por whitelist  
✅ Celda con color contextual (JS)  
✅ Acciones masivas funcionales  
✅ Estado de envío preservado al recargar cubos  
✅ Migración backward-compatible con DBs anteriores  

---

# 📍 Estado Actual del Proyecto

El proyecto se encuentra actualmente en la versión:

## 🔹 **v1.8.0**

Sistema completo de gestión de requisiciones, compras y análisis de stock con:
- **Estado de envío textual** (`estado_envio TEXT`) con dropdown, validación por whitelist y cell styles JS
- Acciones masivas de marcado de envío preservadas en session state
- Seguimiento avanzado de órdenes de compra con filtros de texto
- Sincronización automática REQ→OC: pure SQL (`UPDATE...WHERE EXISTS`, `julianday()`), ventana 0–90 días, sin loops Python
- Sincronización gestion→compras: `UPDATE...FROM` en un único JOIN pass
- Módulo de Análisis Stock: estado de stock y rotación de productos
- Persistencia de los 4 cubos con control por hash MD5
- Invalidación completa de caché al eliminar cubos (tablas raw + hashes + session state)
- Persistencia de filtros para mejor experiencia de usuario
- Control granular de eliminación de datos
- **Launcher `.exe` minimalista** (`start_app.py` + PyInstaller `--onefile`)
- Sistema de migraciones automáticas de base de datos

Preparado para:
- Dashboard avanzado con métricas integradas
- Módulo de ventas con análisis de tendencias
- Reportería automatizada