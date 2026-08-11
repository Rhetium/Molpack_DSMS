# Guía Técnica del Código — Molpack DSMS

> Documento de estudio para la defensa del proyecto.
> Cada módulo se explica en tres niveles: **qué hace** (intuitivo), **cómo lo hace**
> (línea por línea) y **por qué se decidió así** (justificación técnica).

---

## 0. Mapa mental: el sistema en un párrafo

Molpack DSMS es un sistema de gestión de conocimiento para fichas técnicas de
envases y embalajes. Su idea central es que **todo objeto del dominio es la misma
cosa por debajo**: un *K-Item*. Un material comercial es un K-Item. Una ficha
técnica es un K-Item. Cada K-Item tiene metadata común, un contenedor de datos
específico y un vector de 384 dimensiones que representa su significado. Sobre esa
base se construyen cuatro capacidades: un **flujo de estados** que gobierna el ciclo
de vida de las fichas, una **búsqueda semántica** que encuentra por significado y no
por palabra exacta, un **motor de anomalías** de 7 detectores que valida la calidad
de los datos, y una **auditoría** que registra absolutamente todo.

**La frase para el jurado:** *"No modelé materiales y fichas como tablas
independientes. Modelé un supertipo universal —el K-Item— y las entidades concretas
como extensiones suyas. Eso me permite que la búsqueda semántica, el grafo de
relaciones y la auditoría funcionen sobre cualquier tipo de entidad sin escribir
código nuevo para cada una."*

---

## 1. Arquitectura general

### 1.1 Propósito en lenguaje simple

El backend está dividido en capas donde cada una tiene un único trabajo. Una
petición HTTP entra por el **router**, que solo sabe de URLs y códigos de estado.
El router llama a un **servicio**, que es donde vive toda la lógica de negocio. El
servicio manipula **modelos** (objetos Python que representan filas de la base de
datos) y devuelve datos que se convierten en JSON mediante **schemas**.

### 1.2 Flujo completo de una petición

Tomemos `POST /ficha` (crear una ficha técnica):

```
Navegador
  │  axios.post('/api/ficha', datos)     ← frontend/lib/api.js
  │  interceptor agrega: Authorization: Bearer <jwt>
  ▼
Vite dev server  (proxy /api → http://127.0.0.1:8000)
  ▼
FastAPI router   app/routers/ficha.py:39
  │  Pydantic valida el body contra FichaTecnicaCreateSchema
  │  Depends(get_session) abre una sesión async de SQLAlchemy
  │  Depends(get_ficha_service) construye FichaService(session)
  ▼
FichaService.crear()   app/services/fichas_services.py:291
  │  1. valida que el material exista y no esté inactivo
  │  2. normaliza el país a ISO-3166 alpha-2
  │  3. valida unicidad de código local
  │  4. genera el código de ficha
  │  5. crea el KItem base  → KItemService
  │  6. crea la fila FichaTecnica
  │  7. crea la relación pertenece_a → KItemService
  │  8. genera el embedding → BusquedaSemanticaService → EmbeddingService
  │  9. registra auditoría (dentro de cada servicio)
  │ 10. COMMIT único de toda la transacción
  ▼
Respuesta: FichaTecnicaSchema serializado a JSON
```

### 1.3 Justificación técnica: ¿por qué capas?

**El problema que resuelve:** si la lógica de negocio vive en el router, queda
atada a HTTP. No se puede reutilizar desde un script de importación masiva, ni
testear sin levantar un servidor.

**La prueba de que funciona en este proyecto:** el script
[scripts/seed_fichas_excel.py](../scripts/seed_fichas_excel.py) importa fichas
desde Excel llamando directamente a `FichaService.crear()`. Obtiene gratis las
validaciones, la auditoría y los embeddings, sin pasar por HTTP. Y los 111 tests
de `tests/` ejercitan los servicios sin levantar FastAPI ni PostgreSQL.

**Alternativa descartada:** el patrón *Repository* (una capa extra entre servicio y
ORM). Se descartó porque SQLAlchemy **ya es** una capa de abstracción sobre SQL;
agregar otra habría sido una indirección sin beneficio a esta escala.

---

## 2. Capa de configuración — `app/core/`

### 2.1 `database.py` — motor de conexión

**Propósito:** abre el canal hacia PostgreSQL y define la clase base de la que
heredan todos los modelos.

**Desglose:**

```python
DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()
```

- `postgresql+asyncpg` selecciona **asyncpg** como driver, no `psycopg2`. Es el
  driver asíncrono nativo: no bloquea el *event loop* mientras espera respuesta de
  la base.
- `expire_on_commit=False` es la línea sutil e importante. Por defecto SQLAlchemy
  marca todos los objetos como "expirados" tras un commit, y el siguiente acceso a
  un atributo dispara un `SELECT` nuevo. En código asíncrono ese refresco implícito
  provoca el error `MissingGreenlet`. Al desactivarlo, después de
  `await session.commit()` los objetos siguen usables para construir la respuesta.
- `Base = declarative_base()` es la clase raíz del ORM: recolecta los metadatos de
  todas las tablas declaradas.

**Justificación:** todo el stack es asíncrono (FastAPI → SQLAlchemy 2.0 async →
asyncpg) porque el sistema hace operaciones de I/O de latencia alta y variable
(consultas vectoriales, LDAP, lectura de modelos ML). Con un modelo síncrono cada
petición ocuparía un hilo completo mientras espera.

> ⚠️ **Debilidad conocida — prepárate para esta pregunta.** `echo=True` imprime
> **todo el SQL ejecutado, incluidos los valores**. En producción esto llena los
> logs y filtra datos. La respuesta correcta: *"Es configuración de desarrollo para
> poder auditar las consultas que genera el ORM; en producción debe pasarse a
> `echo=False`, idealmente leyendo la variable de entorno `DEBUG`."*

### 2.2 `deps.py` — inyección de dependencias

```python
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
```

**Qué hace:** son 3 líneas que resuelven el ciclo de vida de la conexión. FastAPI
ejecuta el código hasta el `yield`, entrega la sesión al endpoint, y cuando la
respuesta termina retoma después del `yield` para que `async with` cierre la sesión.

