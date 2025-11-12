# blueprints/solicitudes.py
from flask import Blueprint, render_template, request, redirect, session, flash, url_for
from models.solicitudes_model import SolicitudModel
from models.materiales_model import MaterialModel
from models.oficinas_model import OficinaModel
from utils.filters import filtrar_por_oficina_usuario, verificar_acceso_oficina
from utils.permissions import can_access

# Crear blueprint de solicitudes - ✅ CORREGIDO: Definir correctamente el blueprint
solicitudes_bp = Blueprint('solicitudes', __name__, url_prefix='/solicitudes')

# Helpers de autenticación locales
def _require_login():
    return 'usuario_id' in session

def _has_role(*roles):
    rol = (session.get('rol', '') or '').strip().lower()
    return rol in [r.lower() for r in roles]

# ✅ CORREGIDO: ruta base del blueprint ahora es '/'
@solicitudes_bp.route('/')
def listar_solicitudes():
    # Verificación de sesión
    if not _require_login():
        return redirect('/login')

    # ✅ USAR EL SISTEMA DE PERMISOS CENTRALIZADO
    if not can_access('solicitudes', 'view'):
        flash('No tienes permisos para ver el listado de solicitudes', 'danger')
        return redirect('/dashboard')

    # ✅ Todos EXCEPTO tesoreria
    rol = session.get('rol', '')
    if rol == 'tesoreria':
        flash('No tiene permisos para acceder a esta sección', 'danger')
        return redirect('/reportes')

    try:
        # Obtener TODAS las solicitudes sin filtrar aún
        todas_solicitudes = SolicitudModel.obtener_todas() or []

        # ✅ CORRECCIÓN CLAVE: Solo filtrar si NO es administrador ni lider_inventario
        if rol in ['administrador', 'lider_inventario']:
            solicitudes = todas_solicitudes  # Acceso total
        else:
            solicitudes = filtrar_por_oficina_usuario(todas_solicitudes, 'oficina_id')

        # Obtener materiales y oficinas (sin filtrar para admin)
        todos_materiales = MaterialModel.obtener_todos() or []
        if rol in ['administrador', 'lider_inventario']:
            materiales = todos_materiales
        else:
            materiales = filtrar_por_oficina_usuario(todos_materiales, 'oficina_id')
        materiales_dict = {mat['id']: mat for mat in materiales}

        # Oficinas únicas para filtro
        todas_oficinas = OficinaModel.obtener_todas() or []
        if rol in ['administrador', 'lider_inventario']:
            oficinas_filtradas = todas_oficinas
        else:
            oficinas_filtradas = filtrar_por_oficina_usuario(todas_oficinas)
        oficinas_unique = list({oficina['nombre'] for oficina in oficinas_filtradas if oficina.get('nombre')})

        # Estadísticas
        total_solicitudes = len(solicitudes)
        solicitudes_pendientes = len([s for s in solicitudes if s.get('estado', '').lower() == 'pendiente'])
        solicitudes_aprobadas = len([s for s in solicitudes if s.get('estado', '').lower() == 'aprobada'])
        solicitudes_rechazadas = len([s for s in solicitudes if s.get('estado', '').lower() == 'rechazada'])

        # Filtros desde URL
        filtro_estado = request.args.get('estado', 'todos')
        filtro_oficina = request.args.get('oficina', 'todas')

        # Aplicar filtros
        solicitudes_filtradas = solicitudes.copy()
        if filtro_estado != 'todos':
            solicitudes_filtradas = [s for s in solicitudes_filtradas if s.get('estado', '').lower() == filtro_estado.lower()]
        if filtro_oficina != 'todas':
            solicitudes_filtradas = [s for s in solicitudes_filtradas if s.get('oficina_nombre', '') == filtro_oficina]

        return render_template(
            'solicitudes/solicitudes.html',
            solicitudes=solicitudes_filtradas,
            materiales_dict=materiales_dict,
            oficinas_unique=oficinas_unique,
            total_solicitudes=total_solicitudes,
            solicitudes_pendientes=solicitudes_pendientes,
            solicitudes_aprobadas=solicitudes_aprobadas,
            solicitudes_rechazadas=solicitudes_rechazadas,
            filtro_estado=filtro_estado,
            filtro_oficina=filtro_oficina
        )

    except Exception as e:
        print(f"❌ Error obteniendo solicitudes: {e}")
        flash('Error al cargar las solicitudes', 'danger')
        return render_template(
            'solicitudes/solicitudes.html',
            solicitudes=[],
            materiales_dict={},
            oficinas_unique=[],
            total_solicitudes=0,
            solicitudes_pendientes=0,
            solicitudes_aprobadas=0,
            solicitudes_rechazadas=0,
            filtro_estado='todos',
            filtro_oficina='todas'
        )

