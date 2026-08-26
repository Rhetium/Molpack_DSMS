# Despliegue con Docker — guía paso a paso

> Despliegue mínimo del sistema en un host Ubuntu. Dos contenedores: base de
> datos y aplicación. El TLS todavía **no** está resuelto: ver "Pendientes".
>
> Para el detalle de seguridad, LDAP y endurecimiento, ver
> [DESPLIEGUE_Y_SEGURIDAD.md](DESPLIEGUE_Y_SEGURIDAD.md).

---

## Qué se despliega

```
                    ┌──────────────────────────────┐
  Navegador ───────▶│  app  (contenedor)           │
  http://host:8000  │  uvicorn :8000               │
                    │  · sirve la SPA compilada    │
                    │  · sirve la API en /api      │
                    └────────┬───────────┬─────────┘
                             │           │
                LDAP/LDAPS ──┘           └── db (contenedor)
                al Domain Controller          PostgreSQL 16 + pgvector
```

Un solo origen: la SPA y la API se sirven desde el mismo proceso, por eso no
hace falta nginx ni configurar CORS.

---

## Requisitos en el host

- Docker Engine + plugin `compose` (`docker-ce`, `docker-compose-plugin`).
- El usuario de despliegue en el grupo `docker`.
- Salida a internet **durante el build** (PyPI, npm, Hugging Face).
- Salida al Domain Controller por 636/LDAPS si se usa Active Directory.

RAM: reservar al menos 2 GB para el contenedor `app` (carga el modelo de
embeddings en memoria).

---

## Pasos

### 1. Clonar y configurar

```bash
git clone <repo> molpack-dsms && cd molpack-dsms
cp .env.example .env
```

Editar `.env` y completar como mínimo:

| Variable | Nota |
|---|---|
| `DB_USER`, `DB_PASSWORD`, `DB_NAME` | Los usa tanto la app como el contenedor de PostgreSQL al crearse |
| `JWT_SECRET` | Generar uno propio: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `LDAP_*` | Dejar vacío para probar con usuarios locales; completar cuando TI entregue la cuenta de servicio |
| `APP_PORT` | Puerto publicado en el host (8000 por defecto) |

`DB_HOST` y `DB_PORT` no hay que tocarlos: dentro de Compose los fija el
propio `docker-compose.yml` apuntando al servicio `db`.

Permisos del archivo, que contiene secretos:

```bash
chmod 600 .env
```

### 2. Levantar

```bash
docker compose up -d --build
```

El primer build tarda bastante (compila la SPA, instala PyTorch y descarga el
modelo de embeddings dentro de la imagen). Los siguientes reutilizan caché.

El esquema de la base se crea solo: `scripts/schema_clean.sql` se monta en el
directorio de inicialización de PostgreSQL y se ejecuta la primera vez que el
volumen está vacío — incluye las extensiones `pgcrypto` y `vector` y el índice
HNSW.

### 3. Verificar

```bash
docker compose ps          # ambos servicios "running", db "healthy"
docker compose logs -f app # sin errores de conexión ni de modelo
```

En el navegador, `http://<host>:8000` debe mostrar el login, y
`http://<host>:8000/docs` el OpenAPI de FastAPI.

Smoke test completo (login, auditoría, búsqueda semántica, exportación,
rate limiting): sección 9 de [DESPLIEGUE_Y_SEGURIDAD.md](DESPLIEGUE_Y_SEGURIDAD.md).

---

## Operación diaria

```bash
docker compose logs -f app        # ver logs
docker compose restart app        # reiniciar solo la app
docker compose down               # detener (los datos sobreviven)
docker compose up -d --build      # desplegar una versión nueva
```

**Respaldo de la base:**

```bash
docker compose exec db pg_dump -U "$DB_USER" "$DB_NAME" > backups/dsms_$(date +%F).sql
```

**Acceso a la base desde tu equipo.** El puerto 5432 no está publicado a
propósito. Para administrarla con pgAdmin/DBeaver, túnel SSH contra el host:

```bash
ssh -L 5433:localhost:5432 <usuario>@<host>
```

...pero como el contenedor tampoco expone el puerto al host, lo directo es
entrar por `docker compose exec db psql -U "$DB_USER" "$DB_NAME"`.

**Qué respaldar:** el volumen `pgdata` (o el `pg_dump` de arriba) y el
directorio `uploads/`, que tiene las imágenes subidas por los usuarios.

---

## Pendientes antes de considerarlo producción

- [ ] **TLS.** Hoy el tráfico va en HTTP plano, incluido el JWT. Resolver con
      el reverse proxy corporativo de TI o montando nginx + certificado. Cuando
      exista, cambiar el mapeo de puertos a `"127.0.0.1:${APP_PORT}:8000"` para
      que la app deje de ser accesible directamente.
- [ ] **Usuarios locales hardcodeados** (`admin/admin`, `demo/demo`) y el bypass
      del usuario `admin`: deshabilitar (sección 6.3 del documento de seguridad).
- [ ] **`X-Forwarded-For`** propagado al backend cuando haya proxy delante, o el
      rate limiter contará todos los intentos contra la IP del proxy.
- [ ] **LDAPS (636)** en lugar de LDAP plano hacia el Domain Controller.
- [ ] El contenedor corre como `root`. Migrar a un usuario sin privilegios.
- [ ] Backups automatizados (hoy el `pg_dump` es manual).
