import uuid
from datetime import datetime
from sqlalchemy import Column, Numeric, Integer, Date, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base

class Mora(Base):
    __tablename__ = "moras"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prestamo_id     = Column(UUID(as_uuid=True), ForeignKey("prestamos.id"), nullable=False)
    cuota_id        = Column(UUID(as_uuid=True), ForeignKey("cuotas_programadas.id"), nullable=False)

    fecha_generada  = Column(Date, nullable=False, default=datetime.utcnow)
    dias_mora       = Column(Integer, nullable=False)
    saldo_vencido   = Column(Numeric(14, 2), nullable=False)
    tasa_mora       = Column(Numeric(7, 4), nullable=False)
    monto_mora      = Column(Numeric(14, 2), nullable=False)

    es_pagada       = Column(Boolean, default=False)
    fecha_pago      = Column(Date)

    prestamo = relationship("Prestamo")
    cuota    = relationship("CuotaProgramada")

    def __repr__(self):
        return f"<Mora ${self.monto_mora} | {self.dias_mora} días | Pagada: {self.es_pagada}>"
