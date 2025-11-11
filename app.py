# -*- coding: utf-8 -*-
import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, session, flash, jsonify, url_for, send_file
from werkzeug.utils import secure_filename

# Importar modelos
from models.materiales_model import MaterialModel
from models.oficinas_model import OficinaModel
from models.solicitudes_model import SolicitudModel
from models.usuarios_model import UsuarioModel
from models.inventario_corporativo_model import InventarioCorporativoModel

# Importar Utils de forma directa
from utils.filters import filtrar_por_oficina_usuario, verificar_acceso_oficina
from utils.initialization import inicializar_oficina_principal

# Blueprints
from blueprints.auth import auth_bp
from blueprints.materiales import materiales_bp
from blueprints.solicitudes import solicitudes_bp
from blueprints.oficinas import oficinas_bp
from blueprints.aprobadores import aprobadores_bp
from blueprints.reportes import reportes_bp
from blueprints.aprobacion import aprobacion_bp
from blueprints.api import api_bp
from blueprints.inventario_corporativo import inventario_corporativo_bp

# Importar blueprints con alias para consistencia
from routes_prestamos import bp_prestamos
from routes_inventario_corporativo import bp_inv as bp_inventario_corporativo

# Importar conexión a base de datos
from database import get_database_connection

# Configuración de la aplicación
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, 'templates'),
    static_folder=os.path.join(BASE_DIR, 'static')
)

app.secret_key = os.environ.get('SECRET_KEY', os.urandom(32))
app.config['JSON_AS_ASCII'] = False
app.config['TEMPLATES_AUTO_RELOAD'] = True  

# Configuración de uploads
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

# Crear directorio de uploads si no existe
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
print(f"✅ Directorio de uploads: {os.path.abspath(UPLOAD_FOLDER)}")

# Registrar blueprints (CORREGIDO - sin duplicados)
app.register_blueprint(bp_prestamos)
app.register_blueprint(bp_inventario_corporativo)
app.register_blueprint(auth_bp)   
app.register_blueprint(materiales_bp)
app.register_blueprint(solicitudes_bp)
app.register_blueprint(oficinas_bp)
app.register_blueprint(aprobadores_bp)
app.register_blueprint(reportes_bp)


# Registrar nuevos blueprints (SOLO UNA VEZ)
app.register_blueprint(aprobacion_bp)
app.register_blueprint(api_bp)

# CORREGIDO: Registrar inventario corporativo SIN url_prefix ya que las rutas ya lo incluyen
app.register_blueprint(inventario_corporativo_bp)

# Verificar que los blueprints estén registrados correctamente
print("✅ Blueprints registrados:")
for name in app.blueprints:
    print(f"   - {name}")

# ============================================================================
# ERROR HANDLERS
# ============================================================================
@app.errorhandler(404)
def pagina_no_encontrada(error):
    return render_template('error/404.html'), 404

@app.errorhandler(500)
def error_interno(error):
    return render_template('error/500.html'), 500

@app.errorhandler(413)
def archivo_demasiado_grande(error):
    flash('El archivo es demasiado grande. Tamaño máximo: 16MB', 'danger')
    return redirect(request.url)

# ============================================================================
# INICIALIZACIÓN
# ============================================================================
if __name__ == '__main__':
    print("🚀 Iniciando servidor Flask...")
    print(f"📁 Directorio de trabajo: {os.getcwd()}")
    print(f"📁 Directorio de templates: {os.path.abspath('templates')}")
    print(f"📁 Directorio de uploads: {os.path.abspath(UPLOAD_FOLDER)}")

    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
        print(f"✅ Creado directorio de uploads: {UPLOAD_FOLDER}")
    
    # Inicializar Sede Principal usando la función importada
    inicializar_oficina_principal()
    app.run(debug=True, host='0.0.0.0', port=5000)