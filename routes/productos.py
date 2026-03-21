from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import ProductoPrestamo, Usuario
from database import SessionLocal, registrar_auditoria
from routes.auth import admin_or_gerente_required
from decimal import Decimal

productos_bp = Blueprint('productos', __name__)

@productos_bp.route('/productos')
@admin_or_gerente_required
def lista():
    db = SessionLocal()
    productos = db.query(ProductoPrestamo).order_by(ProductoPrestamo.nombre).all()
    db.close()
    return render_template('productos/productos.html', productos=productos)

@productos_bp.route('/productos/nuevo', methods=['POST'])
@admin_or_gerente_required
def nuevo():
    db = SessionLocal()
    try:
        nombre = request.form.get('nombre')
        tasa = Decimal(request.form.get('tasa') or 0) / 100
        monto_min = Decimal(request.form.get('monto_minimo') or 0)
        monto_max = Decimal(request.form.get('monto_maximo') or 0)
        p_min = int(request.form.get('periodos_minimos') or 1)
        p_max = int(request.form.get('periodos_maximos') or 12)
        
        nuevo_p = ProductoPrestamo(
            nombre=nombre,
            descripcion=request.form.get('descripcion'),
            tasa_interes_anual=tasa,
            monto_minimo=monto_min,
            monto_maximo=monto_max,
            periodos_minimos=p_min,
            periodos_maximos=p_max,
            frecuencias_permitidas=request.form.get('frecuencias', 'SEMANAL,QUINCENAL,MENSUAL')
        )
        db.add(nuevo_p)
        db.commit()
        registrar_auditoria(db, session.get('usuario_id'), 'CREAR', 'productos_prestamo', str(nuevo_p.id), f"Creado producto {nombre}")
        flash(f'Producto {nombre} creado exitosamente', 'success')
    except Exception as e:
        db.rollback()
        flash(f'Error al crear producto: {str(e)}', 'error')
    finally:
        db.close()
    return redirect(url_for('productos.lista'))

@productos_bp.route('/productos/editar/<uuid:id>', methods=['POST'])
@admin_or_gerente_required
def editar(id):
    db = SessionLocal()
    try:
        p = db.query(ProductoPrestamo).get(id)
        if not p:
            flash('Producto no encontrado', 'error')
            return redirect(url_for('productos.lista'))
            
        p.nombre = request.form.get('nombre')
        p.descripcion = request.form.get('descripcion')
        p.tasa_interes_anual = Decimal(request.form.get('tasa') or 0) / 100
        p.monto_minimo = Decimal(request.form.get('monto_minimo') or 0)
        p.monto_maximo = Decimal(request.form.get('monto_maximo') or 0)
        p.periodos_minimos = int(request.form.get('periodos_minimos') or 1)
        p.periodos_maximos = int(request.form.get('periodos_maximos') or 12)
        p.activo = 'activo' in request.form
        
        db.commit()
        registrar_auditoria(db, session.get('usuario_id'), 'EDITAR', 'productos_prestamo', str(p.id), f"Editado producto {p.nombre}")
        flash(f'Producto {p.nombre} actualizado', 'success')
    except Exception as e:
        db.rollback()
        flash(f'Error al actualizar producto: {str(e)}', 'error')
    finally:
        db.close()
    return redirect(url_for('productos.lista'))
