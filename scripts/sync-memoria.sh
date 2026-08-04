#!/usr/bin/env bash
# sync-memoria.sh — Sincroniza la memoria organizacional de Cénit Digital
# (patrones validados) en .memoria-cache/. Paso 2bis del Protocolo de
# arranque (CLAUDE.md). Ver docs/memoria-organizacional.md.
#
# NO bloqueante por diseño: sin red, sin `git`/`gh`, o sin acceso al repo
# (es privado), avisa y termina en 0 — el arranque del arnés nunca se rompe
# por esto. Clona por HTTPS con `gh auth git-credential` como helper
# explícito: funciona con cualquier `gh auth login`, sin depender de alias
# SSH ni credential helpers de la máquina.
set -u

REPO_URL="https://github.com/Cenit-Digital/SistemaDeMemoriaUncleBob.git"

# Caché anclada a la raíz del proyecto (junto a CLAUDE.md), no al cwd: el
# script debe poder invocarse desde cualquier subdirectorio.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" || exit 0
DEST="$ROOT/.memoria-cache"

if ! command -v git >/dev/null 2>&1; then
  echo "Aviso: 'git' no está disponible — sigo sin memoria organizacional." >&2
  exit 0
fi

CRED_ARGS=()
if command -v gh >/dev/null 2>&1; then
  # El primer -c vacía la lista de helpers heredados; el segundo delega en gh.
  CRED_ARGS=(-c credential.helper= -c "credential.helper=!gh auth git-credential")
fi

rm -rf "$DEST"
# GIT_TERMINAL_PROMPT=0 + GIT_ASKPASS= + credential.interactive=false: sin
# credenciales válidas el clone FALLA rápido en vez de pedirlas (prompt de
# tty o diálogo de Git Credential Manager) — este paso jamás debe bloquear.
if GIT_TERMINAL_PROMPT=0 GIT_ASKPASS='' \
   git ${CRED_ARGS[@]+"${CRED_ARGS[@]}"} -c credential.interactive=false \
   clone --depth 1 --quiet "$REPO_URL" "$DEST" 2>/dev/null; then
  rm -rf "$DEST/.git"
  n="$(find "$DEST/patterns" -type f -name '*.md' ! -name 'README.md' 2>/dev/null | wc -l | tr -d '[:space:]')"
  echo "Memoria organizacional sincronizada en .memoria-cache/patterns/ (${n:-0} patrones)."
else
  rm -rf "$DEST"
  echo "Aviso: sin red, sin permiso o repo inaccesible — sigo sin memoria organizacional." >&2
fi
exit 0
