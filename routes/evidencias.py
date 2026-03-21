import os
import uuid
from datetime import datetime
from flask import Blueprint, request, redirect, url_for, flash, session, current_app
from werkzeug.utils import secure_filename
from database import SessionLocal, registrar_auditoria
from models import Evidencia, Usuario
from .auth import login_required

evidencias_bp = Blueprint('evidencias', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
MAX_FILE_SIZE = 5 * 1024 * 1024 # 5MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@evidencias_bp.route('/evidencia/subir', methods=['POST'])
@login_required
def subir():
    db = SessionLocal()
    try:
        # Validar si hay archivo
        if 'archivo' not in request.files:
            flash('No se seleccionó ningún archivo', 'error')
            return redirect(request.referrer)
        
        file = request.files['archivo']
        if file.filename == '':
            flash('Nombre de archivo vacío', 'error')
            return redirect(request.referrer)
        
        if file and allowed_file(file.filename):
            # Validar tamaño (aproximado desde el stream si es posible, o después de guardar)
            # Flask usualmente lo valida en la config MAX_CONTENT_LENGTH, pero lo haremos manual por si acaso
            file.seek(0, os.SEEK_END)
            size = file.tell()
            file.seek(0)
            
            if size > MAX_FILE_SIZE:
                flash('El archivo es demasiado grande (máximo 5MB)', 'error')
                return redirect(request.referrer)

            # Obtener datos del formulario
            titulo = request.form.get('titulo') or 'Documento'
            tipo = request.form.get('tipo', 'OTRO')
            cliente_id = request.form.get('cliente_id')
            prestamo_id = request.form.get('prestamo_id')
            pago_id = request.form.get('pago_id')

            # Generar nombre único
            original_filename = secure_filename(file.filename)
            extension = original_filename.rsplit('.', 1)[1].lower()
            unique_filename = f"{uuid.uuid4()}.{extension}"
            
            # Directorio de subida
            upload_folder = os.path.join(current_app.static_folder, 'uploads', 'evidencias')
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder, exist_ok=True)
            
            file_path = os.path.join(upload_folder, unique_filename)
            file.save(file_path)

            # Registrar en DB
            nueva_evidencia = Evidencia(
                titulo=titulo,
                tipo=tipo,
                cliente_id=cliente_id if cliente_id else None,
                prestamo_id=prestamo_id if prestamo_id else None,
                pago_id=pago_id if pago_id else None,
                ruta_archivo=f"uploads/evidencias/{unique_filename}",
                nombre_original=original_filename,
                extension=extension,
                subido_por_usuario_id=session.get('usuario_id')
            )
            db.add(nueva_evidencia)
            db.commit()

            flash('Documento subido exitosamente', 'success')
        else:
            flash('Tipo de archivo no permitido (Solo JPG, PNG, PDF)', 'error')
            
        return redirect(request.referrer)
    except Exception as e:
        db.rollback()
        flash(f'Error al subir archivo: {str(e)}', 'error')
        return redirect(request.referrer)
    finally:
        db.close()
