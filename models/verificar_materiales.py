from database import get_database_connection

def verificar_materiales():
    """Verifica todos los materiales en la base de datos"""
    conn = get_database_connection()
    if conn is None:
        print("❌ No se pudo conectar a la BD")
        return
    
    cursor = conn.cursor()
    try:
        print("🔍 VERIFICANDO MATERIALES EN LA BASE DE DATOS...")
        print("=" * 50)
        
        # Obtener todos los materiales
        cursor.execute("""
            SELECT MaterialId, NombreElemento, RutaImagen, ValorUnitario, CantidadDisponible
            FROM Materiales 
            WHERE Activo = 1
            ORDER BY MaterialId DESC
        """)
        
        materiales = cursor.fetchall()
        print(f"📦 Total de materiales activos: {len(materiales)}")
        print("")
        
        for material in materiales:
            material_id, nombre, ruta_imagen, valor, cantidad = material
            print(f"ID: {material_id}")
            print(f"  Nombre: {nombre}")
            print(f"  RutaImagen: {ruta_imagen}")
            print(f"  Valor: {valor}")
            print(f"  Cantidad: {cantidad}")
            print(f"  Tipo RutaImagen: {type(ruta_imagen)}")
            print("-" * 30)
            
    except Exception as e:
        print(f"❌ Error al verificar materiales: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    verificar_materiales()