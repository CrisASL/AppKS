# AppKS – Sistema de Gestión Operativa

Sistema web interno desarrollado en Python para gestionar **Requisiciones, Compras, Ventas e Inventario**, eliminando la dependencia de planillas Excel. Procesa cubos exportados desde un ERP (Softland) y centraliza la información en una base de datos SQLite local.

> **Contexto:** Proyecto desarrollado a partir de necesidades operativas reales identificadas en un entorno de abastecimiento industrial. Actualmente en fase de validación antes de su implementación.

---

## ¿Qué problema resuelve?

En entornos de abastecimiento industrial, el seguimiento de requisiciones y órdenes de compra suele depender de planillas Excel manuales: datos duplicados, sin historial de cambios, sin sincronización entre áreas. AppKS reemplaza ese flujo con una base de datos local, carga automatizada desde el ERP y una interfaz web accesible sin instalación adicional.

---

## Tecnologías

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

## Arquitectura

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
│   ├── modules/
│   │   └── analisis_stock/
│   │       ├── service.py      # Lógica de cruce inventario × ventas
│   │       └── view.py         # Vista Streamlit del módulo
│   │
│   └── services/
│       ├── compras_service.py
│       └── ventas_inventario_service.py
│
├── data/                       # Base de datos SQLite
├── exports/                    # Exportaciones Excel
├── backups/                    # Respaldos manuales
└── docs/                       # Documentación técnica
```

Arquitectura en capas: **UI → Services → Data Access Layer → SQLite**

---

## Módulos

| Módulo | Estado | Descripción |
|---|---|---|
| Requisiciones | ✅ Operativo | Gestión de solicitudes de compra con edición segura inline |
| Compras | ✅ Operativo | Seguimiento de OC con UPSERT inteligente y filtros avanzados |
| Análisis Stock | ✅ Operativo | Clasificación de productos por estado de stock y rotación |
| Ventas | 🔧 En desarrollo | Módulo de ventas con análisis de tendencias |
| Inventario | 🔧 En desarrollo | Vista de inventario integrada |

---

## Decisiones técnicas destacadas

**Carga idempotente con clave compuesta**
Las requisiciones usan `UNIQUE(numreq, codprod)` con `INSERT OR IGNORE`, lo que permite recargar el cubo diariamente sin duplicar ni sobrescribir datos históricos.

**UPSERT inteligente en compras**
El servicio de compras detecta cambios antes de actualizar: solo ejecuta `UPDATE` si los datos realmente cambiaron, optimizando operaciones en la base de datos.

**Control de versión por hash MD5**
Los cubos de ventas e inventario registran su hash en SQLite. Si el archivo no cambió, se carga desde la base de datos sin reprocesar el Excel.

**Sincronización automática REQ → OC (pure SQL)**
Al cargar el cubo de compras, el sistema actualiza automáticamente las requisiciones mediante un único `UPDATE ... WHERE EXISTS` con subconsultas correlacionadas. Usa `julianday()` para aritmética de fechas dentro de SQLite (ventana 0–90 días, OC con cantidad ≥ 80% de la REQ, selecciona la más cercana en el tiempo). Sin loops Python ni round-trips por fila.

**Sincronización gestion → compras (JOIN único)**
`actualizar_gestion_desde_compras()` ejecuta un solo `UPDATE gestion SET ... FROM compras c WHERE c.num_oc = gestion.oc AND c.codprod = gestion.codprod`, aprovechando el índice `idx_compras_oc_codprod` en un único paso.

**Launcher minimalista**
En lugar de empaquetar Streamlit completo (~99 MB), el `.exe` es un launcher de ~8 MB que invoca `streamlit run` en el entorno virtual del proyecto vía `subprocess`. Más simple, más mantenible.

**Edición segura inline**
La edición de requisiciones usa AG Grid con columnas estrictamente tipadas. Las columnas de estado (`estado_req`, `estado_envio`) son TEXT con validación por whitelist en backend, eliminando conflictos de dtype entre AG Grid (strings), pandas y SQLite. El patrón de override via `session_state` permite acciones masivas (bulk-set) sin recargar datos desde BD.

**Migraciones idempotentes**
El esquema se actualiza automáticamente al arrancar la app. Las migraciones verifican existencia antes de modificar, ejecutables múltiples veces sin errores.

---

## Cómo ejecutar

### Modo desarrollo

```bash
# 1. Crear entorno virtual (primera vez)
python -m venv venv

# 2. Activar
venv\Scripts\activate          # Windows
source venv/bin/activate       # Mac/Linux

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Ejecutar
streamlit run run.py
```

### Launcher .exe (usuario final)

Coloca `AppKS.exe` en la raíz del proyecto junto a `run.py` y la carpeta `venv\`, y ejecuta con doble clic.

```
AppKS/
├── AppKS.exe    ← doble clic
├── run.py
└── venv\
```

> El `.exe` no es autocontenido: delega en el entorno virtual del proyecto. Esto mantiene el ejecutable pequeño y facilita actualizaciones.

### Recompilar el .exe

```bat
build.bat
```

---

## Estado actual

**v1.8.0** – En fase de validación

- Arquitectura modular por servicios (UI / Services / DAL)
- Carga idempotente con clave compuesta para requisiciones y compras
- UPSERT inteligente con detección de cambios
- Control de versión por hash MD5 en cubos de ventas e inventario
- Sincronización automática REQ → OC: pure SQL con `UPDATE ... WHERE EXISTS`, `julianday()` para aritmética de fechas, ventana 0–90 días
- Sincronización gestion → compras: `UPDATE gestion SET ... FROM compras` en un único JOIN pass
- Índice compuesto `idx_historial_req_fecha` en `historial_cambios(requisicion_id, fecha_cambio DESC)`
- Módulo Análisis Stock: estado de stock y rotación de productos
- Edición segura inline en 4 capas (UI → validación → backend → triggers SQL)
- Estados de columna como TEXT con whitelist (`estado_req`, `estado_envio`) — elimina conflictos de tipo entre AG Grid, pandas y SQLite
- Migraciones de esquema automáticas e idempotentes
- Invalidación completa de caché al eliminar cubos (tablas raw + hashes + session state)
- Launcher `.exe` minimalista (~8 MB)

---

## Autor

Cristian Salas – [LinkedIn](https://www.linkedin.com/in/cristian-salas-lizana-b101a18a/)

Proyecto de gestión operativa desarrollado con apoyo de IA (Claude, ChatGPT).