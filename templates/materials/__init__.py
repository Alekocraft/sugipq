#_ini_.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models.materiales_model import MaterialModel
from models.oficinas_model import OficinaModel

materiales_bp = Blueprint('materiales', __name__, template_folder='../templates/materiales')

@materiales_bp.route('/')
def listar():
    if 'usuario_id' not in session:
        flash('Debe iniciar sesión para acceder a esta página', 'danger')
        return redirect(url_for('auth.login'))
    
    materiales = MaterialModel.obtener_todos()
    return render_template('materiales/listar.html', materiales=materiales)

@materiales_bp.route('/crear', methods=['GET', 'POST'])
def crear():
    if 'usuario_id' not in session:
        flash('Debe iniciar sesión para acceder a esta página', 'danger')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        cantidad = int(request.form['cantidad'])
        cantidad_minima = int(request.form['cantidad_minima'])
        oficina_id = int(request.form['oficina_id'])
        
        material_id = MaterialModel.crear(nombre, descripcion, cantidad, cantidad_minima, oficina_id)
        if material_id:
            flash('Material creado exitosamente', 'success')
            return redirect(url_for('materiales.listar'))
        else:
            flash('Error al crear el material', 'danger')
    
    oficinas = OficinaModel.obtener_todas()
    return render_template('materiales/crear.html', oficinas=oficinas)

@materiales_bp.route('/editar/<int:id>', methods=['GET'])
def editar(id):
    if 'usuario_id' not in session:
        flash('Debe iniciar sesión para acceder a esta página', 'danger')
        return redirect(url_for('auth.login'))
    
    material = MaterialModel.obtener_por_id(id)
    oficinas = OficinaModel.obtener_todas()
    
    if not material:
        flash('Material no encontrado', 'danger')
        return redirect(url_for('materiales.listar'))
    
    return render_template('materiales/editar.html', material=material, oficinas=oficinas)

@materiales_bp.route('/actualizar/<int:id>', methods=['POST'])
def actualizar(id):
    if 'usuario_id' not in session:
        flash('Debe iniciar sesión para acceder a esta página', 'danger')
        return redirect(url_for('auth.login'))
    
    nombre = request.form['nombre']
    descripcion = request.form['descripcion']
    cantidad = int(request.form['cantidad'])
    cantidad_minima = int(request.form['cantidad_minima'])
    oficina_id = int(request.form['oficina_id'])
    
    if MaterialModel.actualizar(id, nombre, descripcion, cantidad, cantidad_minima, oficina_id):
        flash('Material actualizado exitosamente', 'success')
    else:
        flash('Error al actualizar el material', 'danger')
    
    return redirect(url_for('materiales.listar'))

@materiales_bp.route('/eliminar/<int:id>', methods=['POST'])
def eliminar(id):
    if 'usuario_id' not in session:
        flash('Debe iniciar sesión para acceder a esta página', 'danger')
        return redirect(url_for('auth.login'))
    
    if MaterialModel.eliminar(id):
        flash('Material eliminado exitosamente', 'success')
    else:
        flash('Error al eliminar el material', 'danger')
    
    return redirect(url_for('materiales.listar'))