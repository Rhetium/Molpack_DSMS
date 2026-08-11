# Guía de Defensa — Molpack DSMS
## Simulador de jurado: 60 preguntas con guión de respuesta

> Cada pregunta incluye **qué está evaluando realmente el jurado** y un **guión de
> respuesta**. No memorices los guiones palabra por palabra: entendé el argumento y
> reformulalo. Un jurado detecta al instante una respuesta recitada.

---

## Cómo usar este documento

| Bloque | Preguntas | Qué evalúa |
|---|---|---|
| A | 1–15 | **Rastreabilidad**: ¿conocés tu propio código? |
| B | 16–33 | **Justificación**: ¿por qué así y no de otra forma? |
| C | 34–48 | **Casos límite**: ¿qué pasa cuando algo sale mal? |
| D | 49–56 | **Preguntas difíciles**: las que exponen debilidades reales |
| E | 57–60 | **Cierre**: visión, alcance, trabajo futuro |

**Tres reglas para la defensa:**

1. **Si no sabés, decilo y ofrecé el camino.** *"No lo tengo presente, pero está en
   `X`; el mecanismo es Y."* Es infinitamente mejor que inventar.
2. **Nunca defiendas lo indefendible.** Ante una debilidad real: reconocela,
   explicá por qué quedó así y cómo se corrige. El jurado evalúa criterio, no
   perfección.
3. **Traé la conversación a tus fortalezas.** Toda respuesta puede terminar
   conectando con el patrón K-Item, la máquina de estados o el versionado.

---

# BLOQUE A — Preguntas de Rastreabilidad

### 1. "Quiero agregar un estado nuevo, 'Aprobado por Calidad', entre Preliminar y Vigente. ¿Dónde tocás?"

**Evalúa:** si tu diseño es realmente extensible o solo lo decís.

**Guión:**
> "Tres archivos, en este orden. Primero `app/core/dsms_constants.py`: defino
> `ESTADO_APROBADO_CALIDAD = "Aprobado por Calidad"`, lo agrego a
> `TRANSACCIONES_PERMITIDAS` cambiando `Preliminar: {Vigente, Obsoleto}` por
> `Preliminar: {AprobadoCalidad, Obsoleto}` y agrego la entrada nueva
> `AprobadoCalidad: {Vigente, Obsoleto}`, y sumo su abreviatura a
> `ESTADO_ABREVIATURAS` porque entra en el código de ficha.
>
> Segundo, si el estado exige campos adicionales, agrego un
> `_validar_para_aprobado_calidad` en `FichaService` y lo engancho en el `elif` de
> `cambiar_estado`.
>
> Tercero, un endpoint semántico en `app/routers/ficha.py`.
>
> **Lo que no toco es el motor de validación.** `_validar_transicion_estado` hace un
> lookup en el diccionario; no tiene condicionales por estado. Esa es exactamente la
> razón por la que modelé las transiciones como datos y no como `if/elif`."

---

### 2. "Si quiero cambiar el umbral que marca un valor como crítico, ¿dónde está?"

**Guión:**
> "`app/core/anomalia_constant.py`, constante `ZSCORE_CRITICO = 3.0`. Se consume en
> `AnomaliaService._detectar_valores_atipicos`, donde comparo
> `if z_score >= ZSCORE_CRITICO: severidad = SEVERIDAD_CRITICA`.
>
> Centralicé todos los umbrales ahí porque calibrar detectores es empírico: si
> estuvieran dispersos, ajustarlos obligaría a tocar lógica y arriesgar regresiones.
> Además `tests/test_anomalia_constant.py` verifica invariantes, como que el umbral
> crítico sea siempre mayor que el de advertencia."

---

### 3. "¿Dónde exactamente se decide que una ficha Vigente no se puede editar?"

**Guión:**
> "`FichaService.actualizar()`, en `app/services/fichas_services.py`. Hay tres ramas:
> si el estado es `Obsoleto` lanzo un 400 y corto; si es `Vigente` o `Revisión`
> derivo a `_modificar_ficha_vigente`; en cualquier otro caso —Borrador o
> Preliminar— voy a `_modificar_ficha_editable`, que edita en el lugar.
>
> Lo importante es que `_modificar_ficha_vigente` **no modifica la ficha vigente**.
> Crea un K-Item nuevo con versión incrementada, copia las secciones, aplica los
> cambios sobre la copia, crea la relación `se_deriva_de` hacia la original y recién
> ahí marca la original como Obsoleto. La ficha publicada nunca se toca."

---

### 4. "Cambio el modelo de embeddings a uno de 768 dimensiones. ¿Qué se rompe?"

**Guión:**
> "Tres puntos. Uno: `EMBEDDING_DIMENSION` en `app/models/kitem.py`, que define
> `Vector(384)`. Dos: la variable de entorno `EMBEDDING_MODEL_NAME`. Tres —y este es
> el crítico— **una migración de base**, porque la columna `vector(384)` no acepta
> vectores de 768; hay que alterar el tipo y **regenerar todos los embeddings**.
>
> Para eso existe `BusquedaSemanticaService.reindexar_masivo`, que recorre los
> K-Items y los reprocesa en lotes de 64. Los vectores viejos y nuevos son
> incomparables: viven en espacios distintos. La reindexación no es opcional, es
> obligatoria."

---

### 5. "Muéstreme dónde se genera el código de una ficha y qué lo determina."

**Guión:**
> "`FichaService._generar_codigo_ficha`. Devuelve
> `f"FT-{codigo_material_local}-{pais}-{abreviatura_estado}-V{version}"`, por ejemplo
> `FT-4500123-CO-BOR-V1.0`.
>
> Depende de cuatro variables: código de material local, país en ISO alpha-2,
> abreviatura del estado —que sale de `ESTADO_ABREVIATURAS`— y versión.
>
> El punto de diseño es que el código es **derivado, no fuente de verdad**. Se
> regenera en cada `cambiar_estado` y en cada `actualizar`. Si lo guardara una sola
> vez, un cambio de estado lo dejaría mintiendo. Al recalcularlo, es imposible que
> se desincronice."

---

### 6. "¿Dónde se garantiza que solo haya una ficha vigente por material y país?"

**Guión:**
> "`_validar_unica_vigente_por_material_pais`, que se invoca desde `cambiar_estado`
> solo cuando el destino es `Vigente`. Hace un `SELECT` con JOIN a `kitem` filtrando
> por mismo material, mismo país, `kitem.estado == 'Vigente'` y excluyendo la ficha
> actual con `id_ficha != ficha.id_ficha`. Si encuentra algo, lanza 400.
>
> El JOIN es obligatorio y no cosmético: `estado_ficha` es una `@property` de Python,
> invisible para SQL. Tengo que filtrar por `KItem.estado`.
>
> **Y debo aclarar algo con honestidad:** es una regla de aplicación, no una
> restricción de base. Un `UNIQUE` parcial —`UNIQUE (material, pais) WHERE estado =
> 'Vigente'`— la haría infalsificable ante escrituras concurrentes. Hoy, dos
> peticiones simultáneas podrían pasar ambas la validación."

---

### 7. "¿Dónde se registra quién hizo cada cambio y cómo lo consulto?"

**Guión:**
> "Todo pasa por `AuditoriaService.registrar`, que inserta en `kitem_auditoria`:
> qué K-Item, qué tipo, qué acción, estado anterior y nuevo, un JSONB de detalles,
> usuario y fecha.
>
> Lo llaman `KItemService` en creación, cambio de estado y relaciones;
> `FichaService` en transiciones, modificaciones y versionado; y
> `BusquedaSemanticaService` al generar embeddings.
>
> Se consulta por `GET /dsms/auditoria`, con filtros por ktype, acción, usuario y
> categoría, o el historial de un K-Item puntual.
>
> **Sobre de dónde sale el 'quién':** del token JWT, mediante la dependencia
> `get_usuario_nombre`. Nunca del cuerpo de la petición. Esto lo corregí
> explícitamente: antes el cliente enviaba su propia identidad y las transiciones de
> estado la tenían hardcodeada como 'sistema', así que la auditoría era falsificable
> en el primer caso e inútil en el segundo. Como el token está firmado con HS256, el
> usuario que queda registrado es criptográficamente atribuible."

---

### 8. "Si una ficha muestra una anomalía incorrecta, ¿cómo rastreo por qué se disparó?"

