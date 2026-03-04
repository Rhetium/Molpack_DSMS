"""
Schemas de validación para Ficha Técnica — Estándar Molpack Corporation.

Define la estructura exacta de cada sección JSONB de la ficha técnica
según el documento de estandarización corporativo.

Patrón de medidas cuantitativas:
    campo_valor:       Decimal  — Valor nominal
    campo_tolerancia:  Decimal  — Tolerancia simétrica (rango = valor ± tolerancia)
    campo_unidad:      String   — Unidad de medida

Validación en dos capas:
1. Pydantic (este archivo): Valida estructura, tipos, y que cada trío valor/tolerancia/unidad
   esté completo. Permite campos adicionales por país (extra = "allow").
2. Service (fichas_services.py): Valida reglas condicionales por tipo de contenido
   (Huevos → pilar/alvéolo, Frutas → cavidad).
"""

from uuid import UUID
from typing import Optional
from pydantic import BaseModel, model_validator
from datetime import datetime
from app.schemas.material import MaterialLiteSchema


# ============================================================
# HELPERS
# ============================================================

def _validar_trios(datos: dict, prefijos: list[str]) -> list[str]:
    """
    Valida que si se envía un _valor, también vengan _tolerancia y _unidad.
    Retorna lista de campos faltantes (vacía si todo ok).
    """
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


# ============================================================
# SUB-SCHEMAS: Secciones JSONB
# ============================================================

class CaracteristicasSchema(BaseModel):
    """
    Sección 'caracteristicas' — Propiedades físicas y funcionales.
    Todos los campos son opcionales ("Depende" en el estándar),
    pero si se envía un _valor, debe venir su _tolerancia y _unidad.
    """
    # Dimensiones
    dimensiones_largo_valor: Optional[float] = None
    dimensiones_largo_tolerancia: Optional[float] = None
    dimensiones_largo_unidad: Optional[str] = None

    dimensiones_ancho_valor: Optional[float] = None
    dimensiones_ancho_tolerancia: Optional[float] = None
    dimensiones_ancho_unidad: Optional[str] = None

    dimensiones_alto_valor: Optional[float] = None
    dimensiones_alto_tolerancia: Optional[float] = None
    dimensiones_alto_unidad: Optional[str] = None

    # Tiempo de encolado
    tiempo_encolado_valor: Optional[float] = None
    tiempo_encolado_tolerancia: Optional[float] = None
    tiempo_encolado_unidad: Optional[str] = None

    # Absorción
    porcentaje_absorcion_valor: Optional[float] = None
    porcentaje_absorcion_tolerancia: Optional[float] = None
    porcentaje_absorcion_unidad: Optional[str] = None

    # Peso
    peso_valor: Optional[float] = None
    peso_tolerancia: Optional[float] = None
    peso_unidad: Optional[str] = None

    # Deflexión interna
    deflexion_interna_valor: Optional[float] = None
    deflexion_interna_tolerancia: Optional[float] = None
    deflexion_interna_unidad: Optional[str] = None

    # Deflexión externa
    deflexion_externa_valor: Optional[float] = None
    deflexion_externa_tolerancia: Optional[float] = None
    deflexion_externa_unidad: Optional[str] = None

    # Ruptura
    ruptura_valor: Optional[float] = None
    ruptura_tolerancia: Optional[float] = None
    ruptura_unidad: Optional[str] = None

    class Config:
        extra = "allow"  # Permitir campos adicionales por país

    @model_validator(mode="after")
    def validar_trios_completos(self):
        datos = self.model_dump()
        prefijos = [
            "dimensiones_largo", "dimensiones_ancho", "dimensiones_alto",
            "tiempo_encolado", "porcentaje_absorcion", "peso",
            "deflexion_interna", "deflexion_externa", "ruptura",
        ]
        errores = _validar_trios(datos, prefijos)
        if errores:
            raise ValueError(
                f"Campos faltantes en caracteristicas (cada medida requiere valor + tolerancia + unidad): "
                f"{', '.join(errores)}"
            )
        return self


