from uuid import UUID
from typing import Optional
from pydantic import BaseModel, model_validator
from datetime import datetime
from app.schemas.material import MaterialLiteSchema


def _validar_trios(datos: dict, prefijos: list[str]) -> list[str]:
    errores = []
    for prefijo in prefijos:
        valor = datos.get(f"{prefijo}_valor")
        tolerancia = datos.get(f"{prefijo}_tolerancia")
        unidad = datos.get(f"{prefijo}_unidad")

        if valor is not None:
            if tolerancia is None:
                errores.append(f"{prefijo}_tolerancia")
            if unidad is None:
                errores.append(f"{prefijo}_unidad")
    return errores


def _validar_pares(datos: dict, prefijos: list[str]) -> list[str]:
    errores = []
    for prefijo in prefijos:
        valor = datos.get(f"{prefijo}_valor")
        unidad = datos.get(f"{prefijo}_unidad")
        if valor is not None and unidad is None:
            errores.append(f"{prefijo}_unidad")
    return errores


class CaracteristicasSchema(BaseModel):
    dimensiones_largo_valor: Optional[float] = None
    dimensiones_largo_tolerancia: Optional[float] = None
    dimensiones_largo_unidad: Optional[str] = None

    dimensiones_ancho_valor: Optional[float] = None
    dimensiones_ancho_tolerancia: Optional[float] = None
    dimensiones_ancho_unidad: Optional[str] = None

    dimensiones_alto_valor: Optional[float] = None
    dimensiones_alto_tolerancia: Optional[float] = None
    dimensiones_alto_unidad: Optional[str] = None

    tiempo_encolado_valor: Optional[float] = None
    tiempo_encolado_unidad: Optional[str] = None

    porcentaje_absorcion_valor: Optional[float] = None
    porcentaje_absorcion_tolerancia: Optional[float] = None
    porcentaje_absorcion_unidad: Optional[str] = None

    peso_valor: Optional[float] = None
    peso_tolerancia: Optional[float] = None
    peso_unidad: Optional[str] = None

    # solo cuando contenido es huevo
    deflexion_interna_valor: Optional[float] = None
    deflexion_interna_unidad: Optional[str] = None

    deflexion_externa_valor: Optional[float] = None
    deflexion_externa_unidad: Optional[str] = None

    ruptura_valor: Optional[float] = None
    ruptura_unidad: Optional[str] = None

    # solo cuando contenido NO es huevo
    resistencia_valor: Optional[float] = None
    resistencia_unidad: Optional[str] = None

    class Config:
        extra = "allow" 

    @model_validator(mode="after")
    def validar_trios_completos(self):
        datos = self.model_dump()
        errores = _validar_trios(datos, [
            "dimensiones_largo", "dimensiones_ancho", "dimensiones_alto",
            "porcentaje_absorcion", "peso",
        ])
        errores += _validar_pares(datos, [
            "tiempo_encolado", "deflexion_interna", "deflexion_externa",
            "ruptura", "resistencia",
        ])
        if errores:
            raise ValueError(
                f"Campos faltantes en caracteristicas: {', '.join(errores)}"
            )
        return self


class CaracteristicasContenidoSchema(BaseModel):
    # Pilar (huevos y otros)
    profundidad_pilar_valor: Optional[float] = None
    profundidad_pilar_tolerancia: Optional[float] = None
    profundidad_pilar_unidad: Optional[str] = None

    # Alvéolo (huevos y otros)
    diametro_alveolo_valor: Optional[float] = None
    diametro_alveolo_tolerancia: Optional[float] = None
    diametro_alveolo_unidad: Optional[str] = None

    # Cavidad (frutas, pintura, vasos, otros)
    profundidad_cavidad_valor: Optional[float] = None
    profundidad_cavidad_tolerancia: Optional[float] = None
    profundidad_cavidad_unidad: Optional[str] = None

    diametro_cavidad_valor: Optional[float] = None
    diametro_cavidad_tolerancia: Optional[float] = None
    diametro_cavidad_unidad: Optional[str] = None

    # Dimensiones de cavidad (demás contenidos: no huevo/fruta/pintura/vaso)
    ancho_cavidad_valor: Optional[float] = None
    ancho_cavidad_tolerancia: Optional[float] = None
    ancho_cavidad_unidad: Optional[str] = None

    largo_cavidad_valor: Optional[float] = None
    largo_cavidad_tolerancia: Optional[float] = None
    largo_cavidad_unidad: Optional[str] = None

    class Config:
        extra = "allow"

    @model_validator(mode="after")
    def validar_trios_completos(self):
        datos = self.model_dump()
        prefijos = [
            "profundidad_pilar", "diametro_alveolo",
            "profundidad_cavidad", "diametro_cavidad",
            "ancho_cavidad", "largo_cavidad",
        ]
        errores = _validar_trios(datos, prefijos)
        if errores:
            raise ValueError(
                f"Campos faltantes en caracteristicas_contenido: {', '.join(errores)}"
            )
        return self


