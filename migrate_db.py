from dotenv import load_dotenv
load_dotenv()  # Carga variables de .env

from database import engine
from sqlalchemy import text
import sys

def migrate():
    print("Iniciando migración manual...")
    with engine.connect() as conn:
        try:
            # Comando para PostgreSQL (Neon)
            # IF NOT EXISTS no está disponible en todas las versiones para ADD COLUMN, 
            # así que usamos un bloque try/except o verificamos la existencia.
            sql = "ALTER TABLE prestamos ADD COLUMN tipo_calculo VARCHAR(20) DEFAULT 'FRANCES'"
            conn.execute(text(sql))
            conn.commit()
            print("EXITO: Columna 'tipo_calculo' agregada a la tabla 'prestamos'.")
        except Exception as e:
            if "already exists" in str(e).lower() or "bloque" in str(e).lower():
                print("AVISO: La columna ya existe o la migración se aplicó parcialmente.")
            else:
                print(f"ERROR: {e}")
                sys.exit(1)

if __name__ == "__main__":
    migrate()
