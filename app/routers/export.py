import os
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_session
from app.core.security import get_usuario_actual
from app.services.export_service import ExportService

import io

router = APIRouter(
    prefix="/export",
    tags=["Exportación"],
    dependencies=[Depends(get_usuario_actual)],
)

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
    xlsx_bytes = await service.exportar_fichas_excel()

    return StreamingResponse(
        io.BytesIO(xlsx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": "attachment; filename=fichas_tecnicas.xlsx"
        },
    )