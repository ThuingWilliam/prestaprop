"""
Script: seed_empresa_admin.py
Crea la empresa base 'PrestaProp' y la vincula al administrador global.
Ejecutar una sola vez en local y en producción.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models import Usuario, Empresa
from models.enums import RolUsuario
from decimal import Decimal

def seed():
    db = SessionLocal()
    try:
        # Buscar si ya existe PrestaProp
        empresa = db.query(Empresa).filter(Empresa.nombre == 'PrestaProp').first()
        if not empresa:
            empresa = Empresa(nombre='PrestaProp', capital_inicial=Decimal('0'))
            db.add(empresa)
            db.flush()
            print(f"[OK] Empresa 'PrestaProp' creada con ID: {empresa.id}")
        else:
            print(f"[INFO] Empresa 'PrestaProp' ya existe. ID: {empresa.id}")

        # Vincular el administrador global a esta empresa
        admin = db.query(Usuario).filter(
            Usuario.rol == RolUsuario.ADMINISTRADOR
        ).first()

        if admin:
            if admin.empresa_id != empresa.id:
                admin.empresa_id = empresa.id
                print(f"[OK] Administrador '{admin.username}' vinculado a PrestaProp")
            else:
                print(f"[INFO] Administrador '{admin.username}' ya estaba vinculado a PrestaProp")
        else:
            print("[WARN] No se encontró ningún usuario con rol ADMINISTRADOR")

        db.commit()
        print("\n✅ Seed completado exitosamente.")
    except Exception as e:
        db.rollback()
        print(f"[ERROR] {e}")
    finally:
        db.close()

if __name__ == '__main__':
    seed()
