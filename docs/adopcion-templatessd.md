# Adopción de TemplateSSDUncleBob en DockerSwarmMemoria

> Este documento explica cómo convive el arnés SDD "Uncle Bob"
> (`TemplateSSDUncleBob`) con la lógica ya existente y en producción de este
> bot. No reescribe ni cambia el comportamiento de producción de
> `DockerSwarmMemoria` — lo documenta y estructura alrededor. Si algo aquí
> pareciera contradecir `program.md`, gana `program.md`.

## Resumen en una frase

`DockerSwarmMemoria` ya era, antes de esta adopción, un bot narrow-scope
bien diseñado con su propio contrato de comportamiento (`program.md`) y su
propia disciplina real de "PR siempre revisada por un humano"; esta adopción
añade la capa de gobernanza y nomenclatura común de `TemplateSSDUncleBob`
por encima de eso —no un rediseño—, y dice explícitamente qué partes de la
plantilla no tienen un equivalente honesto en este stack en vez de
inventarlas.

## El stack real de este repo (por qué no es "Node/TS" sin más)

Antes de adaptar nada se comprobó el manifiesto de stack de este repo: **no
hay `package.json`**, ni `src/`, ni `tests/`, ni ningún gestor de paquetes.
Lo que hay es:

- **`program.md`** — el contrato de comportamiento en lenguaje natural
  (equivalente, en espíritu, a un "programa": qué puede tocar el bot, cuánto
  puede gastar, cuándo debe callarse y escalar a un humano).
- **`schema/graph-vocabulary.md`** — el vocabulario de nodos/aristas que
  estructura lo que el bot extrae.
- **`.github/workflows/daily-memory.yml`** — la única lógica *ejecutable*:
  un workflow de GitHub Actions con varios pasos en bash puro (`scope`,
  `Check for real changes`, `Record run log and advance checkpoint`) y un
  único paso agéntico (`anthropics/claude-code-action`, sin Bash ni red,
  solo lectura + escritura acotada a `dockerswarm-docs/`).
- **`memoria/`** — el estado mutable real del bot (`logs/`, `estado/`).

Es decir: el "código" de este bot es YAML + bash embebido + un contrato en
prosa, no una aplicación en un lenguaje de propósito general. `harness.mjs`
(el motor del arnés) exige Node ≥ 18 para SÍ MISMO, no para el proyecto que
gobierna — pero aquí no hay nada que ese motor tenga que compilar, instalar
ni ejecutar como "suite de tests" en el sentido tradicional.

## Qué se adoptó en esta adopción (archivos de este PR)

| Archivo | Origen |
| --- | --- |
| `harness.config.json` | Nuevo, adaptado — comandos reales de este stack |
| `harness.schema.json` | Copiado tal cual de `TemplateSSDUncleBob` |
| `AGENTS.md` | Nuevo, adaptado |
| `CHECKPOINTS.md` | Nuevo, adaptado |
| `CLAUDE.md` | Nuevo, adaptado (no existía en este repo antes de esta adopción) |
| `scripts/sync-memoria.sh` / `.ps1` | Copiados tal cual de `TemplateSSDUncleBob` |
| `.gitignore` | Nuevo — excluye `.memoria-cache/` (lo genera el script anterior) |
| `docs/adopcion-templatessd.md` | Este documento |

## Cómo se mapea (o no) cada fase del pipeline Uncle Bob

El pipeline es: **spec_partner → gherkin_author → ⏸ puerta humana →
tdd_craftsman → judge → mutation_tester**. Fase por fase, contra este stack:

### 1. `spec_partner` / `project-spec.md`

