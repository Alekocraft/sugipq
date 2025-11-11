# blueprints/reportes.py
from flask import Blueprint, render_template, request, redirect, session, flash, url_for, jsonify, send_file
from io import BytesIO
import pandas as pd
from datetime import datetime
from models.solicitudes_model import SolicitudModel
from models.materiales_model import MaterialModel
from models.oficinas_model import OficinaModel
from utils.filters import filtrar_por_oficina_usuario, verificar_acceso_oficina

# Crear blueprint de reportes
reportes_bp = Blueprint('reportes', __name__, url_prefix='/reportes')

# Helpers de autenticación locales
def _require_login():
    return 'usuario_id' in session

@reportes_bp.route('/')
def reportes_index():
    if not _require_login():
        return redirect('/login')
    
    try:
        todas_solicitudes = SolicitudModel.obtener_todas() or []
        todos_materiales = MaterialModel.obtener_todos() or []
        todas_oficinas = OficinaModel.obtener_todas() or []

        solicitudes = filtrar_por_oficina_usuario(todas_solicitudes, 'oficina_id')
        materiales = filtrar_por_oficina_usuario(todos_materiales, 'oficina_id')
        oficinas = filtrar_por_oficina_usuario(todas_oficinas)

        total_solicitudes = len(solicitudes)
        solicitudes_pendientes = len([s for s in solicitudes if s.get('estado', '').lower() == 'pendiente'])
        solicitudes_aprobadas = len([s for s in solicitudes if s.get('estado', '').lower() == 'aprobada'])
        solicitudes_rechazadas = len([s for s in solicitudes if s.get('estado', '').lower() == 'rechazada'])

        materiales_bajo_stock = len([m for m in materiales if m.get('cantidad', 0) <= 10])
        valor_total_inventario = sum(m.get('valor_total', 0) or 0 for m in materiales)
        total_oficinas = len(oficinas)

        return render_template('reportes/index.html',
                            total_solicitudes=total_solicitudes,
                            solicitudes_pendientes=solicitudes_pendientes,
                            solicitudes_aprobadas=solicitudes_aprobadas,
                            solicitudes_rechazadas=solicitudes_rechazadas,
                            materiales_bajo_stock=materiales_bajo_stock,
                            valor_total_inventario=valor_total_inventario,
                            total_oficinas=total_oficinas)
    except Exception as e:
        print(f"❌ Error cargando reportes: {e}")
        return render_template('reportes/index.html',
                            total_solicitudes=0,
                            solicitudes_pendientes=0,
                            solicitudes_aprobadas=0,
                            solicitudes_rechazadas=0,
                            materiales_bajo_stock=0,
                            valor_total_inventario=0,
                            total_oficinas=0)

@reportes_bp.route('/materiales')
def reporte_materiales():
    if not _require_login():
        return redirect('/login')
    
    try:
        todos_materiales = MaterialModel.obtener_todos() or []
        materiales = filtrar_por_oficina_usuario(todos_materiales, 'oficina_id')

        todas_solicitudes = SolicitudModel.obtener_todas() or []
        solicitudes_filtradas = filtrar_por_oficina_usuario(todas_solicitudes, 'oficina_id')

        valor_total_inventario = sum(m.get('valor_total', 0) or 0 for m in materiales)
        total_solicitudes = len(solicitudes_filtradas)
        total_entregado = sum((m.get('cantidad', 0) or 0) for m in materiales)

        stats_dict = {}
        for material in materiales:
            material_id = material['id']
            solicitudes_mat = [s for s in solicitudes_filtradas if s.get('material_id') == material_id]
            total_sol = len(solicitudes_mat)
            aprobadas = len([s for s in solicitudes_mat if s.get('estado', '').lower() == 'aprobada'])
            pendientes = len([s for s in solicitudes_mat if s.get('estado', '').lower() == 'pendiente'])
            entregado = sum((s.get('cantidad_solicitada', 0) or 0) for s in solicitudes_mat if s.get('estado', '').lower() == 'aprobada')
            stats_dict[material_id] = [total_sol, aprobadas, pendientes, entregado, 0, 0, 0]

        return render_template('reportes/materiales.html',
                             materiales=materiales,
                             valor_total_inventario=valor_total_inventario,
                             total_solicitudes=total_solicitudes,
                             total_entregado=total_entregado,
                             stats_dict=stats_dict)
    except Exception as e:
        print(f"❌ Error generando reporte de materiales: {e}")
        flash('Error al generar el reporte de materiales', 'danger')
        return render_template('reportes/materiales.html',
                             materiales=[],
                             valor_total_inventario=0,
                             total_solicitudes=0,
                             total_entregado=0,
                             stats_dict={})