**Guión:**
> "Dos caminos. El de datos: cada `AnomaliaRegistro` guarda un JSONB `detalles` con
> la evidencia del detector. Para un z-score guardo media, desviación, z-score,
> número de muestras y el rango esperado. Con eso reconstruyo el cálculo sin
> ejecutar nada.
>
> El de diagnóstico: existe `AnomaliaService.analizar_debug(id_ficha)`, expuesto en
> la ruta `/dev/anomalias` del frontend. Devuelve el estado de los siete detectores
> —si estaban activos, cuántas fichas de referencia había, qué campos evaluó y con
> qué estadísticas—. Lo construí precisamente porque depurar un detector
> probabilístico mirando solo el resultado final es inviable."

---

### 9. "¿Dónde está la lógica que impide avanzar una ficha con anomalías pendientes?"

**Guión:**
> "En `cambiar_estado`, después de validar la transición. Consulto
> `AnomaliaRegistro` filtrando por `kitem_id` y `estado == 'pendiente'`; si hay
> alguna, lanzo 400 con el conteo.
>
> Esta es la integración central entre los dos subsistemas: el motor de anomalías no
> es informativo, tiene **poder de veto** sobre el flujo de aprobación. Un humano
> debe aceptar, descartar o corregir antes de que la ficha avance.
>
> **Una limitación que reconozco:** bloqueo ante *cualquier* anomalía pendiente,
> incluidas las de severidad `informativa`. Lo correcto sería filtrar por severidad
> y dejar que solo críticas y advertencias bloqueen."

---

### 10. "Quiero que las fichas también se relacionen con normas ISO. ¿Cuánto código nuevo?"

**Guión:**
> "Muy poco, y ese es justamente el argumento del patrón K-Item.
>
> No necesito tabla puente ni tocar el motor de relaciones. Agrego
> `KTYPE_NORMA = "Norma"` y `REL_CUMPLE_NORMA = "cumple_norma"` en `dsms_constants`,
> lo sumo a `RELACIONES_VALIDAS`, creo la tabla de extensión `norma` con PK
> compartida hacia `kitem.id`, y un `NormaService` para su lógica propia.
>
> Lo que **ya funciona sin escribir una línea**: la relación se crea con
> `KItemService.crear_relacion`, la norma aparece en el grafo de
> `obtener_grafo_kitem`, es buscable semánticamente porque el embedding vive en
> `KItem`, y su auditoría se registra igual que la de cualquier otro K-Item.
>
> Con tablas independientes por entidad, cada una de esas cuatro capacidades habría
> exigido código nuevo."

---

### 11. "¿Dónde se convierte el texto de la ficha en el vector que se guarda?"

**Guión:**
> "Cadena de tres pasos. `BusquedaSemanticaService.asignar_embedding` carga el
> K-Item y llama a `construir_texto_embedding`, que arma un texto plano combinando
> `[ktype] nombre`, la descripción, los campos adicionales que le pase el llamador y
> claves útiles de `metadata_extra`. Ese texto va a `generar_embedding`, que invoca
> `modelo.encode(texto, normalize_embeddings=True)` y devuelve una lista de 384
> flotantes. Finalmente se asigna a `kitem.embedding` y se registra auditoría.
>
> El detalle de diseño está en `construir_texto_embedding`: incluyo el `ktype` dentro
> del texto para que el vector codifique de qué tipo de objeto se trata, y convierto
> guiones bajos en espacios porque el modelo fue entrenado con lenguaje natural."

---

### 12. "Muéstreme el punto exacto donde se confirma la transacción al crear una ficha."

**Guión:**
> "Un solo `await self.db_session.commit()` al final de `FichaService.crear`,
> después de las nueve operaciones previas.
>
> Todos los servicios intermedios —`KItemService`, `AuditoriaService`,
> `BusquedaSemanticaService`— hacen `flush()`, no `commit()`. `flush()` envía el SQL
> dentro de la transacción abierta: las filas existen para esta sesión y ya tienen
> UUID, pero no son visibles para nadie más y desaparecen con un rollback.
>
> Si fallara la generación del embedding en el paso 8, el rollback borra también el
> K-Item, la ficha, la relación y los registros de auditoría. **El servicio que
> inicia la operación es el único que decide cuándo confirmar.** Y esto funciona
> porque todos comparten la misma `AsyncSession`, inyectada una sola vez por
> `get_session`."

---

### 13. "¿Cómo sabe el sistema qué fichas usar como referencia estadística?"

**Guión:**
> "`_obtener_fichas_referencia(categoria, excluir_id)`. Hace JOIN entre
> `ficha_tecnica` y `material_comercial` filtrando por la categoría del material y
> excluyendo la ficha analizada.
>
> La exclusión es imprescindible: si la ficha se incluyera a sí misma, contaminaría
> la media y la desviación contra las que se compara, sesgando el z-score hacia la
> normalidad. Un valor extremo se auto-justificaría.
>
> El criterio de agrupación es la **categoría del material**, no el material
> individual: comparar contra fichas del mismo material daría muestras insuficientes
> casi siempre."

---

### 14. "¿Dónde se decide si una modificación crea versión nueva o edita en el lugar?"

**Guión:**
> "En el `if` de `FichaService.actualizar`, sobre `ficha.estado_ficha`. Obsoleto
> rechaza; Vigente y Revisión derivan a versionado; Borrador y Preliminar editan
> directo.
>
> El criterio es si el documento fue publicado. Borrador y Preliminar son trabajo en
> curso: editarlos no rompe nada. Vigente es un documento que pudo imprimirse o
> enviarse a un cliente; su contenido es un hecho histórico."

---

### 15. "Si quiero agregar un octavo detector de anomalías, ¿qué implica?"

**Guión:**
> "Un método privado en `AnomaliaService` con la firma
> `_detectar_X(ficha, ...) -> list[AnomaliaDetectada]`, una línea
> `anomalias.extend(self._detectar_X(...))` en `analizar_ficha`, y su constante de
> tipo en `anomalia_constant.py`.
>
> No toco los otros siete. Cada detector es independiente y devuelve una lista;
> `analizar_ficha` solo acumula. La persistencia, el conteo por severidad y el
> bloqueo del flujo funcionan sobre la lista agregada, sin importar quién la generó.
>
> Si el detector necesita umbrales, van a `anomalia_constant.py` por coherencia."

---

# BLOQUE B — Justificación y Alternativas

### 16. "¿Por qué el patrón K-Item y no tablas independientes? Suena a complejidad innecesaria."

**Evalúa:** si la decisión arquitectónica más importante fue deliberada o copiada.

**Guión:**
> "El costo del patrón es real: un JOIN extra en casi toda consulta. Lo asumí porque
> compra cuatro capacidades transversales que de otro modo habría que reimplementar
> por cada entidad.
>
> Concretamente: el embedding vive en `KItem`, así que `buscar_por_texto` encuentra
> materiales y fichas con **la misma query**. El grafo `KItemRelacion` conecta
> cualquier tipo con cualquier tipo sin tablas puente. La auditoría es una sola tabla
> con una sola API. Y agregar un tipo nuevo —normas, incidencias— no toca ninguno de
> esos tres subsistemas.
>
> Con tablas independientes tendría `buscar_material` y `buscar_ficha` separadas,
> `material_norma` y `ficha_norma` separadas, y auditorías por entidad. La
> complejidad no desaparece: se multiplica por el número de tipos.
>
> El patrón viene del paper DSMS de Nahshon et al. (2023), que formaliza el K-Item
> como Metadata + Data Container + Semantic Graph. Cada componente tiene su lugar en
> mi esquema: la tabla `kitem`, las tablas de extensión con JSONB, y
> `kitem_relacion` más la columna `embedding`."

---

### 17. "¿Por qué máquina de estados en un diccionario y no una librería como `transitions`?"

**Guión:**
> "Evalué el intercambio. `transitions` aporta callbacks por transición, estados
> jerárquicos y generación de diagramas. Nada de eso lo necesito: tengo cinco
> estados, transiciones planas y los efectos de lado ya están explícitos en
> `cambiar_estado`.
>
> Lo que gano con el diccionario: validación O(1) por hash, cero dependencias, y las
> reglas de negocio legibles en siete líneas que un auditor no programador puede
> revisar.
>
> Lo que perdería con la librería: acoplar una regla de negocio central a una
> dependencia externa, y que entender el flujo exija conocer su API.
>
> Si el sistema creciera a estados jerárquicos o transiciones con guardas complejas,
> reconsideraría."

---

### 18. "¿Por qué pgvector y no Pinecone, Weaviate o FAISS?"

