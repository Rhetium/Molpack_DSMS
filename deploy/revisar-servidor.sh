#!/usr/bin/env bash
# =============================================================
# Molpack DSMS — diagnostico del servidor de despliegue.
#
# SOLO LECTURA: no instala, no levanta, no modifica nada.
#
#   Desde tu equipo, sin copiar el archivo:
#     ssh dsmsadm@172.21.5.74 'bash -s' < deploy/revisar-servidor.sh
#
#   O ya dentro del servidor:
#     bash deploy/revisar-servidor.sh
# =============================================================

titulo() { printf '\n=== %s %s\n' "$1" "$(printf '%.0s-' $(seq 1 $((60 - ${#1}))))"; }
hay()    { command -v "$1" >/dev/null 2>&1; }

titulo "Sistema"
. /etc/os-release 2>/dev/null && echo "SO       : $PRETTY_NAME"
echo "Kernel   : $(uname -r)"
echo "Hostname : $(hostname -f 2>/dev/null || hostname)"
echo "Usuario  : $(id -un)  (grupos: $(id -Gn))"
echo "RAM      : $(free -h 2>/dev/null | awk '/^Mem:/{print $2" total, "$7" disponible"}')"
echo "Disco /  : $(df -h / | awk 'NR==2{print $2" total, "$4" libre ("$5" usado)"}')"

titulo "Docker"
if hay docker; then
  echo "docker   : $(docker --version)"
  if docker compose version >/dev/null 2>&1; then
    echo "compose  : $(docker compose version --short 2>/dev/null)"
  else
    echo "compose  : PLUGIN AUSENTE (hace falta docker-compose-plugin)"
  fi
  if docker info >/dev/null 2>&1; then
    echo "permisos : OK, el usuario puede hablar con el demonio"
  else
    echo "permisos : SIN ACCESO (falta estar en el grupo 'docker' o relogin)"
  fi
else
  echo "docker   : NO INSTALADO"
fi

titulo "Proyecto"
DIR=""
for d in "$HOME/Molpack_DSMS" "$HOME/molpack_dsms" /opt/Molpack_DSMS \
         /srv/Molpack_DSMS "$PWD"; do
  [ -f "$d/docker-compose.yml" ] && { DIR="$d"; break; }
done
if [ -z "$DIR" ]; then
  echo "NO ENCONTRADO: no hay docker-compose.yml en las rutas habituales."
  echo "Buscando en las rutas usuales..."
  find /home /opt /srv /var/www -maxdepth 4 -name docker-compose.yml \
       -not -path '*/node_modules/*' 2>/dev/null | head -5
else
  echo "Directorio : $DIR"
  cd "$DIR" || exit 1
  if [ -d .git ]; then
    echo "Rama       : $(git rev-parse --abbrev-ref HEAD 2>/dev/null)"
    echo "Commit     : $(git log -1 --format='%h %s' 2>/dev/null)"
    echo "Sin commitear: $(git status --porcelain 2>/dev/null | wc -l) archivo(s)"
  else
    echo "Git        : no es un repo (copiado a mano?)"
  fi

  titulo "Archivo .env"
  if [ -f .env ]; then
    echo "Permisos : $(stat -c '%a %U:%G' .env)   (deberia ser 600)"
    echo "Variables definidas (valores ocultos):"
    grep -vE '^\s*#|^\s*$' .env | cut -d= -f1 | sed 's/^/  - /'
    echo "Chequeos:"
    for v in DB_USER DB_PASSWORD DB_NAME JWT_SECRET; do
      grep -qE "^$v=.+" .env && echo "  OK    $v tiene valor" \
                             || echo "  FALTA $v vacio o ausente"
    done
    b=$(grep -E '^APP_BIND=' .env | cut -d= -f2)
    [ "$b" = "127.0.0.1" ] && echo "  OK    APP_BIND=127.0.0.1" \
      || echo "  OJO   APP_BIND='${b:-<ausente>}' (con perfil tls debe ser 127.0.0.1)"
  else
    echo "NO EXISTE .env  -> copiar de .env.example y completar"
  fi

  titulo "Certificados TLS"
  for f in deploy/certs/dsms.crt deploy/certs/dsms.key; do
    [ -f "$f" ] && echo "OK    $f ($(stat -c '%a' "$f"))" || echo "FALTA $f"
  done
  if [ -f deploy/certs/dsms.crt ]; then
    openssl x509 -in deploy/certs/dsms.crt -noout -subject -dates 2>/dev/null
    iss=$(openssl x509 -in deploy/certs/dsms.crt -noout -issuer 2>/dev/null)
    sub=$(openssl x509 -in deploy/certs/dsms.crt -noout -subject 2>/dev/null)
    [ "${iss#issuer=}" = "${sub#subject=}" ] \
      && echo "Tipo: AUTOFIRMADO -> HSTS debe seguir comentado" \
      || echo "Tipo: firmado por CA -> se puede habilitar HSTS"
  fi
  grep -qE '^\s*add_header Strict-Transport-Security' deploy/nginx/dsms.conf 2>/dev/null \
    && echo "HSTS: ACTIVO en dsms.conf" || echo "HSTS: comentado en dsms.conf"

  titulo "Contenedores"
  if hay docker && docker info >/dev/null 2>&1; then
    docker compose ps -a 2>/dev/null || echo "(compose no devolvio nada)"
    echo
    echo "Volumenes del proyecto:"
    docker volume ls --filter name=molpack 2>/dev/null
  fi
fi

titulo "Puertos escuchando"
if hay ss; then
  ss -tlnp 2>/dev/null | awk 'NR==1 || /:(80|443|8000|5432)\s/'
else
  netstat -tlnp 2>/dev/null | grep -E ':(80|443|8000|5432)\s'
fi

titulo "Cortafuegos"
if hay ufw; then sudo -n ufw status 2>/dev/null || echo "ufw presente (requiere sudo para consultar)"; else echo "ufw no instalado"; fi

printf '\n=== Fin del diagnostico %s\n' "$(printf '%.0s-' $(seq 1 38))"