@reportes_bp.route('/materiales/exportar/excel')
def exportar_materiales_excel():
    if not _require_login():
        return redirect('/login')
    
    try:
        todos_materiales = MaterialModel.obtener_todos() or []
        materiales = filtrar_por_oficina_usuario(todos_materiales, 'oficina_id')

        data = []
        for mat in materiales:
            data.append({
                'ID': mat.get('id', ''),
                'Nombre': mat.get('nombre', ''),
                'Valor Unitario': mat.get('valor_unitario', 0),
                'Cantidad': mat.get('cantidad', 0),
                'Valor Total': mat.get('valor_total', 0),
                'Oficina': mat.get('oficina_nombre', ''),
                'Creado por': mat.get('usuario_creador', ''),
                'Fecha Creación': mat.get('fecha_creacion', '')
            })

        df = pd.DataFrame(data)
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Materiales', index=False)
            worksheet = writer.sheets['Materiales']
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                worksheet.column_dimensions[column_letter].width = (max_length + 2)
        output.seek(0)

        fecha_actual = pd.Timestamp.now().strftime('%Y-%m-%d')
        filename = f'reporte_materiales_{fecha_actual}.xlsx'

        return send_file(output,
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                         as_attachment=True,
                         download_name=filename)
    except Exception as e:
        print(f"❌ Error exportando materiales a Excel: {e}")
        flash('Error al exportar el reporte de materiales a Excel', 'danger')
        return redirect(url_for('reportes.reporte_materiales'))

@reportes_bp.route('/inventario')
def reporte_inventario():
    if not _require_login():
        return redirect('/login')
    
    try:
        todos_materiales = MaterialModel.obtener_todos() or []
        materiales = filtrar_por_oficina_usuario(todos_materiales, 'oficina_id')

        materiales_bajo_stock = [m for m in materiales if (m.get('cantidad', 0) or 0) <= 10]
        materiales_stock_normal = [m for m in materiales if (m.get('cantidad', 0) or 0) > 10]
        materiales_sin_stock = [m for m in materiales if (m.get('cantidad', 0) or 0) == 0]

        valor_bajo_stock = sum((m.get('valor_total', 0) or 0) for m in materiales_bajo_stock)
        valor_stock_normal = sum((m.get('valor_total', 0) or 0) for m in materiales_stock_normal)
        valor_total = sum((m.get('valor_total', 0) or 0) for m in materiales)
        cantidad_total = sum((m.get('cantidad', 0) or 0) for m in materiales)

        return render_template('reportes/inventario.html',
                            materiales=materiales,
                            materiales_bajo_stock=materiales_bajo_stock,
                            materiales_stock_normal=materiales_stock_normal,
                            materiales_sin_stock=materiales_sin_stock,
                            valor_bajo_stock=valor_bajo_stock,
                            valor_stock_normal=valor_stock_normal,
                            valor_total=valor_total,
                            cantidad_total=cantidad_total)
    except Exception as e:
        print(f"❌ Error generando reporte de inventario: {e}")
        flash('Error al generar el reporte de inventario', 'danger')
        return render_template('reportes/inventario.html',
                            materiales=[],
                            materiales_bajo_stock=[],
                            materiales_stock_normal=[],
                            materiales_sin_stock=[],
                            valor_bajo_stock=0,
                            valor_stock_normal=0,
                            valor_total=0,
                            cantidad_total=0)

