# 🔄 Sistema de Carga Idempotente - Documentación Técnica

## 📌 Resumen Ejecutivo

El sistema AppKS implementa un **mecanismo de carga idempotente e incremental** que garantiza la integridad de los datos históricos y evita duplicaciones al cargar información desde cubos Excel hacia la base de datos SQLite.

---

## 🎯 Objetivos

1. **Preservar la integridad histórica**: Nunca borrar registros existentes
2. **Evitar duplicaciones**: Una requisición se identifica únicamente por su `NumReq`
3. **Permitir cargas repetibles**: Cargar el mismo cubo múltiples veces sin efectos secundarios
4. **Proveer auditoría completa**: Registrar estadísticas de cada carga
5. **Mapear fechas correctamente**: Convertir `FEmision` del cubo a `fecha_requisicion`

---

## 🏗️ Arquitectura de la Solución

### 1. Esquema de Base de Datos

#### Tabla: `requisiciones`

```sql
CREATE TABLE requisiciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numreq TEXT NOT NULL UNIQUE,  -- ⭐ Clave de negocio ÚNICA
    codprod TEXT NOT NULL,
```sql
CREATE TABLE requisiciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numreq TEXT NOT NULL,
    codprod TEXT NOT NULL,
    desprod TEXT,
    cantidad INTEGER NOT NULL,
    fecha_requisicion DATE,  -- ⭐ NUEVO: Mapeado desde FEmision
    sucursal_destino TEXT DEFAULT 'KS TALCA',
    proveedor TEXT,
    oc TEXT,
    n_guia TEXT,
    fecha_oc DATE,
    observacion TEXT,
    detalle TEXT,
    cant_recibida INTEGER DEFAULT 0,
    estado_oc TEXT DEFAULT 'Pendiente',
    saldo_pendiente INTEGER,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CHECK(cantidad > 0),
    CHECK(cant_recibida >= 0),
    CHECK(saldo_pendiente >= 0),
    
    -- Clave única compuesta: numreq + codprod
    UNIQUE(numreq, codprod)
)
```

**Campos clave**:
- `id`: Campo técnico autoincremental (NO usar para lógica de negocio)
- `numreq`: Identificador de la requisición
- `codprod`: Código del producto
- **Clave compuesta `(numreq, codprod)`**: Una requisición puede tener múltiples productos
- `fecha_requisicion`: **NUEVO** - Fecha de emisión de la requisición

#### Tabla: `cargas_diarias`

```sql
CREATE TABLE cargas_diarias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_carga TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    registros_leidos INTEGER NOT NULL,
    registros_insertados INTEGER NOT NULL,
    registros_omitidos INTEGER DEFAULT 0,
    errores INTEGER DEFAULT 0,
    detalles TEXT,  -- JSON con información adicional
    usuario TEXT DEFAULT 'Cristian Salas'
)
```

---

## 🔧 Implementación Técnica

### Función: `cargar_requisiciones_desde_cubo()`

#### Firma
```python
def cargar_requisiciones_desde_cubo(df_cubo: pd.DataFrame) -> Tuple[int, int, List[str]]
```

#### Flujo de Ejecución

```
1. Inicializar contadores
   ├─ insertadas = 0
   ├─ omitidas = 0
   └─ errores = 0

2. Obtener claves existentes (numreq, codprod)
   └─ SELECT numreq, codprod FROM requisiciones

3. Para cada fila del cubo:
   │
   ├─ ¿Tiene cantidad > 0 para TALCA?
   │  └─ NO → Saltar fila
   │
   ├─ Extraer datos:
   │  ├─ NumReq (identificador de requisición)
   │  ├─ CodProd (código de producto)
   │  ├─ Clave compuesta: (NumReq, CodProd)
   │  ├─ CodProd, DesProd
   │  ├─ FEmision → fecha_requisicion
   │  └─ Otros campos
   │
   ├─ Validar campos críticos
   │  └─ NumReq y CodProd no vacíos
   │
   ├─ ¿(NumReq, CodProd) ya existe en BD?
   │  ├─ SÍ → omitidas++, continuar (NO actualizar)
   │  └─ NO → Insertar nueva línea de requisición
   │
   └─ INSERT OR IGNORE INTO requisiciones (...)

4. Registrar auditoría
   └─ INSERT INTO cargas_diarias (...)

