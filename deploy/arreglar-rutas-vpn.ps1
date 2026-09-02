# =============================================================
# Convivencia Surfshark + FortiClient "VPN MOLANCA" (IPsec).
#
#   Ejecutar en PowerShell COMO ADMINISTRADOR, con Surfshark
#   conectado y ANTES de conectar el tunel MOLANCA:
#     powershell -ExecutionPolicy Bypass -File deploy\arreglar-rutas-vpn.ps1
#
# El problema: FortiClient agrega una ruta /32 hacia su gateway
# (maplantavln.molpack.net) para que el handshake no entre en su
# propio tunel, pero Windows la engancha al adaptador de Surfshark,
# que es donde apunta la ruta por defecto efectiva. El IKE sale
# entonces por el nodo de Surfshark: IKEv1 agresivo + NAT-T sobre
# otro NAT arma el tunel y lo pierde en ~15s por DPD.
#
# La solucion: forzar ese /32 por la interfaz fisica. Al ser el
# prefijo mas largo, gana sobre el 0.0.0.0/1 de Surfshark sin
# tocar el resto del trafico, que sigue saliendo por la VPN.
#
# Las subredes corporativas NO se tocan: las instala FortiClient
# en su propio adaptador al conectar, y una /16 le gana sola al /1.
#
# Nada se crea con -p: todo se limpia al reiniciar.
# =============================================================

$ErrorActionPreference = 'Continue'

$id = [Security.Principal.WindowsIdentity]::GetCurrent()
$pr = New-Object Security.Principal.WindowsPrincipal($id)
if (-not $pr.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "ERROR: hay que ejecutarlo como administrador." -ForegroundColor Red
    exit 1
}

# --- Respaldo ------------------------------------------------
$bk = "$env:TEMP\rutas_backup_$(Get-Date -Format yyyyMMdd_HHmmss).txt"
route print -4 | Out-File -FilePath $bk -Encoding utf8
Write-Host "Respaldo de rutas: $bk" -ForegroundColor Cyan

# --- Gateway fisico (el de la red real, no el de una VPN) -----
# Se descarta cualquier next hop que caiga en un adaptador de tunel.
$fisica = Get-NetRoute -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue |
          Where-Object { $_.NextHop -ne '0.0.0.0' } |
          Sort-Object RouteMetric | Select-Object -First 1
if (-not $fisica) {
    Write-Host "ERROR: no se encontro gateway fisico." -ForegroundColor Red
    exit 1
}
$gw    = $fisica.NextHop
$gwIdx = $fisica.ifIndex
Write-Host "Gateway fisico: $gw (ifIndex $gwIdx)" -ForegroundColor Cyan

# --- Fijar el gateway de MOLANCA por la interfaz fisica -------
# Se resuelve en cada corrida por si Molpack cambia la IP publica.
$fgHost = 'maplantavln.molpack.net'
$ips = (Resolve-DnsName -Name $fgHost -Type A -ErrorAction SilentlyContinue |
        Where-Object { $_.IPAddress }).IPAddress

if (-not $ips) {
    Write-Host "ERROR: no se pudo resolver $fgHost." -ForegroundColor Red
    Write-Host "  Surfshark puede estar filtrando el DNS. Probar con la IP conocida:" -ForegroundColor Yellow
    Write-Host "  route add 200.74.225.142 mask 255.255.255.255 $gw metric 1"
    exit 1
}

Write-Host "`nFijando $fgHost por la interfaz fisica..."
foreach ($ip in $ips) {
    # Borra la version que quedo colgada del adaptador de Surfshark.
    route delete $ip 2>&1 | Out-Null
    $r = route add $ip mask 255.255.255.255 $gw metric 1 if $gwIdx 2>&1
    Write-Host "  $ip -> $gw (if $gwIdx)  $r" -ForegroundColor Green
}

# --- Verificacion --------------------------------------------
Write-Host "`n== Por donde sale ahora el handshake IKE ==" -ForegroundColor Cyan
foreach ($ip in $ips) {
    Find-NetRoute -RemoteIPAddress $ip |
        Where-Object { $_.DestinationPrefix } |
        Select-Object InterfaceAlias, DestinationPrefix, NextHop |
        Format-Table -AutoSize
}
Write-Host "Debe decir Wi-Fi (o Ethernet), NO SurfsharkWireGuard." -ForegroundColor Yellow
Write-Host "`nAhora conecta 'VPN MOLANCA' en FortiClient y verifica:" -ForegroundColor Yellow
Write-Host "  Get-NetAdapter -InterfaceIndex 17 | Select Name,Status"
Write-Host "  Find-NetRoute -RemoteIPAddress 172.21.5.74"
Write-Host "  Test-NetConnection 172.21.5.74 -Port 22"
