# 📋 Decisiones Técnicas – AppKS

Registro de decisiones de arquitectura y diseño tomadas durante el desarrollo. Formato ADR (Architecture Decision Record) liviano.

**Proyecto:** AppKS – Sistema de Gestión Operativa  
**Autor:** Cristian Salas  
**Inicio:** Enero 2026  

---

## ADR-001 – SQLite como base de datos local

**Estado:** Aceptado  
**Versión:** v1.0.0  

### Contexto
La aplicación se ejecuta en un único equipo de uso interno. No hay múltiples usuarios concurrentes. Los datos provienen de cubos Excel exportados desde un ERP propietario (Softland), no de un servicio externo.

### Decisión
Usar SQLite en lugar de un servidor de base de datos (PostgreSQL, MySQL).

### Consecuencias
- Sin instalación ni configuración de servidor de BD
- El archivo `.db` es portable y respaldable con un simple copiar/pegar
- Migraciones mediante `ALTER TABLE` directamente en Python, sin ORM ni herramientas de migración externas
- Limitación aceptada: no apto para múltiples escritores concurrentes (no aplica al caso de uso actual)

---

## ADR-002 – Carga idempotente con INSERT OR IGNORE

**Estado:** Aceptado  
**Versión:** v1.3.0  

### Contexto
El cubo de requisiciones se exporta desde Softland y se recarga diariamente. En la versión inicial, recargar el cubo borraba todos los registros previos, perdiendo los estados administrativos editados manualmente por el usuario.

### Decisión
Usar `INSERT OR IGNORE` con `UNIQUE(numreq, codprod)` en lugar de `DELETE + INSERT`.

```sql
INSERT OR IGNORE INTO requisiciones (numreq, codprod, ...) VALUES (?, ?, ...)
```

### Consecuencias
- Recargar el cubo nunca borra ni sobrescribe datos existentes
- Los campos administrativos (`proveedor`, `oc`, `estado_req`, `estado_envio`, etc.) son preservados en recargas
- Las filas nuevas del cubo se insertan con valores `DEFAULT`
- `cursor.rowcount` clasifica correctamente insertado vs. omitido sin pre-SELECT adicional
- Limitación conocida: si un producto cambia de `numreq` en el ERP, se registra como una fila nueva

---

## ADR-003 – Launcher .exe minimalista en lugar de bundle completo

**Estado:** Aceptado  
**Versión:** v1.5.2  

### Contexto
Se intentó empaquetar Streamlit completo con PyInstaller (`collect_all('streamlit')`). El resultado fue un `.exe` de ~99 MB que fallaba por conflictos con assets estáticos del dev server de Node interno de Streamlit, errores de `bootstrap.run()` y conflictos de puerto.

### Decisión
El `.exe` es un launcher de ~8 MB que simplemente ubica `streamlit.exe` dentro de `venv\Scripts\` y lanza `streamlit run run.py` via `subprocess.Popen()`. Streamlit no se empaqueta.

```python
streamlit_exe = base_dir / "venv" / "Scripts" / "streamlit.exe"
subprocess.Popen([str(streamlit_exe), "run", str(run_py)])
```

### Consecuencias
- Ejecutable de 8 MB en lugar de 99 MB
- Sin hacks de puertos ni `bootstrap.run()`
- Requiere que `venv\` esté en la misma raíz que el `.exe` — no es un ejecutable autocontenido
- Actualizaciones de dependencias no requieren recompilar el `.exe`
- Errores visibles con `tkinter.messagebox` sin necesidad de consola

---

## ADR-004 – Columnas de estado como TEXT en lugar de BOOLEAN/INTEGER

**Estado:** Aceptado  
**Versión:** v1.8.0  

### Contexto
La columna `oc_enviada INTEGER DEFAULT 0` generaba conflictos de tipo en el round-trip AG Grid → pandas → SQLite:
- AG Grid con `agCheckboxCellEditor` devolvía strings `"true"/"false"` al editar
- pandas coercionaba a `bool`, pero SQLite esperaba `int`
- Imposible distinguir "nunca marcado" de "desmarcado" sin lógica adicional
- No extensible a más de dos estados sin cambiar el tipo de columna

### Decisión
Reemplazar columnas boolean de estado por `TEXT` con un whitelist de valores válidos definido en `config.py`.

```python
# config.py
ESTADOS_ENVIO = ["No Enviado", "Enviado"]

