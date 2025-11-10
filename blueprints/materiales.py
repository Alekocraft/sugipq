# blueprints/materiales.py
from flask import Blueprint, render_template, request, redirect, session, flash, url_for, current_app
from werkzeug.utils import secure_filename
import os
from models.materiales_model import MaterialModel
from models.oficinas_model import OficinaModel

# Crear blueprint de materiales
materiales_bp = Blueprint('materiales', __name__, url_prefix='/materiales')

# Helpers de autenticación locales 
def _require_login():
    return 'usuario_id' in session

def _has_role(*roles):
    rol = (session.get('rol', '') or '').strip().lower()
    return rol in [r.lower() for r in roles]

@materiales_bp.route('/')
def listar_materiales():
    if not _require_login():
        return redirect('/login')

    # ? SOLO admin y lider_inventario pueden acceder
    if not _has_role('administrador', 'lider_inventario'):
        flash('No tiene permisos para acceder a esta sección', 'danger')
        return redirect('/dashboard')
        
    try:
        print("?? Cargando lista de materiales...")
        materiales = MaterialModel.obtener_todos() or []
        print(f"? Se cargaron {len(materiales)} materiales para mostrar")
        return render_template('materials/listar.html', materiales=materiales)
    except Exception as e:
        print(f"? Error obteniendo materiales: {e}")
        flash('Error al cargar los materiales', 'danger')
        return render_template('materials/listar.html', materiales=[])

@materiales_bp.route('/crear', methods=['GET', 'POST'])
def crear_material():
    if not _require_login():
        return redirect('/login')

    # ? SOLO admin y lider_inventario pueden acceder
    if not _has_role('administrador', 'lider_inventario'):
        flash('No tiene permisos para acceder a esta sección', 'danger')
        return redirect('/dashboard')

    if request.method == 'GET':
        return render_template('materials/crear.html')

    # POST METHOD
    try:
        print("=== INICIANDO CREACIÓN DE MATERIAL ===")

        # Obtener oficina principal
        oficina_principal = OficinaModel.obtener_por_nombre("Sede Principal")
        if not oficina_principal:
            todas_oficinas = OficinaModel.obtener_todas() or []
            if todas_oficinas:
                oficina_principal = todas_oficinas[0]
                print(f"?? Usando primera oficina disponible: {oficina_principal.get('nombre')}")
            else:
                flash('? Error crítico: No hay oficinas disponibles en el sistema. Contacte al administrador.', 'danger')
                return render_template('materials/crear.html')

        oficina_id = oficina_principal['id']
        print(f"? Usando oficina ID: {oficina_id} - {oficina_principal.get('nombre', 'Sede Principal')}")

        errores = []
        materiales_creados = []

        for i in range(10):
            nombre_key = f'nombre_{i}'
            if nombre_key not in request.form or not request.form[nombre_key].strip():
                continue

            try:
                nombre = request.form.get(f'nombre_{i}', '').strip()
                valor_unitario = float(request.form.get(f'valor_unitario_{i}', 0.0))
                cantidad = int(request.form.get(f'cantidad_{i}', 0))
                imagen = request.files.get(f'imagen_{i}')

                print(f"?? Procesando material {i}: {nombre}")

                # Validaciones
                if not nombre:
                    errores.append(f"Material {i+1}: Nombre es obligatorio.")
                    continue
                if valor_unitario <= 0:
                    errores.append(f"Material {i+1} ({nombre}): Valor unitario debe ser mayor que 0.")
                    continue
                if cantidad <= 0:
                    errores.append(f"Material {i+1} ({nombre}): Cantidad debe ser mayor que 0.")
                    continue
                if not imagen or imagen.filename == '':
                    errores.append(f"Material {i+1} ({nombre}): Imagen es obligatoria.")
                    continue

                # Procesar imagen
                filename = secure_filename(imagen.filename)
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)

                # Verificar que el directorio existe
                os.makedirs(os.path.dirname(filepath), exist_ok=True)

                # Guardar la imagen
                imagen.save(filepath)
                print(f"? Imagen guardada en disco: {filepath}")

                # Ruta para la base de datos
                ruta_imagen = f"uploads/{filename}"
                print(f"? Ruta de imagen para BD: '{ruta_imagen}'")

                # Obtener usuario creador
                usuario_creador = session.get('usuario_nombre', 'Sistema') or session.get('usuario', 'Sistema')

                # Crear material
                print("?? CREANDO MATERIAL CON IMAGEN...")
                material_id = MaterialModel.crear(
                    nombre=nombre,
                    valor_unitario=valor_unitario,
                    cantidad=cantidad,
                    oficina_id=oficina_id,
                    ruta_imagen=ruta_imagen,
                    usuario_creador=usuario_creador
                )

                if material_id:
                    print(f"? Material creado con ID: {material_id}")
                    material_verificado = MaterialModel.obtener_por_id(material_id)
                    if material_verificado:
                        if material_verificado.get('ruta_imagen'):
                            print(f"?? VERIFICACIÓN: Imagen guardada - '{material_verificado['ruta_imagen']}'")
                            materiales_creados.append(nombre)
                        else:
                            print(f"?? ADVERTENCIA: Imagen no se guardó para material {material_id}")
                    else:
                        print(f"?? No se pudo verificar material {material_id}")
                        errores.append(f"Material {i+1} ({nombre}): Error al verificar creación.")
                else:
                    print(f"? Error al crear material: {nombre}")
                    errores.append(f"Material {i+1} ({nombre}): Error en base de datos.")

            except ValueError as ve:
                print(f"? Error de valor: {ve}")
                errores.append(f"Material {i+1}: Valores numéricos inválidos.")
            except Exception as e:
                print(f"? Error al crear material {i+1}: {e}")
                import traceback
                print(f"?? TRACEBACK: {traceback.format_exc()}")
                errores.append(f"Material {i+1} ({nombre or 'Desconocido'}): Error interno del sistema.")

        # Mostrar resultados
        if errores:
            for error in errores:
                flash(error, 'danger')

        if materiales_creados:
            flash(f'? ¡{len(materiales_creados)} material(es) creado(s) exitosamente!', 'success')

        return render_template('materials/crear.html')

    except Exception as e:
        print(f"? Error crítico en crear_material: {e}")
        import traceback
        print(f"?? TRACEBACK: {traceback.format_exc()}")
        flash('Error crítico del sistema.', 'danger')
        return render_template('materials/crear.html')

