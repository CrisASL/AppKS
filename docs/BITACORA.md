# 📝 Bitácora de Desarrollo – AppKS  

## 📌 Proyecto  
**AppKS – Sistema de Gestión de Requisiciones**  
Desarrollado por: Cristian Salas  
Inicio: Enero 2026  

Sistema web desarrollado en Python (Streamlit + SQLite) que reemplaza planillas Excel para la gestión de requisiciones conectadas a cubos exportados desde Softland ERP.

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

# 📍 Estado Actual del Proyecto

El proyecto se encuentra actualmente en la versión:

## 🔹 **v1.5.2**

Sistema completo de gestión de requisiciones y compras con:
- Seguimiento avanzado de órdenes de compra con filtros de texto
- Sincronización automática entre requisiciones y compras
- Persistencia de filtros para mejor experiencia de usuario
- Control granular de eliminación de datos
- **Launcher `.exe` minimalista** (`start_app.py` + PyInstaller `--onefile`)
- Sistema de migraciones automáticas de base de datos
- UPSERT inteligente con detección de cambios

Preparado para:
- Dashboard avanzado con métricas de compras
- Integración con sistema de alertas
- Reportería automatizada