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

# Importar blueprints con alias para consistencia
from routes_prestamos import bp_prestamos

from routes_inventario_corporativo import bp_inv as bp_inventario_corporativo

# Importar conexión a base de datos
from database import get_database_connection

# Configuración de la aplicación
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(32))
app.config['JSON_AS_ASCII'] = False

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

# Verificar que los blueprints estén registrados correctamente
print("✅ Blueprints registrados:")
for name in app.blueprints:
    print(f"   - {name}")

# Importar y registrar otras rutas si es necesario
# from routes_materiales import bp_materiales
# app.register_blueprint(bp_materiales)

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
# RUTAS DE AUTENTICACIÓN
# ============================================================================
@app.route('/')
def index():
    if 'usuario_id' in session:
        return redirect('/dashboard')
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'usuario_id' in session:
        return redirect('/dashboard')
    if request.method == 'POST':
        usuario = request.form['usuario']
        contraseña = request.form['contraseña']
        print(f"🔐 Intentando login para usuario: {usuario}")
        try:
            usuario_info = UsuarioModel.verificar_credenciales(usuario, contraseña)
            if usuario_info:
                session['usuario_id'] = usuario_info['id']
                session['usuario_nombre'] = usuario_info['nombre']
                session['usuario'] = usuario_info['usuario']
                session['rol'] = usuario_info['rol'].lower().strip()
                session['oficina_id'] = usuario_info.get('oficina_id', 1)
                session['oficina_nombre'] = usuario_info.get('oficina_nombre', 'Sede Principal')
                print(f"✅ Login exitoso: {usuario} - Rol: {usuario_info['rol']} - Oficina: {session['oficina_nombre']}")
                flash(f'¡Bienvenido {usuario_info["nombre"]}!', 'success')
                return redirect('/dashboard')
            else:
                print(f"❌ Login fallido para usuario: {usuario}")
                flash('Usuario o contraseña incorrectos', 'danger')
                return render_template('auth/login.html')
        except Exception as e:
            print(f"❌ Error durante login: {e}")
            flash('Error del sistema durante el login', 'danger')
            return render_template('auth/login.html')
    return render_template('auth/login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada correctamente', 'info')
    return redirect('/login')

@app.route('/dashboard')
def dashboard():
    if 'usuario_id' not in session:
        return redirect('/login')
    try:
        print("📊 Cargando dashboard...")
        materiales = []
        oficinas = []
        solicitudes = []
        aprobadores = []
        try:
            materiales = MaterialModel.obtener_todos() or []
            print(f"✅ Materiales cargados: {len(materiales)}")
        except Exception as e:
            print(f"⚠️ Error cargando materiales: {e}")
            materiales = []
        try:
            oficinas = OficinaModel.obtener_todas() or []
            print(f"✅ Oficinas cargadas: {len(oficinas)}")
        except Exception as e:
            print(f"⚠️ Error cargando oficinas: {e}")
            oficinas = []
        try:
            solicitudes = SolicitudModel.obtener_todas() or []
            print(f"✅ Solicitudes cargadas: {len(solicitudes)}")
        except Exception as e:
            print(f"⚠️ Error cargando solicitudes: {e}")
            solicitudes = []
        try:
            aprobadores = UsuarioModel.obtener_aprobadores() or []
            print(f"✅ Aprobadores cargados: {len(aprobadores)}")
        except Exception as e:
            print(f"⚠️ Error cargando aprobadores: {e}")
            aprobadores = []

        return render_template('dashboard.html',
                            materiales=materiales,
                            oficinas=oficinas,
                            solicitudes=solicitudes,
                            aprobadores=aprobadores)
    except Exception as e:
        print(f"❌ Error crítico en dashboard: {e}")
        flash('Error al cargar el dashboard', 'danger')
        return render_template('dashboard.html', 
                            materiales=[], 
                            oficinas=[], 
                            solicitudes=[],
                            aprobadores=[])

# ============================================================================
# RUTAS DE MATERIALES - ACTUALIZADO CON NUEVOS ROLES
# ============================================================================
@app.route('/materiales')
def listar_materiales():
    if 'usuario_id' not in session:
        return redirect('/login')
    
    # ✅ SOLO admin y lider_inventario pueden acceder
    rol = session.get('rol', '')
    if rol not in ['administrador', 'lider_inventario']:
        flash('No tiene permisos para acceder a esta sección', 'danger')
        return redirect('/dashboard')
        
    try:
        print("🔍 Cargando lista de materiales...")
        materiales = MaterialModel.obtener_todos() or []
        print(f"✅ Se cargaron {len(materiales)} materiales para mostrar")
        return render_template('materials/listar.html', materiales=materiales)
    except Exception as e:
        print(f"❌ Error obteniendo materiales: {e}")
        flash('Error al cargar los materiales', 'danger')
        return render_template('materials/listar.html', materiales=[])

