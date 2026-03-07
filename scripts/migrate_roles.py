"""
Script de migración para renombrar los roles en PostgreSQL.
Ejecutar: venv\\Scripts\\python.exe scripts/migrate_roles.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import engine
from sqlalchemy import text

def migrar_roles():
    with engine.connect() as conn:
        try:
            print("Agregando nuevos valores al enum rolusuario...")
            conn.execute(text("ALTER TYPE rolusuario ADD VALUE IF NOT EXISTS 'OFICIAL_COBRO'"))
            conn.execute(text("ALTER TYPE rolusuario ADD VALUE IF NOT EXISTS 'COBRADOR_AUTORIZADO'"))
            conn.commit()
            print("Nuevos valores añadidos al enum.")
        except Exception as e:
            print(f"Error al añadir valores: {e}")
            conn.rollback()
            return

        try:
            print("Actualizando registros existentes...")
            conn.execute(text("UPDATE usuarios SET rol = 'OFICIAL_COBRO' WHERE rol = 'OFICIAL'"))
            conn.execute(text("UPDATE usuarios SET rol = 'COBRADOR_AUTORIZADO' WHERE rol = 'COBRADOR'"))
            conn.commit()
            print("Registros actualizados correctamente.")
        except Exception as e:
            print(f"Error al actualizar registros: {e}")
            conn.rollback()

if __name__ == "__main__":
    migrar_roles()
    print("Migración de roles completada.")