**Por qué importa:** garantiza que **una petición = una sesión = una transacción**.
Aunque `FichaService` cree internamente cuatro servicios más, todos comparten la
misma `AsyncSession`. Por eso el `commit()` final es atómico sobre todo el trabajo.

### 2.3 `security.py` — JWT y rate limiting

**Firma del token:**

```python
payload = {**datos, "exp": ahora + timedelta(hours=8), "iat": ahora}
return jwt.encode(payload, JWT_SECRET, algorithm="HS256")
```

HS256 es HMAC-SHA256: firma **simétrica**, la misma clave firma y verifica. Es la
elección correcta cuando emisor y validador son el mismo servicio. RS256
(asimétrica) tendría sentido si un servicio externo tuviera que validar tokens sin
poder emitirlos.

`verificar_token` distingue dos fallos: `ExpiredSignatureError` (token válido pero
vencido) e `InvalidTokenError` (firma corrupta o manipulada). Ambos devuelven 401
pero con mensajes distintos, lo que permite al frontend reaccionar diferente.

**El `RateLimiter`** protege el login contra fuerza bruta con dos diccionarios:

```python
self.intentos: dict[str, list[tuple[float, bool]]]  # ip → [(timestamp, exitoso)]
self.bloqueados: dict[str, float]                   # ip → timestamp de desbloqueo
```

El algoritmo es una **ventana deslizante**: en cada intento fallido se agrega el
timestamp y luego se filtra la lista descartando los intentos más viejos que
`ventana_segundos` (60s). Si sobreviven 5 o más, la IP se bloquea 300 segundos.

```python
self.intentos[ip] = [(t, e) for t, e in self.intentos[ip]
                     if ahora - t < self.ventana_segundos]
```

**Justificación de la ventana deslizante frente a un contador simple:** un contador
que solo se resetea al éxito bloquearía a un usuario legítimo que se equivocó 5
veces a lo largo de un mes. La ventana exige que los 5 fallos ocurran en 60
segundos, que es el patrón de un ataque automatizado, no de un humano distraído.

> ⚠️ **Limitación:** el estado vive en memoria del proceso. Se pierde al reiniciar y
> no se comparte entre workers de Uvicorn. La respuesta honesta: *"Para un
> despliegue multi-worker habría que mover el contador a Redis con TTL nativo. Para
> el alcance actual —una instancia— es suficiente y evita una dependencia extra."*

### 2.4 `utils.py` — normalización de países

```python
def nombre_pais_a_iso(nombre_pais: str) -> str:
    valor = (nombre_pais or "").strip()
    if len(valor) == 2 and valor.isalpha():
        pais = pycountry.countries.get(alpha_2=valor.upper())
        if pais: return pais.alpha_2
    try:
        return pycountry.countries.search_fuzzy(valor)[0].alpha_2
    except LookupError:
        raise HTTPException(400, f"Nombre de país inválido: {nombre_pais}")
```

**Qué resuelve:** el usuario puede escribir "Colombia", "colombia", "CO" o
"Republic of Colombia". Sin normalizar, la regla *"una sola ficha vigente por
material y país"* fallaría: "Colombia" y "CO" serían países distintos para el
`WHERE`.

**Cómo:** primero intenta la vía rápida (si ya son 2 letras alfabéticas, busca
directo por código ISO). Si no, usa `search_fuzzy`, que tolera errores de tipeo y
nombres en varios idiomas. El resultado siempre es el mismo formato canónico:
alpha-2.

**Justificación:** es una **función pura** —entrada texto, salida texto, sin efectos
de lado— por eso se testea trivialmente en `tests/test_utils_pais.py`. La decisión
clave es normalizar en la **frontera de escritura**, no en la lectura: se guarda
`"CO"` en la base, así todas las comparaciones posteriores son exactas.

### 2.5 `dsms_constants.py` — las reglas de negocio como datos

```python
TRANSACCIONES_PERMITIDAS = {
    ESTADO_BORRADOR:   {ESTADO_PRELIMINAR, ESTADO_OBSOLETO},
    ESTADO_PRELIMINAR: {ESTADO_VIGENTE, ESTADO_OBSOLETO},
    ESTADO_VIGENTE:    {ESTADO_OBSOLETO},
    ESTADO_OBSOLETO:   {ESTADO_REVISION},
    ESTADO_REVISION:   {ESTADO_OBSOLETO, ESTADO_PRELIMINAR},
}
```

**Esta es la decisión de diseño más defendible del proyecto.** La máquina de
estados no está escrita como una cadena de `if/elif` repartida por el código: es
un **diccionario de conjuntos**, es decir, la lista de adyacencia de un grafo
dirigido.

Las consecuencias prácticas:

| Propiedad | Efecto |
|---|---|
| Validar una transición | `nuevo in TRANSACCIONES_PERMITIDAS[actual]` → **O(1)** por hash |
| Agregar un estado | Se edita el diccionario; **cero cambios en la lógica** |
| Auditar las reglas | Se leen 7 líneas, no se rastrean condicionales |
| Testear | Se recorre el diccionario y se verifica cada arista |

**El argumento fuerte:** *"Separé las reglas (datos) del motor que las aplica
(código). Es el mismo principio por el que un intérprete de expresiones regulares
no tiene el patrón hardcodeado."*

### 2.6 `anomalia_constant.py` — umbrales calibrados

Aquí viven todos los números mágicos del motor de anomalías, con nombre y
justificación:

| Constante | Valor | Fundamento |
|---|---|---|
| `ZSCORE_ADVERTENCIA` | 2.0 | En una normal, ±2σ cubre el 95.4%. Fuera de ahí → 1 de cada 22 casos |
| `ZSCORE_CRITICO` | 3.0 | ±3σ cubre el 99.7%. Fuera → 1 de cada 370 |
| `MIN_MUESTRAS_ESTADISTICAS` | 3 | Con menos, media y desviación no tienen sentido |
| `MIN_MUESTRAS_ML` | 5 | Mínimo para entrenar un Isolation Forest por categoría |
| `UMBRAL_DUPLICADO_FICHA` | 0.95 | Fichas del mismo dominio comparten vocabulario: umbral alto |
| `UMBRAL_DUPLICADO_SEMANTICO` | 0.90 | Materiales tienen texto más corto y diverso |
| `UMBRAL_CLASIFICACION_CRUZADA` | 0.85 | Más permisivo: sugerir, no bloquear |
| `PORCENTAJE_UNIDAD_MAYORITARIA` | 0.70 | Se exige consenso claro antes de alertar |