En un proyecto nuevo, `spec_partner` conversa con el humano para producir
`project-spec.md`. **Aquí ese papel ya lo cumple `program.md`**, y lo cumple
mejor de lo que un `project-spec.md` genérico podría: es más específico,
tiene versión, y ya exige explícitamente (`program.md` §7) que cualquier
cambio a su contenido sea "responsabilidad de quien mantiene el repo, no
algo que el bot module en tiempo de ejecución". No se duplica `program.md`
en un `project-spec.md` aparte — sería una segunda fuente de verdad
divergente. Para un cambio estructural futuro (ver más abajo, "Cuándo sí
aplicaría el pipeline completo"), la conversación de spec sigue siendo el
primer paso, solo que su resultado se integra directamente en `program.md`.

### 2. `gherkin_author` / `features/<name>.feature`

Tiene sentido para cambios de comportamiento observable y grandes: por
ejemplo, "cambiar la ventana del circuit-breaker de 3 a 5 ejecuciones
fallidas consecutivas" es perfectamente expresable como
`Given/When/Then` contra el workflow. Hoy no hay ningún cambio así en
curso, así que no se fabricó un `features/` vacío ni un `feature_list.json`
de relleno solo por completitud — ver "Qué no se vendorizó" más abajo.

### 3. `tdd_craftsman` / TDD estricto (Rojo-Verde-Refactor)

**No aplica hoy tal cual.** TDD estricto necesita un `src/` con funciones
testeables unitariamente. El bash embebido en `daily-memory.yml` (cálculo de
alcance, circuit-breaker, avance de checkpoint) es lógica real con ramas
reales que, en principio, **podría** extraerse a scripts independientes y
testearse con `bats`/`shellspec` — pero hacer eso sería reescribir la
implementación actual del workflow, exactamente lo que esta adopción tiene
mandato explícito de NO hacer. Se deja consignado aquí como mejora futura
legítima, no como algo pendiente de esta adopción.

### 4. `judge` / review ("el review es el juego entero")

**Esto ya es la práctica real de este repo para cambios de comportamiento**,
desde antes de esta adopción: `git log` muestra varios cambios al workflow o
al contrato fusionados vía PR revisada por una persona — por ejemplo los
squash-merge etiquetados `(#1)` ("fail closed if the proposed docs don't
build", tras el incidente real de la PR #1 en `DockerSwarmDocs`), `(#2)`
(actualización del contrato para la migración Docusaurus→Starlight de
`DockerSwarmDocs`), `(#3)` (bump de `actions/setup-node` a v7) y `(#4)`
(corrección de afirmaciones de estado obsoletas en los dos README de este
repo). Es una
disciplina real, no aspiracional. Distinto de eso: las entradas rutinarias
`chore(memoria): registrar ejecución del <fecha>` son push directo y
automático del propio bot sobre su propio estado mutable (`memoria/`),
explícitamente permitido sin PR por `program.md` §3 — no son un cambio de
comportamiento y no se espera que pasen por revisión humana una a una. El
arnés nombra y refuerza la disciplina de review sobre lo primero; no
pretende que lo segundo también deba pasar por ahí, y la extiende
explícitamente a cualquier cambio futuro a
`harness.config.json`/`AGENTS.md`/`CHECKPOINTS.md`/`CLAUDE.md` mismos.

### 5. `mutation_tester` / prueba de mutación

**No aplica, con razón explícita** — ver la sección dedicada abajo.

## Qué NO se vendorizó (y por qué, archivo por archivo)

Esta adopción **no** copia mecánicamente todo `TemplateSSDUncleBob`. Es una
decisión explícita, tomada con el mandato de "documenta/estructura
alrededor, no reescribas la lógica ya existente":

| No incluido | Por qué |
| --- | --- |
| `.harness/harness.mjs`, `bin/harness(.ps1)`, `init.sh`/`init.ps1` | Motor Node.js de cero dependencias, pensado para invocar `commands.test`/`commands.mutate` sobre un `src/`+`tests/` real. Este repo no tiene ninguno de los dos ni planea tenerlos: introducir un CLI de Node aquí (un repo que hoy no tiene NINGÚN paso de build/test en Node) sería tooling nuevo sin usuario real. Los comandos reales de este stack ya quedan declarados en `harness.config.json`, ejecutables directamente (`actionlint`) sin necesitar el envoltorio. |
| `.claude/agents/*.md` (9 roles) | Formalizan roles (`tdd_craftsman`, `mutation_tester`…) para fases que no aplican aquí tal cual (ver arriba). Se preserva su *espíritu* en `AGENTS.md`/`CLAUDE.md` sin fingir que los 9 subagentes existen en este repo. Si algún día una feature estructural de este bot amerita el pipeline completo, se traen desde `TemplateSSDUncleBob` en ese momento — incluido `a11y_seo_auditor`, que además no aplicaría nunca aquí: este repo no tiene UI web propia. |
| `docs/workflow.md`, `docs/tdd.md`, `docs/gherkin.md`, `docs/mutation-testing.md`, `docs/verification.md`, `docs/configuration.md`, `docs/tooling.md`, `docs/memoria-organizacional.md` | Documentación del proceso fijo y agnóstico de la plantilla. Vive y se mantiene en el repo canónico `TemplateSSDUncleBob`; duplicarla aquí crearía una segunda copia que diverge con el tiempo. Este documento resume lo relevante; para el detalle completo, consultar la plantilla. |
| `feature_list.json`, `project-spec.md`, `features/`, `progress/` | Son el estado *vivo* del pipeline por feature. No existe hoy ninguna feature estructural de este bot en curso — crear estos ficheros vacíos o con una feature de relleno sería inventar estado que no existe, justo lo que `program.md` §6/§7 prohíbe hacer con datos factuales. Se crean el día que hagan falta de verdad. |
| `.github/AUTONOMOUS.md`, `.github/workflows/autonomous-evolve.yml`, `.github/workflows/guard-sensitive-paths.yml`, `.github/CODEOWNERS`, `.github/workflows/harness-ci.yml` | El mecanismo de auto-evolución **del propio arnés** (un bot semanal/diario que mejora `TemplateSSDUncleBob` y abre PR). Es explícitamente opt-in incluso en la plantilla (`ENABLE_AUTONOMOUS_EVOLVE=true`). Activarlo aquí añadiría un **segundo** bot autónomo de propósito distinto al que ya opera este repo (`daily-memory.yml`), con su propio presupuesto y su propia superficie de riesgo — una decisión de producto que le corresponde a quien mantiene este repo, no a esta adopción. |
| `examples/` | Material de referencia de la plantilla (arneses Python/Node/Go/Rust completos). No aporta nada operativo a este repo concreto. |

Nada de esto es "no se pudo" en el sentido de una limitación técnica: es una
decisión de alcance, documentada aquí para que sea auditable y reversible.
Cualquiera de estas piezas se puede añadir después, tomándola literalmente
del repo canónico `TemplateSSDUncleBob`, sin que este documento quede
desactualizado — solo hay que añadir una fila a la tabla de arriba
explicando cuándo y por qué se trajo.

## Por qué no hay mutación

La prueba de mutación mide si los tests **muerden** introduciendo defectos
pequeños en el código y comprobando que algún test falla. Eso presupone dos
cosas que este repo no tiene: (1) código fuente en un lenguaje de propósito
general con expresiones mutables (`<=`→`<`, `and`→`or`, `return x`→`return
None`…), y (2) una suite de tests unitaria que pueda fallar o no ante esos
mutantes.

`daily-memory.yml` sí tiene bash con lógica real (comparaciones, booleanos),
pero mutar líneas *dentro de un `run:` de YAML* no tiene ninguna herramienta
madura y real detrás — a diferencia de StrykerJS (Node), gremlins (Go),
cargo-mutants (Rust) o PIT (Java), que sí son las herramientas reales que
`TemplateSSDUncleBob` recomienda para esos stacks. Inventar aquí un
"mutador de YAML" casero, solo para poder rellenar `commands.mutate` y que
la casilla de `CHECKPOINTS.md` no quede vacía, sería precisamente el tipo de
comando **inventado** que esta adopción tiene mandato explícito de evitar.

En su lugar, `harness.config.json` usa el escape hatch que el propio esquema
de la plantilla ya provee para este caso: `rules.require_mutation_to_close:
false` para `daily-memory.yml`. La verificación real de ese fichero —
`actionlint` — cubre lo que sí es real: que el YAML es válido, que las
expresiones de contexto de GitHub Actions existen, y (si `shellcheck` está
instalado) que el bash embebido no tiene los errores más comunes de
scripting. La verificación de más alto nivel —¿el bot realmente hace lo que
dice `program.md`?— la dan los gates que ya existen en producción
(circuit-breaker, PR-única-abierta, `verify-build`) y, sobre todo, la
revisión humana de cada PR real, que es irremplazable por ninguna prueba de
mutación.

**Nota (sesión posterior a esta adopción, no reescrita aquí para no perder
el razonamiento original — ver `CHECKPOINTS.md` C7 para el estado
completo):** todo lo de arriba sigue siendo exactamente cierto para
`daily-memory.yml`. Pero este repo ganó después código Python real
(`scripts/rag/`, `scripts/graph/`, pilot de RAG + grafo — ver
`docs/adrs/0001-*.md`/`0002-*.md`), que sí cumple las dos condiciones del
primer párrafo de esta sección (lenguaje de propósito general, suite de
tests real) — para esa parte, `commands.test` y `commands.mutate` de
`harness.config.json` ya NO están vacíos ni se limitan a `actionlint`.

## Memoria organizacional: productor y ¿también consumidor?

`DockerSwarmMemoria` es, por diseño, un **productor** de conocimiento
organizacional: destila commits y documentos de `DockerSwarmInfrastrcture`
en `Claim`s con fuente citable y los propone en `DockerSwarmDocs`
(`schema/graph-vocabulary.md`). Con el paso 2bis ya wireado en `CLAUDE.md`
(`scripts/sync-memoria.sh`), este mismo repo se convierte también, de forma
natural, en **consumidor** de una memoria compartida distinta: la de
`Cenit-Digital/SistemaDeMemoriaUncleBob`, que no destila hechos de
infraestructura sino patrones de desarrollo/arquitectura/tooling ya
validados en otros proyectos que usan `TemplateSSDUncleBob`.

Es una idea interesante y vale la pena dejarla escrita, con dos límites
claros:

1. **Son dos memorias de dominios distintos, y no deberían mezclarse sin
   pensarlo.** La de `SistemaDeMemoriaUncleBob` es sobre *cómo construir
   software* (patrones de testing, de arquitectura, de tooling); la de
   `memoria/` en este mismo repo es sobre *hechos de infraestructura* de
   `DockerSwarmInfrastrcture`. El consumo relevante aquí es para quien
   **desarrolla o mantiene el propio bot** `DockerSwarmMemoria` (p. ej. un
   patrón validado sobre "cómo estructurar un circuit-breaker en un paso de
   CI" sería relevante al tocar `daily-memory.yml`), no una fusión de los dos
   grafos de conocimiento.
2. **No está verificado que `apptolast` (el owner de este repo) tenga acceso
   a la organización `Cenit-Digital`**, dueña del repo privado
   `SistemaDeMemoriaUncleBob` que clona `sync-memoria.sh`. Son, a todas
   luces, dos organizaciones de GitHub distintas. Esto no bloquea nada en la
   práctica — el script está diseñado exactamente para este caso: si no hay
   acceso, avisa y termina en 0 sin romper el arranque de la sesión — pero
   sí significa que, tal como está hoy, el paso 2bis en este repo
   probablemente se limitará a ese aviso no bloqueante en vez de traer
   patrones reales, hasta que alguien confirme (o cree) el acceso entre
   organizaciones, o hasta que exista un repositorio de memoria equivalente
   accesible para `apptolast`.

**No se implementa nada más allá de esto.** Copiar los dos scripts y añadir
el paso 2bis ya deja la puerta abierta; decidir si hace falta un mecanismo
de memoria compartida propio de `apptolast`, o gestionar el acceso entre
organizaciones, es una decisión de producto de quien mantiene ambos repos —
no algo que esta adopción deba resolver por su cuenta.

## Huecos honestos de esta adopción

Por transparencia, y siguiendo la misma disciplina de `program.md` de
marcar `TODO: verificar` en vez de rellenar con un valor plausible:

- **`actionlint` y `shellcheck` no están instalados en el entorno donde se
  hizo esta adopción.** No se pudo ejecutar `commands.test` de verdad contra
  `.github/workflows/daily-memory.yml` para confirmar un resultado en verde
  — se declaró el comando real y estándar para este tipo de stack, pero
  su primera ejecución real queda pendiente de quien tenga el binario
  instalado (o de configurarlo en CI).
- **El acceso de `apptolast` a `Cenit-Digital/SistemaDeMemoriaUncleBob`
  no está confirmado** (ver sección anterior) — se documenta como incógnita
  en vez de asumir que sí o que no.
- **`harness.config.json` no ha sido ejercitado por el motor
  `.harness/harness.mjs`** porque ese motor no se vendorizó en este repo
  (ver "Qué NO se vendorizó"). Sí se validó con una validación de esquema
  JSON directa (`jsonschema`, draft-07) contra `harness.schema.json`.

## Cuándo sí aplicaría el pipeline completo

Si en el futuro este bot necesita un cambio de comportamiento
suficientemente grande como para merecer spec conversada + Gherkin + revisión
formal (por ejemplo: soportar un segundo repo de infraestructura fuente,
cambiar de PR-en-borrador a PR-normal, o añadir un nuevo tipo de documento
al frontmatter), en ese momento:

1. Traer de `TemplateSSDUncleBob` (repo canónico) los ficheros que hagan
   falta de la tabla "Qué NO se vendorizó" — probablemente
   `project-spec.md`, `features/`, `progress/`, y si el cambio toca lógica
   bash extraíble, considerar entonces sí extraerla a `scripts/` testables.
2. Actualizar este documento con una fila nueva explicando qué se trajo y
   por qué, para que la tabla siga siendo la fuente de verdad de qué está
   vendorizado y qué no.
3. Seguir aplicando, sin excepción, las reglas de `program.md` §3/§6/§7 por
   encima de cualquier fase del pipeline: ningún dato sin fuente, ningún
   push directo a `DockerSwarmDocs`/`DockerSwarmInfrastrcture`, ninguna
   fusión automática.
