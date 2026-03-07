"""
Script de ejemplo: Integración del módulo de compras con AppKS
Demuestra cómo usar compras_service.py en el flujo de trabajo existente
"""

import pandas as pd
from app.services import compras_service as cs
from app import database as db
from app import config


def ejemplo_1_inicializacion():
    """
    EJEMPLO 1: Inicializar el módulo de compras por primera vez
    """
    print("=" * 70)
    print("EJEMPLO 1: Inicialización del Módulo de Compras")
    print("=" * 70)
    
    try:
        # Crear las tablas (es idempotente, seguro ejecutar múltiples veces)
        cs.inicializar_modulo_compras()
        
        print("\n✅ Módulo inicializado correctamente")
        print("   - Tabla 'compras' creada")
        print("   - Tabla 'gestion' creada")
        print("   - Índices optimizados creados")
        print("   - Triggers configurados")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


def ejemplo_2_carga_compras_desde_excel():
    """
    EJEMPLO 2: Cargar cubo de compras desde archivo Excel
    """
    print("\n" + "=" * 70)
    print("EJEMPLO 2: Carga de Compras desde Excel")
    print("=" * 70)
    
    # Ruta del archivo (ajustar según tu estructura)
    ruta_archivo = "data/cubos/cubo_compras.xlsx"
    
    try:
        # Opción A: Leer y cargar manualmente
        print(f"\n📂 Leyendo archivo: {ruta_archivo}")
        df_compras = pd.read_excel(ruta_archivo)
        
        print(f"📊 Registros en archivo: {len(df_compras)}")
        print(f"📋 Columnas: {', '.join(df_compras.columns)}")
        
        # Validar estructura
        es_valido, mensaje, _ = cs.validar_columnas_compras(df_compras)
        if not es_valido:
            print(f"\n⚠️ Advertencia: {mensaje}")
            return
        
        print(f"\n✅ Validación exitosa: {mensaje}")
        
        # Cargar a la base de datos
        print("\n🚀 Iniciando carga...")
        with cs.get_db_connection() as conn:
            insertados, omitidos, errores = cs.cargar_compras_desde_dataframe(df_compras, conn)
        
        print(f"\n📊 Resultados:")
        print(f"   ✅ Insertados: {insertados}")
        print(f"   ⏭️  Omitidos: {omitidos}")
        
        if errores:
            print(f"\n⚠️ Errores encontrados ({len(errores)}):")
            for i, error in enumerate(errores[:5]):  # Mostrar máximo 5
                print(f"   {i+1}. {error}")
            if len(errores) > 5:
                print(f"   ... y {len(errores) - 5} más")
        
        # Opción B: Usar función de alto nivel (más simple)
        # insertados, omitidos, errores = cs.cargar_compras_desde_archivo_excel(ruta_archivo)
        
    except FileNotFoundError:
        print(f"\n❌ Error: No se encontró el archivo {ruta_archivo}")
        print("   Asegúrate de colocar el archivo en la ubicación correcta")
    except Exception as e:
        print(f"\n❌ Error inesperado: {str(e)}")


def ejemplo_3_actualizar_gestion():
    """
    EJEMPLO 3: Actualizar tabla de gestión con datos de compras
    """
    print("\n" + "=" * 70)
    print("EJEMPLO 3: Actualización de Gestión desde Compras")
    print("=" * 70)
    
    try:
        with cs.get_db_connection() as conn:
            print("\n🔄 Ejecutando cruce de datos...")
            actualizados, mensajes = cs.actualizar_gestion_desde_compras(conn)
            
            print(f"\n📊 Resultado:")
            print(f"   ✅ Registros actualizados: {actualizados}")
            
            print(f"\n📝 Detalles:")
            for mensaje in mensajes:
                print(f"   {mensaje}")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


