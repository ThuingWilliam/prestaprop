from flask import Blueprint, render_template, session
from sqlalchemy import func
from database import SessionLocal
from models import Prestamo, Cliente, BitacoraAuditoria
from .auth import login_required, admin_required, admin_or_gerente_required
from models.enums import RolUsuario
from sqlalchemy import func, Date
from dateutil.relativedelta import relativedelta

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@login_required
def index():
    db = SessionLocal()
    try:
        from flask import session
        from datetime import date
        hoy = date.today()
        user_id = session.get('usuario_id')
        user_rol = str(session.get('rol', ''))

        # Filtro de seguridad (Isolation)
        filtro_prestamo = []
        filtro_cliente = []
        usuario_actual = None
        if user_rol != "ADMINISTRADOR":
            from models import Usuario
            usuario_actual = db.query(Usuario).filter(Usuario.id == user_id).first()
            if usuario_actual and usuario_actual.empresa_id:
                # Gerente, Oficial y Cobrador de empresa: ven su empresa
                filtro_prestamo.append(Prestamo.cliente.has(empresa_id=usuario_actual.empresa_id))
                filtro_cliente.append(Cliente.empresa_id == usuario_actual.empresa_id)
            else:
                # Sin empresa: solo sus propios registros
                filtro_prestamo.append(Prestamo.creado_por_usuario_id == user_id)
                filtro_cliente.append(Cliente.creado_por_usuario_id == user_id)

        # Métricas Globales (Filtradas si no es Admin)
        total_prestamos = db.query(func.count(Prestamo.id)).filter(*filtro_prestamo).scalar() or 0
        capital_activo = db.query(func.sum(Prestamo.saldo_capital)).filter(*filtro_prestamo).scalar() or 0
        monto_total_prestado = db.query(func.sum(Prestamo.monto_capital)).filter(*filtro_prestamo).scalar() or 0
        
        empresa_capital = 0
        if usuario_actual and usuario_actual.empresa:
            empresa_capital = usuario_actual.empresa.capital_inicial
        
        prestamos_mora_query = db.query(Prestamo).filter(Prestamo.estado == 'EN_MORA', *filtro_prestamo)
        prestamos_mora = prestamos_mora_query.all()
        prestamos_en_mora_count = len(prestamos_mora)
        riesgo_capital = sum(p.saldo_capital for p in prestamos_mora)
        total_clientes = db.query(func.count(Cliente.id)).filter(*filtro_cliente).scalar() or 0
        
        # Eficiencia de Cobro (Filtrada)
        from models import CuotaProgramada
        base_cuotas = db.query(CuotaProgramada).join(Prestamo).filter(*filtro_prestamo)
        
        total_periodos_vencidos = base_cuotas.filter(
            CuotaProgramada.fecha_vencimiento < hoy
        ).count() or 1
        cuotas_pagadas = base_cuotas.filter(
            CuotaProgramada.fecha_vencimiento < hoy,
            CuotaProgramada.estado == 'PAGADA'
        ).count() or 0
        eficiencia_cobro = (cuotas_pagadas / total_periodos_vencidos) * 100
        
        # Métricas Personalizadas (Solo para Operadores)
        mis_cobros_hoy = 0
        mis_clientes_mes = 0
        
        if user_rol != "ADMINISTRADOR":
            from models import Pago
            # Cobros realizados hoy por el usuario logueado
            mis_cobros_hoy = db.query(func.sum(Pago.monto_recibido)).filter(
                Pago.registrado_por == user_id,
                func.cast(Pago.fecha_pago, Date) == hoy
            ).scalar() or 0
            
            # Clientes registrados hoy por el usuario logueado (vía auditoría)
            inicio_mes = hoy.replace(day=1)
            mis_clientes_mes = db.query(func.count(BitacoraAuditoria.id)).filter(
                BitacoraAuditoria.cambiado_por == user_id,
                BitacoraAuditoria.tabla == 'clientes',
                BitacoraAuditoria.accion == 'INSERT',
                BitacoraAuditoria.cambiado_en >= inicio_mes
            ).scalar() or 0

        # --- DATOS PARA GRÁFICAS (DIFERENCIADO ADMIN) ---
        mensual_labels = []
        mensual_data = []
        
        # Nuevas Métricas Detalladas (Oficial)
        oficial_stats = None
        if user_rol not in ["ADMINISTRADOR", "GERENTE_EMPRESA"]:
            from services.prestamo_service import get_user_dashboard_stats
            oficial_stats = get_user_dashboard_stats(db, user_id, hoy)

        # 2. Salud de Cartera (Donut) - Para todos, pero filtrado
        estados_data = db.query(Prestamo.estado, func.count(Prestamo.id)).filter(*filtro_prestamo).group_by(Prestamo.estado).all()
        dict_estados = {e[0]: e[1] for e in estados_data}
        salud_labels = ["Vigente", "En Mora", "Completado"]
        salud_valores = [dict_estados.get('ACTIVO', 0), dict_estados.get('EN_MORA', 0), dict_estados.get('COMPLETADO', 0)]

        if user_rol in ["ADMINISTRADOR", "GERENTE_EMPRESA"]:
            # 1. Rendimiento Mensual (Últimos 6 meses)
            from sqlalchemy import extract
            for i in range(5, -1, -1):
                m_date = hoy.replace(day=1) - relativedelta(months=i)
                label = m_date.strftime('%b')
                
                query_mes = db.query(func.sum(Prestamo.monto_capital)).filter(
                    extract('month', Prestamo.creado_en) == m_date.month,
                    extract('year', Prestamo.creado_en) == m_date.year
                )
                if filtro_prestamo:
                    query_mes = query_mes.filter(*filtro_prestamo)
                
                total_mes = query_mes.scalar() or 0
                mensual_labels.append(label)
                mensual_data.append(float(total_mes))

            # 3. Clientes con múltiples préstamos
            subq = db.query(Prestamo.cliente_id)
            if filtro_prestamo: subq = subq.filter(*filtro_prestamo)
            subq = subq.group_by(Prestamo.cliente_id).having(func.count(Prestamo.id) > 1).subquery()
            
            clientes_multi = db.query(func.count(subq.c.cliente_id)).scalar() or 0
            monto_multi = db.query(func.sum(Prestamo.monto_capital)).filter(Prestamo.cliente_id.in_(subq)).scalar() or 0
        else:
            mensual_labels = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"]
            # Simulación o datos reales de cobros por día de la semana
            mensual_data = [0]*7
            mensual_data[hoy.weekday()] = float(mis_cobros_hoy)
            clientes_multi = 0
            monto_multi = 0

        ultimos_prestamos = db.query(Prestamo).filter(*filtro_prestamo).order_by(Prestamo.creado_en.desc()).limit(5).all()
        bitacora_query = db.query(BitacoraAuditoria)
        if user_rol != "ADMINISTRADOR":
            if user_rol == "GERENTE_EMPRESA":
                # Idealmente filtrar la bitacora por usuarios de su empresa, pero por simplicidad se le muestra lo suyo o omitimos restriccion.
                # Lo restringimos a sus acciones directas por ahora, o sin limite si no se pide.
                bitacora_query = bitacora_query.filter(BitacoraAuditoria.cambiado_por == user_id)
            else:
                bitacora_query = bitacora_query.filter(BitacoraAuditoria.cambiado_por == user_id)
        bitacora = bitacora_query.order_by(BitacoraAuditoria.cambiado_en.desc()).limit(5).all()
        
        return render_template('dashboard/index.html', 
                             total_prestamos=total_prestamos,
                             capital_activo=capital_activo,
                             riesgo_capital=riesgo_capital,
                             prestamos_en_mora=prestamos_en_mora_count,
                             eficiencia_cobro=oficial_stats['meta_semanal']['porcentaje'] if oficial_stats else eficiencia_cobro,
                             total_clientes=total_clientes,
                             monto_total_prestado=monto_total_prestado,
                             # Nuevos datos dinámicos
                             mensual_labels=mensual_labels,
                             mensual_data=mensual_data,
                             salud_labels=salud_labels,
                             salud_valores=salud_valores,
                             clientes_multi=clientes_multi,
                             monto_multi=monto_multi,
                             # ---
                             oficial_stats=oficial_stats,
                             ultimos_prestamos=ultimos_prestamos,
                             bitacora=bitacora,
                             mis_cobros_hoy=mis_cobros_hoy,
                             mis_clientes_mes=mis_clientes_mes,
                             empresa_capital=empresa_capital,
                             hoy=hoy)
    finally:
        db.close()

