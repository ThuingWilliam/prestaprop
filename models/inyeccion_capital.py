import uuid
from datetime import datetime
from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base

class InyeccionCapital(Base):
    __tablename__ = "inyecciones_capital"
    
    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    empresa_id      = Column(UUID(as_uuid=True), ForeignKey("empresas.id"), nullable=False)
    monto           = Column(Numeric(14, 2), nullable=False)
    descripcion     = Column(Text, nullable=True)
    fecha           = Column(DateTime, default=datetime.utcnow)
    registrado_por_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True)
    
    empresa         = relationship("Empresa", back_populates="inyecciones")
    registrado_por  = relationship("Usuario", foreign_keys=[registrado_por_id])

    def __repr__(self):
        return f"<InyeccionCapital empresa={self.empresa_id} monto={self.monto} fecha={self.fecha}>"
