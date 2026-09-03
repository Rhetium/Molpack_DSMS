# Direccionamiento de Docker en el servidor

## El problema

Docker, sin configurar, se asigna direcciones asi:

| Elemento | Rango por defecto |
|---|---|
| `docker0` (bridge por defecto) | `172.17.0.0/16` |
| Redes que crea Compose | pool de `172.17.0.0/16` a `172.31.0.0/16` |

La red de Molpack usa, entre otras, `172.17.0.0/16`, `172.20.0.0/16`,
`172.21.0.0/16` y `192.168.22.0/24` — las cuatro observadas en las rutas que
empuja el tunel "VPN MOLANCA".

Los tres rangos `172.x` **caen dentro del pool por defecto de Docker**. Cuando
Docker instancia una red ahi, el servidor pasa a resolver esas direcciones por
un bridge local en vez de por la LAN corporativa. El resultado es que el host
deja de alcanzar la red de la empresa — y deja de ser alcanzable. En el primer
intento de despliegue esto corto el acceso SSH al servidor.

## El plan de direcciones

Todo fuera del espacio `172.16-172.31` y lejos de `192.168.22.0/24`:

| Uso | Subred |
|---|---|
| Red de este proyecto (fija en `docker-compose.yml`) | `192.168.240.0/24` |
| `docker0`, bridge por defecto (`bip`) | `192.168.241.0/24` |
| Pool para redes que Docker cree por su cuenta | `192.168.244.0/21`, en /24 |

Confirmar estos valores con TI contra el plan de direccionamiento de Molpack
antes de aplicarlos: aca solo se conocen las cuatro redes vistas en el tunel,
no el mapa completo.

## Aplicar (requiere root)

`dsmsadm` no tiene sudo, asi que esta parte la hace TI:

```bash
sudo cp deploy/daemon.json.ejemplo /etc/docker/daemon.json
sudo systemctl restart docker
```

Verificar que `docker0` quedo en el rango nuevo:

```bash
ip -4 addr show docker0
docker network inspect bridge -f '{{range .IPAM.Config}}{{.Subnet}}{{end}}'
```

## Recuperar el servidor si vuelve a quedar incomunicado

Desde consola local o iLO, no por SSH (que es justamente lo que se pierde):

```bash
cd ~/Molpack_DSMS
docker compose --profile tls down
docker network prune -f
```

Eso libera las redes en conflicto y devuelve la conectividad. Recien despues
conviene aplicar el `daemon.json` y volver a desplegar.
