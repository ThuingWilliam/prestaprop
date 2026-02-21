from database import SessionLocal, engine, Base
from models import Usuario, Cliente, ProductoPrestamo, Prestamo, CuotaProgramada, RolUsuario, EstadoCliente, FrecuenciaPago, EstadoPrestamo
from services.prestamo_service import generar_tabla_amortizacion
from datetime import date
from decimal import Decimal

def seed():
    # Crear tablas si no existen
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # 1. Usuario Admin
        if not db.query(Usuario).filter(Usuario.username == "admin").first():
            admin = Usuario(
                nombre="William",
                nombre_completo="William Admin",
                username="admin",
                email="admin@prestamopro.com",
                rol=RolUsuario.ADMINISTRADOR
            )
            admin.set_password("admin123")
            db.add(admin)
        
        # Nuevo Usuario Solicitado: user1 / 123
        if not db.query(Usuario).filter(Usuario.username == "user1").first():
            user1 = Usuario(
                nombre="Operador",
                nombre_completo="Usuario Operativo 1",
                username="user1",
                email="user1@prestamopro.com",
                rol=RolUsuario.OFICIAL
            )
            user1.set_password("123")
            db.add(user1)
            
        db.flush()
        admin = db.query(Usuario).filter(Usuario.username == "admin").first()

        # 2. Producto
        if not db.query(ProductoPrestamo).first():
            producto = ProductoPrestamo(
                nombre="Crédito Personal Premium",
                descripcion="Préstamo de libre inversión categoría A.",
                tasa_interes_anual=Decimal("0.24"),
                monto_minimo=Decimal("1000"),
                monto_maximo=Decimal("50000"),
                periodos_minimos=6,
                periodos_maximos=48
            )
            db.add(producto)
            db.flush()
        else:
            producto = db.query(ProductoPrestamo).first()

        # 3. Cliente
        if not db.query(Cliente).first():
            c1 = Cliente(
                primer_nombre="Juan",
                apellido="Pérez",
                numero_id="001-001-0001",
                telefono="8888-8888",
                correo="juan@email.com",
                ingreso_mensual=Decimal("2500")
            )
            db.add(c1)
            db.flush()
        else:
            c1 = db.query(Cliente).first()

        # 4. Préstamo
        if not db.query(Prestamo).first():
            monto = Decimal("5000")
            tasa = Decimal("0.24")
            tabla = generar_tabla_amortizacion(monto, tasa, FrecuenciaPago.MENSUAL, 12, date.today())
            total_interes = sum(c["interes_cuota"] for c in tabla)
            
            p = Prestamo(
                numero_prestamo="PRE-2024-001",
                cliente_id=c1.id,
                producto_id=producto.id,
                aprobado_por=admin.id,
                monto_capital=monto,
                tasa_interes_anual=tasa,
                frecuencia=FrecuenciaPago.MENSUAL,
                total_periodos=12,
                monto_cuota=tabla[0]["total_cuota"],
                total_interes=total_interes,
                total_a_pagar=monto + total_interes,
                saldo_capital=monto,
                saldo_interes=total_interes,
                fecha_desembolso=date.today(),
                fecha_primer_pago=date.today(),
                estado=EstadoPrestamo.ACTIVO
            )
            db.add(p)
            db.flush()
            for d in tabla:
                db.add(CuotaProgramada(prestamo_id=p.id, **d))

        db.commit()
        print("Base de datos inicializada correctamente.")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