**Guión:**
> "El argumento decisivo es **transaccional**. Con pgvector, el embedding es una
> columna de la misma fila que el resto del K-Item. Cuando hago `commit()`, el dato
> y su vector se persisten atómicamente. Con una base vectorial externa tendría dos
> sistemas que sincronizar, y el escenario de fallo clásico: la ficha se guardó pero
> el vector no, o al revés. Necesitaría escritura en dos fases o un proceso de
> reconciliación.
>
> Segundo argumento: puedo **filtrar y ordenar semánticamente en la misma query**.
> `buscar_por_texto` combina `WHERE ktype = ... AND estado = ...` con
> `ORDER BY embedding <=> consulta`. Con un motor externo tendría que traer los
> k vecinos y filtrarlos después en Python, sin garantía de que queden k resultados.
>
> Tercero: cero infraestructura adicional. Ya necesito PostgreSQL.
>
> FAISS es una librería en memoria, no un almacén persistente: exigiría reconstruir
> el índice al arrancar. Pinecone y Weaviate ganan a escala de millones de vectores;
> a esta escala su ventaja no compensa el costo de consistencia."

---

### 19. "¿Qué complejidad temporal tiene la búsqueda semántica y por qué?"

**Guión:**
> "Depende del índice. Sin índice, PostgreSQL hace escaneo secuencial: calcula la
> distancia coseno contra los n vectores, **O(n·d)** donde d = 384. Con el índice
> HNSW que crea `schema_clean.sql`, la búsqueda aproximada de los k vecinos más
> cercanos es **O(log n)** en la práctica.
>
> HNSW es *Hierarchical Navigable Small World*: un grafo multicapa donde las capas
> superiores tienen enlaces largos para saltar regiones y las inferiores enlaces
> cortos para refinar. La búsqueda desciende por capas haciendo *greedy search*.
>
> El intercambio es que es **aproximada**: puede perder algún vecino real. Los
> parámetros `m = 16` y `ef_construction = 64` controlan ese equilibrio; más altos
> dan mejor *recall* a costa de memoria y tiempo de construcción.
>
> Elegí HNSW sobre IVFFlat porque no requiere datos precargados para construirse ni
> reajustar el parámetro `lists` a medida que el catálogo crece."

---

### 20. "¿Por qué Isolation Forest y no un autoencoder, DBSCAN o One-Class SVM?"

**Guión:**
> "Cuatro criterios, y los ordeno por peso.
>
> **No supervisado obligatorio.** No tengo un histórico etiquetado de 'fichas
> incorrectas'. Eso descarta cualquier clasificador supervisado.
>
> **Funciona con pocas muestras.** Entreno con un mínimo de cinco fichas por
> categoría. Un autoencoder necesita cientos o miles de ejemplos para aprender una
> representación útil; con cinco memoriza.
>
> **Complejidad y determinismo.** Isolation Forest entrena en O(n log n) y predice en
> O(log n). Con `random_state=42` es reproducible, lo cual importa para auditar.
> DBSCAN es O(n log n) pero exige calibrar `eps` y `min_samples`, muy sensibles a la
> escala y difíciles de justificar ante un usuario.
>
> **Interpretabilidad razonable.** El score de decisión tiene una lectura directa:
> qué tan fácil fue aislar el punto. Puedo reportarlo junto con los campos
> analizados. Un autoencoder daría un error de reconstrucción mucho más opaco.
>
> One-Class SVM era el candidato más cercano, pero escala peor —entre O(n²) y O(n³)—
> y es muy sensible al kernel y a `nu`."

---

### 21. "¿Por qué async en todo el stack? ¿No agrega complejidad sin necesidad?"

**Guión:**
> "El sistema es intensivo en I/O de latencia alta y variable: consultas vectoriales,
> autenticación LDAP contra un servidor remoto, lectura de modelos ML desde disco,
> generación de PDFs.
>
> En un modelo síncrono, cada petición ocupa un hilo completo mientras espera. Con
> async, mientras una petición espera la respuesta de PostgreSQL, el *event loop*
> atiende otras. Con el mismo hardware sostengo más concurrencia.
>
> La complejidad que agrega es real —hay que ser disciplinado con el `await`, y
> mezclar código bloqueante mata el beneficio—. Por eso el stack es coherente de
> punta a punta: FastAPI, SQLAlchemy 2.0 async y asyncpg como driver. Si usara
> `psycopg2` dentro de un endpoint async, bloquearía el loop y sería peor que
> síncrono.
>
> El caso donde más se nota es el auto-entrenamiento: lo lanzo con
> `asyncio.create_task` y el usuario recibe su respuesta inmediatamente mientras el
> modelo se reentrena de fondo."

---

### 22. "¿Por qué JSONB para las secciones de la ficha y no columnas normalizadas?"

**Guión:**
> "Las cinco secciones tienen entre 15 y 40 campos cada una, y su composición depende
> del tipo de producto: una ficha de separadores no tiene los mismos campos que una
> de envases. Normalizarlo daría una tabla con más de cien columnas mayormente nulas,
> o un esquema entidad-atributo-valor, que es notoriamente difícil de consultar.
>
> JSONB me da esquema flexible por tipo de producto sin migración, y PostgreSQL lo
> indexa con GIN, así que sigue siendo consultable —no es un blob opaco—.
>
> El costo lo reconozco: **la base no valida el contenido**. Un campo mal escrito no
> lo detecta PostgreSQL. Esa validación la asumen los schemas Pydantic en la
> frontera de entrada y las constantes `CAMPOS_CARACTERISTICAS` en los detectores.
>
> Es un intercambio consciente: muevo la validación de la capa de datos a la capa de
> aplicación a cambio de flexibilidad de esquema."

---

### 23. "¿Por qué UUID y no enteros autoincrementales?"

**Guión:**
> "Tres razones. Se generan en el cliente antes de tocar la base, lo cual simplifica
> operaciones que crean varios objetos relacionados. No filtran información: un
> `id=47` le dice a cualquiera cuántas fichas tiene la empresa. Y no colisionan si en
> el futuro se fusionan bases de distintas plantas.
>
> Los costos son concretos: 16 bytes contra 4, y peor localidad de índice, porque los
> UUID v4 son aleatorios y provocan más divisiones de página en el B-tree que una
> secuencia monótona.
>
> A esta escala el costo es despreciable frente al beneficio. Si el volumen creciera
> mucho, evaluaría UUID v7, que es ordenable temporalmente y recupera la localidad."

---

### 24. "¿Por qué normalizar los embeddings al generarlos?"

**Guión:**
> "Uso `normalize_embeddings=True`, que deja todos los vectores con norma 1. Con
> vectores unitarios, el **producto punto equivale a la similitud coseno**, porque
> el denominador de la fórmula es 1.
>
> Eso permite que pgvector calcule distancias sin normalizar en tiempo de consulta, y
> que el índice HNSW opere directamente sobre esa métrica.
>
> Conceptualmente también es lo correcto: quiero comparar **dirección semántica**, no
> magnitud. Sin normalizar, un texto largo produciría un vector de mayor norma y
> parecería 'más similar' a todo por un artefacto de longitud, no de significado."

---

### 25. "¿Por qué composición entre servicios y no herencia?"

**Guión:**
> "Porque la relación semántica es 'usa', no 'es un'. `FichaService` no es un
> `KItemService` especializado: es un orquestador que **usa** un `KItemService` para
> la parte de K-Item, un `AuditoriaService` para el registro y un `AnomaliaService`
> para el análisis.
>
> Con herencia habría acoplado jerárquicamente servicios que solo colaboran, y
> `FichaService` heredaría métodos que no le corresponden, como `eliminar_relacion`.
>
> Además, la composición me permite pasar la **misma sesión** a todos los
> colaboradores, que es lo que mantiene la transacción única. Y en tests puedo
> reemplazar cualquier colaborador por un mock sin tocar jerarquías."

---

### 26. "¿Por qué las validaciones están en el servicio y no como constraints de base?"

