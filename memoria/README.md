# memoria/

Estado mutable propio del bot DockerSwarmMemoria (ver
[`../program.md`](../program.md), §3 "Ficheros mutables y protegidos").

Esta carpeta está vacía hoy porque todavía no se ha ejecutado ninguna
extracción real (falta configurar `DOCKERSWARM_BOT_PAT` y
`CLAUDE_CODE_OAUTH_TOKEN`, ver [`../README.md`](../README.md)). Su estructura
prevista, a medida que el workflow diario empiece a correr de verdad:

- `logs/` — un registro por ejecución (fecha, commit de referencia de
  `DockerSwarmInfrastrcture`, resultado: PR abierta / sin cambios / fallo con
  motivo). Ver `program.md`, §8.
- `estado/` (a crear cuando exista extracción real) — punto de control
  incremental, típicamente el último commit de `DockerSwarmInfrastrcture` ya
  procesado, para no reprocesar todo el histórico en cada ejecución diaria.

Nada de lo que haya aquí es documentación factual sobre la infraestructura:
es el estado interno del propio bot. La documentación factual siempre vive
en `apptolast/DockerSwarmDocs`, nunca aquí.