class CaracteristicasContenidoSchema(BaseModel):
    """
    Sección 'caracteristicas_contenido' — Propiedades geométricas del contenido.

    Campos condicionales según tipo de contenido del material:
    - Huevos: profundidad_pilar + diametro_alveolo (obligatorios)
    - Frutas: profundidad_cavidad + diametro_cavidad (obligatorios)
    - Otros:  profundidad_pilar + diametro_alveolo (obligatorios)

    La validación condicional (qué grupo es obligatorio) se hace en el service.
    Aquí solo se valida que los tríos estén completos si se envían.
    """
    # Pilar (huevos y otros)
    profundidad_pilar_valor: Optional[float] = None
    profundidad_pilar_tolerancia: Optional[float] = None
    profundidad_pilar_unidad: Optional[str] = None

    # Alvéolo (huevos y otros)
    diametro_alveolo_valor: Optional[float] = None
    diametro_alveolo_tolerancia: Optional[float] = None
    diametro_alveolo_unidad: Optional[str] = None

    # Cavidad (frutas)
    profundidad_cavidad_valor: Optional[float] = None
    profundidad_cavidad_tolerancia: Optional[float] = None
    profundidad_cavidad_unidad: Optional[str] = None

    diametro_cavidad_valor: Optional[float] = None
    diametro_cavidad_tolerancia: Optional[float] = None
    diametro_cavidad_unidad: Optional[str] = None

    class Config:
        extra = "allow"

    @model_validator(mode="after")
    def validar_trios_completos(self):
        datos = self.model_dump()
        prefijos = [
            "profundidad_pilar", "diametro_alveolo",
            "profundidad_cavidad", "diametro_cavidad",
        ]
        errores = _validar_trios(datos, prefijos)
        if errores:
            raise ValueError(
                f"Campos faltantes en caracteristicas_contenido: {', '.join(errores)}"
            )
        return self


class EmpaqueEstibaSchema(BaseModel):
    """
    Sección 'empaque_estiba' — Configuración de empaque y estiba.
    tipo_empaque es obligatorio; los demás dependen del contexto.
    """
    tipo_empaque: str
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
    """
    Sección 'microbiologia' — Parámetros microbiológicos y metales pesados.
    Patrón: valor/limite para microbiología, valor/unidad para metales.
    """
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
    """
    Sección 'manejo_disposicion' — Manejo, almacenamiento y disposición.
    Campos obligatorios: manejo, almacenamiento, transporte, vida_util, uso.
    """
    manejo: str
    almacenamiento: str
    transporte: str
    inocuidad: Optional[str] = None
    disposicion_pt: Optional[str] = None
    garantias: Optional[str] = None
    manipulacion: Optional[str] = None
    vida_util: str
    uso: str

    class Config:
        extra = "allow"


# ============================================================
# SCHEMAS PRINCIPALES DE FICHA TÉCNICA
# ============================================================

class AnomaliaResumen(BaseModel):
    """Resumen de una anomalía detectada (incluido en respuestas de creación/actualización)."""
    tipo_anomalia: str
    severidad: str
    campo_afectado: str | None = None
    mensaje: str


class FichaTecnicaSchema(BaseModel):
    """Schema de respuesta — lectura de ficha técnica."""
    id_ficha: UUID
    id_material_corporativo: UUID
    codigo_ficha_local: str | None = None
    codigo_material_local: str | None = None
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
    """
    Schema de creación — valida estructura de cada sección JSONB.

    Las secciones usan sub-schemas tipados que verifican:
    - Tipos de datos correctos (float, str, int)
    - Tríos valor/tolerancia/unidad completos
    - Pares valor/limite completos (microbiología)
    - Campos obligatorios por sección (manejo_disposicion, empaque_estiba)

    La validación condicional por tipo de contenido (Huevos vs Frutas)
    se hace en el service, no aquí.
    """
    id_material_corporativo: UUID
    codigo_material_local: str
    usuario_creador: str
    pais: str

    caracteristicas: Optional[CaracteristicasSchema] = None
    caracteristicas_contenido: Optional[CaracteristicasContenidoSchema] = None
    empaque_estiba: Optional[EmpaqueEstibaSchema] = None
    microbiologia: Optional[MicrobiologiaSchema] = None
    manejo_disposicion: Optional[ManejoDisposicionSchema] = None

    class Config:
        from_attributes = True


class FichaTecnicaUpdateSchema(BaseModel):
    """
    Schema de actualización — misma validación que creación por sección.
    Solo se actualizan las secciones enviadas.
    """
    caracteristicas: Optional[CaracteristicasSchema] = None
    caracteristicas_contenido: Optional[CaracteristicasContenidoSchema] = None
    empaque_estiba: Optional[EmpaqueEstibaSchema] = None
    microbiologia: Optional[MicrobiologiaSchema] = None
    manejo_disposicion: Optional[ManejoDisposicionSchema] = None
    usuario_actualizacion: str


class FichaTecnicaWithMaterialSchema(BaseModel):
    """Schema de respuesta con material asociado."""
    id_ficha: UUID
    id_material_corporativo: UUID
    codigo_ficha_local: str | None = None
    codigo_material_local: str | None = None
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

class CambioEstadoRequest(BaseModel):
    nuevo_estado: str
    usuario_actualizacion: str
