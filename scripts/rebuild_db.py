from database import engine, Base
from models import Usuario
from seed_data_pro import seed
import sqlalchemy as sa

def rebuild_user_table():
    print("Iniciando reconstrucción de la tabla 'usuarios'...")
    
    # Conectarse y borrar solo la tabla de usuarios para no perder otros datos
    # o simplemente borrar todo si es desarrollo. 
    # Dado que es un error de UndefinedColumn, lo más limpio es recrear.
    try:
        with engine.connect() as conn:
            # Desactivar FK temporalmente si es necesario (Postgres)
            conn.execute(sa.text("DROP TABLE IF EXISTS aplicaciones_pago CASCADE;"))
            conn.execute(sa.text("DROP TABLE IF EXISTS pagos CASCADE;"))
            conn.execute(sa.text("DROP TABLE IF EXISTS cuotas_programadas CASCADE;"))
            conn.execute(sa.text("DROP TABLE IF EXISTS prestamos CASCADE;"))
            conn.execute(sa.text("DROP TABLE IF EXISTS bitacora_auditoria CASCADE;"))
            conn.execute(sa.text("DROP TABLE IF EXISTS usuarios CASCADE;"))
            conn.commit()
        
        print("Tablas antiguas eliminadas.")
        
        # Crear todo de nuevo con el nuevo esquema
        Base.metadata.create_all(bind=engine)
        print("Tablas creadas con el nuevo esquema.")
        
        # Ejecutar el seed para tener datos
        seed()
        print("Base de datos reiniciada y poblada exitosamente.")
        
    except Exception as e:
        print(f"Error durante la reconstrucción: {e}")

if __name__ == "__main__":
    rebuild_user_table()
