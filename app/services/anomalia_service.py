import logging
import statistics
from uuid import UUID
from datetime import datetime

import numpy as np
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ficha import FichaTecnica
from app.models.material import MaterialComercial
from app.models.kitem import KItem
from app.models.anomalia import AnomaliaRegistro

from app.schemas.anomalia import (
    AnomaliaDetectada,
    ResultadoAnalisis,
)

from app.core.anomalia_constant import (
    ANOMALIA_RANGO_CATEGORIA,
    ANOMALIA_VALOR_ATIPICO,
    ANOMALIA_UNIDAD_INCONSISTENTE,
    ANOMALIA_CLASIFICACION_CRUZADA,
    ANOMALIA_DUPLICADO_SEMANTICO,
    ANOMALIA_ML_MULTIVARIADO,
    SEVERIDAD_INFORMATIVA,
    SEVERIDAD_ADVERTENCIA,
    SEVERIDAD_CRITICA,
    ESTADO_ANOMALIA_PENDIENTE,
    CONTEXTO_CREACION,
    CONTEXTO_ACTUALIZACION,
    ZSCORE_ADVERTENCIA,
    ZSCORE_CRITICO,
    MIN_MUESTRAS_ESTADISTICAS,
    UMBRAL_DUPLICADO_SEMANTICO,
    UMBRAL_DUPLICADO_CRITICO,
    FACTOR_MAD,
    ESCALA_MINIMA_RELATIVA,
    ESCALA_MINIMA_SIN_TOLERANCIA,
    CAMPOS_EXCLUIDOS_ZSCORE,
    CAMPOS_DERIVADOS,
    MIN_MUESTRAS_MATERIAL,
    MIN_MUESTRAS_FAMILIA,
    NIVEL_MATERIAL,
    NIVEL_FAMILIA,
    NIVEL_CATEGORIA,
    CAMPOS_DUPLICADO_CLAVE,
    CAMPOS_DUPLICADO_SECUNDARIOS,
    TOLERANCIA_RELATIVA_DUPLICADO,
    COINCIDENCIA_SECUNDARIA_MINIMA,
    UMBRAL_DUPLICADO_MATERIAL_CRITICO,
    calcular_derivados,
    tolerancia_relativa_derivados,
    PORCENTAJE_UNIDAD_MAYORITARIA,
    UMBRAL_CLASIFICACION_CRUZADA,
    CAMPOS_CARACTERISTICAS,
    CAMPOS_CONTENIDO,
    CAMPOS_EMPAQUE,
    ML_SCORE_CRITICO,
    rangos_para_categoria,
)

from app.core.dsms_constants import (
    KTYPE_FICHA_TECNICA,
    KTYPE_MATERIAL_COMERCIAL,
    ESTADO_BORRADOR,
    ESTADO_OBSOLETO,
)

from app.services.semantic_search_service import BusquedaSemanticaService
from app.services.ml_anomalia_service import MLAnomaliaService

logger = logging.getLogger(__name__)

_DESCRIPCION_NIVEL = {
    NIVEL_MATERIAL: "otras fichas del mismo material",
    NIVEL_FAMILIA: "materiales de la misma categoría y capacidad",
    NIVEL_CATEGORIA: "materiales de la misma categoría",
}


