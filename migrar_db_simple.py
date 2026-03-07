"""
Script simple para agregar columna desprod a la base de datos
Ejecutar: python migrar_db_simple.py
"""

import sqlite3
import os

# Ruta a la base de datos
DB_PATH = os.path.join("data", "ks_requisiciones.db")

def migrar():
    if not os.path.exists(DB_PATH):
        print(f"❌ Base de datos no encontrada: {DB_PATH}")
        return
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Verificar si tabla existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='compras'")
        if not cursor.fetchone():
            print("⚠️ Tabla 'compras' no existe. No se requiere migración.")
            conn.close()
            return
        
        # Verificar si columna ya existe
        cursor.execute("PRAGMA table_info(compras)")
        columnas = [row[1] for row in cursor.fetchall()]
        
        if 'desprod' in columnas:
            print("✅ La columna 'desprod' YA EXISTE en la tabla compras")
            print("   No se requieren cambios.")
        else:
            # Agregar columna
            cursor.execute("ALTER TABLE compras ADD COLUMN desprod TEXT")
            conn.commit()
            print("✅ MIGRACIÓN EXITOSA")
            print("   Columna 'desprod' agregada a la tabla compras")
            print("\n💡 Ahora puedes:")
            print("   1. Recargar el Cubo de Compras con la columna DesProd")
            print("   2. Ver la columna 'Nombre Producto' en Seguimiento OC")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error al ejecutar migración: {str(e)}")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("MIGRACIÓN: Agregar columna desprod a tabla compras")
    print("="*60 + "\n")
    migrar()
    print("\n" + "="*60)
    input("\nPresiona ENTER para cerrar...")
