# memoria/

Estado mutable propio del bot DockerSwarmMemoria (ver
[`../program.md`](../program.md), §3 "Ficheros mutables y protegidos").

Su contenido sigue vacío hoy (solo hay marcadores `.gitkeep`) porque todavía
no se ha ejecutado ninguna extracción real (falta configurar
`DOCKERSWARM_BOT_PAT` y `CLAUDE_CODE_OAUTH_TOKEN`, ver
[`../README.md`](../README.md)). El paso del workflow que escribe aquí
(`Record run log and advance checkpoint` en
[`../.github/workflows/daily-memory.yml`](../.github/workflows/daily-memory.yml))
ya está implementado y hace push directo a este mismo repo — solo falta que
existan los secrets para que el workflow llegue a ejecutarse de verdad.

- `logs/` — un registro por ejecución (fecha, commit de referencia de
  `DockerSwarmInfrastrcture`, resultado: PR abierta / sin cambios / fallo con
  motivo, ficheros candidatos considerados). Ver `program.md`, §8.
- `estado/` — punto de control incremental: `ultimo-commit-procesado.txt`
  contiene el último commit de `DockerSwarmInfrastrcture` ya procesado, para
  no reprocesar todo el histórico en cada ejecución diaria.

Nada de lo que haya aquí es documentación factual sobre la infraestructura:
es el estado interno del propio bot. La documentación factual siempre vive
en `apptolast/DockerSwarmDocs`, nunca aquí.
