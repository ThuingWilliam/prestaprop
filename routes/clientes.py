from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from database import SessionLocal, registrar_auditoria
from models import Cliente, Prestamo
from .auth import login_required
from decimal import Decimal

clientes_bp = Blueprint('clientes', __name__)

@clientes_bp.route('/clientes', methods=['GET', 'POST'])
@login_required
def lista_clientes():
    db = SessionLocal()
    try:
        if request.method == 'POST':
            # Registrar entrada para auditoría despues
            
            # Generar cédula temporal si no se proporciona
            numero_id = request.form.get('numero_id')
            if not numero_id or numero_id.strip() == '':
                import uuid
                numero_id = f"TEMP-{str(uuid.uuid4())[:8].upper()}"
            
            ingreso_str = request.form.get('ingreso_mensual') or '0'
            try:
                ingreso_val = Decimal(ingreso_str)
            except:
                ingreso_val = Decimal('0')

            nuevo_cliente = Cliente(
                primer_nombre=request.form.get('primer_nombre'),
                apellido=request.form.get('apellido'),
                numero_id=numero_id,
                telefono=request.form.get('telefono'),
                correo=request.form.get('correo'),
                ingreso_mensual=ingreso_val,
                direccion=request.form.get('direccion'),
                creado_por_usuario_id=session.get('usuario_id')
            )
            db.add(nuevo_cliente)
            db.flush()
            
            # Auditoría
            registrar_auditoria(
                db, "clientes", nuevo_cliente.id, "INSERT", 
                usuario_id=session.get('usuario_id'),
                despues={"nombre": nuevo_cliente.nombre_completo, "id": nuevo_cliente.numero_id}
            )
            
            db.commit()
            flash('Cliente registrado exitosamente', 'success')
            return redirect(url_for('clientes.lista_clientes'))
            
        user_id = session.get('usuario_id')
        user_rol = str(session.get('rol', ''))
        
        query = db.query(Cliente)
        if user_rol != "ADMINISTRADOR":
            query = query.filter(Cliente.creado_por_usuario_id == user_id)
            
        lista = query.order_by(Cliente.creado_en.desc()).all()
        return render_template('clientes/clientes.html', clientes=lista)
    finally:
        db.close()

@clientes_bp.route('/cliente/<uuid:id>')
@login_required
def ver_cliente(id):
    db = SessionLocal()
    try:
        user_id = session.get('usuario_id')
        user_rol = str(session.get('rol', ''))
        
        query = db.query(Cliente).filter(Cliente.id == id)
        if user_rol != "ADMINISTRADOR":
            query = query.filter(Cliente.creado_por_usuario_id == user_id)
            
        cliente = query.first()
        if not cliente:
            flash('Cliente no encontrado o sin permisos', 'error')
            return redirect(url_for('clientes.lista_clientes'))
        prestamos = db.query(Prestamo).filter(Prestamo.cliente_id == id).all()
        return render_template('clientes/ver_cliente.html', cliente=cliente, prestamos=prestamos)
    finally:
        db.close()

@clientes_bp.route('/cliente/editar/<uuid:id>', methods=['GET', 'POST'])
@login_required
def editar_cliente(id):
    db = SessionLocal()
    try:
        user_id = session.get('usuario_id')
        user_rol = str(session.get('rol', ''))
        
        query = db.query(Cliente).filter(Cliente.id == id)
        if user_rol != "ADMINISTRADOR":
            query = query.filter(Cliente.creado_por_usuario_id == user_id)
            
        cliente = query.first()
        if not cliente:
            flash('Cliente no encontrado o sin permisos', 'error')
            return redirect(url_for('clientes.lista_clientes'))
            
        if request.method == 'POST':
            # Auditoría - Capturar estado previo
            antes = {
                "primer_nombre": cliente.primer_nombre,
                "apellido": cliente.apellido,
                "telefono": cliente.telefono,
                "correo": cliente.correo,
                "direccion": cliente.direccion,
                "ingreso_mensual": str(cliente.ingreso_mensual)
            }
            
            # Actualizar campos
            cliente.primer_nombre = request.form.get('primer_nombre')
            cliente.apellido = request.form.get('apellido')
            cliente.telefono = request.form.get('telefono')
            cliente.correo = request.form.get('correo')
            cliente.direccion = request.form.get('direccion')
            
            ingreso_str = request.form.get('ingreso_mensual') or '0'
            try:
                cliente.ingreso_mensual = Decimal(ingreso_str)
            except:
                pass

            db.flush()
            
            # Auditoría
            registrar_auditoria(
                db, "clientes", cliente.id, "UPDATE",
                usuario_id=session.get('usuario_id'),
                antes=antes,
                despues={
                    "nombre": cliente.nombre_completo,
                    "id": cliente.numero_id
                }
            )
            
            db.commit()
            flash('Perfil actualizado correctamente', 'success')
            return redirect(url_for('clientes.ver_cliente', id=id))
            
        return render_template('clientes/ver_cliente.html', cliente=cliente, edit_mode=True) # Reusing template with a modal or flag
    finally:
        db.close()
