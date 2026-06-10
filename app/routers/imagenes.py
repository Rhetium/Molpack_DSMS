"""
Servicio y Router de Imágenes — Upload de fotos de producto y planos mecánicos.

Estándares:
- Máximo 2 imágenes por ficha: foto_producto y plano_mecanico
- Formatos: JPG, PNG
- Tamaño máximo: 2MB por imagen
- Resolución: mínimo 400x400px, máximo 4000x4000px
- Almacenamiento: filesystem en /uploads/productos/{id_ficha}/
- La ruta se guarda en ficha_tecnica.caracteristicas.imagenes (JSONB)

Endpoints:
    POST /ficha/{id_ficha}/imagen      — Sube una imagen
    GET  /ficha/{id_ficha}/imagen/{tipo} — Descarga una imagen
    DELETE /ficha/{id_ficha}/imagen/{tipo} — Elimina una imagen
"""

import os
import uuid
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.core.deps import get_session
from app.models.ficha import FichaTecnica

router = APIRouter(prefix="/ficha", tags=["Imágenes de Fichas"])

# ============================================================
# CONFIGURACIÓN
# ============================================================

# Carpeta base para almacenar imágenes
UPLOAD_DIR = Path("uploads/productos")

# Tipos de imagen permitidos por ficha
TIPOS_IMAGEN = {"foto_producto", "plano_mecanico"}

# Formatos permitidos
FORMATOS_PERMITIDOS = {"image/jpeg", "image/png"}
EXTENSIONES_PERMITIDAS = {".jpg", ".jpeg", ".png"}

# Límites
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
MIN_DIMENSION = 100    # px
MAX_DIMENSION = 8000   # px

# Dimensiones más permisivas para planos técnicos (escaneos de A3/A2 a 300 DPI)
MAX_DIMENSION_PLANO = 8000  # px


# ============================================================
# HELPERS
# ============================================================

def get_upload_path(id_ficha: UUID, tipo: str, extension: str) -> Path:
    """Genera la ruta de almacenamiento para una imagen."""
    dir_ficha = UPLOAD_DIR / str(id_ficha)
    dir_ficha.mkdir(parents=True, exist_ok=True)
    return dir_ficha / f"{tipo}{extension}"


def validar_tipo_imagen(tipo: str) -> None:
    """Valida que el tipo de imagen sea válido."""
    if tipo not in TIPOS_IMAGEN:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de imagen inválido: '{tipo}'. Tipos permitidos: {', '.join(TIPOS_IMAGEN)}",
        )


async def validar_archivo(file: UploadFile) -> bytes:
    """Valida formato, tamaño y lee el contenido del archivo."""
    # Validar formato por content_type
    if file.content_type not in FORMATOS_PERMITIDOS:
        raise HTTPException(
            status_code=400,
            detail=f"Formato no permitido: {file.content_type}. Solo se aceptan JPG y PNG.",
        )

    # Validar extensión del nombre
    ext = Path(file.filename).suffix.lower() if file.filename else ""
    if ext not in EXTENSIONES_PERMITIDAS:
        raise HTTPException(
            status_code=400,
            detail=f"Extensión no permitida: {ext}. Solo se aceptan .jpg, .jpeg, .png",
        )

    # Leer contenido
    contenido = await file.read()

    # Validar tamaño
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
    """
    Valida las dimensiones de la imagen sin dependencias externas.
    Lee los headers del archivo para obtener ancho y alto.
    """
    # Detectar PNG
    if contenido[:8] == b'\x89PNG\r\n\x1a\n':
        if len(contenido) < 24:
            raise HTTPException(status_code=400, detail="Archivo PNG corrupto.")
        width = int.from_bytes(contenido[16:20], 'big')
        height = int.from_bytes(contenido[20:24], 'big')

    # Detectar JPEG
    elif contenido[:2] == b'\xff\xd8':
        width, height = _jpeg_dimensions(contenido)

    else:
        raise HTTPException(status_code=400, detail="Formato de imagen no reconocido.")

    # Validar dimensiones
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
    """Avanza al siguiente marcador JPEG; retorna (marker, pos_tras_marker_byte)."""
    while i < len(data) and data[i] == 0xFF:
        i += 1
    return (data[i], i + 1) if i < len(data) else (0, i)


def _jpeg_dimensions(data: bytes) -> tuple[int, int]:
    """Extrae dimensiones de un JPEG leyendo markers SOF (todos los perfiles)."""
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
    """Busca si ya existe una imagen de este tipo para la ficha."""
    dir_ficha = UPLOAD_DIR / str(id_ficha)
    if not dir_ficha.exists():
        return None
    for ext in EXTENSIONES_PERMITIDAS:
        path = dir_ficha / f"{tipo}{ext}"
        if path.exists():
            return path
    return None


# ============================================================
# ENDPOINTS
# ============================================================

@router.post("/{id_ficha}/imagen")
async def subir_imagen(
    id_ficha: UUID,
    tipo: str = Form(..., description="Tipo de imagen: foto_producto o plano_mecanico"),
    archivo: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
):
    """
    Sube una imagen para una ficha técnica.

    Tipos permitidos: foto_producto, plano_mecanico
    Formatos: JPG, PNG
    Tamaño máximo: 2MB
    Resolución: 400x400 a 4000x4000 px

    Si ya existe una imagen del mismo tipo, la reemplaza.
    """
    # Validar que la ficha existe
    result = await session.execute(
        select(FichaTecnica).where(FichaTecnica.id_ficha == id_ficha)
    )
    ficha = result.scalars().first()
    if not ficha:
        raise HTTPException(status_code=404, detail="Ficha técnica no encontrada.")

    # Solo se pueden subir imágenes en estados editables
    if ficha.estado_ficha in ("Vigente", "Obsoleto"):
        raise HTTPException(
            status_code=400,
            detail=f"No se pueden modificar imágenes de una ficha en estado {ficha.estado_ficha}. "
                   f"Cambia la ficha a Revisión primero.",
        )

    # Validar tipo
    validar_tipo_imagen(tipo)

    # Validar archivo
    contenido = await validar_archivo(archivo)

    # Validar dimensiones
    width, height = validar_dimensiones(contenido)

    # Determinar extensión
    ext = Path(archivo.filename).suffix.lower() if archivo.filename else ".jpg"
    if ext == ".jpeg":
        ext = ".jpg"

    # Eliminar imagen anterior si existe
    anterior = buscar_imagen_existente(id_ficha, tipo)
    if anterior:
        anterior.unlink()

    # Guardar archivo
    ruta = get_upload_path(id_ficha, tipo, ext)
    ruta.write_bytes(contenido)

    # Actualizar JSONB — crear nuevos dicts para que SQLAlchemy detecte el cambio
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
):
    """Descarga/visualiza una imagen de la ficha."""
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