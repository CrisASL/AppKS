# 🏗️ Arquitectura del Sistema – AppKS

## 📌 Visión General

AppKS es una aplicación web local construida sobre **Streamlit + SQLite**. Procesa cubos Excel exportados desde Softland ERP y centraliza la información en una base de datos local, eliminando la dependencia de planillas manuales.

Desarrollado para KS Seguridad Industrial, Sucursal Talca.

---

## 🧱 Stack Tecnológico

| Capa | Tecnología |
|---|---|
| Frontend | Streamlit (Python) |
| Backend | Python 3.10+ |
| Base de datos | SQLite 3 |
| Procesamiento | Pandas, NumPy |
| Gráficos | Plotly |
| Exportación | openpyxl |
| Empaquetado | PyInstaller |

---

## 📁 Estructura de Directorios

```
AppKS/
├── run.py                      # Entry point de Streamlit
├── start_app.py                # Launcher para compilar como .exe
├── build.bat                   # Script de compilación
├── requirements.txt
│
├── app/
│   ├── main.py                 # Aplicación principal + enrutamiento
│   ├── config.py               # Constantes, rutas y configuración global
│   ├── database.py             # Capa de acceso a datos (SQLite)
│   ├── utils.py                # Validaciones y utilidades de carga Excel
│   ├── cache.py                # Caché de lectura Excel por hash MD5
│   ├── ui.py                   # Componentes visuales reutilizables (KPIs, CSS)
│   │
│   ├── modules/                # Módulos de UI por dominio
│   │   └── analisis_stock/
│   │       ├── service.py      # Lógica de cruce inventario × ventas
│   │       └── view.py         # Vista Streamlit del módulo
│   │
│   └── services/               # Servicios de persistencia por cubo
│       ├── check_consistencia.py   # Diagnóstico de consistencia REQ↔OC
│       ├── compras_service.py
│       └── ventas_inventario_service.py
│
├── data/                       # Base de datos SQLite
├── exports/                    # Exportaciones Excel
├── backups/                    # Respaldos manuales
├── docs/                       # Documentación técnica
├── examples/                   # Scripts de referencia
└── logs/
```

---

## 🔄 Capas de la Aplicación

```
┌─────────────────────────────────────────┐
│              Streamlit UI               │  app/main.py + modules/*/view.py
│   (sidebar, páginas, widgets, forms)    │  app/ui.py (CSS, KPI components)
└────────────────────┬────────────────────┘
                     │
┌────────────────────▼────────────────────┐
│           Capa de Servicios             │  app/services/
│  (UPSERT, hash MD5, validación, sync)   │
└────────────────────┬────────────────────┘
                     │
┌────────────────────▼────────────────────┐
│        Capa de Acceso a Datos           │  app/database.py
│   (CRUD, migraciones, triggers SQL,     │
│    limpiar_cubo_* → raw + hashes)       │
└────────────────────┬────────────────────┘
                     │
┌────────────────────▼────────────────────┐
│            SQLite (archivo)             │  data/ks_requisiciones.db
└─────────────────────────────────────────┘
```

---

## 🗄️ Esquema de Base de Datos

### Tablas principales

| Tabla | Módulo | Descripción | Clave única |
|---|---|---|---|
| `requisiciones` | `database.py` | Solicitudes de compra por producto. Incluye `estado_req` y `estado_envio` (TEXT) | `(numreq, codprod)` |
| `historial_cambios` | `database.py` | Auditoría de ediciones en requisiciones | — |
| `log_eliminaciones` | `database.py` | Log de eliminaciones (soft-delete) | — |
| `configuracion` | `database.py` | Pares clave-valor del sistema + hashes MD5 | `clave` |
| `cargas_diarias` | `database.py` | Auditoría de cargas de cubos | — |
| `cubo_ventas_raw` | `database.py` | Cubo de ventas persistido (JSON) | — |
| `cubo_inventario_raw` | `database.py` | Cubo de inventario persistido (JSON) | — |
| `cubo_compras_raw` | `database.py` | Cubo de compras persistido (JSON) | — |
| `cubo_requisiciones_raw` | `database.py` | Cubo de requisiciones persistido (JSON) | — |
| `compras` | `compras_service.py` | Órdenes de compra (cubo Softland) | `(num_oc, codprod)` |
| `gestion` | `compras_service.py` | Seguimiento extendido vinculado a compras | `(numreq, codprod)` |
| `archivos_cargados` | `ventas_inventario_service.py` | Control de hash MD5 por cubo | `nombre_cubo` |

