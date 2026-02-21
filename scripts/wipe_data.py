import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import create_engine, text
from config import Config
from werkzeug.security import generate_password_hash

def wipe_data():
    engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
    with engine.connect() as conn:
        print("Wiping transactional data (pagos, cuotas, prestamos, clientes)...")
        try:
            conn.execute(text("TRUNCATE TABLE aplicaciones_pago CASCADE"))
            conn.execute(text("TRUNCATE TABLE pagos CASCADE"))
            conn.execute(text("TRUNCATE TABLE cuotas_programadas CASCADE"))
            conn.execute(text("TRUNCATE TABLE prestamos CASCADE"))
            conn.execute(text("TRUNCATE TABLE clientes CASCADE"))
            conn.execute(text("TRUNCATE TABLE bitacora_auditoria CASCADE"))
            print("Transactional data wiped.")

            # Delete all non-admin users
            conn.execute(text("DELETE FROM usuarios WHERE rol != 'ADMINISTRADOR'"))
            print("Non-admin users deleted.")

            # Reset admin password to Daylan.13
            new_hash = generate_password_hash("Daylan.13")
            conn.execute(
                text("UPDATE usuarios SET contrasena_hash=:pwd WHERE rol='ADMINISTRADOR'"),
                {"pwd": new_hash}
            )
            print("Admin password reset to: Daylan.13")

            conn.commit()
            print("Done. Only the ADMINISTRADOR user remains.")
        except Exception as e:
            print(f"Error during wipe: {e}")
            conn.rollback()

if __name__ == "__main__":
    wipe_data()
