from flask import Blueprint, render_template, request, redirect, session, flash, jsonify, send_file
from werkzeug.utils import secure_filename
from models.inventario_corporativo_model import InventarioCorporativoModel
import os
import pandas as pd
from io import BytesIO
from datetime import datetime

inventario_corporativo_bp = Blueprint('inventario_corporativo', __name__)


# =========================
#  HELPERS DE AUTENTICACIÓN
# =========================

def _require_login():
    return 'usuario_id' in session


def _has_role(*roles):
    """
    Devuelve True si el rol del usuario está en la lista de roles permitidos.
    """
    rol = (session.get('rol', 'usuario') or 'usuario').strip().lower()
    roles_norm = [r.lower() for r in roles]
    return rol in roles_norm


# ==========================================================
# LISTAR INVENTARIO CORPORATIVO
# ==========================================================
@inventario_corporativo_bp.route('/inventario-corporativo')
def listar_inventario_corporativo():
    if not _require_login():
        return redirect('/login')

    productos = InventarioCorporativoModel.obtener_todos() or []
    total_productos = len(productos)

    return render_template(
        'inventario_corporativo/listar.html',
        productos=productos,
        total_productos=total_productos
    )


# ==========================================================
# VER DETALLE DE PRODUCTO (RUTA ORIGINAL)
# ==========================================================
@inventario_corporativo_bp.route('/inventario-corporativo/<int:producto_id>')
def ver_detalle_producto(producto_id):
    """
    Ver detalle del producto.
    SOLO para roles: administrador y lider_inventario.
    """
    if not _require_login():
        return redirect('/login')

    if not _has_role('administrador', 'lider_inventario'):
        flash('No autorizado para ver el detalle de productos', 'danger')
        return redirect('/inventario-corporativo')

    try:
        producto = InventarioCorporativoModel.obtener_por_id(producto_id)
        if not producto:
            flash('Producto no encontrado', 'danger')
            return redirect('/inventario-corporativo')

        # Usamos el historial correcto definido en el modelo
        historial = InventarioCorporativoModel.historial_asignaciones(producto_id) or []

        return render_template(
            'inventario_corporativo/detalle.html',
            producto=producto,
            historial=historial
        )
    except Exception as e:
        print(f"❌ Error al cargar detalle del producto: {e}")
        flash('Error al cargar el producto', 'danger')
        return redirect('/inventario-corporativo')


# ==========================================================
# CREAR PRODUCTO CORPORATIVO
# ==========================================================
@inventario_corporativo_bp.route('/inventario-corporativo/crear', methods=['GET', 'POST'])
def crear_inventario_corporativo():
    if not _require_login():
        return redirect('/login')

    # Crear solo admin / líder inventario
    if not _has_role('administrador', 'lider_inventario'):
        flash('No autorizado para crear productos', 'danger')
        return redirect('/inventario-corporativo')

    categorias = InventarioCorporativoModel.obtener_categorias() or []
    proveedores = InventarioCorporativoModel.obtener_proveedores() or []

    if request.method == 'POST':
        try:
            codigo_unico = (request.form.get('codigo_unico') or '').strip()
            nombre = (request.form.get('nombre') or '').strip()
            categoria_id = int(request.form.get('categoria_id') or 0)
            proveedor_id = int(request.form.get('proveedor_id') or 0)
            valor_unitario = float(request.form.get('valor_unitario') or 0)
            cantidad = int(request.form.get('cantidad') or 0)
            cantidad_minima = int(request.form.get('cantidad_minima') or 0)
            ubicacion = (request.form.get('ubicacion') or '').strip()
            descripcion = (request.form.get('descripcion') or '').strip()
            es_asignable = 1 if request.form.get('es_asignable') == 'on' else 0
            usuario_creador = (session.get('usuario', 'administrador') or 'administrador')

            if not codigo_unico or not nombre or categoria_id <= 0 or proveedor_id <= 0:
                flash('Completa los campos obligatorios (*)', 'warning')
                return render_template(
                    'inventario_corporativo/crear.html',
                    categorias=categorias,
                    proveedores=proveedores
                )

            # Guardar imagen
            ruta_imagen = None
            archivo = request.files.get('imagen')
            if archivo and archivo.filename:
                filename = secure_filename(archivo.filename)
                upload_dir = os.path.join('static', 'uploads', 'productos')
                os.makedirs(upload_dir, exist_ok=True)
                filepath = os.path.join(upload_dir, filename)
                archivo.save(filepath)
                ruta_imagen = '/' + filepath.replace('\\', '/')

            # Crear registro
            nuevo_id = InventarioCorporativoModel.crear(
                codigo_unico=codigo_unico,
                nombre=nombre,
                descripcion=descripcion,
                categoria_id=categoria_id,
                proveedor_id=proveedor_id,
                valor_unitario=valor_unitario,
                cantidad=cantidad,
                cantidad_minima=cantidad_minima,
                ubicacion=ubicacion,
                es_asignable=es_asignable,
                usuario_creador=usuario_creador,
                ruta_imagen=ruta_imagen
            )

            if nuevo_id:
                flash('✅ Producto corporativo creado correctamente.', 'success')
                return redirect('/inventario-corporativo')
            else:
                flash('❌ No fue posible crear el producto.', 'danger')

        except Exception as e:
            print(f"[POST /inventario-corporativo/crear] Error: {e}")
            flash('❌ Ocurrió un error al guardar.', 'danger')

        return render_template(
            'inventario_corporativo/crear.html',
            categorias=categorias,
            proveedores=proveedores
        )

    return render_template(
        'inventario_corporativo/crear.html',
        categorias=categorias,
        proveedores=proveedores
    )