@reportes_bp.route('/solicitudes')
def reporte_solicitudes():
    if not _require_login():
        return redirect('/login')
    
    try:
        todas_solicitudes = SolicitudModel.obtener_todas() or []
        todos_materiales = MaterialModel.obtener_todos() or []
        todas_oficinas = OficinaModel.obtener_todas() or []

        solicitudes = filtrar_por_oficina_usuario(todas_solicitudes, 'oficina_id')
        materiales = filtrar_por_oficina_usuario(todos_materiales, 'oficina_id')
        oficinas_filtradas = filtrar_por_oficina_usuario(todas_oficinas)
        materiales_dict = {mat['id']: mat for mat in materiales}

        oficinas_unique = list(set([oficina['nombre'] for oficina in oficinas_filtradas if oficina.get('nombre')]))

        filtro_estado = request.args.get('estado', 'todos')
        filtro_oficina = request.args.get('oficina', 'todas')
        filtro_material = request.args.get('material', '').lower()
        filtro_solicitante = request.args.get('solicitante', '').lower()

        solicitudes_filtradas = solicitudes.copy()

        if filtro_estado != 'todos':
            solicitudes_filtradas = [s for s in solicitudes_filtradas if s.get('estado', '').lower() == filtro_estado.lower()]
        if filtro_oficina != 'todas':
            solicitudes_filtradas = [s for s in solicitudes_filtradas if s.get('oficina_nombre', '') == filtro_oficina]
        if filtro_material:
            solicitudes_filtradas = [s for s in solicitudes_filtradas if filtro_material in s.get('material_nombre', '').lower()]
        if filtro_solicitante:
            solicitudes_filtradas = [s for s in solicitudes_filtradas if filtro_solicitante in s.get('usuario_solicitante', '').lower()]

        total_solicitudes = len(solicitudes_filtradas)
        solicitudes_pendientes = len([s for s in solicitudes_filtradas if s.get('estado', '').lower() == 'pendiente'])
        solicitudes_aprobadas = len([s for s in solicitudes_filtradas if s.get('estado', '').lower() == 'aprobada'])
        solicitudes_rechazadas = len([s for s in solicitudes_filtradas if s.get('estado', '').lower() == 'rechazada'])

        return render_template('reportes/solicitudes.html',
                             solicitudes=solicitudes_filtradas,
                             materiales_dict=materiales_dict,
                             oficinas_unique=oficinas_unique,
                             total_solicitudes=total_solicitudes,
                             solicitudes_pendientes=solicitudes_pendientes,
                             solicitudes_aprobadas=solicitudes_aprobadas,
                             solicitudes_rechazadas=solicitudes_rechazadas,
                             filtro_estado=filtro_estado,
                             filtro_oficina=filtro_oficina)
    except Exception as e:
        print(f"❌ Error generando reporte de solicitudes: {e}")
        flash('Error al generar el reporte de solicitudes', 'danger')
        return render_template('reportes/solicitudes.html',
                             solicitudes=[],
                             materiales_dict={},
                             oficinas_unique=[],
                             total_solicitudes=0,
                             solicitudes_pendientes=0,
                             solicitudes_aprobadas=0,
                             solicitudes_rechazadas=0,
                             filtro_estado='todos',
                             filtro_oficina='todas')

@reportes_bp.route('/material/<int:id>')
def reporte_material_detalle(id):
    if not _require_login():
        return redirect('/login')
    
    try:
        material = MaterialModel.obtener_por_id(id)
        if not material:
            flash('Material no encontrado', 'danger')
            return redirect(url_for('reportes.reporte_materiales'))

        if not verificar_acceso_oficina(material.get('oficina_id')):
            flash('No tiene permisos para acceder a este material', 'danger')
            return redirect(url_for('reportes.reporte_materiales'))

        oficina = OficinaModel.obtener_por_id(material.get('oficina_id', 1))
        oficina_nombre = oficina.get('nombre', 'Sede Principal') if oficina else 'Sede Principal'
        material['oficina_nombre'] = oficina_nombre

        todas_solicitudes = SolicitudModel.obtener_todas() or []
        if session.get('rol') in ['administrador', 'lider_inventario']:
            solicitudes = todas_solicitudes
        else:
            solicitudes = filtrar_por_oficina_usuario(todas_solicitudes, 'oficina_id')

        solicitudes_filtradas = filtrar_por_oficina_usuario(todas_solicitudes, 'oficina_id')
        solicitudes_material = [s for s in solicitudes_filtradas if s.get('material_id') == id]

        total_solicitudes = len(solicitudes_material)
        solicitudes_aprobadas = len([s for s in solicitudes_material if s.get('estado', '').lower() == 'aprobada'])

        return render_template('reportes/material_detalle.html',
                         material=material,
                         solicitudes=solicitudes_material,
                         total_solicitudes=total_solicitudes,
                         solicitudes_aprobadas=solicitudes_aprobadas)
    except Exception as e:
        print(f"❌ Error cargando detalle de material: {e}")
        flash('Error al cargar el detalle del material', 'danger')
        return redirect(url_for('reportes.reporte_materiales'))


# 🔽🔽 NUEVAS FUNCIONES AGREGADAS 🔽🔽

