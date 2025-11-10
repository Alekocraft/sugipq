import os
from datetime import datetime
from database import get_database_connection
from models.oficinas_model import OficinaModel

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

def inicializar_directorios():
    """Inicializar directorios necesarios para la aplicación"""
    from config.config import Config
    
    directorios = [
        Config.UPLOAD_FOLDER,
        os.path.join(Config.UPLOAD_FOLDER, 'productos'),
        os.path.join(Config.UPLOAD_FOLDER, 'documentos'),
        os.path.join(Config.UPLOAD_FOLDER, 'perfiles'),
        os.path.join(Config.UPLOAD_FOLDER, 'temp')
    ]
    
    for directorio in directorios:
        try:
            os.makedirs(directorio, exist_ok=True)
            print(f"✅ Directorio verificado: {directorio}")
        except Exception as e:
            print(f"❌ Error creando directorio {directorio}: {e}")

def verificar_configuracion():
    """Verificar que toda la configuración esté correcta"""
    from config.config import Config
    
    print("🔍 Verificando configuración...")
    print(f"📁 Directorio base: {Config.BASE_DIR}")
    print(f"📁 Templates: {Config.TEMPLATE_FOLDER}")
    print(f"📁 Static: {Config.STATIC_FOLDER}")
    print(f"📁 Uploads: {Config.UPLOAD_FOLDER}")
    
    # Verificar que los directorios existan
    for folder in [Config.TEMPLATE_FOLDER, Config.STATIC_FOLDER]:
        if not os.path.exists(folder):
            print(f"❌ Directorio no encontrado: {folder}")
        else:
            print(f"✅ Directorio encontrado: {folder}")
    
    # Verificar secret key
    if Config.SECRET_KEY == 'dev-secret-key-change-in-production':
        print("⚠️ ADVERTENCIA: Usando SECRET_KEY por defecto - Cambia en producción")
    else:
        print("✅ SECRET_KEY configurada correctamente")
    
    print("✅ Configuración verificada")

def inicializar_roles_permisos():
    """Inicializar roles y permisos básicos si no existen"""
    try:
        # Esta función puede expandirse para crear roles en la base de datos
        # Por ahora solo es un placeholder para futuras expansiones
        print("🔍 Verificando configuración de roles...")
        
        from config.config import Config
        roles_configurados = list(Config.ROLES.keys())
        print(f"✅ Roles configurados: {', '.join(roles_configurados)}")
        
    except Exception as e:
        print(f"❌ Error verificando roles: {e}")

def inicializar_todo():
    """Ejecutar todas las inicializaciones"""
    print("🚀 Inicializando aplicación...")
    verificar_configuracion()
    inicializar_directorios()
    inicializar_oficina_principal()
    inicializar_roles_permisos()
    print("✅ Aplicación inicializada correctamente")