def ejemplo_4_proceso_completo():
    """
    EJEMPLO 4: Ejecutar proceso completo (carga + actualización)
    """
    print("\n" + "=" * 70)
    print("EJEMPLO 4: Proceso Completo en Un Solo Paso")
    print("=" * 70)
    
    ruta_archivo = "data/cubos/cubo_compras.xlsx"
    
    try:
        # Leer archivo
        print(f"\n📂 Leyendo archivo: {ruta_archivo}")
        df_compras = pd.read_excel(ruta_archivo)
        print(f"📊 Registros: {len(df_compras)}")
        
        # Ejecutar proceso completo
        print("\n🚀 Ejecutando proceso completo...")
        resultado = cs.ejecutar_proceso_completo_compras(df_compras)
        
        if resultado['exito']:
            print(f"\n✅ {resultado['mensaje_general']}")
            
            print(f"\n📦 Detalles de Carga de Compras:")
            print(f"   Insertados: {resultado['carga_compras']['insertados']}")
            print(f"   Omitidos: {resultado['carga_compras']['omitidos']}")
            
            print(f"\n🔄 Detalles de Actualización de Gestión:")
            print(f"   Actualizados: {resultado['actualizacion_gestion']['actualizados']}")
            
            for mensaje in resultado['actualizacion_gestion']['mensajes']:
                print(f"   {mensaje}")
        else:
            print(f"\n❌ {resultado['mensaje_general']}")
            
    except FileNotFoundError:
        print(f"\n❌ Error: No se encontró el archivo {ruta_archivo}")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


def ejemplo_5_consultas_y_reportes():
    """
    EJEMPLO 5: Consultas y reportes sobre compras
    """
    print("\n" + "=" * 70)
    print("EJEMPLO 5: Consultas y Reportes")
    print("=" * 70)
    
    try:
        with cs.get_db_connection() as conn:
            # Estadísticas generales
            print("\n📊 ESTADÍSTICAS GENERALES")
            print("-" * 70)
            stats = cs.obtener_estadisticas_compras(conn)
            
            print(f"Total de registros: {stats['total_registros']}")
            print(f"OCs únicas: {stats['total_ocs']}")
            print(f"Productos únicos: {stats['total_productos']}")
            print(f"Valor total: ${stats['valor_total']:,.2f}")
            
            if stats['ultima_carga']:
                print(f"Última carga: {stats['ultima_carga']}")
            
            if stats['por_estado']:
                print("\nDistribución por estado:")
                for estado, cantidad in stats['por_estado'].items():
                    print(f"  - {estado}: {cantidad}")
            
            # Compras pendientes
            print("\n📋 COMPRAS PENDIENTES")
            print("-" * 70)
            df_pendientes = cs.obtener_compras_pendientes(conn)
            
            if len(df_pendientes) > 0:
                print(f"Total pendientes: {len(df_pendientes)}")
                print("\nMuestra de primeras 5:")
                print(df_pendientes[['num_oc', 'codprod', 'proveedor', 'saldo_pendiente']].head())
            else:
                print("✅ No hay compras pendientes")
            
            # Ejemplo: Consultar una OC específica
            if stats['total_ocs'] > 0:
                print("\n🔍 EJEMPLO: Detalle de una OC")
                print("-" * 70)
                
                # Obtener la primera OC
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT num_oc FROM compras LIMIT 1")
                num_oc = cursor.fetchone()
                
                if num_oc:
                    num_oc = num_oc[0]
                    print(f"Consultando OC: {num_oc}")
                    
                    df_oc = cs.obtener_compras_por_oc(num_oc, conn)
                    print(f"\nLíneas de la OC: {len(df_oc)}")
                    print(df_oc[['codprod', 'cantidad_solicitada', 'cantidad_total_recibida', 'precio_compra', 'total_linea']])
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


def ejemplo_6_crear_datos_prueba():
    """
    EJEMPLO 6: Crear datos de prueba para testing
    """
    print("\n" + "=" * 70)
    print("EJEMPLO 6: Crear Datos de Prueba")
    print("=" * 70)
    
    try:
        # Crear DataFrame de prueba
        print("\n📝 Creando datos de prueba...")
        df_test = pd.DataFrame({
            'NumOC': ['OC-TEST-001', 'OC-TEST-001', 'OC-TEST-002'],
            'CodProd': ['PROD-A', 'PROD-B', 'PROD-C'],
            'Proveedor': ['Proveedor Test A', 'Proveedor Test A', 'Proveedor Test B'],
            'CantidadSolicitada': [100, 50, 200],
            'CantidadRecibida': [100, 30, 0],
            'CantidadManual': [0, 0, 0],
            'PrecioCompra': [1500, 2000, 1200],
            'FechaOC': ['2026-02-15', '2026-02-15', '2026-02-16'],
            'FechaRecepcion': ['2026-02-16', None, None],
            'EstadoLinea': ['Recibido', 'Parcial', 'Pendiente'],
            'BodegaCodigo': ['BOD-01', 'BOD-01', 'BOD-02'],
            'BodegaNombre': ['Bodega Central', 'Bodega Central', 'Bodega Talca'],
            'Observacion': ['', 'Falta confirmar', '']
        })
        
        print(f"✅ Creados {len(df_test)} registros de prueba")
        print("\n📊 Preview:")
        print(df_test[['NumOC', 'CodProd', 'CantidadSolicitada', 'CantidadRecibida', 'EstadoLinea']])
        
        # Cargar a la BD
        print("\n🚀 Cargando datos de prueba a la base de datos...")
        with cs.get_db_connection() as conn:
            insertados, omitidos, errores = cs.cargar_compras_desde_dataframe(df_test, conn)
        
        print(f"\n📊 Resultado:")
        print(f"   ✅ Insertados: {insertados}")
        print(f"   ⏭️  Omitidos: {omitidos}")
        
        if insertados > 0:
            print("\n💡 Puedes consultar estos datos con los reportes del ejemplo 5")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


