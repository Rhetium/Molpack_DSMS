"""
Router de Exportación — Endpoints para generar PDF y Excel.

Endpoints:
    GET /export/ficha/{id_ficha}/pdf  — Genera PDF de una ficha (con plantilla opcional)
    GET /export/fichas/excel          — Exporta listado de fichas a Excel

La plantilla PDF se configura en: app/templates/plantilla_ficha.pdf
Si no existe, genera PDF sin plantilla (formato limpio propio).
"""

import os
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_session
from app.services.export_service import ExportService

import io

router = APIRouter(prefix="/export", tags=["Exportación"])

# Ruta donde el usuario coloca su plantilla PDF
PLANTILLA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "templates",
    "plantilla_ficha.pdf",
)


def get_export_service(db_session: AsyncSession = Depends(get_session)):
    return ExportService(db_session)


@router.get("/ficha/{id_ficha}/pdf")
async def exportar_ficha_pdf(
    id_ficha: UUID,
    service: ExportService = Depends(get_export_service),
):
    """
    Genera PDF de la ficha técnica.

    Si existe app/templates/plantilla_ficha.pdf, escribe los datos
    sobre esa plantilla. Si no existe, genera PDF con formato propio.

    Solo fichas en estado Preliminar o Vigente.
    """
    plantilla = PLANTILLA_PATH if os.path.exists(PLANTILLA_PATH) else None

    pdf_bytes = await service.exportar_ficha_pdf(id_ficha, plantilla_path=plantilla)

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=ficha_{id_ficha}.pdf"
        },
    )


@router.get("/fichas/excel")
async def exportar_fichas_excel(
    service: ExportService = Depends(get_export_service),
):
    """
    Exporta listado de fichas Preliminares y Vigentes a Excel.
    Incluye características principales.
    """
    xlsx_bytes = await service.exportar_fichas_excel()

    return StreamingResponse(
        io.BytesIO(xlsx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": "attachment; filename=fichas_tecnicas.xlsx"
        },
    )