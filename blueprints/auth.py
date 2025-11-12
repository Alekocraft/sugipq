# blueprints/auth.py
from flask import Blueprint, render_template, request, redirect, session, flash
from models.usuarios_model import UsuarioModel

# ✅ CAMBIO CRÍTICO: Agregar url_prefix para mantener URLs originales
auth_bp = Blueprint('auth', __name__, url_prefix='')

# ✅ Nueva función: Asignar rol según la oficina
def assign_role_by_office(office_name):
    """
    Devuelve el rol asignado según el nombre de la oficina.
    """
    office_name = office_name.lower().strip() if office_name else ''
    
    if 'gerencia' in office_name:
        return 'admin'
    elif 'almacén' in office_name or 'logística' in office_name:
        return 'almacen'
    elif 'finanzas' in office_name or 'contabilidad' in office_name:
        return 'finanzas'
    elif 'rrhh' in office_name or 'recursos humanos' in office_name:
        return 'rrhh'
    else:
        return 'usuario'  # Rol por defecto

@auth_bp.route('/')
def index():
    if 'usuario_id' in session:
        return redirect('/dashboard')
    return redirect('/login')

@auth_bp.route('/login', methods=['GET', 'POST'])
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
                # ✅ CORRECCIÓN: USAR EL ROL DE LA BASE DE DATOS
                session['usuario_id'] = usuario_info['id']
                session['usuario_nombre'] = usuario_info['nombre']
                session['usuario'] = usuario_info['usuario']
                session['rol'] = usuario_info['rol']  # ← ESTA ES LA LÍNEA CLAVE
                session['oficina_id'] = usuario_info.get('oficina_id', 1)
                session['oficina_nombre'] = usuario_info.get('oficina_nombre', '')
                
                print(f"✅ Login exitoso: {usuario} - Rol: {usuario_info['rol']} - Oficina: {usuario_info.get('oficina_nombre', '')}")
                flash(f'¡Bienvenido {usuario_info["nombre"]}!', 'success')
                return redirect('/dashboard')
            else:
                print(f"❌ Login fallido para usuario: {usuario}")
                flash('Usuario o contraseña incorrectos', 'danger')
                return render_template('auth/login.html')
        except Exception as e:
            print(f"❌ Error durante login: {e}")
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}")
            flash('Error del sistema durante el login', 'danger')
            return render_template('auth/login.html')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada correctamente', 'info')
    return redirect('/login')

# blueprints/auth.py - MODIFICAR LA RUTA dashboard
@auth_bp.route('/dashboard')
def dashboard():
    if 'usuario_id' not in session:
        return redirect('/login')
    
    try:
        print("📊 Cargando dashboard...")
        
        # ✅ NUEVO: Obtener filtro de oficina según permisos
        from utils.permissions import user_can_view_all
        oficina_id = None if user_can_view_all() else session.get('oficina_id')
        
        materiales = []
        oficinas = []
        solicitudes = []
        aprobadores = []
        
        try:
            from models.materiales_model import MaterialModel
            materiales = MaterialModel.obtener_todos(oficina_id) or []
            print(f"✅ Materiales cargados: {len(materiales)}")
        except Exception as e:
            print(f"⚠️ Error cargando materiales: {e}")
            materiales = []
        
        try:
            from models.oficinas_model import OficinaModel
            oficinas = OficinaModel.obtener_todas() or []
            print(f"✅ Oficinas cargadas: {len(oficinas)}")
        except Exception as e:
            print(f"⚠️ Error cargando oficinas: {e}")
            oficinas = []
        
        try:
            from models.solicitudes_model import SolicitudModel
            solicitudes = SolicitudModel.obtener_todas(oficina_id) or []
            print(f"✅ Solicitudes cargadas: {len(solicitudes)}")
        except Exception as e:
            print(f"⚠️ Error cargando solicitudes: {e}")
            solicitudes = []
        
        try:
            from models.usuarios_model import UsuarioModel
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
