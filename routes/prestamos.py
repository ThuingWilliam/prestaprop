from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import Prestamo, Cliente, ProductoPrestamo, CuotaProgramada, Pago, MetodoPago, Usuario, FrecuenciaPago
from services.prestamo_service import generar_tabla_amortizacion, aplicar_pago_logica
from database import SessionLocal, registrar_auditoria
from .auth import login_required, admin_required
from decimal import Decimal
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from sqlalchemy import func, Date

prestamos_bp = Blueprint('prestamos', __name__)

@prestamos_bp.route('/nuevo-prestamo', methods=['GET', 'POST'])
@login_required
def nuevo():
    db = SessionLocal()
    try:
        user_id = session.get('usuario_id')
        user_rol = str(session.get('rol', ''))
        
        q_clientes = db.query(Cliente)
        if user_rol != "ADMINISTRADOR":
            q_clientes = q_clientes.filter(Cliente.creado_por_usuario_id == user_id)
            
        clientes = q_clientes.all()
        productos = db.query(ProductoPrestamo).filter(ProductoPrestamo.activo == True).all()
        
        if request.method == 'POST':
            cliente_id = request.form.get('cliente_id')
            producto_id = request.form.get('producto_id')
            monto = Decimal(request.form.get('monto') or 0)
            tasa = Decimal(request.form.get('tasa') or 0) / 100
            tipo_tasa = request.form.get('tipo_tasa') # PERIODICA o ANUAL
            metodo = request.form.get('metodo_calculo') # FIJO o FRANCES
            frecuencia_str = request.form.get('frecuencia')
            plazo = int(request.form.get('plazo') or 12)
            
            frecuencia = FrecuenciaPago[frecuencia_str]
            es_anual = (tipo_tasa == 'ANUAL')
            fecha_inicio = date.today()
            
            from services.prestamo_service import generar_tabla_fija
            if metodo == 'FIJO':
                tabla_datos = generar_tabla_fija(monto, tasa, frecuencia, plazo, fecha_inicio, es_anual=es_anual)
            else:
                tabla_datos = generar_tabla_amortizacion(monto, tasa, frecuencia, plazo, fecha_inicio, es_anual=es_anual)
            total_interes = sum(c["interes_cuota"] for c in tabla_datos)
            
            num_prestamo = f"PRE-{datetime.utcnow().year}-{db.query(Prestamo).count() + 1:04d}"
            
            prestamo = Prestamo(
                numero_prestamo=num_prestamo,
                cliente_id=cliente_id,
                producto_id=producto_id,
                aprobado_por=session.get('usuario_id'),
                creado_por_usuario_id=session.get('usuario_id'),
                monto_capital=monto,
                tasa_interes_anual=tasa if es_anual else (tasa * 24), # Estimación para compatibilidad si no es anual
                frecuencia=frecuencia,
                total_periodos=plazo,
                monto_cuota=tabla_datos[0]["total_cuota"],
                total_interes=total_interes,
                total_a_pagar=monto + total_interes,
                saldo_capital=monto,
                saldo_interes=total_interes,
                fecha_desembolso=fecha_inicio,
                fecha_primer_pago=fecha_inicio,
                estado='ACTIVO'
            )
            db.add(prestamo)
            db.flush()
            
            for d in tabla_datos:
                cuota = CuotaProgramada(prestamo_id=prestamo.id, **d)
                db.add(cuota)
                
            db.commit()
            
            # Auditoría
            registrar_auditoria(
                db, "prestamos", prestamo.id, "INSERT",
                usuario_id=session.get('usuario_id'),
                despues={"numero": prestamo.numero_prestamo, "monto": str(prestamo.monto_capital)}
            )
            db.commit() # Commit final para el log

            flash(f'Préstamo {num_prestamo} creado exitosamente', 'success')
            return redirect(url_for('main.index'))
            
        selected_cliente_id = request.args.get('cliente_id')
        return render_template('prestamos/nuevo_prestamo.html', clientes=clientes, productos=productos, selected_cliente_id=selected_cliente_id)
    finally:
        db.close()

@prestamos_bp.route('/prestamo/<uuid:id>')
@login_required
def ver(id):
    db = SessionLocal()
    try:
        user_id = session.get('usuario_id')
        user_rol = str(session.get('rol', ''))
        
        query = db.query(Prestamo).filter(Prestamo.id == id)
        if user_rol != "ADMINISTRADOR":
            query = query.filter(Prestamo.creado_por_usuario_id == user_id)
            
        prestamo = query.first()
        if not prestamo:
            flash('Préstamo no encontrado o sin permisos', 'error')
            return redirect(url_for('main.index'))
        return render_template('prestamos/ver_prestamo.html', prestamo=prestamo)
    finally:
        db.close()

@prestamos_bp.route('/pago/registrar', methods=['POST'])
@login_required
def registrar_pago():
    db = SessionLocal()
    try:
        prestamo_id = request.form.get('prestamo_id')
        monto = Decimal(request.form.get('monto') or 0)
        metodo = request.form.get('metodo_pago')
        referencia = request.form.get('referencia')
        
        prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()
        if not prestamo:
            flash('Préstamo no encontrado', 'error')
            return redirect(url_for('main.index'))
            
        resumen = aplicar_pago_logica(
            db=db,
            prestamo=prestamo,
            monto_recibido=monto,
            fecha_pago=date.today(),
            metodo=MetodoPago[metodo],
            registrado_por_id=session.get('usuario_id'),
            referencia=referencia
        )
        
        db.commit()
        
        # Auditoría
        registrar_auditoria(
            db, "pagos", prestamo.id, "INSERT",
            usuario_id=session.get('usuario_id'),
            despues={"monto": str(monto), "prestamo": prestamo.numero_prestamo}
        )
        db.commit()

        flash(f'Pago procesado. Aplicado a Capital: ${resumen["aplicado_capital"]}', 'success')
        return redirect(url_for('prestamos.ver', id=prestamo.id))
    except Exception as e:
        db.rollback()
        flash(f'Error al procesar pago: {e}', 'error')
        return redirect(url_for('main.index'))
    finally:
        db.close()