class AnomaliaService:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.busqueda = BusquedaSemanticaService(db_session)
        self.ml = MLAnomaliaService(db_session)


    async def analizar_ficha(
        self,
        id_ficha: UUID,
        usuario: str,
        contexto: str = CONTEXTO_CREACION,
    ) -> ResultadoAnalisis:

        # Obtener ficha + material asociado
        ficha = await self._obtener_ficha(id_ficha)
        material = await self._obtener_material(ficha.id_material_corporativo)

        # Fichas activas de la misma categoría (con su material) como referencia
        referencias = await self._obtener_referencias(
            categoria=material.categoria,
            excluir_id=id_ficha,
        )
        fichas_referencia = [f for f, _ in referencias]
        fichas_estadistica, nivel = self._seleccionar_referencia_estadistica(
            material, referencias,
        )

        anomalias: list[AnomaliaDetectada] = []

        # --- Detector 1: Valores atípicos ---
        anomalias.extend(
            self._detectar_valores_atipicos(ficha, fichas_estadistica, nivel)
        )

        # --- Detector 2: Unidades inconsistentes ---
        anomalias.extend(
            self._detectar_unidades_inconsistentes(ficha, fichas_referencia)
        )

        # --- Detector 3: Duplicados (mismo producto bajo otro material) ---
        anomalias.extend(
            await self._detectar_duplicados_ficha(ficha, material, referencias)
        )

        # --- Detector 4: Clasificación cruzada ---
        cruzadas = await self._detectar_clasificacion_cruzada(
            material=material,
            ficha=ficha,
        )
        anomalias.extend(cruzadas)

        # --- Detector 5: Perfil numérico cruzado ---
        perfil_cruzado = await self._detectar_perfil_numerico_cruzado(
            ficha=ficha,
            material=material,
        )
        anomalias.extend(perfil_cruzado)

        # --- Detector 6: Isolation Forest (multivariado) ---
        anomalias.extend(
            self._detectar_ml_multivariado(ficha=ficha, material=material)
        )

        # --- Detector 7: Rangos dimensionales por categoría ---
        anomalias.extend(
            self._detectar_rango_categoria(ficha=ficha, material=material)
        )

        for anomalia in anomalias:
            await self._persistir_anomalia(
                kitem_id=id_ficha,
                ktype=KTYPE_FICHA_TECNICA,
                anomalia=anomalia,
                usuario=usuario,
                contexto=contexto,
            )

        # Construir resultado
        criticas = sum(1 for a in anomalias if a.severidad == SEVERIDAD_CRITICA)
        advertencias = sum(1 for a in anomalias if a.severidad == SEVERIDAD_ADVERTENCIA)
        informativas = sum(1 for a in anomalias if a.severidad == SEVERIDAD_INFORMATIVA)

        resultado = ResultadoAnalisis(
            kitem_id=id_ficha,
            ktype=KTYPE_FICHA_TECNICA,
            total_anomalias=len(anomalias),
            criticas=criticas,
            advertencias=advertencias,
            informativas=informativas,
            anomalias=anomalias,
        )

        logger.info(
            f"Análisis de anomalías ficha {id_ficha}: "
            f"{len(anomalias)} anomalías "
            f"({criticas} críticas, {advertencias} advertencias, "
            f"{informativas} informativas)"
        )

        return resultado

    async def analizar_material(
        self,
        id_material: UUID,
        usuario: str,
        contexto: str = CONTEXTO_CREACION,
    ) -> ResultadoAnalisis:

        material = await self._obtener_material(id_material)

        anomalias: list[AnomaliaDetectada] = []

        # --- Detector 1: Duplicados semánticos ---
        duplicados = await self._detectar_duplicados_semanticos(
            kitem_id=id_material,
            ktype=KTYPE_MATERIAL_COMERCIAL,
        )
        anomalias.extend(duplicados)

        # --- Detector 2: Clasificación cruzada ---
        cruzadas = await self._detectar_clasificacion_cruzada(
            material=material,
        )
        anomalias.extend(cruzadas)

        # Persistir
        for anomalia in anomalias:
            await self._persistir_anomalia(
                kitem_id=id_material,
                ktype=KTYPE_MATERIAL_COMERCIAL,
                anomalia=anomalia,
                usuario=usuario,
                contexto=contexto,
            )

        criticas = sum(1 for a in anomalias if a.severidad == SEVERIDAD_CRITICA)
        advertencias = sum(1 for a in anomalias if a.severidad == SEVERIDAD_ADVERTENCIA)
        informativas = sum(1 for a in anomalias if a.severidad == SEVERIDAD_INFORMATIVA)

        resultado = ResultadoAnalisis(
            kitem_id=id_material,
            ktype=KTYPE_MATERIAL_COMERCIAL,
            total_anomalias=len(anomalias),
            criticas=criticas,
            advertencias=advertencias,
            informativas=informativas,
            anomalias=anomalias,
        )

        logger.info(
            f"Análisis de anomalías material {id_material}: "
            f"{len(anomalias)} anomalías"
        )

        return resultado


    def _detectar_valores_atipicos(
        self,
        ficha: FichaTecnica,
        fichas_referencia: list[FichaTecnica],
        nivel_referencia: str = NIVEL_CATEGORIA,
    ) -> list[AnomaliaDetectada]:
        """
        Z-score robusto por campo: |valor - mediana| / escala, con
        escala = max(1.4826·MAD, tolerancia declarada, 2% de la mediana).
        Incluye las variables derivadas (gramaje, relación alto/largo).
        """
        anomalias = []

        if len(fichas_referencia) < MIN_MUESTRAS_ESTADISTICAS:
            logger.info(
                f"Solo {len(fichas_referencia)} fichas de referencia, "
                f"insuficientes para detección estadística "
                f"(mínimo {MIN_MUESTRAS_ESTADISTICAS})"
            )
            return anomalias

        for est in self._estadisticas_campos(ficha, fichas_referencia):
            z_score = est["z_score"]
            if z_score >= ZSCORE_CRITICO:
                severidad = SEVERIDAD_CRITICA
            elif z_score >= ZSCORE_ADVERTENCIA:
                severidad = SEVERIDAD_ADVERTENCIA
            else:
                continue  # Valor dentro del rango normal

            valor, unidad = est["valor"], est["unidad"]
            rango_min, rango_max = est["rango_min"], est["rango_max"]
            anomalias.append(AnomaliaDetectada(
                tipo_anomalia=ANOMALIA_VALOR_ATIPICO,
                severidad=severidad,
                campo_afectado=est["campo"],
                valor_detectado=f"{valor} {unidad}".strip(),
                valor_esperado=f"{rango_min} - {rango_max} {unidad}".strip(),
                mensaje=(
                    f"{est['nombre']}: el valor {valor} {unidad} está fuera "
                    f"del rango típico ({rango_min} - {rango_max} {unidad}) "
                    f"para {_DESCRIPCION_NIVEL[nivel_referencia]}."
                ),
                detalles={
                    "mediana": est["mediana"],
                    "escala": est["escala"],
                    "z_score": round(z_score, 4) if z_score != float("inf") else None,
                    "n_muestras": est["n_muestras"],
                    "nivel_referencia": nivel_referencia,
                    "rango_min": rango_min,
                    "rango_max": rango_max,
                },
            ))

        return anomalias

    def _estadisticas_campos(
        self,
        ficha: FichaTecnica,
        fichas_referencia: list[FichaTecnica],
    ) -> list[dict]:
        """Estadística robusta de cada campo numérico analizable de la ficha."""
        resultados = []

        secciones = [
            (ficha.caracteristicas, "caracteristicas", CAMPOS_CARACTERISTICAS),
            (ficha.caracteristicas_contenido, "caracteristicas_contenido", CAMPOS_CONTENIDO),
            (ficha.empaque_estiba, "empaque_estiba", CAMPOS_EMPAQUE),
        ]
        for datos_ficha, nombre_seccion, campos in secciones:
            if not datos_ficha:
                continue

            for campo_valor, campo_unidad, nombre_legible in campos:
                if campo_valor in CAMPOS_EXCLUIDOS_ZSCORE:
                    continue
                valor = datos_ficha.get(campo_valor)
                if not isinstance(valor, (int, float)):
                    continue
                # Campo marcado como N/C por el usuario — excluir de cálculos
                prefijo = campo_valor.removesuffix("_valor")
                if datos_ficha.get(prefijo + "_nc"):
                    continue

                valores_ref = [
                    v for v in self._extraer_valores_campo(
                        fichas_referencia, nombre_seccion, campo_valor
                    )
                    if isinstance(v, (int, float))
                ]
                est = self._estadistica_robusta(
                    valor, valores_ref, datos_ficha.get(prefijo + "_tolerancia"),
                )
                if est:
                    est.update(
                        campo=f"{nombre_seccion}.{campo_valor}",
                        nombre=nombre_legible,
                        unidad=datos_ficha.get(campo_unidad) or "",
                    )
                    resultados.append(est)

        derivados = calcular_derivados(ficha.caracteristicas, ficha.empaque_estiba)
        tolerancias = tolerancia_relativa_derivados(ficha.caracteristicas, ficha.empaque_estiba)
        derivados_ref = [
            calcular_derivados(f.caracteristicas, f.empaque_estiba) for f in fichas_referencia
        ]
        for campo_valor, unidad, nombre_legible in CAMPOS_DERIVADOS:
            if campo_valor not in derivados:
                continue
            valor = derivados[campo_valor]
            valores_ref = [d[campo_valor] for d in derivados_ref if campo_valor in d]
            # Relativa a la referencia, no al valor: un valor erróneo no debe
            # agrandar su propia tolerancia.
            tolerancia = (
                tolerancias.get(campo_valor, 0.0) * statistics.median(valores_ref)
                if valores_ref else 0.0
            )
            est = self._estadistica_robusta(valor, valores_ref, tolerancia or None)
            if est:
                est.update(
                    campo=f"caracteristicas.{campo_valor}",
                    nombre=nombre_legible,
                    unidad=unidad,
                )
                resultados.append(est)

        return resultados

    @staticmethod
    def _estadistica_robusta(
        valor: float,
        valores_ref: list[float],
        tolerancia: float | None,
    ) -> dict | None:
        """Mediana, escala robusta y z-score de `valor`; None si faltan muestras."""
        if len(valores_ref) < MIN_MUESTRAS_ESTADISTICAS:
            return None

        mediana = statistics.median(valores_ref)
        mad = statistics.median(abs(v - mediana) for v in valores_ref)
        tiene_tolerancia = isinstance(tolerancia, (int, float)) and tolerancia > 0
        escala = max(
            FACTOR_MAD * mad,
            abs(tolerancia) if tiene_tolerancia else 0.0,
            (ESCALA_MINIMA_RELATIVA if tiene_tolerancia else ESCALA_MINIMA_SIN_TOLERANCIA)
            * abs(mediana),
        )
        if escala == 0:
            z_score = 0.0 if valor == mediana else float("inf")
        else:
            z_score = abs(valor - mediana) / escala

        decimales = 5 if abs(mediana) < 1 else 2
        return {
            "valor": valor,
            "mediana": round(mediana, decimales),
            "escala": round(escala, decimales),
            "z_score": z_score,
            "n_muestras": len(valores_ref),
            # Las medidas son magnitudes positivas: el rango mostrado no baja de 0
            "rango_min": round(max(0.0, mediana - ZSCORE_ADVERTENCIA * escala), decimales),
            "rango_max": round(mediana + ZSCORE_ADVERTENCIA * escala, decimales),
            "valores_referencia": sorted(valores_ref)[:10],
        }

    def _detectar_unidades_inconsistentes(
        self,
        ficha: FichaTecnica,
        fichas_referencia: list[FichaTecnica],
    ) -> list[AnomaliaDetectada]:
        """
        Detecta cuando una ficha usa una unidad diferente a la
        mayoritaria para un campo dado.

        Ejemplo: si 90% de separadores usan "cm" para largo
        y esta ficha usa "mm", genera advertencia.
        """
        anomalias = []

        if len(fichas_referencia) < MIN_MUESTRAS_ESTADISTICAS:
            return anomalias

        secciones = [
            (ficha.caracteristicas, "caracteristicas", CAMPOS_CARACTERISTICAS),
            (ficha.caracteristicas_contenido, "caracteristicas_contenido", CAMPOS_CONTENIDO),
            (ficha.empaque_estiba, "empaque_estiba", CAMPOS_EMPAQUE),
        ]

        for datos_ficha, nombre_seccion, campos in secciones:
            if not datos_ficha:
                continue

            for campo_valor, campo_unidad, nombre_legible in campos:
                unidad_actual = datos_ficha.get(campo_unidad)
                if not unidad_actual:
                    continue
                # Campo marcado como N/C — excluir de cálculos
                if datos_ficha.get(campo_valor.removesuffix("_valor") + "_nc"):
                    continue

                # Recopilar unidades históricas
                unidades_ref = self._extraer_valores_campo(
                    fichas_referencia, nombre_seccion, campo_unidad
                )

                if not unidades_ref:
                    continue

                # Contar frecuencia de cada unidad
                conteo = {}
                for u in unidades_ref:
                    if u is not None:
                        conteo[u] = conteo.get(u, 0) + 1

                if not conteo:
                    continue

                total = sum(conteo.values())
                unidad_mayoritaria = max(conteo, key=conteo.get)
                porcentaje = conteo[unidad_mayoritaria] / total

                if (
                    unidad_actual != unidad_mayoritaria
                    and porcentaje >= PORCENTAJE_UNIDAD_MAYORITARIA
                ):
                    anomalias.append(AnomaliaDetectada(
                        tipo_anomalia=ANOMALIA_UNIDAD_INCONSISTENTE,
                        severidad=SEVERIDAD_ADVERTENCIA,
                        campo_afectado=f"{nombre_seccion}.{campo_unidad}",
                        valor_detectado=unidad_actual,
                        valor_esperado=(
                            f"{unidad_mayoritaria} "
                            f"(usado en {porcentaje:.0%} de fichas similares)"
                        ),
                        mensaje=(
                            f"{nombre_legible}: se usó '{unidad_actual}' pero "
                            f"el {porcentaje:.0%} de fichas similares usa "
                            f"'{unidad_mayoritaria}'. ¿Es intencional?"
                        ),
                        detalles={
                            "unidad_mayoritaria": unidad_mayoritaria,
                            "porcentaje_mayoritaria": round(porcentaje, 4),
                            "distribucion_unidades": conteo,
                            "n_muestras": total,
                        },
                    ))

        return anomalias

    async def _detectar_duplicados_semanticos(
        self,
        kitem_id: UUID,
        ktype: str,
        excluir_material_id: UUID | None = None,
        umbral: float = UMBRAL_DUPLICADO_SEMANTICO,
        umbral_critico: float = UMBRAL_DUPLICADO_CRITICO,
    ) -> list[AnomaliaDetectada]:
        """
        Busca k-items semánticamente muy similares al actual.

        Para fichas técnicas se pasa excluir_material_id para ignorar
        otras fichas del mismo material: es normal que compartan alta
        similitud semántica al describir el mismo producto.
        Solo se alerta si fichas de materiales DISTINTOS son casi idénticas.
        """
        anomalias = []

        try:
            resultados = await self.busqueda.buscar_similares_a_kitem(
                kitem_id=kitem_id,
                ktype=ktype,
                limite=10,
                umbral_similitud=umbral,
            )

            for resultado in resultados:
                kitem_similar = resultado["kitem"]
                similitud = resultado["similitud"]

                if kitem_similar.id == kitem_id:
                    continue

                # Para fichas: ignorar similares del mismo material corporativo
                if excluir_material_id and ktype == KTYPE_FICHA_TECNICA:
                    ficha_res = await self.db_session.execute(
                        select(FichaTecnica).where(
                            FichaTecnica.id_ficha == kitem_similar.id
                        )
                    )
                    ficha_sim = ficha_res.scalars().first()
                    if ficha_sim and ficha_sim.id_material_corporativo == excluir_material_id:
                        continue

                severidad = (
                    SEVERIDAD_CRITICA if similitud >= umbral_critico
                    else SEVERIDAD_ADVERTENCIA
                )

                anomalias.append(AnomaliaDetectada(
                    tipo_anomalia=ANOMALIA_DUPLICADO_SEMANTICO,
                    severidad=severidad,
                    campo_afectado=None,
                    valor_detectado=None,
                    valor_esperado=None,
                    mensaje=(
                        f"Posible duplicado detectado: '{kitem_similar.nombre}' "
                        f"tiene {similitud:.0%} de similitud con fichas de un "
                        f"material diferente. ¿Es el mismo producto registrado dos veces?"
                    ),
                    detalles={
                        "kitem_similar_id": str(kitem_similar.id),
                        "kitem_similar_nombre": kitem_similar.nombre,
                        "similitud": similitud,
                    },
                ))

        except Exception as e:
            logger.warning(f"Error en detección de duplicados: {e}")

        return anomalias


    async def _detectar_duplicados_ficha(
        self,
        ficha: FichaTecnica,
        material: MaterialComercial,
        referencias: list[tuple[FichaTecnica, MaterialComercial]],
    ) -> list[AnomaliaDetectada]:
        """
        Duplicado = el mismo producto registrado bajo otro material: una ficha
        activa de un material DISTINTO de la misma categoría con largo, ancho,
        alto y peso iguales dentro de la tolerancia declarada (y la mayoría de
        las medidas secundarias también). Se reporta solo la coincidencia más
        cercana. Es crítica si además los materiales son semánticamente casi
        iguales (nombre, contenido, capacidad...).
        """
        mejor = None
        for ficha_ref, material_ref in referencias:
            if material_ref.id_material_corporativo == material.id_material_corporativo:
                continue
            coincidencia = self._coincidencia_numerica(ficha, ficha_ref)
            if coincidencia and (mejor is None or coincidencia["distancia"] < mejor[0]["distancia"]):
                mejor = (coincidencia, ficha_ref, material_ref)

        if mejor is None:
            return []

        coincidencia, ficha_ref, material_ref = mejor
        similitud_material = await self._similitud_kitems(
            material.id_material_corporativo, material_ref.id_material_corporativo,
        )
        severidad = (
            SEVERIDAD_CRITICA
            if similitud_material is not None and similitud_material >= UMBRAL_DUPLICADO_MATERIAL_CRITICO
            else SEVERIDAD_ADVERTENCIA
        )
        kitem_ref = getattr(ficha_ref, "kitem", None)
        nombre_similar = kitem_ref.nombre if kitem_ref else ficha_ref.codigo_ficha_local
        campos = ", ".join(coincidencia["campos_coincidentes"])

        return [AnomaliaDetectada(
            tipo_anomalia=ANOMALIA_DUPLICADO_SEMANTICO,
            severidad=severidad,
            campo_afectado=None,
            valor_detectado=None,
            valor_esperado=None,
            mensaje=(
                f"Posible duplicado: '{nombre_similar}' (material "
                f"'{material_ref.nombre_corporativo}') tiene las mismas medidas "
                f"dentro de tolerancia ({campos}). "
                f"¿Es el mismo producto registrado dos veces?"
            ),
            detalles={
                "kitem_similar_id": str(ficha_ref.id_ficha),
                "kitem_similar_nombre": nombre_similar,
                "material_similar": material_ref.nombre_corporativo,
                "campos_coincidentes": coincidencia["campos_coincidentes"],
                "diferencia_relativa_media": round(coincidencia["distancia"], 4),
                "similitud_material": (
                    round(similitud_material, 4) if similitud_material is not None else None
                ),
            },
        )]

    @staticmethod
    def _coincidencia_numerica(
        ficha: FichaTecnica, otra: FichaTecnica,
    ) -> dict | None:
        """
        Compara las medidas de dos fichas. Devuelve los campos coincidentes y
        la diferencia relativa media si se consideran el mismo producto; None
        en caso contrario.
        """
        def _par(seccion_a, seccion_b, campo):
            seccion_a, seccion_b = seccion_a or {}, seccion_b or {}
            a, b = seccion_a.get(campo), seccion_b.get(campo)
            if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
                return None
            prefijo = campo.removesuffix("_valor")
            tol = max(
                abs(seccion_a.get(prefijo + "_tolerancia") or 0),
                abs(seccion_b.get(prefijo + "_tolerancia") or 0),
                TOLERANCIA_RELATIVA_DUPLICADO * max(abs(a), abs(b)),
            )
            dif = abs(a - b) / max(abs(a), abs(b), 1e-9)
            return abs(a - b) <= tol, dif

        diferencias = []
        for campo in CAMPOS_DUPLICADO_CLAVE:
            r = _par(ficha.caracteristicas, otra.caracteristicas, campo)
            if r is None or not r[0]:
                return None
            diferencias.append(r[1])

        secundarios = []
        for seccion, campo in CAMPOS_DUPLICADO_SECUNDARIOS:
            r = _par(getattr(ficha, seccion), getattr(otra, seccion), campo)
            if r is not None:
                secundarios.append((campo, r))
        if secundarios:
            coinciden = sum(1 for _, (ok, _d) in secundarios if ok)
            if coinciden / len(secundarios) < COINCIDENCIA_SECUNDARIA_MINIMA:
                return None
            diferencias.extend(d for _, (_ok, d) in secundarios)

        return {
            "campos_coincidentes": [
                c.removeprefix("dimensiones_").removesuffix("_valor") for c in CAMPOS_DUPLICADO_CLAVE
            ] + [c.removesuffix("_valor") for c, (ok, _d) in secundarios if ok],
            "distancia": sum(diferencias) / len(diferencias),
        }

    async def _similitud_kitems(self, id_a: UUID, id_b: UUID) -> float | None:
        """Similitud coseno entre los embeddings de dos k-items (None si falta alguno)."""
        result = await self.db_session.execute(
            select(KItem.id, KItem.embedding).where(KItem.id.in_([id_a, id_b]))
        )
        vectores = {id_: emb for id_, emb in result.all() if emb is not None}
        if len(vectores) < 2:
            return None
        a = np.asarray(vectores[id_a], dtype=float)
        b = np.asarray(vectores[id_b], dtype=float)
        norma = np.linalg.norm(a) * np.linalg.norm(b)
        return float(a @ b / norma) if norma else None

    async def _detectar_clasificacion_cruzada(
        self,
        material: MaterialComercial,
        ficha: FichaTecnica | None = None,
    ) -> list[AnomaliaDetectada]:

        try:
            # Compara el embedding guardado del material con los de los demás
            # materiales (misma plantilla de texto). Una consulta por texto libre
            # no alcanzaba nunca el umbral: ni el propio material pasaba de 0.80.
            resultados = await self.busqueda.buscar_similares_a_kitem(
                kitem_id=material.id_material_corporativo,
                ktype=KTYPE_MATERIAL_COMERCIAL,
                limite=10,
                umbral_similitud=UMBRAL_CLASIFICACION_CRUZADA,
            )

            # Ordenados por similitud: se reporta solo el más parecido de otra categoría
            for resultado in resultados:
                anomalia = await self._evaluar_similar_clasificacion(
                    resultado=resultado,
                    material=material,
                    ficha=ficha,
                )
                if anomalia:
                    return [anomalia]

        except Exception as e:
            logger.warning(f"Error en detección de clasificación cruzada: {e}")

        return []

    async def _evaluar_similar_clasificacion(
        self,
        resultado: dict,
        material: MaterialComercial,
        ficha: FichaTecnica | None,
    ) -> AnomaliaDetectada | None:
        kitem_similar = resultado["kitem"]
        similitud     = resultado["similitud"]

        if kitem_similar.id == material.id_material_corporativo:
            return None

        mat_res = await self.db_session.execute(
            select(MaterialComercial).where(
                MaterialComercial.id_material_corporativo == kitem_similar.id
            )
        )
        material_similar = mat_res.scalars().first()
        if not material_similar:
            return None

        cat_sugerida = material_similar.categoria
        cat_actual   = material.categoria
        if not (cat_sugerida and cat_actual
                and cat_sugerida != cat_actual
                and similitud >= UMBRAL_CLASIFICACION_CRUZADA):
            return None

        evidencia_dim = (
            ficha is not None
            and self._tiene_evidencia_dimensional(ficha, cat_sugerida, cat_actual)
        )
        severidad = SEVERIDAD_CRITICA if evidencia_dim else SEVERIDAD_ADVERTENCIA
        nota_dim  = (" Las dimensiones también encajan en la categoría sugerida."
                     if evidencia_dim else "")

        return AnomaliaDetectada(
            tipo_anomalia=ANOMALIA_CLASIFICACION_CRUZADA,
            severidad=severidad,
            campo_afectado="categoria",
            valor_detectado=cat_actual,
            valor_esperado=cat_sugerida,
            mensaje=(
                f"El material '{material.nombre_corporativo}' "
                f"(categoría: {cat_actual}) tiene "
                f"{similitud:.0%} de similitud semántica con "
                f"'{material_similar.nombre_corporativo}' "
                f"(categoría: {cat_sugerida}).{nota_dim} "
                f"¿La categoría es correcta?"
            ),
            detalles={
                "material_similar_id": str(material_similar.id_material_corporativo),
                "material_similar_nombre": material_similar.nombre_corporativo,
                "categoria_sugerida": cat_sugerida,
                "categoria_actual": cat_actual,
                "similitud": similitud,
                "evidencia_dimensional": evidencia_dim,
            },
        )

    @staticmethod
    def _tiene_evidencia_dimensional(
        ficha: FichaTecnica,
        cat_sugerida: str,
        cat_actual: str,
    ) -> bool:
        rangos_sug = rangos_para_categoria(cat_sugerida)
        rangos_dec = rangos_para_categoria(cat_actual)
        if rangos_sug is None or rangos_dec is None:
            return False
        caract = ficha.caracteristicas or {}

        encaja = all(
            isinstance(caract.get(c), (int, float)) and rmin <= caract[c] <= rmax
            for c, (rmin, rmax, _) in rangos_sug.items()
            if caract.get(c) is not None
        )
        fuera = any(
            isinstance(caract.get(c), (int, float)) and not (rmin <= caract[c] <= rmax)
            for c, (rmin, rmax, _) in rangos_dec.items()
            if caract.get(c) is not None
        )
        return encaja and fuera


    async def _detectar_perfil_numerico_cruzado(
        self,
        ficha: FichaTecnica,
        material: MaterialComercial,
    ) -> list[AnomaliaDetectada]:
 
        anomalias = []
        categoria_actual = material.categoria

        if not categoria_actual:
            return anomalias

        # Obtener perfiles (centroides) de todas las categorías
        perfiles = await self._calcular_perfiles_categorias(
            excluir_ficha_id=ficha.id_ficha,
        )

        if len(perfiles) < 2:
            return anomalias

        # Vector numérico de la ficha actual
        vector_ficha = self._extraer_vector_numerico(ficha)
        if not vector_ficha:
            return anomalias

        # Calcular distancia a cada categoría
        distancias = {}
        for categoria, perfil in perfiles.items():
            if perfil["n_muestras"] < MIN_MUESTRAS_ESTADISTICAS:
                continue
            distancia = self._distancia_euclidiana_normalizada(
                vector_ficha, perfil["centroide"], perfil["std"]
            )
            if distancia is not None:
                distancias[categoria] = distancia

        if len(distancias) < 2:
            return anomalias

        # Ordenar por distancia (menor = más parecido)
        ranking = sorted(distancias.items(), key=lambda x: x[1])
        categoria_mas_cercana = ranking[0][0]
        distancia_mas_cercana = ranking[0][1]

        distancia_declarada = distancias.get(categoria_actual)
        if distancia_declarada is None:
            return anomalias

        # Si otra categoría está significativamente más cerca
        if (
            categoria_mas_cercana != categoria_actual
            and distancia_declarada > 0
        ):
            ratio = distancia_mas_cercana / distancia_declarada

            if ratio < 0.7:  # Otra categoría >30% más cerca
                severidad = (
                    SEVERIDAD_CRITICA if ratio < 0.4
                    else SEVERIDAD_ADVERTENCIA
                )
                anomalias.append(AnomaliaDetectada(
                    tipo_anomalia="perfil_numerico_cruzado",
                    severidad=severidad,
                    campo_afectado="categoria",
                    valor_detectado=categoria_actual,
                    valor_esperado=categoria_mas_cercana,
                    mensaje=(
                        f"Los valores numéricos de esta ficha se parecen más "
                        f"a la categoría '{categoria_mas_cercana}' que a "
                        f"'{categoria_actual}'. ¿La clasificación es correcta?"
                    ),
                    detalles={
                        "categoria_declarada": categoria_actual,
                        "categoria_sugerida": categoria_mas_cercana,
                        "distancia_declarada": round(distancia_declarada, 4),
                        "distancia_sugerida": round(distancia_mas_cercana, 4),
                        "ratio": round(ratio, 4),
                        "ranking_categorias": {
                            cat: round(dist, 4) for cat, dist in ranking
                        },
                        "campos_comparados": list(vector_ficha.keys()),
                    },
                ))

        return anomalias

    def _detectar_ml_multivariado(
        self,
        ficha: FichaTecnica,
        material: MaterialComercial,
    ) -> list[AnomaliaDetectada]:

        if not self.ml.modelo_disponible(material.categoria):
            return []

        resultado = self.ml.predecir(ficha, material.categoria)
        if resultado is None or not resultado["es_anomalo"]:
            return []

        score = resultado["score"]
        # Crítica si queda claramente por debajo del umbral calibrado del modelo
        severidad = (
            SEVERIDAD_CRITICA if score <= resultado["umbral"] + ML_SCORE_CRITICO
            else SEVERIDAD_ADVERTENCIA
        )

        campos_resumen = resultado["campos_analizados"][:6]
        if len(resultado["campos_analizados"]) > 6:
            campos_resumen_str = ", ".join(campos_resumen) + "..."
        else:
            campos_resumen_str = ", ".join(campos_resumen)

        return [AnomaliaDetectada(
            tipo_anomalia=ANOMALIA_ML_MULTIVARIADO,
            severidad=severidad,
            campo_afectado=None,
            valor_detectado=None,
            valor_esperado=None,
            mensaje=(
                f"El perfil numérico combinado de esta ficha es inusual "
                f"respecto a las {resultado['n_entrenamiento']} fichas de referencia "
                f"(modelo: {resultado['modelo_usado']}, score: {score:.3f}). "
                f"Campos analizados: {campos_resumen_str}."
            ),
            detalles={
                "score_isolation_forest": round(score, 4),
                "modelo_usado": resultado["modelo_usado"],
                "n_fichas_entrenamiento": resultado["n_entrenamiento"],
                "campos_analizados": resultado["campos_analizados"],
                "umbral_advertencia": round(resultado["umbral"], 4),
                "umbral_critico": round(resultado["umbral"] + ML_SCORE_CRITICO, 4),
            },
        )]

    @staticmethod
    def _anomalia_rango_campo(
        campo: str,
        valor: float,
        minimo: float,
        maximo: float,
        unidad: str,
        categoria: str,
    ) -> AnomaliaDetectada:
        nombre = campo.replace("dimensiones_", "").replace("_valor", "").replace("_", " ").title()
        severidad = (
            SEVERIDAD_CRITICA
            if valor < minimo * 0.5 or valor > maximo * 2
            else SEVERIDAD_ADVERTENCIA
        )
        return AnomaliaDetectada(
            tipo_anomalia=ANOMALIA_RANGO_CATEGORIA,
            severidad=severidad,
            campo_afectado=f"caracteristicas.{campo}",
            valor_detectado=f"{valor} {unidad}",
            valor_esperado=f"{minimo} – {maximo} {unidad}",
            mensaje=(
                f"{nombre} ({valor} {unidad}) está fuera del rango típico "
                f"para la categoría '{categoria}' ({minimo} – {maximo} {unidad}). "
                f"¿El material está bien clasificado?"
            ),
            detalles={
                "categoria": categoria,
                "campo": campo,
                "valor": valor,
                "rango_min": minimo,
                "rango_max": maximo,
                "unidad": unidad,
            },
        )

    def _detectar_rango_categoria(
        self,
        ficha: FichaTecnica,
        material: MaterialComercial,
    ) -> list[AnomaliaDetectada]:
        categoria = material.categoria
        rangos = rangos_para_categoria(categoria)
        if not rangos:
            return []

        caract = ficha.caracteristicas or {}
        anomalias = []

        for campo, (minimo, maximo, unidad) in rangos.items():
            valor = caract.get(campo)
            if valor is None or not isinstance(valor, (int, float)):
                continue
            if valor < minimo or valor > maximo:
                anomalias.append(
                    self._anomalia_rango_campo(campo, valor, minimo, maximo, unidad, categoria)
                )

        return anomalias

    async def _calcular_perfiles_categorias(
        self,
        excluir_ficha_id: UUID | None = None,
    ) -> dict:
        query = (
            select(FichaTecnica, MaterialComercial)
            .join(
                MaterialComercial,
                FichaTecnica.id_material_corporativo
                == MaterialComercial.id_material_corporativo,
            )
        )
        if excluir_ficha_id:
            query = query.where(FichaTecnica.id_ficha != excluir_ficha_id)

        result = await self.db_session.execute(query)
        filas = result.all()

        # Agrupar vectores por categoría
        categorias = {}
        for ficha_ref, material_ref in filas:
            cat = material_ref.categoria
            if not cat:
                continue
            if cat not in categorias:
                categorias[cat] = []
            vector = self._extraer_vector_numerico(ficha_ref)
            if vector:
                categorias[cat].append(vector)

        # Calcular centroide y std por categoría
        perfiles = {}
        for cat, vectores in categorias.items():
            if not vectores:
                continue

            todos_campos = set()
            for v in vectores:
                todos_campos.update(v.keys())

            centroide = {}
            std = {}
            for campo in todos_campos:
                valores = [v[campo] for v in vectores if campo in v]
                if valores:
                    media = sum(valores) / len(valores)
                    centroide[campo] = media
                    if len(valores) > 1:
                        varianza = sum(
                            (x - media) ** 2 for x in valores
                        ) / len(valores)
                        std[campo] = varianza ** 0.5
                    else:
                        std[campo] = 0

            perfiles[cat] = {
                "centroide": centroide,
                "std": std,
                "n_muestras": len(vectores),
            }

        return perfiles

    def _extraer_vector_numerico(self, ficha: FichaTecnica) -> dict:
        vector = {}
        secciones = [
            (ficha.caracteristicas, CAMPOS_CARACTERISTICAS),
            (ficha.caracteristicas_contenido, CAMPOS_CONTENIDO),
            (ficha.empaque_estiba, CAMPOS_EMPAQUE),
        ]
        for datos, campos in secciones:
            if not datos:
                continue
            for campo_valor, *_ in campos:
                if datos.get(campo_valor.removesuffix("_valor") + "_nc"):
                    continue
                valor = datos.get(campo_valor)
                if valor is not None and isinstance(valor, (int, float)):
                    vector[campo_valor] = float(valor)
        return vector

    def _distancia_euclidiana_normalizada(
        self,
        vector: dict,
        centroide: dict,
        std: dict,
    ) -> float | None:
        campos_comunes = set(vector.keys()) & set(centroide.keys())
        if not campos_comunes:
            return None

        suma = 0
        n = 0
        for campo in campos_comunes:
            desv = std.get(campo, 0)
            if desv > 0:
                diff = (vector[campo] - centroide[campo]) / desv
            else:
                diff = 0 if vector[campo] == centroide[campo] else 1
            suma += diff ** 2
            n += 1

        if n == 0:
            return None
        return (suma / n) ** 0.5

    async def analizar_debug(self, id_ficha: UUID) -> dict:

        ficha   = await self._obtener_ficha(id_ficha)
        material = await self._obtener_material(ficha.id_material_corporativo)
        referencias = await self._obtener_referencias(
            categoria=material.categoria,
            excluir_id=id_ficha,
        )
        fichas_ref = [f for f, _ in referencias]
        fichas_est, nivel = self._seleccionar_referencia_estadistica(material, referencias)

        # Texto del embedding actual del KItem
        from sqlalchemy import select as sa_select
        from app.models.kitem import KItem
        ki_res = await self.db_session.execute(
            sa_select(KItem).where(KItem.id == id_ficha)
        )
        kitem = ki_res.scalars().first()
        embedding_nombre = kitem.nombre if kitem else "—"
        embedding_desc   = kitem.descripcion if kitem else "—"
        tiene_embedding  = kitem.embedding is not None if kitem else False

        detectores = []

        # ── D1: Z-Score robusto ──────────────────────────────────
        d1: dict = {
            "id": "D1", "nombre": "Valores Atípicos (Z-Score robusto)",
            "n_fichas_referencia": len(fichas_est),
            "nivel_referencia": nivel,
            "minimo_requerido": MIN_MUESTRAS_ESTADISTICAS,
            "activo": len(fichas_est) >= MIN_MUESTRAS_ESTADISTICAS,
            "campos": [],
        }
        if d1["activo"]:
            for est in self._estadisticas_campos(ficha, fichas_est):
                z = est["z_score"]
                d1["campos"].append({
                    "campo": est["campo"],
                    "nombre": est["nombre"],
                    "valor": est["valor"],
                    "mediana": est["mediana"],
                    "escala": est["escala"],
                    "zscore": round(z, 3) if z != float("inf") else None,
                    "umbral_advertencia": ZSCORE_ADVERTENCIA,
                    "umbral_critico": ZSCORE_CRITICO,
                    "anomalia": z >= ZSCORE_ADVERTENCIA,
                    "severidad": "critica" if z >= ZSCORE_CRITICO else ("advertencia" if z >= ZSCORE_ADVERTENCIA else "ok"),
                    "n_muestras": est["n_muestras"],
                    "valores_referencia": est["valores_referencia"],
                })
        d1["anomalias_generadas"] = sum(1 for c in d1["campos"] if c.get("anomalia"))
        detectores.append(d1)
        secciones_d1 = [
            (ficha.caracteristicas,           "caracteristicas",           CAMPOS_CARACTERISTICAS),
            (ficha.caracteristicas_contenido, "caracteristicas_contenido", CAMPOS_CONTENIDO),
            (ficha.empaque_estiba,            "empaque_estiba",            CAMPOS_EMPAQUE),
        ]

        # ── D2: Unidades inconsistentes ──────────────────────────
        d2: dict = {
            "id": "D2", "nombre": "Unidades Inconsistentes",
            "n_fichas_referencia": len(fichas_ref),
            "activo": True,
            "campos": [],
        }
        for datos_f, nombre_sec, campos in secciones_d1:
            if not datos_f:
                continue
            for campo_valor, campo_unidad, nombre_leg in campos:
                unidad_actual = datos_f.get(campo_unidad)
                if not unidad_actual:
                    continue
                if datos_f.get(campo_valor.removesuffix("_valor") + "_nc"):
                    continue
                unidades_ref = self._extraer_valores_campo(fichas_ref, nombre_sec, campo_unidad)
                conteo: dict = {}
                for u in unidades_ref:
                    if u:
                        conteo[u] = conteo.get(u, 0) + 1
                total = sum(conteo.values())
                if total == 0:
                    continue
                unidad_may = max(conteo, key=conteo.get)
                pct = conteo[unidad_may] / total
                anomalia = (unidad_actual != unidad_may and pct >= PORCENTAJE_UNIDAD_MAYORITARIA)
                d2["campos"].append({
                    "campo": f"{nombre_sec}.{campo_unidad}",
                    "nombre": nombre_leg,
                    "unidad_actual": unidad_actual,
                    "unidad_mayoritaria": unidad_may,
                    "porcentaje_mayoritaria": round(pct, 3),
                    "umbral": PORCENTAJE_UNIDAD_MAYORITARIA,
                    "distribucion": conteo,
                    "n_muestras": total,
                    "anomalia": anomalia,
                })
        d2["anomalias_generadas"] = sum(1 for c in d2["campos"] if c.get("anomalia"))
        detectores.append(d2)

        # ── D3: Duplicados (coincidencia numérica) ───────────────
        d3: dict = {
            "id": "D3", "nombre": "Duplicados (mismo producto, otro material)",
            "nota": (
                "Fichas activas de materiales DISTINTOS de la misma categoría con "
                "largo, ancho, alto y peso iguales dentro de tolerancia"
            ),
            "umbral_critico_material": UMBRAL_DUPLICADO_MATERIAL_CRITICO,
            "similares": [],
            "anomalias_generadas": 0,
        }
        try:
            for ficha_ref, material_ref in referencias:
                if material_ref.id_material_corporativo == material.id_material_corporativo:
                    continue
                coincidencia = self._coincidencia_numerica(ficha, ficha_ref)
                if not coincidencia:
                    continue
                sim = await self._similitud_kitems(
                    material.id_material_corporativo, material_ref.id_material_corporativo,
                )
                kitem_ref = getattr(ficha_ref, "kitem", None)
                d3["similares"].append({
                    "id": str(ficha_ref.id_ficha),
                    "nombre": kitem_ref.nombre if kitem_ref else ficha_ref.codigo_ficha_local,
                    "material": material_ref.nombre_corporativo,
                    "campos_coincidentes": coincidencia["campos_coincidentes"],
                    "diferencia_relativa_media": round(coincidencia["distancia"], 4),
                    "similitud_material": round(sim, 4) if sim is not None else None,
                    "es_duplicado": True,
                    "severidad": (
                        "critica" if sim is not None and sim >= UMBRAL_DUPLICADO_MATERIAL_CRITICO
                        else "advertencia"
                    ),
                })
            d3["similares"].sort(key=lambda x: x["diferencia_relativa_media"])
            d3["anomalias_generadas"] = 1 if d3["similares"] else 0
        except Exception as e:
            d3["error"] = str(e)
        detectores.append(d3)

        # ── D4: Clasificación cruzada ─────────────────────────────
        d4: dict = {
            "id": "D4", "nombre": "Clasificación Cruzada",
            "material_analizado": material.nombre_corporativo,
            "categoria_declarada": material.categoria,
            "umbral": UMBRAL_CLASIFICACION_CRUZADA,
            "materiales_similares": [],
            "anomalias_generadas": 0,
        }
        try:
            resultados_mat = await self.busqueda.buscar_similares_a_kitem(
                kitem_id=material.id_material_corporativo,
                ktype=KTYPE_MATERIAL_COMERCIAL,
                limite=10,
                umbral_similitud=0.5,
            )
            for r in resultados_mat:
                km = r["kitem"]
                sim = r["similitud"]
                if km.id == material.id_material_corporativo:
                    continue
                mat_res = await self.db_session.execute(
                    sa_select(MaterialComercial).where(MaterialComercial.id_material_corporativo == km.id)
                )
                mat_sim = mat_res.scalars().first()
                cat_sim = mat_sim.categoria if mat_sim else "?"
                cruzado = (cat_sim != material.categoria and sim >= UMBRAL_CLASIFICACION_CRUZADA)
                d4["materiales_similares"].append({
                    "id": str(km.id),
                    "nombre": km.nombre,
                    "categoria": cat_sim,
                    "similitud": sim,
                    "categoria_diferente": cat_sim != material.categoria,
                    "es_clasificacion_cruzada": cruzado,
                })
            d4["anomalias_generadas"] = sum(1 for m in d4["materiales_similares"] if m["es_clasificacion_cruzada"])
        except Exception as e:
            d4["error"] = str(e)
        detectores.append(d4)

        # ── D5: Perfil numérico cruzado ───────────────────────────
        d5: dict = {
            "id": "D5", "nombre": "Perfil Numérico Cruzado",
            "categoria_declarada": material.categoria,
            "vector_ficha": {},
            "perfiles_categorias": {},
            "distancias": {},
            "ranking": [],
            "anomalias_generadas": 0,
        }
        try:
            perfiles = await self._calcular_perfiles_categorias(excluir_ficha_id=id_ficha)
            vector_f = self._extraer_vector_numerico(ficha)
            d5["vector_ficha"] = {k: round(v, 3) for k, v in vector_f.items()}
            d5["n_campos_vector"] = len(vector_f)

            for cat, perfil in perfiles.items():
                d5["perfiles_categorias"][cat] = {
                    "n_muestras": perfil["n_muestras"],
                    "n_campos": len(perfil.get("centroide", {})),
                }
                dist = self._distancia_euclidiana_normalizada(vector_f, perfil["centroide"], perfil["std"])
                if dist is not None:
                    d5["distancias"][cat] = round(dist, 4)

            if d5["distancias"]:
                ranking = sorted(d5["distancias"].items(), key=lambda x: x[1])
                d5["ranking"] = [{"categoria": c, "distancia": d} for c, d in ranking]
                cat_mas_cercana = ranking[0][0]
                dist_declarada = d5["distancias"].get(material.categoria)
                dist_cercana   = ranking[0][1]
                if cat_mas_cercana != material.categoria and dist_declarada:
                    ratio = dist_cercana / dist_declarada
                    d5["ratio"] = round(ratio, 4)
                    d5["categoria_sugerida"] = cat_mas_cercana
                    d5["anomalias_generadas"] = 1 if ratio < 0.7 else 0
                    d5["umbral_advertencia"] = 0.7
                    d5["umbral_critico"] = 0.4
        except Exception as e:
            d5["error"] = str(e)
        detectores.append(d5)

        # ── D6: Isolation Forest ──────────────────────────────────
        d6: dict = {
            "id": "D6", "nombre": "Isolation Forest (ML Multivariado)",
            "modelo_categoria_disponible": self.ml.modelo_disponible(material.categoria),
            "modelo_global_disponible": self.ml.modelo_disponible("global"),
            "categoria": material.categoria,
            "anomalias_generadas": 0,
        }
        try:
            resultado_ml = self.ml.predecir(ficha, material.categoria)
            if resultado_ml:
                d6["score"] = round(resultado_ml["score"], 4)
                d6["es_anomalo"] = resultado_ml["es_anomalo"]
                d6["modelo_usado"] = resultado_ml["modelo_usado"]
                d6["n_fichas_entrenamiento"] = resultado_ml["n_entrenamiento"]
                d6["campos_analizados"] = resultado_ml["campos_analizados"]
                d6["umbral_advertencia"] = round(resultado_ml["umbral"], 4)
                d6["umbral_critico"] = round(resultado_ml["umbral"] + ML_SCORE_CRITICO, 4)
                d6["anomalias_generadas"] = 1 if resultado_ml["es_anomalo"] else 0
            else:
                d6["razon_inactivo"] = "Modelo no disponible o sin datos suficientes"
        except Exception as e:
            d6["error"] = str(e)
        detectores.append(d6)

        return {
            "ficha_id": str(id_ficha),
            "codigo_ficha_local": ficha.codigo_ficha_local,
            "estado_ficha": ficha.estado_ficha,
            "material": {
                "id": str(material.id_material_corporativo),
                "nombre": material.nombre_corporativo,
                "categoria": material.categoria,
                "contenido": material.contenido,
                "material_base": material.material_base,
            },
            "n_fichas_referencia_global": len(fichas_ref),
            "embedding": {
                "nombre_kitem": embedding_nombre,
                "descripcion_kitem": embedding_desc,
                "tiene_embedding": tiene_embedding,
            },
            "detectores": detectores,
            "resumen": {
                "total_anomalias_potenciales": sum(d.get("anomalias_generadas", 0) for d in detectores),
                "detectores_activos": sum(1 for d in detectores if d.get("activo", True) and not d.get("error")),
            },
        }

    async def _persistir_anomalia(
        self,
        kitem_id: UUID,
        ktype: str,
        anomalia: AnomaliaDetectada,
        usuario: str,
        contexto: str,
    ) -> AnomaliaRegistro:

        registro = AnomaliaRegistro(
            kitem_id=kitem_id,
            ktype=ktype,
            tipo_anomalia=anomalia.tipo_anomalia,
            severidad=anomalia.severidad,
            campo_afectado=anomalia.campo_afectado,
            valor_detectado=anomalia.valor_detectado,
            valor_esperado=anomalia.valor_esperado,
            mensaje=anomalia.mensaje,
            detalles=anomalia.detalles,
            estado=ESTADO_ANOMALIA_PENDIENTE,
            detectado_por="sistema",
            usuario_creador=usuario,
            fecha_deteccion=datetime.now(),
            contexto=contexto,
        )
        self.db_session.add(registro)
        await self.db_session.flush()
        return registro

    async def resolver_anomalia(
        self,
        id_anomalia: UUID,
        nuevo_estado: str,
        usuario: str,
        nota: str | None = None,
    ) -> AnomaliaRegistro:
        result = await self.db_session.execute(
            select(AnomaliaRegistro).where(AnomaliaRegistro.id == id_anomalia)
        )
        registro = result.scalars().first()
        if not registro:
            from fastapi import HTTPException
            raise HTTPException(404, "Anomalía no encontrada")

        registro.estado = nuevo_estado
        registro.resuelto_por = usuario
        registro.fecha_resolucion = datetime.now()
        registro.nota_resolucion = nota
        self.db_session.add(registro)
        await self.db_session.flush()
        return registro

    async def listar_anomalias(
        self,
        kitem_id: UUID | None = None,
        ktype: str | None = None,
        tipo_anomalia: str | None = None,
        severidad: str | None = None,
        estado: str | None = None,
        limite: int = 50,
    ) -> list[AnomaliaRegistro]:
        query = select(AnomaliaRegistro)

        conditions = []
        if kitem_id:
            conditions.append(AnomaliaRegistro.kitem_id == kitem_id)
        if ktype:
            conditions.append(AnomaliaRegistro.ktype == ktype)
        if tipo_anomalia:
            conditions.append(AnomaliaRegistro.tipo_anomalia == tipo_anomalia)
        if severidad:
            conditions.append(AnomaliaRegistro.severidad == severidad)
        if estado:
            conditions.append(AnomaliaRegistro.estado == estado)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(AnomaliaRegistro.fecha_deteccion.desc()).limit(limite)
        result = await self.db_session.execute(query)
        return result.scalars().all()

    async def _obtener_ficha(self, id_ficha: UUID) -> FichaTecnica:
        result = await self.db_session.execute(
            select(FichaTecnica).where(FichaTecnica.id_ficha == id_ficha)
        )
        ficha = result.scalars().first()
        if not ficha:
            from fastapi import HTTPException
            raise HTTPException(404, "Ficha técnica no encontrada")
        return ficha

    async def _obtener_material(self, id_material: UUID) -> MaterialComercial:
        result = await self.db_session.execute(
            select(MaterialComercial).where(
                MaterialComercial.id_material_corporativo == id_material
            )
        )
        material = result.scalars().first()
        if not material:
            from fastapi import HTTPException
            raise HTTPException(404, "Material comercial no encontrado")
        return material

    async def _obtener_referencias(
        self,
        categoria: str | None,
        excluir_id: UUID | None = None,
    ) -> list[tuple[FichaTecnica, MaterialComercial]]:
        """
        Fichas activas de la categoría con su material. Se excluyen Borrador
        (incompletas) y Obsoleto (la versión anterior duplicaría a la vigente).
        """
        query = (
            select(FichaTecnica, MaterialComercial)
            .join(
                MaterialComercial,
                FichaTecnica.id_material_corporativo
                == MaterialComercial.id_material_corporativo,
            )
            .join(KItem, FichaTecnica.id_ficha == KItem.id)
            .where(KItem.estado.notin_([ESTADO_BORRADOR, ESTADO_OBSOLETO]))
        )
        if categoria:
            query = query.where(MaterialComercial.categoria == categoria)
        if excluir_id:
            query = query.where(FichaTecnica.id_ficha != excluir_id)

        result = await self.db_session.execute(query)
        return [(f, m) for f, m in result.unique().all()]

    @staticmethod
    def _seleccionar_referencia_estadistica(
        material: MaterialComercial,
        referencias: list[tuple[FichaTecnica, MaterialComercial]],
    ) -> tuple[list[FichaTecnica], str]:
        """
        Grupo de comparación para D1, del más específico al más general:
        mismo material → misma familia (categoría + capacidad nominal) → categoría.
        """
        mismo_material = [
            f for f, m in referencias
            if m.id_material_corporativo == material.id_material_corporativo
        ]
        if len(mismo_material) >= MIN_MUESTRAS_MATERIAL:
            return mismo_material, NIVEL_MATERIAL

        capacidad = (getattr(material, "capacidad_nominal", None) or "").strip().lower()
        if capacidad and capacidad != "no aplica":
            familia = [
                f for f, m in referencias
                if (m.capacidad_nominal or "").strip().lower() == capacidad
            ]
            if len(familia) >= MIN_MUESTRAS_FAMILIA:
                return familia, NIVEL_FAMILIA

        return [f for f, _ in referencias], NIVEL_CATEGORIA

    def _extraer_valores_campo(
        self,
        fichas: list[FichaTecnica],
        nombre_seccion: str,
        campo: str,
    ) -> list:
        valores = []
        for ficha in fichas:
            datos = getattr(ficha, nombre_seccion)
            if datos and isinstance(datos, dict):
                valor = datos.get(campo)
                if valor is not None:
                    valores.append(valor)
        return valores