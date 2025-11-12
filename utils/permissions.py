# utils/permissions.py
"""
Sistema de verificación de permisos
"""
from flask import session
from config.permissions import ROLE_PERMISSIONS, OFFICE_MAPPING, get_office_key

class PermissionManager:
    @staticmethod
    def get_user_permissions():
        """Obtiene todos los permisos del usuario actual"""
        role = session.get('rol', '').lower()
        office_name = session.get('oficina_nombre', '')
        office_key = get_office_key(office_name)
        
        # Permisos base del rol
        role_perms = ROLE_PERMISSIONS.get(role, {})
        
        return {
            'role': role_perms,
            'office_key': office_key,
            'office_filter': role_perms.get('office_filter', 'own')
        }
    
    @staticmethod
    def has_module_access(module_name):
        """Verifica acceso a un módulo completo"""
        perms = PermissionManager.get_user_permissions()
        role_modules = perms['role'].get('modules', [])
        return module_name in role_modules
    
    @staticmethod
    def has_action_permission(module, action):
        """Verifica permiso para una acción específica en un módulo"""
        perms = PermissionManager.get_user_permissions()
        role_actions = perms['role'].get('actions', {}).get(module, [])
        return action in role_actions
    
    @staticmethod
    def can_view_actions():
        """Verifica si puede ver columnas de acciones"""
        role = session.get('rol', '').lower()
        office_key = get_office_key(session.get('oficina_nombre', ''))
        return role in ['administrador', 'lider_inventario'] or office_key == 'COQ'

    @staticmethod
    def get_office_filter():
        """Obtiene el filtro de oficina para consultas"""
        perms = PermissionManager.get_user_permissions()
        office_filter = perms.get('office_filter', 'own')
        office_key = perms.get('office_key')
        
        if office_filter == 'all':
            return None
        else:
            return office_key

# Funciones de conveniencia para usar en templates y rutas
def can_access(module, action=None):
    if action:
        return PermissionManager.has_action_permission(module, action)
    return PermissionManager.has_module_access(module)

def can_view_actions():
    return PermissionManager.can_view_actions()

def get_accessible_modules():
    perms = PermissionManager.get_user_permissions()
    role_modules = perms['role'].get('modules', [])
    return role_modules

def get_office_filter():
    return PermissionManager.get_office_filter()

def user_can_view_all():
    perms = PermissionManager.get_user_permissions()
    return perms.get('office_filter') == 'all'

def assign_role_by_office(office_name):
    office_roles = {
        'COQ': 'oficina_coq',
        'CALI': 'oficina_cali', 
        'MEDELLÍN': 'oficina_medellin',
        'BUCARAMANGA': 'oficina_bucaramanga',
        'POLO CLUB': 'oficina_polo_club',
        'NOGAL': 'oficina_nogal',
        'TUNJA': 'oficina_tunja',
        'CARTAGENA': 'oficina_cartagena',
        'MORATO': 'oficina_morato',
        'CEDRITOS': 'oficina_cedritos',
        'LOURDES': 'oficina_lourdes',
        'PEREIRA': 'oficina_pereira',
        'NEIVA': 'oficina_neiva',
        'KENNEDY': 'oficina_kennedy'
    }
    
    office_key = get_office_key(office_name)
    return office_roles.get(office_key, 'oficina_regular')