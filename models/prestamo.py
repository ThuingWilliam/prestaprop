import uuid
from decimal import Decimal
from datetime import datetime
from sqlalchemy import Column, String, Numeric, Integer, Date, DateTime, Enum, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base
from .enums import EstadoPrestamo, FrecuenciaPago, EstadoCuota

class Prestamo(Base):
    __tablename__ = "prestamos"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    numero_prestamo = Column(String(20), unique=True, nullable=False)

    # Claves foráneas
    cliente_id   = Column(UUID(as_uuid=True), ForeignKey("clientes.id"), nullable=False)
    producto_id  = Column(UUID(as_uuid=True), ForeignKey("productos_prestamo.id"), nullable=False)
    aprobado_por = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True)
    creado_por_usuario_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"), nullable=True)

    # Condiciones pactadas
    monto_capital        = Column(Numeric(14, 2), nullable=False)
    tasa_interes_anual   = Column(Numeric(7, 4), nullable=False)
    frecuencia           = Column(Enum(FrecuenciaPago), nullable=False)
    total_periodos       = Column(Integer, nullable=False)
    monto_cuota          = Column(Numeric(14, 2))

    # Totales calculados
    total_interes        = Column(Numeric(14, 2))
    total_a_pagar        = Column(Numeric(14, 2))

    # Saldos vigentes
    saldo_capital        = Column(Numeric(14, 2))
    saldo_interes        = Column(Numeric(14, 2))
    saldo_mora           = Column(Numeric(14, 2), default=0)

    # Fechas
    fecha_solicitud      = Column(Date, default=datetime.utcnow)
    fecha_aprobacion     = Column(Date)
    fecha_desembolso     = Column(Date)
    fecha_primer_pago    = Column(Date)
    fecha_vencimiento    = Column(Date)

    # Estado
    estado               = Column(Enum(EstadoPrestamo), default=EstadoPrestamo.PENDIENTE)

    # Método de cálculo: 'FRANCES' o 'FIJO'
    tipo_calculo         = Column(String(10), nullable=False, default='FRANCES')

    # Refinanciamiento
    prestamo_padre_id    = Column(UUID(as_uuid=True), ForeignKey("prestamos.id"), nullable=True)

    creado_en    = Column(DateTime, default=datetime.utcnow)
    actualizado_en = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones
    cliente              = relationship("Cliente", back_populates="prestamos")
    producto             = relationship("ProductoPrestamo", back_populates="prestamos")
    aprobado_por_usuario = relationship("Usuario", back_populates="prestamos_aprobados", foreign_keys=[aprobado_por])
    tabla_pagos  = relationship("CuotaProgramada", back_populates="prestamo", order_by="CuotaProgramada.fecha_vencimiento", cascade="all, delete-orphan")
    pagos        = relationship("Pago", back_populates="prestamo", cascade="all, delete-orphan")
    prestamo_padre = relationship("Prestamo", remote_side="Prestamo.id", foreign_keys=[prestamo_padre_id])

    @property
    def total_pagado(self):
        """Suma de todo lo recaudado a la fecha (Capital + Interés + Mora)"""
        return sum(p.monto_recibido for p in self.pagos)

    @property
    def monto_pendiente_total(self):
        """Saldo total pendiente de liquidar"""
        return (self.saldo_capital or 0) + (self.saldo_interes or 0) + (self.saldo_mora or 0)

    @property
    def proximo_monto_a_pagar(self):
        """
        Calcula el monto sugerido para el próximo pago:
        - Si hay cuotas vencidas o parciales: la suma de lo pendiente de esas cuotas + mora.
        - Si no: el monto de la siguiente cuota programada.
        """
        from .enums import EstadoCuota
        # Buscar cuotas que no estén pagadas
        cuotas_pendientes = [c for c in self.tabla_pagos if c.estado != EstadoCuota.PAGADA]
        if not cuotas_pendientes:
            return Decimal("0.00")
        
        # Si hay cuotas en mora o parciales, sumar lo que falta
        hoy = datetime.utcnow().date()
        atrasadas_o_parciales = [c for c in cuotas_pendientes if c.fecha_vencimiento <= hoy or c.estado == EstadoCuota.PARCIAL]
        
        if atrasadas_o_parciales:
            total = sum((c.total_cuota + c.monto_mora) - (c.capital_pagado + c.interes_pagado + c.mora_pagada) for c in atrasadas_o_parciales)
            return total
        
        # Si no hay nada atrasado, sugerir la siguiente cuota más cercana
        siguiente = cuotas_pendientes[0]
        return (siguiente.total_cuota + siguiente.monto_mora) - (siguiente.capital_pagado + siguiente.interes_pagado + siguiente.mora_pagada)

    @property
    def cuotas_atrasadas(self):
        """
        Retorna la lista de cuotas programadas que están vencidas y no completamente pagadas.
        """
        hoy = datetime.utcnow().date()
        from .enums import EstadoCuota
        return [
            cuota for cuota in self.tabla_pagos
            if cuota.fecha_vencimiento < hoy and cuota.estado != EstadoCuota.PAGADA
        ]

    @property
    def saldo_capital_dinamico(self):
        """Suma de capital pendiente. Si es Saldo Insoluto, usa la columna directa."""
        if self.tipo_calculo == 'INTERES_SOBRE_SALDO':
            return self.saldo_capital or Decimal("0")
        return sum(c.capital_cuota - c.capital_pagado for c in self.tabla_pagos)

    @property
    def saldo_interes_dinamico(self):
        """Suma de interés pendiente. Si es Saldo Insoluto, usa la columna directa."""
        if self.tipo_calculo == 'INTERES_SOBRE_SALDO':
            return self.saldo_interes or Decimal("0")
        return sum(c.interes_cuota - c.interes_pagado for c in self.tabla_pagos)

    @property
    def saldo_mora_dinamico(self):
        """Suma de mora pendiente. Si es Saldo Insoluto, usa la columna directa."""
        if self.tipo_calculo == 'INTERES_SOBRE_SALDO':
            return self.saldo_mora or Decimal("0")
        return sum(c.monto_mora - c.mora_pagada for c in self.tabla_pagos)

    @property
    def monto_pendiente_total_dinamico(self):
        """Suma de todo lo exigible actualmente."""
        return self.saldo_capital_dinamico + self.saldo_interes_dinamico + self.saldo_mora_dinamico

    def __repr__(self):
        return f"<Prestamo {self.numero_prestamo} | ${self.monto_capital} | {self.estado}>"