**Guión:**
> "Están en ambos lados, según el tipo de regla.
>
> En la base están las invariantes estructurales: claves foráneas con `ON DELETE`
> definido, `NOT NULL`, y un `UNIQUE (source_id, target_id, tipo_relacion)` en
> `kitem_relacion`.
>
> En el servicio están las reglas de negocio: las transiciones válidas, la
> completitud por estado, la unicidad de ficha vigente. Tres razones: producen
> mensajes de error accionables —'faltan Uso, Manejo y Vida útil' en vez de
> 'violación de constraint 23514'—; permiten reglas que dependen de estado dinámico o
> de varias tablas; y son testeables sin base de datos.
>
> **Y admito una excepción incómoda:** la regla de ficha única vigente *debería*
> tener respaldo en base con un `UNIQUE` parcial. Hoy, dos peticiones concurrentes
> podrían pasar ambas la validación de aplicación. Es la brecha más relevante entre
> mis reglas y las garantías reales del motor."

---

### 27. "¿Por qué siete detectores? ¿No es sobreingeniería?"

**Guión:**
> "Son complementarios, no redundantes. Cada uno detecta una clase de error que los
> demás no ven.
>
> El z-score detecta un valor numérico fuera de rango. No detecta que cargaron
> milímetros donde el resto usa centímetros si el número resultante cae en rango:
> para eso está el detector de unidades. Ninguno de los dos detecta que cada campo es
> plausible pero su combinación no existe: para eso está el Isolation Forest. Ninguno
> de los tres detecta que la ficha está bien pero el material está mal clasificado:
> para eso están clasificación cruzada y perfil numérico.
>
> Y hay un eje adicional: **cuántos datos necesitan**. Los rangos duros funcionan
> desde la primera ficha; el z-score necesita tres; el Isolation Forest cinco. El
> sistema degrada ordenadamente: con pocos datos protege menos, pero nunca falla ni
> genera falsos positivos por muestras insuficientes."

---

### 28. "¿Por qué modelo de embeddings local y no la API de OpenAI?"

**Guión:**
> "Tres razones, la primera decisiva. **Privacidad**: son especificaciones técnicas
> de producto de la empresa; no salen de la red. **Costo**: cero por consulta, sin
> límite de tasa. Importa porque el análisis de anomalías genera varios embeddings
> por ficha. **Latencia**: sin viaje de red en un flujo que ya hace varias
> operaciones encadenadas.
>
> El costo es calidad semántica: `all-MiniLM-L6-v2` produce 384 dimensiones contra
> las 1536 de `text-embedding-3-small`, y captura matices con menos finura.
>
> Por eso aislé la dimensión en una constante y el nombre del modelo en una variable
> de entorno: la migración es un cambio de configuración más una reindexación
> masiva, no una reescritura."

---

### 29. "¿Por qué endpoints semánticos como `/publicar` y no un PATCH genérico?"

**Guión:**
> "`POST /ficha/{id}/publicar` expresa una intención de negocio.
> `PATCH /ficha/{id} {"estado": "Vigente"}` expresaría una mutación de campo.
>
> La diferencia práctica: la ruta semántica es autodocumentada en OpenAPI —el jurado
> o un desarrollador nuevo entiende qué hace sin leer el cuerpo—; permite permisos
> por acción, que 'publicar' exija rol de supervisor mientras 'archivar' no; y evita
> que el cliente tenga que conocer los nombres internos de los estados.
>
> Con PATCH genérico, cada cliente necesitaría replicar la máquina de estados para
> saber qué valores son válidos."

---

### 30. "¿Cuál es la complejidad de `_calcular_perfiles_categorias`?"

**Evalúa:** si conocés los costos de tu código, no solo su funcionamiento.

**Guión:**
> "**O(n·c)** donde n es el total de fichas y c el número de campos numéricos. Carga
> *todas* las fichas con su material, las agrupa por categoría, y calcula centroide y
> desviación por campo.
>
> Y acá está el problema que reconozco: **se ejecuta en cada análisis de anomalías**.
> Analizar una ficha implica recalcular los centroides de todas las categorías desde
> cero. Con el volumen actual es imperceptible, pero es O(n) por análisis: no escala.
>
> La corrección natural es cachear los centroides e invalidarlos solo cuando se
> publica una ficha nueva, que es exactamente el evento que ya dispara el
> reentrenamiento del modelo ML. Podrían compartir el mismo mecanismo de
> invalidación."

---

### 31. "¿Por qué `expire_on_commit=False`? ¿No es peligroso?"

**Guión:**
> "Por defecto SQLAlchemy marca los objetos como expirados tras un commit, y el
> siguiente acceso a un atributo dispara un SELECT de refresco. En código asíncrono
> ese refresco implícito ocurre fuera del contexto async y lanza `MissingGreenlet`.
>
> Al desactivarlo, después de `commit()` los objetos siguen usables para construir la
> respuesta HTTP, que es exactamente lo que necesito: `crear()` hace commit y devuelve
> la ficha para serializar.
>
> El riesgo es que los objetos podrían quedar desactualizados si otra transacción
> modificó las filas. En mi caso no aplica: la sesión vive lo que dura una petición y
> los objetos se descartan al responder. Donde necesito el estado fresco —después de
> operaciones que modifican vía UPDATE directo— llamo `refresh()` explícitamente."

---

### 32. "¿Por qué el frontend no usa React Query si está instalado?"

**Evalúa:** honestidad. Es una inconsistencia visible y detectable.

**Guión:**
> "Es una dependencia declarada que quedó sin integrar: solo monto el
> `QueryClientProvider` en `App.jsx`, sin usar `useQuery` ni `useMutation`. El
> fetching real es Axios con `useState` y `useEffect`.
>
> La preví para una migración posterior. Lo que ganaría es caché automática,
> deduplicación de peticiones y revalidación en foco, que hoy no tengo: si dos
> componentes piden la misma lista, se hacen dos peticiones.
>
> Lo documenté explícitamente en `frontend/src/README.md` y en el reporte técnico,
> justamente para que no se lea como que está en uso. En la limpieza reciente
> desinstalé las otras cuatro dependencias que estaban en la misma situación
> —`react-hook-form`, `@hookform/resolvers`, `zod` y `sonner`— porque no tenían un
> plan de migración detrás."

---

### 33. "¿Por qué normalizar países a ISO y no guardar lo que el usuario escribe?"

**Guión:**
> "Porque hay una regla de negocio que compara por país: una sola ficha vigente por
> material y país. Si guardara texto libre, 'Colombia', 'colombia' y 'CO' serían tres
> países distintos para el `WHERE`, y la regla se podría violar sin querer.
>
> `nombre_pais_a_iso` usa `pycountry`: si ya son dos letras alfabéticas busca directo
> por código; si no, usa `search_fuzzy`, que tolera errores de tipeo y nombres en
> varios idiomas. Siempre devuelve alpha-2.
>
> La decisión clave es **normalizar en la frontera de escritura, no en la lectura**.
> Guardo 'CO' en la base, así todas las comparaciones posteriores son exactas y no
> pago el costo de normalizar en cada consulta."

---

# BLOQUE C — Casos Límite y Errores

### 34. "¿Qué pasa si solo hay una ficha en el sistema y creo la segunda?"

**Guión:**
> "Los detectores estadísticos no se activan y esto es deliberado. `MIN_MUESTRAS_ESTADISTICAS`
> vale 3: con una sola ficha de referencia, `_detectar_valores_atipicos` retorna lista
> vacía tras loguear el motivo. Lo mismo el detector de unidades.
>
> El Isolation Forest tampoco: `MIN_MUESTRAS_ML` es 5, y además `modelo_disponible`
> devuelve `False` si no existe el `.pkl`.
>
> Lo que **sí funciona desde la primera ficha** son los rangos duros por categoría
> —conocimiento del dominio, no aprendido— y la detección de duplicados semánticos,
> que solo necesita que exista otro K-Item con embedding.
>
> Es degradación ordenada: sin datos suficientes, el sistema protege menos en vez de
> generar falsos positivos con estadísticas sin sentido."

---

### 35. "¿Qué pasa si la desviación estándar da cero?"

**Guión:**
> "Sería división por cero en `z_score = abs(valor - media) / std`. El código lo
> intercepta antes:
>
> `if std == 0:` — y ahí aplica una regla distinta. Si todas las fichas de referencia
> tienen exactamente el mismo valor y la actual difiere, genera una advertencia con el
> mensaje 'difiere del valor constante'. Si coincide, no hay anomalía y sigue con
> `continue`.
>
> Es un caso real, no teórico: pasa cuando un campo tiene un valor estándar en toda
> una categoría. Sin la guarda, el análisis de anomalías reventaría con
> `ZeroDivisionError` en producción."

---

### 36. "¿Qué pasa si falla la generación del embedding al pasar una ficha a Preliminar?"

