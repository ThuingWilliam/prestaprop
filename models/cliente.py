import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Numeric, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base
from .enums import EstadoCliente
from .empresa import Empresa

class Cliente(Base):
    __tablename__ = "clientes"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    primer_nombre   = Column(String(100), nullable=False)
    apellido        = Column(String(100), nullable=False)
    numero_id       = Column(String(20), unique=True, nullable=False)
    telefono        = Column(String(20), nullable=True)
    correo          = Column(String(150), nullable=True)
    direccion       = Column(Text, nullable=True)
    ocupacion       = Column(String(100), nullable=True)
    ingreso_mensual = Column(Numeric(14, 2), nullable=True)
    liquidacion_promedio = Column(Numeric(14, 2), nullable=True)
    fecha_inicio_laboral = Column(DateTime, nullable=True)
    estado          = Column(Enum(EstadoCliente), default=EstadoCliente.ACTIVO)
    creado_por_usuario_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True)
    empresa_id      = Column(UUID(as_uuid=True), ForeignKey("empresas.id"), nullable=True)
    creado_en       = Column(DateTime, default=datetime.utcnow)

    # Relaciones
    empresa = relationship("Empresa", backref="clientes")
    creado_por_usuario = relationship("Usuario")
    prestamos   = relationship("Prestamo", back_populates="cliente")
    referencias = relationship("ReferenciaCliente", back_populates="cliente", cascade="all, delete-orphan")

    @property
    def nombre_completo(self):
        return f"{self.primer_nombre} {self.apellido}"

    @property
    def antiguedad(self):
        if not self.fecha_inicio_laboral:
            return "No especificado"
        
        from dateutil.relativedelta import relativedelta
        delta = relativedelta(datetime.utcnow(), self.fecha_inicio_laboral)
        
        years = delta.years
        months = delta.months
        
        if years > 0:
            return f"{years} Años, {months} Meses" if months > 0 else f"{years} Años"
        return f"{months} Meses"

class ReferenciaCliente(Base):
    __tablename__ = "referencias_clientes"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cliente_id  = Column(UUID(as_uuid=True), ForeignKey("clientes.id"), nullable=False)
    nombre      = Column(String(150), nullable=False)
    telefono    = Column(String(20), nullable=False)
    parentesco  = Column(String(50))

    cliente = relationship("Cliente", back_populates="referencias")