**Por qué están centralizados:** calibrar un detector es un proceso empírico. Si
los umbrales estuvieran dispersos en el código, ajustarlos exigiría tocar la
lógica y arriesgar regresiones. Aquí se cambia un número y todo el sistema lo
respeta. `tests/test_anomalia_constant.py` verifica las invariantes (por ejemplo,
que el umbral crítico sea siempre mayor que el de advertencia).

---

## 3. Capa de modelos — el patrón K-Item

### 3.1 El concepto

**Propósito en lenguaje simple:** en lugar de tratar materiales y fichas como cosas
sin relación, el sistema dice: *"ambos son objetos de conocimiento"*. Lo que
comparten (nombre, estado, quién lo creó, cuándo, y su representación semántica)
vive en una tabla común: `kitem`. Lo que es específico vive en tablas de extensión.

Esto viene del paper DSMS de Nahshon et al. (2023), citado en el docstring de
[app/models/kitem.py](../app/models/kitem.py):

```
K-Item = Metadata + Data Container + Semantic Graph
```

| Componente | Dónde vive en este proyecto |
|---|---|
| Metadata | Tabla `kitem` (id, ktype, nombre, estado, usuarios, fechas) |
| Data Container | Tablas de extensión + columnas JSONB |
| Semantic Graph | Tabla `kitem_relacion` + columna `embedding` |

### 3.2 `KItem` — el supertipo

```python
class KItem(Base):
    __tablename__ = "kitem"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ktype = Column(Text, nullable=False, index=True)
    embedding = Column(Vector(384), nullable=True)
    ...
```

**Decisiones y sus razones:**

- **UUID en lugar de entero autoincremental.** Un UUID puede generarse en el
  cliente antes de tocar la base; no revela cuántos registros hay (un `id=47`
  filtra información de negocio); y no colisiona si en el futuro se fusionan bases
  de distintas plantas. El costo es 16 bytes en vez de 4 y peor localidad de índice.
- **`ktype` como texto indexado, no como FK a una tabla de tipos.** Es el
  discriminador. Agregar el tipo `Norma` no requiere migración: se inserta con otro
  `ktype`. La contrapartida —que la base no valida el valor— se compensa con las
  constantes `KTYPE_*`.
- **`embedding` en la tabla base, no en las extensiones.** Esta es la decisión que
  hace que todo el sistema semántico sea genérico: `buscar_por_texto` consulta
  `KItem.embedding` y encuentra materiales y fichas **con la misma query**.
- **`metadata_extra` como JSONB.** Escape hatch para datos que no justifican una
  columna. PostgreSQL indexa JSONB con GIN, así que sigue siendo consultable.

### 3.3 Las extensiones y el patrón *proxy*

`FichaTecnica` y `MaterialComercial` usan **PK compartida**: su clave primaria es
además una FK hacia `kitem.id`.

```python
class FichaTecnica(Base):
    id_ficha = Column(UUID, ForeignKey("kitem.id", ondelete="CASCADE"), primary_key=True)
```

Esto fuerza la relación 1:1 a nivel de base de datos: es **imposible** tener una
ficha sin K-Item, y borrar el K-Item arrastra la ficha (`CASCADE`).

El detalle más interesante son las **propiedades proxy**:

```python
@property
def estado_ficha(self):
    return self.kitem.estado if self.kitem else None

@estado_ficha.setter
def estado_ficha(self, valor):
    self.kitem.estado = valor
```

**Qué problema resuelven:** originalmente el estado estaba duplicado en `kitem` y
en `ficha_tecnica`. Eso permite el peor bug posible en una máquina de estados: que
las dos copias se desincronicen. La migración 002 eliminó la columna duplicada
dejando `kitem.estado` como única fuente de verdad.

Pero había código y schemas que leían `ficha.estado_ficha`. Reescribir todo habría
sido riesgoso. La propiedad proxy resuelve ambos objetivos: **una sola fuente de
verdad, cero rupturas de compatibilidad**.

> ⚠️ **La trampa que debes conocer.** Una `@property` de Python es invisible para
> SQL. Esto **no funciona**:
> ```python
> select(FichaTecnica).where(FichaTecnica.estado_ficha == "Vigente")  # ❌
> ```
> Hay que hacer JOIN explícito:
> ```python
> select(FichaTecnica).join(KItem, FichaTecnica.id_ficha == KItem.id) \
>                     .where(KItem.estado == ESTADO_VIGENTE)          # ✔
> ```
> Este patrón aparece en todas las queries del proyecto. El docstring del modelo lo
> advierte explícitamente.

### 3.4 `KItemRelacion` — el grafo

Modela una arista dirigida: `source_id --[tipo_relacion]--> target_id`. Ambos
extremos apuntan a `kitem.id`, así que **cualquier tipo puede relacionarse con
cualquier otro** sin tablas puente por cada par.

La ambigüedad de tener dos FK a la misma tabla se resuelve declarando
`foreign_keys` explícitamente:

```python
relaciones_salientes = relationship("KItemRelacion",
    foreign_keys="KItemRelacion.source_id", back_populates="source", lazy="selectin")
```

`lazy="selectin"` es una decisión de rendimiento: en vez de N consultas (una por
K-Item, el clásico problema **N+1**), SQLAlchemy emite **una sola** consulta extra
con `WHERE source_id IN (...)`. Con 100 K-Items: 101 queries → 2 queries.

### 3.5 `KItemAuditoria` y `AnomaliaRegistro`

Ambas son **tablas de eventos**: se insertan, no se actualizan (salvo el campo de
resolución en anomalías). `KItemAuditoria` usa `ON DELETE SET NULL` en vez de
`CASCADE`, y la razón es de fondo: **si se borra un K-Item, su rastro de auditoría
debe sobrevivir**. Borrar la evidencia junto con el objeto anularía el propósito de
auditar.