**Guión:**
> "**La transición completa se revierte.** El bloque de enriquecimiento está dentro de
> un `try/except`. Si algo falla, capturo la excepción, la logueo con `exc_info=True` y
> lanzo un 500 con `from exc` para preservar la cadena de causa.
>
> Lo importante es que en ese punto **todavía no llamé a `commit()`**. La excepción
> propaga hasta FastAPI, la sesión se cierra sin confirmar y PostgreSQL hace rollback.
> La ficha se queda en Borrador.
>
> Es una decisión explícita de **consistencia sobre disponibilidad**: prefiero que el
> usuario reintente a que la ficha quede en Preliminar sin embedding y sin análisis de
> anomalías, porque entonces sería invisible para la búsqueda semántica y para todos
> los detectores que dependen de ella. Un estado silenciosamente corrupto es peor que
> un error visible.
>
> Nótese el contraste con `_modificar_ficha_editable`: ahí el análisis de anomalías
> falla en modo **degradado** —loguea y devuelve `_anomalias = []`— porque ya hubo
> commit y el dato del usuario está a salvo. La política cambia según lo que esté en
> riesgo."

---

### 37. "¿Qué pasa si dos usuarios publican simultáneamente dos fichas del mismo material y país?"

**Evalúa:** si entendés concurrencia. Es una pregunta trampa y la respuesta correcta es admitir el problema.

**Guión:**
> "Es una **condición de carrera real** y mi implementación actual no la previene por
> completo.
>
> El escenario: ambas transacciones ejecutan
> `_validar_unica_vigente_por_material_pais` antes de que ninguna haya confirmado.
> Ninguna ve a la otra —dependiendo del nivel de aislamiento— y ambas pasan. Resultado:
> dos fichas vigentes violando la regla.
>
> Hay tres formas de corregirlo, en orden de robustez. La mejor es un **índice único
> parcial en base**: `CREATE UNIQUE INDEX ON ficha_tecnica (id_material, pais) WHERE
> estado = 'Vigente'`. PostgreSQL rechazaría la segunda inserción sin importar el
> *timing*, porque la garantía la da el motor y no la aplicación. Segunda opción,
> bloqueo pesimista con `SELECT ... FOR UPDATE` sobre el material. Tercera, elevar el
> aislamiento a `SERIALIZABLE` y reintentar ante fallo de serialización.
>
> Recomendaría la primera: es declarativa, no tiene costo en el camino feliz e
> imposibilita el estado inválido por construcción. Mi validación de aplicación seguiría
> existiendo, pero para dar un mensaje de error claro, no como única garantía."

---

### 38. "¿Qué pasa si el servidor LDAP está caído?"

**Guión:**
> "El sistema sigue funcionando. `AuthService.login` implementa una cascada: el usuario
> `admin` **siempre** se autentica localmente, sin tocar LDAP —es la salida de
> emergencia para no quedar bloqueado si cae el directorio—. Para el resto, si
> `LDAP_HABILITADO` es verdadero intenta LDAP; si falla o no retorna éxito, cae a
> autenticación local.
>
> `LDAP_HABILITADO` se evalúa una sola vez al importar el módulo, como
> `bool(LDAP_SERVER and LDAP_BASE_DN)`. Si no hay configuración, ni siquiera intenta
> conectar.
>
> **Y tengo que ser transparente:** el fallback local usa un diccionario con contraseñas
> en texto plano en el código fuente. Es aceptable como mecanismo de demostración y
> desarrollo, pero en producción debe eliminarse o migrarse a hashes bcrypt en base de
> datos. Es la deuda técnica más importante que tiene el proyecto en seguridad."

---

### 39. "¿Qué pasa si un campo numérico llega como texto, por ejemplo '25 cm' en vez de 25?"

**Guión:**
> "Depende de por dónde entre, y hay una asimetría que reconozco.
>
> Por la API, los schemas Pydantic tipan los campos `*_valor` como numéricos: un string
> no convertible se rechaza con 422 antes de llegar al servicio. Esa es la barrera
> principal.
>
> En los detectores hay protecciones parciales. `_extraer_vector_numerico` valida
> explícitamente con `isinstance(valor, (int, float))` y descarta lo que no lo sea.
> `_detectar_rango_categoria` hace lo mismo.
>
> **Pero `_extraer_valores_campo`, que alimenta el z-score, no filtra por tipo.**
> Recolecta cualquier valor no nulo. Si un string llegara a la base sorteando Pydantic
> —por ejemplo por el script de importación desde Excel, que no pasa por los schemas—,
> el cálculo de la media lanzaría `TypeError` al sumar string con número.
>
> La corrección es una línea: agregar el filtro `isinstance` en ese método, igual que en
> los otros dos. Es la clase de inconsistencia que aparece cuando la validación vive en
> una capa y el consumo en otra."

---

### 40. "¿Qué pasa si intento crear una relación de un K-Item consigo mismo?"

**Guión:**
> "`KItemService.crear_relacion` lo bloquea con un 400. Valida en cuatro pasos y en
> este orden: que el tipo de relación esté en `RELACIONES_VALIDAS`; que existan ambos
> K-Items —usando `obtener_kitem`, que lanza 404 si no—; que `source_id != target_id`; y
> que no exista ya una relación idéntica.
>
> El orden importa: valido el tipo primero porque es O(1) en memoria, antes de gastar
> dos consultas a la base.
>
> El bucle sobre sí mismo se prohíbe porque no tiene semántica útil en este dominio:
> una ficha no 'pertenece a' sí misma ni 'se deriva de' sí misma. Además, en el
> recorrido del grafo generaría un ciclo trivial.
>
> La cuarta validación tiene además respaldo en base: `schema_clean.sql` define
> `UNIQUE (source_id, target_id, tipo_relacion)`. Ahí sí la garantía es del motor."

---

### 41. "¿Qué pasa si el archivo del modelo ML está corrupto?"

**Guión:**
> "Degradación silenciosa, por diseño. `_cargar_modelo` envuelve el `joblib.load` en
> `try/except`; ante cualquier excepción loguea una advertencia y devuelve `None`.
>
> Ese `None` sube hasta `predecir`, que retorna `None`, y `_detectar_ml_multivariado`
> devuelve lista vacía. **El análisis de anomalías continúa con los otros seis
> detectores.**
>
> La decisión de fondo: un modelo ML corrupto no debe impedir que se cree una ficha. Es
> un detector auxiliar, no una validación estructural. Perder capacidad de detección es
> aceptable; bloquear la operación del negocio no lo es.
>
> El contraste con la pregunta 36 es deliberado: ahí sí revierto, porque el embedding no
> es auxiliar —sin él la ficha queda invisible para la búsqueda y para varios
> detectores—.
>
> Y los modelos son regenerables: `POST /anomalias/entrenar` los reconstruye desde las
> fichas existentes. Por eso están en `.gitignore`."

---

### 42. "¿Qué pasa si el usuario marca todos los campos como 'No Corresponde'?"

**Guión:**
> "Los detectores numéricos quedan sin datos y no reportan nada, que es el
> comportamiento correcto.
>
> El mecanismo: por cada campo `X_valor` existe un `X_nc` booleano. En
> `_extraer_vector_numerico`, `_detectar_valores_atipicos`, `_detectar_unidades_inconsistentes`
> y en `_extraer_vector` del servicio ML, lo primero que se hace es
> `if datos.get(campo.removesuffix('_valor') + '_nc'): continue`.
>
> Si todos están marcados, el vector numérico sale vacío y `_detectar_perfil_numerico_cruzado`
> retorna temprano por `if not vector_ficha`.
>
> La razón de fondo: un campo no aplicable no es un dato faltante. Si contara los 'N/C'
> como ceros, contaminaría medias y desviaciones de toda la categoría y generaría falsas
> anomalías en fichas correctas. Distinguir 'no aplica' de 'no cargado' es una decisión
> de modelado de datos, no un detalle de implementación.
>
> Lo que sí seguiría activo: la validación de completitud al pasar a Preliminar, que exige
> características físicas y los cinco campos de manejo y disposición."

---

### 43. "¿Qué pasa si se elimina un K-Item que tiene auditoría y anomalías?"

