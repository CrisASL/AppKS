# 🎯 Guía de Ejecución - AppKS v1.4.0

## 📂 Nueva Estructura del Proyecto

```
APPKS/
│
├── app/                        # 📦 Paquete principal de la aplicación
│   ├── __init__.py
│   ├── main.py                 # ⭐ Aplicación principal (antes app.py)
│   ├── database.py             # 🗄️ Gestión de SQLite
│   ├── config.py               # ⚙️ Configuración
│   ├── utils.py                # 🛠️ Utilidades
│   │
│   ├── services/               # 📊 Servicios de lógica de negocio
│   │   ├── __init__.py
│   │   └── compras_service.py
│   │
│   └── modules/                # 🧩 Módulos reutilizables
│       └── __init__.py
│
├── docs/                       # 📚 Documentación
│   ├── ACTUALIZACION_v1.3.0.md
│   ├── BITACORA.md
│   ├── CARGA_IDEMPOTENTE.md
│   ├── COMPRAS_RESUMEN_TECNICO.md
│   ├── COMPRAS_SERVICE_GUIA.md
│   └── IMPLEMENTACION_COMPRAS_COMPLETA.md
│
├── examples/                   # 🧪 Scripts de ejemplo
│   ├── bosquejo_tabla_editable.py
│   └── ejemplo_integracion_compras.py
│
├── data/                       # 💾 Base de datos
│   └── ks_requisiciones.db
│
├── backups/                    # 🔄 Respaldos
├── exports/                    # 📤 Exportaciones
├── logs/                       # 📋 Logs
│
├── requirements.txt            # 📦 Dependencias
├── README.md                   # 📖 Documentación principal
└── .gitignore                  # 🚫 Archivos ignorados

```

---

## 🚀 Cómo Ejecutar la Aplicación

### Paso 1: Activar Entorno Virtual (si existe)

```powershell
.\venv\Scripts\Activate.ps1
```

Deberías ver `(venv)` al inicio de tu línea de comandos.

### Paso 2: Ejecutar la Aplicación

**Comando principal** (RECOMENDADO):

```powershell
streamlit run run.py
```

La aplicación se abrirá en `http://localhost:8501`

### Alternativa: Con Python directamente

```powershell
python -m streamlit run run.py
```

### ⚠️ Importante

- **Ejecutar desde la raíz del proyecto** (carpeta `AppKS/`)
- **NO ejecutes** `streamlit run app/main.py` directamente (causará error de imports)
- El archivo `run.py` es un launcher que configura el path correctamente

---

## 📝 Cambios Realizados en Imports

### ✅ Archivos Actualizados

#### 1. **app/main.py** (antes app.py)
```python
# ANTES:
import config
import database as db
import utils

# AHORA:
from app import config
from app import database as db
from app import utils
```

#### 2. **app/database.py**
```python
# ANTES:
import config

# AHORA:
from app import config
```

#### 3. **app/utils.py**
```python
# ANTES:
import config

# AHORA:
from app import config
```

#### 4. **app/services/compras_service.py**
```python
# ANTES:
import config

# AHORA:
from app import config
```

#### 5. **examples/ejemplo_integracion_compras.py**
```python
# ANTES:
import compras_service as cs
import database as db
import config

# AHORA:
from app.services import compras_service as cs
from app import database as db
from app import config
```

#### 6. **examples/bosquejo_tabla_editable.py**
```python
# ANTES:
import database as db
import utils
import config

# AHORA:
from app import database as db
from app import utils
from app import config
```

---

## 🔧 Configuración Mejorada

### Rutas Absolutas Automáticas

El archivo `config.py` ahora calcula automáticamente las rutas basadas en la ubicación del proyecto:

```python
import os
from pathlib import Path

# Obtener el directorio base del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent

# Rutas configuradas automáticamente
DB_PATH = os.path.join(BASE_DIR, 'data', 'ks_requisiciones.db')
BACKUP_PATH = os.path.join(BASE_DIR, 'backups')
EXPORT_PATH = os.path.join(BASE_DIR, 'exports')
LOG_PATH = os.path.join(BASE_DIR, 'logs')
```

**Ventajas:**
- ✅ Funciona desde cualquier directorio
- ✅ No requiere ajustes manuales de rutas
- ✅ Compatible con entornos virtuales

---

## 🧪 Ejecutar Scripts de Ejemplo

### Desde la raíz del proyecto:

```bash
# Ejemplo de integración de compras
python -m examples.ejemplo_integracion_compras

# Bosquejo de tabla editable
python -m examples.bosquejo_tabla_editable
```

---

## ✅ Verificación de Funcionamiento

### 1. Verificar estructura de imports

```bash
python -c "from app import config, database, utils; from app.services import compras_service; print('✅ Imports correctos')"
```

### 2. Inicializar base de datos

```bash
python -c "from app import database; database.inicializar_base_datos(); print('✅ BD inicializada')"
```

### 3. Inicializar módulo de compras

```bash
python -c "from app.services import compras_service; compras_service.inicializar_modulo_compras(); print('✅ Compras inicializadas')"
```

---

## 📦 Instalación de Dependencias

```bash
# Activar entorno virtual (si usas uno)
.\venv\Scripts\Activate

# Instalar dependencias
pip install -r requirements.txt
```

---

## 🎨 Ventajas de la Nueva Estructura

### ✅ Modularidad
- Código organizado por responsabilidades
- Fácil de navegar y mantener

### ✅ Escalabilidad
- Agregar nuevos servicios en `app/services/`
- Agregar nuevos módulos en `app/modules/`

### ✅ Profesionalismo
- Estructura estándar de Python
- Imports absolutos claros

### ✅ Separación de Concerns
- Código principal en `app/`
- Documentación en `docs/`
- Ejemplos en `examples/`
- Datos en `data/`

---

## 🚨 Troubleshooting

### Error: "No module named 'app'"

**Solución:** Asegúrate de ejecutar desde la raíz del proyecto:
```bash
cd "c:\Users\crist\Desktop\Resp PC\Portafolio\AppKS"
streamlit run app/main.py
```

### Error: "No such file or directory: 'data/ks_requisiciones.db'"

**Solución:** Las rutas ahora son absolutas. Verifica que las carpetas existan:
```bash
mkdir data backups exports logs
```

### Error en imports de ejemplos

**Solución:** Ejecuta los ejemplos como módulos:
```bash
python -m examples.ejemplo_integracion_compras
```

---

## 📌 Archivos Originales

Los archivos originales permanecen en la raíz por compatibilidad:
- ❌ NO eliminar hasta confirmar que todo funciona
- ✅ Puedes eliminarlos después de probar la nueva estructura

Para limpiar (SOLO después de confirmar funcionamiento):
```bash
Remove-Item app.py, database.py, config.py, utils.py, compras_service.py, bosquejo_tabla_editable.py, ejemplo_integracion_compras.py, *.md -Exclude README.md
```

---

## 🎯 Próximos Pasos

1. ✅ Ejecutar: `streamlit run app/main.py`
2. ✅ Verificar que todo funciona correctamente
3. ✅ Revisar logs por posibles errores
4. ✅ Ejecutar scripts de ejemplo
5. ✅ (Opcional) Eliminar archivos antiguos de la raíz

---

## 📞 Soporte

Si encuentras algún problema:
1. Verifica que estés en el directorio correcto
2. Confirma que los imports sean correctos
3. Revisa el log de errores de Streamlit
4. Asegúrate de que las carpetas `data/`, `backups/`, `exports/` y `logs/` existan

---

✨ **¡Estructura reorganizada con éxito!** ✨