@app.route('/materiales/crear', methods=['GET', 'POST'])
def crear_material():
    if 'usuario_id' not in session:
        return redirect('/login')
    
    # ✅ SOLO admin y lider_inventario pueden acceder
    rol = session.get('rol', '')
    if rol not in ['administrador', 'lider_inventario']:
        flash('No tiene permisos para acceder a esta sección', 'danger')
        return redirect('/dashboard')
    
    if request.method == 'GET':
        return render_template('materials/crear.html')
    
    # POST METHOD - SOLUCIÓN DEFINITIVA
    try:
        print("=== INICIANDO CREACIÓN DE MATERIAL ===")
        
        # Obtener oficina principal
        oficina_principal = OficinaModel.obtener_por_nombre("Sede Principal")
        if not oficina_principal:
            flash('No se encontró la oficina "Sede Principal"', 'danger')
            return render_template('materials/crear.html')      
        oficina_id = oficina_principal['id']
        errores = []
        materiales_creados = []
        
        for i in range(10):
            nombre_key = f'nombre_{i}'
            if nombre_key not in request.form or not request.form[nombre_key].strip():
                continue
                
            try:
                nombre = request.form.get(f'nombre_{i}', '').strip()
                valor_unitario = float(request.form.get(f'valor_unitario_{i}', 0.0))
                cantidad = int(request.form.get(f'cantidad_{i}', 0))
                imagen = request.files.get(f'imagen_{i}')
                
                print(f"🔍 Procesando material {i}: {nombre}")
                
                # Validaciones
                if not nombre:
                    errores.append(f"Material {i+1}: Nombre es obligatorio.")
                    continue
                if valor_unitario <= 0:
                    errores.append(f"Material {i+1} ({nombre}): Valor unitario debe ser mayor que 0.")
                    continue
                if cantidad <= 0:
                    errores.append(f"Material {i+1} ({nombre}): Cantidad debe ser mayor que 0.")
                    continue
                if not imagen or imagen.filename == '':
                    errores.append(f"Material {i+1} ({nombre}): Imagen es obligatoria.")
                    continue
                
                # Procesar imagen
                filename = secure_filename(imagen.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                
                # Verificar que el directorio existe
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                
                # Guardar la imagen
                imagen.save(filepath)
                print(f"✅ Imagen guardada en disco: {filepath}")
                
                # Ruta para la base de datos - CORREGIDO: usar ruta relativa correcta
                ruta_imagen = f"uploads/{filename}"
                print(f"✅ Ruta de imagen para BD: '{ruta_imagen}'")
                
                # Obtener usuario creador
                usuario_creador = session.get('usuario_nombre', 'Sistema')
                if not usuario_creador:
                    usuario_creador = session.get('usuario', 'Sistema')

                # ✅ CREACIÓN DIRECTA CON IMAGEN
                print("🔍 CREANDO MATERIAL CON IMAGEN...")
                material_id = MaterialModel.crear(
                    nombre=nombre,
                    valor_unitario=valor_unitario,
                    cantidad=cantidad,
                    oficina_id=oficina_id,
                    ruta_imagen=ruta_imagen,
                    usuario_creador=usuario_creador
                )

                if material_id:
                    print(f"✅ Material creado con ID: {material_id}")
                    
                    # ✅ VERIFICACIÓN INMEDIATA
                    material_verificado = MaterialModel.obtener_por_id(material_id)
                    if material_verificado:
                        if material_verificado['ruta_imagen']:
                            print(f"🎉 VERIFICACIÓN: Imagen guardada - '{material_verificado['ruta_imagen']}'")
                            materiales_creados.append(nombre)
                        else:
                            print(f"⚠️ ADVERTENCIA: Imagen no se guardó para material {material_id}")
                            # Intentar actualizar solo la imagen
                            print("🔄 Intentando actualizar solo la imagen...")
                            resultado_update = MaterialModel.actualizar_imagen(material_id, ruta_imagen)
                            if resultado_update:
                                print(f"✅ Imagen actualizada correctamente para material {material_id}")
                                materiales_creados.append(nombre)
                            else:
                                errores.append(f"Material {i+1} ({nombre}): Error al guardar imagen.")
                    else:
                        print(f"⚠️ No se pudo verificar material {material_id}")
                        errores.append(f"Material {i+1} ({nombre}): Error al verificar creación.")
                else:
                    print(f"❌ Error al crear material: {nombre}")
                    errores.append(f"Material {i+1} ({nombre}): Error en base de datos.")
                    
            except ValueError as ve:
                print(f"❌ Error de valor: {ve}")
                errores.append(f"Material {i+1}: Valores numéricos inválidos.")
            except Exception as e:
                print(f"❌ Error al crear material {i+1}: {e}")
                import traceback
                print(f"🔍 TRACEBACK: {traceback.format_exc()}")
                errores.append(f"Material {i+1} ({nombre or 'Desconocido'}): Error interno del sistema.")
        
        # Mostrar resultados
        if errores:
            for error in errores:
                flash(error, 'danger')
                
        if materiales_creados:
            flash(f'✅ ¡{len(materiales_creados)} material(es) creado(s) exitosamente!', 'success')
        
        return render_template('materials/crear.html')
        
    except Exception as e:
        print(f"❌ Error crítico en crear_material: {e}")
        import traceback
        print(f"🔍 TRACEBACK: {traceback.format_exc()}")
        flash('Error crítico del sistema.', 'danger')
        return render_template('materials/crear.html')

@app.route('/materiales/editar/<int:material_id>', methods=['GET', 'POST'])
def editar_material(material_id):
    if 'usuario_id' not in session:
        return redirect('/login')
    
    # ✅ SOLO admin y lider_inventario pueden acceder
    rol = session.get('rol', '')
    if rol not in ['administrador', 'lider_inventario']:
        flash('No tiene permisos para acceder a esta sección', 'danger')
        return redirect('/dashboard')
    
    try:
        if request.method == 'POST':
            print(f"🔍 Procesando edición del material {material_id}")
            
            # Obtener datos del formulario
            nombre = request.form.get('nombre')
            valor_unitario_str = request.form.get('valor_unitario', '0')
            cantidad_str = request.form.get('cantidad', '0')
            
            # Validar y convertir datos
            try:
                valor_unitario = float(valor_unitario_str)
                cantidad = int(cantidad_str)
            except ValueError:
                flash('Error: Los valores numéricos no son válidos', 'danger')
                return redirect(f'/materiales/editar/{material_id}')
            
            # Obtener material actual
            material_actual = MaterialModel.obtener_por_id(material_id)
            if not material_actual:
                flash('Material no encontrado', 'danger')
                return redirect('/materiales')
                
            oficina_id = material_actual['oficina_id']
            imagen = request.files.get('imagen')
            ruta_imagen = material_actual['ruta_imagen']
            
            # Procesar nueva imagen si se proporciona
            if imagen and imagen.filename != '':
                try:
                    filename = secure_filename(imagen.filename)
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    imagen.save(filepath)
                    ruta_imagen = f"uploads/{filename}"
                    print(f"✅ Nueva imagen guardada: {ruta_imagen}")
                except Exception as e:
                    print(f"❌ Error guardando nueva imagen: {e}")
                    flash('Error al guardar la nueva imagen', 'danger')
                    return redirect(f'/materiales/editar/{material_id}')
            
            # Actualizar material
            resultado = MaterialModel.actualizar(
                material_id=material_id,
                nombre=nombre,
                valor_unitario=valor_unitario,
                cantidad=cantidad,
                oficina_id=oficina_id,
                ruta_imagen=ruta_imagen
            )
            
            if resultado:
                flash('Material actualizado exitosamente', 'success')
                return redirect('/materiales')
            else:
                flash('Error al actualizar el material', 'danger')
                return redirect(f'/materiales/editar/{material_id}')
        
        # GET request - mostrar formulario de edición
        print(f"🔍 Cargando formulario de edición para material {material_id}")
        material = MaterialModel.obtener_por_id(material_id)
        
        if not material:
            flash('Material no encontrado', 'danger')
            return redirect('/materiales')
        
        print(f"✅ Material cargado: {material['nombre']}")
        return render_template('materials/editar.html', material=material)
        
    except Exception as e:
        print(f"❌ Error en editar_material: {e}")
        import traceback
        print(f"🔍 TRACEBACK: {traceback.format_exc()}")
        flash('Error al procesar la solicitud', 'danger')
        return redirect('/materiales')

@app.route('/materiales/eliminar/<int:material_id>', methods=['POST'])
def eliminar_material(material_id):
    if 'usuario_id' not in session:
        return redirect('/login')
    
    # ✅ SOLO admin y lider_inventario pueden acceder
    rol = session.get('rol', '')
    if rol not in ['administrador', 'lider_inventario']:
        flash('No tiene permisos para acceder a esta sección', 'danger')
        return redirect('/dashboard')
        
    try:
        resultado = MaterialModel.eliminar(material_id)
        if resultado:
            flash('Material eliminado exitosamente', 'success')
        else:
            flash('Error al eliminar el material', 'danger')
    except Exception as e:
        print(f"❌ Error eliminando material: {e}")
        flash('Error al eliminar el material', 'danger')
    return redirect('/materiales')

# ============================================== 
# RUTAS DE OFICINAS - ACTUALIZADO CON NUEVOS ROLES
# ============================================== 
@app.route('/oficinas')
def listar_oficinas():
    if 'usuario_id' not in session:
        return redirect('/login')
    
    # ✅ SOLO admin, lider_inventario y oficina_principal
    rol = session.get('rol', '')
    if rol not in ['administrador', 'lider_inventario', 'oficina_principal']:
        flash('No tiene permisos para acceder a esta sección', 'danger')
        return redirect('/dashboard')
    
    try:
        oficinas = OficinaModel.obtener_todas() or []
        return render_template('oficinas/listar.html', oficinas=oficinas)
    except Exception as e:
        print(f"❌ Error obteniendo oficinas: {e}")
        flash('Error al cargar las oficinas', 'danger')
        return render_template('oficinas/listar.html', oficinas=[])

@app.route('/oficina/detalle/<int:oficina_id>')
def detalle_oficina(oficina_id):
    if 'usuario_id' not in session:
        return redirect('/login')
    
    # Verificar acceso a la oficina
    if not verificar_acceso_oficina(oficina_id):
        flash('No tiene permisos para acceder a esta oficina', 'danger')
        return redirect('/oficinas')
        
    try:
        oficina = OficinaModel.obtener_por_id(oficina_id)
        if not oficina:
            flash('Oficina no encontrada', 'danger')
            return redirect('/oficinas')
        
        # Obtener y filtrar datos por oficina
        todos_materiales = MaterialModel.obtener_todos() or []
        todas_solicitudes = SolicitudModel.obtener_todas() or []
        
        materiales_oficina = filtrar_por_oficina_usuario(todos_materiales, 'oficina_id')
        solicitudes_oficina = filtrar_por_oficina_usuario(todas_solicitudes, 'oficina_id')
        
        return render_template('oficinas/detalle.html',
                            oficina=oficina,
                            materiales=materiales_oficina,
                            solicitudes=solicitudes_oficina)
    except Exception as e:
        print(f"❌ Error cargando detalle de oficina: {e}")
        flash('Error al cargar el detalle de la oficina', 'danger')
        return redirect('/oficinas')

# ============================================================================
# RUTAS DE SOLICITUDES - ACTUALIZADO CON NUEVOS ROLES
# ============================================================================
@app.route('/solicitudes')
def listar_solicitudes():
    if 'usuario_id' not in session:
        return redirect('/login')
    
    # ✅ Todos EXCEPTO tesoreria
    rol = session.get('rol', '')
    if rol == 'tesoreria':
        flash('No tiene permisos para acceder a esta sección', 'danger')
        return redirect('/reportes')
    
    try:
        # Obtener TODAS las solicitudes sin filtrar aún
        todas_solicitudes = SolicitudModel.obtener_todas() or []
        
        # ✅ CORRECCIÓN CLAVE: Solo filtrar si NO es administrador ni lider_inventario
        if rol in ['administrador', 'lider_inventario']:
            solicitudes = todas_solicitudes  # Acceso total
        else:
            solicitudes = filtrar_por_oficina_usuario(todas_solicitudes, 'oficina_id')

        # Obtener materiales y oficinas (sin filtrar para admin)
        todos_materiales = MaterialModel.obtener_todos() or []
        if rol in ['administrador', 'lider_inventario']:
            materiales = todos_materiales
        else:
            materiales = filtrar_por_oficina_usuario(todos_materiales, 'oficina_id')
        materiales_dict = {mat['id']: mat for mat in materiales}

        # Oficinas únicas para filtro
        todas_oficinas = OficinaModel.obtener_todas() or []
        if rol in ['administrador', 'lider_inventario']:
            oficinas_filtradas = todas_oficinas
        else:
            oficinas_filtradas = filtrar_por_oficina_usuario(todas_oficinas)
        oficinas_unique = list({oficina['nombre'] for oficina in oficinas_filtradas if oficina.get('nombre')})

        # Estadísticas
        total_solicitudes = len(solicitudes)
        solicitudes_pendientes = len([s for s in solicitudes if s.get('estado', '').lower() == 'pendiente'])
        solicitudes_aprobadas = len([s for s in solicitudes if s.get('estado', '').lower() == 'aprobada'])
        solicitudes_rechazadas = len([s for s in solicitudes if s.get('estado', '').lower() == 'rechazada'])

        # Filtros desde URL
        filtro_estado = request.args.get('estado', 'todos')
        filtro_oficina = request.args.get('oficina', 'todas')

        # Aplicar filtros
        solicitudes_filtradas = solicitudes.copy()
        if filtro_estado != 'todos':
            solicitudes_filtradas = [s for s in solicitudes_filtradas if s.get('estado', '').lower() == filtro_estado.lower()]
        if filtro_oficina != 'todas':
            solicitudes_filtradas = [s for s in solicitudes_filtradas if s.get('oficina_nombre', '') == filtro_oficina]

        return render_template('solicitudes/solicitudes.html',
                             solicitudes=solicitudes_filtradas,
                             materiales_dict=materiales_dict,
                             oficinas_unique=oficinas_unique,
                             total_solicitudes=total_solicitudes,
                             solicitudes_pendientes=solicitudes_pendientes,
                             solicitudes_aprobadas=solicitudes_aprobadas,
                             solicitudes_rechazadas=solicitudes_rechazadas,
                             filtro_estado=filtro_estado,
                             filtro_oficina=filtro_oficina)
                             
    except Exception as e:
        print(f"❌ Error obteniendo solicitudes: {e}")
        flash('Error al cargar las solicitudes', 'danger')
        return render_template('solicitudes/solicitudes.html', 
                             solicitudes=[],
                             materiales_dict={},
                             oficinas_unique=[],
                             total_solicitudes=0,
                             solicitudes_pendientes=0,
                             solicitudes_aprobadas=0,
                             solicitudes_rechazadas=0,
                             filtro_estado='todos',
                             filtro_oficina='todas')

@app.route('/solicitudes/crear', methods=['GET'])
def mostrar_formulario_solicitud():
    """Muestra el formulario para crear solicitud"""
    if 'usuario_id' not in session:
        return redirect('/login')
    
    # ✅ Todos EXCEPTO tesoreria
    rol = session.get('rol', '')
    if rol == 'tesoreria':
        flash('No tiene permisos para acceder a esta sección', 'danger')
        return redirect('/reportes')
        
    print("Mostrando formulario de creación (GET)")
    try:
        # ✅ CORRECCIÓN: Obtener TODOS los materiales sin filtrar por oficina
        materiales = MaterialModel.obtener_todos() or []
        
        print(f"✅ Materiales cargados para formulario: {len(materiales)}")
        
        return render_template('solicitudes/crear.html', 
                             materiales=materiales)
    except Exception as e:
        print(f"Error al cargar formulario: {e}")
        flash('Error al cargar el formulario', 'error')
        return redirect('/solicitudes')

@app.route('/solicitudes/crear', methods=['POST'])
def procesar_solicitud():
    """Procesa el formulario de creación de solicitud usando el SP"""
    if 'usuario_id' not in session:
        return redirect('/login')
    
    # ✅ Todos EXCEPTO tesoreria
    rol = session.get('rol', '')
    if rol == 'tesoreria':
        flash('No tiene permisos para acceder a esta sección', 'danger')
        return redirect('/reportes')
    
    print("Procesando formulario (POST)")
    try:
        oficina_id = request.form.get('oficina_id')
        material_id = request.form.get('material_id')
        cantidad_solicitada = request.form.get('cantidad_solicitada')
        porcentaje_oficina = request.form.get('porcentaje_oficina')
        observacion = request.form.get('observacion', '').strip()  # ✅ Obtener y limpiar

        # ✅ VALIDACIÓN ACTUALIZADA - OBSERVACIÓN OBLIGATORIA
        if not all([oficina_id, material_id, cantidad_solicitada, porcentaje_oficina, observacion]):
            flash('Todos los campos son obligatorios, incluyendo la observación', 'error')
            return redirect('/solicitudes/crear')

        # ✅ VALIDACIÓN ADICIONAL PARA OBSERVACIÓN NO VACÍA
        if not observacion:
            flash('La observación es obligatoria', 'error')
            return redirect('/solicitudes/crear')

        # ✅ VALIDACIÓN DE MÍNIMO 15 CARACTERES
        if len(observacion) < 15:
            flash('La observación debe tener al menos 15 caracteres', 'error')
            return redirect('/solicitudes/crear')

        oficina_id = int(oficina_id)
        material_id = int(material_id)
        cantidad_solicitada = int(cantidad_solicitada)
        porcentaje_oficina = float(porcentaje_oficina)

        # ✅ VALIDACIÓN DEL PORCENTAJE (1-100)
        if porcentaje_oficina < 1 or porcentaje_oficina > 100:
            flash('El porcentaje debe estar entre 1% y 100%', 'error')
            return redirect('/solicitudes/crear')

        # Verificar acceso a la oficina
        if not verificar_acceso_oficina(oficina_id):
            flash('No tiene permisos para crear solicitudes para esta oficina', 'error')
            return redirect('/solicitudes/crear')

        usuario_nombre = session.get('usuario_nombre', 'Sistema')
        if not usuario_nombre:
            flash('Debe iniciar sesión', 'error')
            return redirect('/login')

        # Crear la solicitud CON OBSERVACIÓN
        solicitud_id = SolicitudModel.crear(
            oficina_id=oficina_id,
            material_id=material_id,
            cantidad_solicitada=cantidad_solicitada,
            porcentaje_oficina=porcentaje_oficina,
            usuario_nombre=usuario_nombre,
            observacion=observacion  # ✅ NUEVO PARÁMETRO
        )

        if solicitud_id:
            flash('Solicitud creada exitosamente! ID: ' + str(solicitud_id), 'success')
            return redirect('/solicitudes/crear')
        else:
            flash('Error al crear la solicitud', 'error')
            return redirect('/solicitudes/crear')

    except Exception as e:
        print(f"ERROR en crear_solicitud: {e}")
        error_msg = str(e)
        
        # Manejar errores específicos del stored procedure
        if 'Límite mensual' in error_msg:
            flash('Límite mensual de 1000 elementos excedido para esta oficina. No puede crear más solicitudes este mes.', 'error')
        elif 'Stock insuficiente' in error_msg or 'excede el inventario' in error_msg:
            flash('Stock insuficiente para completar la solicitud. Verifique la cantidad disponible.', 'error')
        elif 'Cantidad solicitada' in error_msg:
            flash('La cantidad solicitada no es válida. Verifique los límites.', 'error')
        else:
            flash('Error interno del servidor: ' + error_msg, 'error')
        
        return redirect('/solicitudes/crear')

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
# RUTAS DE APROBADORES - ACTUALIZADO CON NUEVOS ROLES
# ============================================================================
@app.route('/aprobadores')
def listar_aprobadores():
    if 'usuario_id' not in session:
        return redirect('/login')
    
    # ✅ SOLO admin, lider_inventario y oficina_principal
    rol = session.get('rol', '')
    if rol not in ['administrador', 'lider_inventario', 'oficina_principal']:
        flash('No tiene permisos para acceder a esta sección', 'danger')
        return redirect('/dashboard')
    
    try:
        aprobadores = UsuarioModel.obtener_aprobadores() or []
        return render_template('aprobadores/listar.html', aprobadores=aprobadores)
    except Exception as e:
        print(f"❌ Error obteniendo aprobadores: {e}")
        flash('Error al cargar los aprobadores', 'danger')
        return render_template('aprobadores/listar.html', aprobadores=[])

# ===================== Inventario Corporativo =====================

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

            # Crear en BD usando TU modelo (ya implementado)
            # INSERT INTO ProductosCorporativos (...) VALUES (...)  -> lastrowid
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
            )  # devuelve id o None. :contentReference[oaicite:2]{index=2}

            if nuevo_id:
                flash('✅ Producto corporativo creado correctamente.', 'success')
                return redirect('/inventario-corporativo')
            else:
                flash('❌ No fue posible crear el producto.', 'danger')

        except Exception as e:
            print(f"[POST /inventario-corporativo/crear] Error: {e}")
            flash('❌ Ocurrió un error al guardar.', 'danger')

        # Si algo falla, re-renderizamos el formulario con las listas
        return render_template('inventario_corporativo/crear.html',
                               categorias=categorias, proveedores=proveedores)

    # GET → solo pintar formulario con listas
    return render_template('inventario_corporativo/crear.html',
                           categorias=categorias, proveedores=proveedores)

 