**Guión:**
> "Comportamientos distintos y deliberados, definidos en las claves foráneas.
>
> `kitem_relacion` tiene `ON DELETE CASCADE` en ambos extremos: las aristas se borran,
> porque una relación sin sus dos nodos no significa nada.
>
> `anomalia_registro` también `CASCADE`: una anomalía describe un objeto; sin él, no
> tiene referente.
>
> `kitem_auditoria` tiene **`ON DELETE SET NULL`**, y esta es la diferencia importante.
> El registro de auditoría **sobrevive** con `kitem_id` nulo. Borrar la evidencia junto
> con el objeto anularía el propósito de auditar: quedaría constancia de que algo se
> creó, se modificó y se eliminó, y quién lo hizo.
>
> `material_comercial` y `ficha_tecnica` tienen `CASCADE` sobre `kitem.id`, lo cual es
> forzoso: comparten la clave primaria, no pueden existir sin su K-Item.
>
> Dicho esto, **no expuse endpoints de eliminación de K-Items**. El sistema archiva —
> estado Obsoleto— en vez de borrar. El `CASCADE` es una red de seguridad para
> operaciones administrativas directas sobre la base."

---

### 44. "¿Qué pasa si el token JWT expira mientras el usuario está trabajando?"

**Guión:**
> "Se maneja en dos capas.
>
> Backend: `verificar_token` captura `ExpiredSignatureError` y devuelve 401 con el
> mensaje 'Sesión expirada'. Lo distingue de `InvalidTokenError` —firma corrupta o
> manipulada—, que devuelve 'Token inválido'. Son situaciones distintas y el frontend
> podría tratarlas distinto.
>
> Frontend: el interceptor de respuesta en `lib/api.js` detecta cualquier 401, limpia
> `dsms_token` y `dsms_user` de `localStorage` y redirige a `/login`, con la guarda de no
> redirigir si ya estás ahí —evita un bucle—.
>
> Existe `POST /auth/refresh` para renovar el token antes de que expire, aunque el
> frontend no lo llama automáticamente todavía.
>
> **La consecuencia práctica que reconozco:** si el token vence mientras el usuario
> completa el formulario de una ficha, pierde lo cargado. La expiración es de 8 horas,
> configurable por `JWT_EXPIRATION_HOURS`, así que en una jornada normal no debería
> ocurrir. La mejora sería refrescar proactivamente cuando falte poco, o persistir el
> borrador en `localStorage`."

---

### 45. "¿Qué pasa si se crea una ficha sin código de material local?"

**Guión:**
> "Se permite, y es intencional. En `crear()`, `codigo_local` puede ser cadena vacía. En
> ese caso se usa el literal `'BORRADOR'` como etiqueta y `'XX'` si tampoco hay país, para
> generar un código provisional del tipo `FT-BORRADOR-XX-BOR-V1.0`.
>
> La validación de unicidad solo se ejecuta `if codigo_local:` — no valido unicidad de la
> nada.
>
> El razonamiento: un borrador es trabajo en curso. Obligar a tener todos los datos para
> guardar por primera vez forzaría al usuario a completar la ficha de una sentada o a
> inventar valores.
>
> **El cierre viene después:** `_validar_para_preliminar` exige código de material local,
> país, nombre local, características físicas y los cinco campos de manejo. Sin eso la
> ficha no sale de Borrador. Y al cambiar de estado el código se regenera con los valores
> reales.
>
> Es validación progresiva: permisiva para guardar, estricta para avanzar."

---

### 46. "¿Qué pasa si dos peticiones piden reindexación masiva al mismo tiempo?"

**Guión:**
> "No hay protección explícita, y el efecto es trabajo duplicado más presión de memoria.
>
> Ambas cargarían el conjunto de K-Items, generarían embeddings en lotes de 64 y
> escribirían. Como cada una tiene su propia sesión y transacción, la última en confirmar
> gana. El resultado final es correcto —el embedding de un texto dado es determinista, así
> que ambas calculan lo mismo— pero se gasta el doble de CPU y se cargan dos copias del
> modelo en memoria si el singleton no estaba inicializado.
>
> El riesgo real no es corrupción sino agotamiento de recursos: con muchos K-Items, dos
> reindexaciones concurrentes podrían tumbar el proceso.
>
> La corrección sería un *lock* de aplicación —`pg_advisory_lock` de PostgreSQL es ideal
> porque es transaccional y no requiere infraestructura extra— o encolar la operación en
> un worker dedicado. Para el uso real, que es una operación administrativa manual y
> esporádica, no lo consideré prioritario, pero es una carencia legítima."

---

### 47. "¿Qué pasa si la búsqueda semántica no encuentra nada por encima del umbral?"

**Guión:**
> "Devuelve lista vacía, sin error. `buscar_por_texto` trae los k más cercanos por
> `ORDER BY distancia ASC LIMIT`, y **después** filtra en Python por
> `similitud >= umbral_similitud`. Si ninguno pasa, la lista queda vacía.
>
> El orden importa y es una decisión consciente. Filtrar por umbral en SQL impediría usar
> el índice HNSW, que está optimizado para 'los k más cercanos', no para 'todos los que
> superan un valor'. Prefiero traer k candidatos usando el índice y descartar en memoria.
>
> El costo: si pido 10 y solo 3 superan el umbral, devuelvo 3, no busco más profundo. Es
> aceptable para el caso de uso.
>
> En los detectores, una lista vacía significa simplemente que no hay anomalía de ese
> tipo. En la interfaz, el usuario ve un mensaje de sin resultados. En ningún punto se
> trata como error, porque no lo es: que nada se parezca a la consulta es información
> válida."

---

### 48. "¿Qué pasa si el JSONB de una sección viene con una estructura inesperada?"

**Guión:**
> "Los detectores lo toleran; la base no lo valida.
>
> `_extraer_valores_campo` verifica `if datos and isinstance(datos, dict)` antes de
> acceder. Si el JSONB fuera una lista o un escalar, lo salta sin romper. Los accesos a
> campos usan `.get()`, que devuelve `None` en vez de lanzar `KeyError`. Y las secciones
> se inicializan con `or {}` en varios puntos, así que un `NULL` se trata como diccionario
> vacío.
>
> **Lo que reconozco es que PostgreSQL no valida la forma del JSONB.** Ese es el costo
> que acepté a cambio de esquema flexible: la validación vive en los schemas Pydantic en
> la frontera de entrada, no en la capa de datos.
>
> El hueco concreto: datos que entren sin pasar por la API —el script de importación desde
> Excel, o SQL directo— no atraviesan esa validación. La mitigación sería una constraint
> `CHECK` con `jsonb_typeof(caracteristicas) = 'object'`, o validar dentro del script de
> importación reutilizando los mismos schemas."

---

# BLOQUE D — Preguntas Difíciles

> Estas apuntan a debilidades reales. **La estrategia correcta es reconocerlas de
> inmediato y demostrar que entendés la solución.** Un jurado experimentado ya las vio;
> intentar esquivarlas es el peor movimiento posible.

### 49. "¿Cómo protege sus endpoints? ¿Puede alguien publicar una ficha sin autenticarse?"

**Evalúa:** si la seguridad es declarativa y verificable o depende de recordar aplicarla.

**Guión:**
> "No. Los 45 endpoints de datos exigen un JWT válido. La única ruta pública es
> `POST /auth/login`, que por definición no puede exigir el token que ella misma emite.
>
> El mecanismo es declarativo, a nivel de router:
> `APIRouter(prefix='/ficha', dependencies=[Depends(get_usuario_actual)])`. Eso aplica la
> validación a todos los endpoints de ese router. Preferí esto a decorar handler por
> handler precisamente porque lo segundo depende de que nadie se olvide; con la
> dependencia en el router, un endpoint nuevo nace protegido.
>
> Hay un segundo problema que resolví junto con este, y que era más sutil: **de dónde
> sale la identidad que se registra en la auditoría.** Antes venía del cuerpo de la
> petición —el cliente mandaba `usuario: 'marco.agrusa'`— y en las transiciones de estado
> estaba directamente hardcodeada como `'sistema'`. Un campo enviado por el cliente es una
> afirmación, no una prueba: cualquiera podía atribuirse acciones a nombre de otro y
> corromper justamente lo que el sistema promete.
>
> Ahora la identidad se extrae del token firmado con la dependencia `get_usuario_nombre`,
> y en los endpoints de creación el router sobrescribe el campo del cuerpo antes de llamar
> al servicio. Los schemas siguen aceptando esos campos como opcionales por compatibilidad,
> pero se descartan.
>
> **Y no es una afirmación que les pido que me crean:** hay un test que recorre el esquema
> OpenAPI real de la aplicación y exige 401 en todo endpoint que no esté en la lista de
> públicos. Si mañana agrego un router y me olvido de la dependencia, la suite falla. Lo
> verifiqué quitando la protección de un router a propósito: el test la detectó.
> Hay además tests que envían `usuario_creador: 'atacante.suplantador'` con el token de
> otro usuario y comprueban que prevalece el del token."