# database.py – Schema
estado_envio TEXT DEFAULT 'No Enviado'

# database.py – Validación al guardar
valor = valor if valor in config.ESTADOS_ENVIO else "No Enviado"
```

### Consecuencias
- Sin conflictos de tipo: AG Grid, pandas y SQLite trabajan con el mismo string
- Extensible: agregar un estado nuevo solo requiere actualizar la constante y la migración
- Validación explícita por whitelist en backend — valores inesperados caen al default
- El primer elemento del array es siempre el valor por defecto (convención del proyecto)
- `oc_enviada` se mantiene en migraciones y save-validator para compatibilidad con DBs anteriores, pero no es visible en la UI

---

## ADR-005 – Sincronización REQ→OC en pure SQL

**Estado:** Aceptado  
**Versión:** v1.7.0  

### Contexto
La sincronización entre requisiciones y órdenes de compra se hacía cargando ambas tablas completas en DataFrames y ejecutando un `UPDATE` por fila en Python (N round-trips). Con tablas grandes, el tiempo de ejecución crecía linealmente y el consumo de memoria era proporcional al tamaño total de los datos.

### Decisión
Reescribir como un único statement SQL con subconsultas correlacionadas y `julianday()` para aritmética de fechas.

```sql
UPDATE requisiciones
SET proveedor = (SELECT c.proveedor FROM compras c
                 WHERE c.codprod = requisiciones.codprod
                   AND julianday(c.fecha_oc) - julianday(requisiciones.fecha_requisicion) BETWEEN 0 AND 90
                   AND c.cantidad >= requisiciones.cantidad * 0.8
                 ORDER BY julianday(c.fecha_oc) - julianday(requisiciones.fecha_requisicion)
                 LIMIT 1),
    ...
WHERE EXISTS (SELECT 1 FROM compras c WHERE ...)
```

### Consecuencias
- N round-trips Python → 1 statement SQL
- Sin carga de DataFrames completos en memoria para este path
- La lógica de negocio (ventana 0–90 días, cantidad ≥ 80%, OC más cercana) vive en SQL, no en Python
- Limitación: más difícil de depurar que un loop Python — se compensó con `print()` de diagnóstico durante desarrollo

---

## ADR-006 – Migraciones idempotentes sin ORM

**Estado:** Aceptado  
**Versión:** v1.0.0 (refinado en v1.5.0, v1.7.0, v1.8.0)  

### Contexto
El esquema de la base de datos evoluciona con cada versión. Los usuarios finales tienen bases de datos existentes que no deben ser borradas al actualizar la aplicación.

### Decisión
Todas las migraciones se ejecutan en `migrar_base_datos_existente()` al arrancar la app, verificando existencia antes de modificar.

```python
columnas_existentes = {col[1] for col in cursor.execute("PRAGMA table_info(requisiciones)")}
if "estado_envio" not in columnas_existentes:
    cursor.execute("ALTER TABLE requisiciones ADD COLUMN estado_envio TEXT DEFAULT 'No Enviado'")
```

Sin ORM, sin archivos de migración separados, sin historial de versiones de esquema.

### Consecuencias
- La app arranca correctamente en cualquier versión de BD existente
- Las migraciones son ejecutables múltiples veces sin errores (idempotentes por definición)
- No hay herramienta de rollback — si una migración es destructiva, se debe hacer backup manual antes
- Convención del proyecto: nunca eliminar columnas via migración automática; solo agregar o modificar defaults
- `migrar_base_datos_existente()` cubre tanto `requisiciones` (campos de estado, clave compuesta) como la columna `desprod` en la tabla `compras` — cualquier migración que afecte ambas tablas va aquí, no en las páginas de UI

---

## ADR-007 – Rehidratación automática de datos con `get_or_load_cubo()`

**Estado:** Aceptado  
**Versión:** v1.8.1  

### Contexto
Streamlit re-ejecuta el script completo en cada interacción. Los DataFrames cargados se almacenan en `session_state`, pero al navegar entre pestañas o eliminar cubos, las claves podían quedar con valor `None`, y la lógica de inicialización solo verificaba `if key not in session_state`, sin considerar el caso de valores `None`.

### Decisión
Implementar `get_or_load_cubo(nombre_cubo)` como punto único de acceso a cubos de datos, con lógica robusta:

```python
def get_or_load_cubo(nombre_cubo: str) -> Optional[pd.DataFrame]:
    session_key = f"cubo_{nombre_cubo}"
    
    # Validar si existe en session_state Y no es None
    if session_key in st.session_state and st.session_state[session_key] is not None:
        df = st.session_state[session_key]
        if isinstance(df, pd.DataFrame) and not df.empty:
            return df
    
    # Rehidratar desde SQLite
    df = cargar_cubo_raw(nombre_cubo)
    st.session_state[session_key] = df
    return df
