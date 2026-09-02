# Certificados TLS

nginx espera dos archivos en este directorio:

| Archivo | Qué es |
|---|---|
| `dsms.crt` | Certificado del servidor. Si lo firma la CA interna, concatenar debajo la cadena de la CA. |
| `dsms.key` | Clave privada, sin passphrase (nginx arranca desatendido). Permisos `600`. |

Ninguno de los dos se versiona: `.gitignore` excluye todo este directorio salvo
este README. La clave privada se genera en la VM y no sale de ahí.

Para generarlos, desde la raíz del repo en la VM:

```bash
./deploy/generar-certificado.sh csr           # entregar dsms.csr a TI
./deploy/generar-certificado.sh autofirmado   # provisional, mientras tanto
```

El detalle está en [docs/DESPLIEGUE_DOCKER.md](../../docs/DESPLIEGUE_DOCKER.md).