# ==========================================================
# EDITAR PRODUCTO CORPORATIVO
# ==========================================================
@inventario_corporativo_bp.route('/inventario-corporativo/editar/<int:producto_id>', methods=['GET', 'POST'])
def editar_producto_corporativo(producto_id):
    if not _require_login():
        return redirect('/login')

    if not _has_role('administrador', 'lider_inventario'):
        flash('No autorizado para editar productos', 'danger')
        return redirect('/inventario-corporativo')

    try:
        producto = InventarioCorporativoModel.obtener_por_id(producto_id)
        if not producto:
            flash('Producto no encontrado', 'danger')
            return redirect('/inventario-corporativo')

        categorias = InventarioCorporativoModel.obtener_categorias() or []
        proveedores = InventarioCorporativoModel.obtener_proveedores() or []

        if request.method == 'POST':
            codigo_unico = (request.form.get('codigo_unico') or '').strip()
            nombre = (request.form.get('nombre') or '').strip()
            categoria_id = int(request.form.get('categoria_id') or 0)
            proveedor_id = int(request.form.get('proveedor_id') or 0)
            valor_unitario = float(request.form.get('valor_unitario') or 0)
            cantidad = int(request.form.get('cantidad') or 0)
            cantidad_minima = int(request.form.get('cantidad_minima') or 0)
            ubicacion = (request.form.get('ubicacion') or '').strip()
            descripcion = (request.form.get('descripcion') or '').strip()
            es_asignable = 1 if request.form.get('es_asignable') == 'on' else 0

            if not codigo_unico or not nombre or categoria_id <= 0 or proveedor_id <= 0:
                flash('Completa los campos obligatorios (*)', 'warning')
                return render_template(
                    'inventario_corporativo/editar.html',
                    producto=producto,
                    categorias=categorias,
                    proveedores=proveedores
                )

            # Guardar imagen
            ruta_imagen = producto.get('ruta_imagen')
            archivo = request.files.get('imagen')
            if archivo and archivo.filename:
                filename = secure_filename(archivo.filename)
                upload_dir = os.path.join('static', 'uploads', 'productos')
                os.makedirs(upload_dir, exist_ok=True)
                filepath = os.path.join(upload_dir, filename)
                archivo.save(filepath)
                ruta_imagen = '/' + filepath.replace('\\', '/')

            # Actualizar registro (coincidiendo con la firma del modelo)
            actualizado = InventarioCorporativoModel.actualizar(
                producto_id=producto_id,
                codigo_unico=codigo_unico,
                nombre=nombre,
                descripcion=descripcion,
                categoria_id=categoria_id,
                proveedor_id=proveedor_id,
                valor_unitario=valor_unitario,
                cantidad=cantidad,
                cantidad_minima=cantidad_minima,
                ubicacion=ubicacion,
                es_asignable=es_asignable,
                ruta_imagen=ruta_imagen
            )

            if actualizado:
                flash('✅ Producto actualizado correctamente.', 'success')
                return redirect(f'/inventario-corporativo/{producto_id}')
            else:
                flash('❌ No fue posible actualizar el producto.', 'danger')

        return render_template(
            'inventario_corporativo/editar.html',
            producto=producto,
            categorias=categorias,
            proveedores=proveedores
        )

    except Exception as e:
        print(f"❌ Error al editar producto: {e}")
        flash('Error al cargar el producto para editar', 'danger')
        return redirect('/inventario-corporativo')


