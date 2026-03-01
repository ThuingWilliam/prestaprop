import os
from dotenv import load_dotenv
load_dotenv()
from database import engine, Base
from models import Empresa
from sqlalchemy import text

def run_migration():
    print("Creando nuevas tablas...")
    Base.metadata.create_all(bind=engine, tables=[Empresa.__table__])
    
    with engine.connect() as conn:
        print("Alterando enum rolusuario...")
        # Note: postgres ENUM alterations might need their own commit before use.
        # But IF NOT EXISTS handles duplicate errors on 9.3+
        try:
            # We must use autocommit for ALTER TYPE
            conn.execution_options(isolation_level="AUTOCOMMIT").execute(text("ALTER TYPE rolusuario ADD VALUE IF NOT EXISTS 'GERENTE_EMPRESA';"))
            print("Enum actualizado.")
        except Exception as e:
            print(f"Error o ya existe: {e}")
        
        print("Añadiendo columnas empresa_id a usuarios y clientes...")
        try:
            conn.execute(text('ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS empresa_id UUID REFERENCES empresas(id);'))
            conn.execute(text('ALTER TABLE clientes ADD COLUMN IF NOT EXISTS empresa_id UUID REFERENCES empresas(id);'))
            conn.commit()
            print("Columnas añadidas exitosamente.")
        except Exception as e:
            print(f"Error modificando columnas: {e}")
            
    print("Migración completada!")

if __name__ == "__main__":
    run_migration()
