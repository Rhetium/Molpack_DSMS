"""
Servicio de Exportación — Genera PDF y Excel de fichas técnicas.

El PDF se genera escribiendo los datos SOBRE un archivo PDF plantilla
que el usuario configura. Si no hay plantilla, genera un PDF limpio.

Solo se pueden exportar fichas en estado Preliminar o Vigente.

Uso:
    service = ExportService(db_session)
    pdf_bytes = await service.exportar_ficha_pdf(id_ficha, plantilla_path=None)
    xlsx_bytes = await service.exportar_fichas_excel(filtros)
"""

import io
from uuid import UUID
from datetime import datetime

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import cm, mm
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.lib.enums import TA_LEFT, TA_CENTER

from pypdf import PdfReader, PdfWriter

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from app.models.ficha import FichaTecnica
from app.models.material import MaterialComercial


VERDE_OSCURO = HexColor('#044926')
VERDE_CLARO = HexColor('#29b34b')
GRIS = HexColor('#6b7280')
NEGRO = HexColor('#000000')


class ExportService:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def _obtener_ficha_con_material(self, id_ficha: UUID):
        """Obtiene ficha + material, valida estado exportable."""
        result = await self.db_session.execute(
            select(FichaTecnica).where(FichaTecnica.id_ficha == id_ficha)
        )
        ficha = result.scalars().first()
        if not ficha:
            raise HTTPException(status_code=404, detail="Ficha no encontrada")

        if ficha.estado_ficha not in ("Preliminar", "Vigente"):
            raise HTTPException(
                status_code=400,
                detail=f"Solo se pueden exportar fichas Preliminares o Vigentes. Estado actual: {ficha.estado_ficha}",
            )

        result_mat = await self.db_session.execute(
            select(MaterialComercial).where(
                MaterialComercial.id_material_corporativo == ficha.id_material_corporativo
            )
        )
        material = result_mat.scalars().first()

        return ficha, material

    # =============================================
    # EXPORTACIÓN PDF
    # =============================================

    async def exportar_ficha_pdf(
        self,
        id_ficha: UUID,
        plantilla_path: str | None = None,
    ) -> bytes:
        """
        Genera PDF de la ficha técnica.
        Si plantilla_path se proporciona, escribe los datos sobre esa plantilla.
        Si no, genera un PDF limpio con formato propio.
        """
        ficha, material = await self._obtener_ficha_con_material(id_ficha)

        # Generar overlay con los datos
        overlay_buffer = io.BytesIO()
        self._generar_overlay(overlay_buffer, ficha, material)
        overlay_buffer.seek(0)

        if plantilla_path:
            # Escribir sobre la plantilla
            return self._merge_con_plantilla(plantilla_path, overlay_buffer)
        else:
            # Sin plantilla, retornar el overlay directamente
            return overlay_buffer.getvalue()

    def _generar_overlay(self, buffer, ficha, material):
        """Genera el canvas con todos los datos de la ficha."""
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        # ---- PÁGINA 1: Info general + Características ----
        y = height - 50

        # Header
        c.setFont("Helvetica-Bold", 16)
        c.setFillColor(VERDE_OSCURO)
        c.drawString(50, y, "FICHA TÉCNICA")
        y -= 20

        c.setFont("Helvetica", 9)
        c.setFillColor(GRIS)
        c.drawString(50, y, f"Código: {ficha.codigo_ficha_local or ficha.codigo_material_local}")
        c.drawRightString(width - 50, y, f"Versión: {ficha.codigo_version}  |  Estado: {ficha.estado_ficha}")
        y -= 8

        # Línea separadora
        c.setStrokeColor(VERDE_CLARO)
        c.setLineWidth(2)
        c.line(50, y, width - 50, y)
        y -= 25

        # Info del material
        y = self._seccion_titulo(c, "INFORMACIÓN DEL MATERIAL", 50, y, width)
        y = self._campo(c, "Nombre Corporativo", material.nombre_corporativo if material else "—", 50, y)
        y = self._campo(c, "Categoría", material.categoria if material else "—", 50, y)
        y = self._campo(c, "Contenido", material.contenido if material else "—", 50, y)
        y = self._campo(c, "Material Base", material.material_base if material else "—", 50, y)
        y -= 10

        # Info de la ficha
        y = self._seccion_titulo(c, "DATOS DE LA FICHA", 50, y, width)
        y = self._campo(c, "País", ficha.pais or "—", 50, y)
        y = self._campo(c, "Código Local", ficha.codigo_material_local or "—", 50, y)
        color_ficha = ficha.caracteristicas.get("color", "—") if ficha.caracteristicas else "—"
        y = self._campo(c, "Color", color_ficha, 50, y)
        y = self._campo(c, "Fecha Creación", str(ficha.fecha_registro.strftime("%d/%m/%Y") if hasattr(ficha, 'fecha_registro') and ficha.fecha_registro else "—"), 50, y)
        y = self._campo(c, "Creador", ficha.usuario_creador or "—", 50, y)
        y -= 10

        # Características
        if ficha.caracteristicas:
            y = self._seccion_titulo(c, "CARACTERÍSTICAS FÍSICAS", 50, y, width)
            y = self._tabla_medidas(c, ficha.caracteristicas, 50, y, width)

        # Características de contenido
        if ficha.caracteristicas_contenido:
            if y < 150:
                c.showPage()
                y = height - 50
            y = self._seccion_titulo(c, "CARACTERÍSTICAS DE CONTENIDO", 50, y, width)
            y = self._tabla_medidas(c, ficha.caracteristicas_contenido, 50, y, width)

        # ---- PÁGINA 2: Empaque, Micro, Manejo ----
        c.showPage()
        y = height - 50

        # Empaque y estiba
        if ficha.empaque_estiba:
            y = self._seccion_titulo(c, "EMPAQUE Y ESTIBA", 50, y, width)
            y = self._tabla_medidas(c, ficha.empaque_estiba, 50, y, width)

        # Microbiología
        if ficha.microbiologia:
            if y < 200:
                c.showPage()
                y = height - 50
            y = self._seccion_titulo(c, "MICROBIOLOGÍA Y METALES PESADOS", 50, y, width)
            y = self._tabla_medidas(c, ficha.microbiologia, 50, y, width)

        # Manejo y disposición
        if ficha.manejo_disposicion:
            if y < 200:
                c.showPage()
                y = height - 50
            y = self._seccion_titulo(c, "MANEJO Y DISPOSICIÓN", 50, y, width)
            for clave, valor in ficha.manejo_disposicion.items():
                if valor and str(valor).strip():
                    y = self._campo_texto_largo(c, clave, str(valor), 50, y, width)
                    if y < 80:
                        c.showPage()
                        y = height - 50

        # Footer
        c.setFont("Helvetica", 7)
        c.setFillColor(GRIS)
        c.drawString(50, 30, f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}  |  DSMS Molpack Corporation")
        c.drawRightString(width - 50, 30, f"Ficha: {ficha.id_ficha}")

        c.save()

    def _merge_con_plantilla(self, plantilla_path: str, overlay_buffer) -> bytes:
        """Combina la plantilla PDF con el overlay de datos."""
        plantilla_reader = PdfReader(plantilla_path)
        overlay_reader = PdfReader(overlay_buffer)
        writer = PdfWriter()

        # Para cada página del overlay, merge con la plantilla
        for i, overlay_page in enumerate(overlay_reader.pages):
            if i < len(plantilla_reader.pages):
                # Usar página de plantilla como base
                base_page = plantilla_reader.pages[i]
                base_page.merge_page(overlay_page)
                writer.add_page(base_page)
            else:
                # Si el overlay tiene más páginas que la plantilla,
                # usar la última página de plantilla o una en blanco
                if len(plantilla_reader.pages) > 0:
                    from copy import copy
                    base_page = copy(plantilla_reader.pages[-1])
                    base_page.merge_page(overlay_page)
                    writer.add_page(base_page)
                else:
                    writer.add_page(overlay_page)

        output = io.BytesIO()
        writer.write(output)
        return output.getvalue()

    # ---- Helpers de dibujo ----

    def _seccion_titulo(self, c, titulo, x, y, width):
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(VERDE_OSCURO)
        c.drawString(x, y, titulo)
        y -= 3
        c.setStrokeColor(VERDE_CLARO)
        c.setLineWidth(0.5)
        c.line(x, y, width - 50, y)
        y -= 15
        return y

    def _campo(self, c, label, valor, x, y):
        c.setFont("Helvetica", 8)
        c.setFillColor(GRIS)
        c.drawString(x, y, label + ":")
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(NEGRO)
        c.drawString(x + 130, y, str(valor))
        y -= 16
        return y

    def _tabla_medidas(self, c, datos, x, y, width):
        """Dibuja tabla de medidas agrupando valor/tolerancia/unidad por propiedad."""
        if not datos:
            return y

        # Agrupar campos: buscar prefijos comunes (_valor, _tolerancia, _unidad)
        propiedades = {}
        for clave, valor in datos.items():
            if valor is None:
                continue
            if clave.endswith('_valor'):
                prefijo = clave.replace('_valor', '')
                propiedades.setdefault(prefijo, {})['valor'] = valor
            elif clave.endswith('_tolerancia'):
                prefijo = clave.replace('_tolerancia', '')
                propiedades.setdefault(prefijo, {})['tolerancia'] = valor
            elif clave.endswith('_unidad'):
                prefijo = clave.replace('_unidad', '')
                propiedades.setdefault(prefijo, {})['unidad'] = valor
            elif clave.endswith('_limite'):
                prefijo = clave.replace('_limite', '')
                propiedades.setdefault(prefijo, {})['limite'] = valor
            else:
                # Campo suelto sin sufijo (tipo_empaque, color_empaque, etc.)
                propiedades[clave] = {'valor': valor}

        if not propiedades:
            return y

        # Header de tabla
        col_prop = x + 10
        col_val = x + 180
        col_tol = x + 270
        col_uni = x + 360

        # Detectar si hay tolerancias o límites
        tiene_tolerancia = any('tolerancia' in v for v in propiedades.values())
        tiene_limite = any('limite' in v for v in propiedades.values())

        c.setFont("Helvetica-Bold", 7)
        c.setFillColor(GRIS)
        c.drawString(col_prop, y, "Propiedad")
        c.drawString(col_val, y, "Valor")
        if tiene_tolerancia:
            c.drawString(col_tol, y, "Tolerancia (±)")
        elif tiene_limite:
            c.drawString(col_tol, y, "Límite")
        c.drawString(col_uni, y, "Unidad")
        y -= 4

        c.setStrokeColor(GRIS)
        c.setLineWidth(0.3)
        c.line(col_prop, y, width - 50, y)
        y -= 12

        # Filas
        for prefijo, vals in propiedades.items():
            nombre = prefijo.replace("_", " ").title()
            c.setFont("Helvetica", 8)
            c.setFillColor(NEGRO)
            c.drawString(col_prop, y, nombre)

            c.setFont("Helvetica-Bold", 8)
            c.drawString(col_val, y, str(vals.get('valor', '')))

            c.setFont("Helvetica", 8)
            c.setFillColor(GRIS)
            if 'tolerancia' in vals:
                c.drawString(col_tol, y, f"± {vals['tolerancia']}")
            elif 'limite' in vals:
                c.drawString(col_tol, y, str(vals['limite']))

            if 'unidad' in vals:
                c.drawString(col_uni, y, str(vals['unidad']))

            c.setFillColor(NEGRO)
            y -= 14
            if y < 60:
                c.showPage()
                y = letter[1] - 50

        y -= 5
        return y

    def _campo_texto_largo(self, c, label, texto, x, y, width):
        nombre = label.replace("_", " ").title()
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(VERDE_OSCURO)
        c.drawString(x, y, nombre)
        y -= 14

        c.setFont("Helvetica", 8)
        c.setFillColor(NEGRO)

        # Word wrap manual
        max_width = width - 100
        words = texto.split()
        line = ""
        for word in words:
            test = line + " " + word if line else word
            if c.stringWidth(test, "Helvetica", 8) > max_width:
                c.drawString(x + 10, y, line)
                y -= 12
                line = word
            else:
                line = test
        if line:
            c.drawString(x + 10, y, line)
            y -= 12

        y -= 8
        return y

    # =============================================
    # EXPORTACIÓN EXCEL
    # =============================================

    async def exportar_fichas_excel(
        self,
        ktype: str | None = None,
    ) -> bytes:
        """Exporta listado de fichas a Excel."""
        query = select(FichaTecnica).where(
            FichaTecnica.estado_ficha.in_(["Preliminar", "Vigente"])
        )
        result = await self.db_session.execute(query)
        fichas = result.scalars().all()

        wb = Workbook()
        ws = wb.active
        ws.title = "Fichas Técnicas"

        # Estilos
        header_font = Font(bold=True, color="FFFFFF", size=10)
        header_fill = PatternFill("solid", fgColor="044926")
        header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
        thin_border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin"),
        )

        # Headers
        headers = [
            # Identificación
            "Código Ficha", "Código Local", "País", "Estado",
            "Versión", "Fecha Creación", "Creador", "Color",
            # Características
            "Largo (valor)", "Largo (tol)", "Largo (unid)",
            "Ancho (valor)", "Ancho (tol)", "Ancho (unid)",
            "Alto (valor)", "Alto (tol)", "Alto (unid)",
            "Peso (valor)", "Peso (tol)", "Peso (unid)",
            "Ruptura (valor)", "Ruptura (tol)", "Ruptura (unid)",
            "T. Encolado (valor)", "T. Encolado (tol)", "T. Encolado (unid)",
            "Absorción (valor)", "Absorción (tol)", "Absorción (unid)",
            "Defl. Int (valor)", "Defl. Int (tol)", "Defl. Int (unid)",
            "Defl. Ext (valor)", "Defl. Ext (tol)", "Defl. Ext (unid)",
            # Contenido
            "Prof. Pilar (valor)", "Prof. Pilar (tol)", "Prof. Pilar (unid)",
            "Diám. Alvéolo (valor)", "Diám. Alvéolo (tol)", "Diám. Alvéolo (unid)",
            "Prof. Cavidad (valor)", "Prof. Cavidad (tol)", "Prof. Cavidad (unid)",
            "Diám. Cavidad (valor)", "Diám. Cavidad (tol)", "Diám. Cavidad (unid)",
            # Empaque
            "Tipo Empaque", "Color Empaque",
            "Alto Emp. (valor)", "Alto Emp. (tol)", "Alto Emp. (unid)",
            "Peso Emp. (valor)", "Peso Emp. (tol)", "Peso Emp. (unid)",
            "Uds/Empaque", "Empaques/Estiba", "Camas/Estiba", "Empaques/Cama",
            # Microbiología
            "Aeróbico (valor)", "Aeróbico (lím)",
            "Moho (valor)", "Moho (lím)",
            "Coliforme (valor)", "Coliforme (lím)",
            "E. Coli (valor)", "E. Coli (lím)",
            "Salmonella (valor)", "Salmonella (lím)",
            "Cadmio", "Plomo", "Mercurio", "Cromo",
            # Manejo
            "Uso", "Manejo", "Almacenamiento", "Transporte", "Vida Útil",
        ]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_align
            cell.border = thin_border

        # Datos
        for row_idx, ficha in enumerate(fichas, 2):
            caract = ficha.caracteristicas or {}
            cont = ficha.caracteristicas_contenido or {}
            emp = ficha.empaque_estiba or {}
            micro = ficha.microbiologia or {}
            manejo = ficha.manejo_disposicion or {}

            fecha = ""
            if hasattr(ficha, 'fecha_registro') and ficha.fecha_registro:
                fecha = ficha.fecha_registro.strftime("%d/%m/%Y")

            data = [
                # Identificación
                ficha.codigo_ficha_local or "",
                ficha.codigo_material_local or "",
                ficha.pais or "",
                ficha.estado_ficha,
                ficha.codigo_version,
                fecha,
                ficha.usuario_creador or "",
                caract.get("color", ""),
                # Características
                caract.get("dimensiones_largo_valor"), caract.get("dimensiones_largo_tolerancia"), caract.get("dimensiones_largo_unidad"),
                caract.get("dimensiones_ancho_valor"), caract.get("dimensiones_ancho_tolerancia"), caract.get("dimensiones_ancho_unidad"),
                caract.get("dimensiones_alto_valor"), caract.get("dimensiones_alto_tolerancia"), caract.get("dimensiones_alto_unidad"),
                caract.get("peso_valor"), caract.get("peso_tolerancia"), caract.get("peso_unidad"),
                caract.get("ruptura_valor"), caract.get("ruptura_tolerancia"), caract.get("ruptura_unidad"),
                caract.get("tiempo_encolado_valor"), caract.get("tiempo_encolado_tolerancia"), caract.get("tiempo_encolado_unidad"),
                caract.get("porcentaje_absorcion_valor"), caract.get("porcentaje_absorcion_tolerancia"), caract.get("porcentaje_absorcion_unidad"),
                caract.get("deflexion_interna_valor"), caract.get("deflexion_interna_tolerancia"), caract.get("deflexion_interna_unidad"),
                caract.get("deflexion_externa_valor"), caract.get("deflexion_externa_tolerancia"), caract.get("deflexion_externa_unidad"),
                # Contenido
                cont.get("profundidad_pilar_valor"), cont.get("profundidad_pilar_tolerancia"), cont.get("profundidad_pilar_unidad"),
                cont.get("diametro_alveolo_valor"), cont.get("diametro_alveolo_tolerancia"), cont.get("diametro_alveolo_unidad"),
                cont.get("profundidad_cavidad_valor"), cont.get("profundidad_cavidad_tolerancia"), cont.get("profundidad_cavidad_unidad"),
                cont.get("diametro_cavidad_valor"), cont.get("diametro_cavidad_tolerancia"), cont.get("diametro_cavidad_unidad"),
                # Empaque
                emp.get("tipo_empaque"), emp.get("color_empaque"),
                emp.get("alto_empaque_valor"), emp.get("alto_empaque_tolerancia"), emp.get("alto_empaque_unidad"),
                emp.get("peso_empaque_valor"), emp.get("peso_empaque_tolerancia"), emp.get("peso_empaque_unidad"),
                emp.get("undidades_empaque"), emp.get("empaques_estiba"), emp.get("camas_estiba"), emp.get("empaques_camas_estiba"),
                # Microbiología
                micro.get("recuento_aerobico_valor"), micro.get("recuento_aerobico_limite"),
                micro.get("recuento_moho_valor"), micro.get("recuento_moho_limite"),
                micro.get("coliforme_valor"), micro.get("coliforme_limite"),
                micro.get("escherichia_coli_valor"), micro.get("escherichia_coli_limite"),
                micro.get("salmonella_spp_valor"), micro.get("salmonella_spp_limite"),
                micro.get("cadmio_valor"), micro.get("plomo_valor"), micro.get("mercurio_valor"), micro.get("cromo_valor"),
                # Manejo
                manejo.get("uso"), manejo.get("manejo"), manejo.get("almacenamiento"),
                manejo.get("transporte"), manejo.get("vida_util"),
            ]
            for col, valor in enumerate(data, 1):
                cell = ws.cell(row=row_idx, column=col, value=valor)
                cell.border = thin_border
                cell.alignment = Alignment(horizontal="center", wrap_text=True)

        # Ancho de columnas
        for col in range(1, len(headers) + 1):
            ws.column_dimensions[ws.cell(row=1, column=col).column_letter].width = 16

        # Columnas de texto más anchas
        manejo_start = len(headers) - 4
        for i in range(manejo_start, len(headers) + 1):
            ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = 30

        output = io.BytesIO()
        wb.save(output)
        return output.getvalue()