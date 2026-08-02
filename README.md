# DockerSwarmMemoria

Bot diario de "memoria viva" para
[`apptolast/DockerSwarmInfrastrcture`](https://github.com/apptolast/DockerSwarmInfrastrcture).
Lee sus commits y documentos recientes, destila decisiones/patrones/incidentes
en documentos con frontmatter citable, y propone esos documentos como PR
contra [`apptolast/DockerSwarmDocs`](https://github.com/apptolast/DockerSwarmDocs)
— siempre fusionada por un humano, nunca en modo automático.

Este repo está operativo. Los dos secrets están configurados desde el
2026-07-30 y el bot ya ha corrido de verdad: 9 ejecuciones (3 fallos
iniciales el 29 y 30 de julio, 6 con éxito desde entonces) y **dos PRs
propuestas y fusionadas por un humano** en `DockerSwarmDocs` (#1 y #4, ambas
el 2026-07-30). Nada de lo que produce este bot se publica, despliega ni
expone en ningún sitio: eso queda fuera de su alcance por diseño (ver
[`program.md`](program.md), §2 y §3).

Desde el 2026-07-30 el bot informa «sin cambios» en cada ejecución. **Eso es
comportamiento correcto, no una avería**: la rama `main` de
`DockerSwarmInfrastrcture` no se ha movido desde ese día, y el checkpoint
incremental de `memoria/estado/ultimo-commit-procesado.txt` apunta
exactamente a su HEAD. El bot volverá a producir en cuanto haya commits
nuevos que destilar.

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
| [`.github/workflows/daily-memory.yml`](.github/workflows/daily-memory.yml) | El workflow diario: checkout de fuentes, cálculo del alcance (bash), paso de extracción real (`anthropics/claude-code-action`), apertura de PR contra `DockerSwarmDocs`, y registro/checkpoint. Implementado y en ejecución diaria desde el 2026-07-30. |
| `memoria/` | Estado mutable propio del bot: `logs/` (un fichero por ejecución) y `estado/` (checkpoint incremental, el último commit de `DockerSwarmInfrastrcture` ya procesado). Con contenido real: hay un log por cada ejecución desde el 2026-07-30 y el checkpoint apunta al HEAD ya procesado. |

## Secrets configurados

Los dos secrets que necesita el workflow **existen desde el 2026-07-30**
(comprobable con `gh secret list --repo apptolast/DockerSwarmMemoria`, que
lista nombre y fecha pero nunca el valor). Aqui no se registra, ni se ha
registrado nunca, el valor de ninguno de los dos.

| Secret | Para que hace falta |
| --- | --- |
| `DOCKERSWARM_BOT_PAT` | Checkout de solo lectura de `apptolast/DockerSwarmInfrastrcture` y apertura de PR (contenidos + pull requests) contra `apptolast/DockerSwarmDocs`. Es un PAT fine-grained propio del bot, con permisos minimos y **sin** el permiso `Workflows`, que es lo que impide que pueda tocar `.github/workflows/` del repo destino. |
| `CLAUDE_CODE_OAUTH_TOKEN` | El paso de extraccion (`anthropics/claude-code-action`) invoca al agente con este token para leer `DockerSwarmInfrastrcture` y redactar los documentos candidatos. |

Hay ademas una dependencia que no es un secret y conviene no perder de vista:
la **GitHub App de Claude Code** tiene que seguir instalada en esta
organizacion. Si se desinstala, el paso de extraccion falla con
"Claude Code is not installed on this repository" y ningun secret arregla
eso.

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