# ============================================================================
# RUTAS DE INVENTARIO CORPORATIVO CON FILTROS
# ============================================================================

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
        
        # Obtener categorías para el filtro - CORREGIDO
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
# RUTAS DE REPORTES (MODIFICADAS CON FILTROS POR OFICINA)
# ============================================================================
@app.route('/reportes')
def reportes_index():
    if 'usuario_id' not in session:
        return redirect('/login')
    try:
        # Obtener todos los datos primero
        todas_solicitudes = SolicitudModel.obtener_todas() or []
        todos_materiales = MaterialModel.obtener_todos() or []
        todas_oficinas = OficinaModel.obtener_todas() or []
        
        # Aplicar filtros por oficina según el rol
        solicitudes = filtrar_por_oficina_usuario(todas_solicitudes, 'oficina_id')
        materiales = filtrar_por_oficina_usuario(todos_materiales, 'oficina_id')
        oficinas = filtrar_por_oficina_usuario(todas_oficinas)
        
        # Calcular estadísticas con datos filtrados
        total_solicitudes = len(solicitudes)
        solicitudes_pendientes = len([s for s in solicitudes if s.get('estado', '').lower() == 'pendiente'])
        solicitudes_aprobadas = len([s for s in solicitudes if s.get('estado', '').lower() == 'aprobada'])
        solicitudes_rechazadas = len([s for s in solicitudes if s.get('estado', '').lower() == 'rechazada'])
        
        materiales_bajo_stock = len([m for m in materiales if m.get('cantidad', 0) <= 10])
        valor_total_inventario = sum(m.get('valor_total', 0) or 0 for m in materiales)
        total_oficinas = len(oficinas)
        
        return render_template('reportes/index.html',
                            total_solicitudes=total_solicitudes,
                            solicitudes_pendientes=solicitudes_pendientes,
                            solicitudes_aprobadas=solicitudes_aprobadas,
                            solicitudes_rechazadas=solicitudes_rechazadas,
                            materiales_bajo_stock=materiales_bajo_stock,
                            valor_total_inventario=valor_total_inventario,
                            total_oficinas=total_oficinas)
    except Exception as e:
        print(f"❌ Error cargando reportes: {e}")
        return render_template('reportes/index.html',
                            total_solicitudes=0,
                            solicitudes_pendientes=0,
                            solicitudes_aprobadas=0,
                            solicitudes_rechazadas=0,
                            materiales_bajo_stock=0,
                            valor_total_inventario=0,
                            total_oficinas=0)

