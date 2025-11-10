from flask import Blueprint, request, session, flash, redirect
from models.solicitudes_model import SolicitudModel
from utils.filters import verificar_acceso_oficina

aprobacion_bp = Blueprint('aprobacion', __name__)

@aprobacion_bp.route('/solicitudes/aprobar/<int:solicitud_id>', methods=['POST'])
def aprobar_solicitud(solicitud_id):
    if 'usuario_id' not in session:
        return redirect('/login')

    rol = session.get('rol', '')
    if rol == 'tesoreria':
        flash('No tiene permisos para acceder a esta sección', 'danger')
        return redirect('/reportes')

    try:
        solicitud = SolicitudModel.obtener_por_id(solicitud_id)
        if not solicitud or not verificar_acceso_oficina(solicitud.get('oficina_id')):
            flash('No tiene permisos para aprobar esta solicitud', 'danger')
            return redirect('/solicitudes')

        usuario_id = session['usuario_id']
        success, message = SolicitudModel.aprobar(solicitud_id, usuario_id)
        if success:
            flash(message, 'success')
        else:
            flash(message, 'danger')
    except Exception as e:
        print(f"❌ Error aprobando solicitud: {e}")
        flash('Error al aprobar la solicitud', 'danger')
    return redirect('/solicitudes')

@aprobacion_bp.route('/solicitudes/aprobar_parcial/<int:solicitud_id>', methods=['POST'])
def aprobar_parcial_solicitud(solicitud_id):
    if 'usuario_id' not in session:
        return redirect('/login')

    rol = session.get('rol', '')
    if rol == 'tesoreria':
        flash('No tiene permisos para acceder a esta sección', 'danger')
        return redirect('/reportes')

    try:
        solicitud = SolicitudModel.obtener_por_id(solicitud_id)
        if not solicitud or not verificar_acceso_oficina(solicitud.get('oficina_id')):
            flash('No tiene permisos para aprobar esta solicitud', 'danger')
            return redirect('/solicitudes')

        usuario_id = session['usuario_id']
        cantidad_aprobada = int(request.form.get('cantidad_aprobada', 0))

        if cantidad_aprobada <= 0:
            flash('La cantidad aprobada debe ser mayor que 0', 'danger')
            return redirect('/solicitudes')

        success, message = SolicitudModel.aprobar_parcial(solicitud_id, usuario_id, cantidad_aprobada)
        if success:
            flash(message, 'success')
        else:
            flash(message, 'danger')
    except ValueError:
        flash('La cantidad aprobada debe ser un número válido', 'danger')
    except Exception as e:
        print(f"❌ Error aprobando parcialmente solicitud: {e}")
        flash('Error al aprobar parcialmente la solicitud', 'danger')
    return redirect('/solicitudes')

@aprobacion_bp.route('/solicitudes/rechazar/<int:solicitud_id>', methods=['POST'])
def rechazar_solicitud(solicitud_id):
    if 'usuario_id' not in session:
        return redirect('/login')

    rol = session.get('rol', '')
    if rol == 'tesoreria':
        flash('No tiene permisos para acceder a esta sección', 'danger')
        return redirect('/reportes')

    try:
        solicitud = SolicitudModel.obtener_por_id(solicitud_id)
        if not solicitud or not verificar_acceso_oficina(solicitud.get('oficina_id')):
            flash('No tiene permisos para rechazar esta solicitud', 'danger')
            return redirect('/solicitudes')

        usuario_id = session['usuario_id']
        observacion = request.form.get('observacion', '')
        if SolicitudModel.rechazar(solicitud_id, usuario_id, observacion):
            flash('Solicitud rechazada exitosamente', 'success')
        else:
            flash('Error al rechazar la solicitud', 'danger')
    except Exception as e:
        print(f"❌ Error rechazando solicitud: {e}")
        flash('Error al rechazar la solicitud', 'danger')
    return redirect('/solicitudes')