# ==========================================================
# ASIGNAR PRODUCTO CORPORATIVO
# ==========================================================
@inventario_corporativo_bp.route('/inventario-corporativo/asignar/<int:producto_id>', methods=['GET', 'POST'])
def asignar_producto_corporativo(producto_id):
    """
    Asignar producto a oficina.
    SOLO admin / lider_inventario.
    """
    if not _require_login():
        return redirect('/login')

    if not _has_role('administrador', 'lider_inventario'):
        flash('No autorizado para asignar productos', 'danger')
        return redirect('/inventario-corporativo')

    try:
        producto = InventarioCorporativoModel.obtener_por_id(producto_id)
        if not producto:
            flash('Producto no encontrado', 'danger')
            return redirect('/inventario-corporativo')

        # No permitir asignar si el producto no es asignable
        if not producto.get('es_asignable'):
            flash('Este producto no es asignable', 'warning')
            return redirect(f'/inventario-corporativo/{producto_id}')

        oficinas = InventarioCorporativoModel.obtener_oficinas() or []
        historial = InventarioCorporativoModel.historial_asignaciones(producto_id) or []

        if request.method == 'POST':
            oficina_id = int(request.form.get('oficina_id') or 0)
            cantidad_asignar = int(request.form.get('cantidad') or 0)

            if not oficina_id or cantidad_asignar <= 0:
                flash('Complete todos los campos requeridos', 'warning')
                return render_template(
                    'inventario_corporativo/asignar.html',
                    producto=producto,
                    oficinas=oficinas,
                    historial=historial
                )

            if cantidad_asignar > producto.get('cantidad', 0):
                flash('No hay suficiente stock disponible', 'danger')
                return render_template(
                    'inventario_corporativo/asignar.html',
                    producto=producto,
                    oficinas=oficinas,
                    historial=historial
                )

            asignado = InventarioCorporativoModel.asignar_a_oficina(
                producto_id=producto_id,
                oficina_id=oficina_id,
                cantidad=cantidad_asignar,
                usuario_accion=session.get('usuario', 'Sistema')
            )

            if asignado:
                flash('✅ Producto asignado correctamente a la oficina.', 'success')
                return redirect(f'/inventario-corporativo/{producto_id}')
            else:
                flash('❌ No fue posible asignar el producto.', 'danger')

        return render_template(
            'inventario_corporativo/asignar.html',
            producto=producto,
            oficinas=oficinas,
            historial=historial
        )

    except Exception as e:
        print(f"❌ Error al asignar producto: {e}")
        flash('Error al cargar el producto para asignar', 'danger')
        return redirect('/inventario-corporativo')


# ==========================================================
# ELIMINAR PRODUCTO CORPORATIVO
# ==========================================================
@inventario_corporativo_bp.route('/inventario-corporativo/eliminar/<int:producto_id>', methods=['POST'])
def eliminar_producto_corporativo(producto_id):
    """
    Eliminar (baja lógica) producto.
    SOLO admin / lider_inventario.
    """
    if not _require_login():
        return redirect('/login')

    if not _has_role('administrador', 'lider_inventario'):
        flash('No autorizado para eliminar productos', 'danger')
        return redirect('/inventario-corporativo')

    try:
        producto = InventarioCorporativoModel.obtener_por_id(producto_id)
        if not producto:
            flash('Producto no encontrado', 'danger')
            return redirect('/inventario-corporativo')

        # Eliminar usando la firma correcta (producto_id, usuario_accion)
        eliminado = InventarioCorporativoModel.eliminar(
            producto_id,
            session.get('usuario', 'Sistema')
        )

        if eliminado:
            flash('✅ Producto eliminado correctamente.', 'success')
        else:
            flash('❌ No fue posible eliminar el producto.', 'danger')

    except Exception as e:
        print(f"❌ Error al eliminar producto: {e}")
        flash('Error al eliminar el producto', 'danger')

    return redirect('/inventario-corporativo')


