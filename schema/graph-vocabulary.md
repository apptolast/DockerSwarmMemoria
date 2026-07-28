# Vocabulario del grafo de conocimiento

Este documento fija el vocabulario de nodos y aristas que
[`apptolast/DockerSwarmMemoria`](../README.md) usa para estructurar lo que
extrae de `apptolast/DockerSwarmInfrastrcture` antes de proponerlo como
documentación en `apptolast/DockerSwarmDocs`.

**Procedencia**: este vocabulario proviene de una síntesis interna de estudio
sobre "graph engineering" — un documento de terceros, **no oficial**, no un
estándar publicado ni una especificación de ningún producto concreto. Se cita
aquí como la referencia que se ha adoptado para este repo, no como una fuente
externa autorizada. No es el mismo esquema que el frontmatter de
`apptolast/sistema-central-admin-servidor` (que es el contrato de
documentación en sí); este vocabulario es el nivel de abajo, pensado para que
lo que este bot extraiga se pueda representar como grafo sin reescritura si
en el futuro `apptolast/sistema-central-admin-servidor` u otro sistema quiere
consumirlo como tal.

## Por qué existe esto hoy

Hoy este repo no tiene todavía ninguna ejecución de extracción real (ver
[`program.md`](../program.md), §10). Este documento no describe un grafo que
ya exista: describe el esquema que se usará en cuanto exista extracción real,
para que desde el primer documento que se proponga en `DockerSwarmDocs` el
formato ya sea consistente con este vocabulario, y no haga falta reescribir
nada retroactivamente.

## Nodos

| Nodo | Qué representa | Ejemplo dentro de este dominio |
| --- | --- | --- |
| `Entity` | Una cosa identificable y estable en la infraestructura: un servicio, un host, una red, un stack, un secret. | El servicio `n8n`, el host `159.195.156.57`, la red `ingress`. |
| `Claim` | Una afirmación factual concreta sobre una `Entity`, en un momento dado. | "El Swarm usa autolock desactivado a fecha X". |
| `Source` | El origen verificable de una `Claim`: un path de fichero, un commit, la salida de un comando. | `docs/TERRAFORM_STATE.md` de `DockerSwarmInfrastrcture`, o el commit `854e160`. |
| `Artifact` | Algo producido como resultado de trabajo: un documento Markdown, un PR, un fichero de log. | El `.md` que este bot propone en `DockerSwarmDocs`. |
| `AgentRun` | Una ejecución concreta del bot (o de cualquier agente) que produjo uno o más `Artifact`. | La ejecución diaria de `daily-memory.yml` del 2026-08-01. |
| `Evaluation` | Un juicio sobre la calidad/confianza de una `Claim` o un `Artifact`, con su rúbrica. | "Confianza alta: la claim cita un path exacto y una fecha verificable". |
| `Task` | Una unidad de trabajo pendiente o en curso, humana o del bot. | "Revisar y fusionar la PR #N en DockerSwarmDocs". |
| `Commit` | Un commit real en un repo de la organización. | Un commit de `DockerSwarmInfrastrcture` que introduce un cambio documentado. |
| `Metric` | Un valor numérico medible asociado a una `Entity` o `Evaluation`, con su fecha de medición. | "Ficheros tocados en la PR: 3, medido en la ejecución del AgentRun". |

## Aristas

