# -*- coding: utf-8 -*-
import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, session, flash, jsonify, url_for
from werkzeug.utils import secure_filename

# Importar modelos
from models.materiales_model import MaterialModel
from models.oficinas_model import OficinaModel
from models.solicitudes_model import SolicitudModel
from models.usuarios_model import UsuarioModel
from models.inventario_corporativo_model import InventarioCorporativoModel

# Importar Utilitis
from utils.filters import filtrar_por_oficina_usuario, verificar_acceso_oficina
from utils.initialization import inicializar_oficina_principal

# blueprints
from blueprints.auth import auth_bp
from blueprints.materiales import materiales_bp
from blueprints.solicitudes import solicitudes_bp
from blueprints.oficinas import oficinas_bp
from blueprints.aprobadores import aprobadores_bp
from blueprints.reportes import reportes_bp

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
app.config['TEMPLATES_AUTO_RELOAD'] = True  # útil en desarrollo

# Configuración de uploads
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB



# Crear directorio de uploads si no existe
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
print(f"✅ Directorio de uploads: {os.path.abspath(UPLOAD_FOLDER)}")

# Registrar blueprints
app.register_blueprint(bp_prestamos)
app.register_blueprint(bp_inventario_corporativo)
app.register_blueprint(auth_bp)   
app.register_blueprint(materiales_bp)
app.register_blueprint(solicitudes_bp)
app.register_blueprint(oficinas_bp)
app.register_blueprint(aprobadores_bp)
app.register_blueprint(reportes_bp)

# Verificar que los blueprints estén registrados correctamente
print("✅ Blueprints registrados:")
for name in app.blueprints:
    print(f"   - {name}")

# ============================================================================
# INICIALIZACIÓN DE DATOS - OFICINA SEDE PRINCIPAL
# ============================================================================
def inicializar_oficina_principal():
    """Verifica y crea la oficina Sede Principal si no existe"""
    try:
        print("🔍 Verificando existencia de oficina 'Sede Principal'...")
        oficina_principal = OficinaModel.obtener_por_nombre("Sede Principal")

        if not oficina_principal:
            print("📝 Creando oficina 'Sede Principal'...")
            conn = get_database_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO Oficinas (
                    NombreOficina, 
                    DirectorOficina, 
                    Ubicacion, 
                    EsPrincipal, 
                    Activo, 
                    FechaCreacion,
                    Email
                ) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                "Sede Principal",
                "Director General",
                "Ubicación Principal",
                1,  # EsPrincipal = True
                1,  # Activo = True
                datetime.now(),
                "sede.principal@empresa.com"
            ))

            conn.commit()
            cursor.close()
            conn.close()
            print("✅ Oficina 'Sede Principal' creada exitosamente")

            # Verificar que se creó correctamente
            oficina_verificada = OficinaModel.obtener_por_nombre("Sede Principal")
            if oficina_verificada:
                print(f"✅ Verificación exitosa - ID: {oficina_verificada['id']}")
            else:
                print("⚠️ Advertencia: No se pudo verificar la creación de la oficina")
        else:
            print(f"✅ Oficina 'Sede Principal' ya existe - ID: {oficina_principal['id']}")
    except Exception as e:
        print(f"❌ Error inicializando oficina principal: {e}")
        import traceback
        print(f"🔍 TRACEBACK: {traceback.format_exc()}")

# ============================================================================
# FUNCIONES HELPER PARA FILTROS POR OFICINA - ACTUALIZADO
# ============================================================================
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
# RUTAS DE APROBACIÓN DE SOLICITUDES (INTEGRADAS EN SOLICITUDES) - ACTUALIZADO
# ============================================================================
@app.route('/solicitudes/aprobar/<int:solicitud_id>', methods=['POST'])
def aprobar_solicitud(solicitud_id):
    if 'usuario_id' not in session:
        return redirect('/login')

    # ✅ Todos EXCEPTO tesoreria
    rol = session.get('rol', '')
    if rol == 'tesoreria':
        flash('No tiene permisos para acceder a esta sección', 'danger')
        return redirect('/reportes')

    try:
        # Verificar acceso a la solicitud
        solicitud = SolicitudModel.obtener_por_id(solicitud_id)
        if not solicitud or not verificar_acceso_oficina(solicitud.get('oficina_id')):
            flash('No tiene permisos para aprobar esta solicitud', 'danger')
            return redirect('/solicitudes')

        usuario_id = session['usuario_id']
        success, message = SolicitudModel.aprobar(solicitud_id, usuario_id)
        if success:
            flash(message, 'success')
        else:
            flash(message, 'danger')
    except Exception as e:
        print(f"❌ Error aprobando solicitud: {e}")
        flash('Error al aprobar la solicitud', 'danger')
    return redirect('/solicitudes')

