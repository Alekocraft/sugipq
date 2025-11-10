# blueprints/aprobadores.py
from flask import Blueprint, render_template, request, redirect, session, flash, url_for
from models.usuarios_model import UsuarioModel

# Crear blueprint de aprobadores
aprobadores_bp = Blueprint('aprobadores', __name__, url_prefix='/aprobadores')

# Helpers de autenticación locales
def _require_login():
    return 'usuario_id' in session

def _has_role(*roles):
    rol = (session.get('rol', '') or '').strip().lower()
    return rol in [r.lower() for r in roles]

@aprobadores_bp.route('/')
def listar_aprobadores():
    if not _require_login():
        return redirect('/login')

    # ? SOLO admin, lider_inventario y oficina_principal
    if not _has_role('administrador', 'lider_inventario', 'oficina_principal'):
        flash('No tiene permisos para acceder a esta sección', 'danger')
        return redirect('/dashboard')

    try:
        aprobadores = UsuarioModel.obtener_aprobadores() or []
        return render_template('aprobadores/listar.html', aprobadores=aprobadores)
    except Exception as e:
        print(f"? Error obteniendo aprobadores: {e}")
        flash('Error al cargar los aprobadores', 'danger')
        return render_template('aprobadores/listar.html', aprobadores=[])