# DockerSwarmMemoria

Bot diario de "memoria viva" para
[`apptolast/DockerSwarmInfrastrcture`](https://github.com/apptolast/DockerSwarmInfrastrcture).
Lee sus commits y documentos recientes, destila decisiones/patrones/incidentes
en documentos con frontmatter citable, y propone esos documentos como PR
contra [`apptolast/DockerSwarmDocs`](https://github.com/apptolast/DockerSwarmDocs)
— siempre fusionada por un humano, nunca en modo automático.

Este repo hoy contiene el andamiaje (contrato de comportamiento, esquema de
conocimiento y workflow); todavía no ha ejecutado ninguna extracción real
porque faltan dos secrets (ver más abajo). Nada de lo que produce este bot se
publica, despliega ni expone en ningún sitio: eso queda fuera de su alcance
por diseño (ver [`program.md`](program.md), §2 y §3).

## Cómo se relaciona con los otros repos

```
apptolast/DockerSwarmInfrastrcture   →   apptolast/DockerSwarmMemoria   →   apptolast/DockerSwarmDocs
   (fuente de verdad,                       (este repo: bot,                  (destino: documentación
    solo lectura para este bot)              lee y destila)                    viva, PR revisada por humano)
```

- **`apptolast/DockerSwarmInfrastrcture`**: la infraestructura real del VPS de
  producción de apptolast (Netcup, Docker Swarm single-node). Es la única
  fuente de verdad factual. Este bot **solo la lee**; nunca hace commit, push
  ni PR ahí, bajo ninguna circunstancia.
- **`apptolast/DockerSwarmMemoria`** (este repo): el bot en sí. Su propio
  estado mutable vive en `memoria/` (logs de ejecución, estado de extracción
  incremental). Su contrato de comportamiento completo está en
  [`program.md`](program.md).
- **`apptolast/DockerSwarmDocs`**: el repo de documentación viva. Este bot
  **nunca hace push directo** a su rama por defecto; solo abre PRs, y esas
  PRs las revisa y fusiona siempre una persona.

Cada documento que este bot proponga en `DockerSwarmDocs` seguirá el
frontmatter YAML obligatorio (`title`, `type`, `owner`, `source-of-truth`,
`last-verified`, `tags`, `status`, `superseded-by`, `depends-on`, `used-by`,
`related-runbooks`, `related-dashboards`, `related-alerts`, `see-also`)
definido por el contrato de documentación de
`apptolast/sistema-central-admin-servidor` (Fase 0), pensado para que ese
contenido pueda alimentar el día de mañana el "segundo cerebro" RAG de esa
plataforma sin necesidad de reescritura. El vocabulario de nodos/aristas que
usa este bot para estructurar lo que extrae está en
[`schema/graph-vocabulary.md`](schema/graph-vocabulary.md).

## Contenido de este repo

| Fichero/carpeta | Qué es |
| --- | --- |
| [`program.md`](program.md) | El contrato de comportamiento del bot: objetivo, ficheros mutables/protegidos, presupuesto, política de commit/revert, escalado a humano, criterio de éxito/parada. |
| [`schema/graph-vocabulary.md`](schema/graph-vocabulary.md) | El vocabulario de nodos (`Entity`, `Claim`, `Source`, `Artifact`, `AgentRun`, `Evaluation`, `Task`, `Commit`, `Metric`) y aristas (`MENTIONS`, `SUPPORTS`, `CONTRADICTS`, `DERIVED_FROM`, `PRODUCED`, `EVALUATES`, `REVISES`, `SUPERSEDES`, `DEPENDS_ON`, `PARENT_OF`, `RESOLVED_TO`) que usa este bot para estructurar lo que extrae. |
| [`.github/workflows/daily-memory.yml`](.github/workflows/daily-memory.yml) | El workflow diario: checkout de fuentes, paso de extracción (hoy placeholder) y apertura de PR contra `DockerSwarmDocs`. |
| `memoria/` | Estado mutable propio del bot: logs de ejecución y, en el futuro, estado de extracción incremental. Vacío hoy porque no ha corrido ninguna extracción real todavía. |

## Secrets pendientes de configurar

Ninguno de estos dos secrets existe todavía en este repo. **No se ha
inventado ni hardcodeado ningún valor**; el workflow los referencia mediante
`${{ secrets.* }}` y fallará de forma explícita hasta que existan. Configurar
ambos es una decisión y una acción del propietario del repo (Settings →
Secrets and variables → Actions), no de este bot.

| Secret | Para qué hace falta | Por qué falta |
| --- | --- | --- |
| `DOCKERSWARM_BOT_PAT` | Checkout de solo lectura de `apptolast/DockerSwarmInfrastrcture` (repo privado) y apertura de PR (con permiso de contenidos/PR) contra `apptolast/DockerSwarmDocs` (repo privado). | Es un token propio del bot (fine-grained PAT recomendado, con permisos mínimos: lectura sobre `DockerSwarmInfrastrcture`, lectura/escritura de contenidos y pull requests sobre `DockerSwarmDocs`). No existe todavía porque crearlo implica una decisión de alcance/rotación que corresponde al propietario de la organización. |
| `CLAUDE_CODE_OAUTH_TOKEN` | El paso de extracción real (hoy un placeholder marcado `TODO(humano)` en el workflow) invocaría al agente con este token para leer `DockerSwarmInfrastrcture` y redactar los documentos candidatos. | No se ha configurado todavía porque la extracción real no está implementada; hasta que exista, este secret no tiene ningún consumidor real y no debe crearse "por si acaso" con un valor de relleno. |

Sin estos dos secrets, el workflow diario se ejecutará igualmente (el cron
sigue disparándose) pero fallará en los pasos de checkout de
`DockerSwarmInfrastrcture`/`DockerSwarmDocs`: ese es el comportamiento
esperado, no un error de este repo. El paso de extracción seguirá siendo un
placeholder explícito hasta que alguien lo sustituya por la implementación
real (ver el comentario `TODO(humano)` en
[`daily-memory.yml`](.github/workflows/daily-memory.yml)).

## Principio de "siempre fusionado por un humano"

Este bot **nunca** hace merge de sus propias PRs, ni activa auto-merge, ni
hace push directo a la rama por defecto de `DockerSwarmDocs`. Cada propuesta:

- se abre como PR en borrador (`draft`) contra `DockerSwarmDocs`,
- va etiquetada como generada automáticamente,
- cita su fuente exacta para cada afirmación factual, o la marca
  `TODO: verificar` si no pudo confirmarla,
- y solo se convierte en documentación real cuando una persona la revisa y
  la fusiona explícitamente.

Este principio no es un detalle de implementación: es la razón de ser de
`program.md` (ver §3 y §7 de ese fichero) y no se relaja bajo ninguna
circunstancia, incluida la disponibilidad futura de más presupuesto o mejor
tooling.

## Estado relativo a otros proyectos de la organización

- `engram` (memoria viva `mem_search`/`mem_save` de
  `apptolast/kmp-sdd-harness`) **no está instalado** en la máquina donde se
  ejecuta este bot ni se usa hoy. El diseño de este repo deja espacio para
  incorporarlo más adelante (ver la nota final de
  [`schema/graph-vocabulary.md`](schema/graph-vocabulary.md)) sin que eso
  implique una reescritura.
- Este repo no despliega, publica ni configura DNS/Traefik/GitHub Pages de
  nada. Esa es siempre una decisión aparte del propietario, nunca una acción
  automática de este bot.
