from database import get_database_connection

class MaterialModel:
    @staticmethod
    def obtener_todos():
        conn = get_database_connection()
        if conn is None:
            return []
        cursor = conn.cursor()
        try:
            # CONSULTA CORREGIDA - SOLO CAMPOS QUE EXISTEN
            cursor.execute("""
                SELECT 
                    MaterialId, 
                    NombreElemento, 
                    ValorUnitario, 
                    CantidadDisponible,
                    ISNULL(ValorTotal, 0) as ValorTotal,
                    OficinaCreadoraId, 
                    Activo, 
                    FechaCreacion,
                    UsuarioCreador, 
                    RutaImagen
                FROM Materiales 
                WHERE Activo = 1 
                ORDER BY MaterialId DESC
            """)
            materiales = []
            for row in cursor.fetchall():
                material = {
                    'id': row[0],
                    'nombre': row[1],
                    'valor_unitario': float(row[2]) if row[2] else 0.0,
                    'cantidad': row[3] if row[3] else 0,
                    'valor_total': float(row[4]) if row[4] else 0.0,
                    'oficina_id': row[5],
                    'activo': row[6],
                    'fecha_creacion': row[7],
                    'usuario_creador': row[8],
                    'ruta_imagen': row[9],
                    'cantidad_minima': 10  # VALOR FIJO POR DEFECTO
                }
                materiales.append(material)
            return materiales
        except Exception as e:
            print(f"Error en MaterialModel.obtener_todos: {e}")
            return []
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def obtener_por_id(material_id):
        conn = get_database_connection()
        if conn is None:
            return None
        cursor = conn.cursor()
        try:
            # CONSULTA CORREGIDA - SOLO CAMPOS QUE EXISTEN
            cursor.execute("""
                SELECT 
                    MaterialId, 
                    NombreElemento, 
                    ValorUnitario, 
                    CantidadDisponible, 
                    ISNULL(ValorTotal, 0) as ValorTotal,
                    OficinaCreadoraId, 
                    Activo, 
                    FechaCreacion,
                    UsuarioCreador, 
                    RutaImagen
                FROM Materiales
                WHERE MaterialId = ? AND Activo = 1
            """, (material_id,))
            row = cursor.fetchone()
            if row:
                ruta_imagen = row[9]
                if ruta_imagen and isinstance(ruta_imagen, bytes):
                    try:
                        ruta_imagen = ruta_imagen.decode('utf-8')
                    except:
                        ruta_imagen = ""
                return {
                    'id': row[0],
                    'nombre': row[1],
                    'valor_unitario': float(row[2]) if row[2] else 0.0,
                    'cantidad': row[3] if row[3] else 0,
                    'valor_total': float(row[4]) if row[4] else 0.0,
                    'oficina_id': row[5],
                    'activo': bool(row[6]) if row[6] is not None else True,
                    'fecha_creacion': row[7],
                    'usuario_creador': row[8],
                    'ruta_imagen': ruta_imagen if ruta_imagen and ruta_imagen != 'None' else None,
                    'cantidad_minima': 10  # VALOR FIJO POR DEFECTO
                }
            return None
        except Exception as e:
            print(f"Error al obtener material por ID: {e}")
            return None
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def crear(nombre, valor_unitario, cantidad, oficina_id, ruta_imagen=None, usuario_creador="Sistema"):
        conn = get_database_connection()
        if conn is None:
            print("ERROR: No hay conexion a la BD")
            return None
        cursor = conn.cursor()
        try:
            # Validaciones basicas
            if not nombre or nombre.strip() == '':
                print("Nombre vacio")
                return None
            if valor_unitario <= 0:
                print("Valor unitario invalido")
                return None
            if cantidad < 0:
                print("Cantidad invalida")
                return None
        
            print(f"INSERTANDO MATERIAL EN BD:")
            print(f"   - Nombre: {nombre}")
            print(f"   - Valor: {valor_unitario}")
            print(f"   - Cantidad: {cantidad}")
            print(f"   - Oficina: {oficina_id}")
            print(f"   - RutaImagen recibida: '{ruta_imagen}'")
        
            # MANEJO CORRECTO DE LA RUTA DE IMAGEN - FORZAR STRING
            ruta_imagen_final = str(ruta_imagen).strip() if ruta_imagen else None
            print(f"   - Imagen a guardar: '{ruta_imagen_final}'")
        
            # VERIFICAR QUE LA OFICINA EXISTE
            cursor.execute("SELECT COUNT(*) FROM Oficinas WHERE OficinaId = ?", (oficina_id,))
            oficina_exists = cursor.fetchone()[0]
            print(f"Oficina existe: {oficina_exists}")
            
            if oficina_exists == 0:
                print("La oficina no existe")
                return None
        
            # SQL DE INSERCION SIN CantidadMinima (usa el valor por defecto de la BD)
            sql = """
                INSERT INTO Materiales (
                    NombreElemento, 
                    ValorUnitario, 
                    CantidadDisponible, 
                    OficinaCreadoraId, 
                    Activo, 
                    FechaCreacion, 
                    UsuarioCreador, 
                    RutaImagen
                ) 
                VALUES (?, ?, ?, ?, 1, GETDATE(), ?, ?)
            """
        
            print("Ejecutando INSERT...")
            # EJECUCION DIRECTA CON PARAMETROS
            params = (
                str(nombre), 
                float(valor_unitario), 
                int(cantidad), 
                int(oficina_id), 
                str(usuario_creador), 
                ruta_imagen_final
            )
            print(f"Parametros: {params}")
            
            cursor.execute(sql, params)
            affected = cursor.rowcount
            print(f"INSERT ejecutado - filas afectadas: {affected}")
            
            conn.commit()
            print("Commit realizado")
        
            # OBTENER EL ID DEL MATERIAL CREADO
            cursor.execute("SELECT MAX(MaterialId) FROM Materiales")
            max_row = cursor.fetchone()
            
            if max_row and max_row[0] is not None:
                material_id = int(max_row[0])
                print(f"MATERIAL CREADO EXITOSAMENTE - ID: {material_id}")
                
                # VERIFICACION FINAL DESPUES DEL COMMIT
                cursor.execute("""
                    SELECT MaterialId, NombreElemento, RutaImagen
                    FROM Materiales 
                    WHERE MaterialId = ?
                """, (material_id,))
                verif_row = cursor.fetchone()
                
                if verif_row:
                    id_verif, nombre_verif, ruta_verif = verif_row
                    print(f"VERIFICACION FINAL EN BD:")
                    print(f"   - ID: {id_verif}")
                    print(f"   - Nombre: {nombre_verif}")
                    print(f"   - RutaImagen: '{ruta_verif}'")
                    print(f"   - Tipo RutaImagen: {type(ruta_verif)}")
                    
                    # CONFIRMAR QUE LA RUTA NO SEA NULL
                    if ruta_verif is not None:
                        print(f"IMAGEN GUARDADA CORRECTAMENTE: '{ruta_verif}'")
                    
                    return material_id
                else:
                    print("El material no se encontro despues de crearlo")
                    return None
            else:
                print("NO SE PUDO OBTENER ID DEL MATERIAL")
                return None
                
        except Exception as e:
            print(f"ERROR CRITICO en MaterialModel.crear: {str(e)}")
            import traceback
            print(f"TRACEBACK COMPLETO: {traceback.format_exc()}")
            conn.rollback()
            return None
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def actualizar(material_id, nombre, valor_unitario, cantidad, oficina_id, ruta_imagen=None):
        conn = get_database_connection()
        if conn is None:
            print("No se pudo establecer conexion a la base de datos")
            return False
        cursor = conn.cursor()
        try:
            if valor_unitario <= 0:
                return False
                
            if ruta_imagen is None:
                cursor.execute("""
                    UPDATE Materiales 
                    SET NombreElemento = ?, ValorUnitario = ?, CantidadDisponible = ?, OficinaCreadoraId = ?
                    WHERE MaterialId = ?
                """, (nombre, valor_unitario, cantidad, oficina_id, material_id))
            else:
                cursor.execute("""
                    UPDATE Materiales 
                    SET NombreElemento = ?, ValorUnitario = ?, CantidadDisponible = ?, OficinaCreadoraId = ?, RutaImagen = ?
                    WHERE MaterialId = ?
                """, (nombre, valor_unitario, cantidad, oficina_id, ruta_imagen, material_id))
                
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error al actualizar material: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def actualizar_imagen(material_id, ruta_imagen):
        """Metodo especifico para actualizar solo la imagen"""
        conn = get_database_connection()
        if conn is None:
            print("No se pudo establecer conexion a la base de datos")
            return False
        cursor = conn.cursor()
        try:
            print(f"Actualizando imagen para material {material_id}: '{ruta_imagen}'")
            cursor.execute("""
                UPDATE Materiales 
                SET RutaImagen = ?
                WHERE MaterialId = ?
            """, (ruta_imagen, material_id))
            
            affected = cursor.rowcount
            conn.commit()
            print(f"Imagen actualizada - filas afectadas: {affected}")
            return affected > 0
        except Exception as e:
            print(f"Error al actualizar imagen: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def eliminar(material_id):
        conn = get_database_connection()
        if conn is None:
            print("No se pudo establecer conexion a la base de datos")
            return False
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE Materiales SET Activo = 0 WHERE MaterialId = ?", (material_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error al eliminar material: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()