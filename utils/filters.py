# utils/filters.py
from flask import session

def filtrar_por_oficina_usuario(datos, campo_oficina_id='oficina_id'):
    """
    Filtra datos según la oficina del usuario actual
    """
    if 'rol' not in session:
        return []

    rol = session['rol']
    oficina_id_usuario = session.get('oficina_id')

    # Roles con acceso total
    if rol in ['administrador', 'lider_inventario']:
        return datos

    # Roles restringidos a su oficina
    if rol in ['oficina_principal', 'aprobador', 'tesoreria']:
        return [item for item in datos if item.get(campo_oficina_id) == oficina_id_usuario]

    return []

def verificar_acceso_oficina(oficina_id):
    """
    Verifica si el usuario tiene acceso a la oficina especificada
    """
    if 'rol' not in session:
        return False

    rol = session['rol']
    oficina_id_usuario = session.get('oficina_id')

    # Roles con acceso total
    if rol in ['administrador', 'lider_inventario']:
        return True

    # Roles restringidos a su oficina
    if rol in ['oficina_principal', 'aprobador', 'tesoreria']:
        return oficina_id == oficina_id_usuario

    return False