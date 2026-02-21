import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Numeric, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base
from .enums import EstadoCliente

class Cliente(Base):
    __tablename__ = "clientes"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    primer_nombre   = Column(String(100), nullable=False)
    apellido        = Column(String(100), nullable=False)
    numero_id       = Column(String(20), unique=True, nullable=False)
    telefono        = Column(String(20))
    correo          = Column(String(150))
    direccion       = Column(Text)
    ocupacion       = Column(String(100))
    ingreso_mensual = Column(Numeric(14, 2))
    estado          = Column(Enum(EstadoCliente), default=EstadoCliente.ACTIVO)
    creado_por_usuario_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True)
    creado_en       = Column(DateTime, default=datetime.utcnow)

    # Relaciones
    creado_por_usuario = relationship("Usuario")
    prestamos   = relationship("Prestamo", back_populates="cliente")
    referencias = relationship("ReferenciaCliente", back_populates="cliente", cascade="all, delete-orphan")

    @property
    def nombre_completo(self):
        return f"{self.primer_nombre} {self.apellido}"

class ReferenciaCliente(Base):
    __tablename__ = "referencias_clientes"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cliente_id  = Column(UUID(as_uuid=True), ForeignKey("clientes.id"), nullable=False)
    nombre      = Column(String(150), nullable=False)
    telefono    = Column(String(20), nullable=False)
    parentesco  = Column(String(50))

    cliente = relationship("Cliente", back_populates="referencias")