---

## 4. Capa de schemas — `app/schemas/`

**Propósito:** los schemas Pydantic son el **contrato** entre el mundo exterior y el
sistema. Definen qué se acepta como entrada y qué forma tiene la salida.

**Cómo funciona:** cuando un endpoint declara `ficha_data: FichaTecnicaCreateSchema`,
FastAPI intercepta el JSON, lo valida contra el schema y **rechaza con 422 antes de
ejecutar una sola línea de lógica de negocio** si algo no encaja. Es una barrera
declarativa.

`from_attributes = True` (antes `orm_mode`) permite el camino inverso: construir un
schema desde un objeto ORM leyendo sus atributos.

**Justificación — la separación modelo/schema:** son responsabilidades distintas.
El modelo describe **cómo se persiste**; el schema describe **cómo se comunica**.
Mantenerlos separados permite exponer subconjuntos (`MaterialLiteSchema` para
listados) sin filtrar campos internos, y cambiar el esquema de base sin romper la
API. Es el patrón **DTO** (*Data Transfer Object*).

---

## 5. Capa de servicios — el corazón del sistema

Todos los servicios reciben la `AsyncSession` por constructor y componen los
servicios que necesitan:

```
FichaService    ──▶ KItemService, AuditoriaService, BusquedaSemanticaService, AnomaliaService
MaterialService ──▶ KItemService, BusquedaSemanticaService, AnomaliaService
KItemService    ──▶ AuditoriaService
BusquedaSemantica ─▶ AuditoriaService, embedding_service (módulo)
AnomaliaService ──▶ BusquedaSemanticaService, MLAnomaliaService
```

**Por qué composición y no herencia:** un `FichaService` no *es un* `KItemService`,
sino que *usa* uno. La herencia habría acoplado jerárquicamente servicios que solo
colaboran. Y como todos comparten la misma sesión, la transacción sigue siendo una.

### 5.1 `AuditoriaService` — el más simple y el más importante

```python
async def registrar(self, kitem_id, ktype, accion, usuario,
                    estado_anterior=None, estado_nuevo=None, detalles=None):
    evento = KItemAuditoria(...)
    self.db_session.add(evento)
    await self.db_session.flush()
    return evento
```

**La línea clave es `flush()`, no `commit()`.** La diferencia:

- `flush()` envía el `INSERT` a PostgreSQL **dentro de la transacción abierta**. La
  fila existe para esta sesión y ya tiene su UUID asignado, pero **no es visible
  para nadie más** y desaparece si hay rollback.
- `commit()` cierra la transacción y hace el cambio permanente.

**Por qué esto es correcto:** si `FichaService.crear()` falla en el paso 8, el
rollback debe borrar también los registros de auditoría de los pasos 1-7. Si
`AuditoriaService` hiciera `commit()`, quedarían eventos huérfanos describiendo una
ficha que nunca existió. **El servicio que inicia la operación es el único que
decide cuándo confirmar.**

### 5.2 `embedding_service.py` — de texto a vector

Es un **módulo de funciones**, no una clase, porque no tiene estado por instancia.

**El singleton perezoso:**

```python
_model: Optional[SentenceTransformer] = None

def get_embedding_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _model
```

`all-MiniLM-L6-v2` pesa ~90 MB y tarda segundos en cargarse. Sin este patrón se
cargaría en cada petición. Con él se carga **una vez, en la primera petición que lo
necesite** (no al arrancar: eso haría lento el arranque aunque nadie busque).

**La construcción del texto** es donde está la inteligencia real:

```python
partes.append(f"[{ktype}] {nombre}")     # el tipo entra en el texto
...
pares.append(f"{clave_limpia}: {valor}") # "material_base" → "material base"
```

Dos decisiones sutiles:
1. **El `ktype` se incluye en el texto.** Así el vector codifica "esto es una ficha
   técnica", separando en el espacio vectorial una ficha de un material aunque
   describan lo mismo.
2. **Los guiones bajos se convierten en espacios.** El modelo fue entrenado con
   lenguaje natural: `"material base: PET"` produce mejor representación que
   `"material_base: PET"`, donde el tokenizador partiría el término de forma
   arbitraria.

**La normalización:**

```python
embedding = modelo.encode(texto, normalize_embeddings=True)
```

Con vectores normalizados (norma = 1), el **producto punto equivale al coseno**.
Esto permite que pgvector use el operador de distancia coseno directamente sobre el
índice HNSW, sin normalizar en tiempo de consulta.

> **Pregunta probable: ¿por qué un modelo local y no la API de OpenAI?**
> Tres razones: (1) los datos técnicos de la empresa no salen de la red;
> (2) costo cero por consulta y sin límite de tasa; (3) sin latencia de red
> —el análisis de anomalías genera varios embeddings por ficha—. El costo es
> menor calidad semántica que un modelo de 1536 dimensiones. La constante
> `EMBEDDING_DIMENSION` está aislada justamente para permitir migrar.

### 5.3 `BusquedaSemanticaService` — búsqueda por significado

**El núcleo:**

```python
distancia = KItem.embedding.cosine_distance(embedding_consulta)
query = (select(KItem, (1 - distancia).label("similitud"))
         .where(and_(*conditions))
         .order_by(distancia.asc())
         .limit(limite))
```

**Lo importante: la búsqueda ocurre dentro de PostgreSQL, no en Python.**
`cosine_distance` se traduce al operador `<=>` de pgvector, que puede usar el índice
HNSW. La alternativa ingenua —traer todos los vectores a Python y comparar— sería
O(n) en memoria y en transferencia de red.

- La **distancia coseno** va de 0 (idénticos) a 2 (opuestos); por eso
  `similitud = 1 - distancia`.
- El `ORDER BY distancia ASC ... LIMIT` es lo que activa el índice: HNSW resuelve
  *"los k más cercanos"*, no *"todos los que superan un umbral"*.
