import os
from decimal import Decimal

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'enterprise_secret_key_123!@#')

    # En local usa la DB de PostgreSQL. En Render usa la variable DATABASE_URL (Neon).
    _db_url = os.environ.get('DATABASE_URL', 'postgresql://postgres:admin@localhost:5432/prestamos')
    # Neon a veces devuelve 'postgres://' que SQLAlchemy no acepta; lo corregimos:
    SQLALCHEMY_DATABASE_URI = _db_url.replace('postgres://', 'postgresql://', 1)

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    DEBUG = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'
    PORT = int(os.environ.get('PORT', 5000))
    PERMANENT_SESSION_LIFETIME = 180  # 3 minutos
