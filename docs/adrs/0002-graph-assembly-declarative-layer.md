---
title: "ADR-0002: Ensamblado real del grafo declarativo (Capa 1) sobre el frontmatter de DockerSwarmDocs"
status: accepted
date: 2026-08-04
owner: pablo
supersedes: null
superseded-by: null
tags: [architecture, knowledge-graph, rag, pilot]
---

# ADR-0002: Ensamblado real del grafo declarativo (Capa 1)

## Status

**Accepted** — 2026-08-04. Pilot, no producción — mismo alcance que
ADR-0001 (aditivo, no conectado a `daily-memory.yml`).

## Context

`schema/graph-vocabulary.md` (ya existente en este repo, anterior a este
ADR) define un vocabulario de nodos (`Entity`, `Claim`, `Source`,
`Artifact`, `AgentRun`, `Evaluation`, `Task`, `Commit`, `Metric`) y aristas
(`MENTIONS`, `SUPPORTS`, `CONTRADICTS`, `DERIVED_FROM`, `PRODUCED`,
`EVALUATES`, `REVISES`, `SUPERSEDES`, `DEPENDS_ON`, `PARENT_OF`,
`RESOLVED_TO`) citando como procedencia "una síntesis interna de estudio
sobre 'graph engineering' — un documento de terceros, no oficial". El
propietario (Pablo) subió ese documento exacto durante esta sesión:
**"Graph Engineering: The Karpathy Loop, Improved 1000x by Itself — The
Anthropic Playbook"** (síntesis fechada julio 2026).

**Nota de procedencia, con la misma honestidad que exige el propio
documento**: su portada declara explícitamente *"Independently compiled,
July 2026 - not affiliated with Andrej Karpathy and Anthropic - and not
endorsed"*, y su sección de agradecimientos repite: *"This document is an
independent synthesis assembled for study. It is not affiliated with or
endorsed by Andrej Karpathy, Anthropic, Sequoia Capital, Bun, or any other
organization mentioned."* Este ADR cita sus ideas como lo que son — una
síntesis de terceros sobre trabajo público de Karpathy (`autoresearch`,
`AgentHub`) y guías de Anthropic (Building Effective Agents, Dynamic
Workflows, Knowledge Graph Construction Cookbook) — nunca como
documentación oficial de Anthropic ni de Karpathy. El vocabulario de nodos
y aristas de `schema/graph-vocabulary.md` coincide, término a término, con
el Apéndice ("Terms Used in This Note", node types / edge types) de ese
documento — confirma que la adopción original ya fue fiel a esa fuente, no
inventada.

El propio README de este repo ya advertía: "Sigue sin existir un grafo
persistido y consultable: lo que hay hoy son estos documentos Markdown con
frontmatter aplicando el vocabulario de abajo, no un almacén de grafo
real." Este ADR cierra esa brecha para la Capa 1 (declarativa) — no para
las Capas 2/3.

## Qué dice la fuente sobre CUÁNDO construir un grafo

Antes de decidir el alcance, esta síntesis es explícita sobre los límites
(Sección IX.C, "When Not to Use a Graph"): *"Do not introduce a knowledge
graph merely because the system has agents. A graph may be unnecessary
when: tasks are independent, no cross-session state is required, answers
depend on one document, relations are fixed and simple, a relational table
answers every query, provenance is not needed, or extraction errors would
outweigh traversal value."* Y en la ruta de construcción práctica (Sección
VI.E, "Month 1: Wire Into a Graph"): *"Begin with versioned JSON or
relational tables. Store: entities, claims, sources, relations, artifacts,
agent runs, evaluations, versions, aliases, open questions. Add entity
extraction with Haiku and resolution with Sonnet. Attach provenance to
every edge."*

