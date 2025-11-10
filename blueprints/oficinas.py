# blueprints/oficinas.py
from flask import Blueprint, render_template, request, redirect, session, flash, url_for
from models.oficinas_model import OficinaModel
from models.materiales_model import MaterialModel
from models.solicitudes_model import SolicitudModel
from utils.filters import filtrar_por_oficina_usuario, verificar_acceso_oficina

# Crear blueprint de oficinas
oficinas_bp = Blueprint('oficinas', __name__, url_prefix='/oficinas')

# Helpers de autenticación locales
def _require_login():
    return 'usuario_id' in session

def _has_role(*roles):
    rol = (session.get('rol', '') or '').strip().lower()
    return rol in [r.lower() for r in roles]

@oficinas_bp.route('/')
def listar_oficinas():
    if not _require_login():
        return redirect('/login')

    # ? SOLO admin, lider_inventario y oficina_principal
    if not _has_role('administrador', 'lider_inventario', 'oficina_principal'):
        flash('No tiene permisos para acceder a esta sección', 'danger')
        return redirect('/dashboard')

    try:
        oficinas = OficinaModel.obtener_todas() or []
        return render_template('oficinas/listar.html', oficinas=oficinas)
    except Exception as e:
        print(f"? Error obteniendo oficinas: {e}")
        flash('Error al cargar las oficinas', 'danger')
        return render_template('oficinas/listar.html', oficinas=[])

@oficinas_bp.route('/detalle/<int:oficina_id>')
def detalle_oficina(oficina_id):
    if not _require_login():
        return redirect('/login')

    # Verificar acceso a la oficina
    if not verificar_acceso_oficina(oficina_id):
        flash('No tiene permisos para acceder a esta oficina', 'danger')
        return redirect(url_for('oficinas.listar_oficinas'))
        
    try:
        oficina = OficinaModel.obtener_por_id(oficina_id)
        if not oficina:
            flash('Oficina no encontrada', 'danger')
            return redirect(url_for('oficinas.listar_oficinas'))

        # Obtener y filtrar datos por oficina
        todos_materiales = MaterialModel.obtener_todos() or []
        todas_solicitudes = SolicitudModel.obtener_todas() or []

        materiales_oficina = filtrar_por_oficina_usuario(todos_materiales, 'oficina_id')
        solicitudes_oficina = filtrar_por_oficina_usuario(todas_solicitudes, 'oficina_id')

        return render_template('oficinas/detalle.html',
                            oficina=oficina,
                            materiales=materiales_oficina,
                            solicitudes=solicitudes_oficina)
    except Exception as e:
        print(f"? Error cargando detalle de oficina: {e}")
        flash('Error al cargar el detalle de la oficina', 'danger')
        return redirect(url_for('oficinas.listar_oficinas'))