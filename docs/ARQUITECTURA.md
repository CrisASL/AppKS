# 🏗️ Arquitectura del Sistema – AppKS

## 📌 Visión General

AppKS es una aplicación web local construida sobre **Streamlit + SQLite**. Procesa cubos Excel exportados desde Softland ERP y centraliza la información en una base de datos local, eliminando la dependencia de planillas manuales.

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
│   │
│   ├── modules/                # Módulos de UI por dominio
│   │   └── analisis_stock/
│   │       ├── service.py      # Lógica de cruce inventario × ventas
│   │       └── view.py         # Vista Streamlit del módulo
│   │
│   └── services/               # Servicios de persistencia por cubo
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
│   (sidebar, páginas, widgets, forms)    │
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

| Tabla | Descripción | Clave única |
|---|---|---|
| `requisiciones` | Solicitudes de compra por producto | `(numreq, codprod)` |
| `compras` | Órdenes de compra (cubo Softland) | `(num_oc, codprod)` |
| `cubos_raw` | Datos crudos de cubos Excel persistidos | — |
| `cargas_diarias` | Auditoría de cargas de cubos | — |
| `archivos_cargados` | Control de hash MD5 por cubo | `nombre_cubo` |
| `historial_cambios` | Auditoría de ediciones en requisiciones | — |
| `configuracion` | Pares clave-valor del sistema | `clave` |

### Triggers

| Trigger | Tabla | Acción |
|---|---|---|
| `calcular_saldo_insert` | `requisiciones` | Calcula `saldo_pendiente` al insertar |
| `calcular_saldo_update` | `requisiciones` | Recalcula `saldo_pendiente` al actualizar |
| `auditoria_cambios` | `requisiciones` | Registra ediciones en `historial_cambios` |

---

## 📦 Módulos y Servicios

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
- Migración automática (añade columnas nuevas en BD existentes)
- Métricas de carga: insertados / actualizados / sin cambios

### `app/services/ventas_inventario_service.py`

- Persiste cubos de Ventas e Inventario en SQLite
- **Control por hash MD5**: evita reprocesar archivos Excel sin cambios
- Tabla `archivos_cargados` registra última carga por cubo

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
| UPSERT idempotente | `compras_service.py` |
| Control de versión por hash | `ventas_inventario_service.py`, `database.py` |
| Context manager para conexiones | Todos los módulos de BD |
| Migraciones incrementales | `database.py` → `migrar_base_datos_existente()` |
| Session state para persistencia de UI | `main.py` |
| Separación service / view | `modules/analisis_stock/` |
| Invalidación de caché en limpieza | `main.py` → `st.cache_data.clear()` + loop `session_state` + `st.rerun()` |
| Conteo real sin caché | `main.py` → `_contar_registros_db(tabla)` via `sqlite3` directo |

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
