# models/solicitudes_model.py
from database import get_database_connection
import datetime

class SolicitudModel:
    @staticmethod
    def crear(oficina_id, material_id, cantidad_solicitada, porcentaje_oficina, usuario_nombre, observacion=""):
        conn = get_database_connection()
        if conn is None:
            return None
        cursor = conn.cursor()
        try:
            cursor.execute(
                "{CALL sp_CrearSolicitud (?, ?, ?, ?, ?, ?)}",
                (oficina_id, material_id, cantidad_solicitada, porcentaje_oficina, usuario_nombre, observacion)
            )
            result = cursor.fetchone()
            conn.commit()
            return result[0] if result else None
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def _obtener_aprobador_id(usuario_id):
        conn = get_database_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT AprobadorId FROM Usuarios WHERE UsuarioId = ?", (usuario_id,))
            row = cursor.fetchone()
            return row[0] if row and row[0] else 1
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def aprobar(solicitud_id, usuario_aprobador_id):
        conn = get_database_connection()
        if conn is None:
            return False, "Error de conexión"
        cursor = conn.cursor()
        try:
            aprobador_id = SolicitudModel._obtener_aprobador_id(usuario_aprobador_id)
            # NOTA: El SP original en bd.txt NO recibe email, así que lo eliminamos
            cursor.execute(
                "{CALL sp_AprobarSolicitud (?, ?)}",
                (solicitud_id, aprobador_id)
            )
            conn.commit()
            return True, "✅ Solicitud aprobada exitosamente"
        except Exception as e:
            conn.rollback()
            error_msg = str(e)
            if "Límite mensual" in error_msg:
                return False, "❌ Límite mensual excedido"
            elif "Stock insuficiente" in error_msg or "excede el inventario" in error_msg:
                return False, "❌ Stock insuficiente"
            else:
                return False, f"❌ Error: {error_msg}"
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def aprobar_parcial(solicitud_id, usuario_aprobador_id, cantidad_aprobada):
        # Aprobación completa + entrega parcial
        success, msg = SolicitudModel.aprobar(solicitud_id, usuario_aprobador_id)
        if not success:
            return False, msg
        conn = get_database_connection()
        if conn is None:
            return False, "Error de conexión"
        cursor = conn.cursor()
        try:
            usuario_nombre = "Sistema"
            cursor.execute(
                "{CALL sp_RegistrarEntrega (?, ?, ?, ?)}",
                (solicitud_id, cantidad_aprobada, usuario_nombre, "Aprobación parcial")
            )
            conn.commit()
            return True, f"✅ {cantidad_aprobada} unidades entregadas"
        except Exception as e:
            conn.rollback()
            return False, f"⚠️ Error al registrar entrega: {e}"
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def rechazar(solicitud_id, usuario_aprobador_id, observacion=""):
        conn = get_database_connection()
        if conn is None:
            return False
        cursor = conn.cursor()
        try:
            aprobador_id = SolicitudModel._obtener_aprobador_id(usuario_aprobador_id)
            cursor.execute("""
                UPDATE SolicitudesMaterial 
                SET EstadoId = 3, 
                    FechaAprobacion = GETDATE(), 
                    AprobadorId = ?, 
                    Observacion = ?
                WHERE SolicitudId = ? AND EstadoId = 1
            """, (aprobador_id, observacion, solicitud_id))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def obtener_todas():
        return SolicitudModel.obtener_todas_ordenadas()

    @staticmethod
    def obtener_para_aprobador():
        conn = get_database_connection()
        if conn is None:
            return []
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT 
                    sm.SolicitudId,
                    m.NombreElemento,
                    sm.UsuarioSolicitante,
                    o.NombreOficina,
                    sm.OficinaSolicitanteId,  -- ✅ Incluido
                    sm.CantidadSolicitada,
                    es.NombreEstado,
                    sm.FechaSolicitud,
                    sm.Observacion,
                    sm.MaterialId,
                    sm.PorcentajeOficina,
                    sm.ValorTotalSolicitado,
                    sm.ValorOficina,
                    sm.ValorSedePrincipal,
                    m.ValorUnitario,
                    m.CantidadDisponible,
                    sm.FechaAprobacion
                FROM dbo.SolicitudesMaterial sm
                INNER JOIN dbo.Materiales m ON sm.MaterialId = m.MaterialId
                INNER JOIN dbo.Oficinas o ON sm.OficinaSolicitanteId = o.OficinaId
                INNER JOIN dbo.EstadosSolicitud es ON sm.EstadoId = es.EstadoId
                WHERE sm.EstadoId = 1
                ORDER BY sm.FechaSolicitud DESC
            """)
            return SolicitudModel._mapear_solicitudes(cursor.fetchall())
        except Exception as e:
            print(f"Error en obtener_para_aprobador: {e}")
            return []
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def obtener_todas_ordenadas():
        conn = get_database_connection()
        if conn is None:
            return []
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT 
                    sm.SolicitudId,
                    m.NombreElemento,
                    sm.UsuarioSolicitante,
                    o.NombreOficina,
                    sm.OficinaSolicitanteId,  -- ✅ Incluido
                    sm.CantidadSolicitada,
                    es.NombreEstado,
                    sm.FechaSolicitud,
                    sm.Observacion,
                    sm.MaterialId,
                    sm.PorcentajeOficina,
                    sm.ValorTotalSolicitado,
                    sm.ValorOficina,
                    sm.ValorSedePrincipal,
                    m.ValorUnitario,
                    m.CantidadDisponible,
                    sm.FechaAprobacion
                FROM dbo.SolicitudesMaterial sm
                INNER JOIN dbo.Materiales m ON sm.MaterialId = m.MaterialId
                INNER JOIN dbo.Oficinas o ON sm.OficinaSolicitanteId = o.OficinaId
                INNER JOIN dbo.EstadosSolicitud es ON sm.EstadoId = es.EstadoId
                ORDER BY 
                    CASE es.NombreEstado 
                        WHEN 'Pendiente' THEN 1
                        WHEN 'Aprobada' THEN 2
                        WHEN 'Rechazada' THEN 3
                        ELSE 4
                    END,
                    sm.FechaSolicitud DESC
            """)
            return SolicitudModel._mapear_solicitudes(cursor.fetchall())
        except Exception as e:
            print(f"Error en obtener_todas_ordenadas: {e}")
            return []
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def _mapear_solicitudes(rows):
        solicitudes = []
        for row in rows:
            solicitud = {
                'id': row[0],
                'material_nombre': row[1],
                'usuario_solicitante': row[2],
                'oficina_nombre': row[3],
                'oficina_id': row[4],  # ✅ Ahora sí está
                'cantidad_solicitada': row[5],
                'estado': row[6],  # Ej: "Pendiente", "Aprobada", etc.
                'fecha_solicitud': row[7],
                'observacion': row[8] or '',
                'material_id': row[9],
                'porcentaje_oficina': float(row[10]) if row[10] else 0,
                'valor_total_solicitado': float(row[11]) if row[11] else 0,
                'valor_oficina': float(row[12]) if row[12] else 0,
                'valor_sede': float(row[13]) if row[13] else 0,
                'valor_unitario': float(row[14]) if row[14] else 0,
                'stock_disponible': row[15] if row[15] else 0,
                'fecha_aprobacion': row[16]
            }
            solicitudes.append(solicitud)
        return solicitudes

    @staticmethod
    def obtener_por_id(solicitud_id):
        conn = get_database_connection()
        if conn is None:
            return None
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT 
                    sm.SolicitudId,
                    m.NombreElemento,
                    sm.UsuarioSolicitante,
                    o.NombreOficina,
                    sm.OficinaSolicitanteId,
                    sm.CantidadSolicitada,
                    es.NombreEstado,
                    sm.FechaSolicitud,
                    sm.Observacion,
                    sm.MaterialId,
                    sm.PorcentajeOficina,
                    sm.ValorTotalSolicitado,
                    sm.ValorOficina,
                    sm.ValorSedePrincipal,
                    m.ValorUnitario,
                    m.CantidadDisponible,
                    sm.FechaAprobacion
                FROM dbo.SolicitudesMaterial sm
                INNER JOIN dbo.Materiales m ON sm.MaterialId = m.MaterialId
                INNER JOIN dbo.Oficinas o ON sm.OficinaSolicitanteId = o.OficinaId
                INNER JOIN dbo.EstadosSolicitud es ON sm.EstadoId = es.EstadoId
                WHERE sm.SolicitudId = ?
            """, (solicitud_id,))
            rows = cursor.fetchall()
            if rows:
                return SolicitudModel._mapear_solicitudes(rows)[0]
            return None
        except Exception as e:
            print(f"Error en obtener_por_id: {e}")
            return None
        finally:
            cursor.close()
            conn.close()