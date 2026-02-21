import uuid
from datetime import datetime
from sqlalchemy import Column, String, Numeric, Date, DateTime, Enum, ForeignKey, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base
from .enums import MetodoPago

class Pago(Base):
    __tablename__ = "pagos"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prestamo_id    = Column(UUID(as_uuid=True), ForeignKey("prestamos.id"), nullable=False)
    registrado_por = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=False)

    fecha_pago       = Column(Date, nullable=False, default=datetime.utcnow)
    monto_recibido   = Column(Numeric(14, 2), nullable=False)
    metodo_pago      = Column(Enum(MetodoPago), default=MetodoPago.EFECTIVO)
    numero_referencia = Column(String(100))
    notas            = Column(Text)

    # Desglose
    aplicado_mora      = Column(Numeric(14, 2), default=0)
    aplicado_interes   = Column(Numeric(14, 2), default=0)
    aplicado_capital   = Column(Numeric(14, 2), default=0)

    # Bandera recálculo
    genero_recalculo   = Column(Boolean, default=False)
    nuevo_monto_cuota  = Column(Numeric(14, 2))

    creado_en = Column(DateTime, default=datetime.utcnow)

    # Relaciones
    prestamo              = relationship("Prestamo", back_populates="pagos")
    registrado_por_usuario = relationship("Usuario", back_populates="pagos_registrados")
    aplicaciones          = relationship("AplicacionPago", back_populates="pago", cascade="all, delete-orphan")

class AplicacionPago(Base):
    __tablename__ = "aplicaciones_pago"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pago_id     = Column(UUID(as_uuid=True), ForeignKey("pagos.id"), nullable=False)
    cuota_id    = Column(UUID(as_uuid=True), ForeignKey("cuotas_programadas.id"), nullable=False)

    monto_aplicado    = Column(Numeric(14, 2), nullable=False)
    capital_aplicado  = Column(Numeric(14, 2), default=0)
    interes_aplicado  = Column(Numeric(14, 2), default=0)
    mora_aplicada     = Column(Numeric(14, 2), default=0)

    pago  = relationship("Pago", back_populates="aplicaciones")
    cuota = relationship("CuotaProgramada", back_populates="aplicaciones")
