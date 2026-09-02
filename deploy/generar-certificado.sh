#!/usr/bin/env bash
# =============================================================
# Molpack DSMS — certificado TLS para mksvx64lnn10.molpack.org
#
#   ./deploy/generar-certificado.sh csr           # camino recomendado
#   ./deploy/generar-certificado.sh autofirmado   # provisional
#
# "csr" genera la clave privada y una solicitud de firma para entregar a TI:
# el certificado lo emite la CA interna de Molpack (AD CS) y entonces los
# equipos del dominio ya confian en el, sin avisos en el navegador.
#
# "autofirmado" produce un certificado que sirve igual para cifrar, pero que
# cada navegador marcara como no confiable hasta que TI distribuya la CA. Usarlo
# solo para no frenar las pruebas mientras se tramita el otro.
# =============================================================
set -euo pipefail

FQDN="${FQDN:-mksvx64lnn10.molpack.org}"
HOSTNAME_CORTO="${HOSTNAME_CORTO:-MKSVX64LNN10}"
IP="${IP:-172.21.5.74}"
DIAS="${DIAS:-825}"

DESTINO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/certs"
mkdir -p "$DESTINO"

# Los SAN son lo que el navegador valida; el CN ya no se mira. Van los tres
# nombres porque al sistema se entra indistintamente por FQDN, por nombre corto
# o por IP, y un nombre ausente aca da error de certificado.
CONFIG="$(mktemp)"
trap 'rm -f "$CONFIG"' EXIT
cat > "$CONFIG" <<EOF
[req]
distinguished_name = dn
req_extensions     = ext
prompt             = no

[dn]
C  = VE
O  = Molpack
OU = Tecnologia de la Informacion
CN = $FQDN

[ext]
subjectAltName   = DNS:$FQDN, DNS:$HOSTNAME_CORTO, IP:$IP
keyUsage         = critical, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
EOF

case "${1:-}" in
  csr)
    # Si ya existe la clave (p.ej. la que dejo el autofirmado) se reutiliza.
    # Asi el certificado que devuelva TI encaja con la clave ya instalada y
    # el reemplazo es solo el .crt, sin regenerar nada mas.
    if [[ -f "$DESTINO/dsms.key" ]]; then
      echo "Reutilizando clave existente: $DESTINO/dsms.key"
      openssl req -new \
        -key "$DESTINO/dsms.key" \
        -out "$DESTINO/dsms.csr" \
        -config "$CONFIG"
    else
      openssl req -new -newkey rsa:2048 -nodes \
        -keyout "$DESTINO/dsms.key" \
        -out    "$DESTINO/dsms.csr" \
        -config "$CONFIG"
    fi
    chmod 600 "$DESTINO/dsms.key"
    echo
    echo "Clave privada : $DESTINO/dsms.key   (NO se entrega a nadie)"
    echo "Solicitud     : $DESTINO/dsms.csr   (esto es lo que va a TI)"
    echo
    echo "TI debe devolver el certificado firmado. Guardarlo como"
    echo "$DESTINO/dsms.crt, con la cadena de la CA concatenada debajo, y"
    echo "reiniciar nginx:  docker compose --profile tls restart nginx"
    ;;

  autofirmado)
    # Igual que en csr: si ya hay clave se conserva, para no invalidar un
    # CSR que pueda estar en tramite con TI.
    if [[ -f "$DESTINO/dsms.key" ]]; then
      echo "Reutilizando clave existente: $DESTINO/dsms.key"
      openssl req -x509 -new -sha256 \
        -days "$DIAS" \
        -key "$DESTINO/dsms.key" \
        -out "$DESTINO/dsms.crt" \
        -config "$CONFIG" -extensions ext
    else
      openssl req -x509 -new -newkey rsa:2048 -nodes -sha256 \
        -days "$DIAS" \
        -keyout "$DESTINO/dsms.key" \
        -out    "$DESTINO/dsms.crt" \
        -config "$CONFIG" -extensions ext
    fi
    chmod 600 "$DESTINO/dsms.key"
    echo
    echo "Certificado autofirmado en $DESTINO (valido $DIAS dias)."
    echo "Los navegadores mostraran un aviso hasta que TI distribuya la CA."
    echo "Dejar HSTS comentado en deploy/nginx/dsms.conf mientras sea este."
    ;;

  *)
    echo "Uso: $0 {csr|autofirmado}" >&2
    exit 1
    ;;
esac
