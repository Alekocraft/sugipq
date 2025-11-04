from flask import Blueprint, render_template, request, redirect, session, flash
from datetime import datetime
from database import get_database_connection  # ajusta el import si tu helper tiene otro nombre

bp_prestamos = Blueprint('prestamos', __name__, url_prefix='/prestamos')

# Nombre de la tabla de préstamos para ELEMENTOS PUBLICITARIOS
LOANS_TABLE = "dbo.PrestamosElementos"

def _require_login():
    return 'usuario_id' in session

def _has_role(*roles):
    return (session.get('rol', '') or '').strip().lower() in [r.lower() for r in roles]


@bp_prestamos.get('/')
def listar():
    """
    Lista préstamos desde dbo.PrestamosElementos (Elementos Publicitarios).
    Hace el JOIN a Usuarios de forma robusta: detecta la mejor columna de "nombre".
    """
    if not _require_login():
        return redirect('/login')

    prestamos = []
    conn = cur = None
    try:
        conn = get_database_connection()
        cur = conn.cursor()

        # Verificar tabla de préstamos de elementos
        cur.execute("""
            SELECT 1
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA='dbo' AND TABLE_NAME='PrestamosElementos'
        """)
        if not cur.fetchone():
            flash("No existe la tabla dbo.PrestamosElementos. Ejecuta el script DDL para crearla.", "danger")
            return render_template('prestamos/listar.html', prestamos=[])

        # Detectar columna de "nombre" en Usuarios
        cur.execute("""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA='dbo' AND TABLE_NAME='Usuarios'
        """)
        cols_usuarios = {r[0] for r in cur.fetchall()}
        # orden de preferencia
        posibles_nombres = ['NombreCompleto', 'NombreUsuario', 'Nombre', 'Usuario', 'Correo', 'Email']
        user_name_col = next((c for c in posibles_nombres if c in cols_usuarios), None)
        if not user_name_col:
            # último recurso: usar el id como texto
            user_name_expr = "CAST(u.UsuarioId AS VARCHAR(50))"
        else:
            user_name_expr = f"u.{user_name_col}"

        # Detectar también columna de nombre en Oficinas (fallback seguro)
        cur.execute("""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA='dbo' AND TABLE_NAME='Oficinas'
        """)
        cols_oficinas = {r[0] for r in cur.fetchall()}
        oficina_name_col = 'NombreOficina' if 'NombreOficina' in cols_oficinas else next(
            (c for c in ['Nombre', 'Descripcion', 'Codigo'] if c in cols_oficinas), None
        )
        oficina_name_expr = f"o.{oficina_name_col}" if oficina_name_col else "CAST(o.OficinaId AS VARCHAR(50))"

        # SELECT final (incluye Evento y FechaDevolucionReal para la UI)
        sql = f"""
            SELECT 
                p.PrestamoId,
                e.NombreElemento,
                p.CantidadPrestada,
                p.FechaPrestamo,
                p.FechaDevolucionPrevista,
                p.Estado,
                {user_name_expr} AS UsuarioSolicitante,
                {oficina_name_expr} AS NombreOficina,
                p.Evento,
                p.FechaDevolucionReal
            FROM dbo.PrestamosElementos AS p
            JOIN dbo.ElementosPublicitarios AS e ON e.ElementoId = p.ElementoId
            JOIN dbo.Usuarios AS u              ON u.UsuarioId = p.UsuarioSolicitanteId
            JOIN dbo.Oficinas AS o              ON o.OficinaId = p.OficinaId
            ORDER BY p.PrestamoId DESC
        """
        cur.execute(sql)

        for r in cur.fetchall():
            prestamos.append({
                'id': r[0],
                'elemento': r[1],
                'cantidad': r[2],
                'fecha_prestamo': r[3],
                'fecha_devolucion_prevista': r[4],
                'estado': r[5],
                'usuario_solicitante': r[6],
                'oficina': r[7],
                'evento': r[8],
                'fecha_devolucion_real': r[9],
            })

    except Exception as e:
        flash(f'Error cargando préstamos: {e}', 'danger')
    finally:
        try:
            if cur: cur.close()
            if conn: conn.close()
        except:
            pass

    return render_template('prestamos/listar.html', prestamos=prestamos)