@app.route('/reportes/materiales')
def reporte_materiales():
    if 'usuario_id' not in session:
        return redirect('/login')
    try:
        # Obtener y filtrar materiales
        todos_materiales = MaterialModel.obtener_todos() or []
        materiales = filtrar_por_oficina_usuario(todos_materiales, 'oficina_id')
        
        # Obtener y filtrar solicitudes para estadísticas
        todas_solicitudes = SolicitudModel.obtener_todas() or []
        solicitudes_filtradas = filtrar_por_oficina_usuario(todas_solicitudes, 'oficina_id')
        
        # Calcular estadísticas con datos filtrados
        valor_total_inventario = sum(m.get('valor_total', 0) or 0 for m in materiales)
        total_solicitudes = len(solicitudes_filtradas)
        total_entregado = sum((m.get('cantidad', 0) or 0) for m in materiales)
        
        # Crear stats_dict con datos filtrados
        stats_dict = {}
        for material in materiales:
            material_id = material['id']
            solicitudes_mat = [s for s in solicitudes_filtradas if s.get('material_id') == material_id]
            
            total_sol = len(solicitudes_mat)
            aprobadas = len([s for s in solicitudes_mat if s.get('estado', '').lower() == 'aprobada'])
            pendientes = len([s for s in solicitudes_mat if s.get('estado', '').lower() == 'pendiente'])
            entregado = sum((s.get('cantidad_solicitada', 0) or 0) for s in solicitudes_mat if s.get('estado', '').lower() == 'aprobada')
            
            stats_dict[material_id] = [total_sol, aprobadas, pendientes, entregado, 0, 0, 0]
        
        return render_template('reportes/materiales.html',
                             materiales=materiales,
                             valor_total_inventario=valor_total_inventario,
                             total_solicitudes=total_solicitudes,
                             total_entregado=total_entregado,
                             stats_dict=stats_dict)
    except Exception as e:
        print(f"❌ Error generando reporte de materiales: {e}")
        flash('Error al generar el reporte de materiales', 'danger')
        return render_template('reportes/materiales.html',
                             materiales=[],
                             valor_total_inventario=0,
                             total_solicitudes=0,
                             total_entregado=0,
                             stats_dict={})

