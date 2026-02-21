import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Index, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base

class BitacoraAuditoria(Base):
    __tablename__ = "bitacora_auditoria"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tabla        = Column(String(60), nullable=False)
    registro_id  = Column(String(60), nullable=False)
    accion       = Column(String(10), nullable=False)    # INSERT | UPDATE | DELETE
    valores_antes = Column(Text)                         # JSON del estado previo
    valores_despues = Column(Text)                       # JSON del estado nuevo
    descripcion  = Column(Text)                         # Resumen del cambio
    cambiado_por = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True)
    cambiado_en  = Column(DateTime, default=datetime.utcnow)

    # Relación para obtener el objeto usuario
    cambiado_por_usuario = relationship("Usuario")

    __table_args__ = (
        Index("ix_auditoria_tabla_registro", "tabla", "registro_id"),
        Index("ix_auditoria_fecha", "cambiado_en"),
    )

    def __repr__(self):
        return f"<Auditoria {self.accion} en {self.tabla} | {self.cambiado_en}>"
