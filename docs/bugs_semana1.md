# Bugs Semana 1 — AppKS Auditoría de Código
**Fecha:** 2026-04-26  
**Backup baseline:** `backups/baseline_20260426_233211.db` (79.6 MB)  
**Estado DB:** 540 REQ · 74.549 compras · 1.239 cambios en historial

---

## ALTA PRIORIDAD

### BUG-01 · `st.set_page_config()` no es la primera llamada Streamlit
**Módulo:** `app/main.py` — líneas 36–52  
**Síntoma:** Si `db.inicializar_base_datos()` o `db.migrar_base_datos_existente()` lanzan excepción, se ejecuta `st.error()` / `st.warning()` ANTES de `st.set_page_config()`. Streamlit exige que `set_page_config` sea la primera llamada absoluta; si no lo es, la app crashea con `StreamlitAPIException`.  
**Reproducir:** Renombrar temporalmente el archivo `.db` para forzar fallo en inicialización y observar crash.  
**Corrección:** `st.set_page_config()` movido antes de los bloques try/except. Errores acumulados en `_startup_errors[]` y mostrados en `main()`.  
**Estado:** ✅ Cerrado — v1.8.2

---

### BUG-02 · Estados OC en DB no coinciden con `config.ESTADOS_OC`
**Módulo:** `app/database.py:actualizar_requisiciones_desde_compras()` + `app/config.py`  
**Síntoma real en DB:**
```
estado_oc actual en BD:
  'Recibido'       → 183 filas   (no existe en config)
  'Sin Recepción'  → 149 filas   (no existe en config)
  'Parcial'        →   3 filas   (no existe en config)
  'Pendiente'      → 205 filas   (OK)

config.ESTADOS_OC esperados:
  'Recepción Completa', 'Recepción Parcial', 'OC Generada', etc.
```
**Impacto:**
- El gráfico de torta "Estado de OC" muestra colores incorrectos (no hay color en `COLORES_ESTADO` para "Recibido" ni "Sin Recepción").
- El filtro "Estado" en Gestión Requisiciones nunca filtra "Recibido" porque la opción del multiselect es "Recepción Completa".
- 335 REQ con OC asignada aparecen con `estado_req = "Pendiente"` (inconsistencia de negocio).

**Causa raíz:** El campo `estado_linea` de la tabla `compras` (valores del ERP externo) se escribe directamente a `estado_oc` en `requisiciones` sin pasar por un mapa de normalización.  
**Corrección:** Agregar diccionario de mapeo en `actualizar_requisiciones_desde_compras()`:
```python
MAPA_ESTADO_LINEA = {
    "Recibido":       "Recepción Completa",
    "Sin Recepción":  "Pendiente",
    "Parcial":        "Recepción Parcial",
    # añadir según valores reales del ERP
}
```
**Pasos para reproducir:** `sqlite3 data/ks_requisiciones.db "SELECT estado_oc, COUNT(*) FROM requisiciones GROUP BY estado_oc"`  
**Estado:** ✅ Cerrado — v1.8.2 · `_MAPA_ESTADO_ERP` en Step 2 + CASE SQL en Step 3 + migración idempotente corrigió 335 filas existentes

---

### BUG-03 · Backup incompleto en modo WAL
**Módulo:** `app/main.py:pagina_configuracion()` — línea 1829  
**Síntoma:** El botón "Crear Backup" hace `shutil.copy2(ruta_origen, ruta_destino)` copiando solo el `.db`. La DB está en modo WAL (verificado: existen `ks_requisiciones.db-wal` y `ks_requisiciones.db-shm`). Si hay páginas no traspasadas al archivo principal, el backup estará incompleto o corrupto.  
**Reproducir:** Crear backup, abrir con `sqlite3 backups/ultimo_backup.db "PRAGMA integrity_check"`.  
**Corrección:** `PRAGMA wal_checkpoint(FULL)` ejecutado en una conexión temporal antes de `shutil.copy2()`.  
**Estado:** ✅ Cerrado — v1.8.2

---

### BUG-04 · AGGrid key fijo no refresca la grilla al cambiar filtros
**Módulo:** `app/main.py:tabla_listado_requisiciones()` — línea 1265  
**Síntoma:** `key="aggrid_requisiciones"` es estático. Cuando el usuario aplica filtros que cambian el DataFrame, AG Grid mantiene el estado interno de la grilla anterior (scroll, selección, ediciones pendientes). Las ediciones no confirmadas de una búsqueda anterior pueden mezclarse con los datos nuevos.  
**Reproducir:** Editar celda sin guardar → cambiar filtro → intentar guardar: puede escribir datos en la fila incorrecta.  
**Corrección:** Key computado como `f"aggrid_req_{abs(hash(str(filtros)+filtro_desprod+str(filtro_proveedor)+str(len(df_grid)))) % 1_000_000}"`.  
**Estado:** ✅ Cerrado — v1.8.2

---