@app.route('/reportes/materiales/exportar/excel')
def exportar_materiales_excel():
    if 'usuario_id' not in session:
        return redirect('/login')
    try:
        import pandas as pd
        from io import BytesIO
        from flask import send_file
        
        # Obtener y filtrar materiales
        todos_materiales = MaterialModel.obtener_todos() or []
        materiales = filtrar_por_oficina_usuario(todos_materiales, 'oficina_id')
        
        # Crear DataFrame solo con materiales filtrados
        data = []
        for mat in materiales:
            data.append({
                'ID': mat.get('id', ''),
                'Nombre': mat.get('nombre', ''),
                'Valor Unitario': mat.get('valor_unitario', 0),
                'Cantidad': mat.get('cantidad', 0),
                'Valor Total': mat.get('valor_total', 0),
                'Oficina': mat.get('oficina_nombre', ''),
                'Creado por': mat.get('usuario_creador', ''),
                'Fecha Creación': mat.get('fecha_creacion', '')
            })
        
        df = pd.DataFrame(data)
        
        # Crear archivo Excel en memoria
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Materiales', index=False)
            
            # Formatear columnas
            workbook = writer.book
            worksheet = writer.sheets['Materiales']
            
            # Ajustar ancho de columnas
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = (max_length + 2)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        output.seek(0)
        
        # Enviar archivo
        fecha_actual = pd.Timestamp.now().strftime('%Y-%m-%d')
        filename = f'reporte_materiales_{fecha_actual}.xlsx'
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        print(f"❌ Error exportando materiales a Excel: {e}")
        flash('Error al exportar el reporte de materiales a Excel', 'danger')
        return redirect('/reportes/materiales')