- El filtro por `umbral_similitud` se aplica **después**, en Python. Es una
  concesión consciente: filtrar por umbral en SQL impediría usar el índice.

**Complejidad:** HNSW (*Hierarchical Navigable Small World*) da búsqueda aproximada
en **O(log n)** frente al O(n) del escaneo secuencial. Es *aproximada*: puede
perder algún vecino real, un intercambio deliberado de exactitud por velocidad.

**Búsqueda híbrida:** `buscar_por_texto` acepta `filtro_texto`, que agrega un
`ILIKE` sobre nombre y descripción. Combina filtrado léxico exacto con ranking
semántico.

**Reindexación masiva** usa `generar_embeddings_batch`, que aprovecha la
vectorización del modelo: procesar 64 textos juntos es mucho más rápido que 64
llamadas sueltas, porque las operaciones matriciales se paralelizan.

### 5.4 `AnomaliaService` — 7 detectores en capas

**Propósito:** validar que los datos que entran tengan sentido comparados con lo que
ya existe. No valida sintaxis (eso lo hace Pydantic) sino **plausibilidad**.

`analizar_ficha` orquesta 7 detectores independientes y acumula sus hallazgos:

#### Detector 1 — Valores atípicos (Z-score)

```python
media = sum(valores_ref) / len(valores_ref)
varianza = sum((v - media) ** 2 for v in valores_ref) / len(valores_ref)
std = varianza ** 0.5
z_score = abs(valor - media) / std
```

Mide **a cuántas desviaciones estándar está el valor de la media** de fichas de la
misma categoría. z ≥ 3 → crítico; z ≥ 2 → advertencia.

Tres detalles que revelan cuidado:
- **Guarda de muestras:** si hay menos de 3 fichas de referencia, no analiza. Con 2
  muestras la desviación estándar es ruido.
- **Caso `std == 0`:** si todas las fichas tienen el mismo valor, el z-score sería
  división por cero. El código lo intercepta y aplica otra regla: *"difiere del
  valor constante"*.
- **Campos "N/C":** si el usuario marcó un campo como *No Corresponde*
  (`<campo>_nc == True`), se excluye del cálculo. Un campo no aplicable no debe
  contaminar las estadísticas.

> **Nota sobre la varianza poblacional.** El código divide por `n`, no por `n-1`
> (corrección de Bessel). Con n pequeño esto **subestima** la dispersión, haciendo
> el detector algo más sensible. Si te lo preguntan: *"Es varianza poblacional; trato
> las fichas existentes como la población de referencia completa, no como una muestra
> de un universo mayor. Con n-1 el detector sería más conservador."*

#### Detector 2 — Unidades inconsistentes

Cuenta la frecuencia de cada unidad en fichas similares y alerta si la actual
difiere de una mayoritaria con ≥70% de consenso. Detecta el error clásico de
cargar milímetros donde el resto usa centímetros —error que **el z-score no
detectaría** si el número resultante cae en rango.

#### Detector 3 — Duplicados semánticos

Busca K-Items con similitud ≥ 0.95. La sutileza:

```python
if excluir_material_id and ktype == KTYPE_FICHA_TECNICA:
    # ignorar fichas del mismo material
```

Es **normal** que dos versiones de la ficha del mismo producto sean casi idénticas.
Solo se alerta si fichas de **materiales distintos** lo son —eso sí indica registro
duplicado.

#### Detector 4 — Clasificación cruzada

Si un material se parece semánticamente (≥0.85) a otro de **categoría distinta**,
sugiere que la clasificación puede estar mal. La severidad sube a crítica si además
hay **evidencia dimensional**:

```python
encaja = all(... rmin <= caract[c] <= rmax for c in rangos_sug ...)
fuera  = any(... not (rmin <= caract[c] <= rmax) for c in rangos_dec ...)
return encaja and fuera
```

Es decir: las medidas encajan en la categoría sugerida **y** se salen de la
declarada. Dos evidencias independientes —texto y números— apuntando a lo mismo.

#### Detector 5 — Perfil numérico cruzado

Calcula el **centroide** (vector de medias) de cada categoría y mide la distancia
euclidiana normalizada de la ficha a cada uno:

```python
diff = (vector[campo] - centroide[campo]) / desv   # normalización por σ
suma += diff ** 2
return (suma / n) ** 0.5
```

La normalización por desviación estándar es esencial: sin ella, un campo medido en
gramos (~500) dominaría a uno medido en milímetros (~3) por pura escala.

Luego compara: si la categoría más cercana no es la declarada y está **más de un
30% más cerca** (`ratio < 0.7`), alerta. Usar un **ratio** en lugar de una distancia
absoluta lo hace independiente de la escala del espacio.

#### Detector 6 — Isolation Forest (multivariado)

Los detectores 1-5 miran campos de a uno o de a pocos. Este mira **la combinación
completa**. Detecta el caso en que cada valor individual es plausible pero su
combinación no existe en los datos históricos (ej: largo grande + peso mínimo).

#### Detector 7 — Rangos duros por categoría

Rangos físicos absolutos definidos por conocimiento del dominio, no aprendidos.
Es la red de seguridad que funciona **desde la primera ficha**, cuando no hay datos
para estadística.

**La arquitectura de detección, en una frase para el jurado:**

> *"Los siete detectores son complementarios, no redundantes. Van de lo univariado
> a lo multivariado, de lo determinístico a lo estadístico a lo aprendido, y de lo
> numérico a lo semántico. Los rangos duros funcionan con cero datos; el z-score
> necesita 3 fichas; el Isolation Forest necesita 5. El sistema degrada
> ordenadamente: con pocos datos protege menos, pero nunca falla."*

### 5.5 `MLAnomaliaService` — Isolation Forest

**Por qué Isolation Forest y no otra cosa:** es un algoritmo **no supervisado**. No
requiere ejemplos etiquetados de "ficha mala" —que no existen, porque nadie
etiquetó un histórico de errores—. Su principio: construye árboles con cortes
aleatorios; los puntos anómalos quedan **aislados con menos cortes** porque están en
regiones poco densas. La longitud de camino promedio es el score.

Complejidad de entrenamiento: **O(n log n)**. Predicción: **O(log n)**.

