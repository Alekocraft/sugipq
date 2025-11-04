from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models.solicitudes_model import SolicitudModel
from models.materiales_model import MaterialModel
from models.oficinas_model import OficinaModel
from models.usuarios_model import UsuarioModel

solicitudes_bp = Blueprint('solicitudes', __name__, template_folder='../templates/solicitudes')

@solicitudes_bp.route('/')
def listar():
    if 'usuario_id' not in session:
        flash('Debe iniciar sesión para acceder a esta página', 'danger')
        return redirect(url_for('auth.login'))
    
    solicitudes = SolicitudModel.obtener_todas()
    return render_template('solicitudes/listar.html', solicitudes=solicitudes)

@solicitudes_bp.route('/crear', methods=['GET', 'POST'])
def crear():
    if 'usuario_id' not in session:
        flash('Debe iniciar sesión para acceder a esta página', 'danger')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        material_id = int(request.form['material_id'])
        cantidad_solicitada = int(request.form['cantidad_solicitada'])
        justificacion = request.form['justificacion']
        usuario_id = session['usuario_id']
        
        # Obtener la oficina del usuario
        usuario = UsuarioModel.obtener_por_id(usuario_id)
        if not usuario:
            flash('Usuario no encontrado', 'danger')
            return redirect(url_for('solicitudes.crear'))
        
        oficina_id = usuario['oficina_id']
        
        solicitud_id = SolicitudModel.crear(material_id, usuario_id, oficina_id, cantidad_solicitada, justificacion)
        if solicitud_id:
            flash('Solicitud creada exitosamente', 'success')
            return redirect(url_for('solicitudes.listar'))
        else:
            flash('Error al crear la solicitud', 'danger')
    
    materiales = MaterialModel.obtener_todos()
    return render_template('solicitudes/crear.html', materiales=materiales)

@solicitudes_bp.route('/aprobar')
def aprobar():
    if 'usuario_id' not in session:
        flash('Debe iniciar sesión para acceder a esta página', 'danger')
        return redirect(url_for('auth.login'))
    
    usuario_id = session['usuario_id']
    solicitudes = SolicitudModel.obtener_para_aprobador(usuario_id)
    
    return render_template('solicitudes/aprobar.html', solicitudes=solicitudes)

@solicitudes_bp.route('/aprobar/<int:id>', methods=['POST'])
def aprobar_solicitud(id):
    if 'usuario_id' not in session:
        flash('Debe iniciar sesión para acceder a esta página', 'danger')
        return redirect(url_for('auth.login'))
    
    usuario_id = session['usuario_id']
    
    success, message = SolicitudModel.aprobar(id, usuario_id)
    
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('solicitudes.aprobar'))

@solicitudes_bp.route('/rechazar/<int:id>', methods=['POST'])
def rechazar_solicitud(id):
    if 'usuario_id' not in session:
        flash('Debe iniciar sesión para acceder a esta página', 'danger')
        return redirect(url_for('auth.login'))
    
    usuario_id = session['usuario_id']
    
    if SolicitudModel.rechazar(id, usuario_id):
        flash('Solicitud rechazada exitosamente', 'success')
    else:
        flash('Error al rechazar la solicitud', 'danger')
    
    return redirect(url_for('solicitudes.aprobar'))