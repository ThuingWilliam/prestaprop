import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Numeric, Boolean, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base

class ProductoPrestamo(Base):
    __tablename__ = "productos_prestamo"

    id                    = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre                = Column(String(100), nullable=False)
    descripcion           = Column(Text)
    tasa_interes_anual    = Column(Numeric(7, 4), nullable=False)
    tasa_mora_mensual     = Column(Numeric(7, 4), default=0.0300)
    cargo_mora_fijo       = Column(Numeric(10, 2), default=0)
    monto_minimo          = Column(Numeric(14, 2), nullable=False)
    monto_maximo          = Column(Numeric(14, 2), nullable=False)
    periodos_minimos      = Column(Integer, nullable=False)
    periodos_maximos      = Column(Integer, nullable=False)
    frecuencias_permitidas = Column(String(60), default="SEMANAL,QUINCENAL,MENSUAL")
    activo                 = Column(Boolean, default=True)
    creado_en              = Column(DateTime, default=datetime.utcnow)

    prestamos = relationship("Prestamo", back_populates="producto")
