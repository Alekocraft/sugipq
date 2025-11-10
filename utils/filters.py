from flask import session
from models.materiales_model import MaterialModel
from models.solicitudes_model import SolicitudModel
from models.inventario_corporativo_model import InventarioCorporativoModel

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

# ============================================================================
# FILTROS ESPECÍFICOS POR MODELO
# ============================================================================

def filtrar_materiales_por_oficina():
    """Filtrar materiales por oficina del usuario"""
    materiales = MaterialModel.obtener_todos() or []
    return filtrar_por_oficina_usuario(materiales)

def filtrar_solicitudes_por_oficina():
    """Filtrar solicitudes por oficina del usuario"""
    solicitudes = SolicitudModel.obtener_todas() or []
    return filtrar_por_oficina_usuario(solicitudes, 'oficina_id')

def filtrar_inventario_por_oficina():
    """Filtrar inventario corporativo por oficina del usuario"""
    inventario = InventarioCorporativoModel.obtener_todos() or []
    return filtrar_por_oficina_usuario(inventario, 'oficina_id')

# ============================================================================
# FILTROS AVANZADOS PARA INVENTARIO CORPORATIVO
# ============================================================================

def aplicar_filtros_inventario_corporativo(productos, filtros):
    """
    Aplicar múltiples filtros al inventario corporativo
    
    Args:
        productos: Lista de productos
        filtros: Diccionario con filtros a aplicar
    
    Returns:
        Lista de productos filtrados
    """
    productos_filtrados = productos.copy()
    
    # Filtro por oficina
    if filtros.get('oficina'):
        oficina_filtro = filtros['oficina']
        if oficina_filtro == 'Sede Principal':
            productos_filtrados = [p for p in productos_filtrados if p.get('oficina', 'Sede Principal') == 'Sede Principal']
        elif oficina_filtro == 'Oficinas de Servicio':
            productos_filtrados = [p for p in productos_filtrados if p.get('oficina', 'Sede Principal') != 'Sede Principal']
        else:
            productos_filtrados = [p for p in productos_filtrados if p.get('oficina', '') == oficina_filtro]
    
    # Filtro por categoría
    if filtros.get('categoria'):
        categoria_filtro = filtros['categoria'].lower()
        productos_filtrados = [p for p in productos_filtrados if p.get('categoria', '').lower() == categoria_filtro]
    
    # Filtro por stock
    if filtros.get('stock'):
        stock_filtro = filtros['stock']
        if stock_filtro == 'bajo':
            productos_filtrados = [p for p in productos_filtrados if p.get('cantidad', 0) <= p.get('cantidad_minima', 5)]
        elif stock_filtro == 'normal':
            productos_filtrados = [p for p in productos_filtrados if p.get('cantidad', 0) > p.get('cantidad_minima', 5)]
        elif stock_filtro == 'sin':
            productos_filtrados = [p for p in productos_filtrados if p.get('cantidad', 0) == 0]
    
    return productos_filtrados

def obtener_estadisticas_inventario(productos):
    """
    Calcular estadísticas del inventario
    
    Args:
        productos: Lista de productos
    
    Returns:
        Diccionario con estadísticas
    """
    total_productos = len(productos)
    valor_total = sum(p.get('valor_unitario', 0) * p.get('cantidad', 0) for p in productos)
    productos_bajo_stock = len([p for p in productos if p.get('cantidad', 0) <= p.get('cantidad_minima', 5)])
    productos_sin_stock = len([p for p in productos if p.get('cantidad', 0) == 0])
    
    # Distribución por oficina
    oficinas = {}
    for producto in productos:
        oficina = producto.get('oficina', 'Sin Oficina')
        if oficina not in oficinas:
            oficinas[oficina] = 0
        oficinas[oficina] += 1
    
    return {
        'total_productos': total_productos,
        'valor_total': valor_total,
        'productos_bajo_stock': productos_bajo_stock,
        'productos_sin_stock': productos_sin_stock,
        'distribucion_oficinas': oficinas
    }

# ============================================================================
# FILTROS PARA DASHBOARD Y REPORTES
# ============================================================================

def obtener_estadisticas_dashboard():
    """Obtener estadísticas para el dashboard"""
    from .auth import get_current_user
    
    user = get_current_user()
    if not user:
        return {}
    
    # Materiales filtrados
    materiales = filtrar_materiales_por_oficina()
    
    # Solicitudes filtradas
    solicitudes = filtrar_solicitudes_por_oficina()
    
    # Inventario corporativo (solo para roles específicos)
    inventario_corporativo = []
    if user['rol'] in ['administrador', 'lider_inventario', 'inventario_corporativo']:
        inventario_corporativo = InventarioCorporativoModel.obtener_todos() or []
    
    return {
        'total_materiales': len(materiales),
        'total_solicitudes': len(solicitudes),
        'solicitudes_pendientes': len([s for s in solicitudes if s.get('estado') == 'pendiente']),
        'solicitudes_aprobadas': len([s for s in solicitudes if s.get('estado') == 'aprobada']),
        'solicitudes_rechazadas': len([s for s in solicitudes if s.get('estado') == 'rechazada']),
        'total_productos_corporativos': len(inventario_corporativo),
        'productos_bajo_stock': len([p for p in inventario_corporativo if p.get('cantidad', 0) <= p.get('cantidad_minima', 5)])
    }