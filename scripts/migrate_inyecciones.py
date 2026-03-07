"""
Script de migración para crear la tabla inyecciones_capital en la BD.
Ejecutar: venv\\Scripts\\python.exe scripts/migrate_inyecciones.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import engine

def migrar():
    from sqlalchemy import text
    print("Creando tabla inyecciones_capital...")
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS inyecciones_capital (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                empresa_id UUID NOT NULL REFERENCES empresas(id),
                monto NUMERIC(14,2) NOT NULL,
                descripcion TEXT,
                fecha TIMESTAMP DEFAULT NOW(),
                registrado_por_id UUID REFERENCES usuarios(id)
            )
        """))
        conn.commit()
    print("Tabla inyecciones_capital creada exitosamente.")

if __name__ == "__main__":
    migrar()