# ==========================================================
# FUNCIONES AUXILIARES DE FILTROS
# ==========================================================
def aplicar_filtros_adicionales(productos, oficina, categoria, stock):
    productos_filtrados = productos.copy()

    if oficina:
        if oficina == 'Sede Principal':
            productos_filtrados = [
                p for p in productos_filtrados
                if p.get('oficina', 'Sede Principal') == 'Sede Principal'
            ]
        elif oficina == 'Oficinas de Servicio':
            productos_filtrados = [
                p for p in productos_filtrados
                if p.get('oficina', 'Sede Principal') != 'Sede Principal'
            ]
        else:
            productos_filtrados = [
                p for p in productos_filtrados
                if p.get('oficina', '') == oficina
            ]

    if categoria:
        productos_filtrados = [
            p for p in productos_filtrados
            if p.get('categoria', '').lower() == categoria.lower()
        ]

    if stock:
        stock_filters = {
            'bajo': lambda p: p.get('cantidad', 0) <= p.get('cantidad_minima', 5),
            'normal': lambda p: p.get('cantidad', 0) > p.get('cantidad_minima', 5),
            'sin': lambda p: p.get('cantidad', 0) == 0
        }
        if stock in stock_filters:
            productos_filtrados = [
                p for p in productos_filtrados if stock_filters[stock](p)
            ]

    return productos_filtrados


def preparar_oficinas_filtradas(tipo, oficinas_db):
    if tipo == 'sede':
        return [{'nombre': 'Sede Principal'}] + [
            {'nombre': of['nombre']} for of in oficinas_db if of['nombre'] != 'Sede Principal'
        ]
    elif tipo == 'oficinas':
        return [{'nombre': of['nombre']} for of in oficinas_db if of['nombre'] != 'Sede Principal']
    else:
        return [{'nombre': 'Sede Principal'}] + [
            {'nombre': of['nombre']} for of in oficinas_db if of['nombre'] != 'Sede Principal'
        ]


# ==========================================================
# VISTAS FILTRADAS
# ==========================================================
@inventario_corporativo_bp.route('/inventario-corporativo/sede-principal')
def inventario_corporativo_sede_principal():
    if not _require_login():
        return redirect('/login')
    return listar_inventario_corporativo_filtrado('sede')


@inventario_corporativo_bp.route('/inventario-corporativo/oficinas-servicio')
def inventario_corporativo_oficinas_servicio():
    if not _require_login():
        return redirect('/login')
    return listar_inventario_corporativo_filtrado('oficinas')


@inventario_corporativo_bp.route('/inventario-corporativo/filtrado/<tipo>')
def listar_inventario_corporativo_filtrado(tipo):
    if not _require_login():
        return redirect('/login')

    rol = session.get('rol', '')
    if rol not in ['administrador', 'lider_inventario', 'inventario_corporativo']:
        flash('No tiene permisos para acceder a esta sección', 'danger')
        return redirect('/dashboard')

    try:
        filtro_oficina = request.args.get('oficina', '').strip()
        filtro_categoria = request.args.get('categoria', '').strip()
        filtro_stock = request.args.get('stock', '').strip()

        productos = InventarioCorporativoModel.obtener_todos_con_oficina() or []
        oficinas_db = InventarioCorporativoModel.obtener_oficinas() or []
        categorias_db = InventarioCorporativoModel.obtener_categorias() or []

        config = {
            'sede': {
                'titulo': "Sede Principal",
                'subtitulo': "Productos asignados a la sede principal",
                'filtro': lambda p: p.get('oficina', 'Sede Principal') == 'Sede Principal'
            },
            'oficinas': {
                'titulo': "Oficinas de Servicio",
                'subtitulo': "Productos distribuidos en oficinas de servicio",
                'filtro': lambda p: p.get('oficina', 'Sede Principal') != 'Sede Principal'
            },
            'default': {
                'titulo': "Inventario Corporativo",
                'subtitulo': "Todos los productos corporativos",
                'filtro': lambda p: True
            }
        }.get(tipo, {})

        productos = [p for p in productos if config['filtro'](p)]
        productos_filtrados = aplicar_filtros_adicionales(
            productos,
            filtro_oficina,
            filtro_categoria,
            filtro_stock
        )

        total_productos = len(productos_filtrados)
        valor_total = sum(
            p.get('valor_unitario', 0) * p.get('cantidad', 0)
            for p in productos_filtrados
        )
        productos_bajo_stock = len([
            p for p in productos_filtrados
            if p.get('cantidad', 0) <= p.get('cantidad_minima', 5)
        ])

        oficinas_filtradas = preparar_oficinas_filtradas(tipo, oficinas_db)
        categorias = [{'nombre': cat.get('nombre', '')} for cat in categorias_db]

        return render_template(
            'inventario_corporativo/listar_con_filtros.html',
            productos=productos_filtrados,
            titulo=config['titulo'],
            subtitulo=config['subtitulo'],
            tipo=tipo,
            total_productos=total_productos,
            valor_total=valor_total,
            productos_bajo_stock=productos_bajo_stock,
            total_oficinas=len(oficinas_filtradas),
            oficinas_filtradas=oficinas_filtradas,
            categorias=categorias,
            filtro_oficina=filtro_oficina,
            filtro_categoria=filtro_categoria,
            filtro_stock=filtro_stock
        )
    except Exception as e:
        print(f"❌ Error cargando inventario corporativo: {e}")
        flash('Error al cargar el inventario corporativo', 'danger')
        return render_template('inventario_corporativo/listar_con_filtros.html', productos=[])