@app.route('/reportes/inventario')
def reporte_inventario():
    if 'usuario_id' not in session:
        return redirect('/login')
    try:
        # Obtener y filtrar materiales
        todos_materiales = MaterialModel.obtener_todos() or []
        materiales = filtrar_por_oficina_usuario(todos_materiales, 'oficina_id')
        
        # Filtrar con valores por defecto
        materiales_bajo_stock = [m for m in materiales if (m.get('cantidad', 0) or 0) <= 10]
        materiales_stock_normal = [m for m in materiales if (m.get('cantidad', 0) or 0) > 10]
        materiales_sin_stock = [m for m in materiales if (m.get('cantidad', 0) or 0) == 0]
        
        # Calcular valores con seguridad
        valor_bajo_stock = sum((m.get('valor_total', 0) or 0) for m in materiales_bajo_stock)
        valor_stock_normal = sum((m.get('valor_total', 0) or 0) for m in materiales_stock_normal)
        valor_total = sum((m.get('valor_total', 0) or 0) for m in materiales)
        cantidad_total = sum((m.get('cantidad', 0) or 0) for m in materiales)
        
        return render_template('reportes/inventario.html',
                            materiales=materiales,
                            materiales_bajo_stock=materiales_bajo_stock,
                            materiales_stock_normal=materiales_stock_normal,
                            materiales_sin_stock=materiales_sin_stock,
                            valor_bajo_stock=valor_bajo_stock,
                            valor_stock_normal=valor_stock_normal,
                            valor_total=valor_total,
                            cantidad_total=cantidad_total)
    except Exception as e:
        print(f"❌ Error generando reporte de inventario: {e}")
        flash('Error al generar el reporte de inventario', 'danger')
        return render_template('reportes/inventario.html',
                            materiales=[],
                            materiales_bajo_stock=[],
                            materiales_stock_normal=[],
                            materiales_sin_stock=[],
                            valor_bajo_stock=0,
                            valor_stock_normal=0,
                            valor_total=0,
                            cantidad_total=0)