@bp_prestamos.get('/crear')
def crear_get():
    """
    Formulario para crear préstamo de ELEMENTOS PUBLICITARIOS.
    """
    if not _require_login():
        return redirect('/login')
    if not _has_role('administrador', 'lider_inventario'):
        flash('No autorizado para crear préstamos', 'danger')
        return redirect('/prestamos')

    elementos = []
    conn = cur = None
    try:
        conn = get_database_connection()
        cur = conn.cursor()

        # Cargar ElementosPublicitarios activos
        cur.execute("""
            SELECT ElementoId, NombreElemento, ValorUnitario, CantidadDisponible, RutaImagen
            FROM dbo.ElementosPublicitarios
            WHERE Activo = 1
            ORDER BY NombreElemento ASC
        """)
        for r in cur.fetchall():
            elementos.append({
                'id': r[0],
                'nombre': r[1],
                'valor_unitario': float(r[2] or 0),
                'cantidad': int(r[3] or 0),
                'ruta_imagen': (r[4] or '')
            })

    except Exception as e:
        flash(f'Error cargando elementos publicitarios: {e}', 'danger')
    finally:
        try:
            if cur: cur.close()
            if conn: conn.close()
        except:
            pass

    return render_template('prestamos/crear.html', elementos=elementos)


@bp_prestamos.post('/crear')
def crear_post():
    """
    Inserta préstamo en dbo.PrestamosElementos, valida y descuenta stock en dbo.ElementosPublicitarios.
    No toca PrestamosMaterial ni Materiales.
    """
    if not _require_login():
        return redirect('/login')
    if not _has_role('administrador', 'lider_inventario', 'oficina_principal', 'inventario_corporativo'):
        flash('No autorizado para crear préstamos', 'danger')
        return redirect('/prestamos')

    elemento_id = int(request.form.get('elemento_id', '0'))
    cantidad    = int(request.form.get('cantidad_prestada', '0'))
    fdev_prev   = request.form.get('fecha_devolucion_prevista')
    evento      = request.form.get('evento', '')
    observ      = request.form.get('observaciones', '')

    usuario_id  = int(request.form.get('usuario_id') or session.get('usuario_id'))
    oficina_id  = int(request.form.get('oficina_id') or session.get('oficina_id'))

    if elemento_id <= 0 or cantidad <= 0 or not fdev_prev:
        flash('Complete todos los campos obligatorios', 'warning')
        return redirect('/prestamos/elementos/crearmaterial')


    conn = cur = None
    try:
        conn = get_database_connection()
        cur = conn.cursor()

        # Verificar tabla
        cur.execute("""
            SELECT 1
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'PrestamosElementos'
        """)
        if not cur.fetchone():
            flash("No existe la tabla dbo.PrestamosElementos. Ejecuta el script DDL para crearla.", "danger")
            return redirect('/prestamos')

        # 1) Validación de stock en ElementosPublicitarios
        cur.execute("""
            SELECT CantidadDisponible, NombreElemento
            FROM dbo.ElementosPublicitarios
            WHERE ElementoId = ? AND Activo = 1
        """, (elemento_id,))
        row = cur.fetchone()
        if not row:
            flash('El elemento seleccionado no existe o no está activo', 'danger')
            return redirect('/prestamos/crear')

        stock_actual = int(row[0] or 0)
        nombre_elemento = row[1]
        if cantidad > stock_actual:
            flash(f'Cantidad solicitada ({cantidad}) excede el stock disponible ({stock_actual}) de "{nombre_elemento}".', 'danger')
            return redirect('/prestamos/crear')

        # 2) Insertar préstamo (fecha de préstamo vía GETDATE(); estado PRESTADO)
        cur.execute(f"""
            INSERT INTO {LOANS_TABLE}
                (ElementoId,
                 UsuarioSolicitanteId,
                 OficinaId,
                 CantidadPrestada,
                 FechaDevolucionPrevista,
                 Evento,
                 Observaciones,
                 UsuarioPrestador,
                 Activo,
                 FechaPrestamo,
                 Estado)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, GETDATE(), 'PRESTADO')
        """, (
            elemento_id,
            usuario_id,
            oficina_id,
            cantidad,
            datetime.strptime(fdev_prev, '%Y-%m-%d'),
            evento,
            observ,
            session.get('usuario_nombre', 'sistema')
        ))

        # 3) Descontar stock en ElementosPublicitarios
        cur.execute("""
            UPDATE dbo.ElementosPublicitarios
            SET CantidadDisponible = CantidadDisponible - ?
            WHERE ElementoId = ?
        """, (cantidad, elemento_id))

        conn.commit()
        flash(f'✅ Préstamo de "{nombre_elemento}" registrado correctamente', 'success')

    except Exception as e:
        try:
            if conn: conn.rollback()
        except:
            pass
        flash(f'Error al registrar el préstamo: {e}', 'danger')
    finally:
        try:
            if cur: cur.close()
            if conn: conn.close()
        except:
            pass

    return redirect('/prestamos')