@solicitudes_bp.route('/crear', methods=['GET'])
def mostrar_formulario_solicitud():
    """Muestra el formulario para crear solicitud"""
    if not _require_login():
        return redirect('/login')

    # ✅ Todos EXCEPTO tesoreria
    rol = session.get('rol', '')
    if rol == 'tesoreria':
        flash('No tiene permisos para acceder a esta sección', 'danger')
        return redirect('/reportes')

    print("Mostrando formulario de creación (GET)")
    try:
        # ✅ CORRECCIÓN: Obtener TODOS los materiales sin filtrar por oficina
        materiales = MaterialModel.obtener_todos() or []

        print(f"✅ Materiales cargados para formulario: {len(materiales)}")

        return render_template('solicitudes/crear.html', materiales=materiales)
    except Exception as e:
        print(f"Error al cargar formulario: {e}")
        flash('Error al cargar el formulario', 'error')
        return redirect(url_for('solicitudes.listar_solicitudes'))

@solicitudes_bp.route('/crear', methods=['POST'])
def procesar_solicitud():
    """Procesa el formulario de creación de solicitud usando el SP"""
    if not _require_login():
        return redirect('/login')

    # ✅ Todos EXCEPTO tesoreria
    rol = session.get('rol', '')
    if rol == 'tesoreria':
        flash('No tiene permisos para acceder a esta sección', 'danger')
        return redirect('/reportes')

    print("Procesando formulario (POST)")
    try:
        oficina_id = request.form.get('oficina_id')
        material_id = request.form.get('material_id')
        cantidad_solicitada = request.form.get('cantidad_solicitada')
        porcentaje_oficina = request.form.get('porcentaje_oficina')
        observacion = request.form.get('observacion', '').strip()

        # ✅ VALIDACIÓN ACTUALIZADA - OBSERVACIÓN OBLIGATORIA
        if not all([oficina_id, material_id, cantidad_solicitada, porcentaje_oficina, observacion]):
            flash('Todos los campos son obligatorios, incluyendo la observación', 'error')
            return redirect(url_for('solicitudes.mostrar_formulario_solicitud'))

        # ✅ VALIDACIÓN ADICIONAL PARA OBSERVACIÓN NO VACÍA
        if not observacion:
            flash('La observación es obligatoria', 'error')
            return redirect(url_for('solicitudes.mostrar_formulario_solicitud'))

        # ✅ VALIDACIÓN DE MÍNIMO 15 CARACTERES
        if len(observacion) < 15:
            flash('La observación debe tener al menos 15 caracteres', 'error')
            return redirect(url_for('solicitudes.mostrar_formulario_solicitud'))

        oficina_id = int(oficina_id)
        material_id = int(material_id)
        cantidad_solicitada = int(cantidad_solicitada)
        porcentaje_oficina = float(porcentaje_oficina)

        # ✅ VALIDACIÓN DEL PORCENTAJE (1-100)
        if porcentaje_oficina < 1 or porcentaje_oficina > 100:
            flash('El porcentaje debe estar entre 1% y 100%', 'error')
            return redirect(url_for('solicitudes.mostrar_formulario_solicitud'))

        # Verificar acceso a la oficina
        if not verificar_acceso_oficina(oficina_id):
            flash('No tiene permisos para crear solicitudes para esta oficina', 'error')
            return redirect(url_for('solicitudes.mostrar_formulario_solicitud'))

        usuario_nombre = session.get('usuario_nombre', 'Sistema')
        if not usuario_nombre:
            flash('Debe iniciar sesión', 'error')
            return redirect('/login')

        # Crear la solicitud CON OBSERVACIÓN
        solicitud_id = SolicitudModel.crear(
            oficina_id=oficina_id,
            material_id=material_id,
            cantidad_solicitada=cantidad_solicitada,
            porcentaje_oficina=porcentaje_oficina,
            usuario_nombre=usuario_nombre,
            observacion=observacion
        )

        if solicitud_id:
            flash('Solicitud creada exitosamente! ID: ' + str(solicitud_id), 'success')
            return redirect(url_for('solicitudes.mostrar_formulario_solicitud'))
        else:
            flash('Error al crear la solicitud', 'error')
            return redirect(url_for('solicitudes.mostrar_formulario_solicitud'))

    except Exception as e:
        print(f"ERROR en crear_solicitud: {e}")
        error_msg = str(e)

        # Manejar errores específicos del stored procedure
        if 'Límite mensual' in error_msg:
            flash('Límite mensual de 1000 elementos excedido para esta oficina. No puede crear más solicitudes este mes.', 'error')
        elif 'Stock insuficiente' in error_msg or 'excede el inventario' in error_msg:
            flash('Stock insuficiente para completar la solicitud. Verifique la cantidad disponible.', 'error')
        elif 'Cantidad solicitada' in error_msg:
            flash('La cantidad solicitada no es válida. Verifique los límites.', 'error')
        else:
            flash('Error interno del servidor: ' + error_msg, 'error')

        return redirect(url_for('solicitudes.mostrar_formulario_solicitud'))

