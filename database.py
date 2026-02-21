from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from config import Config
import json

engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def registrar_auditoria(db: Session, tabla: str, registro_id: str, accion: str, usuario_id: str = None, antes: dict = None, despues: dict = None, descripcion: str = None):
    """Registra un evento en la bitácora de auditoría."""
    from models.auditoria import BitacoraAuditoria
    log = BitacoraAuditoria(
        tabla=tabla,
        registro_id=str(registro_id),
        accion=accion,
        valores_antes=json.dumps(antes, default=str) if antes else None,
        valores_despues=json.dumps(despues, default=str) if despues else None,
        descripcion=descripcion,
        cambiado_por=usuario_id
    )
    db.add(log)
    db.flush()
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