**El pipeline de sklearn:**

```python
Pipeline([
    ("imputer", SimpleImputer(strategy="mean")),
    ("scaler",  StandardScaler()),
    ("modelo",  IsolationForest(n_estimators=100, contamination=cont, random_state=42)),
])
```

Cada etapa resuelve un problema concreto:
- **`SimpleImputer`**: las fichas tienen campos vacíos; sklearn no acepta `NaN`. Se
  rellenan con la media de la columna.
- **`StandardScaler`**: lleva cada campo a media 0 y desviación 1, evitando que las
  escalas dispares dominen.
- **`random_state=42`**: hace el entrenamiento **reproducible**. Sin esto, entrenar
  dos veces con los mismos datos daría modelos distintos —inaceptable para auditar.

**Dos decisiones defendibles:**

```python
def _contamination(n: int) -> float:
    return float(np.clip(1.0 / n, 0.05, 0.10))
```

`contamination` es la proporción esperada de anomalías. Se **adapta al tamaño**: con
pocas fichas, 1/n acotado entre 5% y 10%. Fijarlo en 10% con 5 fichas obligaría al
modelo a marcar media ficha como anómala siempre.

```python
fraccion_valida = np.mean(~np.isnan(X), axis=0)
mascara_cols = fraccion_valida >= 0.30
```

**Descarta columnas con menos del 30% de datos reales.** Una columna casi vacía, tras
la imputación, sería casi toda valores idénticos: ruido que empeora el modelo.

**Estrategia de dos niveles:** entrena un modelo global más uno por categoría con ≥5
fichas. En predicción intenta el específico y **cae al global** si no existe. Es un
*graceful degradation*: siempre hay respuesta, con la mejor precisión disponible.

Los modelos se serializan con `joblib` a `.pkl` y se cachean en memoria
(`self._cache`) para evitar leer disco en cada predicción.

### 5.6 `FichaService` — el orquestador

Es el servicio más extenso porque implementa el ciclo de vida completo.

#### `crear()` — el flujo transaccional

El orden importa y es defendible: primero **todas las validaciones** (material
existe, no está inactivo, código único), después **todas las escrituras**. Fallar
temprano evita trabajo desperdiciado.

La ficha nace siempre en `Borrador` v1.0, con código generado:

```python
return f"FT-{codigo_material_local}-{pais_norm}-{abreviatura_estado}-V{codigo_version}"
# → FT-4500123-CO-BOR-V1.0
```

El código es **derivado, no almacenado como fuente de verdad**: se regenera en cada
cambio de estado. Así nunca puede desincronizarse del estado real.

#### `cambiar_estado()` — la máquina de estados en acción

Secuencia de validaciones, de barata a cara:

1. `_validar_transicion_estado` → O(1), lookup en el diccionario
2. Validaciones de completitud según destino (`_validar_para_preliminar` / `_vigente`)
3. `_validar_unica_vigente_por_material_pais` → una query
4. **Bloqueo por anomalías pendientes**

```python
if anomalias_pendientes:
    raise HTTPException(400, f"hay {len(anomalias_pendientes)} anomalía(s) pendiente(s)")
```

**Esta es la integración clave entre los dos subsistemas:** el motor de anomalías no
es informativo, tiene **poder de veto** sobre el flujo de aprobación. Una ficha no
avanza con anomalías sin resolver. Un humano debe aceptarlas, descartarlas o
corregir el dato.

**El enriquecimiento al pasar a Preliminar** merece atención. Al crear la ficha aún
no hay datos suficientes para un buen embedding. Al pasar a Preliminar sí, entonces
se reescriben nombre y descripción del K-Item con información rica (material,
categoría, contenido, dimensiones) y se regenera el vector:

```python
nombre_rico = f"Ficha: {material.nombre_corporativo} - {ficha.codigo_material_local} ({ficha.pais})"
```

Todo esto va dentro de un `try/except` que **revierte la transición** si falla:

```python
except Exception as exc:
    raise HTTPException(500, "...la transición fue revertida.") from exc
```

Sin `commit()`, la excepción propaga y la sesión hace rollback. La ficha se queda en
Borrador en lugar de quedar en Preliminar sin analizar. **Consistencia sobre
disponibilidad.**

#### El auto-entrenamiento en background

```python
if nuevo_estado == ESTADO_VIGENTE and not _entrenamiento_en_cooldown():
    task = asyncio.create_task(_ejecutar_entrenamiento_bg())
    _bg_tasks.add(task)
    task.add_done_callback(_bg_tasks.discard)
```

Cuando una ficha se publica, el conjunto de entrenamiento creció: conviene
reentrenar. Pero eso tarda segundos y el usuario no debe esperar.

- `asyncio.create_task` lanza la corrutina **sin await**: el endpoint responde ya.
- `_bg_tasks.add(task)` mantiene una **referencia fuerte**. Sin ella el recolector
  de basura podría destruir la tarea a mitad de ejecución —es un bug clásico y
  documentado de asyncio.
- `add_done_callback(_bg_tasks.discard)` limpia el set al terminar, evitando fuga.
- El **cooldown de 1 hora** se persiste en un archivo (`ml_models/.last_training`),
  no en memoria: sobrevive a reinicios. Evita reentrenar 20 veces si se publican 20
  fichas seguidas.
- La tarea abre **su propia sesión** (`AsyncSessionLocal()`), porque la del request
  se cierra al responder.

#### `actualizar()` — versionado automático

Aquí está la regla de negocio más valiosa del sistema:

```python
if ficha.estado_ficha == ESTADO_OBSOLETO:
    raise HTTPException(400, "No se puede modificar una ficha en estado Obsoleto.")

if ficha.estado_ficha in (ESTADO_VIGENTE, ESTADO_REVISION):
    return await self._modificar_ficha_vigente(...)   # ← crea nueva versión

return await self._modificar_ficha_editable(...)      # ← edita in-place
```

**Una ficha Vigente no se edita: se versiona.** `_modificar_ficha_vigente`:

