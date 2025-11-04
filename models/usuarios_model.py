from database import get_database_connection
import bcrypt
class UsuarioModel:
    @staticmethod
    def verificar_credenciales(usuario, password):
        conn = get_database_connection()
        if conn is None:
            return None
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT u.UsuarioId, u.NombreUsuario, u.ContraseñaHash, u.Rol, u.OficinaId,
                       o.NombreOficina
                FROM Usuarios u
                LEFT JOIN Oficinas o ON u.OficinaId = o.OficinaId
                WHERE u.NombreUsuario = ? AND u.Activo = 1
            """, (usuario,))
            row = cursor.fetchone()
            if row:
                stored_hash = row[2]
                if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
                    return {
                        'id': row[0],
                        'nombre': row[1],
                        'usuario': row[1],
                        'rol': row[3],
                        'oficina_id': row[4] if row[4] is not None else 1,
                        'oficina_nombre': row[5] if row[5] is not None else 'Sede Principal'  # ✅ NUEVO
                    }
            return None
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def obtener_por_id(usuario_id):
        conn = get_database_connection()
        if conn is None:
            return None
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT UsuarioId, NombreUsuario, Rol, OficinaId 
                FROM Usuarios 
                WHERE UsuarioId = ? AND Activo = 1
            """, (usuario_id,))
            row = cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'nombre': row[1],
                    'usuario': row[1],
                    'rol': row[2],
                    'oficina_id': row[3] if row[3] is not None else 1
                }
            return None
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def obtener_aprobadores():
        conn = get_database_connection()
        if conn is None:
            return []
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT UsuarioId, NombreUsuario, Rol, OficinaId 
                FROM Usuarios 
                WHERE Rol IN ('aprobador', 'oficina_principal', 'administrador')
                AND Activo = 1
                ORDER BY NombreUsuario
            """)
            aprobadores = []
            for row in cursor.fetchall():
                aprobadores.append({
                    'id': row[0],
                    'nombre': row[1],
                    'usuario': row[1],
                    'rol': row[2],
                    'oficina_id': row[3] if row[3] is not None else 1
                })
            return aprobadores
        finally:
            cursor.close()
            conn.close()