---

### 50. "Encontré una validación que no valida nada. Explíquela."

**Guión:**
> "Se refiere a `_validar_contenido_por_tipo`. Tiene razón: calcula `tiene_algun_valor`
> recorriendo los campos que terminan en `_valor`, y luego hace `if not tiene_algun_valor:
> return` — pero si hay valores, cae al final de la función y retorna igual. **Es código
> muerto.** La rama que debía validar quedó vacía.
>
> El origen: iba a validar que el tipo de contenido declarado fuera coherente con los
> campos cargados, usando la constante `TIPOS_CONTENIDO` de `dsms_constants.py`. La
> estructura quedó, la regla nunca se escribió.
>
> El impacto es acotado: se invoca en `crear` y en ambas ramas de `actualizar`, así que
> hoy son tres llamadas sin efecto. No causa comportamiento incorrecto, pero da la falsa
> impresión de que existe una validación que no existe, que es peor que no tenerla.
>
> Lo correcto es implementarla o eliminarla. Eliminarla es la opción honesta si no voy a
> escribir la regla ahora."

---

### 51. "¿Cómo sabe que sus detectores no generan falsos positivos masivos?"

**Evalúa:** rigor metodológico. Es la pregunta más difícil de todas.

**Guión:**
> "Con honestidad: **no tengo una medición formal de precisión y recall**, y no puedo
> tenerla, porque eso requiere un conjunto de fichas etiquetadas por un experto como
> correctas o incorrectas, que no existe.
>
> Lo que sí tengo son tres mitigaciones de diseño.
>
> **Umbrales conservadores con base estadística.** El z-score de 2σ deja fuera el 95.4%
> de una distribución normal; el de 3σ, el 99.7%. No son números arbitrarios.
>
> **Guardas de muestra mínima.** Ningún detector estadístico opera con menos de 3
> muestras, y el ML con menos de 5. Esto elimina la fuente más común de falsos positivos:
> estadísticas calculadas sobre datos insuficientes.
>
> **Severidad graduada con veto solo donde importa.** No todo bloquea igual. Y las
> anomalías no se descartan: se resuelven explícitamente con estado `aceptada`,
> `descartada` o `corregida`, quedando quién y por qué en `resuelto_por` y
> `nota_resolucion`.
>
> **Y ahí está el camino de validación que el diseño ya habilita:** la tabla
> `anomalia_registro` acumula el histórico de resoluciones. Una anomalía marcada como
> `descartada` es, por definición, un falso positivo etiquetado por un humano. Con
> suficiente volumen puedo calcular la tasa de falsos positivos **por tipo de detector** y
> recalibrar los umbrales con datos reales en vez de con teoría. Ese es el trabajo futuro
> más valioso del proyecto, y la razón por la que persisto las resoluciones en vez de solo
> borrar la anomalía."

---

### 52. "Sus tests no tocan la base de datos. ¿Realmente prueban algo?"

**Guión:**
> "Prueban la lógica de negocio, que es donde está el riesgo real de este sistema, y no
> prueban la integración, que es una brecha que reconozco.
>
> Lo que cubren los 111 tests: la máquina de estados completa, incluyendo transiciones
> inválidas; las validaciones de completitud por estado; la generación e incremento de
> códigos y versiones; los detectores de anomalías con sus casos límite —desviación cero,
> muestras insuficientes, campos N/C—; y la orquestación de `cambiar_estado` y `actualizar`
> contra una `FakeSession`, que valida el *branching*: que una ficha Vigente genere versión
> nueva, que una anomalía pendiente bloquee, que la original se marque Obsoleto.
>
> Lo que no cubren: que el SQL generado sea correcto, que los JOIN a `kitem` devuelvan lo
> esperado, que pgvector ordene bien, que las constraints se disparen.
>
> El beneficio de la decisión es concreto: corren en 16 segundos en cualquier máquina sin
> infraestructura, y cuando fallan es por lógica rota, no por una base caída. Eso los hace
> ejecutables en cada cambio.
>
> El siguiente paso natural es una capa de tests de integración con `testcontainers`
> levantando PostgreSQL con pgvector en Docker. Sería lenta, se ejecutaría en CI y no en
> cada guardado, y cubriría exactamente lo que hoy falta."

---

### 53. "Si el sistema crece a 100.000 fichas, ¿qué se rompe primero?"

**Guión:**
> "Tengo identificados cuatro puntos, y los ordeno por cuándo aparecerían.
>
> **Primero, `_calcular_perfiles_categorias`.** Carga todas las fichas con su material en
> cada análisis de anomalías para recalcular centroides. Es O(n) por análisis. Con 100.000
> fichas, crear una sola haría un escaneo completo. Es el cuello de botella más urgente y
> la solución es cachear los centroides, invalidándolos cuando se publica una ficha —el
> mismo evento que ya dispara el reentrenamiento ML—.
>
> **Segundo, `listar()` sin paginación.** `SELECT * FROM ficha_tecnica` sin `LIMIT` traería
> 100.000 filas con sus JSONB a memoria y las serializaría a JSON. Solución directa:
> `limit`/`offset`, o paginación por cursor, que es más eficiente en tablas grandes.
>
> **Tercero, el N+1 en detección de duplicados.** Por cada K-Item similar hago una consulta
> adicional para obtener su ficha. Con límite de 10, son 10 consultas extra por análisis;
> molesto pero acotado. Se resuelve con un JOIN.
>
> **Cuarto, el reentrenamiento del Isolation Forest.** Es O(n log n) sobre todas las fichas.
> Con 100.000 dejaría de ser viable en background y habría que moverlo a un job programado
> nocturno, o entrenar sobre una muestra estratificada.
>
> Lo que **sí escala**: la búsqueda semántica, gracias al índice HNSW con O(log n), que es
> precisamente la operación que uno esperaría que fuera el problema."

---

### 54. "Guarda el JWT en localStorage. ¿No sabe que es vulnerable a XSS?"

**Guión:**
> "Lo sé, y es un intercambio consciente, no un descuido.
>
> El riesgo concreto: si un atacante logra ejecutar JavaScript en la página, puede leer
> `localStorage` y exfiltrar el token. Una cookie `HttpOnly` sería inaccesible desde
> JavaScript y eliminaría ese vector.
>
> Por qué no lo hice: `HttpOnly` implica que el frontend no puede leer el token, así que la
> gestión de sesión pasa enteramente al servidor —endpoint de logout que invalide, manejo de
> `SameSite`, y protección CSRF, porque las cookies se envían automáticamente y eso reabre
> un vector distinto—. Es la opción correcta para producción, pero es más superficie de
> implementación.
>
> Y quiero ser preciso sobre la magnitud del riesgo: **si hay XSS, el atacante ya puede
> hacer peticiones autenticadas desde la sesión de la víctima**, tenga o no acceso al token.
> `HttpOnly` limita la exfiltración —que el token se use fuera del navegador comprometido—,
> que es peor, pero no salva de un XSS.
>
> La defensa real contra XSS es no tenerlo: React escapa por defecto todo lo que se
> renderiza, y en este código no hay ningún `dangerouslySetInnerHTML`. Eso es lo que
> verifiqué."

---

### 55. "Su sistema depende de un modelo de embeddings que no entrenó. ¿Qué aporta usted?"

**Evalúa:** si distinguís entre usar una herramienta y diseñar un sistema.

