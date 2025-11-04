# -*- coding: utf-8 -*-
# routes_inventario_corporativo.py (sin acentos para evitar errores de encoding en Windows)
from flask import Blueprint, render_template, request, redirect, session, flash, url_for
from models.inventario_corporativo_model import InventarioCorporativoModel, generar_codigo_unico
from datetime import datetime

bp_inv = Blueprint('invcorp', __name__)

def _require_login():
    return 'usuario_id' in session

def _has_role(*roles):
    rol = (session.get('rol', 'usuario') or 'usuario').strip().lower()
    return rol in [r.lower() for r in roles]

@bp_inv.route('/inventario-corporativo')
def inv_listar():
    if not _require_login():
        return redirect('/login')
    
    # Verificar permisos
    if not _has_role('administrador', 'lider_inventario', 'inventario_corporativo'):
        flash('No tiene permisos para acceder a esta sección', 'danger')
        return redirect('/dashboard')
    
    try:
        productos = InventarioCorporativoModel.obtener_todos()
        
        # Calcular estadísticas para las tarjetas
        valor_total_inventario = sum(p.get('valor_unitario', 0) * p.get('cantidad', 0) for p in productos)
        productos_bajo_stock = len([p for p in productos if p.get('cantidad', 0) <= p.get('cantidad_minima', 5)])
        productos_asignables = len([p for p in productos if p.get('es_asignable', False)])
        
        # Obtener categorías únicas para filtros
        categorias_db = InventarioCorporativoModel.obtener_categorias() or []
        categorias_unicas = list(set([cat.get('nombre_categoria', '') for cat in categorias_db if cat.get('nombre_categoria')]))
        
        print(f"✅ Productos cargados: {len(productos)}")
        print(f"✅ Valor total: {valor_total_inventario}")
        print(f"✅ Productos bajo stock: {productos_bajo_stock}")
        print(f"✅ Productos asignables: {productos_asignables}")
        
        return render_template('inventario_corporativo/listar.html',
                            productos=productos,
                            valor_total_inventario=valor_total_inventario,
                            productos_bajo_stock=productos_bajo_stock,
                            productos_asignables=productos_asignables,
                            categorias_unicas=categorias_unicas,
                            now=datetime.now())
                             
    except Exception as e:
        print(f"❌ Error cargando inventario corporativo: {e}")
        flash('Error al cargar el inventario corporativo', 'danger')
        # Proporcionar valores por defecto para evitar el error
        return render_template('inventario_corporativo/listar.html',
                            productos=[],
                            valor_total_inventario=0,
                            productos_bajo_stock=0,
                            productos_asignables=0,
                            categorias_unicas=[],
                            now=datetime.now())

@bp_inv.route('/inventario-corporativo/<int:producto_id>')
def inv_detalle(producto_id):
    if not _require_login():
        return redirect('/login')
    producto = InventarioCorporativoModel.obtener_por_id(producto_id)
    if not producto:
        flash('Producto no encontrado', 'warning')
        return redirect('/inventario-corporativo')
    historial = InventarioCorporativoModel.historial_asignaciones(producto_id)
    return render_template('inventario_corporativo/detalle.html', producto=producto, historial=historial)

@bp_inv.route('/inventario-corporativo/crear', methods=['GET', 'POST'])
def inv_crear():
    if not _require_login():
        return redirect('/login')
    
    # Verificar permisos para crear productos
    if not _has_role('administrador', 'lider_inventario'):
        flash('No autorizado para crear productos', 'danger')
        return redirect('/inventario-corporativo')
    
    categorias = InventarioCorporativoModel.obtener_categorias()
    proveedores = InventarioCorporativoModel.obtener_proveedores()
    
    if request.method == 'POST':
        # GENERAR CÓDIGO ÚNICO AUTOMÁTICAMENTE en lugar de leerlo del formulario
        codigo_unico = generar_codigo_unico()

        nombre = (request.form.get('nombre') or '').strip()
        categoria_id = request.form.get('categoria_id')
        proveedor_id = request.form.get('proveedor_id')
        valor_unitario = request.form.get('valor_unitario')
        cantidad = request.form.get('cantidad')
        cantidad_minima = request.form.get('cantidad_minima')
        ubicacion = (request.form.get('ubicacion') or '').strip()
        descripcion = (request.form.get('descripcion') or '').strip()
        es_asignable = 1 if request.form.get('es_asignable') else 0
        usuario_creador = (session.get('usuario', 'sistema') or 'sistema')

        # Imagen opcional
        imagen = request.files.get('imagen')
        ruta_imagen = None
        if imagen and imagen.filename:
            ruta_imagen = f"static/uploads/{imagen.filename}"
            imagen.save(ruta_imagen)

        # Validaciones básicas
        if not nombre or not categoria_id or not proveedor_id:
            flash('Complete todos los campos obligatorios', 'danger')
            return render_template('inventario_corporativo/crear.html', 
                                 categorias=categorias, proveedores=proveedores)

        try:
            ok_id = InventarioCorporativoModel.crear(
                codigo_unico, nombre, descripcion, categoria_id, proveedor_id,
                valor_unitario, cantidad, cantidad_minima, ubicacion,
                es_asignable, usuario_creador, ruta_imagen
            )
            if ok_id:
                flash(f"✅ Producto '{nombre}' creado con código {codigo_unico}", "success")
                return redirect('/inventario-corporativo')
            else:
                flash('No fue posible crear el producto', 'danger')
        except Exception as e:
            flash(f'Error al crear producto: {str(e)}', 'danger')
            
    return render_template('inventario_corporativo/crear.html', 
                         categorias=categorias, proveedores=proveedores)