5. Retornar (insertadas, errores, mensajes)
```

#### Código Clave

```python
# 1. Verificar existencia (caché en memoria para performance)
# Usa clave compuesta (numreq, codprod)
cursor.execute("SELECT numreq, codprod FROM requisiciones")
claves_existentes = {(row[0], row[1]) for row in cursor.fetchall()}

# 2. Mapear FEmision → fecha_requisicion
fecha_requisicion = None
femision = row.get('FEmision')

if pd.notna(femision):
    try:
        if isinstance(femision, str):
            fecha_requisicion = pd.to_datetime(femision, errors='coerce').strftime('%Y-%m-%d')
        elif isinstance(femision, (pd.Timestamp, datetime)):
            fecha_requisicion = femision.strftime('%Y-%m-%d')
        else:
            # Número de serie de Excel
            fecha_requisicion = pd.to_datetime(femision, origin='1899-12-30', unit='D', errors='coerce')
            if pd.notna(fecha_requisicion):
                fecha_requisicion = fecha_requisicion.strftime('%Y-%m-%d')
    except:
        pass  # Si falla, fecha_requisicion = None

# 3. Insertar solo si la combinación (numreq, codprod) no existe
if (numreq, codprod) in claves_existentes:
    omitidas += 1
    continue  # Saltar, NO actualizar

cursor.execute("""
    INSERT OR IGNORE INTO requisiciones (
        numreq, codprod, desprod, cantidad, fecha_requisicion, ...
    ) VALUES (
        :numreq, :codprod, :desprod, :cantidad, :fecha_requisicion, ...
    )
""", datos_requisicion)

if cursor.rowcount > 0:
    insertadas += 1
    claves_existentes.add((numreq, codprod))  # Actualizar caché
else:
    omitidas += 1
```

---

## 🔐 Garantías de Idempotencia

### ✅ Propiedad 1: No Destrucción de Datos

```python
# ❌ PROHIBIDO (código anterior)
cursor.execute("DELETE FROM requisiciones")

# ✅ CORRECTO (código actual)
# Solo INSERT, nunca DELETE
```

### ✅ Propiedad 2: Unicidad por (NumReq, CodProd)

```sql
-- Constraint UNIQUE compuesto en (numreq, codprod)
UNIQUE(numreq, codprod)

-- INSERT OR IGNORE garantiza que:
-- Si (NumReq, CodProd) existe → NO inserta, NO falla, NO actualiza
-- Si (NumReq, CodProd) nuevo → Inserta normalmente
-- Permite múltiples productos por requisición
```

### ✅ Propiedad 3: Cargas Repetibles

```
Carga 1:  100 registros leídos → 100 insertados, 0 omitidos
Carga 2:  100 registros leídos → 0 insertados, 100 omitidos
Carga 3:  120 registros leídos → 20 insertados, 100 omitidos
```

**Resultado**: Datos consistentes, sin duplicados

---

## 🛡️ Sistema de Migración

### Función: `migrar_base_datos_existente()`

Ejecuta migraciones automáticas para bases de datos existentes:

1. **Agrega campo `fecha_requisicion`** si no existe
2. **Crea índice UNIQUE compuesto en `(numreq, codprod)`** si no existe
3. **Elimina duplicados** antes de crear el índice (mantiene el más reciente)

```python
# Seguro ejecutar múltiples veces
db.inicializar_base_datos()  # Crea tablas nuevas
db.migrar_base_datos_existente()  # Agrega campos/constraints faltantes
```

---

## 📊 Auditoría y Trazabilidad

### Registro en `cargas_diarias`

Cada carga registra:

```json
{
  "fecha_carga": "2026-02-10 14:30:00",
  "registros_leidos": 150,
  "insertadas": 25,
  "omitidas": 125,
  "errores": 0,
  "detalles": {
    "duracion_segundos": 2.34,
    "mensajes_error": [],
    "registros_leidos": 150,
    "insertadas": 25,
    "omitidas": 125,
    "errores": 0
  },
  "usuario": "Cristian Salas"
}
```

### Consulta del Historial

```python
# Obtener últimas 50 cargas
df_historial = db.obtener_historial_cargas(limite=50)

