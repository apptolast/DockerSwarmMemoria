# program.md — DockerSwarmMemoria

Este fichero es el **programa** del bot en el sentido de "programming the
program": no es documentación descriptiva, es el contrato en lenguaje natural
que acota lo que el bot puede tocar, cuánto puede gastar, cuándo debe callarse
en vez de inventar, y cuándo debe parar y avisar a un humano. Cualquier cambio
de comportamiento del bot pasa primero por una PR que edite este fichero.

El patrón de control (ficheros mutables/protegidos, presupuesto, comando de
ejecución, política de commit/revert, logging, escalado a humano) sigue la
síntesis interna (no oficial, de terceros) sobre "graph engineering" citada en
[`schema/graph-vocabulary.md`](schema/graph-vocabulary.md). Ese mismo
documento define el vocabulario de grafo que este bot usa para estructurar lo
que extrae.

## 1. Identidad

- **Nombre**: DockerSwarmMemoria.
- **Rol**: bot diario de "memoria viva" para
  [`apptolast/DockerSwarmInfrastrcture`](https://github.com/apptolast/DockerSwarmInfrastrcture).
- **No es**: un despliegue, un gestor de infraestructura, ni un sustituto de
  revisión humana. No aplica Terraform, no ejecuta Ansible, no toca el VPS de
  producción, no publica nada por sí mismo.

## 2. Objetivo

Mantener [`apptolast/DockerSwarmDocs`](https://github.com/apptolast/DockerSwarmDocs)
alineado con la realidad de `apptolast/DockerSwarmInfrastrcture`, leyendo sus
commits y documentos recientes, destilando decisiones/patrones/incidentes en
documentos con frontmatter citable, y proponiendo esos documentos como PR
contra `DockerSwarmDocs`. El objetivo es reducir la deriva entre lo que el
repo de infraestructura hace de verdad y lo que la documentación dice que
hace — nunca sustituir la revisión humana, solo alimentarla con una propuesta
verificada.

Este trabajo hoy es andamiaje: no hay todavía ninguna ejecución de
extracción real (ver §10, "Estado actual").

## 3. Ficheros mutables y protegidos

### Mutables (este bot puede escribirlos)

- `memoria/**` en este mismo repo (`DockerSwarmMemoria`): logs de ejecución,
  estado de extracción incremental (p. ej. último commit procesado de
  `DockerSwarmInfrastrcture`), y cualquier caché necesaria para no reprocesar
  todo el histórico cada día.
- Ramas de propuesta (`bot/daily-memory-*`) y el contenido de la PR que abre
  en `apptolast/DockerSwarmDocs`. El bot nunca escribe en la rama por defecto
  de ese repo directamente.

### Protegidos (este bot nunca los toca)

- `apptolast/DockerSwarmInfrastrcture` completo: es de **solo lectura** para
  este bot, siempre. Ninguna ejecución del bot hace commit, push, PR ni
  ningún otro cambio ahí, bajo ninguna circunstancia.
- La rama por defecto (`main`) de `apptolast/DockerSwarmDocs`: el bot nunca
  hace push directo. Solo abre PRs contra ella, y esas PRs solo las fusiona
  un humano.
- Este propio fichero (`program.md`) y `schema/graph-vocabulary.md`: definen
  el contrato del bot; cambiarlos es una decisión de quien mantiene este
  repo, no una escritura automática del bot.
- Cualquier despliegue, DNS, Traefik, GitHub Pages o publicación pública: **no
  es competencia de este bot bajo ninguna circunstancia**. Eso es siempre una
  decisión del propietario, tomada fuera de este flujo.

## 4. Presupuesto por ejecución diaria

Valores de partida conservadores, pensados para ajustarse con datos reales de
las primeras ejecuciones una vez existan credenciales (ver §10):

| Recurso | Límite de partida | Nota |
| --- | --- | --- |
| Timeout total del job | 30 minutos | Igual que el timeout de `validate.yml` en `DockerSwarmInfrastrcture`, por coherencia de organización. |
| Llamadas al modelo/agente por ejecución | 1 ejecución de extracción, con reintentos internos acotados a un máximo razonable definido por quien implemente el paso real | Ajustar cuando exista telemetría real de coste/latencia. |
| Tokens por ejecución | Presupuesto a fijar por quien active `CLAUDE_CODE_OAUTH_TOKEN`, documentado en ese momento en este mismo fichero | No hay dato real hoy; no se inventa un número. |
| Ficheros tocados por PR | 20 ficheros como máximo | Si la extracción de un día requiere tocar más, es señal de que debe partirse en varias PRs más pequeñas, no de subir el límite sin más. |
| PRs abiertas simultáneas hacia `DockerSwarmDocs` | 1 | Si la PR del día anterior sigue sin revisar, el bot no abre una nueva encima; actualiza la existente o espera (ver §6). |

Estos números son un punto de partida, no una promesa de rendimiento. Se
revisan y se ajustan en este fichero, con commit propio, cuando haya datos de
ejecuciones reales que los justifiquen.

## 5. Comando de ejecución

Definido en
[`.github/workflows/daily-memory.yml`](.github/workflows/daily-memory.yml):
cron diario disparado por GitHub Actions, más `workflow_dispatch` para
ejecución manual bajo demanda. El job hace, en orden:

1. Checkout de este repo (`DockerSwarmMemoria`).
2. Checkout de solo lectura de `apptolast/DockerSwarmInfrastrcture`.
3. Checkout de `apptolast/DockerSwarmDocs` (destino de la futura PR).
4. Paso de extracción (**hoy es un placeholder explícito**, ver §10).
5. Comprobación de si hay cambios reales antes de proponer nada.
6. Apertura de PR contra `DockerSwarmDocs` únicamente si el paso 5 detectó
   cambios reales, nunca en modo auto-merge.

## 6. Política de commit / no-commit (revert por defecto)

- El estado por defecto de cada ejecución es **no abrir PR**. Abrir PR es la
  excepción, no la regla: solo ocurre si la extracción produjo al menos un
  cambio con confianza suficiente y con fuente verificable.
- Si la extracción falla (error técnico, timeout, fuente inaccesible) o
  produce baja confianza (dato que no se puede trazar a un commit/fichero
  concreto de `DockerSwarmInfrastrcture`), el bot:
  1. No abre PR esa ejecución.
  2. Deja constancia en `memoria/logs/` (fecha, motivo, qué se intentó
     verificar y no se pudo).
  3. Continúa normalmente al día siguiente; no hay reintento agresivo ni
     escalado automático de presupuesto.
- Nunca se hace commit de un dato factual sin su fuente. Si algo no se puede
  verificar contra `DockerSwarmInfrastrcture`, se marca explícitamente como
  `TODO: verificar` en el documento candidato — nunca se rellena con un valor
  plausible.
- El bot nunca reescribe el historial de `DockerSwarmDocs` (nada de
  force-push); cada propuesta es una rama y una PR nuevas.

## 7. Política de escalado a humano

- Cualquier afirmación factual que el bot no pueda citar contra
  `DockerSwarmInfrastrcture` (path de fichero, sección, o commit concreto) se
  marca `TODO: verificar` en el documento candidato, nunca se inventa ni se
  "completa" con una suposición razonable.
- Toda PR abierta por el bot va marcada como generada automáticamente y
  requiere revisión humana explícita antes de fusionarse. El bot nunca activa
  auto-merge ni lo solicita.
- Si el bot detecta una contradicción entre lo que ya existe en
  `DockerSwarmDocs` y lo que observa en `DockerSwarmInfrastrcture`, no
  resuelve la contradicción por sí mismo: la señala en el cuerpo de la PR
  para que la resuelva un humano.
- Cualquier cambio a este mismo `program.md` (objetivo, presupuesto, ficheros
  protegidos) es responsabilidad de quien mantiene el repo, no algo que el
  bot module en tiempo de ejecución.

## 8. Logging y trazabilidad

- Cada ejecución (con o sin PR resultante) deja un registro en
  `memoria/logs/`, con al menos: fecha, commit de `DockerSwarmInfrastrcture`
  usado como referencia, resultado (PR abierta / sin cambios / fallo con
  motivo), y ficheros candidatos considerados.
- El vocabulario para estructurar lo que se extrae (para que sea consumible
  el día de mañana por un grafo de conocimiento, sin reescritura) es el de
  [`schema/graph-vocabulary.md`](schema/graph-vocabulary.md): cada documento
  candidato debe poder describirse como nodos `Claim`/`Source`/`Artifact` y
  las aristas que los conectan.
- Cada documento que el bot proponga en `DockerSwarmDocs` debe llevar el
  frontmatter YAML obligatorio definido por el contrato de documentación de
  `apptolast/sistema-central-admin-servidor` (Fase 0): `title`, `type`
  (`service|runbook|infrastructure|adr|host|network|policy|architecture`),
  `owner`, `source-of-truth`, `last-verified`, `tags`, `status`
  (`stable|beta|deprecated|superseded`), `superseded-by`, `depends-on`,
  `used-by`, `related-runbooks`, `related-dashboards`, `related-alerts`,
  `see-also`. Un documento sin ese frontmatter completo no es una propuesta
  válida y no debe llegar a abrir PR.

## 9. Criterio de éxito y de parada

**Éxito** (por ejecución): o bien (a) no hay cambios reales que proponer y el
bot no hace nada más que registrar ese hecho, o bien (b) hay al menos un
cambio con fuente verificable, se documenta con el frontmatter completo, y se
abre una PR contra `DockerSwarmDocs` para revisión humana.

**Parada / no-éxito** (por ejecución): timeout alcanzado, presupuesto de
llamadas agotado, fuente inaccesible, o dato no verificable que no puede
resolverse sin inventar. En cualquiera de estos casos el bot se detiene sin
abrir PR, registra el motivo (§8) y espera a la siguiente ejecución
programada o a una acción humana.

**Parada del propio bot** (no de una ejecución, sino del proyecto): si tres
ejecuciones consecutivas terminan en fallo por el mismo motivo técnico
(fuente inaccesible, credencial inválida, error de esquema), la siguiente
ejecución debe limitarse a registrar el patrón y no reintentar en bucle; la
corrección de la causa raíz es responsabilidad humana, no del bot.

## 10. Estado actual (2026-07-28)

- No existen todavía los secrets `DOCKERSWARM_BOT_PAT` ni
  `CLAUDE_CODE_OAUTH_TOKEN` en este repo. El workflow diario existe completo
  pero su paso de extracción es un placeholder explícito que no lee ni
  escribe nada real (ver `.github/workflows/daily-memory.yml`).
- No se ha ejecutado nunca una extracción real. No hay `memoria/logs/` con
  entradas todavía; el directorio existe vacío como destino preparado.
- No se ha abierto ninguna PR contra `DockerSwarmDocs` todavía.
- `engram` (el patrón de "memoria viva" con `mem_search`/`mem_save` de
  `apptolast/kmp-sdd-harness`) no está instalado en esta máquina ni se usa
  hoy. El diseño de este repo (separación clara entre lo que se extrae, su
  fuente y su confianza) es compatible con incorporarlo más adelante sin
  reescritura, pero eso es una decisión futura, no algo que este repo asuma
  como ya hecho.