@app.route('/solicitudes/aprobar_parcial/<int:solicitud_id>', methods=['POST'])
def aprobar_parcial_solicitud(solicitud_id):
    if 'usuario_id' not in session:
        return redirect('/login')

    # ✅ Todos EXCEPTO tesoreria
    rol = session.get('rol', '')
    if rol == 'tesoreria':
        flash('No tiene permisos para acceder a esta sección', 'danger')
        return redirect('/reportes')

    try:
        # Verificar acceso a la solicitud
        solicitud = SolicitudModel.obtener_por_id(solicitud_id)
        if not solicitud or not verificar_acceso_oficina(solicitud.get('oficina_id')):
            flash('No tiene permisos para aprobar esta solicitud', 'danger')
            return redirect('/solicitudes')

        usuario_id = session['usuario_id']
        cantidad_aprobada = int(request.form.get('cantidad_aprobada', 0))

        if cantidad_aprobada <= 0:
            flash('La cantidad aprobada debe ser mayor que 0', 'danger')
            return redirect('/solicitudes')

        success, message = SolicitudModel.aprobar_parcial(solicitud_id, usuario_id, cantidad_aprobada)
        if success:
            flash(message, 'success')
        else:
            flash(message, 'danger')
    except ValueError:
        flash('La cantidad aprobada debe ser un número válido', 'danger')
    except Exception as e:
        print(f"❌ Error aprobando parcialmente solicitud: {e}")
        flash('Error al aprobar parcialmente la solicitud', 'danger')
    return redirect('/solicitudes')

@app.route('/solicitudes/rechazar/<int:solicitud_id>', methods=['POST'])
def rechazar_solicitud(solicitud_id):
    if 'usuario_id' not in session:
        return redirect('/login')

    # ✅ Todos EXCEPTO tesoreria
    rol = session.get('rol', '')
    if rol == 'tesoreria':
        flash('No tiene permisos para acceder a esta sección', 'danger')
        return redirect('/reportes')

    try:
        # Verificar acceso a la solicitud
        solicitud = SolicitudModel.obtener_por_id(solicitud_id)
        if not solicitud or not verificar_acceso_oficina(solicitud.get('oficina_id')):
            flash('No tiene permisos para rechazar esta solicitud', 'danger')
            return redirect('/solicitudes')

        usuario_id = session['usuario_id']
        observacion = request.form.get('observacion', '')
        if SolicitudModel.rechazar(solicitud_id, usuario_id, observacion):
            flash('Solicitud rechazada exitosamente', 'success')
        else:
            flash('Error al rechazar la solicitud', 'danger')
    except Exception as e:
        print(f"❌ Error rechazando solicitud: {e}")
        flash('Error al rechazar la solicitud', 'danger')
    return redirect('/solicitudes')

 # ============================================================================
# RUTAS DE INVENTARIO CORPORATIVO
# ============================================================================

@app.route('/inventario-corporativo')
def listar_inventario_corporativo():
    # Requiere sesión como el resto de vistas
    if 'usuario_id' not in session:
        return redirect('/login')

    # Traer productos corporativos
    productos = InventarioCorporativoModel.obtener_todos() or []

    # Conteo para encabezado
    total_productos = len(productos)

    # Render del template que ya tienes:
    # templates/inventario_corporativo/listar.html
    return render_template(
        'inventario_corporativo/listar.html',
        productos=productos,
        total_productos=total_productos
    )

