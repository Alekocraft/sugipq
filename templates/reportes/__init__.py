from flask import Blueprint, render_template, session, redirect, url_for, flash
from models.solicitudes_model import SolicitudModel
from models.materiales_model import MaterialModel
from models.oficinas_model import OficinaModel

reportes_bp = Blueprint('reportes', __name__, template_folder='../templates/reportes')

@reportes_bp.route('/')
def index():
    if 'usuario_id' not in session:
        flash('Debe iniciar sesión para acceder a esta página', 'danger')
        return redirect(url_for('auth.login'))
    
    # Obtener estadísticas generales
    solicitudes = SolicitudModel.obtener_todas()
    materiales = MaterialModel.obtener_todos()
    
    total_solicitudes = len(solicitudes)
    solicitudes_pendientes = len([s for s in solicitudes if s['estado'] == 'pendiente'])
    solicitudes_aprobadas = len([s for s in solicitudes if s['estado'] == 'aprobada'])
    solicitudes_rechazadas = len([s for s in solicitudes if s['estado'] == 'rechazada'])
    
    materiales_bajo_stock = len([m for m in materiales if m['cantidad'] <= m['cantidad_minima']])
    
    return render_template('reportes/index.html',
                         total_solicitudes=total_solicitudes,
                         solicitudes_pendientes=solicitudes_pendientes,
                         solicitudes_aprobadas=solicitudes_aprobadas,
                         solicitudes_rechazadas=solicitudes_rechazadas,
                         materiales_bajo_stock=materiales_bajo_stock)

@reportes_bp.route('/solicitudes')
def solicitudes():
    if 'usuario_id' not in session:
        flash('Debe iniciar sesión para acceder a esta página', 'danger')
        return redirect(url_for('auth.login'))
    
    # Obtener TODAS las solicitudes para el reporte
    todas_solicitudes = SolicitudModel.obtener_todas()
    
    # Calcular estadísticas
    total_solicitudes = len(todas_solicitudes)
    solicitudes_pendientes = len([s for s in todas_solicitudes if s['estado'] == 'pendiente'])
    solicitudes_aprobadas = len([s for s in todas_solicitudes if s['estado'] == 'aprobada'])
    solicitudes_rechazadas = len([s for s in todas_solicitudes if s['estado'] == 'rechazada'])
    
    print(f"DEBUG: Total solicitudes encontradas: {total_solicitudes}")  # Para debugging
    
    return render_template('reportes/solicitudes.html',
                         solicitudes=todas_solicitudes,
                         total_solicitudes=total_solicitudes,
                         solicitudes_pendientes=solicitudes_pendientes,
                         solicitudes_aprobadas=solicitudes_aprobadas,
                         solicitudes_rechazadas=solicitudes_rechazadas)

@reportes_bp.route('/materiales')
def materiales():
    if 'usuario_id' not in session:
        flash('Debe iniciar sesión para acceder a esta página', 'danger')
        return redirect(url_for('auth.login'))
    
    materiales = MaterialModel.obtener_todos()
    return render_template('reportes/materiales.html', materiales=materiales)

@reportes_bp.route('/material/<int:id>')
def material_detalle(id):
    if 'usuario_id' not in session:
        flash('Debe iniciar sesión para acceder a esta página', 'danger')
        return redirect(url_for('auth.login'))
    
    material = MaterialModel.obtener_por_id(id)
    if not material:
        flash('Material no encontrado', 'danger')
        return redirect(url_for('reportes.materiales'))
    
    # Obtener todas las solicitudes para este material
    todas_solicitudes = SolicitudModel.obtener_todas()
    solicitudes_material = [s for s in todas_solicitudes if s['material_id'] == id]
    
    total_solicitudes = len(solicitudes_material)
    solicitudes_aprobadas = len([s for s in solicitudes_material if s['estado'] == 'aprobada'])
    
    return render_template('reportes/material_detalle.html',
                         material=material,
                         solicitudes=solicitudes_material,
                         total_solicitudes=total_solicitudes,
                         solicitudes_aprobadas=solicitudes_aprobadas)

@reportes_bp.route('/inventario')
def inventario():
    if 'usuario_id' not in session:
        flash('Debe iniciar sesión para acceder a esta página', 'danger')
        return redirect(url_for('auth.login'))
    
    materiales = MaterialModel.obtener_todos()
    
    # Calcular estadísticas de inventario
    total_materiales = len(materiales)
    materiales_bajo_stock = len([m for m in materiales if m['cantidad'] <= m['cantidad_minima']])
    materiales_stock_normal = len([m for m in materiales if m['cantidad'] > m['cantidad_minima']])
    
    return render_template('reportes/inventario.html',
                         materiales=materiales,
                         total_materiales=total_materiales,
                         materiales_bajo_stock=materiales_bajo_stock,
                         materiales_stock_normal=materiales_stock_normal)