Para el corpus real de `DockerSwarmDocs` (9 páginas, relaciones declaradas
a mano en frontmatter, ya con `depends-on`/`used-by`/`see-also` explícitos)
la propia guía de la fuente ("relations are fixed and simple" → posible
candidato a NO necesitar grafo) compite con el hecho de que esas relaciones
YA se declaran hoy sin ningún sitio real que las materialice y permita
recorrerlas (traversal) — ninguna herramienta hoy responde "¿qué se rompe
si falla X?" sin que un humano lea 9 ficheros a mano. Se decide que ese
caso concreto (preguntas de cascada/impacto) SÍ justifica el grafo mínimo
descrito abajo, seleccionando explícitamente **solo la Capa 1** ("versioned
JSON... entity extraction... attach provenance to every edge" sin el paso
de extracción vía LLM) por ser la que la propia fuente describe como punto
de partida, 100% determinista y ya cubierta por datos reales existentes.

## Decision

**Ensamblar el grafo REAL (NetworkX `MultiDiGraph`, igual que describe la
síntesis para el paso de "Assembly" del Cookbook, Sección IV.C) a partir,
única y exclusivamente, del frontmatter YA existente y escrito a mano en
`DockerSwarmDocs`** — cero llamadas a modelo, cero extracción de texto
libre. Implementado en `scripts/graph/build_graph.py` +
`scripts/graph/query_graph.py`.

### Esquema aplicado (subconjunto de `schema/graph-vocabulary.md`)

| Campo de frontmatter | Nodo/arista construido |
| --- | --- |
| Cada página factual | Nodo `Entity`, id `{type}:{slug}` (mismo formato que ya usa `see-also` en el frontmatter real, p. ej. `"policy:compuertas-abiertas"` — no se inventa un esquema de ids nuevo) |
| `source-of-truth` | Nodo `Source` propio + arista `SUPPORTS` hacia la `Entity` |
| `depends-on: [X]` | Arista `DEPENDS_ON`: `Entity -> X` |
| `used-by: [X]` | Arista `DEPENDS_ON` invertida: `X -> Entity` (graph-vocabulary.md ya prescribe esta traducción exacta) |
| `related-runbooks`, `related-dashboards`, `see-also` | Arista `MENTIONS` |
| `related-alerts` | Nodo `Entity` de tipo `alert` (cadena libre, no resuelta contra otras páginas) + arista `MENTIONS` |
| `superseded-by: X` | Arista `SUPERSEDES`: `X -> Entity` |
| Página tipo "splash" (`index.md`, sin los 13 campos) | Excluida del grafo — comportamiento correcto según `CHECKPOINTS.md` de `DockerSwarmDocs`, C2, no un error |

### Verificación real contra el corpus (commit `8eb4497`)

Ejecutado de verdad, no simulado:

- **21 nodos, 44 aristas** (12 `Entity` + 9 `Source`; 30 `MENTIONS` + 9
  `SUPPORTS` + 5 `DEPENDS_ON`).
- **0 referencias colgantes**: cada `depends-on`/`used-by`/`see-also`/
  `superseded-by` de las 9 páginas reales resuelve a una entidad real del
  propio corpus — verificado programáticamente, no solo revisado a ojo.