@materiales_bp.route('/editar/<int:material_id>', methods=['GET', 'POST'])
def editar_material(material_id):
    if not _require_login():
        return redirect('/login')

    # ? SOLO admin y lider_inventario pueden acceder
    if not _has_role('administrador', 'lider_inventario'):
        flash('No tiene permisos para acceder a esta sección', 'danger')
        return redirect('/dashboard')

    try:
        if request.method == 'POST':
            print(f"?? Procesando edición del material {material_id}")

            # Obtener datos del formulario
            nombre = request.form.get('nombre')
            valor_unitario_str = request.form.get('valor_unitario', '0')
            cantidad_str = request.form.get('cantidad', '0')

            # Validar y convertir datos
            try:
                valor_unitario = float(valor_unitario_str)
                cantidad = int(cantidad_str)
            except ValueError:
                flash('Error: Los valores numéricos no son válidos', 'danger')
                return redirect(url_for('materiales.editar_material', material_id=material_id))

            # Obtener material actual
            material_actual = MaterialModel.obtener_por_id(material_id)
            if not material_actual:
                flash('Material no encontrado', 'danger')
                return redirect(url_for('materiales.listar_materiales'))

            oficina_id = material_actual['oficina_id']
            imagen = request.files.get('imagen')
            ruta_imagen = material_actual['ruta_imagen']

            # Procesar nueva imagen si se proporciona
            if imagen and imagen.filename != '':
                try:
                    filename = secure_filename(imagen.filename)
                    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                    imagen.save(filepath)
                    ruta_imagen = f"uploads/{filename}"
                    print(f"? Nueva imagen guardada: {ruta_imagen}")
                except Exception as e:
                    print(f"? Error guardando nueva imagen: {e}")
                    flash('Error al guardar la nueva imagen', 'danger')
                    return redirect(url_for('materiales.editar_material', material_id=material_id))

            # Actualizar material
            resultado = MaterialModel.actualizar(
                material_id=material_id,
                nombre=nombre,
                valor_unitario=valor_unitario,
                cantidad=cantidad,
                oficina_id=oficina_id,
                ruta_imagen=ruta_imagen
            )

            if resultado:
                flash('Material actualizado exitosamente', 'success')
                return redirect(url_for('materiales.listar_materiales'))
            else:
                flash('Error al actualizar el material', 'danger')
                return redirect(url_for('materiales.editar_material', material_id=material_id))

        # GET request - mostrar formulario de edición
        print(f"?? Cargando formulario de edición para material {material_id}")
        material = MaterialModel.obtener_por_id(material_id)

        if not material:
            flash('Material no encontrado', 'danger')
            return redirect(url_for('materiales.listar_materiales'))

        print(f"? Material cargado: {material['nombre']}")
        return render_template('materials/editar.html', material=material)

    except Exception as e:
        print(f"? Error en editar_material: {e}")
        import traceback
        print(f"?? TRACEBACK: {traceback.format_exc()}")
        flash('Error al procesar la solicitud', 'danger')
        return redirect(url_for('materiales.listar_materiales'))

@materiales_bp.route('/eliminar/<int:material_id>', methods=['POST'])
def eliminar_material(material_id):
    if not _require_login():
        return redirect('/login')

    # ? SOLO admin y lider_inventario pueden acceder
    if not _has_role('administrador', 'lider_inventario'):
        flash('No tiene permisos para acceder a esta sección', 'danger')
        return redirect('/dashboard')
        
    try:
        resultado = MaterialModel.eliminar(material_id)
        if resultado:
            flash('Material eliminado exitosamente', 'success')
        else:
            flash('Error al eliminar el material', 'danger')
    except Exception as e:
        print(f"? Error eliminando material: {e}")
        flash('Error al eliminar el material', 'danger')
    return redirect(url_for('materiales.listar_materiales'))