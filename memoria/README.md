# memoria/

Estado mutable propio del bot DockerSwarmMemoria (ver
[`../program.md`](../program.md), §3 "Ficheros mutables y protegidos").

Tiene contenido real desde el 2026-07-30: hay un log por cada ejecucion en
`logs/` y el checkpoint de `estado/` apunta al ultimo commit de
`DockerSwarmInfrastrcture` ya procesado. El paso del workflow que escribe
aqui (`Record run log and advance checkpoint` en
[`../.github/workflows/daily-memory.yml`](../.github/workflows/daily-memory.yml))
hace push directo a este mismo repo, nunca a los otros dos.

- `logs/` — un registro por ejecución (fecha, commit de referencia de
  `DockerSwarmInfrastrcture`, resultado: PR abierta / sin cambios / fallo con
  motivo, ficheros candidatos considerados). Ver `program.md`, §8.
- `estado/` — punto de control incremental: `ultimo-commit-procesado.txt`
  contiene el último commit de `DockerSwarmInfrastrcture` ya procesado, para
  no reprocesar todo el histórico en cada ejecución diaria.

Nada de lo que haya aquí es documentación factual sobre la infraestructura:
es el estado interno del propio bot. La documentación factual siempre vive
en `apptolast/DockerSwarmDocs`, nunca aquí.
