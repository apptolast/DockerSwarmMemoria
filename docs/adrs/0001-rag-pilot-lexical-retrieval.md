---
title: "ADR-0001: Recuperación léxica (BM25) versionada en git como pilot de RAG para DockerSwarmMemoria"
status: accepted
date: 2026-08-04
owner: pablo
supersedes: null
superseded-by: null
tags: [architecture, rag, ai, pilot]
---

# ADR-0001: Recuperación léxica (BM25) versionada en git como pilot de RAG

## Status

**Accepted** — 2026-08-04. Pilot, no producción: no está conectado a
`daily-memory.yml` (ver "Qué no incluye esta primera vuelta").

## Context

El propietario (Pablo) pidió preparar "la memoria" (`DockerSwarmMemoria`)
para RAG, como prueba de concepto, antes de decidir si el patrón se
generaliza a la plantilla de `Cenit-Digital`. Pidió explícitamente
investigación previa y "no inventar nada".

`apptolast/sistema-central-admin-servidor` ya tiene un stack RAG completo,
aceptado y documentado (su ADR-0003: R2R (SciPhi-AI) + Spring AI 1.1 +
PostgreSQL/pgvector + OpenAI `text-embedding-3-large`; su ADR-0004: grafo de
conocimiento en 3 capas + 5 capas anti-alucinación). Ese stack está diseñado
para el clúster **Kubernetes** de ese proyecto. `DockerSwarmInfrastrcture` —
la infraestructura real que `DockerSwarmMemoria` documenta — es **Docker
Swarm**, no Kubernetes, y `DockerSwarmMemoria` no tiene hoy ningún servidor
propio: corre solo como GitHub Actions efímero (ver `program.md`, §5), sin
base de datos ni proceso persistente de ningún tipo.

El corpus a indexar (`apptolast/DockerSwarmDocs`) tiene, a fecha de este
ADR, 9 páginas / 75 chunks tras trocear por sección H2 (~96 tokens/chunk de
media) — verificado ejecutando `scripts/rag/build_index.py` contra el
corpus real, commit `8eb4497`.

## Investigación realizada

Se investigó (documentación oficial, no solo memoria de entrenamiento) antes
de decidir:

