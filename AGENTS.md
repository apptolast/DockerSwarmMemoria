# AGENTS.md — Mapa de navegación para agentes de IA

> Punto de entrada para cualquier agente que trabaje en este repositorio.
> NO es una biblia de reglas: es un **mapa**. Lee solo lo que necesites,
> cuando lo necesites (divulgación progresiva) — mismo espíritu que el
> `AGENTS.md` de `TemplateSSDUncleBob`, del que este archivo es una
> adaptación.
>
> **Este archivo NO sustituye a `program.md`.** `program.md` es el contrato
> de comportamiento de producción de este bot (identidad, objetivo, ficheros
> mutables/protegidos, presupuesto, política de commit/revert, escalado a
> humano, criterio de éxito/parada) y tiene prioridad sobre cualquier
> instrucción de este archivo si hay conflicto. `AGENTS.md` añade la capa de
> gobernanza del arnés SDD alrededor de ese contrato ya existente. El
> razonamiento completo de esta adopción vive en
> `docs/adopcion-templatessd.md`.

## 1. Antes de empezar (obligatorio)

1. Lee `program.md` completo.
2. Lee `schema/graph-vocabulary.md` (el vocabulario de nodos/aristas que
   estructura lo que este bot extrae).
3. Lee las entradas más recientes de `memoria/logs/` para el estado real de
   las últimas ejecuciones del bot.
4. **2bis.** Sincroniza la memoria organizacional (paso no bloqueante):
   `scripts/sync-memoria.sh` (POSIX) o `pwsh scripts/sync-memoria.ps1`
   (Windows). Ver `CLAUDE.md` y `docs/adopcion-templatessd.md`.
5. Si tu tarea cambia el comportamiento del bot (`program.md`,
   `.github/workflows/daily-memory.yml` o `schema/graph-vocabulary.md`), lee
   `docs/adopcion-templatessd.md` antes de tocar nada: ahí está cómo (y
   cuándo) se aplica el pipeline del arnés — spec → Gherkin → TDD → judge →
   mutación — a este stack concreto, y qué partes no aplican y por qué.

## 2. Mapa del repositorio

| Archivo / carpeta | Qué contiene | Cuándo leerlo |
| --- | --- | --- |
| `program.md` | ⭐ El contrato de comportamiento del bot: objetivo, ficheros mutables/protegidos, presupuesto, escalado a humano. Fuente de verdad de producción. | Siempre, antes de cualquier cambio |
| `schema/graph-vocabulary.md` | Vocabulario de nodos/aristas (`Claim`, `Source`, `Artifact`, `AgentRun`…) que estructura lo que el bot extrae | Al tocar la extracción o el frontmatter propuesto |
| `.github/workflows/daily-memory.yml` | La única lógica ejecutable de este repo: workflow diario (bash puro + un paso agéntico `anthropics/claude-code-action` sin shell ni red) | Antes de cambiar el pipeline de extracción |
| `memoria/logs/` · `memoria/estado/` | Bitácora por ejecución y checkpoint incremental — estado mutable real del bot | Para contexto de ejecuciones recientes |
| `harness.config.json` (+ `harness.schema.json`) | ⭐ Comandos REALES de verificación de este stack, adaptados (no inventados) | Antes de tocar el arnés o de proponer un cambio al workflow |
| `CHECKPOINTS.md` | Criterios objetivos de "estado final correcto", adaptados a este stack (incluye por qué C6 no aplica y el estado real, no solo "no aplica", de C7 tanto para `daily-memory.yml` como para `scripts/rag`/`scripts/graph`) | Para auto-evaluarte al cerrar una sesión |
| `docs/adopcion-templatessd.md` | Cómo convive el arnés SDD con la lógica ya existente del bot; qué se adoptó, qué no se vendorizó y por qué | Antes de aplicar cualquier fase del pipeline a un cambio real |
| `scripts/sync-memoria.sh` (`.ps1`) | Sincroniza patrones validados de la organización en `.memoria-cache/` (paso 2bis, no bloqueante) | Al arrancar sesión |
| `CLAUDE.md` | Protocolo de arranque de Claude Code en este repo | Siempre, al empezar sesión con Claude Code |
| `scripts/rag/` (+ su propio `README.md`) | Pilot de recuperación léxica BM25 sobre el corpus de `DockerSwarmDocs` — manual, de solo lectura, cero dependencias externas. Ver `docs/adrs/0001-rag-pilot-lexical-retrieval.md` | Al tocar el pilot de RAG, o antes de decidir si algún día se conecta a producción |
| `scripts/graph/` (+ su propio `README.md`) | Pilot de grafo de conocimiento declarativo (Capa 1, `schema/graph-vocabulary.md` aplicado al frontmatter real) sobre el mismo corpus — manual, de solo lectura. Ver `docs/adrs/0002-graph-assembly-declarative-layer.md` | Al tocar el pilot de grafo, o antes de decidir si algún día se conecta a producción |
| `.github/workflows/rag-pilot.yml` | Workflow manual (`workflow_dispatch`), permisos de solo lectura, para consultar los dos pilots de arriba — deliberadamente separado de `daily-memory.yml`, no lo toca | Al ejecutar o modificar el pilot en CI |
| `docs/adrs/` | Decisiones del pilot de RAG + grafo (ADR-0001 BM25 vs. embeddings, ADR-0002 grafo declarativo) — mismo espíritu que las ADRs de `sistema-central-admin-servidor`, adaptado a este repo | Antes de modificar `scripts/rag/` o `scripts/graph/` |
| `rag/` | Artefactos generados por los dos pilots (`index.json`, `graph.json`) — nunca se editan a mano, no están comprometidos a git (ver `.gitignore`) | Nunca hace falta leerlo directamente; se regenera con los scripts de arriba |