### Índices

| Índice | Tabla | Columnas |
|---|---|---|
| `idx_requisiciones_numreq` | `requisiciones` | `numreq` |
| `idx_requisiciones_codprod` | `requisiciones` | `codprod` |
| `idx_requisiciones_estado` | `requisiciones` | `estado` |
| `idx_requisiciones_oc` | `requisiciones` | `oc` |
| `idx_requisiciones_fecha_oc` | `requisiciones` | `fecha_oc` |
| `idx_historial_requisicion` | `historial_cambios` | `requisicion_id` |
| `idx_historial_req_fecha` ⭐ | `historial_cambios` | `(requisicion_id, fecha_cambio DESC)` |
| `idx_cargas_fecha` | `cargas_diarias` | `fecha` |
| `idx_compras_num_oc` | `compras` | `num_oc` |
| `idx_compras_codprod` | `compras` | `codprod` |
| `idx_compras_oc_codprod` | `compras` | `(num_oc, codprod)` |
| `idx_compras_fecha_oc` | `compras` | `fecha_oc` |
| `idx_compras_estado` | `compras` | `estado` |
| `idx_compras_proveedor` | `compras` | `proveedor` |
| `idx_gestion_numreq` | `gestion` | `numreq` |
| `idx_gestion_codprod` | `gestion` | `codprod` |
| `idx_gestion_oc` | `gestion` | `oc` |
| `idx_gestion_oc_codprod` | `gestion` | `(oc, codprod)` |
| `idx_gestion_estado` | `gestion` | `estado` |

> ⭐ Índice compuesto agregado en v1.7.0. Cubre `obtener_historial()` con index-only scan.

### Triggers

| Trigger | Tabla | Acción |
|---|---|---|
| `registrar_cambio_estado` | `requisiciones` | Inserta en `historial_cambios` al cambiar `estado` |
| `registrar_cambio_proveedor` | `requisiciones` | Inserta en `historial_cambios` al cambiar `proveedor` |
| `registrar_cambio_oc` | `requisiciones` | Inserta en `historial_cambios` al cambiar `oc` |
| `registrar_cambio_cant_recibida` | `requisiciones` | Inserta en `historial_cambios` al cambiar `cant_recibida` |
| `actualizar_fecha_modificacion` | `requisiciones` | Actualiza `fecha_modificacion` en cada UPDATE |
| `calcular_saldo_pendiente_insert` | `requisiciones` | Calcula `saldo_pendiente` al insertar |
| `calcular_saldo_pendiente_update` | `requisiciones` | Recalcula `saldo_pendiente` al actualizar |
| `calcular_total_linea_insert` | `compras` | Calcula `total_linea` al insertar |
| `calcular_total_linea_update` | `compras` | Recalcula `total_linea` al actualizar |
| `calcular_saldo_gestion_insert` | `gestion` | Calcula `saldo` al insertar |
| `calcular_saldo_gestion_update` | `gestion` | Recalcula `saldo` al actualizar |
| `actualizar_fecha_mod_gestion` | `gestion` | Actualiza `fecha_modificacion` en cada UPDATE |

---

## 📦 Módulos y Servicios

### `app/ui.py`

Componentes visuales reutilizables. Centraliza el CSS y los widgets de presentación para mantener `main.py` limpio.

- **`inject_css()`**: inyecta los estilos globales de la app (sidebar, navegación, colores, tipografía)
- **`kpi_hero()`**: métrica principal de tamaño grande con delta opcional
- **`kpi_card()`**: métrica secundaria compacta
- **`empty_state()`**: placeholder con ícono, título y subtítulo para secciones sin datos
- **`section_label()`**: etiqueta de sección para el sidebar

### `app/cache.py`

Caché de lectura de archivos Excel con `@st.cache_data`.

- **`cargar_excel()`**: lee una hoja específica de un Excel. La clave de caché combina hash MD5 del archivo + nombre de hoja + tipo de cubo, invalidando automáticamente si cualquiera de estos cambia
- Incluye lógica de limpieza para tablas pivot de Softland (detección de header real, eliminación de filas `"(en blanco)"` y `"Total"`)

### `app/database.py`

