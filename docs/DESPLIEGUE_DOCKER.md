# Despliegue con Docker — guía paso a paso

> Despliegue del sistema en un host Ubuntu. Tres contenedores: base de datos,
> aplicación y —con el perfil `tls`— nginx para terminar HTTPS.
>
> Para el detalle de seguridad, LDAP y endurecimiento, ver
> [DESPLIEGUE_Y_SEGURIDAD.md](DESPLIEGUE_Y_SEGURIDAD.md).

---

## Servidor de destino

| Dato | Valor |
|---|---|
| Sistema operativo | Ubuntu 26.04 |
| IP | `172.21.5.74` |
| Hostname | `MKSVX64LNN10` |
| FQDN | `mksvx64lnn10.molpack.org` |
| Usuario de despliegue | `dsmsadm` |
| Alcance de red | VPN Molanca Planta, Oficina Caracas, Planta Valencia |

Molpack **no** dispone de reverse proxy corporativo, así que el TLS lo termina
el propio despliegue con el contenedor `nginx`.

---

## Qué se despliega

```
                    ┌──────────────────────────────┐
  Navegador ───────▶│  nginx  (perfil "tls")       │
  https://host      │  :443 · termina TLS          │
                    │  · cabeceras de seguridad    │
                    │  · X-Forwarded-For           │
                    └──────────────┬───────────────┘
                                   │ red interna de Compose
                    ┌──────────────▼───────────────┐
                    │  app  (contenedor)           │
                    │  uvicorn :8000               │
                    │  · sirve la SPA compilada    │
                    │  · sirve la API en /api      │
                    └────────┬───────────┬─────────┘
                             │           │
                LDAP/LDAPS ──┘           └── db (contenedor)
                al Domain Controller          PostgreSQL 16 + pgvector
```

Un solo origen: la SPA y la API se sirven desde el mismo proceso, por eso nginx
solo hace `proxy_pass` —sin reescribir rutas— y no hace falta configurar CORS.

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
| `APP_BIND` | `127.0.0.1` con el perfil `tls`; `0.0.0.0` solo para pruebas sin TLS |
| `FORWARDED_ALLOW_IPS` | `*` con el perfil `tls`, para que el rate limiter vea la IP real del usuario |
| `AUTH_LOCAL_HABILITADO` | `false` en producción: apaga los usuarios embebidos (`admin/admin`, `demo/demo`) |

`DB_HOST` y `DB_PORT` no hay que tocarlos: dentro de Compose los fija el
propio `docker-compose.yml` apuntando al servicio `db`.

Permisos del archivo, que contiene secretos:

```bash
chmod 600 .env
```

### 2. Certificado TLS

```bash
./deploy/generar-certificado.sh csr           # entregar deploy/certs/dsms.csr a TI
./deploy/generar-certificado.sh autofirmado   # provisional, para no esperar
```

El camino correcto es el `csr`: TI lo firma con la CA interna del dominio y los
equipos de Molpack confían en el certificado sin avisos. El autofirmado cifra
igual pero cada navegador mostrará una advertencia hasta que TI distribuya la
CA por GPO.

Mientras el certificado sea autofirmado, **HSTS debe quedar comentado** en
[deploy/nginx/dsms.conf](../deploy/nginx/dsms.conf): una vez que el navegador
registra HSTS para este host deja de ofrecer el "continuar de todos modos" ante
un certificado no confiable, y el sistema queda inaccesible.

Los certificados no se versionan y la clave privada no sale de la VM.

### 3. Levantar

```bash
docker compose --profile tls up -d --build      # con HTTPS
docker compose up -d --build                    # sin nginx, HTTP plano (pruebas)
```

El primer build tarda bastante (compila la SPA, instala PyTorch y descarga el
modelo de embeddings dentro de la imagen). Los siguientes reutilizan caché.

El esquema de la base se crea solo: `scripts/schema_clean.sql` se monta en el
directorio de inicialización de PostgreSQL y se ejecuta la primera vez que el
volumen está vacío — incluye las extensiones `pgcrypto` y `vector` y el índice
HNSW.

### 4. Verificar

```bash
docker compose --profile tls ps   # los tres "running", db "healthy"
docker compose logs -f app        # sin errores de conexión ni de modelo
docker compose logs nginx         # sin errores de certificado
```

En el navegador, `https://mksvx64lnn10.molpack.org` debe mostrar el login, y
`https://mksvx64lnn10.molpack.org/docs` el OpenAPI de FastAPI. `http://` debe
redirigir al 443.

Smoke test completo (login, auditoría, búsqueda semántica, exportación,
rate limiting): sección 9 de [DESPLIEGUE_Y_SEGURIDAD.md](DESPLIEGUE_Y_SEGURIDAD.md).

---

## Operación diaria

```bash
docker compose logs -f app                    # ver logs
docker compose restart app                    # reiniciar solo la app
docker compose --profile tls restart nginx    # recargar tras cambiar el certificado
docker compose --profile tls down             # detener (los datos sobreviven)
docker compose --profile tls up -d --build    # desplegar una versión nueva
```

El `--profile tls` hace falta en cada comando que deba alcanzar a nginx; sin él,
`down` deja el contenedor corriendo y `ps` no lo lista.

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

Resueltos en el repositorio:

- [x] **TLS.** Contenedor `nginx` con perfil `tls`, cabeceras de seguridad y CSP.
      Falta el certificado firmado por la CA interna y descomentar HSTS.
- [x] **Usuarios locales hardcodeados** y el bypass del usuario `admin`: se
      apagan solos al configurar LDAP, o con `AUTH_LOCAL_HABILITADO=false`.
- [x] **`X-Forwarded-For`**: uvicorn corre con `--proxy-headers` y nginx propaga
      la IP real, acotado por `FORWARDED_ALLOW_IPS`.

Pendientes:

- [ ] **Certificado de la CA interna** de Molpack para `mksvx64lnn10.molpack.org`
      y, una vez confiable, **habilitar HSTS**.
- [ ] **LDAPS (636)** en lugar de LDAP plano hacia el Domain Controller, con el
      certificado del DC confiable en el host.
- [ ] El contenedor corre como `root`. Migrar a un usuario sin privilegios.
- [ ] Backups automatizados (hoy el `pg_dump` es manual).
- [ ] El rate limiter sigue en memoria del proceso: se reinicia con el
      contenedor. Mover a Redis si se necesita persistencia entre despliegues.
