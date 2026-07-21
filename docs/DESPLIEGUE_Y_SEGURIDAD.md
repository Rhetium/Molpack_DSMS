# Molpack DSMS — Guía de Despliegue y Seguridad (para TI)

> **Audiencia:** equipo de TI / Infraestructura / Ciberseguridad de Molpack.
> **Propósito:** todo lo necesario para desplegar el sistema, integrarlo con
> **Active Directory (LDAP)** y endurecerlo para producción.
> **Fuente:** este documento se elaboró leyendo el código fuente real
> (rama `Development`). Los puntos marcados **⚠️** son acciones obligatorias
> antes de exponer el sistema.

---

## 0. Resumen ejecutivo

Molpack DSMS es una aplicación web de gestión de fichas técnicas compuesta por:

- **Backend** API REST en Python (FastAPI, ASGI) — puerto **8000**.
- **Frontend** SPA en React (compilado con Vite a archivos estáticos).
- **Base de datos** PostgreSQL con las extensiones **pgvector** y **uuid-ossp**.
- **Autenticación** contra **Active Directory (LDAP)** con emisión de tokens JWT.

El repositorio **no incluye** Dockerfile, docker-compose ni pipeline de CI/CD:
el despliegue es **manual**. El código está preparado para funcionar pero
**no está endurecido para producción de fábrica**; la Sección 7 lista lo que TI
debe configurar antes de publicarlo.

### Bloqueadores conocidos (leer antes de empezar)

| # | Bloqueador | Impacto | Sección |
|---|---|---|---|
| 1 | `requirements.txt` **incompleto** (faltan PyJWT, ldap3, reportlab, pypdf, openpyxl) | La app arranca pero falla en runtime al autenticar/exportar | 3.1 |
| 2 | Sin **CORS/TLS/reverse proxy** configurado | El navegador bloquea llamadas si front y back no son mismo origen; tráfico sin cifrar | 7 |
| 3 | Motor de BD con `echo=True` | Registra **todo el SQL** (incl. datos) en consola: ruido y fuga de información | 7 |
| 4 | **Usuarios locales hardcodeados** (`admin/admin`, etc.) siempre activos | Acceso con credenciales por defecto | 6.3 / 7 |
| 5 | `JWT_SECRET` con valor por defecto si no se define en `.env` | Tokens falsificables | 6.1 / 7 |

---

## 1. Arquitectura de despliegue

```
                           ┌──────────────────────────┐
   Navegador del usuario   │  Reverse proxy / TLS      │   (TI debe proveer:
   (HTTPS) ───────────────▶│  Nginx / IIS / Traefik    │    Nginx o similar)
                           │  · sirve estáticos (SPA)  │
                           │  · enruta /api → :8000    │
                           └────────────┬──────────────┘
                        estáticos │            │ /api (proxy)
                    ┌─────────────▼──┐   ┌─────▼─────────────────┐
                    │  Frontend SPA  │   │  Backend FastAPI      │
                    │  (dist/ Vite)  │   │  uvicorn :8000        │
                    └────────────────┘   └───┬───────────┬───────┘
                                             │           │
                              LDAP/LDAPS ────┘           └──── PostgreSQL
                              (389 / 636)                       (5432)
                              a Domain Controller               + pgvector
```

**Puertos involucrados:**

| Servicio | Puerto | Notas |
|---|---|---|
| Backend (uvicorn) | 8000 | HTTP interno; no exponer directo a Internet |
| PostgreSQL | 5432 | Solo accesible desde el backend |
| LDAP / LDAPS | 389 / 636 | Desde el backend hacia el/los Domain Controller |
| Reverse proxy | 443 (HTTPS) | Único punto expuesto al usuario final |
| Frontend dev (Vite) | 5173 | **Solo desarrollo**, no producción |

---

## 2. Requisitos de plataforma

| Componente | Requisito |
|---|---|
| Sistema operativo | Linux (recomendado para producción) o Windows Server |
| Python | 3.12 (probado con 3.12.5) |
| Node.js | 20 LTS+ (solo para **compilar** el frontend; no se necesita en runtime) |
| PostgreSQL | 14+ con extensiones **`vector` (pgvector)** y **`uuid-ossp`** |
| RAM | El backend carga en memoria el modelo de embeddings (~90 MB) + PyTorch. Mínimo recomendado **2 GB** libres para el proceso |
| Disco | Espacio para: imágenes subidas, modelos ML (`.pkl`) y (opcional) modelo de embeddings en caché de HuggingFace |
| Red saliente | El primer arranque descarga el modelo `all-MiniLM-L6-v2` desde HuggingFace (o pre-provisionarlo offline) |

