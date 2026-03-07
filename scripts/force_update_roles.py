import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import engine
from sqlalchemy import text

def forzar_update():
    with engine.connect() as conn:
        try:
            print("Forzando actualización de roles antiguos...")
            res = conn.execute(text("UPDATE usuarios SET rol = 'OFICIAL_COBRO' WHERE CAST(rol AS VARCHAR) = 'OFICIAL'"))
            print(f"Oficiales: {res.rowcount}")
            res2 = conn.execute(text("UPDATE usuarios SET rol = 'COBRADOR_AUTORIZADO' WHERE CAST(rol AS VARCHAR) = 'COBRADOR'"))
            print(f"Cobradores: {res2.rowcount}")
            conn.commit()
            print("HECHO")
        except Exception as e:
            conn.rollback()
            print("ERROR", str(e))

if __name__ == "__main__":
    forzar_update()