**Sobre el pilot de RAG + grafo (`scripts/rag/`, `scripts/graph/`,
`.github/workflows/rag-pilot.yml`, `docs/adrs/`, `rag/`):** es aditivo y de
solo lectura — no modifica `program.md`, `schema/graph-vocabulary.md` ni
`.github/workflows/daily-memory.yml`, no escribe en
`DockerSwarmInfrastrcture` ni en `DockerSwarmDocs`, y no se dispara solo
(`workflow_dispatch` manual únicamente). Las reglas duras de la Sección 3 le
aplican igual que al resto del repo; se documenta aparte aquí solo porque es
la incorporación más reciente y todavía no forma parte del contrato de
producción del bot (`program.md`) — esa es una decisión futura y explícita
de quien mantiene el repo, no algo que este pilot de por sí implique.

## 3. Reglas duras (no negociables)

Heredadas de `program.md` — el arnés no las relaja, existe para que sea más
difícil violarlas por accidente:

- **`apptolast/DockerSwarmInfrastrcture` es de solo lectura, siempre.**
  Ninguna sesión hace commit, push ni PR ahí bajo ninguna circunstancia
  (`program.md` §3).
- **Nunca push directo a la rama por defecto de `apptolast/DockerSwarmDocs`.**
  Solo PRs en borrador, revisadas y fusionadas por un humano (`program.md`
  §3, §6, §7).
- **Nunca edites `astro.config.mjs` de `DockerSwarmDocs`.** Es de
  mantenimiento humano exclusivo (`program.md` §3).
- **Ningún dato factual sin fuente.** Lo no verificable se marca
  `TODO: verificar`, nunca se completa con un valor plausible (`program.md`
  §6, §7).
- **Cambiar `program.md` o `schema/graph-vocabulary.md` es decisión de quien
  mantiene el repo**, no algo que un agente module en tiempo de ejecución
  (`program.md` §7).
- **Este repo no despliega, no publica, no toca DNS/Traefik/GitHub Pages**
  bajo ninguna circunstancia (`program.md` §2, §3).

Añadidas por la adopción del arnés (razonamiento completo en
`docs/adopcion-templatessd.md`):

- **No inventes comandos de verificación.** `harness.config.json` declara
  los reales de este stack (`actionlint`). Si algo no tiene equivalente real
  para este stack (la prueba de mutación), se marca explícitamente
  "no aplica" con su motivo — nunca se simula con un script inventado solo
  para rellenar el campo.
- **Un cambio estructural al bot (nuevo campo de frontmatter, nueva regla de
  presupuesto, nuevo paso del workflow) se conversa antes de editar
  `program.md` directamente** — el espíritu de `spec_partner`, y ya lo exigía
  `program.md` §7 para cambios de contrato. Los cambios lo bastante grandes
  como para merecerlo pueden formalizarse con Gherkin
  (`features/<name>.feature`, tomado de `TemplateSSDUncleBob` en el momento
  en que haga falta); los cambios pequeños siguen su cauce actual — edición
  directa + PR revisada por humano —, que es el proceso real que ya usa este
  repo.
- **"El review es el juego entero" ya es la norma de este repo para cambios
  de comportamiento**: los cambios a `program.md`, al workflow o al schema
  llegaron por PR revisada por una persona (ver en `git log` los commits con
  PR asociado, p. ej. los squash-merge etiquetados `(#1)`-`(#4)`). Las
  entradas rutinarias `chore(memoria): registrar ejecución...` son la
  excepción explícita y documentada: push directo y automático del propio
  bot sobre su propio estado mutable (`memoria/`), permitido por
  `program.md` §3 — no son "cambios de comportamiento" y no pasan por PR. El
  arnés nombra y refuerza la disciplina de review sobre lo primero; no
  pretende que lo segundo también deba pasar por ahí.

## 4. Qué NO vendoriza esta adopción (y por qué)

Este repo no copia mecánicamente todo `TemplateSSDUncleBob`. No hay
`.harness/` (motor Node), `bin/harness`, `init.sh`/`init.ps1`,
`.claude/agents/*.md`, `feature_list.json`, `project-spec.md`, `features/`,
`progress/`, ni el bot de auto-evolución del arnés
(`autonomous-evolve.yml`/`AUTONOMOUS.md`). Es una decisión explícita, no un
olvido: el razonamiento completo, archivo por archivo, está en
`docs/adopcion-templatessd.md`. En una frase — este repo ya es un bot de
producción narrow-scope con su propio contrato (`program.md`) y su propia
disciplina real de PR-revisada-por-humano; el arnés se añade como capa de
gobernanza y verificación alrededor de eso, no como un refactor hacia
"proyecto con `src/` desarrollado feature a feature por TDD", que no es lo
que este repo es ni lo que `program.md` §1 dice que deba llegar a ser.

## 5. Si te bloqueas

- Relee `program.md`: tiene prioridad sobre cualquier otro documento de este
  repositorio, incluido este `AGENTS.md`.
- Si una herramienta no hace lo que esperas, **no inventes un workaround**:
  documenta el bloqueo (en `memoria/logs/` si es una ejecución del bot, o en
  tu respuesta si es una sesión interactiva) y para.
