import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base
from .empresa import Empresa
from .enums import RolUsuario
from werkzeug.security import generate_password_hash, check_password_hash

class Usuario(Base):
    __tablename__ = "usuarios"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre         = Column(String(100), nullable=False)
    nombre_completo = Column(String(150), nullable=True) # Opcional
    username       = Column(String(50), unique=True, nullable=False)
    email          = Column(String(150), unique=True, nullable=False)
    contrasena_hash = Column(String(255), nullable=False)
    rol            = Column(Enum(RolUsuario), nullable=False, default=RolUsuario.OFICIAL_COBRO)
    activo         = Column(Boolean, default=True)
    creado_en      = Column(DateTime, default=datetime.utcnow)
    empresa_id     = Column(UUID(as_uuid=True), ForeignKey("empresas.id"), nullable=True)

    # Relaciones
    empresa = relationship("Empresa", backref="usuarios")
    prestamos_aprobados = relationship("Prestamo", back_populates="aprobado_por_usuario", foreign_keys="[Prestamo.aprobado_por]")
    pagos_registrados = relationship("Pago", back_populates="registrado_por_usuario")

    def set_password(self, password):
        self.contrasena_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.contrasena_hash, password)

    def __repr__(self):
        return f"<Usuario {self.username} [{self.rol}]>"
