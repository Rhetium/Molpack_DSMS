"""
Servicio MaterialComercial — Refactorizado para DSMS.

Al crear un material, se crea automáticamente su kitem base
en la tabla kitem, asegurando que todo material es un k-item
del dataspace y puede participar en el grafo de conocimiento.

ACTUALIZACIÓN: Integración con búsqueda semántica (pgvector).
Al crear o actualizar un material, se genera automáticamente
su embedding vectorial para búsqueda por similitud.
"""

from uuid import UUID
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.material import MaterialComercial
from app.schemas.material import MaterialCreateSchema
from app.schemas.kitem import KItemCreateSchema
from app.services.kitem_service import KItemService
from app.services.semantic_search_service import BusquedaSemanticaService
from app.core.dsms_constants import (
    KTYPE_MATERIAL_COMERCIAL,
    ACCION_MODIFICACION,
)


class MaterialService:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.kitem_service = KItemService(db_session)
        self.busqueda = BusquedaSemanticaService(db_session)

    # =========================================
    # Campos adicionales para embedding
    # =========================================

    def _campos_embedding(self, material: MaterialComercial) -> dict:
        """Extrae los campos específicos del material para enriquecer el embedding."""
        return {
            "categoria": material.categoria,
            "tipo_producto": material.tipo_producto,
            "contenido": material.contenido,
            "material_base": material.material_base,
            "color_base": material.color_base,
        }

    # =========================================
    # CRUD
    # =========================================

    async def listar(self) -> list[MaterialComercial]:
        result = await self.db_session.execute(select(MaterialComercial))
        return result.scalars().all()

    async def obtener(self, id_material: UUID) -> MaterialComercial:
        result = await self.db_session.execute(
            select(MaterialComercial).where(
                MaterialComercial.id_material_corporativo == id_material
            )
        )
        material = result.scalars().first()
        if not material:
            raise HTTPException(
                status_code=404, detail="Material comercial no encontrado"
            )
        return material

    async def crear(self, material_data: MaterialCreateSchema) -> MaterialComercial:
        """
        Crea un material comercial con integración al DSMS:
        1. Crea el kitem base
        2. Crea el material comercial con el mismo UUID
        3. Genera el embedding para búsqueda semántica
        4. Commit de toda la transacción
        """
        now = datetime.now()

        # --- PASO 1: Crear el kitem base ---
        kitem = await self.kitem_service.crear_kitem(
            KItemCreateSchema(
                ktype=KTYPE_MATERIAL_COMERCIAL,
                nombre=material_data.nombre_corporativo,
                descripcion=(
                    f"Material comercial: {material_data.nombre_corporativo} "
                    f"({material_data.categoria or 'sin categoría'}) - "
                    f"{material_data.tipo_producto or 'sin tipo'}"
                ),
                estado=material_data.estado_material,
                metadata_extra={
                    "categoria": material_data.categoria,
                    "tipo_producto": material_data.tipo_producto,
                    "material_base": material_data.material_base,
                },
                usuario_creador=material_data.usuario_creador,
            )
        )

        # --- PASO 2: Crear el material con el mismo UUID ---
        material = MaterialComercial(
            id_material_corporativo=kitem.id,
            nombre_corporativo=material_data.nombre_corporativo,
            contenido=material_data.contenido,
            categoria=material_data.categoria,
            material_base=material_data.material_base,
            capacidad_nominal=material_data.capacidad_nominal,
            color_base=material_data.color_base,
            tipo_producto=material_data.tipo_producto,
            estado_material=material_data.estado_material,
            fecha_creacion=now,
            fecha_actualizacion=now,
        )
        self.db_session.add(material)
        await self.db_session.flush()

        # --- PASO 3: Generar embedding para búsqueda semántica ---
        await self.busqueda.asignar_embedding(
            kitem_id=material.id_material_corporativo,
            campos_adicionales=self._campos_embedding(material),
            usuario=material_data.usuario_creador,
        )

        # --- PASO 4: Commit atómico (kitem + material + embedding + auditoría) ---
        await self.db_session.commit()
        await self.db_session.refresh(material)
        return material

    async def actualizar(
        self,
        id_material: UUID,
        datos_actualizacion: dict,
        usuario: str,
    ) -> MaterialComercial:
        """
        Actualiza un material comercial existente.

        1. Actualiza los campos del material comercial
        2. Sincroniza nombre/descripción en el kitem base
        3. Regenera el embedding para reflejar los cambios
        4. Registra auditoría de modificación

        Args:
            id_material: UUID del material a actualizar.
            datos_actualizacion: Dict con los campos a modificar.
                Campos válidos: nombre_corporativo, contenido, categoria,
                material_base, capacidad_nominal, color_base, tipo_producto,
                estado_material.
            usuario: Usuario que realiza la modificación.

        Returns:
            El material actualizado.
        """
        material = await self.obtener(id_material)
        now = datetime.now()

        # Campos actualizables del material comercial
        campos_validos = {
            "nombre_corporativo",
            "contenido",
            "categoria",
            "material_base",
            "capacidad_nominal",
            "color_base",
            "tipo_producto",
            "estado_material",
        }

        cambios = {}
        for campo, valor in datos_actualizacion.items():
            if campo in campos_validos and valor is not None:
                valor_anterior = getattr(material, campo)
                if valor_anterior != valor:
                    setattr(material, campo, valor)
                    cambios[campo] = {
                        "anterior": valor_anterior,
                        "nuevo": valor,
                    }

        if not cambios:
            return material  # Sin cambios, retornar sin modificar

        material.fecha_actualizacion = now
        self.db_session.add(material)
        await self.db_session.flush()

        # --- Sincronizar kitem base si cambió nombre o campos relevantes ---
        kitem = await self.kitem_service.obtener_kitem(id_material)
        kitem.usuario_ultima_actualizacion = usuario
        kitem.fecha_actualizacion = now

        if "nombre_corporativo" in cambios:
            kitem.nombre = material.nombre_corporativo

        # Actualizar descripción del kitem con los datos actuales
        kitem.descripcion = (
            f"Material comercial: {material.nombre_corporativo} "
            f"({material.categoria or 'sin categoría'}) - "
            f"{material.tipo_producto or 'sin tipo'}"
        )

        # Actualizar metadata_extra del kitem
        kitem.metadata_extra = {
            "categoria": material.categoria,
            "tipo_producto": material.tipo_producto,
            "material_base": material.material_base,
        }

        self.db_session.add(kitem)
        await self.db_session.flush()

        # --- Auditoría: registrar modificación ---
        await self.kitem_service.auditoria.registrar(
            kitem_id=id_material,
            ktype=KTYPE_MATERIAL_COMERCIAL,
            accion=ACCION_MODIFICACION,
            usuario=usuario,
            detalles={
                "campos_modificados": list(cambios.keys()),
                "cambios": cambios,
            },
        )

        # --- Regenerar embedding con los datos actualizados ---
        await self.busqueda.asignar_embedding(
            kitem_id=id_material,
            campos_adicionales=self._campos_embedding(material),
            usuario=usuario,
        )

        # --- Commit atómico ---
        await self.db_session.commit()
        await self.db_session.refresh(material)
        return material