import uuid
from datetime import datetime
from sqlalchemy import Column, String, Numeric, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base

class Empresa(Base):
    __tablename__ = "empresas"
    
    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre          = Column(String(150), nullable=False)
    capital_inicial = Column(Numeric(14, 2), default=0.00, nullable=False)
    creado_en       = Column(DateTime, default=datetime.utcnow)
    
    inyecciones     = relationship("InyeccionCapital", back_populates="empresa", order_by="InyeccionCapital.fecha.desc()")

    def __repr__(self):
        return f"<Empresa {self.nombre} | Capital: {self.capital_inicial}>"
