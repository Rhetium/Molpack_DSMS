"""
Servicio principal de detección de anomalías — Orquestador.

Coordina los diferentes detectores (numérico, unidades, clasificación,
duplicados) y persiste los resultados en el repositorio histórico.

Fase 1: Detección basada en estadísticas y reglas.
Fase 2 (futura): Integración con Isolation Forest, One-Class SVM, Autoencoders.

Uso:
    anomalia_svc = AnomaliaService(db_session)
    resultado = await anomalia_svc.analizar_ficha(id_ficha, usuario)
    # resultado.anomalias → lista de anomalías detectadas
"""

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
    ANOMALIA_VALOR_ATIPICO,
    ANOMALIA_UNIDAD_INCONSISTENTE,
    ANOMALIA_CLASIFICACION_CRUZADA,
    ANOMALIA_DUPLICADO_SEMANTICO,
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
    PORCENTAJE_UNIDAD_MAYORITARIA,
    UMBRAL_CLASIFICACION_CRUZADA,
    CAMPOS_CARACTERISTICAS,
    CAMPOS_CONTENIDO,
    CAMPOS_EMPAQUE,
)

from app.core.dsms_constants import (
    KTYPE_FICHA_TECNICA,
    KTYPE_MATERIAL_COMERCIAL,
)

from app.services.semantic_search_service import BusquedaSemanticaService

logger = logging.getLogger(__name__)