@prestamos_bp.route('/caja')
@login_required
@admin_required
def caja():
    db = SessionLocal()
    try:
        hoy = date.today()
        pagos_hoy = db.query(Pago).filter(func.cast(Pago.fecha_pago, Date) == hoy).all()
        historial = db.query(Pago).order_by(Pago.fecha_pago.desc()).limit(50).all()
        return render_template('caja/caja.html', pagos=pagos_hoy, total_hoy=sum(p.monto_recibido for p in pagos_hoy), historial=historial)
    finally:
        db.close()

@prestamos_bp.route('/agenda')
@login_required
def agenda():
    db = SessionLocal()
    try:
        user_id = session.get('usuario_id')
        user_rol = str(session.get('rol', ''))
        
        hoy = date.today()
        fecha_limite = hoy + relativedelta(months=2)
        
        query = db.query(CuotaProgramada).join(Prestamo).filter(
            CuotaProgramada.estado != 'PAGADA',
            CuotaProgramada.fecha_vencimiento <= fecha_limite
        )
        
        if user_rol != "ADMINISTRADOR":
            query = query.filter(Prestamo.creado_por_usuario_id == user_id)
            
        proximos = query.order_by(CuotaProgramada.fecha_vencimiento.asc()).all()
        return render_template('prestamos/agenda.html', cobros=proximos)
    finally:
        db.close()

@prestamos_bp.route('/prestamo/ajustar-tasa', methods=['POST'])
@login_required
@admin_required
def ajustar_tasa():
    db = SessionLocal()
    try:
        prestamo_id = request.form.get('prestamo_id')
        nueva_tasa = Decimal(request.form.get('nueva_tasa') or 0)
        modo = request.form.get('modo_ajuste', 'FUTURE_ONLY')
        
        prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()
        if not prestamo:
            flash('Préstamo no encontrado', 'error')
            return redirect(url_for('main.index'))
            
        from services.prestamo_service import reajustar_tasa_prestamo
        exito = reajustar_tasa_prestamo(db, prestamo, nueva_tasa, modo=modo)
        
        if exito:
            # Auditoría
            registrar_auditoria(
                db, "prestamos", prestamo.id, "UPDATE",
                usuario_id=session.get('usuario_id'),
                descripcion=f"Ajuste de tasa a {nueva_tasa}% (Modo: {modo})"
            )
            db.commit()
            flash(f'Tasa de interés ajustada exitosamente a {nueva_tasa}%', 'success')
        else:
            flash('No se pudo ajustar la tasa', 'error')
            
        return redirect(url_for('prestamos.ver', id=prestamo.id))
    except Exception as e:
        db.rollback()
        flash(f'Error al ajustar tasa: {e}', 'error')
        return redirect(url_for('main.index'))
    finally:
        db.close()

@prestamos_bp.route('/pago/descargar-recibo/<uuid:pago_id>')
@login_required
def descargar_recibo(pago_id):
    db = SessionLocal()
    try:
        from models import Pago
        from services.prestamo_service import generar_recibo_pdf_bytes
        from flask import Response
        
        pago = db.query(Pago).filter(Pago.id == pago_id).first()
        if not pago:
            flash('Cobro no encontrado', 'error')
            return redirect(url_for('main.index'))
            
        # Seguridad: Solo admin o el oficial que creó el préstamo/cliente
        user_id = session.get('usuario_id')
        user_rol = str(session.get('rol', ''))
        if user_rol != "ADMINISTRADOR" and str(pago.prestamo.creado_por_usuario_id) != user_id:
            flash('Acceso denegado al recibo', 'danger')
            return redirect(url_for('main.index'))
            
        pdf_bytes = generar_recibo_pdf_bytes(pago)
        
        import io
        from flask import send_file
        
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"Recibo_{pago.prestamo.numero_prestamo}_{pago.fecha_pago.strftime('%Y%m%d')}.pdf"
        )
    finally:
        db.close()

@prestamos_bp.route('/prestamo/descargar-resumen/<uuid:id>')
@login_required
def descargar_resumen(id):
    db = SessionLocal()
    try:
        from services.prestamo_service import generar_resumen_pdf_bytes
        from flask import send_file
        import io
        
        user_id = session.get('usuario_id')
        user_rol = str(session.get('rol', ''))
        
        query = db.query(Prestamo).filter(Prestamo.id == id)
        if user_rol != "ADMINISTRADOR":
            query = query.filter(Prestamo.creado_por_usuario_id == user_id)
            
        prestamo = query.first()
        if not prestamo:
            flash('Préstamo no encontrado o sin permisos', 'error')
            return redirect(url_for('main.index'))
            
        pdf_bytes = generar_resumen_pdf_bytes(prestamo)
        
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"Reporte_Ejecutivo_{prestamo.numero_prestamo}.pdf"
        )
    finally:
        db.close()