```

Además, modificar `inicializar_session_state()` para cargar cubos si NO existen O si son `None`:

```python
if key not in st.session_state or st.session_state[key] is None:
    st.session_state[key] = db.cargar_cubo_raw(cubo)
```

### Consecuencias
- Los datos persisten automáticamente entre navegaciones de pestañas
- La rehidratación ocurre bajo demanda sin cargas innecesarias
- Punto único de acceso facilita debugging y mantenimiento
- Eliminar cubos requiere `.pop()` en lugar de asignación `= None`
- Compatible con arquitectura existente sin cambios en BD

---

## ADR-008 – Normalización de estados ERP en sincronización REQ→OC

**Estado:** Aceptado  
**Versión:** v1.8.2  

### Contexto
El campo `estado_linea` de Softland ERP usa valores propios (`'Recibido'`, `'Sin Recepción'`, `'Parcial'`) que no pertenecen a `config.ESTADOS_OC`. Al copiar ese valor directamente a `estado_oc` en requisiciones, el gráfico de torta perdía sus colores y los filtros por estado retornaban 0 resultados.

### Decisión
Interponer un diccionario `_MAPA_ESTADO_ERP` local a `actualizar_requisiciones_desde_compras()` y un `CASE` SQL equivalente en el Step 3 (pure SQL):

```python
_MAPA_ESTADO_ERP = {
    "Recibido":      "Recepción Completa",
    "Sin Recepción": "OC Generada",
    "Parcial":       "Recepción Parcial",
}
```

La migración en `migrar_base_datos_existente()` normaliza datos históricos con un `UPDATE ... CASE` idempotente.

### Consecuencias
- Todos los valores de `estado_oc` pertenecen al catálogo `config.ESTADOS_OC`
- `COLORES_ESTADO` y los filtros de la UI funcionan correctamente
- Agregar nuevos estados ERP requiere actualizar solo `_MAPA_ESTADO_ERP` y el CASE SQL
- La migración es idempotente: múltiples ejecuciones no generan cambios duplicados
- `COLORES_ESTADO` en `config.py` incluye los alias ERP (`'Recibido'`, `'Sin Recepción'`, `'Parcial'`) como respaldo: si algún registro llega sin normalizar (edge-case), el gráfico de torta igual muestra un color coherente

---

## ADR-009 – Validación two-pass con rechazo atómico en carga masiva

**Estado:** Aceptado  
**Versión:** v1.8.4

### Contexto
`cargar_requisiciones_desde_cubo()` validaba y escribía fila a fila en el mismo loop. Si el archivo tenía errores a mitad del recorrido, los registros anteriores ya estaban confirmados en BD. Si una excepción de BD ocurría a mitad de la carga, no había forma de revertir las inserciones anteriores de esa misma carga.

### Decisión
Separar el procesamiento en dos fases estrictamente secuenciales:

```python
# FASE 1 – solo validación, ninguna escritura en BD
filas_validas = []
for row in df:
    # validar; acumular errores
    filas_validas.append(datos_normalizados)

if mensajes_error:
    return 0, len(mensajes_error), mensajes_error  # rechazar todo

# FASE 2 – inserción atómica
with get_db_connection() as conn:  # commit en exit, rollback en exception
    for datos in filas_validas:
        cursor.execute("INSERT OR IGNORE ...", datos)
```

Complementado con `validar_filas_requisiciones()` en `utils.py`, llamada como `pre_save_validator` antes de guardar el hash del archivo — si falla la validación, el mismo archivo puede subirse de nuevo sin que el sistema lo considere "ya procesado".

### Consecuencias
- La BD nunca queda en estado parcialmente cargado: o se insertan todos los registros válidos o ninguno
- El usuario ve la tabla de errores completa antes de cualquier escritura y puede corregir el archivo
- `get_db_connection()` ya implementaba commit/rollback — solo fue necesario eliminar el `try/except` interno por fila en la FASE 2
- Si el archivo tiene filas válidas y una inválida, se rechaza completo; el usuario debe corregir el archivo fuente
