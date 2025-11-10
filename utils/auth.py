# utils/auth.py
from flask import session

def require_login():
    """Verifica si el usuario está logueado"""
    return 'usuario_id' in session

def has_role(*roles):
    """Verifica si el usuario tiene alguno de los roles especificados"""
    rol = (session.get('rol', '') or '').strip().lower()
    return rol in [r.lower() for r in roles]