- **R2R (SciPhi-AI)**: última release `3.6.6` (17 ago 2025, vía la API JSON
  de PyPI); sin releases nuevas desde entonces hasta la fecha de este ADR
  (ago 2026) pese a presentarse como "SoTA production-ready" — señal de
  desarrollo activo más lento de lo que su propio README sugiere. Su propia
  documentación oficial confirma que PostgreSQL es obligatorio en todos sus
  modos ("R2R uses PostgreSQL as the sole provider", <https://r2r-docs.sciphi.ai/documentation/configuration/postgres>)
  y que el modo "full" añade además Hatchet + RabbitMQ (issue pública:
  <https://github.com/SciPhi-AI/R2R/issues/2146>). Es un stack de 4+
  contenedores para un corpus de 9-15 documentos.
- **pgvector**: última release confirmada `0.8.2` (26 feb 2026, anuncio
  oficial de PostgreSQL, <https://www.postgresql.org/about/news/pgvector-082-released-3245>)
  — activamente mantenido, pero exige una instancia PostgreSQL nueva que
  hoy no existe para este proyecto, que habría que aprovisionar y mantener
  indefinidamente para un corpus que cabe entero en memoria.
- **sqlite-vec**: última release `~v0.1.9` (mar 2026,
  <https://github.com/asg017/sqlite-vec/releases>), preversión 1.0, con un
  hiato de mantenimiento reconocido por su propio autor — riesgo de
  bus-factor de un solo mantenedor. El sucesor propio de SQLite, "Vec1",
  también preversión 1.0 y su propia documentación declara "testing is
  insufficient" (<https://sqlite.org/vec1>).
- **Fuerza bruta (similitud coseno/BM25 en memoria, sin base de datos
  vectorial)**: evidencia neutral y fechada, no de un vendor de bases de
  datos vectoriales: Doug Turnbull, "Just brute force your embeddings" (29
  jul 2026, <https://softwaredoug.com/blog/2026/07/29/just-brute-force-embeddings>),
  con benchmarks propios mostrando fuerza bruta cómoda hasta ~1M vectores de
  384 dimensiones en hardware ordinario. Este corpus está 4-5 órdenes de
  magnitud por debajo de ese punto de fricción.
- **Modelos de embeddings locales (CPU, sin API de pago)**: se intentó
  descargar `sentence-transformers/all-MiniLM-L6-v2` desde Hugging Face Hub
  para probarlo en este mismo sandbox — **bloqueado por la política de red
  del sandbox de esta sesión** (`ProxyError('403 Forbidden')`; el mismo
  bloqueo se confirmó independientemente al intentar `go install` de
  `actionlint` contra `proxy.golang.org`/`sum.golang.org`/`golang.org` — ver
  `docs/adopcion-templatessd.md` de este repo y el propio historial de esta
  sesión). GitHub Actions (donde correría esto en producción) no tiene esa
  restricción — los runners `ubuntu-24.04` tienen acceso de red completo —
  pero este ADR documenta con honestidad que **el pilot no pudo verificarse
  end-to-end con un modelo neuronal en este entorno de desarrollo concreto**,
  así que no se puede afirmar que ese camino esté probado, solo que está
  disponible.
- **OpenAI `text-embedding-3-small`/`-large`**: precios confirmados vigentes
  ($0.02 / $0.13 por millón de tokens de entrada,
  <https://developers.openai.com/api/docs/models/text-embedding-3-small>,
  `.../text-embedding-3-large`) — coste trivial para este corpus, pero
  requiere una API key y facturación nuevas que hoy no existen para este
  repo (los secrets configurados son `DOCKERSWARM_BOT_PAT` y
  `CLAUDE_CODE_OAUTH_TOKEN`, ninguno de OpenAI).
- **Validación de citas / anti-alucinación**: la referencia oficial más
  clara es la Citations API de Anthropic
  (<https://platform.claude.com/docs/en/build-with-claude/citations>): las
  citas se extraen del texto fuente indexado en vez de generarse libremente,
  lo que impide que se inventen. El patrón aplicado en `query.py` (umbral +
  cita obligatoria + verificación programática de que la cita resuelve a un
  chunk real) sigue la misma idea, adaptado a un script propio.

## Decision

**Recuperación léxica BM25, en memoria, sobre un índice JSON versionable en
git** (`scripts/rag/build_index.py` + `scripts/rag/query.py`), sin base de
datos vectorial, sin modelo de embeddings, sin servicio nuevo de ningún
tipo. Cero dependencias externas — solo la librería estándar de Python 3
(ya disponible en los runners `ubuntu-24.04` de GitHub Actions).

Se añade además un workflow separado, manual (`workflow_dispatch`),
`(.github/workflows/rag-pilot.yml`, con permiso `contents: read` únicamente
— no puede escribir nada, en ningún repo, bajo ninguna circunstancia. No
toca `daily-memory.yml`.

### Por qué léxico y no semántico en esta primera vuelta

1. **Proporción al corpus real** (75 chunks): la propia evidencia de
   Turnbull citada arriba muestra que la fuerza bruta no empieza a sufrir
   hasta ~1M vectores. Cualquier motor vectorial dedicado sería
   desproporcionado.
2. **Cero infraestructura nueva que mantener**: coherente con que este
   repo hoy no tiene ningún servidor propio (`program.md`, §1: "No es un
   despliegue, un gestor de infraestructura").
3. **No se pudo verificar honestamente un modelo neuronal en este sandbox**
   (ver "Investigación realizada" arriba) — se prefirió no enviar un pilot
   sin verificar de verdad de punta a punta antes que fingir una prueba que
   no se hizo.
4. **Corpus técnico con identificadores exactos** (hostnames, nombres de
   servicio, flags): la coincidencia léxica exacta es, en este dominio
   concreto, una base defendible y no claramente inferior a la semántica
   para las preguntas típicas de este corpus (factuales, con nombres
   propios).

### Calibración del umbral

Contra el corpus real (commit `8eb4497`, 75 chunks), 7 preguntas de prueba
(`scripts/rag/test_calibration.py`) fijan dos guardas independientes:

- `DEFAULT_THRESHOLD = 6.0`: por debajo del score más bajo observado entre
  preguntas dentro de alcance (10.24) y por encima del score más alto
  observado en una pregunta fuera de alcance con un término incidental
  coincidente (3.47 — ver "el caso 'pablo'" abajo).
- `MIN_MATCHED_TERMS = 2`: ningún resultado se acepta si coincide en menos
  de 2 términos distintos de la consulta.

**El caso "pablo"** (hallazgo real, no hipotético): la pregunta "¿Qué modelo
de coche conduce Pablo y de qué color es?" —completamente fuera de
alcance— obtuvo un score BM25 de 3.47 en un chunk sobre Traefik, porque la
palabra "pablo" aparece una vez de forma incidental ahí y su IDF es alto
(término raro). Un único término raro coincidente puede superar un umbral
de score razonable por sí solo; de ahí la segunda guarda
(`MIN_MATCHED_TERMS`), no solo la primera.

### Limitación conocida (no resuelta, documentada con honestidad)

La pregunta "¿Qué framework de frontend usa el proyecto
sistema-central-admin-servidor?" —cuya respuesta real vive en el ADR-0002
de ESE OTRO repo, no en este corpus— devuelve `CITED` con 4 términos
coincidentes y score 18.6, porque "sistema-central-admin-servidor" se
tokeniza en 4 palabras (`sistema`, `central`, `admin`, `servidor`) que
aparecen juntas, de forma incidental, en un enlace de la sección
"Referencias" de `introduccion.md`. Ninguna de las dos guardas de arriba
detecta este caso: ni el score ni el conteo de términos distinguen "estas 4
palabras coincidieron porque son un nombre propio compuesto irrelevante"
de "estas 4 palabras coinciden porque el contenido es relevante". No se
parcheó con una heurística ad-hoc (arriesga sobreajustar a este único caso
sin generalizar) — se documenta como limitación real y conocida de la
recuperación puramente léxica, exactamente el tipo de caso donde una
recuperación semántica (embeddings) sí distinguiría el significado del
texto citado además de la superficie de las palabras.

## Qué no incluye esta primera vuelta

- **Ninguna llamada a un LLM para sintetizar una respuesta en prosa.** Este
  pilot es solo recuperación (retrieval): devuelve los chunks reales, con su
  cita, o el mensaje de "no encuentro evidencia" — nunca un resumen
  generado. Añadir un paso de generación (reutilizando
  `anthropics/claude-code-action` con `CLAUDE_CODE_OAUTH_TOKEN`, exactamente
  como ya hace el paso `extract` de `daily-memory.yml`) es un incremento
  natural y de bajo riesgo sobre esta base, pero no se ha ejercitado
  end-to-end en este pilot — sería deshonesto afirmar que sí.
- **No se modifica `program.md`, `daily-memory.yml` ni
  `schema/graph-vocabulary.md`.** `AGENTS.md` de este mismo repo ya exige
  conversar cualquier cambio estructural al bot antes de aplicarlo — esta
  primera vuelta es aditiva y separada a propósito.
- **`rag/index.json` no se comete a git** (ver `.gitignore`): es un artefacto
  generado, y comprometerlo hoy sin un paso automático que lo regenere lo
  dejaría obsoleto en cuanto `DockerSwarmDocs` cambie. Se genera bajo
  demanda (`build_index.py`) — wired into `daily-memory.yml` es, de nuevo,
  una decisión estructural futura, no de este ADR.

## Consequences

### Positivas

- Cero coste, cero infraestructura nueva, cero dependencia de red para
  construir y consultar el índice.
- Totalmente auditable: el índice es JSON legible (términos y frecuencias
  por chunk, no vectores opacos).
- Las citas se verificaron independientemente contra `git cat-file`/`git
  show` del commit real de `DockerSwarmDocs` — no son un formato que se
  *dice* correcto, se *comprobó* que resuelve.

### Negativas

- Recuperación puramente léxica: la limitación documentada arriba
  (compuestos/nombres propios) es real y no se ha resuelto.
- Sin paso de generación: la respuesta son chunks citados, no una respuesta
  en prosa lista para pegar en un chat.
- No verificado con embeddings reales en este entorno (ver "Investigación
  realizada") — swap de proveedor sigue siendo trabajo futuro, no algo ya
  probado.

## Alternatives considered

Ver "Investigación realizada" arriba — R2R, pgvector, sqlite-vec y OpenAI
embeddings se descartaron todos por desproporción a esta escala concreta o
por no poder verificarse en este entorno, no por descarte apriorístico.

## References

- <https://pypi.org/pypi/r2r/json>
- <https://r2r-docs.sciphi.ai/documentation/configuration/postgres>
- <https://github.com/SciPhi-AI/R2R/issues/2146>
- <https://www.postgresql.org/about/news/pgvector-082-released-3245>
- <https://github.com/asg017/sqlite-vec/releases>
- <https://sqlite.org/vec1>
- <https://softwaredoug.com/blog/2026/07/29/just-brute-force-embeddings>
- <https://huggingface.co/google/embeddinggemma-300m>
- <https://huggingface.co/Qwen/Qwen3-Embedding-0.6B>
- <https://sbert.net/docs/sentence_transformer/pretrained_models.html>
- <https://docs.github.com/en/actions/reference/github-hosted-runners-reference>
- <https://developers.openai.com/api/docs/models/text-embedding-3-small>
- <https://developers.openai.com/api/docs/models/text-embedding-3-large>
- <https://platform.claude.com/docs/en/build-with-claude/citations>
- ADR-0003 y ADR-0004 de `apptolast/sistema-central-admin-servidor` — el
  stack RAG ya decidido para el proyecto hermano en Kubernetes, punto de
  partida de esta investigación.

## Reversal triggers

Re-evaluar este ADR si:

- El corpus de `DockerSwarmDocs` crece hacia varios miles de páginas (el
  propio benchmark de Turnbull citado arriba deja de ser tranquilizador
  mucho antes de eso, pero da margen amplio).
- Un modelo de embeddings local puede verificarse de verdad en el entorno
  donde esto se ejecuta (GitHub Actions, no este sandbox) y se decide que
  la limitación de "nombres compuestos" (ver arriba) es lo bastante costosa
  como para justificar el cambio.
- Se decide conectar este pilot a `daily-memory.yml` de verdad — en ese
  momento, revisar si `rag/index.json` debe pasar a comprometerse a git
  (como hace `memoria/estado/`) y si conviene mutation testing/otra
  disciplina adicional del arnés SDD para el código Python nuevo.
