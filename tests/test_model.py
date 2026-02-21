from database import SessionLocal
from models import Prestamo
import json

db = SessionLocal()
prestamo = db.query(Prestamo).first()
if prestamo:
    print(f"Prestamo: {prestamo.numero_prestamo}")
    print(f"Monto Capital: {prestamo.monto_capital} (Type: {type(prestamo.monto_capital)})")
    print(f"Total Pagado: {prestamo.total_pagado} (Type: {type(prestamo.total_pagado)})")
    print(f"Saldo Capital: {prestamo.saldo_capital} (Type: {type(prestamo.saldo_capital)})")
    print(f"Monto Pendiente Total: {prestamo.monto_pendiente_total} (Type: {type(prestamo.monto_pendiente_total)})")
    
    # Test formatting
    print(f"Formatted Capital: {'{:,.2f}'.format(prestamo.monto_capital)}")
    print(f"Formatted Paid: {'{:,.2f}'.format(prestamo.total_pagado)}")
else:
    print("No prestamos found")
db.close()
