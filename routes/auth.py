from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from functools import wraps
from models.enums import RolUsuario
from database import SessionLocal, registrar_auditoria
from models import Usuario, Empresa, InyeccionCapital
from decimal import Decimal

auth_bp = Blueprint('auth', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            flash('Por favor inicie sesión', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('rol') != RolUsuario.ADMINISTRADOR.value:
            flash('Acceso denegado: Se requieren permisos de Administrador', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

def admin_or_gerente_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('rol') not in [RolUsuario.ADMINISTRADOR.value, RolUsuario.GERENTE_EMPRESA.value]:
            flash('Acceso denegado: Se requieren permisos de Administrador o Gerente', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        db = SessionLocal()
        usuario = db.query(Usuario).filter(Usuario.username == username).first()
        if usuario and usuario.check_password(password):
            session['usuario_id'] = str(usuario.id)
            session['usuario_nombre'] = usuario.nombre
            session['rol'] = usuario.rol.value
            if usuario.empresa:
                session['empresa_nombre'] = usuario.empresa.nombre
            flash(f'Bienvenido {usuario.nombre}', 'success')
            return redirect(url_for('main.index'))
        flash('Credenciales inválidas', 'danger')
    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))

# Gestión de Usuarios (Admin)
@auth_bp.route('/usuarios')
@login_required
@admin_or_gerente_required
def listar_usuarios():
    db = SessionLocal()
    try:
        user_rol = session.get('rol')
        user_id = session.get('usuario_id')
        query = db.query(Usuario)
        
        if user_rol == RolUsuario.GERENTE_EMPRESA.value:
            usuario_actual = query.filter(Usuario.id == user_id).first()
            query = query.filter(Usuario.rol != RolUsuario.ADMINISTRADOR)
            if usuario_actual and usuario_actual.empresa_id:
                query = query.filter(Usuario.empresa_id == usuario_actual.empresa_id)
            else:
                query = query.filter(Usuario.id == user_id)
                
        usuarios = query.order_by(Usuario.nombre.asc()).all()
        return render_template('usuarios/usuarios.html', usuarios=usuarios)
    finally:
        db.close()

@auth_bp.route('/usuarios/nuevo', methods=['GET', 'POST'])
@login_required
@admin_or_gerente_required
def nuevo_usuario():
    if request.method == 'POST':
        db = SessionLocal()
        try:
            usuario_actual = db.query(Usuario).get(session.get('usuario_id'))
            if session.get('rol') == RolUsuario.ADMINISTRADOR.value:
                emp_id = request.form.get('empresa_id')
                empresa_id_asignada = emp_id if emp_id else None
            else:
                empresa_id_asignada = usuario_actual.empresa_id
            
            rol_solicitado = RolUsuario(request.form.get('rol'))
            
            # Validación de seguridad: el gerente solo puede crear Oficiales o Cobradores
            if session.get('rol') == RolUsuario.GERENTE_EMPRESA.value:
                if rol_solicitado not in [RolUsuario.OFICIAL_COBRO, RolUsuario.COBRADOR_AUTORIZADO]:
                    flash('No tienes permiso para asignar este rol.', 'danger')
                    return redirect(url_for('auth.listar_usuarios'))

            nuevo = Usuario(
                nombre=request.form.get('nombre'),
                email=request.form.get('email'),
                username=request.form.get('username'),
                rol=rol_solicitado,
                empresa_id=empresa_id_asignada
            )
            nuevo.set_password(request.form.get('password'))
            db.add(nuevo)
            
            # Auditoría
            registrar_auditoria(
                db, tabla='usuarios', registro_id=nuevo.id, accion='INSERT',
                usuario_id=session.get('usuario_id'),
                descripcion=f"Creado usuario: {nuevo.username} ({nuevo.rol.value})"
            )
            db.commit()
            flash('Usuario creado exitosamente', 'success')
            return redirect(url_for('auth.listar_usuarios'))
        except Exception as e:
            db.rollback()
            flash(f'Error al crear usuario: {str(e)}', 'danger')
        finally:
            db.close()
            
    db = SessionLocal()
    empresas = []
    if session.get('rol') == RolUsuario.ADMINISTRADOR.value:
        empresas = db.query(Empresa).all()
    db.close()
    return render_template('usuarios/usuarios.html', modo='nuevo', empresas=empresas)

@auth_bp.route('/usuarios/editar/<uuid:id>', methods=['GET', 'POST'])
@login_required
@admin_or_gerente_required
def editar_usuario(id):
    db = SessionLocal()
    try:
        usuario = db.query(Usuario).get(id)
        if not usuario:
            flash('Usuario no encontrado', 'danger')
            return redirect(url_for('auth.listar_usuarios'))
            
        if request.method == 'POST':
            # Validación de seguridad para evitar saltos de privilegio
            rol_solicitado = RolUsuario(request.form.get('rol'))
            if session.get('rol') == RolUsuario.GERENTE_EMPRESA.value:
                # El gerente no puede ascender a un super admin a menos que él mismo lo sea (lo cual es imposible)
                # Tampoco puede ascenderse a o crear otro gerente, ni degradar a su propio jefe.
                # Nota: si trata de editar un admin o un gerente, lo ideal es bloquear.
                if rol_solicitado not in [RolUsuario.OFICIAL_COBRO, RolUsuario.COBRADOR_AUTORIZADO]:
                    flash('No tienes permiso para conceder este rol.', 'danger')
                    return redirect(url_for('auth.listar_usuarios'))
                if usuario.rol in [RolUsuario.ADMINISTRADOR, RolUsuario.GERENTE_EMPRESA] and usuario.id != session.get('usuario_id'):
                    flash('No puedes editar roles de gerentes o administradores.', 'danger')
                    return redirect(url_for('auth.listar_usuarios'))
                    
            usuario.nombre = request.form.get('nombre')
            usuario.email = request.form.get('email')
            usuario.username = request.form.get('username')
            usuario.rol = rol_solicitado
            
            if session.get('rol') == RolUsuario.ADMINISTRADOR.value:
                emp_id = request.form.get('empresa_id')
                usuario.empresa_id = emp_id if emp_id else None
            
            password = request.form.get('password')
            if password:
                usuario.set_password(password)
                
            # Auditoría
            registrar_auditoria(
                db, tabla='usuarios', registro_id=usuario.id, accion='UPDATE',
                usuario_id=session.get('usuario_id'),
                descripcion=f"Editado usuario: {usuario.username}"
            )
            db.commit()
            flash('Usuario actualizado correctamente', 'success')
            return redirect(url_for('auth.listar_usuarios'))
            
        empresas = []
        if session.get('rol') == RolUsuario.ADMINISTRADOR.value:
            empresas = db.query(Empresa).all()
            
        return render_template('usuarios/usuarios.html', usuario=usuario, modo='editar', empresas=empresas)
    finally:
        db.close()

@auth_bp.route('/mi-empresa', methods=['GET', 'POST'])
@login_required
@admin_or_gerente_required
def mi_empresa():
    db = SessionLocal()
    try:
        usuario = db.query(Usuario).get(session.get('usuario_id'))
        
        if request.method == 'POST':
            accion = request.form.get('accion')
            
            if accion == 'actualizar_nombre':
                # Solo actualiza el nombre de la empresa
                nombre = request.form.get('nombre')
                if usuario.empresa:
                    usuario.empresa.nombre = nombre
                    # Si cambia el nombre, actualizamos la sesión
                    session['empresa_nombre'] = nombre
                else:
                    nueva_empresa = Empresa(nombre=nombre, capital_inicial=Decimal('0'))
                    db.add(nueva_empresa)
                    db.flush()
                    usuario.empresa_id = nueva_empresa.id
                    session['empresa_nombre'] = nombre
                db.commit()
                flash('Nombre de la empresa actualizado.', 'success')
                
            elif accion == 'inyectar_capital':
                # Registra una nueva inyección de capital
                try:
                    monto = Decimal(request.form.get('monto') or '0')
                except:
                    monto = Decimal('0')
                descripcion = request.form.get('descripcion', '')
                
                if monto <= 0:
                    flash('El monto de inyección debe ser mayor a cero.', 'danger')
                else:
                    if not usuario.empresa:
                        flash('Primero debes configurar el nombre de la empresa.', 'warning')
                    else:
                        inyeccion = InyeccionCapital(
                            empresa_id=usuario.empresa.id,
                            monto=monto,
                            descripcion=descripcion,
                            registrado_por_id=usuario.id
                        )
                        db.add(inyeccion)
                        # Sumar al capital acumulado
                        usuario.empresa.capital_inicial += monto
                        db.commit()
                        flash(f'Inyección de ${monto:,.2f} registrada exitosamente.', 'success')
            
            return redirect(url_for('auth.mi_empresa'))
            
        # Historial de inyecciones
        inyecciones = db.query(InyeccionCapital).filter(
            InyeccionCapital.empresa_id == usuario.empresa_id
        ).order_by(InyeccionCapital.fecha.desc()).all() if usuario and usuario.empresa_id else []
        
        return render_template('auth/mi_empresa.html', empresa=usuario.empresa, inyecciones=inyecciones)
    finally:
        db.close()
