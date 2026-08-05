# Instrucciones para Claude — DockerSwarmMemoria (arnés TemplateSSDUncleBob)

> Este archivo se carga automáticamente al inicio de cada sesión de Claude
> Code en este repositorio.
>
> `DockerSwarmMemoria` es un bot narrow-scope de memoria organizacional.
> `program.md` es su contrato de comportamiento de **producción** y tiene
> prioridad sobre cualquier instrucción de este archivo si hay conflicto.
> Este `CLAUDE.md` añade la capa de gobernanza de `TemplateSSDUncleBob`
> alrededor de ese contrato ya existente; no lo sustituye ni lo reescribe.
> Ver `docs/adopcion-templatessd.md` para el razonamiento completo de esta
> adopción y `AGENTS.md` para el mapa de navegación.

## Qué eres en este repositorio

No hay un subagente `craftsman_lead` vendorizado aquí (ver
`docs/adopcion-templatessd.md`, "Qué no se vendoriza"): este repo no adoptó
mecánicamente los 9 roles de `.claude/agents/` de la plantilla porque no
desarrolla código de aplicación en `src/` por TDD — su única lógica
ejecutable es `.github/workflows/daily-memory.yml`, gobernada por el
contrato de `program.md`. Aun así, trabaja con el mismo espíritu que
`craftsman_lead`: **no implementes a lo loco**, demuestra que algo funciona
en vez de afirmarlo, y no saltes la puerta de revisión humana sobre ningún
PR que cambie el comportamiento del bot — esa puerta ya existe y es real en
este repo (ver en `git log` los cambios a `program.md`/al workflow fusionados
vía PR, p. ej. `(#1)`-`(#4)`). Las entradas automáticas
`chore(memoria): registrar ejecución...` son la excepción explícita: push
directo del propio bot sobre su propio estado mutable, permitido por
`program.md` §3 — no un cambio de comportamiento que debiera pasar por PR.

## Protocolo de arranque

1. Lee `program.md` completo. Es el contrato de comportamiento del bot:
   objetivo, ficheros mutables/protegidos, presupuesto, política de
   commit/revert, escalado a humano. Tiene prioridad sobre cualquier otra
   instrucción si hay conflicto.
2. Lee `AGENTS.md` para el mapa de navegación y las reglas duras heredadas
   de `program.md`.
3. Lee las entradas más recientes de `memoria/logs/` para el estado real de
   las últimas ejecuciones del bot.
4. **2bis. Sincroniza la memoria organizacional** (paso no bloqueante,
   heredado tal cual de `TemplateSSDUncleBob`):

   ```bash
   scripts/sync-memoria.sh        # POSIX / macOS / Linux
   pwsh scripts/sync-memoria.ps1  # Windows
   ```

   Si `.memoria-cache/patterns/<categoría>/` trae patrones relevantes a tu
   tarea (por ejemplo `tooling`, `arquitectura`, `testing`), revísalos antes
   de diseñar desde cero, respetando su "Cuándo NO aplica". El script clona
   `Cenit-Digital/SistemaDeMemoriaUncleBob` (repo privado); si esta sesión no
   tiene acceso a esa organización, el script avisa y termina en 0 sin
   bloquear nada — mismo comportamiento no bloqueante que en la plantilla
   original. Ver `docs/adopcion-templatessd.md`, sección "Memoria
   organizacional: productor y ¿también consumidor?", para una posibilidad
   relacionada con este mismo mecanismo que todavía NO está implementada.
5. Si tu tarea toca `.github/workflows/daily-memory.yml`, `program.md` o
   `schema/graph-vocabulary.md`: lee `docs/adopcion-templatessd.md` primero.
   Ahí está cómo (y cuándo) aplica el pipeline spec → Gherkin → TDD → judge →
   mutación de la plantilla a este stack concreto, y por qué la mutación
   está marcada explícitamente "no aplica" en `harness.config.json`.

## Comandos de verificación de este stack

Declarados en `harness.config.json` (no hay `bin/harness` vendorizado en
este repo — ver `docs/adopcion-templatessd.md`). Para
`.github/workflows/daily-memory.yml` (producción, YAML + bash embebido), el
comando real de verificación sigue siendo:

```bash
actionlint    # valida .github/workflows/daily-memory.yml (YAML + bash embebido)
```

Antes de proponer un cambio al workflow, confirma que `actionlint` queda
limpio (0 warnings — incluye shellcheck sobre cada bloque `run:`).

Desde el pilot de RAG + grafo (`scripts/rag/`, `scripts/graph/`), este repo
SÍ tiene código Python real y SÍ tiene prueba de mutación real — la frase
"no hay `pytest` ni prueba de mutación porque no hay `src/` en un lenguaje
de propósito general" ya no es cierta para esas dos carpetas (sigue siendo
cierta para `daily-memory.yml`, que no cambia). Comandos reales:

```bash
python3 scripts/rag/test_calibration.py     # regresión de calibración BM25
python3 scripts/graph/test_graph.py          # regresión del grafo declarativo
ruff check scripts/rag/ scripts/graph/ scripts/mutate.py   # lint

# mutación (uno por fichero — no hay un único comando, ver harness.config.json → commands.mutate):
python3 scripts/mutate.py scripts/rag/query.py --test-cmd "python3 scripts/rag/test_calibration.py"
python3 scripts/mutate.py scripts/graph/query_graph.py --test-cmd "python3 scripts/graph/test_graph.py"
```

Detalle completo (por qué `scripts/mutate.py` y no `mutmut`, resultados,
qué supervivientes se aceptan y por qué) en `CHECKPOINTS.md` C7 y en
`docs/adrs/0001-rag-pilot-lexical-retrieval.md` /
`docs/adrs/0002-graph-assembly-declarative-layer.md`, sección "Prueba de
mutación" de cada una.

## Reglas duras (heredadas de `program.md`, no negociables)

- `apptolast/DockerSwarmInfrastrcture` es de **solo lectura**, siempre.
- Nunca push directo a la rama por defecto de `apptolast/DockerSwarmDocs`;
  solo PRs en borrador, revisadas por un humano.
- Nunca edites `astro.config.mjs` de `DockerSwarmDocs`.
- Ningún dato factual sin fuente verificable (`TODO: verificar` si no se
  puede confirmar contra `DockerSwarmInfrastrcture`).
- Este repo no despliega, no publica, no toca DNS/Traefik/GitHub Pages.

## Cuándo NO aplica ninguna disciplina de orquestación

- Preguntas conceptuales o de exploración del repo (lectura pura) → responde
  directamente, sin más ceremonia.
- Cambios de documentación que no alteran `program.md`, el workflow ni el
  schema → puedes editarlos tú mismo, siempre con PR y revisión humana igual
  que el resto de cambios de este repo.
