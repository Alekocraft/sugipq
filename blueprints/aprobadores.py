from flask import Blueprint, render_template, request, redirect, session, flash, url_for, current_app
from models.usuarios_model import UsuarioModel
from utils.permissions import can_access

# 📘 Crear blueprint de aprobadores
aprobadores_bp = Blueprint('aprobadores', __name__, url_prefix='/aprobadores')


# 🧩 Helper: Verifica si el usuario está logueado
def _require_login():
    return 'usuario_id' in session


# 📄 Ruta principal: listar aprobadores
@aprobadores_bp.route('/')
def listar_aprobadores():
    # 🔒 Verificación de sesión
    if not _require_login():
        flash('Debe iniciar sesión para acceder a esta sección', 'warning')
        return redirect(url_for('auth.login'))

    # 🔐 Verificación de permisos
    if not can_access('aprobadores', 'view'):
        flash('No tiene permisos para acceder a esta sección', 'danger')
        return redirect(url_for('dashboard'))

    try:
        # 📦 Obtener lista de aprobadores desde el modelo
        aprobadores = UsuarioModel.obtener_aprobadores() or []
        return render_template('aprobadores/listar.html', aprobadores=aprobadores)

    except Exception as e:
        # ⚠️ Manejo de errores
        current_app.logger.error(f"❌ Error obteniendo aprobadores: {e}")
        flash('Ocurrió un error al cargar los aprobadores', 'danger')
        return render_template('aprobadores/listar.html', aprobadores=[])