class CuotaProgramada(Base):
    __tablename__ = "cuotas_programadas"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prestamo_id   = Column(UUID(as_uuid=True), ForeignKey("prestamos.id"), nullable=False)

    numero_cuota  = Column(Integer, nullable=False)
    fecha_vencimiento = Column(Date, nullable=False)

    # Montos programados
    capital_cuota  = Column(Numeric(14, 2), nullable=False)
    interes_cuota  = Column(Numeric(14, 2), nullable=False)
    total_cuota    = Column(Numeric(14, 2), nullable=False)
    saldo_restante = Column(Numeric(14, 2), nullable=False)

    # Mora generada
    monto_mora     = Column(Numeric(14, 2), default=0)
    dias_mora      = Column(Integer, default=0)

    # Montos realmente pagados
    capital_pagado  = Column(Numeric(14, 2), default=0)
    interes_pagado  = Column(Numeric(14, 2), default=0)
    mora_pagada     = Column(Numeric(14, 2), default=0)
    total_pagado    = Column(Numeric(14, 2), default=0)

    estado       = Column(Enum(EstadoCuota), default=EstadoCuota.PENDIENTE)
    fecha_pago   = Column(Date)

    # Relaciones
    prestamo       = relationship("Prestamo", back_populates="tabla_pagos")
    aplicaciones   = relationship("AplicacionPago", back_populates="cuota", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("prestamo_id", "numero_cuota", name="uq_prestamo_cuota"),
        Index("ix_cuota_vencimiento", "fecha_vencimiento"),
        Index("ix_cuota_estado", "estado"),
    )