@bp_inv.route('/inventario-corporativo/editar/<int:producto_id>', methods=['GET', 'POST'])
def inv_editar(producto_id):
    if not _require_login():
        return redirect('/login')
    if not _has_role('administrador', 'lider_inventario'):
        flash('No autorizado', 'danger')
        return redirect('/inventario-corporativo')

    producto = InventarioCorporativoModel.obtener_por_id(producto_id)
    if not producto:
        flash('Producto no encontrado', 'warning')
        return redirect('/inventario-corporativo')

    categorias = InventarioCorporativoModel.obtener_categorias()
    proveedores = InventarioCorporativoModel.obtener_proveedores()

    if request.method == 'POST':
        try:
            ok = InventarioCorporativoModel.actualizar(
                producto_id=producto_id,
                codigo_unico=(request.form.get('codigo_unico') or '').strip(),
                nombre=(request.form.get('nombre') or '').strip(),
                descripcion=(request.form.get('descripcion') or '').strip(),
                categoria_id=request.form.get('categoria_id'),
                proveedor_id=request.form.get('proveedor_id'),
                valor_unitario=request.form.get('valor_unitario'),
                cantidad_minima=request.form.get('cantidad_minima'),
                ubicacion=(request.form.get('ubicacion') or '').strip(),
                es_asignable=1 if request.form.get('es_asignable') else 0
            )
            if ok:
                flash('Producto actualizado correctamente', 'success')
                return redirect(f'/inventario-corporativo/{producto_id}')
            else:
                flash('No se pudo actualizar el producto', 'danger')
        except Exception as e:
            flash(f'Error al actualizar: {str(e)}', 'danger')

    return render_template('inventario_corporativo/editar.html',
                           producto=producto, categorias=categorias, proveedores=proveedores)

@bp_inv.route('/inventario-corporativo/eliminar/<int:producto_id>', methods=['POST'])
def inv_eliminar(producto_id):
    if not _require_login():
        return redirect('/login')
    if not _has_role('administrador', 'lider_inventario'):
        flash('No autorizado', 'danger')
        return redirect('/inventario-corporativo')
    
    try:
        ok = InventarioCorporativoModel.eliminar(producto_id, session.get('usuario', 'sistema'))
        if ok:
            flash('Producto eliminado correctamente', 'success')
        else:
            flash('No se pudo eliminar el producto', 'danger')
    except Exception as e:
        flash(f'Error al eliminar: {str(e)}', 'danger')
        
    return redirect('/inventario-corporativo')

@bp_inv.route('/inventario-corporativo/asignar/<int:producto_id>', methods=['GET','POST'])
def inv_asignar(producto_id):
    if not _require_login():
        return redirect('/login')
    if not _has_role('administrador', 'lider_inventario'):
        flash('No autorizado', 'danger')
        return redirect('/inventario-corporativo')

    producto = InventarioCorporativoModel.obtener_por_id(producto_id)
    if not producto:
        flash('Producto no encontrado', 'warning')
        return redirect('/inventario-corporativo')
    
    if not producto.get('es_asignable'):
        flash('Este producto no es asignable', 'warning')
        return redirect(f'/inventario-corporativo/{producto_id}')
    
    oficinas = InventarioCorporativoModel.obtener_oficinas()
    historial = InventarioCorporativoModel.historial_asignaciones(producto_id)

    if request.method == 'POST':
        oficina_id = request.form.get('oficina_id')
        cantidad = request.form.get('cantidad')
        usuario_accion = session.get('usuario', 'sistema')
        
        # Validaciones
        if not oficina_id or not cantidad:
            flash('Seleccione una oficina y especifique la cantidad', 'danger')
        else:
            try:
                cantidad_int = int(cantidad)
                if cantidad_int <= 0:
                    flash('La cantidad debe ser mayor a 0', 'danger')
                elif cantidad_int > producto['cantidad']:
                    flash('La cantidad solicitada excede el stock disponible', 'danger')
                else:
                    ok = InventarioCorporativoModel.asignar_a_oficina(
                        producto_id, oficina_id, cantidad_int, usuario_accion
                    )
                    if ok:
                        flash('Asignación registrada correctamente', 'success')
                        return redirect(f'/inventario-corporativo/{producto_id}')
                    else:
                        flash('No se pudo completar la asignación. Verifique el stock disponible.', 'danger')
            except ValueError:
                flash('La cantidad debe ser un número válido', 'danger')
            except Exception as e:
                flash(f'Error al asignar: {str(e)}', 'danger')

    return render_template('inventario_corporativo/asignar.html',
                           producto=producto, oficinas=oficinas, historial=historial)

@bp_inv.route('/inventario-corporativo/reportes')
def inv_reportes():
    if not _require_login():
        return redirect('/login')
    
    # Verificar permisos para ver reportes
    if not _has_role('administrador', 'lider_inventario', 'consultor'):
        flash('No autorizado para ver reportes', 'danger')
        return redirect('/inventario-corporativo')
    
    try:
        stock_por_categoria = InventarioCorporativoModel.reporte_stock_por_categoria()
        valor_inventario = InventarioCorporativoModel.reporte_valor_inventario()
        asignaciones_por_oficina = InventarioCorporativoModel.reporte_asignaciones_por_oficina()
        
        return render_template('inventario_corporativo/reportes.html',
                               stock_por_categoria=stock_por_categoria,
                               valor_inventario=valor_inventario,
                               asignaciones_por_oficina=asignaciones_por_oficina)
    except Exception as e:
        flash(f'Error al generar reportes: {str(e)}', 'danger')
        return redirect('/inventario-corporativo')