@app.route('/inventario-corporativo/crear', methods=['GET', 'POST'])
def crear_inventario_corporativo():
    if 'usuario_id' not in session:
        return redirect('/login')

    # Siempre cargamos las listas para el formulario
    categorias = InventarioCorporativoModel.obtener_categorias() or []
    proveedores = InventarioCorporativoModel.obtener_proveedores() or []

    if request.method == 'POST':
        try:
            # Campos del formulario
            codigo_unico    = (request.form.get('codigo_unico') or '').strip()
            nombre          = (request.form.get('nombre') or '').strip()
            categoria_id    = int(request.form.get('categoria_id') or 0)
            proveedor_id    = int(request.form.get('proveedor_id') or 0)
            valor_unitario  = float(request.form.get('valor_unitario') or 0)
            cantidad        = int(request.form.get('cantidad') or 0)
            cantidad_minima = int(request.form.get('cantidad_minima') or 0)
            ubicacion       = (request.form.get('ubicacion') or '').strip()
            descripcion     = (request.form.get('descripcion') or '').strip()
            es_asignable    = 1 if request.form.get('es_asignable') == 'on' else 0
            usuario_creador = (session.get('usuario', 'administrador') or 'administrador')

            # Validaciones mínimas
            if not codigo_unico or not nombre or categoria_id <= 0 or proveedor_id <= 0:
                flash('Completa los campos obligatorios (*)', 'warning')
                return render_template('inventario_corporativo/crear.html',
                                       categorias=categorias, proveedores=proveedores)

            # Manejo de imagen (opcional)
            ruta_imagen = None
            archivo = request.files.get('imagen')
            if archivo and archivo.filename:
                filename = secure_filename(archivo.filename)
                upload_dir = os.path.join('static', 'uploads', 'productos')
                os.makedirs(upload_dir, exist_ok=True)
                filepath = os.path.join(upload_dir, filename)
                archivo.save(filepath)
                # Guardamos la ruta para la BD (ruta relativa que puedas servir)
                ruta_imagen = '/' + filepath.replace('\\', '/')

            # Crear en BD usando el modelo
            nuevo_id = InventarioCorporativoModel.crear(
                codigo_unico=codigo_unico,
                nombre=nombre,
                descripcion=descripcion,
                categoria_id=categoria_id,
                proveedor_id=proveedor_id,
                valor_unitario=valor_unitario,
                cantidad=cantidad,
                cantidad_minima=cantidad_minima,
                ubicacion=ubicacion,
                es_asignable=es_asignable,
                usuario_creador=usuario_creador,
                ruta_imagen=ruta_imagen
            )

            if nuevo_id:
                flash('✅ Producto corporativo creado correctamente.', 'success')
                return redirect('/inventario-corporativo')
            else:
                flash('❌ No fue posible crear el producto.', 'danger')

        except Exception as e:
            print(f"[POST /inventario-corporativo/crear] Error: {e}")
            flash('❌ Ocurrió un error al guardar.', 'danger')

        # Si algo falla, re-renderizamos el formulario con las listas
        return render_template('inventario_corporportivo/crear.html',
                               categorias=categorias, proveedores=proveedores)

    # GET → solo pintar formulario con listas
    return render_template('inventario_corporativo/crear.html',
                           categorias=categorias, proveedores=proveedores)

