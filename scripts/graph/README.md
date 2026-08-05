# scripts/graph/ — Grafo de conocimiento declarativo (Capa 1) de `DockerSwarmDocs`

Ensambla en un grafo real (NetworkX `MultiDiGraph`) las relaciones que ya
existen hoy, a mano, en el frontmatter YAML de cada página de
`apptolast/DockerSwarmDocs` — sin ninguna llamada a modelo, 100%
determinista. Razonamiento completo: [`docs/adrs/0002-graph-assembly-declarative-layer.md`](../../docs/adrs/0002-graph-assembly-declarative-layer.md)
(raíz del repo). Vocabulario de nodos/aristas: [`schema/graph-vocabulary.md`](../../schema/graph-vocabulary.md)
(ya existente en este repo, anterior a este pilot).

Única dependencia externa: `networkx` (ver `requirements.txt`).

## Instalación

```bash
pip install -r scripts/graph/requirements.txt
```

## Requisito para ejecutar estos scripts localmente

Igual que `scripts/rag/` (ver su propio README): un checkout hermano de
`apptolast/DockerSwarmDocs`, junto a este repo.

## Uso

Construir el grafo desde el corpus real:

```bash
cd scripts/graph
python3 build_graph.py \
  --docs-path ../../../DockerSwarmDocs/src/content/docs \
  --output ../../rag/graph.json
```

Añade `--fail-on-dangling` para que el proceso termine con código 1 si
alguna referencia (`depends-on`/`used-by`/`see-also`/`superseded-by`) no
resuelve a una entidad real del corpus.

Consultar el grafo ya construido (subcomandos, estilo `ah` CLI — ver
ADR-0002):

```bash
# Qué depende DIRECTAMENTE de esta entidad
python3 query_graph.py --graph ../../rag/graph.json children policy:compuertas-abiertas

# Cierre transitivo de qué se rompe en cascada si esta entidad falla
python3 query_graph.py --graph ../../rag/graph.json impact policy:compuertas-abiertas

# De qué depende esta entidad, transitivamente (lo contrario de impact)
python3 query_graph.py --graph ../../rag/graph.json depends-on network:topologia-red

# Camino más corto entre dos entidades, con cita de fuente real en cada salto
python3 query_graph.py --graph ../../rag/graph.json path architecture:introduccion network:topologia-red

# Entidades de las que nada depende
python3 query_graph.py --graph ../../rag/graph.json leaves
```

## Contrato de citación

Toda arista devuelta por `query_graph.py` cita el documento que **de verdad
declaró** esa relación en su frontmatter (atributo `claim_source` en cada
arista, fijado en `build_graph.py` en el momento de crearla) — nunca se
infiere ni se inventa una relación que no esté ya escrita a mano en algún
`.md` real. Si no hay camino entre dos entidades, `path` lo dice
explícitamente en vez de forzar una respuesta.

**Nota de fiabilidad**: una versión anterior de `impact()`/`path()` (dentro
de esta misma sesión, corregida antes de esta entrega) etiquetaba la
dirección de la relación según el orden del recorrido interno en vez de
según la dirección real declarada en el frontmatter — el conjunto de
entidades devueltas ya era correcto, pero el texto de cada salto podía leer
la relación al revés. Ver ADR-0002, sección "Bug encontrado y corregido",
para el caso real que lo expuso y la corrección aplicada. Queda fijado como
regresión ejecutable en `test_graph.py` (los tres casos con
`-DEPENDS_ON->`/`claim_source` en su nombre).

## Qué NO hace este grafo (Capa 1 solamente)

- Ninguna extracción vía LLM (Capa 2) ni inferencia multi-hop (Capa 3) — ver
  ADR-0002, "Qué NO construye esta primera vuelta".
- Ninguna escritura a `DockerSwarmInfrastrcture` ni a `DockerSwarmDocs`: de
  solo lectura sobre lo que ya existe.

## Verificación

```bash
python3 test_graph.py
```

Reconstruye el grafo desde el corpus real y comprueba 12 aserciones ya
verificadas a mano: conteo de nodos/aristas, 0 referencias colgantes, las 2
entidades sin referencia entrante conocidas, `leaves()`/`children()`/
`depends-on()` exactos, la cascada completa de `impact()`, y los 3 casos de
regresión del bug de dirección. Si el checkout hermano de `DockerSwarmDocs`
no existe, el test se salta con aviso explícito y sale con código 0 (mismo
criterio que `scripts/rag/test_calibration.py`).

## Ficheros

| Fichero | Qué hace |
| --- | --- |
| `build_graph.py` | Construye `rag/graph.json` desde el frontmatter de `DockerSwarmDocs`. Expone `never_referenced_entities()` como diagnóstico de salud del grafo. |
| `query_graph.py` | Consultas de traversal (`children`, `impact`, `depends-on`, `path`, `leaves`) sobre el grafo ya construido. |
| `test_graph.py` | Regresión ejecutable, incluida la del bug de dirección corregido en esta sesión. |
| `requirements.txt` | Única dependencia: `networkx`. |

`rag/graph.json` es un artefacto generado, no comprometido a git (ver
`.gitignore`) — se regenera bajo demanda o en CI (ver
`.github/workflows/rag-pilot.yml`).