class AnomaliaService:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.busqueda = BusquedaSemanticaService(db_session)

    # =========================================================
    # API PÚBLICA
    # =========================================================

    async def analizar_ficha(
        self,
        id_ficha: UUID,
        usuario: str,
        contexto: str = CONTEXTO_CREACION,
    ) -> ResultadoAnalisis:
        """
        Analiza una ficha técnica en busca de anomalías.

        Ejecuta todos los detectores:
        1. Valores atípicos en campos numéricos
        2. Unidades inconsistentes
        3. Duplicados semánticos
        4. Clasificación cruzada (via material asociado)

        Args:
            id_ficha: UUID de la ficha a analizar.
            usuario: Usuario que solicita el análisis.
            contexto: 'creacion', 'actualizacion' o 'analisis_batch'.

        Returns:
            ResultadoAnalisis con todas las anomalías encontradas.
        """
        # Obtener ficha + material asociado
        ficha = await self._obtener_ficha(id_ficha)
        material = await self._obtener_material(ficha.id_material_corporativo)

        # Obtener fichas históricas del mismo tipo para comparación
        fichas_referencia = await self._obtener_fichas_referencia(
            categoria=material.categoria,
            contenido=material.contenido,
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
        )
        anomalias.extend(duplicados)

        # --- Detector 4: Clasificación cruzada ---
        cruzadas = await self._detectar_clasificacion_cruzada(
            material=material,
        )
        anomalias.extend(cruzadas)

        # --- Detector 5: Perfil numérico cruzado ---
        perfil_cruzado = await self._detectar_perfil_numerico_cruzado(
            ficha=ficha,
            material=material,
        )
        anomalias.extend(perfil_cruzado)

        # Persistir anomalías en el repositorio histórico
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
        """
        Analiza un material comercial en busca de anomalías.

        Detectores:
        1. Duplicados semánticos
        2. Clasificación cruzada

        Args:
            id_material: UUID del material a analizar.
            usuario: Usuario que solicita el análisis.
            contexto: 'creacion', 'actualizacion' o 'analisis_batch'.

        Returns:
            ResultadoAnalisis con las anomalías encontradas.
        """
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

    # =========================================================
    # DETECTOR 1: VALORES ATÍPICOS
    # =========================================================

    def _detectar_valores_atipicos(
        self,
        ficha: FichaTecnica,
        fichas_referencia: list[FichaTecnica],
    ) -> list[AnomaliaDetectada]:
        """
        Compara valores numéricos de la ficha contra las estadísticas
        de fichas del mismo tipo/categoría.

        Usa Z-score cuando hay suficientes muestras (>= MIN_MUESTRAS).
        """
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
                    # Todos los valores son iguales; si el nuevo difiere, es anómalo
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

    # =========================================================
    # DETECTOR 2: UNIDADES INCONSISTENTES
    # =========================================================

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

    # =========================================================
    # DETECTOR 3: DUPLICADOS SEMÁNTICOS
    # =========================================================

    async def _detectar_duplicados_semanticos(
        self,
        kitem_id: UUID,
        ktype: str,
    ) -> list[AnomaliaDetectada]:
        """
        Busca k-items semánticamente muy similares al actual
        usando los embeddings de pgvector.
        """
        anomalias = []

        try:
            # Buscar k-items similares (excluyendo el actual)
            resultados = await self.busqueda.buscar_similares(
                kitem_id=kitem_id,
                ktype=ktype,
                limite=5,
                umbral_similitud=UMBRAL_DUPLICADO_SEMANTICO,
            )

            for resultado in resultados:
                kitem_similar = resultado["kitem"]
                similitud = resultado["similitud"]

                # No reportar si es el mismo k-item
                if kitem_similar.id == kitem_id:
                    continue

                if similitud >= UMBRAL_DUPLICADO_CRITICO:
                    severidad = SEVERIDAD_CRITICA
                else:
                    severidad = SEVERIDAD_ADVERTENCIA

                anomalias.append(AnomaliaDetectada(
                    tipo_anomalia=ANOMALIA_DUPLICADO_SEMANTICO,
                    severidad=severidad,
                    campo_afectado=None,
                    valor_detectado=None,
                    valor_esperado=None,
                    mensaje=(
                        f"Posible duplicado detectado: '{kitem_similar.nombre}' "
                        f"tiene {similitud:.0%} de similitud. "
                        f"¿Es el mismo registro?"
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

    # =========================================================
    # DETECTOR 4: CLASIFICACIÓN CRUZADA
    # =========================================================

    async def _detectar_clasificacion_cruzada(
        self,
        material: MaterialComercial,
    ) -> list[AnomaliaDetectada]:
        """
        Detecta cuando un material parece pertenecer a otra categoría
        basándose en la similitud semántica con materiales de otras categorías.

        Ejemplo: Material declarado como "Bandeja" pero su perfil es
        idéntico al de los "Separadores".
        """
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
                kitem_similar = resultado["kitem"]
                similitud = resultado["similitud"]

                # No reportar si es el mismo material
                if kitem_similar.id == material.id_material_corporativo:
                    continue

                # Obtener la categoría del material similar
                result = await self.db_session.execute(
                    select(MaterialComercial).where(
                        MaterialComercial.id_material_corporativo == kitem_similar.id
                    )
                )
                material_similar = result.scalars().first()
                if not material_similar:
                    continue

                # Solo alertar si la categoría es diferente
                if (
                    material_similar.categoria
                    and material.categoria
                    and material_similar.categoria != material.categoria
                    and similitud >= UMBRAL_CLASIFICACION_CRUZADA
                ):
                    anomalias.append(AnomaliaDetectada(
                        tipo_anomalia=ANOMALIA_CLASIFICACION_CRUZADA,
                        severidad=SEVERIDAD_ADVERTENCIA,
                        campo_afectado="categoria",
                        valor_detectado=material.categoria,
                        valor_esperado=material_similar.categoria,
                        mensaje=(
                            f"El material '{material.nombre_corporativo}' "
                            f"(categoría: {material.categoria}) tiene "
                            f"{similitud:.0%} de similitud con "
                            f"'{material_similar.nombre_corporativo}' "
                            f"(categoría: {material_similar.categoria}). "
                            f"¿La categoría es correcta?"
                        ),
                        detalles={
                            "material_similar_id": str(material_similar.id_material_corporativo),
                            "material_similar_nombre": material_similar.nombre_corporativo,
                            "categoria_similar": material_similar.categoria,
                            "categoria_actual": material.categoria,
                            "similitud": similitud,
                        },
                    ))

        except Exception as e:
            logger.warning(f"Error en detección de clasificación cruzada: {e}")

        return anomalias

    # =========================================================
    # DETECTOR 5: PERFIL NUMÉRICO CRUZADO
    # =========================================================

    async def _detectar_perfil_numerico_cruzado(
        self,
        ficha: FichaTecnica,
        material: MaterialComercial,
    ) -> list[AnomaliaDetectada]:
        """
        Compara el perfil numérico de una ficha contra los promedios
        de cada categoría. Si los valores encajan mejor en otra categoría,
        genera una alerta.

        Ejemplo: Ficha de "Bandeja 1x30" (categoría Bandejas) cuyos valores
        numéricos se parecen más a los de categoría "Separador".
        """
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

    async def _calcular_perfiles_categorias(
        self,
        excluir_ficha_id: UUID | None = None,
    ) -> dict:
        """
        Calcula el centroide (media) y desviación estándar de los
        valores numéricos agrupados por categoría del material.
        """
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
        """
        Extrae un vector de valores numéricos de una ficha.
        Combina campos de caracteristicas, caracteristicas_contenido y empaque.
        """
        vector = {}
        secciones = [
            (ficha.caracteristicas, CAMPOS_CARACTERISTICAS),
            (ficha.caracteristicas_contenido, CAMPOS_CONTENIDO),
            (ficha.empaque_estiba, CAMPOS_EMPAQUE),
        ]
        for datos, campos in secciones:
            if not datos:
                continue
            for campo_valor, campo_unidad, nombre_legible in campos:
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
        """
        Distancia euclidiana normalizada por desviación estándar
        entre un vector y un centroide. Solo usa campos comunes.
        """
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

    # =========================================================
    # REPOSITORIO HISTÓRICO
    # =========================================================

    async def _persistir_anomalia(
        self,
        kitem_id: UUID,
        ktype: str,
        anomalia: AnomaliaDetectada,
        usuario: str,
        contexto: str,
    ) -> AnomaliaRegistro:
        """Guarda una anomalía detectada en el repositorio histórico."""
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
        """Marca una anomalía como aceptada, descartada o corregida."""
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
        """Consulta anomalías históricas con filtros opcionales."""
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

    # =========================================================
    # HELPERS INTERNOS
    # =========================================================

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
        contenido: str | None,
        excluir_id: UUID | None = None,
    ) -> list[FichaTecnica]:
        """
        Obtiene fichas del mismo tipo de material (categoría + contenido)
        para usar como referencia estadística.
        """
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
        if contenido:
            conditions.append(MaterialComercial.contenido == contenido)
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
        """Extrae valores de un campo específico de una lista de fichas."""
        valores = []
        for ficha in fichas:
            datos = getattr(ficha, nombre_seccion)
            if datos and isinstance(datos, dict):
                valor = datos.get(campo)
                if valor is not None:
                    valores.append(valor)
        return valores