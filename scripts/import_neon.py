"""
Script para crear las tablas en Neon.tech usando SQLAlchemy.
Ejecutar con el venv activado desde la raiz del proyecto:
    py scripts/import_neon.py
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from database import engine, Base
# Importar TODOS los modelos para que SQLAlchemy los registre
from models import (
    Usuario, Cliente, ReferenciaCliente, ProductoPrestamo,
    Prestamo, CuotaProgramada, Pago, AplicacionPago,
    Mora, BitacoraAuditoria
)

def main():
    print(f"Connecting to: {engine.url}")
    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    print("All tables created successfully on Neon!")
    
    # Verificar tablas creadas
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"\nTables found ({len(tables)}):")
    for t in sorted(tables):
        print(f"  - {t}")

if __name__ == "__main__":
    main()
