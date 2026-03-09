# AppKS  Sistema de Gestión Operativa

Sistema interno desarrollado para gestionar **Compras, Requisiciones, Ventas e Inventario**, eliminando la dependencia de planillas Excel. Procesa cubos exportados desde Softland ERP y centraliza la información en una base de datos SQLite.

---

## Tecnologías

- Python 3.10+
- Streamlit
- SQLite
- Pandas

---

## Estructura del Proyecto

```
AppKS/

 AppKS.exe            launcher (doble clic para abrir)
 start_app.py         script launcher
 run.py               entry point de Streamlit
 build.bat            recompila AppKS.exe
 requirements.txt

 app/
    main.py
    config.py
    database.py
    utils.py
    modules/
    services/
        compras_service.py

 data/                base de datos SQLite
 exports/             exportaciones Excel
 backups/             respaldos manuales
 docs/                documentación técnica
 examples/            scripts de referencia
```

---

## Cómo ejecutar

### Opción A  Launcher .exe (usuario final)

Coloca `AppKS.exe` en la raíz del proyecto (junto a `run.py` y la carpeta `venv\`) y haz doble clic.

**Requisito:** el equipo debe tener el entorno virtual `venv\` con las dependencias instaladas.

```
AppKS/
 AppKS.exe    doble clic
 run.py
 venv\
```

### Opción B  Modo desarrollo

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

### Opción C  Recompilar AppKS.exe

```bat
build.bat
```

Copia `dist\AppKS.exe` a la raíz del proyecto tras la compilación.

---

## Módulos

| Módulo | Estado |
|---|---|
| Requisiciones | Operativo |
| Compras | Operativo |
| Análisis Stock | Operativo |
| Ventas | En desarrollo |
| Inventario | En desarrollo |

---

## Flujo de uso

1. Cargar cubo de Compras  inserta/actualiza órdenes de compra
2. Cargar cubo de Requisiciones  registra solicitudes
3. Sincronización automática requisiciones  compras
4. Filtrar, analizar y exportar

---

## Estado actual

**v1.6.1**

- Arquitectura modular por servicios
- UPSERT inteligente en compras
- Carga idempotente (no duplica al recargar)
- Control de versión por hash MD5 en cubos de ventas e inventario
- Sincronización automática requisiciones → compras con validación temporal correcta
- Migraciones de esquema automáticas
- Módulo Análisis Stock: cruce inventario × ventas, estado de stock y rotación
- Edición segura desde la UI
- Launcher .exe para usuarios finales
- Invalidación completa de caché al eliminar cubos (tablas raw + hashes + session state)

---

## Autor

Cristian Salas - Proyecto interno de gestión operativa  KS Seguridad Industrial, Sucursal Talca.
Desarrollado con IA (Claude Sonnet y ChatGPT) 
