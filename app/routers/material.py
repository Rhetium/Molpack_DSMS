from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_session
from app.core.security import get_usuario_actual, get_usuario_nombre
from app.schemas.material import AnomaliaResumen, MaterialSchema, MaterialCreateSchema, MaterialUpdateSchema, CambioEstadoMaterialRequest
from app.services.material_service import MaterialService

router = APIRouter(
    prefix="/material",
    tags=["material"],
    dependencies=[Depends(get_usuario_actual)],
)


def get_material_service(
    session: AsyncSession = Depends(get_session),
) -> MaterialService:
    return MaterialService(db_session=session)


@router.get("", response_model=List[MaterialSchema])
async def listar_materiales(
    service: MaterialService = Depends(get_material_service),
):
    return await service.listar()


@router.get("/{id_material}", response_model=MaterialSchema)
async def obtener_material(
    id_material: UUID,
    service: MaterialService = Depends(get_material_service),
):
    return await service.obtener(id_material)


@router.post("", response_model=MaterialSchema, status_code=201)
async def crear_material(
    material_data: MaterialCreateSchema,
    service: MaterialService = Depends(get_material_service),
    usuario: str = Depends(get_usuario_nombre),
):
    # La identidad la impone el token, no el cuerpo de la petición.
    material_data.usuario_creador = usuario
    mateiral = await service.crear(material_data)
    resultado = MaterialSchema.model_validate(mateiral)
    if hasattr(mateiral,'_anomalias') and mateiral._anomalias:
        resultado.anomalias = [
            AnomaliaResumen(
                tipo_anomalia=a.tipo_anomalia,
                severidad=a.severidad,
                campo_afectado=a.campo_afectado,
                mensaje=a.mensaje,
            )
            for a in mateiral._anomalias
        ]
    return resultado

@router.patch("/{id_material}", response_model=MaterialSchema)
async def actualizar_material(
    id_material: UUID,
    datos: MaterialUpdateSchema,
    service: MaterialService = Depends(get_material_service),
    usuario: str = Depends(get_usuario_nombre),
):
    datos_dict = datos.model_dump(exclude={"usuario"}, exclude_none=True)
    material = await service.actualizar(
        id_material=id_material,
        datos_actualizacion=datos_dict,
        usuario=usuario
    )
    resultado = MaterialSchema.model_validate(material)
    if hasattr(material,'_anomalias') and material._anomalias:
        resultado.anomalias = [
            AnomaliaResumen(
                tipo_anomalia=a.tipo_anomalia,
                severidad=a.severidad,
                campo_afectado=a.campo_afectado,
                mensaje=a.mensaje,
            )
            for a in material._anomalias
        ]
    return resultado


@router.patch("/{id_material}/estado", response_model=MaterialSchema)
async def cambiar_estado_material(
    id_material: UUID,
    request: CambioEstadoMaterialRequest,
    service: MaterialService = Depends(get_material_service),
    usuario: str = Depends(get_usuario_nombre),
):
    material = await service.actualizar(
        id_material=id_material,
        datos_actualizacion={"estado_material": request.estado_material},
        usuario=usuario,
    )
    return MaterialSchema.model_validate(material)