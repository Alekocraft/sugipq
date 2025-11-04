# models/prestamos_model.py
from database import get_database_connection

class PrestamosModel:
    
    @staticmethod
    def obtener_todos():
        conn = get_database_connection()
        if not conn:
            return []
        try:
            cursor = conn.cursor()
            query = """
                SELECT 
                    pm.PrestamoId as id,
                    m.NombreElemento as material,
                    u.NombreUsuario as usuario_solicitante,
                    o.NombreOficina as oficina,
                    pm.CantidadPrestada as cantidad,
                    pm.FechaPrestamo,
                    pm.FechaDevolucionPrevista,
                    pm.FechaDevolucionReal,
                    pm.Estado,
                    pm.Evento,
                    pm.Observaciones,
                    pm.UsuarioPrestador
                FROM PrestamosMaterial pm
                INNER JOIN Materiales m ON pm.MaterialId = m.MaterialId
                INNER JOIN Usuarios u ON pm.UsuarioSolicitanteId = u.UsuarioId
                INNER JOIN Oficinas o ON pm.OficinaId = o.OficinaId
                WHERE pm.Activo = 1
                ORDER BY pm.FechaPrestamo DESC
            """
            cursor.execute(query)
            columns = [column[0] for column in cursor.description]
            prestamos = [dict(zip(columns, row)) for row in cursor.fetchall()]
            return prestamos
        except Exception as e:
            print(f"Error obteniendo prestamos: {e}")
            return []
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @staticmethod
    def crear(material_id, usuario_solicitante_id, oficina_id, cantidad_prestada,
              fecha_devolucion_prevista, evento, observaciones, usuario_prestador):
        conn = get_database_connection()
        if not conn:
            return None
        try:
            cursor = conn.cursor()
            query = """
                INSERT INTO PrestamosMaterial (
                    MaterialId, UsuarioSolicitanteId, OficinaId, CantidadPrestada,
                    FechaDevolucionPrevista, Evento, Observaciones, UsuarioPrestador,
                    Activo, FechaPrestamo, Estado
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, GETDATE(), 'PRESTADO')
            """
            cursor.execute(query, (
                material_id, usuario_solicitante_id, oficina_id, cantidad_prestada,
                fecha_devolucion_prevista, evento, observaciones, usuario_prestador
            ))
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            print(f"Error creando prestamo: {e}")
            conn.rollback()
            return None
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @staticmethod
    def registrar_devolucion(prestamo_id, observaciones=None):
        conn = get_database_connection()
        if not conn:
            return False
        try:
            cursor = conn.cursor()
            query = """
                UPDATE PrestamosMaterial 
                SET Estado = 'DEVUELTO', 
                    FechaDevolucionReal = GETDATE(),
                    Observaciones = ISNULL(Observaciones, '') + ' ' + ISNULL(?, '')
                WHERE PrestamoId = ? AND Activo = 1
            """
            cursor.execute(query, (observaciones, prestamo_id))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error registrando devolucion: {e}")
            conn.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @staticmethod
    def obtener_usuarios():
        conn = get_database_connection()
        if not conn:
            return []
        try:
            cursor = conn.cursor()
            query = """
                SELECT UsuarioId as id, NombreUsuario as nombre 
                FROM Usuarios 
                WHERE Activo = 1
                ORDER BY NombreUsuario
            """
            cursor.execute(query)
            return [{'id': row[0], 'nombre': row[1]} for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error obteniendo usuarios: {e}")
            return []
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()