---

## 3. Despliegue del backend

### 3.1 ⚠️ Dependencias (corregir antes de instalar)

`requirements.txt` **no lista todas** las dependencias que el código importa.
Faltan las siguientes (se usan en autenticación, seguridad y exportación):

```
PyJWT          # JWT (app/core/security.py)
ldap3          # Active Directory (app/services/auth_service.py)
reportlab      # PDF (app/services/export_service.py)
pypdf          # PDF con plantilla
openpyxl       # Exportación a Excel
```

**Acción:** agregarlas a `requirements.txt` (con versiones fijadas) o instalarlas
explícitamente. Sin ellas, la app **arranca** pero devuelve error 500 al iniciar
sesión o exportar.

### 3.2 Instalación

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt      # + las dependencias faltantes de 3.1
```

### 3.3 Ejecución en producción

**No** usar `--reload`. Servir con un gestor de procesos (systemd, supervisor) y
un worker ASGI de producción, por ejemplo:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
# o gunicorn con workers uvicorn:
# gunicorn app.main:app -k uvicorn.workers.UvicornWorker -b 127.0.0.1:8000 -w 1
```

> **Advertencia sobre workers:** el **rate limiter de login vive en memoria del
> proceso** (Sección 6.2). Con varios workers, cada uno lleva su propio conteo,
> debilitando la protección anti-fuerza-bruta. Para escalar horizontalmente,
> mover el rate limiting a un almacén compartido (Redis) o al reverse proxy.

### 3.4 Dependencias de filesystem (persistencia)

El backend escribe en el disco local (relativo al directorio de ejecución). En
un despliegue con contenedores o múltiples nodos, **estos directorios deben ser
volúmenes persistentes y respaldados**:

| Ruta | Contenido | Criticidad |
|---|---|---|
| `uploads/productos/{id_ficha}/` | Imágenes subidas (foto producto, plano) | Alta — datos de usuario |
| `app/ml_models/*.pkl` | Modelos Isolation Forest entrenados | Media — regenerables con `POST /anomalias/entrenar` |
| `app/ml_models/.last_training` | Marca de cooldown de reentrenamiento | Baja |
| `app/templates/plantilla_ficha.pdf` | Plantilla PDF opcional para exportación | Baja — si falta, genera PDF propio |

---

## 4. Despliegue del frontend

El frontend es una SPA que se **compila** a archivos estáticos:

```bash
cd frontend
npm install
npm run build        # genera frontend/dist/
```

Servir el contenido de `frontend/dist/` desde el reverse proxy, y **enrutar
`/api` hacia el backend** (`http://127.0.0.1:8000`), replicando el proxy que en
desarrollo hace Vite:

- En dev, [frontend/vite.config.js](../frontend/vite.config.js) reescribe
  `'/api' → target :8000` quitando el prefijo `/api`.
- En **producción, el reverse proxy debe hacer lo mismo** (p. ej. en Nginx
  `location /api/ { proxy_pass http://127.0.0.1:8000/; }`).

> Nota: `vite.config.js` tiene `host: '0.0.0.0'` y `allowedHosts:
> ['.ngrok-free.dev']` — esto es para **túneles de demostración con ngrok** en
> desarrollo; no aplica ni debe usarse en producción.

---

## 5. Base de datos

1. Provisionar PostgreSQL 14+ y crear la base de datos.
2. Habilitar extensiones (el script ya lo hace):
   ```sql
   CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
   CREATE EXTENSION IF NOT EXISTS "vector";      -- pgvector
   ```
3. Crear el esquema:
   ```bash
   psql -U <user> -d <db> -f scripts/create_tables.sql
   ```
4. **Índice vectorial (recomendado al crecer el catálogo):** el índice IVFFlat
   de pgvector está **comentado** en `scripts/create_tables.sql` (sección 7). Con
   pocos registros la búsqueda por escaneo completo es suficiente; con volumen
   alto, descomentarlo y crearlo **después** de cargar datos:
   ```sql
   CREATE INDEX ix_kitem_embedding_ivfflat
     ON kitem USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);
   ```
