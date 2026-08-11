import logging
from uuid import UUID
from datetime import datetime

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
    UMBRAL_DUPLICADO_FICHA,
    UMBRAL_DUPLICADO_FICHA_CRITICO,
    PORCENTAJE_UNIDAD_MAYORITARIA,
    UMBRAL_CLASIFICACION_CRUZADA,
    CAMPOS_CARACTERISTICAS,
    CAMPOS_CONTENIDO,
    CAMPOS_EMPAQUE,
    ML_SCORE_CRITICO,
    ML_SCORE_ADVERTENCIA,
    rangos_para_categoria,
)

from app.core.dsms_constants import (
    KTYPE_FICHA_TECNICA,
    KTYPE_MATERIAL_COMERCIAL,
)

from app.services.semantic_search_service import BusquedaSemanticaService
from app.services.ml_anomalia_service import MLAnomaliaService

logger = logging.getLogger(__name__)


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

        # Fichas de la misma categoría como referencia estadística
        fichas_referencia = await self._obtener_fichas_referencia(
            categoria=material.categoria,
            excluir_id=id_ficha,
        )

        anomalias: list[AnomaliaDetectada] = []

        # --- Detector 1: Valores atípicos ---
        anomalias.extend(
            self._detectar_valores_atipicos(ficha, fichas_referencia)
        )

        # --- Detector 2: Unidades inconsistentes ---
        anomalias.extend(
            self._detectar_unidades_inconsistentes(ficha, fichas_referencia)
        )

        # --- Detector 3: Duplicados semánticos ---
        duplicados = await self._detectar_duplicados_semanticos(
            kitem_id=id_ficha,
            ktype=KTYPE_FICHA_TECNICA,
            excluir_material_id=material.id_material_corporativo,
            umbral=UMBRAL_DUPLICADO_FICHA,
            umbral_critico=UMBRAL_DUPLICADO_FICHA_CRITICO,
        )
        anomalias.extend(duplicados)

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
    ) -> list[AnomaliaDetectada]:

        anomalias = []

        if len(fichas_referencia) < MIN_MUESTRAS_ESTADISTICAS:
            logger.info(
                f"Solo {len(fichas_referencia)} fichas de referencia, "
                f"insuficientes para detección estadística "
                f"(mínimo {MIN_MUESTRAS_ESTADISTICAS})"
            )
            return anomalias

        # Analizar cada sección JSONB
        secciones = [
            (ficha.caracteristicas, "caracteristicas", CAMPOS_CARACTERISTICAS),
            (ficha.caracteristicas_contenido, "caracteristicas_contenido", CAMPOS_CONTENIDO),
            (ficha.empaque_estiba, "empaque_estiba", CAMPOS_EMPAQUE),
        ]

        for datos_ficha, nombre_seccion, campos in secciones:
            if not datos_ficha:
                continue

            for campo_valor, campo_unidad, nombre_legible in campos:
                valor = datos_ficha.get(campo_valor)
                if valor is None:
                    continue
                # Campo marcado como N/C por el usuario — excluir de cálculos
                if datos_ficha.get(campo_valor.removesuffix("_valor") + "_nc"):
                    continue

                # Recopilar valores históricos del mismo campo
                valores_ref = self._extraer_valores_campo(
                    fichas_referencia, nombre_seccion, campo_valor
                )

                if len(valores_ref) < MIN_MUESTRAS_ESTADISTICAS:
                    continue

                # Calcular estadísticas
                media = sum(valores_ref) / len(valores_ref)
                varianza = sum((v - media) ** 2 for v in valores_ref) / len(valores_ref)
                std = varianza ** 0.5

                if std == 0:

                    if valor != media:
                        anomalias.append(AnomaliaDetectada(
                            tipo_anomalia=ANOMALIA_VALOR_ATIPICO,
                            severidad=SEVERIDAD_ADVERTENCIA,
                            campo_afectado=f"{nombre_seccion}.{campo_valor}",
                            valor_detectado=str(valor),
                            valor_esperado=f"{media} (todas las fichas tienen este valor)",
                            mensaje=(
                                f"{nombre_legible}: el valor {valor} difiere del "
                                f"valor constante {media} en fichas similares."
                            ),
                            detalles={
                                "media": media,
                                "std": 0,
                                "n_muestras": len(valores_ref),
                                "valores_referencia": valores_ref[:10],
                            },
                        ))
                    continue

                # Z-score
                z_score = abs(valor - media) / std

                if z_score >= ZSCORE_CRITICO:
                    severidad = SEVERIDAD_CRITICA
                elif z_score >= ZSCORE_ADVERTENCIA:
                    severidad = SEVERIDAD_ADVERTENCIA
                else:
                    continue  # Valor dentro del rango normal

                rango_min = round(media - ZSCORE_ADVERTENCIA * std, 2)
                rango_max = round(media + ZSCORE_ADVERTENCIA * std, 2)
                unidad = datos_ficha.get(campo_unidad, "")

                anomalias.append(AnomaliaDetectada(
                    tipo_anomalia=ANOMALIA_VALOR_ATIPICO,
                    severidad=severidad,
                    campo_afectado=f"{nombre_seccion}.{campo_valor}",
                    valor_detectado=f"{valor} {unidad}",
                    valor_esperado=f"{rango_min} - {rango_max} {unidad}",
                    mensaje=(
                        f"{nombre_legible}: el valor {valor} {unidad} está fuera "
                        f"del rango típico ({rango_min} - {rango_max} {unidad}) "
                        f"para materiales similares."
                    ),
                    detalles={
                        "media": round(media, 4),
                        "std": round(std, 4),
                        "z_score": round(z_score, 4),
                        "n_muestras": len(valores_ref),
                        "rango_min": rango_min,
                        "rango_max": rango_max,
                    },
                ))

        return anomalias

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


    async def _detectar_clasificacion_cruzada(
        self,
        material: MaterialComercial,
        ficha: FichaTecnica | None = None,
    ) -> list[AnomaliaDetectada]:

        anomalias = []

        try:
            # Buscar materiales similares de CUALQUIER categoría
            resultados = await self.busqueda.buscar_por_texto(
                texto_consulta=(
                    f"{material.nombre_corporativo} "
                    f"{material.contenido or ''} "
                    f"{material.material_base or ''}"
                ),
                ktype=KTYPE_MATERIAL_COMERCIAL,
                limite=10,
                umbral_similitud=UMBRAL_CLASIFICACION_CRUZADA,
            )

            for resultado in resultados:
                anomalia = await self._evaluar_similar_clasificacion(
                    resultado=resultado,
                    material=material,
                    ficha=ficha,
                )
                if anomalia:
                    anomalias.append(anomalia)

        except Exception as e:
            logger.warning(f"Error en detección de clasificación cruzada: {e}")

        return anomalias

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
        severidad = (
            SEVERIDAD_CRITICA if score <= ML_SCORE_CRITICO
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
                "umbral_advertencia": ML_SCORE_ADVERTENCIA,
                "umbral_critico": ML_SCORE_CRITICO,
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
        fichas_ref = await self._obtener_fichas_referencia(
            categoria=material.categoria,
            excluir_id=id_ficha,
        )

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

        # ── D1: Z-Score ──────────────────────────────────────────
        d1: dict = {
            "id": "D1", "nombre": "Valores Atípicos (Z-Score)",
            "n_fichas_referencia": len(fichas_ref),
            "minimo_requerido": MIN_MUESTRAS_ESTADISTICAS,
            "activo": len(fichas_ref) >= MIN_MUESTRAS_ESTADISTICAS,
            "campos": [],
        }
        secciones_d1 = [
            (ficha.caracteristicas,           "caracteristicas",           CAMPOS_CARACTERISTICAS),
            (ficha.caracteristicas_contenido, "caracteristicas_contenido", CAMPOS_CONTENIDO),
            (ficha.empaque_estiba,            "empaque_estiba",            CAMPOS_EMPAQUE),
        ]
        if d1["activo"]:
            for datos_f, nombre_sec, campos in secciones_d1:
                if not datos_f:
                    continue
                for campo_valor, campo_unidad, nombre_leg in campos:
                    valor = datos_f.get(campo_valor)
                    if valor is None:
                        continue
                    if datos_f.get(campo_valor.removesuffix("_valor") + "_nc"):
                        continue
                    valores_ref = self._extraer_valores_campo(fichas_ref, nombre_sec, campo_valor)
                    if len(valores_ref) < MIN_MUESTRAS_ESTADISTICAS:
                        continue
                    media = sum(valores_ref) / len(valores_ref)
                    std   = (sum((v - media) ** 2 for v in valores_ref) / len(valores_ref)) ** 0.5
                    zscore = abs(valor - media) / std if std > 0 else 0
                    d1["campos"].append({
                        "campo": f"{nombre_sec}.{campo_valor}",
                        "nombre": nombre_leg,
                        "valor": valor,
                        "media_historica": round(media, 3),
                        "std_historica": round(std, 3),
                        "zscore": round(zscore, 3),
                        "umbral_advertencia": ZSCORE_ADVERTENCIA,
                        "umbral_critico": ZSCORE_CRITICO,
                        "anomalia": zscore > ZSCORE_ADVERTENCIA,
                        "severidad": "critica" if zscore > ZSCORE_CRITICO else ("advertencia" if zscore > ZSCORE_ADVERTENCIA else "ok"),
                        "n_muestras": len(valores_ref),
                        "valores_referencia": sorted(valores_ref)[:10],
                    })
        d1["anomalias_generadas"] = sum(1 for c in d1["campos"] if c.get("anomalia"))
        detectores.append(d1)

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

        # ── D3: Duplicados semánticos ─────────────────────────────
        d3: dict = {
            "id": "D3", "nombre": "Duplicados Semánticos",
            "embedding_kitem_nombre": embedding_nombre,
            "embedding_kitem_descripcion": embedding_desc,
            "tiene_embedding": tiene_embedding,
            "nota": "Solo se alertan fichas de materiales DISTINTOS al analizado",
            "umbral_advertencia": UMBRAL_DUPLICADO_FICHA,
            "umbral_critico": UMBRAL_DUPLICADO_FICHA_CRITICO,
            "similares": [],
            "anomalias_generadas": 0,
        }
        try:
            resultados_dup = await self.busqueda.buscar_similares_a_kitem(
                kitem_id=id_ficha,
                ktype=KTYPE_FICHA_TECNICA,
                limite=10,
                umbral_similitud=0.5,
            )
            for r in resultados_dup:
                km = r["kitem"]
                sim = r["similitud"]
                # Obtener material de la ficha similar para indicar si es mismo material
                ficha_res = await self.db_session.execute(
                    sa_select(FichaTecnica).where(FichaTecnica.id_ficha == km.id)
                )
                ficha_sim = ficha_res.scalars().first()
                mismo_material = (
                    ficha_sim is not None
                    and ficha_sim.id_material_corporativo == material.id_material_corporativo
                )
                es_duplicado = not mismo_material and sim >= UMBRAL_DUPLICADO_FICHA
                d3["similares"].append({
                    "id": str(km.id),
                    "nombre": km.nombre,
                    "similitud": sim,
                    "mismo_material": mismo_material,
                    "ignorado_por_mismo_material": mismo_material,
                    "es_duplicado": es_duplicado,
                    "severidad": (
                        "ignorado" if mismo_material
                        else "critica" if sim >= UMBRAL_DUPLICADO_FICHA_CRITICO
                        else "advertencia" if sim >= UMBRAL_DUPLICADO_FICHA
                        else "ok"
                    ),
                })
            d3["anomalias_generadas"] = sum(1 for s in d3["similares"] if s["es_duplicado"])
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
            texto_mat = f"{material.nombre_corporativo} {material.contenido or ''} {material.material_base or ''}"
            resultados_mat = await self.busqueda.buscar_por_texto(
                texto_consulta=texto_mat,
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
                d6["umbral_advertencia"] = ML_SCORE_ADVERTENCIA
                d6["umbral_critico"] = ML_SCORE_CRITICO
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

    async def _obtener_fichas_referencia(
        self,
        categoria: str | None,
        excluir_id: UUID | None = None,
    ) -> list[FichaTecnica]:
        query = (
            select(FichaTecnica)
            .join(
                MaterialComercial,
                FichaTecnica.id_material_corporativo
                == MaterialComercial.id_material_corporativo,
            )
        )

        conditions = []
        if categoria:
            conditions.append(MaterialComercial.categoria == categoria)
        if excluir_id:
            conditions.append(FichaTecnica.id_ficha != excluir_id)

        if conditions:
            query = query.where(and_(*conditions))

        result = await self.db_session.execute(query)
        return result.scalars().all()

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