## MEDIA PRIORIDAD

### BUG-05 · `migrar_tabla_compras_agregar_desprod()` se llama en CADA render
**Módulo:** `app/main.py:pagina_seguimiento_oc()` — línea 1429  
**Síntoma:** Cada vez que el usuario navega a "Seguimiento OC", se ejecuta una migración DDL (`ALTER TABLE`). SQLite lanza una excepción si la columna ya existe (aunque probablemente se capture en un try/except interno). Es overhead innecesario y puede causar logs de error falsos.  
**Corrección:** Mover esta migración a `db.migrar_base_datos_existente()` que ya se llama una sola vez al iniciar.  
**Estado:** ✅ Cerrado — v1.8.3 · Llamada removida de `pagina_seguimiento_oc()`; migración movida a `migrar_base_datos_existente()` en database.py

---

### BUG-06 · KPI "Productos Únicos" muestra datos de pendientes, no del total
**Módulo:** `app/main.py:pagina_configuracion()` tab2 — línea 1899  
**Síntoma:** El metric "Productos Únicos" usa `stats["productos_pendientes"]` que es `codprod.nunique()` SOLO en filas con `saldo_pendiente > 0`. El label dice "Únicos" sugiriendo el universo total.  
**Corrección:** Cambiar el label a "Productos con Saldo Pendiente" o calcular el total real:
```python
st.metric("Productos con Saldo Pendiente", stats["productos_pendientes"])
```
**Estado:** ✅ Cerrado — v1.8.3 · Label corregido en tab2 y tab4

---

### BUG-07 · "Total Requisiciones" en tab Limpiar muestra suma incorrecta
**Módulo:** `app/main.py:pagina_configuracion()` tab4 — línea 2001  
**Síntoma:** `stats["req_pendientes"] + stats["oc_transito"]` no es el total de registros. Hay 540 REQ en la DB pero esta suma muestra un número distinto (excluye completadas, canceladas, etc.).  
**Corrección:**
```python
cursor.execute("SELECT COUNT(*) FROM requisiciones")
total_real = cursor.fetchone()[0]
st.metric("Total Requisiciones", total_real)
```
**Estado:** ✅ Cerrado — v1.8.3 · `total_req` agregado a `obtener_estadisticas_generales()`; metric usa `stats["total_req"]`

---

### BUG-08 · Botón "Limpiar Filtros" en Seguimiento OC sin key único
**Módulo:** `app/main.py:pagina_seguimiento_oc()` — línea 1607  
**Síntoma:** `st.button("🔄 Limpiar Filtros", type="secondary")` sin `key=`. Si Streamlit detecta dos botones con el mismo label en la misma sesión puede generar `DuplicateWidgetID` o comportamiento inesperado al cambiar de pestaña.  
**Corrección:** Agregar `key="btn_limpiar_oc"`.  
**Estado:** ✅ Cerrado — v1.8.3

---

### BUG-09 · `fecha_oc` editable en AGGrid puede recibir strings mal formateados
**Módulo:** `app/main.py` línea 1166 + `app/database.py:actualizar_requisicion_desde_ui()`  
**Síntoma:** AG Grid con `customDateTimeFormat: 'dd/MM/yyyy'` puede devolver fechas como strings en distintos formatos según el locale del navegador (ej. "4/26/2026" vs "26-04-2026"). La validación en `actualizar_requisicion_desde_ui` solo hace `pd.to_datetime(valor)` que acepta muchos formatos silenciosamente y puede guardar una fecha incorrecta.  
**Corrección:** Normalizar a `YYYY-MM-DD` explícitamente antes de guardar:
```python
if campo == "fecha_oc" and valor:
    try:
        valor = pd.to_datetime(valor, dayfirst=True).strftime("%Y-%m-%d")
    except:
        continue
```
**Estado:** ✅ Cerrado — v1.8.3 · `pd.to_datetime(valor, dayfirst=True).strftime("%Y-%m-%d")`

---

### BUG-10 · `getattr(st.session_state, session_key)` sin valor default
**Módulo:** `app/main.py:_widget_cubo_uploader()` — línea 257  
**Síntoma:** Si la clave no existe en session_state, `getattr` sin default lanza `AttributeError`. En práctica no ocurre porque `inicializar_session_state()` siempre inicializa las claves, pero si alguien llama al widget con una `session_key` nueva sin inicializar, crashea.  
**Corrección:** Cambiar a `getattr(st.session_state, session_key, None)`.  
**Estado:** ✅ Cerrado — v1.8.3

---

## BAJA PRIORIDAD

### BUG-11 · Gráfico "Estado de OC" sin colores para estados del ERP
**Módulo:** `app/main.py:pagina_dashboard()` — línea 639  
**Síntoma:** `color_discrete_map=config.COLORES_ESTADO` no tiene claves para "Recibido", "Sin Recepción", "Parcial". Plotly asigna colores automáticos aleatorios para estos estados, rompiendo consistencia visual.  
**Relacionado con:** BUG-02  
**Estado:** ✅ Cerrado — v1.8.3 · Colores alias ERP agregados a `COLORES_ESTADO` en config.py como respaldo

