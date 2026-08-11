import os
import shutil
import uuid
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.core.deps import get_session
from app.core.security import get_usuario_actual
from app.models.ficha import FichaTecnica

router = APIRouter(
    prefix="/ficha",
    tags=["Imágenes de Fichas"],
    dependencies=[Depends(get_usuario_actual)],
)

UPLOAD_DIR = Path("uploads/productos")

TIPOS_IMAGEN = {"foto_producto", "plano_mecanico"}

FORMATOS_PERMITIDOS = {"image/jpeg", "image/png"}
EXTENSIONES_PERMITIDAS = {".jpg", ".jpeg", ".png"}

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
MIN_DIMENSION = 100    # px
MAX_DIMENSION = 8000   # px

MAX_DIMENSION_PLANO = 8000  # px


def get_upload_path(id_ficha: UUID, tipo: str, extension: str) -> Path:
    dir_ficha = UPLOAD_DIR / str(id_ficha)
    dir_ficha.mkdir(parents=True, exist_ok=True)
    return dir_ficha / f"{tipo}{extension}"


def validar_tipo_imagen(tipo: str) -> None:
    if tipo not in TIPOS_IMAGEN:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de imagen inválido: '{tipo}'. Tipos permitidos: {', '.join(TIPOS_IMAGEN)}",
        )


async def validar_archivo(file: UploadFile) -> bytes:
    if file.content_type not in FORMATOS_PERMITIDOS:
        raise HTTPException(
            status_code=400,
            detail=f"Formato no permitido: {file.content_type}. Solo se aceptan JPG y PNG.",
        )

    ext = Path(file.filename).suffix.lower() if file.filename else ""
    if ext not in EXTENSIONES_PERMITIDAS:
        raise HTTPException(
            status_code=400,
            detail=f"Extensión no permitida: {ext}. Solo se aceptan .jpg, .jpeg, .png",
        )

    contenido = await file.read()

    if len(contenido) > MAX_FILE_SIZE:
        tamano_mb = len(contenido) / (1024 * 1024)
        raise HTTPException(
            status_code=400,
            detail=f"Imagen demasiado grande: {tamano_mb:.1f}MB. Máximo permitido: 2MB.",
        )

    if len(contenido) == 0:
        raise HTTPException(status_code=400, detail="El archivo está vacío.")

    return contenido


def validar_dimensiones(contenido: bytes) -> tuple[int, int]:
    if contenido[:8] == b'\x89PNG\r\n\x1a\n':
        if len(contenido) < 24:
            raise HTTPException(status_code=400, detail="Archivo PNG corrupto.")
        width = int.from_bytes(contenido[16:20], 'big')
        height = int.from_bytes(contenido[20:24], 'big')

    elif contenido[:2] == b'\xff\xd8':
        width, height = _jpeg_dimensions(contenido)

    else:
        raise HTTPException(status_code=400, detail="Formato de imagen no reconocido.")

    if width < MIN_DIMENSION or height < MIN_DIMENSION:
        raise HTTPException(
            status_code=400,
            detail=f"Imagen muy pequeña: {width}x{height}px. Mínimo: {MIN_DIMENSION}x{MIN_DIMENSION}px.",
        )

    if width > MAX_DIMENSION or height > MAX_DIMENSION:
        raise HTTPException(
            status_code=400,
            detail=f"Imagen muy grande: {width}x{height}px. Máximo: {MAX_DIMENSION}x{MAX_DIMENSION}px.",
        )

    return width, height


_JPEG_SOF_MARKERS = frozenset(range(0xC0, 0xD0)) - {0xC4, 0xCC}
_JPEG_NO_LENGTH = frozenset([0xD8, 0xD9, *range(0xD0, 0xD8)])  # SOI, EOI, RST0-RST7


def _jpeg_next_marker(data: bytes, i: int) -> tuple[int, int]:
    while i < len(data) and data[i] == 0xFF:
        i += 1
    return (data[i], i + 1) if i < len(data) else (0, i)


def _jpeg_dimensions(data: bytes) -> tuple[int, int]:
    i = 2
    while i + 3 < len(data):
        marker, i = _jpeg_next_marker(data, i)
        if marker in _JPEG_NO_LENGTH:
            continue
        if marker == 0xDA:  # SOS — fin de cabeceras
            break
        if i + 1 >= len(data):
            break
        length = int.from_bytes(data[i:i + 2], 'big')
        if marker in _JPEG_SOF_MARKERS and i + 6 < len(data):
            height = int.from_bytes(data[i + 3:i + 5], 'big')
            width = int.from_bytes(data[i + 5:i + 7], 'big')
            return width, height
        i += length
    raise HTTPException(status_code=400, detail="No se pudieron leer las dimensiones del JPEG.")


def buscar_imagen_existente(id_ficha: UUID, tipo: str) -> Path | None:

    dir_ficha = UPLOAD_DIR / str(id_ficha)
    if not dir_ficha.exists():
        return None
    for ext in EXTENSIONES_PERMITIDAS:
        path = dir_ficha / f"{tipo}{ext}"
        if path.exists():
            return path
    return None