class EmpaqueEstibaSchema(BaseModel):
    tipo_empaque: Optional[str] = None
    color_empaque: Optional[str] = None

    alto_empaque_valor: Optional[float] = None
    alto_empaque_tolerancia: Optional[float] = None
    alto_empaque_unidad: Optional[str] = None

    peso_empaque_valor: Optional[float] = None
    peso_empaque_tolerancia: Optional[float] = None
    peso_empaque_unidad: Optional[str] = None

    undidades_empaque: Optional[int] = None
    empaques_estiba: Optional[int] = None
    camas_estiba: Optional[int] = None
    empaques_camas_estiba: Optional[int] = None

    class Config:
        extra = "allow"

    @model_validator(mode="after")
    def validar_trios_completos(self):
        datos = self.model_dump()
        prefijos = ["alto_empaque", "peso_empaque"]
        errores = _validar_trios(datos, prefijos)
        if errores:
            raise ValueError(
                f"Campos faltantes en empaque_estiba: {', '.join(errores)}"
            )
        return self


class MicrobiologiaSchema(BaseModel):
    # Microbiología (valor + límite)
    recuento_aerobico_valor: Optional[float] = None
    recuento_aerobico_limite: Optional[float] = None

    recuento_moho_valor: Optional[float] = None
    recuento_moho_limite: Optional[float] = None

    coliforme_valor: Optional[float] = None
    coliforme_limite: Optional[float] = None

    escherichia_coli_valor: Optional[float] = None
    escherichia_coli_limite: Optional[float] = None

    salmonella_spp_valor: Optional[float] = None
    salmonella_spp_limite: Optional[float] = None

    # Metales pesados (valor + unidad)
    cadmio_valor: Optional[float] = None
    cadmio_unidad: Optional[str] = None

    plomo_valor: Optional[float] = None
    plomo_unidad: Optional[str] = None

    mercurio_valor: Optional[float] = None
    mercurio_unidad: Optional[str] = None

    cromo_valor: Optional[float] = None
    cromo_unidad: Optional[str] = None

    class Config:
        extra = "allow"

    @model_validator(mode="after")
    def validar_pares_completos(self):
        errores = []

        # Microbiología: si hay valor, debe haber límite y viceversa
        pares_micro = [
            "recuento_aerobico", "recuento_moho", "coliforme",
            "escherichia_coli", "salmonella_spp",
        ]
        for prefijo in pares_micro:
            valor = getattr(self, f"{prefijo}_valor", None)
            limite = getattr(self, f"{prefijo}_limite", None)
            if valor is not None and limite is None:
                errores.append(f"{prefijo}_limite")
            if limite is not None and valor is None:
                errores.append(f"{prefijo}_valor")

        # Metales: si hay valor, debe haber unidad
        metales = ["cadmio", "plomo", "mercurio", "cromo"]
        for metal in metales:
            valor = getattr(self, f"{metal}_valor", None)
            unidad = getattr(self, f"{metal}_unidad", None)
            if valor is not None and unidad is None:
                errores.append(f"{metal}_unidad")

        if errores:
            raise ValueError(
                f"Campos faltantes en microbiologia: {', '.join(errores)}"
            )
        return self


