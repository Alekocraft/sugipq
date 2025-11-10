import os
from werkzeug.utils import secure_filename
from flask import flash
from config.config import Config

def allowed_file(filename):
    """Verificar si la extensión del archivo es permitida"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

def save_uploaded_file(file, subfolder=''):
    """Guardar archivo subido de forma segura"""
    if file and file.filename:
        if allowed_file(file.filename):
            # Generar nombre seguro
            filename = secure_filename(file.filename)
            
            # Crear subdirectorio si se especifica
            upload_dir = os.path.join(Config.UPLOAD_FOLDER, subfolder)
            os.makedirs(upload_dir, exist_ok=True)
            
            filepath = os.path.join(upload_dir, filename)
            file.save(filepath)
            
            # Devolver ruta relativa para la web
            return f'/{filepath.replace(os.sep, "/")}'
        else:
            raise ValueError(f"Tipo de archivo no permitido. Extensiones permitidas: {', '.join(Config.ALLOWED_EXTENSIONS)}")
    return None

def get_user_permissions():
    """Obtener permisos del usuario actual basado en su rol"""
    from flask import session
    role = session.get('rol')
    return Config.ROLES.get(role, [])

def can_access(section):
    """Verificar si el usuario puede acceder a una sección"""
    permissions = get_user_permissions()
    return section in permissions

def format_currency(value):
    """Formatear valor como moneda"""
    if value is None:
        return "$0"
    try:
        return f"${value:,.0f}"
    except (ValueError, TypeError):
        return "$0"

def format_date(date_value, format_str='%d/%m/%Y'):
    """Formatear fecha"""
    if date_value:
        try:
            return date_value.strftime(format_str)
        except (AttributeError, ValueError):
            return str(date_value)
    return ""

def get_pagination_params(default_per_page=20):
    """Obtener parámetros de paginación desde request"""
    from flask import request
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', default_per_page, type=int)
    return page, per_page

def flash_errors(form):
    """Flash todos los errores de un formulario"""
    for field, errors in form.errors.items():
        for error in errors:
            field_label = getattr(form, field).label.text if hasattr(form, field) else field
            flash(f"Error en {field_label}: {error}", 'danger')

def generate_codigo_unico(prefix, existing_codes):
    """Generar código único automáticamente"""
    import random
    import string
    
    while True:
        # Generar parte aleatoria
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        codigo = f"{prefix}-{random_part}"
        
        # Verificar que no exista
        if codigo not in existing_codes:
            return codigo

def calcular_valor_total(cantidad, valor_unitario):
    """Calcular valor total"""
    try:
        return cantidad * valor_unitario
    except (TypeError, ValueError):
        return 0

def validar_stock(cantidad_solicitada, stock_disponible):
    """Validar que la cantidad solicitada no exceda el stock"""
    return cantidad_solicitada <= stock_disponible

def obtener_mes_actual():
    """Obtener nombre del mes actual en español"""
    from datetime import datetime
    meses = [
        'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
        'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
    ]
    return meses[datetime.now().month - 1]