@main_bp.route('/auditoria')
@login_required
@admin_required
def auditoria():
    db = SessionLocal()
    try:
        # Solo admin
        logs = db.query(BitacoraAuditoria).order_by(BitacoraAuditoria.cambiado_en.desc()).limit(100).all()
        return render_template('reportes/auditoria.html', logs=logs)
    finally:
        db.close()

@main_bp.route('/reporte-maestro')
@login_required
def reporte_maestro():
    db = SessionLocal()
    try:
        from models import Pago, CuotaProgramada
        user_id = session.get('usuario_id')
        user_rol = str(session.get('rol', ''))
        
        q_prestamos = db.query(Prestamo)
        q_pagos = db.query(Pago).join(Prestamo)
        q_clientes = db.query(Cliente)
        
        if user_rol != "ADMINISTRADOR":
            if user_rol == "GERENTE_EMPRESA":
                from models import Usuario
                usuario_actual = db.query(Usuario).filter(Usuario.id == user_id).first()
                if usuario_actual and usuario_actual.empresa_id:
                    q_prestamos = q_prestamos.filter(Prestamo.cliente.has(empresa_id=usuario_actual.empresa_id))
                    # q_pagos depends on prestamo, we join it above
                    q_pagos = q_pagos.filter(Prestamo.cliente.has(empresa_id=usuario_actual.empresa_id))
                    q_clientes = q_clientes.filter(Cliente.empresa_id == usuario_actual.empresa_id)
            else:
                q_prestamos = q_prestamos.filter(Prestamo.creado_por_usuario_id == user_id)
                q_pagos = q_pagos.filter(Prestamo.creado_por_usuario_id == user_id)
                q_clientes = q_clientes.filter(Cliente.creado_por_usuario_id == user_id)

        prestamos = q_prestamos.order_by(Prestamo.creado_en.desc()).all()
        pagos = q_pagos.order_by(Pago.fecha_pago.desc()).limit(100).all()
        clientes = q_clientes.order_by(Cliente.apellido.asc()).all()
        return render_template('reportes/reporte_maestro.html', prestamos=prestamos, pagos=pagos, clientes=clientes)
    finally:
        db.close()