def clonar_imagenes_ficha(
    id_origen: UUID, id_destino: UUID, caracteristicas: dict | None
) -> dict | None:

    if not caracteristicas:
        return caracteristicas

    imagenes = caracteristicas.get("imagenes")
    if not imagenes:
        return caracteristicas

    imagenes_nuevas: dict = {}
    for tipo, info in imagenes.items():
        origen = buscar_imagen_existente(id_origen, tipo)
        if not origen:
            # No hay archivo físico en el origen; conservar metadata tal cual.
            imagenes_nuevas[tipo] = info
            continue
        destino = get_upload_path(id_destino, tipo, origen.suffix)
        shutil.copy2(origen, destino)
        imagenes_nuevas[tipo] = {**info, "ruta": str(destino)}

    return {**caracteristicas, "imagenes": imagenes_nuevas}


@router.post("/{id_ficha}/imagen")
async def subir_imagen(
    id_ficha: UUID,
    tipo: str = Form(..., description="Tipo de imagen: foto_producto o plano_mecanico"),
    archivo: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    usuario: dict = Depends(get_usuario_actual),
):


    result = await session.execute(
        select(FichaTecnica).where(FichaTecnica.id_ficha == id_ficha)
    )
    ficha = result.scalars().first()
    if not ficha:
        raise HTTPException(status_code=404, detail="Ficha técnica no encontrada.")

    if ficha.estado_ficha in ("Vigente", "Obsoleto"):
        raise HTTPException(
            status_code=400,
            detail=f"No se pueden modificar imágenes de una ficha en estado {ficha.estado_ficha}. "
                   f"Cambia la ficha a Revisión primero.",
        )


    validar_tipo_imagen(tipo)


    contenido = await validar_archivo(archivo)


    width, height = validar_dimensiones(contenido)


    ext = Path(archivo.filename).suffix.lower() if archivo.filename else ".jpg"
    if ext == ".jpeg":
        ext = ".jpg"


    anterior = buscar_imagen_existente(id_ficha, tipo)
    if anterior:
        anterior.unlink()


    ruta = get_upload_path(id_ficha, tipo, ext)
    ruta.write_bytes(contenido)


    imagenes_previas = (ficha.caracteristicas or {}).get("imagenes", {})
    imagenes_nuevas = {
        **imagenes_previas,
        tipo: {
            "ruta": str(ruta),
            "nombre_original": archivo.filename,
            "formato": archivo.content_type,
            "tamano_bytes": len(contenido),
            "ancho": width,
            "alto": height,
        },
    }
    ficha.caracteristicas = {**(ficha.caracteristicas or {}), "imagenes": imagenes_nuevas}
    flag_modified(ficha, "caracteristicas")
    session.add(ficha)
    await session.commit()

    return {
        "mensaje": f"Imagen '{tipo}' subida exitosamente.",
        "tipo": tipo,
        "nombre_original": archivo.filename,
        "tamano": f"{len(contenido) / 1024:.0f} KB",
        "dimensiones": f"{width}x{height} px",
        "ruta": f"/ficha/{id_ficha}/imagen/{tipo}",
    }


@router.get("/{id_ficha}/imagen/{tipo}")
async def obtener_imagen(
    id_ficha: UUID,
    tipo: str,
    usuario: dict = Depends(get_usuario_actual),
):
    """Descarga/visualiza una imagen de la ficha. Requiere autenticación."""
    validar_tipo_imagen(tipo)

    ruta = buscar_imagen_existente(id_ficha, tipo)
    if not ruta:
        raise HTTPException(
            status_code=404,
            detail=f"No hay imagen '{tipo}' para esta ficha.",
        )

    media_type = "image/png" if ruta.suffix == ".png" else "image/jpeg"
    return FileResponse(
        ruta,
        media_type=media_type,
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


@router.delete("/{id_ficha}/imagen/{tipo}")
async def eliminar_imagen(
    id_ficha: UUID,
    tipo: str,
    session: AsyncSession = Depends(get_session),
    usuario: dict = Depends(get_usuario_actual),
):
    """Elimina una imagen de la ficha."""
    validar_tipo_imagen(tipo)

    ruta = buscar_imagen_existente(id_ficha, tipo)
    if not ruta:
        raise HTTPException(
            status_code=404,
            detail=f"No hay imagen '{tipo}' para esta ficha.",
        )

    # Eliminar archivo
    ruta.unlink()

    # Actualizar JSONB
    result = await session.execute(
        select(FichaTecnica).where(FichaTecnica.id_ficha == id_ficha)
    )
    ficha = result.scalars().first()
    if ficha and ficha.caracteristicas:
        imagenes_previas = ficha.caracteristicas.get("imagenes", {})
        imagenes_nuevas = {k: v for k, v in imagenes_previas.items() if k != tipo}
        ficha.caracteristicas = {**ficha.caracteristicas, "imagenes": imagenes_nuevas}
        flag_modified(ficha, "caracteristicas")
        session.add(ficha)
        await session.commit()

    return {"mensaje": f"Imagen '{tipo}' eliminada exitosamente."}