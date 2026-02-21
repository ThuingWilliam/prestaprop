from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from functools import wraps
from models.enums import RolUsuario
from database import SessionLocal, registrar_auditoria
from models import Usuario

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
@admin_required
def listar_usuarios():
    db = SessionLocal()
    try:
        usuarios = db.query(Usuario).order_by(Usuario.nombre.asc()).all()
        return render_template('usuarios/usuarios.html', usuarios=usuarios)
    finally:
        db.close()

@auth_bp.route('/usuarios/nuevo', methods=['GET', 'POST'])
@login_required
@admin_required
def nuevo_usuario():
    if request.method == 'POST':
        db = SessionLocal()
        try:
            nuevo = Usuario(
                nombre=request.form.get('nombre'),
                email=request.form.get('email'),
                username=request.form.get('username'),
                rol=RolUsuario(request.form.get('rol'))
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
    return render_template('usuarios/usuarios.html', modo='nuevo')

@auth_bp.route('/usuarios/editar/<uuid:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_usuario(id):
    db = SessionLocal()
    try:
        usuario = db.query(Usuario).get(id)
        if not usuario:
            flash('Usuario no encontrado', 'danger')
            return redirect(url_for('auth.listar_usuarios'))
            
        if request.method == 'POST':
            usuario.nombre = request.form.get('nombre')
            usuario.email = request.form.get('email')
            usuario.username = request.form.get('username')
            usuario.rol = RolUsuario(request.form.get('rol'))
            
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
            
        return render_template('usuarios/usuarios.html', usuario=usuario, modo='editar')
    finally:
        db.close()
