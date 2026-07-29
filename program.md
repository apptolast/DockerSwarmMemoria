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
| Llamadas al modelo/agente por ejecución | 1 invocación de `anthropics/claude-code-action` (`claude-sonnet-5`), sin reintento automático si falla | Configurado en `.github/workflows/daily-memory.yml`, paso `extract`. Solo se invoca si hay commits nuevos que procesar (ver §5). |
| Turnos agénticos por ejecución | `--max-turns 40` | Límite duro de la CLI (`claude -p`); la ejecución se detiene con error si lo alcanza sin haber terminado. |
| Gasto en USD por ejecución | `--max-budget-usd 3.00` | Punto de partida sin telemetría real todavía (2026-07-29, ver §10); se ajusta aquí en cuanto haya coste real observado de las primeras ejecuciones. |
| Ficheros tocados por PR | 20 ficheros como máximo | Si la extracción de un día requiere tocar más, es señal de que debe partirse en varias PRs más pequeñas, no de subir el límite sin más. Aplicado como instrucción explícita al agente, no como límite técnico forzado por el workflow. |
| PRs abiertas simultáneas hacia `DockerSwarmDocs` | 1 | Aplicado en el paso `existing-pr` de `daily-memory.yml`: si ya hay una PR abierta con la etiqueta `automated-pr`, la ejecución de hoy no abre otra — lo deja registrado en `memoria/logs/` y espera (ver §6). |

Estos números son un punto de partida, no una promesa de rendimiento. Se
revisan y se ajustan en este fichero, con commit propio, cuando haya datos de
ejecuciones reales que los justifiquen.

## 5. Comando de ejecución

Definido en
[`.github/workflows/daily-memory.yml`](.github/workflows/daily-memory.yml):
cron diario disparado por GitHub Actions, más `workflow_dispatch` para
ejecución manual bajo demanda. El job hace, en orden:

1. Checkout de este repo (`DockerSwarmMemoria`, con permiso de escritura para
   el paso 9).
2. Checkout de solo lectura de `apptolast/DockerSwarmInfrastrcture`.
3. Checkout de `apptolast/DockerSwarmDocs` (destino de la futura PR).
4. Cálculo en bash puro (sin agente) de qué cambió en
   `DockerSwarmInfrastrcture` desde el último commit procesado
   (`memoria/estado/`), o instantánea completa si es la primera ejecución.
   Este mismo paso evalúa también el circuit-breaker de §9 (últimas 3
   entradas de `memoria/logs/` fallidas por el mismo motivo).
5. Comprobación de que no haya ya una PR automática abierta sin revisar
   (máximo 1 simultánea, ver §4) — antes de gastar presupuesto en extraer,
   no después.
6. Paso de extracción (**implementado**, ver §10): `anthropics/claude-code-action`,
   solo si el paso 4 encontró algo que procesar, el paso 5 no encontró una
   PR ya abierta, y el circuit-breaker no está activo.
7. Comprobación de si hay cambios reales en `DockerSwarmDocs` antes de
   proponer nada (siempre `false` si el paso 6 no llegó a ejecutarse).
8. Apertura de PR contra `DockerSwarmDocs` únicamente si el paso 7 detectó
   cambios reales, nunca en modo auto-merge.
9. Registro de la ejecución en `memoria/logs/` y avance del checkpoint en
   `memoria/estado/`, con push directo a la rama por defecto de este mismo
   repo (nunca a `DockerSwarmDocs` ni a `DockerSwarmInfrastrcture`). Corre
   siempre, incluso si un paso anterior falló, para dejar constancia (§6). El
   checkpoint solo avanza si el rango de commits de esta ejecución se
   procesó de verdad (o si no había nada que procesar) — nunca si el
   circuit-breaker, la PR-ya-abierta o un fallo de extracción lo impidieron,
   para no perder ese rango sin procesar.

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
- Además del contrato anterior, `DockerSwarmDocs` es un sitio Docusaurus cuyo
  sidebar se genera automáticamente a partir del campo `sidebar_position` de
  cada fichero (ver `sidebars.js` de ese repo). No forma parte del contrato
  de `sistema-central-admin-servidor`, pero también es obligatorio en cada
  documento propuesto por este bot para que la página aparezca donde debe.

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

**Implementado** en el paso `scope` de `daily-memory.yml`: compara las 3
entradas más recientes de `memoria/logs/` y, si las 3 tienen exactamente el
mismo texto de `Resultado:` empezando por "fallo:", marca
`circuit_breaker=true` y la ejecución de ese día no llega a extraer. Es una
pausa de una ejecución, no un apagado permanente: se reevalúa en cada
ejecución con la ventana de las 3 últimas entradas, así que un fallo real y
persistente sigue pausando el reintento de forma indefinida, y un único
`Resultado:` distinto en la ventana (por ejemplo, tras corregir la causa
raíz) rompe el patrón y permite reintentar de nuevo.

## 10. Estado actual (2026-07-29)

- El paso de extracción real ya está implementado (ver
  `.github/workflows/daily-memory.yml`, paso `extract`): invoca
  `anthropics/claude-code-action` (fijado a un commit concreto, no a un tag
  móvil) con el presupuesto de §4, sin acceso a shell ni red — el cálculo de
  qué cambió desde la última ejecución lo hace un paso anterior en bash puro
  (`scope`), no el agente. El checkpoint incremental
  (`memoria/estado/ultimo-commit-procesado.txt`) y el log por ejecución
  (`memoria/logs/YYYY-MM-DD.md`) también están implementados, con push directo
  del propio bot a la rama por defecto de este mismo repo (mutable por
  contrato, §3) — nunca a `DockerSwarmDocs` ni a `DockerSwarmInfrastrcture`.
- La comprobación de "máximo 1 PR abierta simultánea" (§4) corre antes de
  extraer, no después: si ya hay una PR automática sin revisar, el paso
  `extract` ni siquiera se invoca ese día (ahorra presupuesto) y el
  checkpoint no avanza, para no perder ese rango de commits sin procesar. El
  circuit-breaker de §9 está implementado con la misma lógica de "no
  avanzar el checkpoint si no se procesó de verdad".
- Sigue sin existir ninguno de los dos secrets, `DOCKERSWARM_BOT_PAT` ni
  `CLAUDE_CODE_OAUTH_TOKEN`. Configurarlos sigue siendo una decisión y una
  acción explícita del propietario del repo (ver README.md, "Secrets
  pendientes de configurar"); nadie los ha inventado ni cargado con un valor
  de relleno. Sin ellos, el workflow sigue fallando de forma explícita en los
  checkouts cruzados y el paso `extract` nunca llega a invocarse con un token
  real.
- Consecuencia directa de lo anterior: no se ha ejecutado nunca una
  extracción real todavía, ni con la implementación de hoy. El presupuesto en
  USD de §4 (`--max-budget-usd 3.00`) es un punto de partida sin telemetría
  real que lo respalde — se revisará en cuanto exista una primera ejecución
  real que lo justifique o lo contradiga.
- No se ha abierto ninguna PR contra `DockerSwarmDocs` todavía.
- `engram` (el patrón de "memoria viva" con `mem_search`/`mem_save` de
  `apptolast/kmp-sdd-harness`) no está instalado en esta máquina ni se usa
  hoy. El diseño de este repo (separación clara entre lo que se extrae, su
  fuente y su confianza) es compatible con incorporarlo más adelante sin
  reescritura, pero eso es una decisión futura, no algo que este repo asuma
  como ya hecho.
