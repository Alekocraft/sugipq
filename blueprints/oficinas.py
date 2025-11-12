# blueprints/oficinas.py

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    session,
    flash,
    url_for,
)
from models.oficinas_model import OficinaModel
from models.materiales_model import MaterialModel
from models.solicitudes_model import SolicitudModel
from utils.filters import filtrar_por_oficina_usuario, verificar_acceso_oficina
from utils.permissions import can_access  # ✅ nuevo import


# El blueprint expone todas sus rutas bajo /oficinas
oficinas_bp = Blueprint("oficinas", __name__, url_prefix="/oficinas")


def _require_login() -> bool:
    """Retorna True si hay sesión iniciada."""
    return "usuario_id" in session


@oficinas_bp.route("/", methods=["GET"])
def listar_oficinas():
    """
    Lista todas las oficinas visibles para el usuario.
    Requiere sesión y permiso de vista para oficinas.
    """
    if not _require_login():
        return redirect("/login")

    # ✅ CORREGIR: Verificar permiso para módulo 'oficinas'
    if not can_access("oficinas", "view"):
        flash("No tiene permisos para acceder a esta sección", "danger")
        return redirect("/dashboard")

    try:
        oficinas = OficinaModel.obtener_todas() or []
        return render_template("oficinas/listar.html", oficinas=oficinas)
    except Exception as e:
        print(f"❌ Error obteniendo oficinas: {e}")
        flash("Error al cargar las oficinas", "danger")
        return render_template("oficinas/listar.html", oficinas=[])


@oficinas_bp.route("/detalle/<int:oficina_id>", methods=["GET"])
def detalle_oficina(oficina_id: int):
    """
    Muestra el detalle de una oficina específica (materiales y solicitudes filtradas por oficina del usuario).
    Requiere sesión y verificación de acceso a esa oficina.
    """
    if not _require_login():
        return redirect("/login")

    if not verificar_acceso_oficina(oficina_id):
        flash("No tiene permisos para acceder a esta oficina", "danger")
        return redirect(url_for("oficinas.listar_oficinas"))

    try:
        oficina = OficinaModel.obtener_por_id(oficina_id)
        if not oficina:
            flash("Oficina no encontrada", "danger")
            return redirect(url_for("oficinas.listar_oficinas"))

        # Cargas masivas y filtrado por oficina del usuario
        todos_materiales = MaterialModel.obtener_todos() or []
        todas_solicitudes = SolicitudModel.obtener_todas() or []

        materiales_oficina = filtrar_por_oficina_usuario(
            todos_materiales, "oficina_id"
        )
        solicitudes_oficina = filtrar_por_oficina_usuario(
            todas_solicitudes, "oficina_id"
        )

        return render_template(
            "oficinas/detalle.html",
            oficina=oficina,
            materiales=materiales_oficina,
            solicitudes=solicitudes_oficina,
        )
    except Exception as e:
        print(f"❌ Error cargando detalle de oficina: {e}")
        flash("Error al cargar el detalle de la oficina", "danger")
        return redirect(url_for("oficinas.listar_oficinas"))