1. Crea un K-Item nuevo con versión incrementada (1.0 → 2.0), en estado Preliminar
2. Copia todas las secciones y aplica los cambios sobre la copia
3. Clona las imágenes al nuevo directorio (`clonar_imagenes_ficha`)
4. Crea la relación `se_deriva_de` → trazabilidad de linaje
5. Marca la ficha original como **Obsoleto**
6. Registra **dos** eventos de auditoría: la obsolescencia y la nueva versión

**Por qué:** una ficha Vigente es un documento publicado que puede estar impreso o
enviado a un cliente. Editarla en el lugar reescribiría la historia. El sistema
implementa **inmutabilidad de documentos publicados**, igual que un sistema
contable no borra asientos: los reversa.

### 5.7 `AuthService` — LDAP con fallback

Estrategia de cascada: `admin` siempre local (evita quedar fuera si cae el AD) →
LDAP si está configurado → local como respaldo.

**Justificación:** el sistema debe integrarse al Active Directory corporativo (sin
gestionar contraseñas propias), pero seguir siendo demostrable y desarrollable sin
acceso a la red de la empresa.

> ⚠️ **Debilidad seria — anticípala.** `USUARIOS_LOCALES` tiene contraseñas **en
> texto plano en el código fuente**. La respuesta honesta: *"Es un mecanismo de
> respaldo para desarrollo y demostración. En producción debe eliminarse o
> reemplazarse por hashes bcrypt/argon2 en base de datos. Es la deuda técnica más
> importante que tiene el proyecto en seguridad."* No intentes justificarlo: el
> jurado valorará más que lo identifiques vos.

### 5.8 `ExportService`

Genera PDF con ReportLab dibujando un *overlay* que luego se fusiona con una
plantilla corporativa vía pypdf. Permite que el diseño gráfico lo mantenga el área
de comunicación (editando el PDF plantilla) sin tocar código. Si no hay plantilla,
devuelve el overlay solo: degradación elegante.

---

## 6. Capa de routers

Los routers son deliberadamente delgados:

```python
def get_ficha_service(session: AsyncSession = Depends(get_session)) -> FichaService:
    return FichaService(db_session=session)

@router.post("", response_model=FichaTecnicaSchema, status_code=201)
async def crear_ficha(ficha_data: FichaTecnicaCreateSchema,
                      service: FichaService = Depends(get_ficha_service)):
    ficha = await service.crear(ficha_data)
    ...
```

Las dependencias se **encadenan**: FastAPI resuelve `get_session`, se lo pasa a
`get_ficha_service`, y este construye el servicio. En tests se puede sobrescribir
con `app.dependency_overrides`.

Los endpoints de transición son **semánticos, no genéricos**:

| Endpoint | Transición |
|---|---|
| `POST /ficha/{id}/aprobar-inicial` | Borrador → Preliminar |
| `POST /ficha/{id}/publicar` | Preliminar → Vigente |
| `POST /ficha/{id}/archivar` | → Obsoleto |

**Justificación:** `POST /ficha/{id}/publicar` expresa una **intención de negocio**;
`PATCH /ficha/{id} {"estado": "Vigente"}` expresaría una mutación de campo. El
primero es autodocumentado y permite permisos por acción.

### 6.1 Autenticación y origen de la identidad

Cada router de datos declara la validación una sola vez:

```python
router = APIRouter(
    prefix="/ficha",
    tags=["ficha"],
    dependencies=[Depends(get_usuario_actual)],
)
```

`dependencies=[...]` a nivel de `APIRouter` aplica la dependencia a **todos** sus
endpoints. Es la diferencia entre proteger un router y proteger 12 handlers uno
por uno, olvidando alguno. `POST /auth/login` es la única ruta pública: no puede
exigir el token que ella misma emite.

**La identidad viene del token, no del cliente.** Este es el punto sutil e
importante. Antes, los endpoints leían el usuario del cuerpo de la petición:

```python
usuario=request.usuario                     # ❌ autodeclarado por el cliente
usuario_actualizacion="sistema"             # ❌ constante, sin trazabilidad
usuario: str = "sistema"                    # ❌ query param manipulable
```

Un campo `usuario` enviado por el cliente es una **afirmación**, no una prueba.
Cualquiera podía registrar acciones a nombre de otra persona y corromper
exactamente aquello que el sistema promete: la auditoría. Ahora:

```python
async def publicar_ficha(
    id_ficha: UUID,
    service: FichaService = Depends(get_ficha_service),
    usuario: str = Depends(get_usuario_nombre),   # ✔ extraído del JWT firmado
):
    return await service.cambiar_estado(id_ficha, ESTADO_VIGENTE,
                                        usuario_actualizacion=usuario)
```

`get_usuario_nombre` ([security.py](../app/core/security.py)) depende de
`get_usuario_actual`, así que la firma ya fue verificada; solo extrae el
identificador. En los endpoints de creación, el router **sobrescribe** el campo
del cuerpo antes de invocar al servicio:

```python
ficha_data.usuario_creador = usuario   # lo que mandó el cliente se descarta
```

Los campos `usuario` / `usuario_creador` siguen aceptándose en los schemas como
opcionales por compatibilidad, pero se ignoran.

**Verificación automatizada:**
[tests/test_routers_autenticacion.py](../tests/test_routers_autenticacion.py)
recorre el esquema OpenAPI real y exige 401 en todo endpoint no declarado
público, más tests que envían `usuario_creador: "atacante.suplantador"` con un
token de otro usuario y comprueban que prevalece el del token. Un router nuevo
queda cubierto sin tocar el test.

> ⚠️ **Consecuencia de diseño en las imágenes.** Como `GET /ficha/{id}/imagen/{tipo}`
> exige token, **no puede consumirse desde un `<img src>`**: las etiquetas `<img>`
> no envían el header `Authorization`. El frontend descarga la imagen con Axios
> (`responseType: 'blob'`) y la expone vía *object URL* local. Es el precio de
> proteger un recurso binario con Bearer token.

---

## 7. Frontend

**Arquitectura:** React 19 + React Router 7 + Tailwind 4. Datos con **Axios +
`useState`/`useEffect`**; formularios con `useState` y `<form>` nativo.

