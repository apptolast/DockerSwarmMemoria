# sync-memoria.ps1 — Sincroniza la memoria organizacional de Cénit Digital
# (patrones validados) en .memoria-cache\. Paso 2bis del Protocolo de
# arranque (CLAUDE.md). Ver docs/memoria-organizacional.md.
#
# NO bloqueante por diseño: cualquier fallo (sin red, sin git/gh, repo
# privado inaccesible) avisa y termina en 0 — el arranque nunca se rompe.
# Gemelo Windows de scripts/sync-memoria.sh, misma convención que
# init.sh / init.ps1.
#
# Nota: sin caracteres tipo guion largo dentro de las cadenas — Windows
# PowerShell 5.1 lee UTF-8 sin BOM como ANSI y esos bytes rompen el parseo
# (misma convención que init.ps1 / bin/harness.ps1).

$repoUrl = 'https://github.com/Cenit-Digital/SistemaDeMemoriaUncleBob.git'

# Caché anclada a la raíz del proyecto (junto a CLAUDE.md), no al cwd: el
# script debe poder invocarse desde cualquier subdirectorio.
$root = Split-Path -Parent $PSScriptRoot
$dest = Join-Path $root '.memoria-cache'

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
  Write-Warning "'git' no está disponible: sigo sin memoria organizacional."
  exit 0
}

$credArgs = @()
if (Get-Command gh -ErrorAction SilentlyContinue) {
  # El primer -c vacía la lista de helpers heredados; el segundo delega en gh.
  $credArgs = @('-c', 'credential.helper=', '-c', 'credential.helper=!gh auth git-credential')
}

if (Test-Path $dest) { Remove-Item -Recurse -Force $dest }

# GIT_TERMINAL_PROMPT=0 + GIT_ASKPASS vacio + credential.interactive=false:
# sin credenciales validas el clone FALLA rapido en vez de pedirlas (prompt
# de consola o dialogo de Git Credential Manager). Se restauran al salir.
$oldPrompt = $env:GIT_TERMINAL_PROMPT
$oldAskpass = $env:GIT_ASKPASS
$env:GIT_TERMINAL_PROMPT = '0'
$env:GIT_ASKPASS = ''
try {
  git @credArgs -c credential.interactive=false clone --depth 1 --quiet $repoUrl $dest 2>$null
} finally {
  if ($null -eq $oldPrompt) { Remove-Item Env:GIT_TERMINAL_PROMPT -ErrorAction SilentlyContinue } else { $env:GIT_TERMINAL_PROMPT = $oldPrompt }
  if ($null -eq $oldAskpass) { Remove-Item Env:GIT_ASKPASS -ErrorAction SilentlyContinue } else { $env:GIT_ASKPASS = $oldAskpass }
}

if ($LASTEXITCODE -eq 0 -and (Test-Path $dest)) {
  $gitDir = Join-Path $dest '.git'
  if (Test-Path $gitDir) { Remove-Item -Recurse -Force $gitDir }
  $n = @(Get-ChildItem -Path (Join-Path $dest 'patterns') -Recurse -Filter '*.md' -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -ne 'README.md' }).Count
  Write-Output "Memoria organizacional sincronizada en .memoria-cache\patterns\ ($n patrones)."
} else {
  if (Test-Path $dest) { Remove-Item -Recurse -Force $dest }
  Write-Warning 'Sin red, sin permiso o repo inaccesible: sigo sin memoria organizacional.'
}
exit 0