- CRUD completo para `requisiciones`, `historial_cambios`, `cargas_diarias` y tablas raw
- Inicialización de esquema, índices y triggers al arrancar
- **`actualizar_requisiciones_desde_compras()`**: sincronización REQ→OC en 3 pasos (proveedor de respaldo, match por observación, match automático). Normaliza `estado_linea` del ERP mediante `_MAPA_ESTADO_ERP` (Python) y CASE SQL antes de escribir `estado_oc`, garantizando coherencia con `config.ESTADOS_OC`
- **`actualizar_requisicion_desde_ui()`**: normaliza `fecha_oc` a `YYYY-MM-DD` con `dayfirst=True` antes de persistir; validación por whitelist para `estado_envio` y `estado_req`
- **`cargar_requisiciones_desde_cubo()`**: patrón two-pass — FASE 1 valida todas las filas sin escribir en BD (rechaza si hay errores); FASE 2 inserta en transacción atómica vía `get_db_connection()` con rollback automático. `INSERT OR IGNORE` con `UNIQUE(numreq, codprod)`
- **`get_or_load_cubo()`**: rehidratación automática de cubos desde SQLite con validación robusta
- **`obtener_estadisticas_generales()`**: retorna `total_req` (conteo real de filas) además de pendientes, tránsito y productos
- Migraciones idempotentes: `migrar_base_datos_existente()`, cubre `requisiciones` y columna `desprod` en `compras`; ejecutable múltiples veces al arrancar
- Limpieza de cubos: `limpiar_cubo_*()` elimina tablas operacionales + raw + hashes

### `app/modules/analisis_stock/`

Cruce entre cubo de Inventario y cubo de Ventas histórico para KS Talca.

**`service.py`**
- Clasifica **estado de stock**: `Falta de stock` / `Stock óptimo` / `Sobrestock`
  - Referencia: ventas del mismo mes del año anterior × 2 meses
- Clasifica **rotación**: `Alta` / `Media` / `Baja` (meses con venta > 0)

**`view.py`**
- Métricas de resumen (totales por estado y rotación)
- Filtros por estado de stock, rotación y código de producto
- Tabla ordenable con columnas de stock actual, objetivo y ventas mensuales

### `app/services/compras_service.py`

- **UPSERT inteligente** con detección de cambios (no actualiza si los datos no cambian)
- Clave compuesta `(num_oc, codprod)` para evitar duplicados
- Lookup de existencia por índice (`SELECT 1 ... LIMIT 1`) en lugar de pre-carga completa de la tabla
- **`actualizar_gestion_desde_compras()`**: sincronización con un único `UPDATE gestion SET ... FROM compras c WHERE c.num_oc = gestion.oc AND c.codprod = gestion.codprod` usando `idx_compras_oc_codprod`
- Migración automática (añade columnas nuevas en BD existentes)
- Métricas de carga: insertados / actualizados / sin cambios

### `app/services/ventas_inventario_service.py`

- Persiste cubos de Ventas e Inventario en SQLite
- **Control por hash MD5**: evita reprocesar archivos Excel sin cambios
- Tabla `archivos_cargados` registra última carga por cubo

### `app/services/check_consistencia.py`

- Diagnóstico de consistencia entre `requisiciones` y `compras`
- 4 checks: **OC sin REQ** / **REQ sin OC** (>14 días sin OC, guía ni observación) / **Montos descuadrados** (`ABS(total_linea − precio × cantidad) > 1`) / **Recepciones excedidas** (`recibida + manual > solicitada + 0.01`)
- `ejecutar_diagnostico()`: corre los 4 checks en una sola conexión, retorna DataFrames + resumen con conteos por severidad

---

## 🔁 Flujo de Datos

```
Excel (Softland ERP)
        │
        ▼
  Carga en UI  ──►  Validación de columnas (utils.py)
        │
        ▼
  Hash MD5  ──►  ¿Cambió el archivo?
        │              │
       NO              SÍ
        │              │
        ▼              ▼
  Carga desde BD   UPSERT / INSERT
        │              │
        └──────┬────────┘
               ▼
         SQLite (cubos_raw + tablas de negocio)
               │
               ▼
         Session State (Streamlit)
               │
               ▼
   Módulos de análisis y visualización
```

---

## 🧩 Patrones Implementados