@reportes_bp.route('/solicitudes/exportar/excel')
def exportar_solicitudes_excel():
    if not _require_login():
        return redirect('/login')
    
    try:
        filtro_estado = request.args.get('estado', 'todos')
        filtro_oficina = request.args.get('oficina', 'todas')
        filtro_material = request.args.get('material', '').lower()
        filtro_solicitante = request.args.get('solicitante', '').lower()

        todas_solicitudes = SolicitudModel.obtener_todas() or []
        todos_materiales = MaterialModel.obtener_todos() or []
        todas_oficinas = OficinaModel.obtener_todas() or []

        solicitudes = filtrar_por_oficina_usuario(todas_solicitudes, 'oficina_id')
        materiales = filtrar_por_oficina_usuario(todos_materiales, 'oficina_id')
        oficinas_filtradas = filtrar_por_oficina_usuario(todas_oficinas)
        materiales_dict = {mat['id']: mat for mat in materiales}

        solicitudes_filtradas = solicitudes.copy()

        if filtro_estado != 'todos':
            solicitudes_filtradas = [s for s in solicitudes_filtradas if s.get('estado', '').lower() == filtro_estado.lower()]
        if filtro_oficina != 'todas':
            solicitudes_filtradas = [s for s in solicitudes_filtradas if s.get('oficina_nombre', '') == filtro_oficina]
        if filtro_material:
            solicitudes_filtradas = [s for s in solicitudes_filtradas if filtro_material in s.get('material_nombre', '').lower()]
        if filtro_solicitante:
            solicitudes_filtradas = [s for s in solicitudes_filtradas if filtro_solicitante in s.get('usuario_solicitante', '').lower()]

        data = []
        for sol in solicitudes_filtradas:
            material_nombre = sol.get('material_nombre', 'N/A')
            if materiales_dict and materiales_dict.get(sol.get('material_id')):
                material_nombre = materiales_dict[sol.get('material_id')].get('nombre', material_nombre)
            data.append({
                'ID': sol.get('id', ''),
                'Material': material_nombre,
                'Cantidad Solicitada': sol.get('cantidad_solicitada', 0),
                'Cantidad Aprobada': sol.get('cantidad_aprobada', 0),
                'Solicitante': sol.get('usuario_solicitante', ''),
                'Oficina': sol.get('oficina_nombre', ''),
                'Estado': sol.get('estado', ''),
                'Fecha Solicitud': sol.get('fecha_solicitud', ''),
                'Fecha Aprobación': sol.get('fecha_aprobacion', ''),
                'Observaciones': sol.get('observacion', '')
            })

        df = pd.DataFrame(data)
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Solicitudes', index=False)
            worksheet = writer.sheets['Solicitudes']
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                worksheet.column_dimensions[column_letter].width = (max_length + 2)
        output.seek(0)

        fecha_actual = pd.Timestamp.now().strftime('%Y-%m-%d')
        filename = f'reporte_solicitudes_{fecha_actual}.xlsx'

        return send_file(output,
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                         as_attachment=True,
                         download_name=filename)
    except Exception as e:
        print(f"❌ Error exportando solicitudes a Excel: {e}")
        flash('Error al exportar el reporte de solicitudes a Excel', 'danger')
        return redirect(url_for('reportes.reporte_solicitudes'))


@reportes_bp.route('/inventario/exportar/excel')
def exportar_inventario_excel():
    if not _require_login():
        return redirect('/login')
    
    try:
        todos_materiales = MaterialModel.obtener_todos() or []
        materiales = filtrar_por_oficina_usuario(todos_materiales, 'oficina_id')

        materiales_bajo_stock = [m for m in materiales if (m.get('cantidad', 0) or 0) <= 10]
        materiales_stock_normal = [m for m in materiales if (m.get('cantidad', 0) or 0) > 10]

        def crear_dataframe_materiales(lista_materiales, nombre_hoja):
            data = []
            for mat in lista_materiales:
                data.append({
                    'ID': mat.get('id', ''),
                    'Material': mat.get('nombre', ''),
                    'Stock Actual': mat.get('cantidad', 0),
                    'Valor Unitario': mat.get('valor_unitario', 0),
                    'Valor Total': mat.get('valor_total', 0),
                    'Oficina': mat.get('oficina_nombre', ''),
                    'Creado por': mat.get('usuario_creador', ''),
                    'Fecha Creación': mat.get('fecha_creacion', '')
                })
            return pd.DataFrame(data)

        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            if materiales_bajo_stock:
                df_bajo_stock = crear_dataframe_materiales(materiales_bajo_stock, 'Bajo Stock')
                df_bajo_stock.to_excel(writer, sheet_name='Bajo Stock', index=False)
            if materiales_stock_normal:
                df_stock_normal = crear_dataframe_materiales(materiales_stock_normal, 'Stock Normal')
                df_stock_normal.to_excel(writer, sheet_name='Stock Normal', index=False)

            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    worksheet.column_dimensions[column_letter].width = (max_length + 2)
        output.seek(0)

        fecha_actual = pd.Timestamp.now().strftime('%Y-%m-%d')
        filename = f'reporte_inventario_{fecha_actual}.xlsx'

        return send_file(output,
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                         as_attachment=True,
                         download_name=filename)
    except Exception as e:
        print(f"❌ Error exportando inventario a Excel: {e}")
        flash('Error al exportar el reporte de inventario a Excel', 'danger')
        return redirect(url_for('reportes.reporte_inventario'))