def ejemplo_7_migracion_requisiciones_a_gestion():
    """
    EJEMPLO 7: Migrar datos de requisiciones a gestión (si es necesario)
    """
    print("\n" + "=" * 70)
    print("EJEMPLO 7: Migración de Requisiciones a Gestión")
    print("=" * 70)
    
    try:
        with cs.get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar si hay datos en requisiciones
            cursor.execute("SELECT COUNT(*) FROM requisiciones")
            count_req = cursor.fetchone()[0]
            
            print(f"\n📊 Registros en requisiciones: {count_req}")
            
            if count_req == 0:
                print("⚠️ No hay datos en requisiciones para migrar")
                return
            
            # Verificar si gestión está vacía
            cursor.execute("SELECT COUNT(*) FROM gestion")
            count_gest = cursor.fetchone()[0]
            
            print(f"📊 Registros actuales en gestión: {count_gest}")
            
            if count_gest > 0:
                print("\n⚠️ La tabla gestión ya tiene datos")
                respuesta = input("¿Deseas migrar de todas formas? (s/n): ")
                if respuesta.lower() != 's':
                    print("Operación cancelada")
                    return
            
            # Migrar datos
            print("\n🔄 Migrando datos de requisiciones a gestión...")
            cursor.execute("""
                INSERT OR IGNORE INTO gestion (
                    numreq, codprod, desprod, cantidad, fecha_requisicion,
                    sucursal_destino, proveedor, oc, estado_oc, fecha_oc,
                    cant_recibida, saldo_pendiente
                )
                SELECT 
                    numreq, codprod, desprod, cantidad, fecha_requisicion,
                    sucursal_destino, proveedor, oc, estado_oc, fecha_oc,
                    cant_recibida, saldo_pendiente
                FROM requisiciones
            """)
            
            migrados = cursor.rowcount
            conn.commit()
            
            print(f"\n✅ Migración completada: {migrados} registros migrados")
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


def menu_principal():
    """
    Menú interactivo para ejecutar ejemplos
    """
    print("\n" + "=" * 70)
    print("MÓDULO DE COMPRAS - EJEMPLOS DE INTEGRACIÓN")
    print("AppKS - KS Seguridad Industrial")
    print("=" * 70)
    
    while True:
        print("\n📋 Selecciona un ejemplo:")
        print("  1. Inicializar módulo de compras")
        print("  2. Cargar compras desde Excel")
        print("  3. Actualizar gestión desde compras")
        print("  4. Proceso completo (carga + actualización)")
        print("  5. Consultas y reportes")
        print("  6. Crear datos de prueba")
        print("  7. Migrar requisiciones a gestión")
        print("  8. Ejecutar todos los ejemplos")
        print("  0. Salir")
        
        opcion = input("\nOpción: ").strip()
        
        if opcion == '1':
            ejemplo_1_inicializacion()
        elif opcion == '2':
            ejemplo_2_carga_compras_desde_excel()
        elif opcion == '3':
            ejemplo_3_actualizar_gestion()
        elif opcion == '4':
            ejemplo_4_proceso_completo()
        elif opcion == '5':
            ejemplo_5_consultas_y_reportes()
        elif opcion == '6':
            ejemplo_6_crear_datos_prueba()
        elif opcion == '7':
            ejemplo_7_migracion_requisiciones_a_gestion()
        elif opcion == '8':
            ejemplo_1_inicializacion()
            ejemplo_6_crear_datos_prueba()
            ejemplo_5_consultas_y_reportes()
        elif opcion == '0':
            print("\n👋 ¡Hasta luego!")
            break
        else:
            print("\n❌ Opción no válida")


if __name__ == "__main__":
    """
    Ejecutar el script directamente mostrará el menú interactivo
    """
    menu_principal()