**El cliente HTTP** ([frontend/lib/api.js](../frontend/lib/api.js)) centraliza dos
interceptores:

```javascript
// REQUEST: inyecta el JWT en cada petición
config.headers.Authorization = `Bearer ${token}`;

// RESPONSE: ante 401, limpia sesión y redirige a /login
if (status === 401) { localStorage.removeItem('dsms_token'); ... }
```

**Justificación:** ninguna página maneja tokens. Si mañana se cambia el esquema de
autenticación, se toca un archivo. El manejo del 401 es global: la expiración se
resuelve en un solo lugar en vez de en 15 componentes.

> ⚠️ El token vive en `localStorage`, accesible desde JavaScript y por tanto
> vulnerable a XSS. La alternativa robusta es una cookie `HttpOnly` + `SameSite`,
> que exige endpoint de logout y manejo de CSRF. Es un intercambio consciente
> entre simplicidad y superficie de ataque.
>
> ⚠️ No hay middleware CORS en `main.py`. En desarrollo funciona porque Vite hace
> proxy de `/api` (mismo origen). En producción, si el frontend se sirve desde otro
> origen, hay que agregar `CORSMiddleware`.

---

## 8. Testing

111 tests, sin base de datos, en ~16 segundos. Dos estrategias:

**Lógica pura** — se instancian servicios con `__new__` para saltarse el `__init__`
(que exigiría conexión):

```python
service = FichaService.__new__(FichaService)   # sin DB ni embeddings
service._validar_transicion_estado("Borrador", "Vigente")   # debe lanzar 400
```

**Orquestación** — `FakeSession` cuyo `execute()` devuelve resultados predefinidos
en orden, con colaboradores mockeados. Valida el *branching* de negocio
(transiciones, bloqueo por anomalías, versionado) sin PostgreSQL.

**Justificación:** los tests corren en cualquier máquina sin infraestructura, y
fallan por lógica rota, no por una base caída. La contrapartida —que no validan
SQL real ni pgvector— es una brecha reconocida: no hay tests end-to-end todavía.

---

## 9. Debilidades conocidas (tenerlas identificadas es una fortaleza)

| # | Debilidad | Dónde | Respuesta preparada |
|---|---|---|---|
| 1 | Contraseñas en texto plano | `auth_service.py:27` | Deuda técnica reconocida; migrar a bcrypt en BD |
| ~~2~~ | ~~Endpoints sin autenticación~~ | ~~`app/routers/`~~ | ✅ **RESUELTO** — los 45 endpoints exigen JWT; verificado por test sobre OpenAPI |
| ~~3~~ | ~~Usuario hardcodeado `"sistema"`~~ | ~~`ficha.py`~~ | ✅ **RESUELTO** — la identidad se extrae del token con `get_usuario_nombre` |
| 4 | `echo=True` en producción | `database.py:16` | Filtra datos en logs; parametrizar con `DEBUG` |
| 5 | `JWT_SECRET` con default embebido | `security.py:12` | Debe fallar el arranque si no está definida |
| 6 | Rate limiter en memoria | `security.py:104` | No sobrevive reinicio ni multi-worker; migrar a Redis |
| 7 | `listar()` sin paginación | `fichas_services.py:253` | O(n) y crece sin límite; agregar `limit/offset` |
| 8 | `_calcular_perfiles_categorias` carga todas las fichas | `anomalia_service.py:795` | O(n) por análisis; cachear centroides |
| 9 | N+1 en detección de duplicados | `anomalia_service.py:444` | Una query por candidato; resolver con JOIN |
| 10 | `_validar_contenido_por_tipo` no valida nada | `fichas_services.py:194` | Calcula `tiene_algun_valor` y retorna sin usarlo. **Es código muerto** |
| 11 | `obtener_grafo_kitem` pasa `metadata=` | `kitem_service.py:245` | El schema espera `metadata_relacion`; Pydantic ignora el extra y el campo sale siempre `None` |
| 12 | Sin CORS middleware | `main.py` | Depende del proxy de Vite; romperá en producción cross-origin |
| 13 | Cualquier anomalía bloquea la transición | `fichas_services.py:454` | Incluso las `informativa`; debería filtrar por severidad |
| 14 | Sin tests end-to-end | `tests/` | Cubre lógica, no integración con pgvector |

**Cómo presentar esto si te preguntan por limitaciones:**

> *"Identifiqué catorce y ya corregí las dos más graves. La autenticación no
> estaba aplicada a los routers y la identidad para auditoría se leía del cuerpo
> de la petición, lo que permitía registrar acciones a nombre de otro usuario.
> Ambas están resueltas y cubiertas por tests que recorren el esquema OpenAPI, así
> que un endpoint nuevo desprotegido rompe la suite.
>
> De las doce restantes: seguridad de despliegue —credenciales en código, logging
> verboso, secreto JWT con valor por defecto—, que bloquearían una puesta en
> producción real; rendimiento a escala —falta de paginación y recálculo de
> centroides—, que no se manifiestan con el volumen actual pero sí a partir de unos
> miles de fichas; y dos defectos concretos: una validación que quedó vacía y un
> campo del grafo que se serializa nulo por un nombre de parámetro desalineado con
> el schema."*

---

## 10. Las cinco ideas que debes poder defender

1. **Patrón K-Item.** Un supertipo universal permite que búsqueda semántica, grafo y
   auditoría funcionen sobre cualquier entidad sin código nuevo por tipo.
2. **Máquina de estados como datos.** Las reglas son un diccionario, no condicionales
   dispersos: validación O(1), extensible sin tocar lógica.
3. **Inmutabilidad de lo publicado.** Modificar una ficha Vigente genera una versión
   nueva y obsoleta la anterior, con relación `se_deriva_de` que preserva el linaje.
4. **Defensa en profundidad para calidad de datos.** Siete detectores complementarios
   que degradan ordenadamente según cuántos datos históricos existan, con poder de
   veto sobre el flujo de aprobación.
5. **Transacción única por operación.** Los servicios hacen `flush()`, solo el
   orquestador hace `commit()`. O se persiste todo —dato, embedding, relación,
   auditoría, anomalías— o no se persiste nada.