@app.route('/reportes/inventario/exportar/excel')
def exportar_inventario_excel():
    if 'usuario_id' not in session:
        return redirect('/login')
    try:
        import pandas as pd
        from io import BytesIO
        from flask import send_file
        
        # Obtener y filtrar materiales
        todos_materiales = MaterialModel.obtener_todos() or []
        materiales = filtrar_por_oficina_usuario(todos_materiales, 'oficina_id')
        
        # Crear DataFrame para inventario
        data = []
        for mat in materiales:
            estado_stock = "Normal"
            if mat.get('cantidad', 0) == 0:
                estado_stock = "Sin Stock"
            elif mat.get('cantidad', 0) <= 10:
                estado_stock = "Bajo Stock"
                
            data.append({
                'ID': mat.get('id', ''),
                'Nombre': mat.get('nombre', ''),
                'Cantidad': mat.get('cantidad', 0),
                'Valor Unitario': mat.get('valor_unitario', 0),
                'Valor Total': mat.get('valor_total', 0),
                'Estado Stock': estado_stock,
                'Oficina': mat.get('oficina_nombre', ''),
                'Última Actualización': mat.get('fecha_actualizacion', '')
            })
        
        df = pd.DataFrame(data)
        
        # Crear archivo Excel en memoria
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Inventario', index=False)
            
            # Formatear columnas
            workbook = writer.book
            worksheet = writer.sheets['Inventario']
            
            # Ajustar ancho de columnas
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = (max_length + 2)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        output.seek(0)
        
        # Enviar archivo
        fecha_actual = pd.Timestamp.now().strftime('%Y-%m-%d')
        filename = f'reporte_inventario_{fecha_actual}.xlsx'
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        print(f"❌ Error exportando inventario a Excel: {e}")
        flash('Error al exportar el reporte de inventario a Excel', 'danger')
        return redirect('/reportes/inventario')

@app.route('/reportes/solicitudes')
def reporte_solicitudes():
    if 'usuario_id' not in session:
        return redirect('/login')
    try:
        # Obtener y filtrar datos
        todas_solicitudes = SolicitudModel.obtener_todas() or []
        todos_materiales = MaterialModel.obtener_todos() or []
        todas_oficinas = OficinaModel.obtener_todas() or []
        
        solicitudes = filtrar_por_oficina_usuario(todas_solicitudes, 'oficina_id')
        materiales = filtrar_por_oficina_usuario(todos_materiales, 'oficina_id')
        oficinas_filtradas = filtrar_por_oficina_usuario(todas_oficinas)
        
        # Crear diccionario de materiales para imágenes
        materiales_dict = {mat['id']: mat for mat in materiales}
        
        # Obtener oficinas únicas para el filtro (solo las permitidas)
        oficinas_unique = list(set([oficina['nombre'] for oficina in oficinas_filtradas if oficina.get('nombre')]))
        
        # Obtener filtros de la URL
        filtro_estado = request.args.get('estado', 'todos')
        filtro_oficina = request.args.get('oficina', 'todas')
        filtro_material = request.args.get('material', '').lower()
        filtro_solicitante = request.args.get('solicitante', '').lower()
        
        # Aplicar filtros a las solicitudes
        solicitudes_filtradas = solicitudes.copy()
        
        if filtro_estado != 'todos':
            solicitudes_filtradas = [s for s in solicitudes_filtradas if s.get('estado', '').lower() == filtro_estado.lower()]
        
        if filtro_oficina != 'todas':
            solicitudes_filtradas = [s for s in solicitudes_filtradas if s.get('oficina_nombre', '') == filtro_oficina]
        
        if filtro_material:
            solicitudes_filtradas = [s for s in solicitudes_filtradas if filtro_material in s.get('material_nombre', '').lower()]
        
        if filtro_solicitante:
            solicitudes_filtradas = [s for s in solicitudes_filtradas if filtro_solicitante in s.get('usuario_solicitante', '').lower()]
        
        # Calcular estadísticas con las solicitudes FILTRADAS
        total_solicitudes = len(solicitudes_filtradas)
        solicitudes_pendientes = len([s for s in solicitudes_filtradas if s.get('estado', '').lower() == 'pendiente'])
        solicitudes_aprobadas = len([s for s in solicitudes_filtradas if s.get('estado', '').lower() == 'aprobada'])
        solicitudes_rechazadas = len([s for s in solicitudes_filtradas if s.get('estado', '').lower() == 'rechazada'])
        
        return render_template('reportes/solicitudes.html',
                             solicitudes=solicitudes_filtradas,
                             materiales_dict=materiales_dict,
                             oficinas_unique=oficinas_unique,
                             total_solicitudes=total_solicitudes,
                             solicitudes_pendientes=solicitudes_pendientes,
                             solicitudes_aprobadas=solicitudes_aprobadas,
                             solicitudes_rechazadas=solicitudes_rechazadas,
                             filtro_estado=filtro_estado,
                             filtro_oficina=filtro_oficina)
    except Exception as e:
        print(f"❌ Error generando reporte de solicitudes: {e}")
        flash('Error al generar el reporte de solicitudes', 'danger')
        return render_template('reportes/solicitudes.html',
                             solicitudes=[],
                             materiales_dict={},
                             oficinas_unique=[],
                             total_solicitudes=0,
                             solicitudes_pendientes=0,
                             solicitudes_aprobadas=0,
                             solicitudes_rechazadas=0,
                             filtro_estado='todos',
                             filtro_oficina='todas')