- **2 entidades sin ninguna referencia entrante todavía** (hallazgo real,
  no un error del código): `architecture:adopcion-templatessd` (página
  nueva de esta misma sesión, ninguna otra página la referencia aún) y
  `runbook:observabilidad-backup` (consistente con lo que ya señalaba
  `astro.config.mjs` de `DockerSwarmDocs` sobre esa página: añadida en el
  PR #10 pero pendiente de integrarse en la navegación).
- **Consulta de cascada verificada con un ejemplo real**: `impact
  policy:compuertas-abiertas` devuelve correctamente, con cita de fuente en
  cada salto, que `service:catalogo-servicios`,
  `runbook:observabilidad-backup` y `architecture:agentes-operadores`
  dependen directamente, y `network:topologia-red` depende
  transitivamente (vía `catalogo-servicios`) — el mismo patrón de pregunta
  que ADR-0004 de `sistema-central-admin-servidor` ya proponía como
  ejemplo ("si cae timescaledb-0, ¿qué se rompe en cascada?"), aquí
  ejecutado de verdad sobre datos reales en vez de quedar como ejemplo
  hipotético.

### Bug encontrado y corregido: dirección de la relación en `impact()`/`path()`

Durante la verificación final de esta sesión (no en el desarrollo inicial)
se encontró un bug real, no hipotético, comparando a mano la salida de
`impact policy:compuertas-abiertas` contra el frontmatter real de
`observabilidad-backup.md`:

- La primera versión de `impact()` recorre un grafo `depends_reverse`
  (`v -> u` por cada arista original `u -> v DEPENDS_ON`, necesario para
  poder recorrer "qué depende de mí" en vez de "de qué dependo") y
  etiquetaba cada salto usando el **orden del recorrido** (`a -DEPENDS_ON->
  b`) en vez de la **dirección real declarada en el frontmatter**. El
  conjunto de entidades impactadas ya era correcto (eso se verificó primero,
  contrastando con `depends-on network:topologia-red` como comprobación
  cruzada); lo que estaba invertido era el texto de cada salto: para el
  salto de `observabilidad-backup`, la primera versión imprimía
  `"policy:compuertas-abiertas -DEPENDS_ON-> runbook:observabilidad-backup"`,
  cuando `observabilidad-backup.md` declara literalmente
  `depends-on: ["policy:compuertas-abiertas"]` — la relación real va al
  revés de lo impreso.
- `path()` tenía la misma clase de bug: calculaba el camino más corto sobre
  una vista **no dirigida** del grafo (correcto, para responder "¿hay
  conexión?" sin importar el sentido) pero luego reportaba `"from": a, "to":
  b"` con el orden de ESE recorrido no dirigido, incluso cuando la única
  arista real declarada iba de `b` a `a`. Caso de prueba que lo expone sin
  ambigüedad: `path policy:compuertas-abiertas runbook:observabilidad-backup`
  — solo existe la arista real `observabilidad-backup -> compuertas-abiertas`
  (nunca al revés), y la versión con el bug reportaba la dirección opuesta.
- Se consideró primero un parche mínimo (invertir solo el orden de
  impresión, citando igualmente `graph.nodes[b]`) pero se descartó por
  incorrecto: para las aristas `DEPENDS_ON` derivadas de `used-by` (p. ej.
  `diagnosticos-conocidos.md` declara `used-by:
  ["architecture:agentes-operadores"]`), el documento que de verdad declara
  la relación es el **destino** de la arista, no su origen — un parche
  puramente posicional habría citado el fichero equivocado en ese caso
  concreto. La corrección real fue añadir un atributo `claim_source` a cada
  arista en el único punto donde se sabe con certeza qué documento la
  declaró (`build_graph.py`, en el momento de crearla), y hacer que
  `impact()`/`path()` lean ese atributo en vez de re-inferir la dirección
  por la posición de los nodos en un recorrido.
- Verificado tras el arreglo: `impact policy:compuertas-abiertas` ahora
  imprime `"runbook:observabilidad-backup -DEPENDS_ON-> policy:compuertas-
  abiertas"` (dirección real); `path policy:compuertas-abiertas
  runbook:observabilidad-backup` ahora reporta la relación real en sentido
  `observabilidad-backup -> compuertas-abiertas`; e `impact
  runbook:diagnosticos-conocidos` cita `diagnosticos-conocidos.md` (quien
  declara `used-by`), no `agentes-operadores.md`. Los tres casos quedan
  fijados como regresión ejecutable en `scripts/graph/test_graph.py` (no
  solo verificados a mano una vez) para que este bug no pueda reaparecer sin
  que el test falle.

Se documenta este bug explícitamente, en vez de solo corregirlo en
silencio, por el mismo motivo que el resto de este ADR: en un pilot cuyo
propósito entero es citar con precisión de qué documento sale cada
relación, un error de dirección en esa cita es exactamente el tipo de fallo
que "0 errores" debe cubrir — encontrarlo y corregirlo en la verificación
final es el proceso funcionando como debe, no algo que convenga ocultar.

## Prueba de mutación

Añadida en una sesión posterior a la aceptación de este ADR — mismo
contexto y misma sesión que el bug de dirección documentado arriba (ver
`CHECKPOINTS.md`, C7, para el resumen y la tabla de los 4 ficheros del
pilot completo). El porqué de `scripts/mutate.py` en vez de `mutmut` (bloqueo
real encontrado y descartado) y el bug real encontrado en el propio mutador
(caché de bytecode dando falsos negativos, corregido en
`scripts/mutate.py`) están documentados una sola vez, en
`docs/adrs/0001-rag-pilot-lexical-retrieval.md`, sección "Prueba de
mutación" — aplican sin cambios a `scripts/graph/`, no se repiten aquí.

### Resultados: `scripts/graph/build_graph.py`

42 mutantes válidos, **19 muertos, score 45.2%**.

### Resultados: `scripts/graph/query_graph.py`

43 mutantes válidos, **20 muertos, score 46.5%**. Un superviviente cerrado
aparte de los ya aceptados abajo: `load_graph()` (deserializa `rag/graph.json`
de vuelta a un `MultiDiGraph`) y `graph_to_jsonable()` (su contraparte en
`build_graph.py`) no los ejercitaba ningún caso de `test_graph.py` — la
suite construye el grafo en memoria con `build_graph()` y consulta
directamente sobre ese objeto, sin pasar nunca por el camino real de
serializar a JSON y releer que sí usa `rag-pilot.yml` en producción
(`build_graph.py` escribe `rag/graph.json`, `query_graph.py --graph` lo
relee). Cerrado con un caso nuevo: construir el grafo, serializarlo con
`graph_to_jsonable()`, escribirlo a un fichero temporal, releerlo con
`load_graph()`, y comprobar que `impact(policy:compuertas-abiertas)` sobre
el grafo recargado da exactamente las mismas 4 entidades que sobre el grafo
en memoria (más una comprobación de `node_count`/`edge_count` del propio
dict serializado). Mata el mutante de `return graph, data -> return None` en
`load_graph()`; no mata los de `directed=True`/`multigraph=True` mutados a
`False` en la misma línea (ver "Por qué no se persigue el 100%" abajo — el
caso elegido no resulta ser sensible a esos dos parámetros concretos para
esta consulta concreta).

### Por qué no se persigue el 100%

Mismas categorías que ADR-0001 (solo-CLI, ramas defensivas para entrada que
el corpus real no produce, precisión de reporting), con dos matices propios
del grafo:

- **El bloque de despacho de `main()`** (`if args.command == "children":
  ... elif ... == "impact": ...` en `query_graph.py`) es la mayor
  concentración de supervivientes de los 4 ficheros (10 de 24) — es
  íntegramente CLI, `test_graph.py` llama a `children`/`impact`/`path`/etc.
  directamente, nunca a través de `args.command`.
- **Parámetros de deserialización no siempre sensibles al caso de prueba
  elegido** (`directed`/`multigraph` en `load_graph()`, ver arriba): cerrar
  esto de verdad exigiría un caso que dependa explícitamente de una arista
  paralela o de la direccionalidad para dar una respuesta distinta — más
  ingeniería de caso de prueba de la que este pilot justifica hoy, con un
  grafo de 21 nodos donde ese escenario no se ha dado todavía de forma
  natural.

No se persigue el 100% por el mismo motivo que en ADR-0001: la disciplina
de proporción al tamaño real del corpus (21 nodos, 44 aristas) que ya rige
el resto de esta decisión.

## Qué NO construye esta primera vuelta

- **Capa 2 (extraída vía LLM)**: la síntesis describe "Extraction (Haiku).
  Resolution (Sonnet)" para convertir prosa libre en entidades/relaciones
  nuevas. No implementado aquí — exigiría una llamada a modelo por
  documento, con su propio presupuesto y su propio riesgo de falsos
  positivos (ver la propia sección de la fuente sobre "Entity Resolution
  as a Reasoning Task" y sus fallos conocidos de fusión incorrecta). Añadir
  esto es un incremento futuro razonable, no simulado aquí con una
  heurística de recorte de texto que fingiera ser "extracción".
- **Capa 3 (inferencia multi-hop tipo Cognee)**: ADR-0004 del proyecto
  hermano ya la marca explícitamente como Fase 7, diferida. Este pilot no
  la adelanta.
- **Nodos `AgentRun`/`Evaluation`/`Task`/`Commit`/`Metric`**: el vocabulario
  los define, pero no hay hoy ninguna fuente declarativa de ese tipo de dato
  en `DockerSwarmDocs` (no son parte del contrato de 13 campos) — no se
  inventan a partir de nada.
- **Ninguna escritura a `DockerSwarmInfrastrcture` ni a `DockerSwarmDocs`**:
  este grafo es de solo lectura sobre lo que ya existe; no propone cambios
  ni PRs.

## Consequences

### Positivas

- 100% determinista, cero riesgo de alucinación (cada arista viene de una
  línea de frontmatter real, verificable con `git show`).
- Responde de verdad preguntas de cascada/impacto que hoy nadie puede
  responder sin leer 9 ficheros a mano.
- El hallazgo de "2 entidades sin referencia entrante" es información real
  y accionable sobre el propio estado de `DockerSwarmDocs`, obtenida gratis
  como subproducto de construir el grafo.

### Negativas

- Solo cubre lo que ya está declarado a mano — no descubre relaciones
  nuevas que un humano no haya escrito explícitamente en el frontmatter
  (esa es, precisamente, la Capa 2 que este ADR decide no construir
  todavía).
- El grafo (`rag/graph.json`) es, como el índice de ADR-0001, un artefacto
  generado bajo demanda, no comprometido a git (mismo razonamiento: se
  quedaría obsoleto sin un paso automático de regeneración, que es una
  decisión estructural futura sobre `daily-memory.yml`).

## Alternatives considered

1. **No construir ningún grafo, solo mantener el frontmatter como está** —
   descartado: es exactamente la brecha que el propio README de este repo
   ya señalaba como pendiente, y la fuente citada arriba confirma que las
   preguntas de cascada/impacto SÍ justifican el coste en este caso
   concreto.
2. **Construir ya la Capa 2 (extracción vía LLM)** — descartado para esta
   primera vuelta: mayor coste, mayor superficie de error (fusiones
   incorrectas de entidades, ver la propia fuente), y los datos
   declarativos ya existentes no están agotados como fuente de valor
   todavía.
3. **Grafo en una base de datos dedicada (Neo4j, etc.)** — descartado por
   la misma razón de proporción que ADR-0001: 21 nodos caben enteros en
   memoria: introducir un motor de grafos dedicado sería la misma clase de
   sobre-ingeniería que la fuente advierte evitar ("Do not introduce a
   knowledge graph merely because the system has agents").

## References

- Documento fuente: "Graph Engineering: The Karpathy Loop, Improved 1000x
  by Itself — The Anthropic Playbook" (síntesis independiente, julio 2026,
  no afiliada ni respaldada por Andrej Karpathy ni Anthropic — ver nota de
  procedencia arriba). Subido por Pablo a esta sesión.
- `schema/graph-vocabulary.md` de este mismo repo (vocabulario ya adoptado
  antes de este ADR).
- ADR-0004 de `apptolast/sistema-central-admin-servidor` (el ejemplo de
  cascada "timescaledb-0", aquí verificado con datos reales por primera
  vez).
- <https://networkx.org/> (MultiDiGraph, la misma librería que la fuente
  describe para el paso de ensamblado del Cookbook).

## Reversal triggers

Re-evaluar este ADR si:

- El número de páginas/relaciones crece lo suficiente como para que 21
  nodos en memoria deje de ser trivial (sin indicio de esto hoy).
- Se decide construir la Capa 2 (extracción vía LLM) — en ese momento,
  revisar si el esquema de ids (`{type}:{slug}`) sigue siendo suficiente o
  hace falta resolución de entidades de verdad (alias, duplicados).
- Se decide conectar este grafo a `daily-memory.yml` — igual que en
  ADR-0001, decisión estructural futura, no de este documento.
