"""
Crea el usuario Administrador en la DB de Neon.
Ejecutar: py scripts/seed_admin_neon.py
"""
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from database import SessionLocal
from models import Usuario, RolUsuario

def main():
    db = SessionLocal()
    try:
        # Verificar si ya existe un admin
        admin = db.query(Usuario).filter(Usuario.rol == RolUsuario.ADMINISTRADOR).first()
        if admin:
            print(f"Admin already exists: {admin.username}")
            admin.set_password("Daylan.13")
            db.commit()
            print("Password updated to: Daylan.13")
            return
        
        # Crear admin
        admin = Usuario(
            nombre="Administrador",
            nombre_completo="Administrador del Sistema",
            username="admin",
            email="admin@prestapro.com",
            rol=RolUsuario.ADMINISTRADOR
        )
        admin.set_password("Daylan.13")
        db.add(admin)
        db.commit()
        print("Admin created successfully!")
        print(f"  Username: admin")
        print(f"  Password: Daylan.13")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