5. ⚠️ **Motor con logging verboso:** el engine se crea con `echo=True`
   ([app/core/database.py](../app/core/database.py)), lo que imprime **todo el
   SQL ejecutado** (incluye valores). En producción cambiar a `echo=False` para
   evitar ruido y fuga de datos en logs.

---

## 6. Medidas de seguridad implementadas

### 6.1 Autenticación y tokens (JWT)

Implementado en [app/core/security.py](../app/core/security.py):

- Tokens **JWT firmados con HS256**, expiración configurable
  (`JWT_EXPIRATION_HOURS`, por defecto **8 horas**).
- El token se emite en `POST /auth/login` y se exige en el header
  `Authorization: Bearer <token>` para **todos** los routers de datos, gracias a
  la dependencia global `Depends(get_usuario_actual)` registrada en
  [app/main.py](../app/main.py).
- `GET /auth/me` valida vigencia; `POST /auth/refresh` renueva el token.
- El payload contiene: usuario, nombre, rol, iniciales, email, método, `iat`,
  `exp`. **No** contiene contraseñas.

**Puntos de atención:**
- ⚠️ `JWT_SECRET` tiene un **valor por defecto de desarrollo** embebido en el
  código; si no se define en `.env`, los tokens son falsificables. **Definir un
  secreto fuerte** (`python -c "import secrets; print(secrets.token_hex(32))"`).
- El token se almacena en el navegador en **`localStorage`** y el frontend
  **decodifica el payload en cliente** para leer la expiración. `localStorage` es
  accesible por JavaScript ⇒ expuesto a **XSS**. Mitigar con CSP estricta y, si
  se requiere mayor robustez, migrar a cookies `HttpOnly`.

### 6.2 Rate limiting anti-fuerza-bruta

`RateLimiter` en memoria ([app/core/security.py](../app/core/security.py)):

- Máximo **5 intentos fallidos por IP** en ventana de **60 s**.
- Al excederlos, **bloqueo de 300 s (5 min)** con respuesta **HTTP 429**.
- Se resetea con un login exitoso.

**Limitaciones:** es **por proceso** y **en memoria** → se reinicia al reiniciar
el servicio y no se comparte entre workers/nodos (ver 3.3). La IP se toma de
`request.client.host`, por lo que **detrás de un reverse proxy** hay que
propagar la IP real (`X-Forwarded-For`) o el conteo será por la IP del proxy.

### 6.3 Modelo de autenticación híbrido (LDAP + local)

[app/services/auth_service.py](../app/services/auth_service.py):

- Si LDAP está configurado, autentica contra **Active Directory** (ver Sección 8).
- Si LDAP no está configurado o falla, cae a **usuarios locales**.
- ⚠️ Existen **usuarios locales hardcodeados** en el código para desarrollo
  (`admin/admin`, `marco.agrusa/…`, `demo/demo`), y el usuario **`admin` siempre
  se autentica localmente**, incluso con LDAP activo. **En producción deben
  eliminarse o deshabilitarse** (ver Sección 7).

### 6.4 Validación de entrada

- **Schemas Pydantic** validan tipos y formatos en todos los endpoints.
- **Carga de imágenes** ([app/routers/imagenes.py](../app/routers/imagenes.py))
  valida: content-type (`image/jpeg|png`), extensión, tamaño y **dimensiones
  leyendo las cabeceras del archivo** (sin ejecutar el binario). Solo se permiten
  2 tipos (`foto_producto`, `plano_mecanico`) y solo en fichas en estado editable.
  - Nota: el límite real de tamaño es **5 MB** (`MAX_FILE_SIZE`), aunque la
    documentación interna dice 2 MB — conviene unificar el valor.

### 6.5 Auditoría / trazabilidad

- **Toda mutación** (creación, cambio de estado, modificación, relaciones,
  embeddings) se registra de forma automática en la tabla `kitem_auditoria` con
  usuario, acción, estado anterior/nuevo, timestamp y detalles.
- Las anomalías detectadas quedan en `anomalia_registro` con su estado de
  resolución. Esto provee un **rastro de auditoría** consultable.

### 6.6 Superficie de red