@main_bp.route('/vencidos')
@login_required
def vencidos():
    db = SessionLocal()
    try:
        from models import CuotaProgramada
        from datetime import date
        hoy = date.today()
        proximos_vencidos = db.query(CuotaProgramada).join(Prestamo).filter(
            CuotaProgramada.estado != 'PAGADA',
            CuotaProgramada.fecha_vencimiento < hoy
        )
        
        user_id = session.get('usuario_id')
        user_rol = str(session.get('rol', ''))
        if user_rol != "ADMINISTRADOR":
            proximos_vencidos = proximos_vencidos.filter(Prestamo.creado_por_usuario_id == user_id)
            
        proximos_vencidos = proximos_vencidos.order_by(CuotaProgramada.fecha_vencimiento.asc()).all()
        return render_template('prestamos/vencidos.html', cobros=proximos_vencidos, hoy=hoy)
    finally:
        db.close()

# --- NUEVOS REPORTES ANALÍTICOS ---

@main_bp.route('/reporte/eficiencia')
@login_required
def reporte_eficiencia():
    db = SessionLocal()
    try:
        from services.prestamo_service import get_collection_efficiency
        from datetime import date
        hoy = date.today()
        inicio_mes = hoy.replace(day=1)
        
        user_id = session.get('usuario_id')
        user_rol = str(session.get('rol', ''))
        uid_filter = user_id if user_rol != "ADMINISTRADOR" else None
        
        stats_mes = get_collection_efficiency(db, inicio_mes, hoy, uid_filter)
        stats_anual = get_collection_efficiency(db, hoy.replace(month=1, day=1), hoy, uid_filter)
        
        return render_template('reportes/eficiencia.html', stats_mes=stats_mes, stats_anual=stats_anual)
    finally:
        db.close()

@main_bp.route('/reporte/aging')
@login_required
def reporte_aging():
    db = SessionLocal()
    try:
        from services.prestamo_service import get_aging_portfolio
        user_id = session.get('usuario_id')
        user_rol = str(session.get('rol', ''))
        uid_filter = user_id if user_rol != "ADMINISTRADOR" else None
        
        report = get_aging_portfolio(db, uid_filter)
        return render_template('reportes/aging.html', report=report)
    finally:
        db.close()

@main_bp.route('/reporte/rentabilidad')
@login_required
@admin_or_gerente_required
def reporte_rentabilidad():
    db = SessionLocal()
    try:
        from services.prestamo_service import get_portfolio_profitability
        user_id = session.get('usuario_id')
        user_rol = str(session.get('rol', ''))
        uid_filter = user_id if user_rol != "ADMINISTRADOR" else None
        
        stats = get_portfolio_profitability(db, uid_filter)
        return render_template('reportes/rentabilidad.html', stats=stats)
    finally:
        db.close()
