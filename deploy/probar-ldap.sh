#!/usr/bin/env bash
# =============================================================
# Molpack DSMS — prueba de credenciales LDAP.
#
# SOLO LECTURA: no toca el .env ni reinicia nada. Sirve para saber si la
# cuenta de servicio funciona ANTES de configurar LDAP, porque al definir
# LDAP_SERVER los usuarios locales se apagan solos: si la cuenta no sirve,
# el sistema queda sin ningun login posible.
#
# Corre dentro del contenedor 'app', que es quien tiene que alcanzar el DC:
# misma libreria (ldap3) y misma posicion de red que en produccion.
#
#   bash deploy/probar-ldap.sh
#
# La contrasena se pide por teclado, no se guarda en disco ni en el historial.
# =============================================================
set -euo pipefail

DC_HOST="${DC_HOST:-MKSVX64WSN01.molpack.org}"
BIND_DN="${BIND_DN:-MKI000S016@molpack.org}"
BASE_DN="${BASE_DN:-DC=molpack,DC=org}"
# Usuario cualquiera del dominio para probar la busqueda. Por defecto la
# propia cuenta de servicio, que siempre existe.
USUARIO_PRUEBA="${USUARIO_PRUEBA:-MKI000S016}"

echo "DC      : $DC_HOST"
echo "Cuenta  : $BIND_DN"
echo "Base    : $BASE_DN"
echo "Buscando: $USUARIO_PRUEBA"
echo

read -r -s -p "Contrasena de la cuenta de servicio: " LDAP_PW
echo
echo

docker compose exec -T -e LDAP_TEST_PW="$LDAP_PW" \
                      -e DC_HOST="$DC_HOST" \
                      -e BIND_DN="$BIND_DN" \
                      -e BASE_DN="$BASE_DN" \
                      -e USUARIO_PRUEBA="$USUARIO_PRUEBA" \
                      app python - <<'PY'
import os
import sys

from ldap3 import ALL, SUBTREE, Connection, Server
from ldap3.core.exceptions import LDAPException

host = os.environ["DC_HOST"]
bind_dn = os.environ["BIND_DN"]
base_dn = os.environ["BASE_DN"]
usuario = os.environ["USUARIO_PRUEBA"]
pw = os.environ["LDAP_TEST_PW"]

url = f"ldaps://{host}:636"
print(f"1. Conectando a {url} ...")

try:
    server = Server(url, use_ssl=True, get_info=ALL)
    conn = Connection(server, user=bind_dn, password=pw, auto_bind=True)
except LDAPException as exc:
    print(f"   FALLO el bind: {exc}")
    print("\n   Causas tipicas: contrasena vencida o rotada, cuenta")
    print("   deshabilitada o bloqueada, o el formato del usuario.")
    sys.exit(1)

print("   OK  bind con la cuenta de servicio\n")

print(f"2. Buscando (sAMAccountName={usuario}) bajo {base_dn} ...")
conn.search(
    search_base=base_dn,
    search_filter=f"(sAMAccountName={usuario})",
    search_scope=SUBTREE,
    attributes=["cn", "displayName", "mail", "memberOf", "sAMAccountName"],
)

if not conn.entries:
    print("   El bind funciono pero la busqueda no devolvio nada.")
    print("   La cuenta puede no tener permiso de lectura sobre esa base.")
    conn.unbind()
    sys.exit(2)

e = conn.entries[0]
print("   OK  usuario encontrado")
print(f"       DN     : {e.entry_dn}")
print(f"       nombre : {e.displayName if 'displayName' in e else e.cn}")
print(f"       correo : {e.mail if 'mail' in e and e.mail else '(sin correo)'}")

grupos = [str(g) for g in e.memberOf.values] if "memberOf" in e else []
print(f"\n3. Grupos del usuario ({len(grupos)}):")
for g in grupos:
    print(f"       {g}")
if not grupos:
    print("       (ninguno visible)")
print("\n   Si mas adelante se quiere filtrar por grupo, LDAP_GRUPO_AUTORIZADO")
print("   tiene que ser uno de esos DN, copiado exactamente como aparece.")

conn.unbind()
print("\nRESULTADO: las credenciales sirven. Se puede configurar el .env.")
PY