@solicitudes_bp.route('/aprobar/<int:solicitud_id>', methods=['POST'])
def aprobar_solicitud(solicitud_id):
    if not _require_login():
        return redirect('/login')

    # ✅ Todos EXCEPTO tesoreria
    rol = session.get('rol', '')
    if rol == 'tesoreria':
        flash('No tiene permisos para acceder a esta sección', 'danger')
        return redirect('/reportes')

    try:
        # Verificar acceso a la solicitud
        solicitud = SolicitudModel.obtener_por_id(solicitud_id)
        if not solicitud or not verificar_acceso_oficina(solicitud.get('oficina_id')):
            flash('No tiene permisos para aprobar esta solicitud', 'danger')
            return redirect(url_for('solicitudes.listar_solicitudes'))

        usuario_id = session['usuario_id']
        success, message = SolicitudModel.aprobar(solicitud_id, usuario_id)
        if success:
            flash(message, 'success')
        else:
            flash(message, 'danger')
    except Exception as e:
        print(f"❌ Error aprobando solicitud: {e}")
        flash('Error al aprobar la solicitud', 'danger')
    return redirect(url_for('solicitudes.listar_solicitudes'))

@solicitudes_bp.route('/aprobar_parcial/<int:solicitud_id>', methods=['POST'])
def aprobar_parcial_solicitud(solicitud_id):
    if not _require_login():
        return redirect('/login')

    # ✅ Todos EXCEPTO tesoreria
    rol = session.get('rol', '')
    if rol == 'tesoreria':
        flash('No tiene permisos para acceder a esta sección', 'danger')
        return redirect('/reportes')

    try:
        # Verificar acceso a la solicitud
        solicitud = SolicitudModel.obtener_por_id(solicitud_id)
        if not solicitud or not verificar_acceso_oficina(solicitud.get('oficina_id')):
            flash('No tiene permisos para aprobar esta solicitud', 'danger')
            return redirect(url_for('solicitudes.listar_solicitudes'))

        usuario_id = session['usuario_id']
        cantidad_aprobada = int(request.form.get('cantidad_aprobada', 0))

        if cantidad_aprobada <= 0:
            flash('La cantidad aprobada debe ser mayor que 0', 'danger')
            return redirect(url_for('solicitudes.listar_solicitudes'))

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
    return redirect(url_for('solicitudes.listar_solicitudes'))

@solicitudes_bp.route('/rechazar/<int:solicitud_id>', methods=['POST'])
def rechazar_solicitud(solicitud_id):
    if not _require_login():
        return redirect('/login')

    # ✅ Todos EXCEPTO tesoreria
    rol = session.get('rol', '')
    if rol == 'tesoreria':
        flash('No tiene permisos para acceder a esta sección', 'danger')
        return redirect('/reportes')

    try:
        # Verificar acceso a la solicitud
        solicitud = SolicitudModel.obtener_por_id(solicitud_id)
        if not solicitud or not verificar_acceso_oficina(solicitud.get('oficina_id')):
            flash('No tiene permisos para rechazar esta solicitud', 'danger')
            return redirect(url_for('solicitudes.listar_solicitudes'))

        usuario_id = session['usuario_id']
        observacion = request.form.get('observacion', '')
        if SolicitudModel.rechazar(solicitud_id, usuario_id, observacion):
            flash('Solicitud rechazada exitosamente', 'success')
        else:
            flash('Error al rechazar la solicitud', 'danger')
    except Exception as e:
        print(f"❌ Error rechazando solicitud: {e}")
        flash('Error al rechazar la solicitud', 'danger')
    return redirect(url_for('solicitudes.listar_solicitudes'))

# ✅ NUEVA RUTA: Registrar devolución
@solicitudes_bp.route('/devolucion/<int:solicitud_id>', methods=['POST'])
def registrar_devolucion(solicitud_id):
    if not _require_login():
        return redirect('/login')

    # ✅ Todos EXCEPTO tesoreria
    rol = session.get('rol', '')
    if rol == 'tesoreria':
        flash('No tiene permisos para acceder a esta sección', 'danger')
        return redirect('/reportes')

    try:
        # Verificar acceso a la solicitud
        solicitud = SolicitudModel.obtener_por_id(solicitud_id)
        if not solicitud or not verificar_acceso_oficina(solicitud.get('oficina_id')):
            flash('No tiene permisos para procesar esta solicitud', 'danger')
            return redirect(url_for('solicitudes.listar_solicitudes'))

        cantidad_devuelta = int(request.form.get('cantidad_devuelta', 0))
        observacion = request.form.get('observacion', '').strip()
        usuario_id = session['usuario_id']

        if cantidad_devuelta <= 0:
            flash('La cantidad devuelta debe ser mayor que 0', 'danger')
            return redirect(url_for('solicitudes.listar_solicitudes'))

        success, message = SolicitudModel.registrar_devolucion(
            solicitud_id, usuario_id, cantidad_devuelta, observacion
        )
        
        if success:
            flash(message, 'success')
        else:
            flash(message, 'danger')
            
    except ValueError:
        flash('La cantidad devuelta debe ser un número válido', 'danger')
    except Exception as e:
        print(f"❌ Error registrando devolución: {e}")
        flash('Error al registrar la devolución', 'danger')
        
    return redirect(url_for('solicitudes.listar_solicitudes'))