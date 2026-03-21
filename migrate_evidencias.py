from dotenv import load_dotenv
import os

# Cargar variables de entorno
load_dotenv()

from database import engine, Base
from sqlalchemy import text
import models # Importar modelos para que Base los conozca

def migrate():
    print("--- Iniciando Migración de Evidencias y Mejoras de Clientes ---")
    
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            # 1. Agregar columnas a 'clientes'
            print("Agregando columnas a 'clientes'...")
            
            # liquidacion_promedio
            try:
                conn.execute(text("ALTER TABLE clientes ADD COLUMN liquidacion_promedio NUMERIC(14, 2)"))
                print("  + Columna 'liquidacion_promedio' agregada.")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print("  - Columna 'liquidacion_promedio' ya existe.")
                else:
                    raise e
            
            # fecha_inicio_laboral
            try:
                conn.execute(text("ALTER TABLE clientes ADD COLUMN fecha_inicio_laboral TIMESTAMP WITHOUT TIME ZONE"))
                print("  + Columna 'fecha_inicio_laboral' agregada.")
            except Exception as e:
                if "already exists" in str(e).lower():
                    print("  - Columna 'fecha_inicio_laboral' ya existe.")
                else:
                    raise e

            trans.commit()
            print("Columnas de 'clientes' sincronizadas.")
        except Exception as e:
            trans.rollback()
            print(f"Error migrando columnas: {e}")
            return

    # 2. Crear tabla 'evidencias' (y otras faltantes)
    print("Sincronizando tablas (create_all)...")
    try:
        Base.metadata.create_all(engine)
        print("Tablas sincronizadas con éxito.")
    except Exception as e:
        print(f"Error sincronizando tablas: {e}")

    print("--- Migración Finalizada ---")

if __name__ == "__main__":
    migrate()
