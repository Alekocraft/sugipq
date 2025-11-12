# utils/filters.py
from flask import session
from utils.permissions import can_access

def filtrar_por_oficina_usuario(datos, campo_oficina_id='oficina_id'):
    """
    Filtra datos según la oficina del usuario actual.
    """
    if 'rol' not in session:
        return []

    oficina_id_usuario = session.get('oficina_id')

    # Administrador y líder de inventario tienen acceso completo
    if can_access('materiales', 'view') and can_access('solicitudes', 'view'):
        return datos

    # Otros roles solo pueden ver datos de su oficina
    return [item for item in datos if item.get(campo_oficina_id) == oficina_id_usuario]

def verificar_acceso_oficina(oficina_id):
    """
    Verifica si el usuario actual tiene acceso a una oficina específica.
    """
    if 'rol' not in session:
        return False

    oficina_id_usuario = session.get('oficina_id')

    # Administrador y líder de inventario tienen acceso completo
    if can_access('materiales', 'view') and can_access('solicitudes', 'view'):
        return True

    # Otros roles solo acceden a su propia oficina
    return oficina_id == oficina_id_usuario