class ManejoDisposicionSchema(BaseModel):
    manejo: Optional[str] = None
    almacenamiento: Optional[str] = None
    transporte: Optional[str] = None
    inocuidad: Optional[str] = None
    disposicion_pt: Optional[str] = None
    garantias: Optional[str] = None
    manipulacion: Optional[str] = None
    vida_util: Optional[str] = None
    uso: Optional[str] = None

    class Config:
        extra = "allow"

class AnomaliaResumen(BaseModel):
    tipo_anomalia: str
    severidad: str
    campo_afectado: str | None = None
    mensaje: str


class FichaTecnicaSchema(BaseModel):
    id_ficha: UUID
    id_material_corporativo: UUID
    codigo_ficha_local: str | None = None
    codigo_material_local: str | None = None
    nombre_local_material: str | None = None
    codigo_version: str | None = None
    usuario_creador: str | None = None
    usuario_ultima_actualizacion: str | None = None
    estado_ficha: str | None = None
    fecha_registro: datetime | None = None
    fecha_actualizacion: datetime | None = None
    pais: str | None = None

    caracteristicas: dict | None = None
    caracteristicas_contenido: dict | None = None
    empaque_estiba: dict | None = None
    microbiologia: dict | None = None
    manejo_disposicion: dict | None = None

    anomalias: list[AnomaliaResumen] | None = None

    class Config:
        from_attributes = True


class FichaTecnicaCreateSchema(BaseModel):
    id_material_corporativo: UUID
    # Opcionales en borrador — obligatorios para avanzar a Preliminar
    codigo_material_local: str | None = None
    nombre_local_material: str | None = None
    # Sobrescrito por el router con la identidad del token JWT.
    usuario_creador: str | None = None
    pais: str | None = None

    caracteristicas: Optional[CaracteristicasSchema] = None
    caracteristicas_contenido: Optional[CaracteristicasContenidoSchema] = None
    empaque_estiba: Optional[EmpaqueEstibaSchema] = None
    microbiologia: Optional[MicrobiologiaSchema] = None
    manejo_disposicion: Optional[ManejoDisposicionSchema] = None

    class Config:
        from_attributes = True


class FichaTecnicaUpdateSchema(BaseModel):
    nombre_local_material: str | None = None
    # Solo editables mientras la ficha está en Borrador (placeholders de creación)
    codigo_material_local: str | None = None
    pais: str | None = None
    caracteristicas: Optional[CaracteristicasSchema] = None
    caracteristicas_contenido: Optional[CaracteristicasContenidoSchema] = None
    empaque_estiba: Optional[EmpaqueEstibaSchema] = None
    microbiologia: Optional[MicrobiologiaSchema] = None
    manejo_disposicion: Optional[ManejoDisposicionSchema] = None
    # Ignorado: la identidad se toma del token JWT (get_usuario_nombre).
    usuario_actualizacion: str | None = None


class FichaTecnicaWithMaterialSchema(BaseModel):
    id_ficha: UUID
    id_material_corporativo: UUID
    codigo_ficha_local: str | None = None
    codigo_material_local: str | None = None
    nombre_local_material: str | None = None
    codigo_version: str | None = None
    usuario_creador: str | None = None
    usuario_ultima_actualizacion: str | None = None
    estado_ficha: str | None = None
    fecha_registro: datetime | None = None
    fecha_actualizacion: datetime | None = None
    pais: str | None = None

    caracteristicas: dict | None = None
    caracteristicas_contenido: dict | None = None
    empaque_estiba: dict | None = None
    microbiologia: dict | None = None
    manejo_disposicion: dict | None = None

    material: MaterialLiteSchema

    class Config:
        from_attributes = True

class FichaVersionSchema(BaseModel):
    id_ficha: UUID
    codigo_ficha_local: str | None = None
    codigo_version: str | None = None
    estado_ficha: str | None = None
    usuario_ultima_actualizacion: str | None = None
    fecha_registro: datetime | None = None
    fecha_actualizacion: datetime | None = None

    class Config:
        from_attributes = True


class CambioEstadoRequest(BaseModel):
    nuevo_estado: str
    # Ignorado: la identidad se toma del token JWT (get_usuario_nombre).
    # Se conserva como opcional por compatibilidad con clientes existentes.
    usuario_actualizacion: str | None = None
