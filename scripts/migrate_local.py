import sys, os
from dotenv import load_dotenv
load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine, Base
from sqlalchemy import text

def migrar_local():
    print(f"Conectado a la base de datos: {engine.url}")
    
    with engine.connect() as conn:
        try:
            print("Añadiendo nuevos roles al enum...")
            conn.execute(text("ALTER TYPE rolusuario ADD VALUE IF NOT EXISTS 'GERENTE_EMPRESA'"))
            conn.execute(text("ALTER TYPE rolusuario ADD VALUE IF NOT EXISTS 'OFICIAL_COBRO'"))
            conn.execute(text("ALTER TYPE rolusuario ADD VALUE IF NOT EXISTS 'COBRADOR_AUTORIZADO'"))
            conn.commit()
            print("OK.")
        except Exception as e:
            print("Ignorando error de enum (puede que ya existan):", str(e))
            conn.rollback()

        try:
            print("Actualizando roles antiguos...")
            conn.execute(text("UPDATE usuarios SET rol = 'OFICIAL_COBRO' WHERE CAST(rol AS VARCHAR) = 'OFICIAL'"))
            conn.execute(text("UPDATE usuarios SET rol = 'COBRADOR_AUTORIZADO' WHERE CAST(rol AS VARCHAR) = 'COBRADOR'"))
            conn.execute(text("UPDATE bitacora_auditoria SET descripcion = REPLACE(descripcion, 'OFICIAL', 'OFICIAL_COBRO') WHERE descripcion LIKE '%OFICIAL%'"))
            conn.commit()
            print("OK.")
        except Exception as e:
            print("Ignorando error de update (quizás no hay tabla de usuarios todavía):", str(e))
            conn.rollback()
            
    # Finalmente creamos las tablas faltantes como inyecciones_capital o empresas que importamos en los modelos.
    print("Creando tablas faltantes (InyeccionCapital, Empresa si no existen)...")
    from models import Empresa, InyeccionCapital
    Base.metadata.create_all(bind=engine)
    print("Base de datos sincronizada exhaustivamente con los modelos locales.")

if __name__ == "__main__":
    migrar_local()
