# blueprints/materiales.py

from __future__ import annotations

# Standard library
import os

# Third-party
from flask import Blueprint, render_template, request, redirect, session, flash, url_for, current_app
from werkzeug.utils import secure_filename

# Local
from models.materiales_model import MaterialModel
from models.oficinas_model import OficinaModel
from utils.permissions import can_access

materiales_bp = Blueprint('materiales', __name__, url_prefix='/materiales')


def _require_login() -> bool:
    return 'usuario_id' in session


@materiales_bp.route('/', methods=['GET'])
def listar_materiales():
    """Listar todos los materiales (protegido por permisos)."""
    if not can_access('materiales', 'view'):
        flash('❌ No tienes permisos para acceder a materiales', 'danger')
        print(f"🚫 Acceso denegado a /materiales - Usuario: {session.get('usuario_nombre')}")
        return redirect('/dashboard')

    try:
        print("📦 Cargando lista de materiales...")
        materiales = MaterialModel.obtener_todos() or []
        print(f"📦 Se cargaron {len(materiales)} materiales para mostrar")
        return render_template('materials/listar.html', materiales=materiales)
    except Exception as e:
        print(f"❌ Error obteniendo materiales: {e}")
        flash('Error al cargar los materiales', 'danger')
        return render_template('materials/listar.html', materiales=[])


@materiales_bp.route('/crear', methods=['GET', 'POST'])
def crear_material():
    if not _require_login():
        return redirect('/login')

    if not can_access('materiales', 'view'):
        flash('No tiene permisos para acceder a esta sección', 'danger')
        return redirect('/dashboard')

    if request.method == 'GET':
        return render_template('materials/crear.html')

    # resto del código idéntico...
    # (sin alterar ninguna otra lógica ni variable)
