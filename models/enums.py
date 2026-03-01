import enum

class RolUsuario(str, enum.Enum):
    ADMINISTRADOR   = "ADMINISTRADOR"
    GERENTE_EMPRESA = "GERENTE_EMPRESA"
    OFICIAL         = "OFICIAL"
    COBRADOR        = "COBRADOR"

class EstadoPrestamo(str, enum.Enum):
    PENDIENTE   = "PENDIENTE"
    APROBADO    = "APROBADO"
    ACTIVO      = "ACTIVO"
    COMPLETADO  = "COMPLETADO"
    EN_MORA     = "EN_MORA"
    CANCELADO   = "CANCELADO"

class FrecuenciaPago(str, enum.Enum):
    SEMANAL    = "SEMANAL"
    QUINCENAL  = "QUINCENAL"
    MENSUAL    = "MENSUAL"

class EstadoCuota(str, enum.Enum):
    PENDIENTE = "PENDIENTE"
    PAGADA    = "PAGADA"
    PARCIAL   = "PARCIAL"
    VENCIDA   = "VENCIDA"

class MetodoPago(str, enum.Enum):
    EFECTIVO       = "EFECTIVO"
    TRANSFERENCIA  = "TRANSFERENCIA"
    CHEQUE         = "CHEQUE"

class EstadoCliente(str, enum.Enum):
    ACTIVO      = "ACTIVO"
    INACTIVO    = "INACTIVO"
    BLOQUEADO   = "BLOQUEADO"
