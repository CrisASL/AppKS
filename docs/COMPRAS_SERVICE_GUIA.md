# Módulo de Compras - Guía de Uso

## 📋 Descripción General

El módulo `compras_service.py` implementa un sistema robusto de gestión de compras con las siguientes características:

### ✅ Características Productivas

1. **Idempotencia garantizada**: Las operaciones pueden ejecutarse múltiples veces sin duplicar datos
2. **Eficiencia en SQLite**: Usa índices, transacciones y consultas optimizadas
3. **Integridad de datos**: Constraints, triggers y validaciones a nivel de BD
4. **Manejo robusto de errores**: Try/except, rollback automático, mensajes detallados
5. **Arquitectura modular**: Separación clara de responsabilidades

---

## 🏗️ Arquitectura

### Tablas Creadas

#### 1. Tabla `compras`
```sql
- id (PK autoincremental)
- num_oc (TEXT) + codprod (TEXT) → UNIQUE constraint
- cantidad_solicitada, cantidad_recibida, cantidad_manual (REAL)
- precio_compra (REAL)
- total_linea (REAL GENERATED) → Calculado automáticamente
- fecha_oc, fecha_recepcion (TEXT formato ISO)
- estado_linea, bodega_codigo, bodega_nombre (TEXT)
- observacion (TEXT)
- fecha_carga (TEXT) → Timestamp automático
```

**Índices optimizados**:
- `idx_compras_num_oc`
- `idx_compras_codprod`
- `idx_compras_oc_codprod` (compuesto para cruces)
- `idx_compras_fecha_oc`
- `idx_compras_estado`
- `idx_compras_proveedor`

#### 2. Tabla `gestion`
```sql
- Similar a requisiciones pero con campos adicionales:
  - bodega_ingreso
  - observacion_oc
  - Relación lógica con compras vía (oc, codprod)
```

**Triggers automáticos**:
- Cálculo de `saldo_pendiente` = cantidad - cant_recibida
- Actualización de `fecha_modificacion`

---

## 🚀 Uso Básico

### 1. Inicialización (ejecutar una vez)

```python
import compras_service as cs

# Crear las tablas (es idempotente, puede ejecutarse múltiples veces)
cs.inicializar_modulo_compras()
```

### 2. Cargar datos desde DataFrame

#### Opción A: Desde DataFrame en memoria

```python
import pandas as pd
import compras_service as cs

# Suponer que tienes un DataFrame con datos del cubo de compras
df_compras = pd.read_excel("data/cubos/cubo_compras.xlsx")

# Cargar a la base de datos
with cs.get_db_connection() as conn:
    insertados, omitidos, errores = cs.cargar_compras_desde_dataframe(df_compras, conn)
    
    print(f"✅ Insertados: {insertados}")
    print(f"⚠️ Omitidos: {omitidos}")
    
    if errores:
        print("❌ Errores:")
        for error in errores:
            print(f"   - {error}")
```

#### Opción B: Desde archivo Excel directamente

```python
import compras_service as cs

# Carga directa desde archivo
insertados, omitidos, errores = cs.cargar_compras_desde_archivo_excel(
    "data/cubos/cubo_compras.xlsx"
)
```

### 3. Actualizar gestión desde compras

```python
import compras_service as cs

with cs.get_db_connection() as conn:
    actualizados, mensajes = cs.actualizar_gestion_desde_compras(conn)
    
    print(f"✅ Registros actualizados: {actualizados}")
    for mensaje in mensajes:
        print(mensaje)
```

### 4. Proceso completo en un solo paso

```python
import pandas as pd
import compras_service as cs

# Leer cubo de compras
df_compras = pd.read_excel("data/cubos/cubo_compras.xlsx")

# Ejecutar proceso completo: carga + cruce
resultado = cs.ejecutar_proceso_completo_compras(df_compras)

if resultado['exito']:
    print(resultado['mensaje_general'])
    print(f"\n📦 Compras:")
    print(f"   Insertadas: {resultado['carga_compras']['insertados']}")
    print(f"   Omitidas: {resultado['carga_compras']['omitidos']}")
    
    print(f"\n🔄 Gestión:")
    print(f"   Actualizados: {resultado['actualizacion_gestion']['actualizados']}")
else:
    print(f"❌ {resultado['mensaje_general']}")
```

---

## 📊 Consultas y Reportes

### Estadísticas generales

