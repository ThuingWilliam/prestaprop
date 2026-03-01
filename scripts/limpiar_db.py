import os
from dotenv import load_dotenv

# Cargar el .env (Asegúrate de que estás apuntando a Neon si quieres borrar allí)
load_dotenv()

from database import SessionLocal
from models import Usuario, Cliente, Empresa, Prestamo, CuotaProgramada, Pago, BitacoraAuditoria, AplicacionPago
from models.enums import RolUsuario

def resetear_base_datos():
    db = SessionLocal()
    try:
        print("Iniciando borrado de datos...")
        
        # El orden es importante por las Foreign Keys
        db.query(AplicacionPago).delete()
        db.query(Pago).delete()
        db.query(CuotaProgramada).delete()
        db.query(Prestamo).delete()
        db.query(BitacoraAuditoria).delete()
        db.query(Cliente).delete()
        
        # Eliminar todos los usuarios excepto el administrador global original
        usuarios = db.query(Usuario).all()
        admin_guardado = False
        for u in usuarios:
            if u.rol == RolUsuario.ADMINISTRADOR and not admin_guardado:
                admin_guardado = True  # Guardamos el primer admin que encontremos
                # CRITICO: Remover la vinculación del admin a cualquier empresa si existiese, 
                # antes de borrar empresas para no chocar con ForeignKeys.
                u.empresa_id = None
                print(f"Conservando administrador: {u.username}")
            else:
                db.delete(u)
                
        db.flush() # Actualizamos la DB antes de borrar empresas para remover refs
                
        # Finalmente eliminar las empresas (ya que los usuarios no-admin y clientes se borraron)
        db.query(Empresa).delete()
        
        db.commit()
        print("Limpieza completada exitosamente. Solo ha quedado el administrador.")
        
    except Exception as e:
        db.rollback()
        print(f"Error durante la limpieza: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    resetear_base_datos()
