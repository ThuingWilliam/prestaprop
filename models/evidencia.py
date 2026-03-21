import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base

class Evidencia(Base):
    __tablename__ = "evidencias"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    titulo         = Column(String(150), nullable=False) # Nombre descriptivo dado por el usuario
    
    # Relaciones (Al menos una debe estar poblada dependiendo del contexto)
    cliente_id     = Column(UUID(as_uuid=True), ForeignKey("clientes.id"), nullable=True)
    prestamo_id    = Column(UUID(as_uuid=True), ForeignKey("prestamos.id"), nullable=True)
    pago_id        = Column(UUID(as_uuid=True), ForeignKey("pagos.id"), nullable=True)
    
    # Datos del archivo
    tipo           = Column(String(50)) # 'CLIENTE', 'DESEMBOLSO', 'PAGO', 'OTRO'
    ruta_archivo   = Column(String(255), nullable=False)
    nombre_original = Column(String(255))
    extension      = Column(String(10))
    
    fecha_subida   = Column(DateTime, default=datetime.utcnow)
    subido_por_usuario_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True)

    # Relaciones ORM
    cliente = relationship("Cliente", backref="evidencias")
    prestamo = relationship("Prestamo", backref="evidencias")
    pago = relationship("Pago", backref="evidencias")
    subido_por = relationship("Usuario")

    def __repr__(self):
        return f"<Evidencia {self.titulo} | {self.tipo}>"