| Patrón | Dónde |
|---|---|
| Carga idempotente con `INSERT OR IGNORE` | `database.py` → `cargar_requisiciones_desde_cubo()` |
| UPSERT inteligente con detección de cambios | `compras_service.py` → `cargar_compras_desde_dataframe()` |
| Control de versión por hash MD5 | `ventas_inventario_service.py`, `database.py` |
| Sincronización REQ→OC pure SQL (`UPDATE...WHERE EXISTS`, `julianday()`) | `database.py` → `actualizar_requisiciones_desde_compras()` |
| Sincronización gestion→compras con JOIN único (`UPDATE...FROM`) | `compras_service.py` → `actualizar_gestion_desde_compras()` |
| Rehidratación automática de datos | `database.py` → `get_or_load_cubo()` |
| Context manager para conexiones | Todos los módulos de BD |
| Migraciones incrementales idempotentes | `database.py` → `migrar_base_datos_existente()` |
| Session state para persistencia de UI | `main.py` |
| Separación service / view | `modules/analisis_stock/` |
| Invalidación de caché en limpieza | `main.py` → `st.cache_data.clear()` + loop `session_state` + `st.rerun()` |
| Override masivo de estado via session state | `main.py` → `estado_envio_override` / `st.rerun()` |
| Edición segura en 4 capas | UI → `utils.py` → `CAMPOS_EDITABLES_UI` (backend) → triggers SQL |
| Normalización de estados ERP → estados internos | `database.py` → `_MAPA_ESTADO_ERP` + CASE SQL en sync REQ→OC |
| AGGrid key dinámico por filtros activos | `main.py` → `_grid_key = f"aggrid_req_{hash(...)}"` |
| `set_page_config` como primera llamada Streamlit | `main.py` → `_startup_errors[]` + display en `main()` |
| Backup WAL-safe con checkpoint previo | `main.py` → `PRAGMA wal_checkpoint(FULL)` antes de `shutil.copy2` |
| Normalización de `fecha_oc` a `YYYY-MM-DD` al guardar | `database.py` → `actualizar_requisicion_desde_ui()` con `dayfirst=True` |
| Acceso a `session_state` por índice `[]` | `main.py` → `_widget_cubo_uploader()` — evita problemas de serialización |
| Validación two-pass con rechazo total antes de INSERT masivo | `utils.py` → `validar_filas_requisiciones()` + `database.py` → `cargar_requisiciones_desde_cubo()` |
| `pre_save_validator` inyectable en widget de carga | `main.py` → `_widget_cubo_uploader(pre_save_validator=...)` |

---

## 📐 Convenciones de Columnas de Estado

Las columnas que representan un estado editable por el usuario siguen el patrón `estado_* TEXT` en lugar de INTEGER/bool. Esto aplica actualmente a `estado_req` y `estado_envio` en la tabla `requisiciones`.

### Por qué TEXT y no BOOLEAN/INTEGER

| Aspecto | INTEGER (bool) | TEXT |
|---|---|---|
| AG Grid devuelve | `"true"` / `"false"` (string) | El mismo valor que se guardó |
| pandas lee | requiere `.astype(bool)` | Listo para usar |
| SQLite guarda | `0` / `1` | `'No Enviado'` / `'Enviado'` |
| Conflictos de tipo | frecuentes en round-trip | ninguno |
| Extensibilidad | solo dos valores | cualquier cantidad de estados |

### Estructura del patrón

```sql
-- Schema
estado_envio TEXT DEFAULT 'No Enviado'

-- Migración idempotente
IF "estado_envio" NOT IN columnas_existentes:
    ALTER TABLE requisiciones ADD COLUMN estado_envio TEXT DEFAULT 'No Enviado'
```

```python
# config.py
ESTADOS_ENVIO = ["No Enviado", "Enviado"]  # primer elemento = default

# utils.py – normalización al preparar el df
df["estado_envio"] = df["estado_envio"].fillna("No Enviado").astype(str)

# database.py – validación al guardar
valor = valor if valor in config.ESTADOS_ENVIO else "No Enviado"
```

### Cómo agregar un nuevo estado o columna de estado

1. Definir la constante en `config.py`: `ESTADOS_NUEVA = ["A", "B", "C"]`
2. Agregar la columna en el schema `CREATE TABLE` de `database.py`
3. Agregar el bloque de migración idempotente en `migrar_base_datos_existente()`
4. Agregar la normalización en `preparar_df_para_edicion_segura()` en `utils.py`
5. Agregar el bloque de validación en `actualizar_requisicion_desde_ui()` de `database.py`
6. Configurar la columna en el AG Grid de `main.py` con `agSelectCellEditor` y `cellStyle` JsCode

---

## 🚀 Ejecución

### Desarrollo

```bash
streamlit run run.py
```

### Usuario final

```
AppKS.exe  →  start_app.py  →  subprocess: streamlit run run.py
                                            └── abre navegador en localhost:8501
```

El `.exe` (~8 MB) es un launcher minimalista. Requiere `venv\` con dependencias instaladas en la misma raíz del proyecto.