@bp_prestamos.post('/devolver/<int:prestamo_id>')
def devolver(prestamo_id):
    """
    Registra la devolución de un préstamo de elemento publicitario.
    Acepta fecha_devolucion_real y observacion_devolucion del modal.
    """
    if 'usuario_id' not in session:
        return redirect('/login')

    fecha_real_str = request.form.get('fecha_devolucion_real')
    observacion = (request.form.get('observacion_devolucion') or '').strip()

    conn = cur = None
    try:
        # Validación básica de fecha
        if not fecha_real_str:
            flash('Debe indicar la fecha de devolución.', 'warning')
            return redirect('/prestamos')
        
        # Parseo de fecha con manejo de error
        try:
            fecha_real = datetime.strptime(fecha_real_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Formato de fecha inválido. Use YYYY-MM-DD.', 'warning')
            return redirect('/prestamos')

        conn = get_database_connection()
        cur = conn.cursor()

        # 1) Traer préstamo y validar estado - MEJORADO para incluir más datos
        cur.execute("""
            SELECT p.ElementoId, p.CantidadPrestada, p.Estado, 
                   p.FechaPrestamo, COALESCE(p.Observaciones, ''),
                   e.NombreElemento
            FROM dbo.PrestamosElementos AS p
            JOIN dbo.ElementosPublicitarios AS e ON e.ElementoId = p.ElementoId
            WHERE p.PrestamoId = ?
        """, (prestamo_id,))
        row = cur.fetchone()
        
        if not row:
            flash('Préstamo no encontrado.', 'danger')
            return redirect('/prestamos')

        elemento_id, cantidad_prestada, estado, fecha_prestamo, obs_prev, nombre_elemento = \
            int(row[0]), int(row[1]), (row[2] or '').upper(), row[3], row[4], row[5]

        if estado == 'DEVUELTO':
            flash('Este préstamo ya fue marcado como DEVUELTO.', 'info')
            return redirect('/prestamos')

        # Validaciones de fecha mejoradas
        hoy = datetime.now().date()
        fecha_prestamo_date = fecha_prestamo.date() if fecha_prestamo else None
        
        if fecha_real > hoy:
            flash('La fecha de devolución no puede ser futura.', 'warning')
            return redirect('/prestamos')
        
        if fecha_prestamo_date and fecha_real < fecha_prestamo_date:
            flash('La fecha de devolución no puede ser anterior a la fecha del préstamo.', 'warning')
            return redirect('/prestamos')

        # 2) Actualizar préstamo - MEJORADO para registrar quién hizo la devolución
        nueva_obs = obs_prev
        if observacion:
            prefijo = ' | ' if nueva_obs else ''
            usuario_devolucion = session.get('usuario_nombre', 'Sistema')
            nueva_obs = f"{nueva_obs}{prefijo}Devolución [{usuario_devolucion}]: {observacion}"

        cur.execute("""
            UPDATE dbo.PrestamosElementos
            SET Estado = 'DEVUELTO',
                FechaDevolucionReal = ?,
                Observaciones = ?,
                UsuarioDevolucion = ?
            WHERE PrestamoId = ?
        """, (fecha_real, nueva_obs, session.get('usuario_nombre', 'Sistema'), prestamo_id))

        # 3) Devolver stock
        cur.execute("""
            UPDATE dbo.ElementosPublicitarios
            SET CantidadDisponible = CantidadDisponible + ?
            WHERE ElementoId = ?
        """, (cantidad_prestada, elemento_id))

        conn.commit()
        flash(f'✅ Devolución de "{nombre_elemento}" registrada correctamente.', 'success')

    except Exception as e:
        try:
            if conn: 
                conn.rollback()
        except:
            pass
        flash(f'Error al marcar la devolución: {str(e)}', 'danger')
    finally:
        try:
            if cur: 
                cur.close()
            if conn: 
                conn.close()
        except:
            pass

    return redirect('/prestamos')

# --- Rutas para crear materiales publicitarios ---

# GET: /prestamos/elementos/crearmaterial
@bp_prestamos.route('/elementos/crearmaterial', methods=['GET'], endpoint='crear_elemento_publicitario_get')
def crear_elemento_publicitario_get():
    if not _require_login():
        return redirect('/login')
    if not _has_role('administrador', 'lider_inventario'):
        flash('No autorizado para crear materiales', 'danger')
        return redirect('/prestamos')
    return render_template('prestamos/elemento_crear.html')


# POST: /prestamos/elementos/crearmaterial
@bp_prestamos.route('/elementos/crearmaterial', methods=['POST'], endpoint='crear_elemento_publicitario_post')
def crear_elemento_publicitario_post():
    if not _require_login():
        return redirect('/login')
    if not _has_role('administrador', 'lider_inventario'):
        flash('No autorizado para crear materiales', 'danger')
        return redirect('/prestamos/elementos/crearmaterial')

    nombre_elemento = (request.form.get('nombre_elemento') or '').strip()
    valor_unitario  = request.form.get('valor_unitario')
    cantidad_disp   = request.form.get('cantidad_disponible')
    imagen          = request.files.get('imagen')

    oficina_id      = session.get('oficina_id')
    usuario_nombre  = (session.get('usuario_nombre') or 'administrador').strip() or 'administrador'
    usuario_id      = session.get('usuario_id')

    if not oficina_id:
        flash('No se encontró la oficina en la sesión. Vuelve a iniciar sesión.', 'danger')
        return redirect('/prestamos/elementos/crearmaterial')

    try:
        valor_unitario = float(valor_unitario)
        cantidad_disp  = int(cantidad_disp)
    except Exception:
        flash('Valor unitario o cantidad no válidos.', 'warning')
        return redirect('/prestamos/elementos/crearmaterial')

    if not nombre_elemento or valor_unitario <= 0 or cantidad_disp < 0:
        flash('Complete nombre, valor (>0) y stock (>=0).', 'warning')
        return redirect('/prestamos/elementos/crearmaterial')

    # Guardar imagen bajo /static/uploads/elementos y persistir ruta web "static/uploads/elementos/..."
    ruta_imagen = None
    if imagen and imagen.filename:
        from werkzeug.utils import secure_filename
        import os
        filename = secure_filename(imagen.filename)
        project_root = os.path.dirname(os.path.abspath(__file__))
        static_dir   = os.path.join(project_root, 'static')
        upload_dir   = os.path.join(static_dir, 'uploads', 'elementos')
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, filename)
        imagen.save(file_path)
        ruta_imagen = f'static/uploads/elementos/{filename}'

    conn = cur = None
    try:
        conn = get_database_connection()
        cur = conn.cursor()

        # Columnas disponibles
        cur.execute("""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA='dbo' AND TABLE_NAME='ElementosPublicitarios'
        """)
        cols = {r[0] for r in cur.fetchall()}

        # Campos a insertar (NO incluir ValorTotal porque es calculado)
        columnas = ["NombreElemento", "ValorUnitario", "CantidadDisponible", "RutaImagen", "Activo", "OficinaCreadoraId"]
        valores  = [nombre_elemento, valor_unitario, cantidad_disp, ruta_imagen, 1, int(oficina_id)]

        # UsuarioCreador (NOT NULL en tu esquema)
        if "UsuarioCreador" in cols:
            columnas.append("UsuarioCreador")
            valores.append(usuario_nombre)

        # Si existe UsuarioCreadorId también lo llenamos (opcional)
        if "UsuarioCreadorId" in cols and usuario_id:
            columnas.append("UsuarioCreadorId")
            valores.append(int(usuario_id))

        # Si "CantidadMinima" es NOT NULL sin default, añade aquí un valor
        # if "CantidadMinima" in cols:
        #     columnas.append("CantidadMinima")
        #     valores.append(10)  # o el que corresponda

        # IMPORTANTE: NO agregar "ValorTotal" (es calculado)
        # if "ValorTotal" in cols:  # <- NO usar, dejar que SQL la calcule

        placeholders = ", ".join(["?"] * len(columnas))
        sql = f"INSERT INTO dbo.ElementosPublicitarios ({', '.join(columnas)}) VALUES ({placeholders})"
        cur.execute(sql, tuple(valores))
        conn.commit()

        flash('✅ Elemento publicitario creado correctamente', 'success')
        return redirect('/prestamos/elementos/crearmaterial')


    except Exception as e:
        try:
            if conn: conn.rollback()
        except: pass
        flash(f'Error al crear el material: {e}', 'danger')
        return redirect('/prestamos/elementos/crearmaterial')
    finally:
        try:
            if cur: cur.close()
            if conn: conn.close()
        except: pass

