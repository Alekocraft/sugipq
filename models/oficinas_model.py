from database import get_database_connection

class OficinaModel:
    @staticmethod
    def obtener_todas():
        conn = get_database_connection()
        if conn is None:
            print("❌ No se pudo establecer conexión a la base de datos")
            return []
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT OficinaId, NombreOficina, DirectorOficina, Ubicacion, 
                       EsPrincipal, Activo, FechaCreacion, Email
                FROM Oficinas
                ORDER BY NombreOficina
            """)
            oficinas = []
            for row in cursor.fetchall():
                oficinas.append({
                    'id': row[0],
                    'nombre': row[1],
                    'director': row[2] or 'No asignado',
                    'ubicacion': row[3] or 'No especificada',
                    'es_principal': bool(row[4]) if row[4] is not None else False,
                    'activo': bool(row[5]) if row[5] is not None else True,
                    'fecha_creacion': row[6],
                    'email': row[7] or ''
                })
            return oficinas
        except Exception as e:
            print(f"❌ Error al obtener oficinas: {e}")
            return []
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def obtener_por_id(oficina_id):
        conn = get_database_connection()
        if conn is None:
            print("❌ No se pudo establecer conexión a la base de datos")
            return None
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT OficinaId, NombreOficina, DirectorOficina, Ubicacion, 
                       EsPrincipal, Activo, FechaCreacion, Email
                FROM Oficinas
                WHERE OficinaId = ?
            """, (oficina_id,))
            row = cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'nombre': row[1],
                    'director': row[2] or 'No asignado',
                    'ubicacion': row[3] or 'No especificada',
                    'es_principal': bool(row[4]) if row[4] is not None else False,
                    'activo': bool(row[5]) if row[5] is not None else True,
                    'fecha_creacion': row[6],
                    'email': row[7] or ''
                }
            return None
        except Exception as e:
            print(f"❌ Error al obtener oficina por ID: {e}")
            return None
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def obtener_por_nombre(nombre):
        """Obtiene una oficina por su nombre."""
        conn = get_database_connection()
        if conn is None:
            print("❌ No se pudo establecer conexión a la base de datos")
            return None
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT OficinaId FROM Oficinas WHERE NombreOficina = ?", (nombre,))
            row = cursor.fetchone()
            return {'id': row[0]} if row else None
        except Exception as e:
            print(f"❌ Error al obtener oficina por nombre: {e}")
            return None
        finally:
            cursor.close()
            conn.close()