| Arista | De → A | Significado |
| --- | --- | --- |
| `MENTIONS` | `Artifact`/`Claim` → `Entity` | El artefacto o la afirmación hace referencia a esa entidad. |
| `SUPPORTS` | `Source` → `Claim` | La fuente respalda la afirmación tal cual está escrita. |
| `CONTRADICTS` | `Source`/`Claim` → `Claim` | Una fuente o afirmación entra en conflicto con otra ya existente; no se resuelve automáticamente (ver `program.md`, §7). |
| `DERIVED_FROM` | `Claim`/`Artifact` → `Source`/`Commit` | El elemento se dedujo directamente de esa fuente o commit. |
| `PRODUCED` | `AgentRun` → `Artifact` | Esa ejecución generó ese artefacto. |
| `EVALUATES` | `Evaluation` → `Claim`/`Artifact` | Esa evaluación juzga ese elemento, con una rúbrica explícita. |
| `REVISES` | `Artifact`/`Commit` → `Artifact` | Un artefacto nuevo corrige o actualiza a uno anterior sin sustituirlo del todo. |
| `SUPERSEDES` | `Artifact`/`Claim` → `Artifact`/`Claim` | El elemento nuevo reemplaza al anterior por completo; el anterior queda marcado `superseded-by`, nunca borrado sin más. |
| `DEPENDS_ON` | `Entity`/`Task` → `Entity`/`Task` | Relación de dependencia operativa o de orden. |
| `PARENT_OF` | `Entity`/`Task` → `Entity`/`Task` | Relación jerárquica o de composición. |
| `RESOLVED_TO` | `Task` → `Artifact`/`Commit` | La tarea se cerró produciendo ese resultado concreto. |

## Invariantes obligatorios

Toda escritura de este bot al vocabulario anterior — hoy en forma de
documentos Markdown con frontmatter, mañana posiblemente en forma de grafo
real — debe cumplir:

1. **Toda `Claim` tiene una `Source` vía `SUPPORTS`/`DERIVED_FROM`, o se marca
   explícitamente como inferencia.** Nunca se presenta una inferencia como si
   tuviera fuente directa.
2. **Todo `Artifact` tiene el `AgentRun` que lo produjo**, vía `PRODUCED`.
   Ningún documento propuesto por este bot aparece sin la ejecución que lo
   generó siendo trazable.
3. **Toda `Evaluation` identifica su rúbrica.** No hay juicios de confianza
   sin criterio explícito (p. ej. "confianza alta = cita path + commit +
   fecha"; "confianza baja = no se pudo verificar contra la fuente").
4. **Todo objeto reemplazado sigue siendo direccionable.** Nunca se borra un
   `Artifact` o una `Claim` superada sin más: se enlaza con `SUPERSEDES` y se
   marca `superseded-by` en su frontmatter, igual que exige el contrato de
   `apptolast/sistema-central-admin-servidor`.

## Relación con el frontmatter de `DockerSwarmDocs`

Cada documento que este bot proponga en `DockerSwarmDocs` lleva el
frontmatter YAML definido por `apptolast/sistema-central-admin-servidor`
(ver [`program.md`](../program.md), §8). La correspondencia con este
vocabulario es:

| Campo de frontmatter | Nodo/arista equivalente |
| --- | --- |
| `source-of-truth` | `Source`, conectado por `SUPPORTS`/`DERIVED_FROM` |
| `last-verified` | Propiedad temporal de la arista `SUPPORTS`/`DERIVED_FROM` |
| `depends-on` | Aristas `DEPENDS_ON` hacia otras `Entity` |
| `used-by` | Aristas `DEPENDS_ON` inversas, o `PARENT_OF` según el caso |
| `related-runbooks` | Aristas `MENTIONS`/`DEPENDS_ON` hacia `Artifact` de tipo runbook |
| `related-dashboards`, `related-alerts` | Aristas `MENTIONS` hacia `Entity`/`Artifact` externos, hoy fuera del alcance de este repo |
| `see-also` | Aristas `MENTIONS` genéricas |
| `superseded-by` | Arista `SUPERSEDES` desde el documento nuevo |
| `status: superseded` | Confirma que el nodo `Artifact` tiene una arista `SUPERSEDES` entrante |

## Nota sobre `engram`

`apptolast/kmp-sdd-harness` define un patrón de "memoria viva" (`mem_search`
/ `mem_save`) y la idea de que cada feature lleva un `spec.md` autosuficiente
como mecanismo anti-deriva. `engram` no está instalado en esta máquina y este
repo no lo usa ni asume que exista. Se deja constancia aquí de que el
vocabulario de nodos/aristas de este documento es compatible en espíritu con
ese patrón (un `Claim` con su `Source` es, en esencia, lo que `mem_save`
guardaría; una consulta `mem_search` sería una lectura sobre `SUPPORTS`/
`MENTIONS`), por si en el futuro se decide integrar `engram` sin tener que
rediseñar este esquema desde cero.