# Obtener información de la última carga
ultima = db.obtener_ultima_carga()
print(f"Última carga: {ultima['fecha_carga']}")
print(f"Insertadas: {ultima['registros_insertados']}")
```

---

## 🧪 Casos de Prueba

### Caso 1: Primera Carga

**Entrada**: Cubo con 100 requisiciones  
**Resultado Esperado**:
- `insertadas = 100`
- `omitidas = 0`
- `errores = 0`

### Caso 2: Carga de Mismo Cubo

**Entrada**: Mismo cubo con 100 requisiciones  
**Resultado Esperado**:
- `insertadas = 0`
- `omitidas = 100`
- `errores = 0`

### Caso 3: Carga Incremental

**Entrada**: Cubo actualizado con 120 requisiciones (20 nuevas)  
**Resultado Esperado**:
- `insertadas = 20`
- `omitidas = 100`
- `errores = 0`

### Caso 4: NumReq Duplicado en Cubo

**Entrada**: Cubo con NumReq duplicado (error humano)  
**Resultado Esperado**:
- Primera ocurrencia: inserta
- Segunda ocurrencia: omite
- Sin errores críticos

---

## ⚠️ Consideraciones Importantes

### 1. No Actualización de Registros Existentes

**Regla**: Si una línea con `(NumReq = "REQ-001", CodProd = "PROD-123")` ya existe en la BD, NO se actualizará aunque el cubo tenga datos diferentes.

**Razón**: Mantener integridad histórica. Los datos en BD pueden haber sido modificados manualmente por el usuario.

**Solución**: Si necesitas actualizar una línea de requisición existente, hazlo desde la interfaz **📋 Gestión Requisiciones**.

### 2. Calidad de Datos en el Origen

**Importante**: La combinación `(NumReq, CodProd)` debe ser única en el cubo Excel.

**Validación recomendada**: Antes de cargar, verificar en Excel:
```excel
=COUNTIFS(B:B, B2, C:C, C2) > 1  ' Detectar duplicados en NumReq + CodProd
```

**Nota**: Es válido que una requisición (NumReq) tenga múltiples productos (CodProd), pero cada combinación debe aparecer una sola vez.

### 3. Performance con Grandes Volúmenes

**Optimización**: La función carga las claves compuestas existentes en memoria (caché):

```python
claves_existentes = {(row[0], row[1]) for row in cursor.fetchall()}
# Búsqueda O(1) en lugar de consulta SQL por cada fila
```

**Recomendación**: Para cubos con > 10,000 filas, considerar implementar caché con índice hash.

---

## 🔄 Flujo de Trabajo Recomendado

### Carga Diaria

```
Día 1:
├─ Actualizar cubo desde Power Query (conectado a Softland)
├─ Cargar cubo en AppKS
├─ Resultado: 50 requisiciones nuevas insertadas
└─ Verificar en "Historial de Cargas"

Día 2:
├─ Actualizar cubo desde Power Query
├─ Cargar cubo en AppKS
├─ Resultado: 15 requisiciones nuevas insertadas, 50 omitidas
└─ Verificar en "Historial de Cargas"

Día 3: ...
```

### Workflow Completo

1. **Mañana**: Actualizar cubos desde Power Query
2. **Cargar en AppKS**: Subir Cubo de Requisiciones
3. **Verificar**: Revisar cantidad de insertadas/omitidas
4. **Trabajar**: Gestionar requisiciones, crear OC, etc.
5. **Noche**: Crear backup de la BD

---

## 📚 Referencias de Código

- **Archivo**: `database.py`
- **Función principal**: `cargar_requisiciones_desde_cubo()` (línea ~415)
- **Migración**: `migrar_base_datos_existente()` (línea ~262)
- **Esquema**: `inicializar_base_datos()` (línea ~42)
- **Auditoría**: `obtener_historial_cargas()` (línea ~754)

---

## 🎓 Buenas Prácticas para Desarrolladores

1. **Nunca usar `id` para lógica de negocio**: Usar clave compuesta `(numreq, codprod)`
2. **No hacer UPDATE en cargas masivas**: Solo INSERT
3. **Validar datos antes de insertar**: Campos críticos no vacíos
4. **Registrar siempre en auditoría**: Tabla `cargas_diarias`
5. **Manejar fechas de manera robusta**: Conversión segura con try/except
6. **Caché de claves existentes compuestas**: Para performance
7. **Tests de idempotencia**: Verificar que cargar 2x = mismos datos
8. **Permitir múltiples productos por requisición**: Cada combinación (NumReq, CodProd) es única

---

**Desarrollado por**: Cristian Salas  
**Empresa**: KS Seguridad Industrial - Sucursal Talca  
**Fecha**: Febrero 2026