# ============================================================================
# RUTAS DE INVENTARIO CORPORATIVO CON FILTROS
# ============================================================================
@app.route('/api/inventario-corporativo/estadisticas')
def api_estadisticas_inventario_corporativo():
    """API para obtener estadísticas del inventario corporativo"""
    if 'usuario_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401

    # ✅ SOLO admin, lider_inventario e inventario_corporativo pueden acceder
    rol = session.get('rol', '')
    if rol not in ['administrador', 'lider_inventario', 'inventario_corporativo']:
        return jsonify({'error': 'No tiene permisos para acceder a esta sección'}), 403

    try:
        # Obtener todos los productos CON información de oficina
        productos = InventarioCorporativoModel.obtener_todos_con_oficina() or []

        # Calcular estadísticas
        total_productos = len(productos)
        productos_sede = len([p for p in productos if p.get('oficina', 'Sede Principal') == 'Sede Principal'])
        productos_oficinas = total_productos - productos_sede

        return jsonify({
            'total_productos': total_productos,
            'productos_sede': productos_sede,
            'productos_oficinas': productos_oficinas
        })
    except Exception as e:
        print(f"❌ Error obteniendo estadísticas: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/inventario-corporativo/sede-principal')
def inventario_corporativo_sede_principal():
    """Vista filtrada para Sede Principal"""
    if 'usuario_id' not in session:
        return redirect('/login')

    # ✅ SOLO admin, lider_inventario e inventario_corporativo pueden acceder
    rol = session.get('rol', '')
    if rol not in ['administrador', 'lider_inventario', 'inventario_corporativo']:
        flash('No tiene permisos para acceder a esta sección', 'danger')
        return redirect('/dashboard')

    return listar_inventario_corporativo_filtrado('sede')

@app.route('/inventario-corporativo/oficinas-servicio')
def inventario_corporativo_oficinas_servicio():
    """Vista filtrada para Oficinas de Servicio (excluye Sede Principal)"""
    if 'usuario_id' not in session:
        return redirect('/login')

    # ✅ SOLO admin, lider_inventario e inventario_corporativo pueden acceder
    rol = session.get('rol', '')
    if rol not in ['administrador', 'lider_inventario', 'inventario_corporativo']:
        flash('No tiene permisos para acceder a esta sección', 'danger')
        return redirect('/dashboard')

    return listar_inventario_corporativo_filtrado('oficinas')

@app.route('/inventario-corporativo/filtrado/<tipo>')
def listar_inventario_corporativo_filtrado(tipo):
    """Vista principal con filtros para inventario corporativo"""
    if 'usuario_id' not in session:
        return redirect('/login')

    # ✅ SOLO admin, lider_inventario e inventario_corporativo pueden acceder
    rol = session.get('rol', '')
    if rol not in ['administrador', 'lider_inventario', 'inventario_corporativo']:
        flash('No tiene permisos para acceder a esta sección', 'danger')
        return redirect('/dashboard')

    try:
        # Obtener parámetros de filtro
        filtro_oficina = request.args.get('oficina', '')
        filtro_categoria = request.args.get('categoria', '')
        filtro_stock = request.args.get('stock', '')

        # Obtener todos los productos CON información de oficina
        productos = InventarioCorporativoModel.obtener_todos_con_oficina() or []

        # Obtener oficinas para el filtro
        oficinas_db = InventarioCorporativoModel.obtener_oficinas() or []

        if tipo == 'sede':
            # Solo productos de Sede Principal
            productos = [p for p in productos if p.get('oficina', 'Sede Principal') == 'Sede Principal']
            titulo = "Sede Principal"
            subtitulo = "Productos asignados a la sede principal"
            # Para sede principal, mostrar todas las oficinas en el filtro
            oficinas_filtradas = [{'nombre': 'Sede Principal'}] + [{'nombre': of['nombre']} for of in oficinas_db if of['nombre'] != 'Sede Principal']
        elif tipo == 'oficinas':
            # EXCLUIR SEDE PRINCIPAL - solo oficinas de servicio
            productos = [p for p in productos if p.get('oficina', 'Sede Principal') != 'Sede Principal']
            titulo = "Oficinas de Servicio"
            subtitulo = "Productos distribuidos en oficinas de servicio"
            # Para oficinas de servicio, excluir Sede Principal del filtro
            oficinas_filtradas = [{'nombre': of['nombre']} for of in oficinas_db if of['nombre'] != 'Sede Principal']
        else:
            titulo = "Inventario Corporativo"
            subtitulo = "Todos los productos corporativos"
            oficinas_filtradas = [{'nombre': 'Sede Principal'}] + [{'nombre': of['nombre']} for of in oficinas_db if of['nombre'] != 'Sede Principal']

        # Aplicar filtros adicionales
        productos_filtrados = productos.copy()

        if filtro_oficina:
            if filtro_oficina == 'Sede Principal':
                productos_filtrados = [p for p in productos_filtrados if p.get('oficina', 'Sede Principal') == 'Sede Principal']
            elif filtro_oficina == 'Oficinas de Servicio':
                productos_filtrados = [p for p in productos_filtrados if p.get('oficina', 'Sede Principal') != 'Sede Principal']
            else:
                productos_filtrados = [p for p in productos_filtrados if p.get('oficina', '') == filtro_oficina]

        if filtro_categoria:
            productos_filtrados = [p for p in productos_filtrados if p.get('categoria', '').lower() == filtro_categoria.lower()]

        if filtro_stock:
            if filtro_stock == 'bajo':
                productos_filtrados = [p for p in productos_filtrados if p.get('cantidad', 0) <= p.get('cantidad_minima', 5)]
            elif filtro_stock == 'normal':
                productos_filtrados = [p for p in productos_filtrados if p.get('cantidad', 0) > p.get('cantidad_minima', 5)]
            elif filtro_stock == 'sin':
                productos_filtrados = [p for p in productos_filtrados if p.get('cantidad', 0) == 0]

        # Calcular estadísticas
        total_productos = len(productos_filtrados)
        valor_total = sum(p.get('valor_unitario', 0) * p.get('cantidad', 0) for p in productos_filtrados)
        productos_bajo_stock = len([p for p in productos_filtrados if p.get('cantidad', 0) <= p.get('cantidad_minima', 5)])

        # Obtener categorías para el filtro
        categorias_db = InventarioCorporativoModel.obtener_categorias() or []
        categorias = [{'nombre': cat.get('nombre_categoria', '')} for cat in categorias_db]

        print(f"✅ Categorías cargadas: {len(categorias)}")
        print(f"✅ Oficinas cargadas: {len(oficinas_filtradas)}")
        print(f"✅ Productos cargados: {len(productos_filtrados)}")

        return render_template('inventario_corporativo/listar_con_filtros.html',
                            productos=productos_filtrados,
                            titulo=titulo,
                            subtitulo=subtitulo,
                            tipo=tipo,
                            total_productos=total_productos,
                            valor_total=valor_total,
                            productos_bajo_stock=productos_bajo_stock,
                            total_oficinas=len(oficinas_filtradas),
                            oficinas_filtradas=oficinas_filtradas,
                            categorias=categorias,
                            filtro_oficina=filtro_oficina,
                            filtro_categoria=filtro_categoria,
                            filtro_stock=filtro_stock)
                             
    except Exception as e:
        print(f"❌ Error cargando inventario corporativo: {e}")
        flash('Error al cargar el inventario corporativo', 'danger')
        return render_template('inventario_corporativo/listar_con_filtros.html',
                            productos=[],
                            titulo="Error",
                            subtitulo="No se pudieron cargar los productos",
                            tipo=tipo,
                            total_productos=0,
                            valor_total=0,
                            productos_bajo_stock=0,
                            total_oficinas=0,
                            oficinas_filtradas=[],
                            categorias=[],
                            filtro_oficina='',
                            filtro_categoria='',
                            filtro_stock='')

@app.route('/inventario-corporativo/exportar/excel/<tipo>')
def exportar_inventario_corporativo_excel(tipo):
    """Exportar inventario corporativo a Excel con filtros aplicados"""
    if 'usuario_id' not in session:
        return redirect('/login')

    # ✅ SOLO admin, lider_inventario e inventario_corporativo pueden acceder
    rol = session.get('rol', '')
    if rol not in ['administrador', 'lider_inventario', 'inventario_corporativo']:
        flash('No tiene permisos para acceder a esta sección', 'danger')
        return redirect('/dashboard')

    try:
        import pandas as pd
        from io import BytesIO
        from flask import send_file
        from datetime import datetime

        # Obtener parámetros de filtro
        filtro_oficina = request.args.get('oficina', '')
        filtro_categoria = request.args.get('categoria', '')
        filtro_stock = request.args.get('stock', '')

        # Obtener productos CON información de oficina
        productos = InventarioCorporativoModel.obtener_todos_con_oficina() or []

        # Aplicar filtro por tipo
        if tipo == 'sede':
            productos = [p for p in productos if p.get('oficina', 'Sede Principal') == 'Sede Principal']
            sheet_name = 'Sede Principal'
        elif tipo == 'oficinas':
            # EXCLUIR SEDE PRINCIPAL - solo oficinas de servicio
            productos = [p for p in productos if p.get('oficina', 'Sede Principal') != 'Sede Principal']
            sheet_name = 'Oficinas Servicio'
        else:
            sheet_name = 'Inventario Completo'

        # Aplicar filtros adicionales
        if filtro_oficina:
            if filtro_oficina == 'Sede Principal':
                productos = [p for p in productos if p.get('oficina', 'Sede Principal') == 'Sede Principal']
            elif filtro_oficina == 'Oficinas de Servicio':
                productos = [p for p in productos if p.get('oficina', 'Sede Principal') != 'Sede Principal']
            else:
                productos = [p for p in productos if p.get('oficina', '') == filtro_oficina]

        if filtro_categoria:
            productos = [p for p in productos if p.get('categoria', '').lower() == filtro_categoria.lower()]

        if filtro_stock:
            if filtro_stock == 'bajo':
                productos = [p for p in productos if p.get('cantidad', 0) <= p.get('cantidad_minima', 5)]
            elif filtro_stock == 'normal':
                productos = [p for p in productos if p.get('cantidad', 0) > p.get('cantidad_minima', 5)]
            elif filtro_stock == 'sin':
                productos = [p for p in productos if p.get('cantidad', 0) == 0]

        # Crear DataFrame
        data = []
        for producto in productos:
            data.append({
                'Código': producto.get('codigo_unico', ''),
                'Producto': producto.get('nombre', ''),
                'Descripción': producto.get('descripcion', ''),
                'Categoría': producto.get('categoria', ''),
                'Proveedor': producto.get('proveedor', ''),
                'Valor Unitario': producto.get('valor_unitario', 0),
                'Cantidad': producto.get('cantidad', 0),
                'Cantidad Mínima': producto.get('cantidad_minima', 0),
                'Ubicación': producto.get('ubicacion', ''),
                'Oficina': producto.get('oficina', 'Sede Principal'),
                'Asignable': 'Sí' if producto.get('es_asignable', False) else 'No',
                'Estado Stock': 'Bajo' if producto.get('cantidad', 0) <= producto.get('cantidad_minima', 5) else 'Normal' if producto.get('cantidad', 0) > 0 else 'Sin Stock'
            })

        df = pd.DataFrame(data)

        # Crear archivo Excel en memoria
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)

            # Ajustar ancho de columnas
            worksheet = writer.sheets[sheet_name]
            for idx, col in enumerate(df.columns):
                max_len = max(df[col].astype(str).str.len().max(), len(col)) + 2
                worksheet.column_dimensions[chr(65 + idx)].width = min(max_len, 50)

        output.seek(0)

        # Nombre del archivo
        filename = f"inventario_corporativo_{sheet_name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"

        return send_file(output, 
                        download_name=filename, 
                        as_attachment=True, 
                        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    except Exception as e:
        print(f"❌ Error exportando a Excel: {e}")
        flash('Error al exportar el archivo Excel', 'danger')
        return redirect(request.referrer or '/inventario-corporativo')

# ============================================================================
# API ENDPOINTS
# ============================================================================
@app.route('/api/material/<int:material_id>')
def api_material(material_id):
    if 'usuario_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    try:
        material = MaterialModel.obtener_por_id(material_id)
        if material and verificar_acceso_oficina(material.get('oficina_id')):
            return jsonify(material)
        else:
            return jsonify({'error': 'Material no encontrado o sin permisos'}), 404
    except Exception as e:
        print(f"❌ Error API material: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/api/material/<int:material_id>/stock', methods=['GET'])
def api_material_stock(material_id):
    if 'usuario_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    try:
        material = MaterialModel.obtener_por_id(material_id)
        if material and verificar_acceso_oficina(material.get('oficina_id')):
            return jsonify({
                'stock': material.get('cantidad', 0),
                'valor_unitario': material.get('valor_unitario', 0)
            })
        else:
            return jsonify({'error': 'Material no encontrado o sin permisos'}), 404
    except Exception as e:
        print(f"❌ Error API stock: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/api/oficina/<int:oficina_id>/materiales')
def api_oficina_materiales(oficina_id):
    if 'usuario_id' not in session:
        return jsonify({'error': 'No autorizado'}), 401
    try:
        # Verificar acceso a la oficina
        if not verificar_acceso_oficina(oficina_id):
            return jsonify({'error': 'No tiene permisos para acceder a esta oficina'}), 403

        materiales = MaterialModel.obtener_todos() or []
        materiales_oficina = [mat for mat in materiales if mat.get('oficina_id') == oficina_id]
        return jsonify(materiales_oficina)
    except Exception as e:
        print(f"❌ Error API oficina materiales: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

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

    # Verificar que existe el directorio de uploads
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
        print(f"✅ Creado directorio de uploads: {UPLOAD_FOLDER}")
    # Inicializar Sede Principal
    inicializar_oficina_principal()
    app.run(debug=True, host='0.0.0.0', port=5000)