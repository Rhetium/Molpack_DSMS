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
import os
from uuid import UUID
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from pypdf import PdfReader, PdfWriter

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from app.models.ficha import FichaTecnica
from app.models.material import MaterialComercial
from app.models.kitem import KItem


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

        y = self._dibujar_cabecera(c, ficha, width, height)
        y = self._dibujar_seccion_info(c, ficha, material, y)
        y = self._dibujar_caracteristicas_p1(c, ficha, y, width, height)

        c.showPage()
        self._dibujar_pagina2(c, ficha, width, height)

        c.save()

    def _dibujar_cabecera(self, c, ficha, width, height):
        y = height - 50
        c.setFont("Helvetica-Bold", 16)
        c.setFillColor(VERDE_OSCURO)
        c.drawString(50, y, "FICHA TÉCNICA")
        y -= 20
        c.setFont("Helvetica", 9)
        c.setFillColor(GRIS)
        c.drawString(50, y, f"Código: {ficha.codigo_ficha_local or ficha.codigo_material_local}")
        c.drawRightString(width - 50, y, f"Versión: {ficha.codigo_version}  |  Estado: {ficha.estado_ficha}")
        y -= 8
        c.setStrokeColor(VERDE_CLARO)
        c.setLineWidth(2)
        c.line(50, y, width - 50, y)
        return y - 22

    def _dibujar_seccion_info(self, c, ficha, material, y_top):
        X_IZQ, X_DER = 50, 325
        COL_IZQ_W, COL_DER_W = 255, 220
        y_izq = self._dibujar_columna_info(c, ficha, material, X_IZQ, y_top, COL_IZQ_W)
        y_der = self._dibujar_imagenes(c, ficha, X_DER, y_top, COL_DER_W)
        return min(y_izq, y_der) - 18

    def _dibujar_columna_info(self, c, ficha, material, x, y, col_width):
        mat_nombre = material.nombre_corporativo if material else "—"
        mat_cat = material.categoria if material else "—"
        mat_cont = material.contenido if material else "—"
        mat_base = material.material_base if material else "—"

        y = self._seccion_titulo_col(c, "INFORMACIÓN DEL MATERIAL", x, y, col_width)
        y = self._campo_col(c, "Nombre Corporativo", mat_nombre, x, y, col_width)
        y = self._campo_col(c, "Categoría", mat_cat, x, y, col_width)
        y = self._campo_col(c, "Contenido", mat_cont, x, y, col_width)
        y = self._campo_col(c, "Material Base", mat_base, x, y, col_width)
        y -= 8

        color_ficha = (ficha.caracteristicas or {}).get("color", "—")
        fecha_str = ficha.fecha_registro.strftime("%d/%m/%Y") if getattr(ficha, "fecha_registro", None) else "—"

        y = self._seccion_titulo_col(c, "DATOS DE LA FICHA", x, y, col_width)
        y = self._campo_col(c, "País", ficha.pais or "—", x, y, col_width)
        y = self._campo_col(c, "Código Local", ficha.codigo_material_local or "—", x, y, col_width)
        y = self._campo_col(c, "Color", color_ficha, x, y, col_width)
        y = self._campo_col(c, "Fecha Creación", fecha_str, x, y, col_width)
        y = self._campo_col(c, "Creado por", ficha.usuario_creador or "—", x, y, col_width)
        return y

    def _dibujar_caracteristicas_p1(self, c, ficha, y, width, height):
        if ficha.caracteristicas:
            y = self._seccion_titulo(c, "CARACTERÍSTICAS FÍSICAS", 50, y, width)
            y = self._tabla_medidas(c, ficha.caracteristicas, 50, y, width)
        if ficha.caracteristicas_contenido:
            if y < 150:
                c.showPage()
                y = height - 50
            y = self._seccion_titulo(c, "CARACTERÍSTICAS DE CONTENIDO", 50, y, width)
            y = self._tabla_medidas(c, ficha.caracteristicas_contenido, 50, y, width)
        return y

    def _dibujar_pagina2(self, c, ficha, width, height):
        y = height - 50
        if ficha.empaque_estiba:
            y = self._seccion_titulo(c, "EMPAQUE Y ESTIBA", 50, y, width)
            y = self._tabla_medidas(c, ficha.empaque_estiba, 50, y, width)
        if ficha.microbiologia:
            if y < 200:
                c.showPage()
                y = height - 50
            y = self._seccion_titulo(c, "MICROBIOLOGÍA Y METALES PESADOS", 50, y, width)
            y = self._tabla_medidas(c, ficha.microbiologia, 50, y, width)
        if ficha.manejo_disposicion:
            if y < 200:
                c.showPage()
                y = height - 50
            y = self._dibujar_manejo(c, ficha.manejo_disposicion, y, width, height)
        c.setFont("Helvetica", 7)
        c.setFillColor(GRIS)
        c.drawString(50, 30, f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}  |  DSMS Molpack Corporation")
        c.drawRightString(width - 50, 30, f"Ficha: {ficha.id_ficha}")

    def _dibujar_manejo(self, c, manejo, y, width, height):
        y = self._seccion_titulo(c, "MANEJO Y DISPOSICIÓN", 50, y, width)
        for clave, valor in manejo.items():
            if valor and str(valor).strip():
                y = self._campo_texto_largo(c, clave, str(valor), 50, y, width)
                if y < 80:
                    c.showPage()
                    y = height - 50
        return y

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

    def _seccion_titulo_col(self, c, titulo, x, y, col_width):
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(VERDE_OSCURO)
        c.drawString(x, y, titulo)
        y -= 3
        c.setStrokeColor(VERDE_CLARO)
        c.setLineWidth(0.5)
        c.line(x, y, x + col_width, y)
        y -= 13
        return y

    def _campo_col(self, c, label, valor, x, y, col_width):
        label_w = 92
        val_x = x + label_w + 4
        max_val_w = col_width - label_w - 6
        c.setFont("Helvetica", 7.5)
        c.setFillColor(GRIS)
        c.drawString(x, y, label + ":")
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(NEGRO)
        valor_str = str(valor)
        while c.stringWidth(valor_str, "Helvetica-Bold", 8) > max_val_w and len(valor_str) > 3:
            valor_str = valor_str[:-1]
        if valor_str != str(valor):
            valor_str = valor_str[:-1] + "…"
        c.drawString(val_x, y, valor_str)
        y -= 14
        return y

    def _dibujar_imagenes(self, c, ficha, x, y, col_width):
        imagenes = (ficha.caracteristicas or {}).get("imagenes", {})
        if not imagenes:
            return y
        img_h = 105
        label_h = 13
        gap = 10
        tipos = [("foto_producto", "FOTO DEL PRODUCTO"), ("plano_mecanico", "PLANO MECÁNICO")]
        for tipo_id, tipo_label in tipos:
            info = imagenes.get(tipo_id)
            if not info:
                continue
            ruta = info.get("ruta", "")
            if not ruta or not os.path.exists(ruta):
                continue
            try:
                img = ImageReader(ruta)
                c.setFont("Helvetica-Bold", 7)
                c.setFillColor(GRIS)
                c.drawString(x, y, tipo_label)
                y -= label_h
                img_bottom = y - img_h
                c.drawImage(img, x, img_bottom, width=col_width, height=img_h, preserveAspectRatio=True, mask='auto')
                c.setStrokeColor(GRIS)
                c.setLineWidth(0.3)
                c.rect(x, img_bottom, col_width, img_h)
                y = img_bottom - gap
            except Exception:  # noqa: BLE001
                continue
        return y

    def _tabla_medidas(self, c, datos, x, y, width):
        propiedades = self._agrupar_propiedades(datos)
        if not propiedades:
            return y
        tiene_tol = any('tolerancia' in v for v in propiedades.values())
        tiene_lim = any('limite' in v for v in propiedades.values())
        y = self._tabla_header(c, x, y, width, tiene_tol, tiene_lim)
        for prefijo, vals in propiedades.items():
            y = self._tabla_fila(c, prefijo, vals, x, y)
        return y - 5

    def _es_campo_excluido(self, clave, valor):
        return valor is None or clave == 'imagenes' or clave.endswith('_nc') or isinstance(valor, (dict, list))

    def _agrupar_propiedades(self, datos):
        sufijos = {'_valor': 'valor', '_tolerancia': 'tolerancia', '_unidad': 'unidad', '_limite': 'limite'}
        propiedades = {}
        for clave, valor in datos.items():
            if self._es_campo_excluido(clave, valor):
                continue
            campo_encontrado = False
            for sufijo, campo in sufijos.items():
                if clave.endswith(sufijo):
                    prefijo = clave[:-len(sufijo)]
                    propiedades.setdefault(prefijo, {})[campo] = valor
                    campo_encontrado = True
                    break
            if not campo_encontrado:
                propiedades[clave] = {'valor': valor}
        return propiedades

    def _tabla_header(self, c, x, y, width, tiene_tol, tiene_lim):
        col_prop, col_val, col_tol, col_uni = x + 10, x + 180, x + 270, x + 360
        c.setFont("Helvetica-Bold", 7)
        c.setFillColor(GRIS)
        c.drawString(col_prop, y, "Propiedad")
        c.drawString(col_val, y, "Valor")
        if tiene_tol:
            c.drawString(col_tol, y, "Tolerancia (±)")
        elif tiene_lim:
            c.drawString(col_tol, y, "Límite")
        c.drawString(col_uni, y, "Unidad")
        y -= 4
        c.setStrokeColor(GRIS)
        c.setLineWidth(0.3)
        c.line(col_prop, y, width - 50, y)
        return y - 12

    def _tabla_fila(self, c, prefijo, vals, x, y):
        col_prop, col_val, col_tol, col_uni = x + 10, x + 180, x + 270, x + 360
        c.setFont("Helvetica", 8)
        c.setFillColor(NEGRO)
        c.drawString(col_prop, y, prefijo.replace("_", " ").title())
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

    _EXCEL_HEADERS = [
        "Código Ficha", "Código Local", "País", "Estado",
        "Versión", "Fecha Creación", "Creador", "Color",
        "Largo (valor)", "Largo (tol)", "Largo (unid)",
        "Ancho (valor)", "Ancho (tol)", "Ancho (unid)",
        "Alto (valor)", "Alto (tol)", "Alto (unid)",
        "Peso (valor)", "Peso (tol)", "Peso (unid)",
        "Ruptura (valor)", "Ruptura (unid)",
        "T. Encolado (valor)", "T. Encolado (unid)",
        "Absorción (valor)", "Absorción (tol)", "Absorción (unid)",
        "Defl. Int (valor)", "Defl. Int (unid)",
        "Defl. Ext (valor)", "Defl. Ext (unid)",
        "Resistencia (valor)", "Resistencia (unid)",
        "Prof. Pilar (valor)", "Prof. Pilar (tol)", "Prof. Pilar (unid)",
        "Diám. Alvéolo (valor)", "Diám. Alvéolo (tol)", "Diám. Alvéolo (unid)",
        "Prof. Cavidad (valor)", "Prof. Cavidad (tol)", "Prof. Cavidad (unid)",
        "Diám. Cavidad (valor)", "Diám. Cavidad (tol)", "Diám. Cavidad (unid)",
        "Tipo Empaque", "Color Empaque",
        "Alto Emp. (valor)", "Alto Emp. (tol)", "Alto Emp. (unid)",
        "Peso Emp. (valor)", "Peso Emp. (tol)", "Peso Emp. (unid)",
        "Uds/Empaque", "Empaques/Estiba", "Camas/Estiba", "Empaques/Cama",
        "Aeróbico (valor)", "Aeróbico (lím)",
        "Moho (valor)", "Moho (lím)",
        "Coliforme (valor)", "Coliforme (lím)",
        "E. Coli (valor)", "E. Coli (lím)",
        "Salmonella (valor)", "Salmonella (lím)",
        "Cadmio", "Plomo", "Mercurio", "Cromo",
        "Uso", "Manejo", "Almacenamiento", "Transporte", "Vida Útil",
    ]

    async def exportar_fichas_excel(self) -> bytes:
        """Exporta listado de fichas a Excel."""
        result = await self.db_session.execute(
            select(FichaTecnica)
            .join(KItem, FichaTecnica.id_ficha == KItem.id)
            .where(KItem.estado.in_(["Preliminar", "Vigente"]))
        )
        fichas = result.scalars().all()

        wb = Workbook()
        ws = wb.active
        ws.title = "Fichas Técnicas"

        thin_border = Border(left=Side(style="thin"), right=Side(style="thin"), top=Side(style="thin"), bottom=Side(style="thin"))
        hdr_font = Font(bold=True, color="FFFFFF", size=10)
        hdr_fill = PatternFill("solid", fgColor="044926")
        hdr_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

        for col, header in enumerate(self._EXCEL_HEADERS, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font, cell.fill, cell.alignment, cell.border = hdr_font, hdr_fill, hdr_align, thin_border

        for row_idx, ficha in enumerate(fichas, 2):
            for col, valor in enumerate(self._fila_excel(ficha), 1):
                cell = ws.cell(row=row_idx, column=col, value=valor)
                cell.border = thin_border
                cell.alignment = Alignment(horizontal="center", wrap_text=True)

        n = len(self._EXCEL_HEADERS)
        for col in range(1, n + 1):
            ws.column_dimensions[ws.cell(row=1, column=col).column_letter].width = 16
        for i in range(n - 4, n + 1):
            ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = 30

        output = io.BytesIO()
        wb.save(output)
        return output.getvalue()

    def _fila_excel(self, ficha) -> list:
        caract = ficha.caracteristicas or {}
        cont = ficha.caracteristicas_contenido or {}
        emp = ficha.empaque_estiba or {}
        micro = ficha.microbiologia or {}
        manejo = ficha.manejo_disposicion or {}
        fecha = ficha.fecha_registro.strftime("%d/%m/%Y") if getattr(ficha, "fecha_registro", None) else ""
        return [
            ficha.codigo_ficha_local or "", ficha.codigo_material_local or "",
            ficha.pais or "", ficha.estado_ficha, ficha.codigo_version,
            fecha, ficha.usuario_creador or "", caract.get("color", ""),
            caract.get("dimensiones_largo_valor"), caract.get("dimensiones_largo_tolerancia"), caract.get("dimensiones_largo_unidad"),
            caract.get("dimensiones_ancho_valor"), caract.get("dimensiones_ancho_tolerancia"), caract.get("dimensiones_ancho_unidad"),
            caract.get("dimensiones_alto_valor"), caract.get("dimensiones_alto_tolerancia"), caract.get("dimensiones_alto_unidad"),
            caract.get("peso_valor"), caract.get("peso_tolerancia"), caract.get("peso_unidad"),
            caract.get("ruptura_valor"), caract.get("ruptura_unidad"),
            caract.get("tiempo_encolado_valor"), caract.get("tiempo_encolado_unidad"),
            caract.get("porcentaje_absorcion_valor"), caract.get("porcentaje_absorcion_tolerancia"), caract.get("porcentaje_absorcion_unidad"),
            caract.get("deflexion_interna_valor"), caract.get("deflexion_interna_unidad"),
            caract.get("deflexion_externa_valor"), caract.get("deflexion_externa_unidad"),
            caract.get("resistencia_valor"), caract.get("resistencia_unidad"),
            cont.get("profundidad_pilar_valor"), cont.get("profundidad_pilar_tolerancia"), cont.get("profundidad_pilar_unidad"),
            cont.get("diametro_alveolo_valor"), cont.get("diametro_alveolo_tolerancia"), cont.get("diametro_alveolo_unidad"),
            cont.get("profundidad_cavidad_valor"), cont.get("profundidad_cavidad_tolerancia"), cont.get("profundidad_cavidad_unidad"),
            cont.get("diametro_cavidad_valor"), cont.get("diametro_cavidad_tolerancia"), cont.get("diametro_cavidad_unidad"),
            emp.get("tipo_empaque"), emp.get("color_empaque"),
            emp.get("alto_empaque_valor"), emp.get("alto_empaque_tolerancia"), emp.get("alto_empaque_unidad"),
            emp.get("peso_empaque_valor"), emp.get("peso_empaque_tolerancia"), emp.get("peso_empaque_unidad"),
            emp.get("undidades_empaque"), emp.get("empaques_estiba"), emp.get("camas_estiba"), emp.get("empaques_camas_estiba"),
            micro.get("recuento_aerobico_valor"), micro.get("recuento_aerobico_limite"),
            micro.get("recuento_moho_valor"), micro.get("recuento_moho_limite"),
            micro.get("coliforme_valor"), micro.get("coliforme_limite"),
            micro.get("escherichia_coli_valor"), micro.get("escherichia_coli_limite"),
            micro.get("salmonella_spp_valor"), micro.get("salmonella_spp_limite"),
            micro.get("cadmio_valor"), micro.get("plomo_valor"), micro.get("mercurio_valor"), micro.get("cromo_valor"),
            manejo.get("uso"), manejo.get("manejo"), manejo.get("almacenamiento"),
            manejo.get("transporte"), manejo.get("vida_util"),
        ]