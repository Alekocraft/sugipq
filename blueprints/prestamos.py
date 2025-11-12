from flask import Blueprint, render_template, request, redirect, url_for, flash, session, send_file, after_this_request
from utils.permissions import can_access
from io import BytesIO
from datetime import datetime
import pandas as pd
import tempfile
import os

# Si estos vienen de otro módulo, importa de allí:
# from models.prestamo import PrestamoModel
# from utils.filtros import filtrar_por_oficina_usuario

prestamos_bp = Blueprint('prestamos', __name__)

# =========================
# Rutas existentes
# =========================
@prestamos_bp.route('/prestamos/elementos/crearmaterial', methods=['GET', 'POST'])
def crear_material_prestamo():
    """Ruta para crear materiales en el módulo de préstamos"""
    if not can_access('materiales', 'create'):
        flash('❌ No tienes permisos para crear materiales', 'danger')
        print(f"🚫 Acceso denegado a crear material - Usuario: {session.get('usuario_nombre')}, Rol: {session.get('rol')}")
        return redirect('/prestamos')

    if request.method == 'POST':
        nombre = request.form.get('nombre')
        # TODO: lógica para crear el material con `nombre` ...
        flash('Material creado exitosamente', 'success')
        return redirect('/prestamos/elementos')

    return render_template('prestamos/crear_material.html')


@prestamos_bp.route('/prestamos')
def listar_prestamos():
    """Listar todos los préstamos (accesible)"""
    return render_template('prestamos/listar.html')


@prestamos_bp.route('/prestamos/crear', methods=['GET', 'POST'])
def crear_prestamo():
    """Crear nuevo préstamo"""
    if not can_access('prestamos', 'create'):
        flash('No tienes permisos para crear préstamos', 'danger')
        return redirect('/prestamos')
    # TODO: Lógica para crear préstamo...
    return render_template('prestamos/crear_prestamo.html')


# =========================
# Exportaciones
# =========================
@prestamos_bp.route('/prestamos/exportar/excel')
def exportar_prestamos_excel():
    """
    Exporta los préstamos filtrados a Excel.
    Permiso sugerido: leer/exportar préstamos.
    """
    # Puedes usar 'read' o un permiso específico como 'export'
    if not can_access('prestamos', 'read'):
        flash('❌ No tienes permisos para exportar préstamos', 'danger')
        return redirect(url_for('prestamos.listar_prestamos'))

    try:
        # Parámetros de filtro
        filtro_estado = request.args.get('estado', '').strip()

        # Obtener y filtrar préstamos
        todos_prestamos = PrestamoModel.obtener_todos() or []
        prestamos = filtrar_por_oficina_usuario(todos_prestamos, 'oficina_id')

        if filtro_estado:
            prestamos = [p for p in prestamos if p.get('estado', '') == filtro_estado]

        # Armar DataFrame
        columnas = [
            'ID', 'Material', 'Cantidad', 'Valor Unitario', 'Subtotal',
            'Solicitante', 'Oficina', 'Fecha Préstamo', 'Fecha Devolución Esperada', 'Estado'
        ]
        data = [{
            'ID': p.get('id', ''),
            'Material': p.get('material', ''),
            'Cantidad': p.get('cantidad', 0),
            'Valor Unitario': p.get('valor_unitario', 0),
            'Subtotal': p.get('subtotal', 0),
            'Solicitante': p.get('solicitante_nombre', ''),
            'Oficina': p.get('oficina_nombre', ''),
            'Fecha Préstamo': p.get('fecha', ''),
            'Fecha Devolución Esperada': p.get('fecha_prevista', ''),
            'Estado': p.get('estado', '')
        } for p in prestamos]

        df = pd.DataFrame(data, columns=columnas)

        # Crear Excel en memoria
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Préstamos', index=False)

            # Ajuste de ancho de columnas (openpyxl)
            ws = writer.sheets['Préstamos']
            for col_cells in ws.columns:
                max_len = 0
                col_letter = col_cells[0].column_letter
                for c in col_cells:
                    try:
                        max_len = max(max_len, len(str(c.value)) if c.value is not None else 0)
                    except Exception:
                        pass
                ws.column_dimensions[col_letter].width = max_len + 2

        output.seek(0)

        fecha_actual = datetime.now().strftime('%Y-%m-%d')
        filename = f'prestamos_{fecha_actual}.xlsx'

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        print(f"❌ Error exportando préstamos a Excel: {e}")
        flash('Error al exportar el reporte de préstamos a Excel', 'danger')
        return redirect(url_for('prestamos.listar_prestamos'))


@prestamos_bp.route('/prestamos/exportar/pdf')
def exportar_prestamos_pdf():
    """
    Exporta los préstamos filtrados a PDF (WeasyPrint).
    Permiso sugerido: leer/exportar préstamos.
    """
    if not can_access('prestamos', 'read'):
        flash('❌ No tienes permisos para exportar préstamos', 'danger')
        return redirect(url_for('prestamos.listar_prestamos'))

    try:
        from weasyprint import HTML  # requiere weasyprint instalado

        # Parámetros de filtro
        filtro_estado = request.args.get('estado', '').strip()

        # Obtener y filtrar préstamos
        todos_prestamos = PrestamoModel.obtener_todos() or []
        prestamos = filtrar_por_oficina_usuario(todos_prestamos, 'oficina_id')

        if filtro_estado:
            prestamos = [p for p in prestamos if p.get('estado', '') == filtro_estado]

        # HTML del PDF
        filas_html = "\n".join(f"""
            <tr>
                <td>{p.get('id', '')}</td>
                <td>{p.get('material', '')}</td>
                <td>{p.get('cantidad', 0)}</td>
                <td>{p.get('solicitante_nombre', '')}</td>
                <td>{p.get('oficina_nombre', '')}</td>
                <td>{p.get('fecha', '')}</td>
                <td>{p.get('estado', '')}</td>
            </tr>
        """ for p in prestamos)

        html_content = f"""
        <html>
        <head>
            <meta charset="utf-8" />
            <style>
                body {{ font-family: Arial, sans-serif; font-size: 12px; }}
                h1 {{ margin: 0; }}
                .header {{ text-align: center; margin-bottom: 16px; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th, td {{ border: 1px solid #ddd; padding: 6px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .meta {{ color: #555; font-size: 11px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Reporte de Préstamos</h1>
                <div class="meta">
                    Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}<br/>
                    Total de préstamos: {len(prestamos)}
                </div>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Material</th>
                        <th>Cantidad</th>
                        <th>Solicitante</th>
                        <th>Oficina</th>
                        <th>Fecha</th>
                        <th>Estado</th>
                    </tr>
                </thead>
                <tbody>
                    {filas_html}
                </tbody>
            </table>
        </body>
        </html>
        """

        # Crear PDF temporal y asegurarnos de borrarlo después de enviar
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        tmp_path = tmp.name
        tmp.close()
        HTML(string=html_content).write_pdf(tmp_path)

        @after_this_request
        def _remove_file(response):
            try:
                os.remove(tmp_path)
            except Exception as _:
                pass
            return response

        fecha_actual = datetime.now().strftime('%Y-%m-%d')
        filename = f'prestamos_{fecha_actual}.pdf'

        return send_file(
            tmp_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        print(f"❌ Error exportando préstamos a PDF: {e}")
        flash('Error al exportar el reporte de préstamos a PDF', 'danger')
        return redirect(url_for('prestamos.listar_prestamos'))