- **Endpoint público sin autenticación:** `GET /ficha/{id}/imagen/{tipo}` se sirve
  sin token (se consume vía `<img src>`). Cualquiera con el **UUID** de una ficha
  puede recuperar sus imágenes. Si las imágenes son sensibles, protegerlas
  (token en query firmado, o servir tras el proxy con auth). El resto de la API
  exige JWT.

---

## 7. ⚠️ Checklist de endurecimiento para producción

Acciones **obligatorias/recomendadas** antes de exponer el sistema. Ninguna
está resuelta "de fábrica" en el repositorio:

- [ ] **Completar `requirements.txt`** con PyJWT, ldap3, reportlab, pypdf,
      openpyxl (Sección 3.1).
- [ ] **`JWT_SECRET` fuerte y único** por entorno; nunca el valor por defecto.
- [ ] **Deshabilitar/eliminar usuarios locales** hardcodeados y el bypass del
      usuario `admin` (Sección 6.3), o restringirlos a un entorno de soporte
      controlado.
- [ ] **Terminación TLS/HTTPS** en el reverse proxy (la app sirve HTTP plano).
- [ ] **Usar LDAPS (636) o StartTLS** hacia el AD para no enviar credenciales en
      claro (Sección 8).
- [ ] **Configurar CORS** si el frontend se sirve desde un origen distinto al
      backend. **Actualmente no hay `CORSMiddleware`**; el modelo funciona solo
      si front y `/api` comparten origen vía el reverse proxy.
- [ ] **`echo=False`** en el engine de BD (Sección 5).
- [ ] **Propagar la IP real** (`X-Forwarded-For`) al backend para que el rate
      limiter y los logs no vean solo la IP del proxy.
- [ ] **Gestión de secretos:** `.env` fuera del control de versiones (ya está en
      `.gitignore`), permisos restringidos (p. ej. `chmod 600`), idealmente un
      gestor de secretos (Vault, AWS SM, DPAPI/DSC en Windows).
- [ ] **Backups** de PostgreSQL y del directorio `uploads/`.
- [ ] **CSP y cabeceras de seguridad** (X-Content-Type-Options, X-Frame-Options,
      HSTS) en el reverse proxy; mitiga el riesgo de XSS sobre el JWT en
      `localStorage`.
- [ ] **Rotación/expiración** de la contraseña de la cuenta de servicio LDAP
      gestionada con TI.
- [ ] Revisar la exposición del **endpoint público de imágenes** (Sección 6.6).
- [ ] Restringir el acceso a **PostgreSQL** (firewall) solo desde el backend.

---

## 8. Integración con Active Directory (LDAP) — lo que TI debe proveer

Esta es la parte que requiere coordinación directa con TI. La autenticación LDAP
la implementa [app/services/auth_service.py](../app/services/auth_service.py) con
la librería **`ldap3`**.

### 8.1 Variables de entorno a configurar (`.env`)

| Variable | Descripción | Ejemplo |
|---|---|---|
| `LDAP_SERVER` | URL del Domain Controller | `ldaps://dc01.molpack.net:636` (recom.) o `ldap://dc01.molpack.net` |
| `LDAP_BASE_DN` | DN base donde buscar usuarios | `DC=molpack,DC=net` |
| `LDAP_BIND_DN` | DN de la **cuenta de servicio** (bind) | `CN=svc_dsms,OU=Service Accounts,DC=molpack,DC=net` |
| `LDAP_BIND_PASSWORD` | Contraseña de la cuenta de servicio | *(secreto)* |
| `LDAP_GRUPO_AUTORIZADO` | DN del grupo cuyos miembros pueden entrar | `CN=DSMS_Users,OU=Groups,DC=molpack,DC=net` |
| `LDAP_USER_FILTER` | Filtro de búsqueda del usuario | `(sAMAccountName={username})` (por defecto) |
| `LDAP_USE_SSL` | Usar SSL (LDAPS) | `true` |

> **Activación:** LDAP se considera habilitado solo si **`LDAP_SERVER` y
> `LDAP_BASE_DN` tienen valor** (`LDAP_HABILITADO`). Si están vacíos, el sistema
> **solo** usará usuarios locales.

### 8.2 Flujo de autenticación contra AD (lo que ocurre en cada login)