```python
import compras_service as cs

with cs.get_db_connection() as conn:
    stats = cs.obtener_estadisticas_compras(conn)
    
    print(f"Total registros: {stats['total_registros']}")
    print(f"OCs únicas: {stats['total_ocs']}")
    print(f"Productos únicos: {stats['total_productos']}")
    print(f"Valor total: ${stats['valor_total']:,.2f}")
    print(f"Última carga: {stats['ultima_carga']}")
    
    print("\nEstados:")
    for estado, cantidad in stats['por_estado'].items():
        print(f"  {estado}: {cantidad}")
```

### Consultar compras por OC

```python
import compras_service as cs

with cs.get_db_connection() as conn:
    df_oc = cs.obtener_compras_por_oc("OC-12345", conn)
    print(df_oc)
```

### Obtener compras pendientes

```python
import compras_service as cs

with cs.get_db_connection() as conn:
    df_pendientes = cs.obtener_compras_pendientes(conn)
    print(f"Compras pendientes: {len(df_pendientes)}")
    print(df_pendientes[['num_oc', 'codprod', 'saldo_pendiente']])
```

---

## 🔧 Integración con Streamlit

### Ejemplo en `app.py`

```python
import streamlit as st
import pandas as pd
import compras_service as cs

def pagina_carga_compras():
    """Página para cargar cubo de compras"""
    st.title("📦 Carga de Compras")
    
    # Inicializar módulo (seguro ejecutar múltiples veces)
    cs.inicializar_modulo_compras()
    
    # Upload de archivo
    archivo = st.file_uploader(
        "Seleccionar cubo de compras (Excel)",
        type=['xlsx', 'xls']
    )
    
    if archivo:
        # Leer archivo
        df = pd.read_excel(archivo)
        
        st.info(f"📊 Registros en archivo: {len(df)}")
        
        # Preview
        with st.expander("👁️ Vista previa de datos"):
            st.dataframe(df.head(10))
        
        # Botón de carga
        if st.button("🚀 Cargar Compras y Actualizar Gestión", type="primary"):
            with st.spinner("Procesando..."):
                # Ejecutar proceso completo
                resultado = cs.ejecutar_proceso_completo_compras(df)
                
                if resultado['exito']:
                    st.success(resultado['mensaje_general'])
                    
                    # Mostrar detalles
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.metric(
                            "Compras Insertadas",
                            resultado['carga_compras']['insertados']
                        )
                        st.metric(
                            "Compras Omitidas",
                            resultado['carga_compras']['omitidos']
                        )
                    
                    with col2:
                        st.metric(
                            "Registros Actualizados en Gestión",
                            resultado['actualizacion_gestion']['actualizados']
                        )
                    
                    # Mostrar errores si los hay
                    if resultado['carga_compras']['errores']:
                        with st.expander("⚠️ Ver errores"):
                            for error in resultado['carga_compras']['errores']:
                                st.warning(error)
                else:
                    st.error(resultado['mensaje_general'])
    
    # Mostrar estadísticas actuales
    st.divider()
    st.subheader("📊 Estadísticas Actuales")
    
    with cs.get_db_connection() as conn:
        stats = cs.obtener_estadisticas_compras(conn)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Registros", stats['total_registros'])
        with col2:
            st.metric("OCs Únicas", stats['total_ocs'])
        with col3:
            st.metric("Productos", stats['total_productos'])
        with col4:
            st.metric("Valor Total", f"${stats['valor_total']:,.0f}")
        
        if stats['por_estado']:
            st.subheader("Estados de Compras")
            df_estados = pd.DataFrame([
                {'Estado': k, 'Cantidad': v} 
                for k, v in stats['por_estado'].items()
            ])
            st.dataframe(df_estados, use_container_width=True)
```

---

## 📝 Formato del Cubo de Compras (Excel)

El DataFrame debe tener las siguientes columnas:

### Columnas Requeridas:
- `NumOC`: Número de orden de compra
- `CodProd`: Código del producto
- `Proveedor`: Nombre del proveedor
- `CantidadSolicitada`: Cantidad solicitada
- `CantidadRecibida`: Cantidad recibida
- `PrecioCompra`: Precio unitario
- `FechaOC`: Fecha de la orden
- `EstadoLinea`: Estado (ej: "Pendiente", "Recibido")

### Columnas Opcionales:
- `CantidadManual`: Ajuste manual de cantidad
- `FechaRecepcion`: Fecha de recepción
- `BodegaCodigo`: Código de bodega
- `BodegaNombre`: Nombre de bodega
- `Observacion`: Observaciones

### Ejemplo de datos:

| NumOC   | CodProd | Proveedor     | CantidadSolicitada | CantidadRecibida | PrecioCompra | FechaOC    | EstadoLinea |
|---------|---------|---------------|-------------------|------------------|--------------|------------|-------------|
| OC-001  | P-123   | Proveedor A   | 100               | 100              | 1500         | 2026-02-10 | Recibido    |
| OC-001  | P-456   | Proveedor A   | 50                | 30               | 2000         | 2026-02-10 | Parcial     |
| OC-002  | P-789   | Proveedor B   | 200               | 0                | 1200         | 2026-02-12 | Pendiente   |

---

## 🔐 Características de Seguridad

### 1. Idempotencia
```python
# Puedes ejecutar múltiples veces sin duplicar datos
cs.inicializar_modulo_compras()  # ✅ Seguro
cs.cargar_compras_desde_dataframe(df, conn)  # ✅ Solo inserta nuevos
cs.actualizar_gestion_desde_compras(conn)  # ✅ Actualiza sin duplicar
```

### 2. Manejo de Errores
```python
try:
    with cs.get_db_connection() as conn:
        # Si algo falla, se hace rollback automático
        insertados, omitidos, errores = cs.cargar_compras_desde_dataframe(df, conn)
except Exception as e:
    # La conexión se cierra correctamente
    print(f"Error: {e}")
```

### 3. Validaciones
- Campos requeridos: `num_oc`, `codprod`
- Tipos de datos automáticos
- Fechas en formato ISO (YYYY-MM-DD)
- Números convertidos con manejo de errores

---

## ⚡ Optimizaciones para Producción

### 1. Índices Compuestos
```sql
-- Optimiza el cruce gestion-compras
CREATE INDEX idx_compras_oc_codprod ON compras(num_oc, codprod);
CREATE INDEX idx_gestion_oc_codprod ON gestion(oc, codprod);
```

### 2. Consultas Batch
```python
# Actualización masiva en una sola query (eficiente)
# Ver función: actualizar_gestion_desde_compras()
```

### 3. Transacciones
```python
with cs.get_db_connection() as conn:
    # Todo dentro de una transacción
    # Commit automático al salir
    # Rollback automático si hay error
```

---

## 🧪 Testing

### Prueba básica del módulo:

```bash
python compras_service.py
```

Esto ejecutará:
1. Inicialización de tablas
2. Verificación de estadísticas
3. Muestra de información

### Prueba manual:

```python
import pandas as pd
import compras_service as cs

# Crear datos de prueba
df_test = pd.DataFrame({
    'NumOC': ['OC-TEST-001', 'OC-TEST-001'],
    'CodProd': ['PROD-A', 'PROD-B'],
    'Proveedor': ['Proveedor Test', 'Proveedor Test'],
    'CantidadSolicitada': [100, 50],
    'CantidadRecibida': [100, 30],
    'PrecioCompra': [1500, 2000],
    'FechaOC': ['2026-02-15', '2026-02-15'],
    'EstadoLinea': ['Recibido', 'Parcial']
})

# Cargar
with cs.get_db_connection() as conn:
    insertados, omitidos, errores = cs.cargar_compras_desde_dataframe(df_test, conn)
    print(f"Resultado: {insertados} insertados, {omitidos} omitidos")
```

---

## 📌 Notas Importantes

1. **No crear archivo separado**: El módulo `compras_service.py` es autosuficiente y sigue el mismo patrón que `database.py`

2. **Importación en app.py**:
   ```python
   import compras_service as cs
   ```

3. **Requiere config.py**: El módulo usa `config.DB_PATH` para la conexión

4. **Compatible con database.py**: Usa el mismo patrón arquitectónico

5. **Listo para producción**: Incluye todas las características mencionadas

---

## 🎯 Ventajas del Diseño

✅ **Idempotencia**: Nunca duplica datos  
✅ **Eficiencia**: Índices optimizados para SQLite  
✅ **Integridad**: Constraints y triggers a nivel BD  
✅ **Claridad**: Código autodocumentado y modular  
✅ **Robusto**: Manejo completo de errores  
✅ **Escalable**: Preparado para crecimiento  
✅ **Mantenible**: Fácil de entender y modificar  

---

## 📞 Soporte

Para dudas o problemas:
1. Revisar logs de error retornados por las funciones
2. Verificar estructura del cubo de compras
3. Consultar estadísticas con `obtener_estadisticas_compras()`
4. Revisar constraints de la base de datos con SQLite Browser