@app.route('/reportes/solicitudes/exportar/excel')
def exportar_solicitudes_excel():
    if 'usuario_id' not in session:
        return redirect('/login')
    try:
        import pandas as pd
        from io import BytesIO
        from flask import send_file
        
        # Obtener y filtrar solicitudes
        todas_solicitudes = SolicitudModel.obtener_todas() or []
        solicitudes = filtrar_por_oficina_usuario(todas_solicitudes, 'oficina_id')
        
        # Crear DataFrame solo con solicitudes filtradas
        data = []
        for sol in solicitudes:
            data.append({
                'ID': sol.get('id', ''),
                'Material': sol.get('material_nombre', ''),
                'Oficina': sol.get('oficina_nombre', ''),
                'Cantidad Solicitada': sol.get('cantidad_solicitada', 0),
                'Cantidad Aprobada': sol.get('cantidad_aprobada', 0),
                'Estado': sol.get('estado', ''),
                'Valor Solicitado': sol.get('valor_total_solicitado', 0),
                'Valor Aprobado': sol.get('valor_total_aprobado', 0),
                'Solicitante': sol.get('usuario_solicitante', ''),
                'Fecha Solicitud': sol.get('fecha_solicitud', ''),
                'Fecha Aprobación': sol.get('fecha_aprobacion', ''),
                'Aprobador': sol.get('usuario_aprobador', ''),
                'Observaciones': sol.get('observacion', '')
            })
        
        df = pd.DataFrame(data)
        
        # Crear archivo Excel en memoria
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Solicitudes', index=False)
            
            # Formatear columnas
            workbook = writer.book
            worksheet = writer.sheets['Solicitudes']
            
            # Ajustar ancho de columnas
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = (max_length + 2)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        output.seek(0)
        
        # Enviar archivo
        fecha_actual = pd.Timestamp.now().strftime('%Y-%m-%d')
        filename = f'reporte_solicitudes_{fecha_actual}.xlsx'
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        print(f"❌ Error exportando a Excel: {e}")
        flash('Error al exportar el reporte a Excel', 'danger')
        return redirect('/reportes/solicitudes')

@app.route('/reportes/material/<int:id>')
def reporte_material_detalle(id):
    if 'usuario_id' not in session:
        return redirect('/login')
    try:
        material = MaterialModel.obtener_por_id(id)
        if not material:
            flash('Material no encontrado', 'danger')
            return redirect('/reportes/materiales')
        
        # Verificar acceso al material
        if not verificar_acceso_oficina(material.get('oficina_id')):
            flash('No tiene permisos para acceder a este material', 'danger')
            return redirect('/reportes/materiales')
        
        # Obtener el nombre de la oficina
        oficina = OficinaModel.obtener_por_id(material.get('oficina_id', 1))
        oficina_nombre = oficina.get('nombre', 'Sede Principal') if oficina else 'Sede Principal'
        
        # Agregar nombre de oficina al material
        material['oficina_nombre'] = oficina_nombre
        
        # Obtener todas las solicitudes para este material (filtradas por oficina)
        
        # Obtener todas las solicitudes
        todas_solicitudes = SolicitudModel.obtener_todas() or []

        # ✅ Solo filtrar si NO es administrador ni lider_inventario
        if session.get('rol') in ['administrador', 'lider_inventario']:
            solicitudes = todas_solicitudes
        else:
            solicitudes = filtrar_por_oficina_usuario(todas_solicitudes, 'oficina_id')
        solicitudes_filtradas = filtrar_por_oficina_usuario(todas_solicitudes, 'oficina_id')
        solicitudes_material = [s for s in solicitudes_filtradas if s.get('material_id') == id]
        
        total_solicitudes = len(solicitudes_material)
        solicitudes_aprobadas = len([s for s in solicitudes_material if s.get('estado', '').lower() == 'aprobada'])
        
        return render_template('reportes/material_detalle.html',
                         material=material,
                         solicitudes=solicitudes_material,
                         total_solicitudes=total_solicitudes,
                         solicitudes_aprobadas=solicitudes_aprobadas)
    except Exception as e:
        print(f"❌ Error cargando detalle de material: {e}")
        flash('Error al cargar el detalle del material', 'danger')
        return redirect('/reportes/materiales')

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
    
    app.run(debug=True, host='0.0.0.0', port=5000)