---

### BUG-12 · `obtener_top_productos_ultimo_mes` hardcodea 30 días
**Módulo:** `app/database.py` — línea 1087  
**Síntoma:** El gráfico dice "Último Mes" pero usa exactamente 30 días. En febrero muestra casi 2 meses; en meses largos excluye días válidos. Inconsistencia menor.  
**Corrección:** Usar `relativedelta(months=1)` de `dateutil` o documentar que es "30 días".  
**Estado:** ✅ Cerrado — v1.8.3 · Título corregido a "Últimos 30 Días"

---

### BUG-13 · `setattr(st.session_state, ...)` práctica no recomendada
**Módulo:** `app/main.py:_widget_cubo_uploader()` — líneas 298, 305  
**Síntoma:** Usa `setattr(st.session_state, session_key, df)` en vez del acceso estándar `st.session_state[session_key] = df`. Streamlit recomienda el acceso por índice para garantizar la serialización correcta.  
**Estado:** ✅ Cerrado — v1.8.3 · Los 3 `setattr` reemplazados por `st.session_state[session_key] = ...`

---

## RESUMEN

| Prioridad | Total | Abiertos | Cerrados |
|---|---|---|---|
| Alta | 4 | 0 | 4 ✅ |
| Media | 6 | 0 | 6 ✅ |
| Baja | 3 | 0 | 3 ✅ |
| **Total** | **13** | **0** | **13** |

## Checkpoints de validación

Para confirmar que cada bug está resuelto:

- **BUG-01:** `streamlit run run.py` en DB vacía → no hay `StreamlitAPIException`.
- **BUG-02:** `SELECT estado_oc, COUNT(*) FROM requisiciones GROUP BY estado_oc` → solo valores de `config.ESTADOS_OC`.
- **BUG-03:** Crear backup → `sqlite3 backups/X.db "PRAGMA integrity_check"` → retorna `ok`.
- **BUG-04:** Editar celda → cambiar filtro → contenido de grilla es coherente con los nuevos filtros.
- **BUG-05:** `grep "migrar_tabla_compras" app/main.py` → 0 ocurrencias en `pagina_seguimiento_oc`.
- **BUG-06:** Label del metric dice "Pendientes" no "Únicos".
- **BUG-07:** Metric muestra 540 (o el total real de la DB).
- **BUG-08:** `grep 'Limpiar Filtros' app/main.py` → todos los botones tienen `key=`.
- **BUG-09:** Guardar fecha en formato `dd/MM/yyyy` → en DB queda `YYYY-MM-DD`.
- **BUG-10:** `getattr(st.session_state, "cualquier_clave_nueva", None)` → no crashea.
- **BUG-11:** Pie chart muestra colores definidos para todos los estados.
- **BUG-12:** Título del gráfico dice "Últimos 30 días" en vez de "Último Mes".
- **BUG-13:** `grep "setattr(st.session_state" app/main.py` → 0 ocurrencias.

---

## Día 4 — Cierre Semana 1 (2026-04-28)

### Entregables

| Tarea | Archivo | Descripción |
|---|---|---|
| Validador Excel | `app/utils.py:validar_filas_requisiciones` | Rechazo total si hay errores de columnas, tipos o duplicados (NumReq+CodProd) |
| Transacción atómica | `app/database.py:cargar_requisiciones_desde_cubo` | Two-pass: validar todo → insertar todo en una sola transacción con rollback automático |
| Panel Diagnóstico | `app/services/check_consistencia.py` | 4 checks de consistencia entre REQ y OC |
| Tab Diagnóstico | `app/main.py:pagina_configuracion` | Tab "🔍 Diagnóstico" en ⚙️ Configuración (solo lectura) |

### Checks del panel Diagnóstico

| Check | Criterio | Severidad |
|---|---|---|
| OC sin REQ | `num_oc` no aparece en `requisiciones.oc` | 🔴 Alta |
| REQ sin OC (+14d) | Sin OC, guía ni observación, con > 14 días | 🔴 Alta |
| Montos descuadrados | `ABS(total_linea - precio × cantidad) > 1` | 🟡 Media |
| Recepciones excedidas | `recibida + manual > solicitada + 0.01` | 🟡 Media |

### Estado final bugs (cierre semana 1)

| Prioridad | Total | Cerrados |
|---|---|---|
| Alta | 4 | 4 ✅ |
| Media | 6 | 6 ✅ |
| Baja | 3 | 3 ✅ |
| **Total** | **13** | **13 ✅** |

**Validación Día 4:**
- Panel Diagnóstico funcional en ⚙️ Configuración → tab 🔍 Diagnóstico
- ≥ 80% bugs Alta resueltos: **100%** (4/4)
- Todos los bugs del backlog semana 1 cerrados
