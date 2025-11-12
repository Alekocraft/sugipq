# config/permissions.py
"""
Sistema centralizado de permisos basado en roles y oficinas
"""

ROLE_PERMISSIONS = {
    'administrador': {
        'modules': ['dashboard', 'material_pop', 'inventario_corporativo', 'prestamo_material'],
        'actions': {
            'materiales': ['view', 'create', 'edit', 'delete'],
            'solicitudes': ['view', 'create', 'approve', 'reject', 'partial_approve'],
            'oficinas': ['view', 'manage'],
            'aprobadores': ['view', 'manage'],
            'reportes': ['view_all'],
            'inventario_corporativo': ['view', 'create', 'edit', 'delete', 'assign'],
            'prestamos': ['view', 'create', 'approve', 'reject', 'return', 'manage_materials']
        },
        'office_filter': 'all'
    },
    'lider_inventario': {
        'modules': ['dashboard', 'material_pop', 'inventario_corporativo', 'prestamo_material'],
        'actions': {
            'materiales': ['view', 'create', 'edit', 'delete'],
            'solicitudes': ['view', 'create', 'approve', 'reject', 'partial_approve'],
            'oficinas': ['view'],
            'aprobadores': ['view'],
            'reportes': ['view_all'],
            'inventario_corporativo': ['view', 'create', 'edit', 'delete', 'assign'],
            'prestamos': ['view', 'create', 'approve', 'reject', 'return', 'manage_materials']
        },
        'office_filter': 'all'
    },
    'oficina_coq': {
        'modules': ['dashboard', 'material_pop', 'prestamo_material', 'reportes'],
        'actions': {
            'materiales': ['view', 'create'],
            'solicitudes': ['view', 'create'],
            'prestamos': ['view', 'create'],
            'reportes': ['view_own']
        },
        'office_filter': 'COQ'
    },
    'oficina_cali': {
        'modules': ['dashboard', 'material_pop', 'prestamo_material', 'reportes', 'oficinas'],  # ✅ Agregar 'oficinas'
        'actions': {
            # ❌ MATERIALES: SIN ACCESO
            'materiales': [],

            # ✅ SOLICITUDES: Solo puede CREAR, no ver listado
            'solicitudes': ['create'],

            # ✅ OFICINAS: Puede ver (NUEVO)
            'oficinas': ['view'],

            # ✅ APROBADORES: Puede ver
            'aprobadores': ['view'],

            # ✅ PRÉSTAMOS: Puede ver sus préstamos y crear nuevos
            'prestamos': ['view_own', 'create'],

            # ✅ REPORTES: Solo de su oficina (NO TOCAR)
            'reportes': ['view_own']
        },
        'office_filter': 'CALI'
    },  # ←🚩 faltaba esta coma
    'oficina_medellin': {
        'modules': ['dashboard', 'material_pop', 'prestamo_material', 'reportes'],
        'actions': {
            'materiales': ['view', 'create'],
            'solicitudes': ['view', 'create'],
            'prestamos': ['view', 'create'],
            'reportes': ['view_own']
        },
        'office_filter': 'MEDELLÍN'
    },
    'oficina_regular': {
        'modules': ['dashboard', 'reportes'],
        'actions': {
            'reportes': ['view_own']
        },
        'office_filter': 'own'
    }
}

OFFICE_MAPPING = {
    'COQ': 'COQ',
    'POLO CLUB': 'POLO CLUB',
    'NOGAL': 'NOGAL',
    'TUNJA': 'TUNJA',
    'CARTAGENA': 'CARTAGENA',
    'MORATO': 'MORATO',
    'MEDELLÍN': 'MEDELLÍN',
    'CEDRITOS': 'CEDRITOS',
    'LOURDES': 'LOURDES',
    'CALI': 'CALI',
    'PEREIRA': 'PEREIRA',
    'NEIVA': 'NEIVA',
    'KENNEDY': 'KENNEDY',
    'BUCARAMANGA': 'BUCARAMANGA'
}

def get_office_key(office_name: str) -> str:
    """
    Normaliza el nombre de oficina y lo mapea si existe en OFFICE_MAPPING.
    """
    key = office_name.upper().strip()
    return OFFICE_MAPPING.get(key, key)
