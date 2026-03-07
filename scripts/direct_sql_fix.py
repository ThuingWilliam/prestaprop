import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def crear_inyecciones():
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    conn.autocommit = True
    cursor = conn.cursor()
    
    print("Conectado a Neon. Creando tabla...")
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inyecciones_capital (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                empresa_id UUID NOT NULL REFERENCES empresas(id),
                monto NUMERIC(14,2) NOT NULL,
                descripcion TEXT,
                fecha TIMESTAMP DEFAULT NOW(),
                registrado_por_id UUID REFERENCES usuarios(id)
            )
        """)
        print("Tabla creada.")
    except Exception as e:
        print(f"Error: {e}")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    crear_inyecciones()
