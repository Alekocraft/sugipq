# utils/initialization.py
from datetime import datetime
from models.oficinas_model import OficinaModel
from database import get_database_connection

def inicializar_oficina_principal():
    """Verifica y crea la oficina Sede Principal si no existe"""
    try:
        print("?? Verificando existencia de oficina 'Sede Principal'...")
        oficina_principal = OficinaModel.obtener_por_nombre("Sede Principal")

        if not oficina_principal:
            print("?? Creando oficina 'Sede Principal'...")
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
            print("? Oficina 'Sede Principal' creada exitosamente")

            # Verificar que se creó correctamente
            oficina_verificada = OficinaModel.obtener_por_nombre("Sede Principal")
            if oficina_verificada:
                print(f"? Verificación exitosa - ID: {oficina_verificada['id']}")
            else:
                print("?? Advertencia: No se pudo verificar la creación de la oficina")
        else:
            print(f"? Oficina 'Sede Principal' ya existe - ID: {oficina_principal['id']}")
    except Exception as e:
        print(f"? Error inicializando oficina principal: {e}")
        import traceback
        print(f"?? TRACEBACK: {traceback.format_exc()}")