"""
Script maestro de migración — ejecutar primero al desplegar.
Crea las tablas empresas e inyecciones_capital si no existen.
Ejecutar: venv\\Scripts\\python.exe scripts/migrate_all.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import engine
from sqlalchemy import text

SQL = """
-- Tabla de Empresas
CREATE TABLE IF NOT EXISTS empresas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre VARCHAR(150) NOT NULL,
    capital_inicial NUMERIC(14,2) DEFAULT 0.00,
    creado_en TIMESTAMP DEFAULT NOW()
);

-- Columnas empresa_id en usuarios y clientes
DO $$ BEGIN
    ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS empresa_id UUID REFERENCES empresas(id);
EXCEPTION WHEN duplicate_column THEN NULL; END $$;

DO $$ BEGIN
    ALTER TABLE clientes ADD COLUMN IF NOT EXISTS empresa_id UUID REFERENCES empresas(id);
EXCEPTION WHEN duplicate_column THEN NULL; END $$;

-- Nuevos valores del enum de rol
DO $$ BEGIN
    ALTER TYPE rolusuario ADD VALUE IF NOT EXISTS 'GERENTE_EMPRESA';
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
    ALTER TYPE rolusuario ADD VALUE IF NOT EXISTS 'OFICIAL_COBRO';
EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
    ALTER TYPE rolusuario ADD VALUE IF NOT EXISTS 'COBRADOR_AUTORIZADO';
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Renombrar roles existentes
UPDATE usuarios SET rol = 'OFICIAL_COBRO' WHERE rol = 'OFICIAL';
UPDATE usuarios SET rol = 'COBRADOR_AUTORIZADO' WHERE rol = 'COBRADOR';

-- Tabla de Inyecciones de Capital
CREATE TABLE IF NOT EXISTS inyecciones_capital (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id UUID NOT NULL REFERENCES empresas(id),
    monto NUMERIC(14,2) NOT NULL,
    descripcion TEXT,
    fecha TIMESTAMP DEFAULT NOW(),
    registrado_por_id UUID REFERENCES usuarios(id)
);
"""

if __name__ == "__main__":
    print("Ejecutando migración completa...")
    with engine.connect() as conn:
        conn.execute(text(SQL))
        conn.commit()
    print("¡Migración completada exitosamente!")