**Guión:**
> "Es correcto: `all-MiniLM-L6-v2` es un modelo preentrenado, y entrenar uno propio no
> tendría sentido —requiere corpus masivos y no mejoraría nada aquí—.
>
> Mi aporte está en cinco decisiones de ingeniería alrededor de él.
>
> **Qué texto se le da.** `construir_texto_embedding` no le pasa el nombre a secas: compone
> tipo, nombre, descripción y campos contextuales seleccionados, convierte guiones bajos en
> espacios porque el modelo fue entrenado con lenguaje natural, e incluye el `ktype` para que
> el vector codifique de qué clase de objeto se trata. La calidad del embedding depende
> directamente de eso.
>
> **Cuándo se genera.** Al crear la ficha hay pocos datos, así que el embedding inicial es
> pobre. Al pasar a Preliminar reescribo nombre y descripción del K-Item con información
> rica —material, categoría, contenido, dimensiones— y regenero el vector. Es una decisión
> de diseño de flujo, no del modelo.
>
> **Dónde se almacena.** En `KItem`, no en las extensiones. Eso es lo que hace que la
> búsqueda semántica funcione sobre cualquier tipo de entidad con una sola query.
>
> **Cómo se interpreta.** El modelo devuelve un número de similitud. Que 0.95 signifique
> 'posible duplicado' para fichas pero 0.90 para materiales, y que 0.85 dispare una revisión
> de clasificación, son umbrales que calibré para este dominio. El modelo no sabe nada de
> fichas técnicas.
>
> **Cómo se combina.** El duplicado semántico solo alerta si los materiales son distintos;
> la clasificación cruzada sube a crítica solo si además hay evidencia dimensional
> independiente. Eso es lógica de dominio construida sobre la salida del modelo.
>
> El modelo es un componente. El sistema es la arquitectura que lo hace útil para un
> problema concreto."

---

### 56. "Encontré un campo que siempre sale nulo en el grafo. ¿Sabe cuál?"

**Guión:**
> "Sí: `metadata_relacion` en `obtener_grafo_kitem`.
>
> El bug es un nombre de parámetro desalineado. En `KItemService.obtener_grafo_kitem`
> construyo el schema pasando `metadata=rel.metadata`. Hay dos errores encadenados. Primero,
> el atributo del modelo se llama `metadata_relacion`, no `metadata` —`metadata` en un modelo
> declarativo de SQLAlchemy es el objeto `MetaData` de la tabla, algo completamente
> distinto—. Segundo, el schema `KItemRelacionDetalleSchema` declara el campo como
> `metadata_relacion`.
>
> Como Pydantic v2 ignora por defecto los argumentos extra, no lanza error: descarta
> `metadata=` y deja `metadata_relacion` con su valor por defecto, `None`. **Falla en
> silencio**, que es la peor clase de fallo.
>
> El efecto: cualquier dato guardado en `metadata_relacion` —contexto, peso, prioridad de
> una relación— es invisible en el endpoint del grafo. La corrección es cambiar el
> argumento a `metadata_relacion=rel.metadata_relacion`.
>
> Y la lección más general: configurar Pydantic con `extra='forbid'` habría convertido este
> fallo silencioso en un error explícito la primera vez que se ejecutó."

---

# BLOQUE E — Cierre

### 57. "En una frase, ¿cuál es la contribución de su trabajo?"

**Guión:**
> "Un sistema de gestión de conocimiento donde la calidad del dato no depende de la
> disciplina del usuario: el modelo K-Item permite que búsqueda semántica, grafo de
> relaciones y auditoría operen sobre cualquier tipo de entidad sin código específico, y
> siete detectores complementarios validan la plausibilidad de cada ficha con poder de veto
> sobre el flujo de aprobación."

---

### 58. "¿Qué haría distinto si empezara de nuevo?"

**Guión:**
> "Tres cosas concretas.
>
> **Aplicaría autenticación desde el primer endpoint.** Agregarla al final fue más
> trabajo y había dejado huecos: el usuario hardcodeado como 'sistema' en las
> transiciones, y la identidad leída del cuerpo de la petición en el resto. Con
> `dependencies=[Depends(...)]` a nivel de router desde el inicio, el costo habría sido
> nulo. Lo corregí, pero tuve que tocar nueve routers, seis schemas y cinco páginas del
> frontend en lugar de escribir una línea por router desde el principio.
>
> **Escribiría las constraints de base junto con las validaciones de servicio.** El caso de
> la ficha única vigente muestra que una regla de negocio sin respaldo en el motor es
> falsificable bajo concurrencia.
>
> **Levantaría la capa de integración antes.** Los tests de lógica pura fueron la decisión
> correcta para iterar rápido, pero postergarlos indefinidamente dejó sin verificar que las
> queries con JOIN a `kitem` —que son casi todas, por el patrón de propiedades proxy— hagan
> lo que creo.
>
> Lo que **no** cambiaría: el patrón K-Item y las reglas de negocio como datos. Son las dos
> decisiones que hicieron que agregar funcionalidad fuera barato durante todo el proyecto."

---

### 59. "¿Cuál es el siguiente paso si esto se llevara a producción?"

**Guión:**
> "Por prioridad, en tres bloques.
>
> **Bloqueantes de seguridad, antes de exponerlo:** eliminar el diccionario de usuarios
> locales con contraseñas en claro —y el recuadro del login que las muestra en pantalla—;
> hacer que el arranque falle si `JWT_SECRET` no está definida, en vez de usar el valor
> por defecto; pasar `echo=False` en el motor de base para no filtrar datos en los logs; y
> agregar el middleware CORS con orígenes explícitos.
>
> La autenticación de los endpoints y la trazabilidad del usuario ya están resueltas y
> cubiertas por tests.
>
> **Robustez de datos:** el índice único parcial para ficha vigente, paginación en los
> listados, y la caché de centroides.
>
> **Operación:** tests de integración con `testcontainers`, y mover el rate limiter a Redis
> para que funcione con múltiples workers.
>
> El primer bloque es de días. Los otros dos son mejoras incrementales que no bloquean un
> piloto controlado."

---

### 60. "¿Por qué debería confiar en un sistema que detecta anomalías con probabilidades?"

**Evalúa:** si entendés los límites de tu propia herramienta.

**Guión:**
> "Porque el sistema no decide: **asiste a quien decide**.
>
> Ninguna anomalía modifica un dato ni rechaza una ficha automáticamente. Lo que hace es
> impedir que avance en el flujo hasta que **una persona** la resuelva explícitamente, con
> tres opciones: aceptarla —el dato es raro pero correcto—, descartarla —es un falso
> positivo— o corregirla. Quién resolvió, cuándo y con qué justificación queda en
> `resuelto_por`, `fecha_resolucion` y `nota_resolucion`.
>
> Y cada anomalía viene con su evidencia en el campo `detalles`: media, desviación, z-score,
> número de muestras, rango esperado. El usuario no recibe un veredicto opaco; recibe el
> cálculo para poder discrepar con fundamento.
>
> La comparación correcta no es contra un sistema perfecto: es contra el estado previo, que
> era revisión manual sin comparación sistemática contra el histórico. Un detector con
> falsos positivos que un humano descarta en segundos es estrictamente mejor que no detectar
> nada.
>
> Y como esas resoluciones se persisten, el sistema acumula el insumo para medir su propia
> tasa de error por detector y recalibrarse. Está diseñado para ser corregible, que es la
> propiedad que uno debe exigirle a un sistema probabilístico."

---

## Checklist final antes de la defensa

**Debés poder hacer esto sin dudar:**

- [ ] Dibujar el diagrama de clases en un pizarrón (ver [diagrama-clases.md](diagrama-clases.md))
- [ ] Escribir de memoria `TRANSACCIONES_PERMITIDAS` completo
- [ ] Explicar por qué `estado_ficha` no funciona en un `WHERE`
- [ ] Nombrar los 7 detectores y qué error detecta cada uno
- [ ] Explicar la diferencia entre `flush()` y `commit()` y por qué importa
- [ ] Recorrer el flujo completo de `POST /ficha` nombrando cada capa
- [ ] Enumerar 5 debilidades del proyecto con su corrección

**Las tres frases que deberías decir en algún momento:**

1. *"Separé las reglas de negocio de la lógica que las aplica: las transiciones son un diccionario, no condicionales."*
2. *"Una ficha publicada no se edita, se versiona: el sistema implementa inmutabilidad de documentos con trazabilidad de linaje."*
3. *"Los siete detectores degradan ordenadamente según cuántos datos históricos existan: con pocos datos protegen menos, pero nunca fallan."*

**Y una advertencia:** si el jurado encuentra una debilidad que vos no mencionaste,
perdés más que si la hubieras traído vos. La mayor que queda abierta son las
**credenciales en texto plano** en `auth_service.py`, visibles además en el recuadro
de ayuda del login. Mencionala proactivamente al hablar de trabajo futuro: convertís
una vulnerabilidad de la defensa en evidencia de criterio técnico.

**Un punto fuerte que sí conviene traer solo:** la autenticación y la trazabilidad del
usuario estaban rotas y las corregiste, con tests que recorren el esquema OpenAPI para
que no vuelvan a romperse. Contar el problema, la corrección y cómo la verificaste
demuestra más criterio que no haber tenido el problema nunca.
