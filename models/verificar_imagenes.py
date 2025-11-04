from materiales_model import MaterialModel
import os

def verificar_imagenes():
    """Verifica el estado de las imágenes de los materiales"""
    print("🔍 VERIFICANDO ESTADO DE IMÁGENES")
    print("=" * 60)
    
    # Obtener todos los materiales
    materiales = MaterialModel.obtener_todos()
    
    if not materiales:
        print("❌ No hay materiales para verificar")
        return
    
    print(f"📦 Total de materiales: {len(materiales)}")
    print("")
    
    for material in materiales:
        print(f"🆔 Material ID: {material['id']}")
        print(f"   Nombre: {material['nombre']}")
        print(f"   Ruta en BD: '{material['ruta_imagen']}'")
        print(f"   Tipo de dato: {type(material['ruta_imagen'])}")
        
        if material['ruta_imagen'] and material['ruta_imagen'] != 'None':
            # Construir ruta completa del archivo
            ruta_completa = os.path.join('static', material['ruta_imagen'])
            ruta_url = f"/static/{material['ruta_imagen']}"
            
            print(f"   📁 Ruta en disco: {ruta_completa}")
            print(f"   🌐 URL accesible: {ruta_url}")
            
            # Verificar si el archivo existe
            if os.path.exists(ruta_completa):
                print("   ✅ ARCHIVO EXISTE en el servidor")
                # Verificar permisos
                if os.access(ruta_completa, os.R_OK):
                    print("   ✅ ARCHIVO ACCESIBLE (permisos OK)")
                else:
                    print("   ❌ ARCHIVO NO ACCESIBLE (problema de permisos)")
            else:
                print("   ❌ ARCHIVO NO EXISTE en el servidor")
        else:
            print("   ❌ SIN RUTA DE IMAGEN en la base de datos")
        
        print("-" * 50)

if __name__ == "__main__":
    verificar_imagenes()