# ==========================================================
# EXPORTAR INVENTARIO A EXCEL
# ==========================================================
@inventario_corporativo_bp.route('/inventario-corporativo/exportar/excel/<tipo>')
def exportar_inventario_corporativo_excel(tipo):
    if not _require_login():
        return redirect('/login')

    try:
        filtro_oficina = request.args.get('oficina', '')
        filtro_categoria = request.args.get('categoria', '')
        filtro_stock = request.args.get('stock', '')

        productos = InventarioCorporativoModel.obtener_todos_con_oficina() or []

        if tipo == 'sede':
            productos = [
                p for p in productos
                if p.get('oficina', 'Sede Principal') == 'Sede Principal'
            ]
            sheet_name = 'Sede Principal'
        elif tipo == 'oficinas':
            productos = [
                p for p in productos
                if p.get('oficina', 'Sede Principal') != 'Sede Principal'
            ]
            sheet_name = 'Oficinas Servicio'
        else:
            sheet_name = 'Inventario Completo'

        productos = aplicar_filtros_adicionales(
            productos,
            filtro_oficina,
            filtro_categoria,
            filtro_stock
        )

        data = [{
            'Código': p.get('codigo_unico', ''),
            'Producto': p.get('nombre', ''),
            'Descripción': p.get('descripcion', ''),
            'Categoría': p.get('categoria', ''),
            'Proveedor': p.get('proveedor', ''),
            'Valor Unitario': p.get('valor_unitario', 0),
            'Cantidad': p.get('cantidad', 0),
            'Cantidad Mínima': p.get('cantidad_minima', 0),
            'Ubicación': p.get('ubicacion', ''),
            'Oficina': p.get('oficina', 'Sede Principal'),
            'Asignable': 'Sí' if p.get('es_asignable', False) else 'No',
            'Estado Stock': (
                'Bajo' if p.get('cantidad', 0) <= p.get('cantidad_minima', 5)
                else 'Normal' if p.get('cantidad', 0) > 0 else 'Sin Stock'
            )
        } for p in productos]

        df = pd.DataFrame(data)

        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            worksheet = writer.sheets[sheet_name]
            for idx, col in enumerate(df.columns):
                max_len = max(df[col].astype(str).str.len().max(), len(col)) + 2
                worksheet.column_dimensions[chr(65 + idx)].width = min(max_len, 50)

        output.seek(0)
        filename = f"inventario_corporativo_{sheet_name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"

        return send_file(
            output,
            download_name=filename,
            as_attachment=True,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except Exception as e:
        print(f"❌ Error exportando a Excel: {e}")
        flash('Error al exportar el archivo Excel', 'danger')
        return redirect(request.referrer or '/inventario-corporativo')


# ==========================================================
# API ESTADÍSTICAS
# ==========================================================
@inventario_corporativo_bp.route('/api/inventario-corporativo/estadisticas')
def api_estadisticas_inventario_corporativo():
    if not _require_login():
        return jsonify({'error': 'No autorizado'}), 401

    try:
        productos = InventarioCorporativoModel.obtener_todos_con_oficina() or []
        total = len(productos)
        sede = len([p for p in productos if p.get('oficina', 'Sede Principal') == 'Sede Principal'])
        oficinas = total - sede

        return jsonify({
            'total_productos': total,
            'productos_sede': sede,
            'productos_oficinas': oficinas
        })
    except Exception as e:
        print(f"❌ Error obteniendo estadísticas: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500