1. **Bind de servicio:** el backend se conecta al DC con `LDAP_BIND_DN` /
   `LDAP_BIND_PASSWORD`.
2. **Búsqueda del usuario** por `sAMAccountName` bajo `LDAP_BASE_DN`
   (scope SUBTREE), solicitando los atributos: `cn`, `displayName`, `mail`,
   `memberOf`, `sAMAccountName`, `department`, `title`.
3. **Bind del usuario:** intenta autenticar con el DN encontrado y la contraseña
   ingresada → valida la credencial.
4. **Autorización por grupo:** si `LDAP_GRUPO_AUTORIZADO` está definido, verifica
   que ese grupo esté en el `memberOf` del usuario; si no, **deniega**.
5. **Extracción de datos y rol:** toma `displayName`, `mail`, `department`. El
   **rol** se deriva del `memberOf`:
   - grupo que contenga `admin` → **Administrador**
   - grupo que contenga `qa` o `calidad` → **QA**
   - en otro caso → **Consultor** (rol por defecto).
6. Si el login es exitoso, el backend **emite el JWT** propio (el AD solo valida
   identidad; la sesión posterior es por token).

> **Fallback:** si el bind de servicio o la búsqueda fallan, el sistema intenta
> autenticación **local** como respaldo (ver 6.3 y checklist).

### 8.3 Requisitos de red y directorio (checklist para TI)

- [ ] **Conectividad de red / firewall:** permitir del **servidor del backend**
      hacia el/los **Domain Controller** el puerto **636 (LDAPS)** —recomendado—
      o **389 (LDAP)**.
- [ ] **Resolución DNS** del hostname del DC desde el servidor del backend.
- [ ] **Cuenta de servicio** (`svc_dsms` o equivalente) con permiso de **lectura**
      sobre los objetos de usuario y el atributo `memberOf` bajo el `BASE_DN`.
      Preferible contraseña gestionada / no expirable, o rotación coordinada.
- [ ] **Grupo de autorización** (`DSMS_Users` o el que definan) creado y poblado
      con los usuarios que deben acceder.
- [ ] **Grupos de rol** (opcional): grupos cuyo nombre contenga `admin`, `qa` o
      `calidad` para el mapeo automático de roles (Administrador / QA / Consultor).
- [ ] **Certificado del DC** confiable en el servidor del backend si se usa LDAPS
      (para validar la cadena TLS).
- [ ] **Formato del filtro** confirmado: por defecto `sAMAccountName`; ajustar
      `LDAP_USER_FILTER` si Molpack usa `userPrincipalName` u otro atributo.

### 8.4 Prueba de la integración

Tras configurar el `.env`:

1. Verificar conectividad al DC (`Test-NetConnection dc01.molpack.net -Port 636`
   en Windows, o `nc -vz dc01.molpack.net 636` en Linux).
2. Levantar el backend y llamar a `POST /auth/login` con un usuario real del AD
   que pertenezca al grupo autorizado.
3. Confirmar que la respuesta trae `"metodo": "ldap"` (no `"local"`) y un token.
4. Probar un usuario **fuera** del grupo autorizado → debe denegar el acceso.

---

## 9. Verificación post-despliegue (smoke test)

- [ ] `GET /docs` responde (OpenAPI de FastAPI) a través del reverse proxy.
- [ ] Login con usuario de AD devuelve `metodo: ldap` + token.
- [ ] Una llamada autenticada (p. ej. `GET /material`) responde 200 con el token
      y 401 sin él.
- [ ] Crear un material/ficha genera fila en `kitem_auditoria`.
- [ ] La búsqueda semántica responde (confirma que el modelo de embeddings cargó
      y que pgvector funciona).
- [ ] Exportar una ficha a PDF/Excel funciona (confirma reportlab/openpyxl).
- [ ] Tras 5 logins fallidos, el 6º devuelve HTTP 429 (rate limiting).
- [ ] Los logs **no** muestran SQL crudo (confirma `echo=False`).

---

## 10. Contacto y trazabilidad del documento

- Reporte técnico general del sistema: [docs/REPORTE_TECNICO.md](REPORTE_TECNICO.md).
- Este documento describe el estado del código en la rama `Development`. Cualquier
  discrepancia con el comportamiento real debe verificarse contra el archivo
  citado en cada sección.
```
