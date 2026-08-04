# scripts/rag/ — Recuperación léxica (BM25) sobre `DockerSwarmDocs`

Pilot de RAG (Retrieval-Augmented Generation) para `apptolast/DockerSwarmDocs`.
Razonamiento completo de por qué BM25 léxico y no embeddings neuronales en
esta primera vuelta: [`docs/adrs/0001-rag-pilot-lexical-retrieval.md`](../../docs/adrs/0001-rag-pilot-lexical-retrieval.md)
(raíz del repo).

Cero dependencias externas: solo la librería estándar de Python 3.12+. No
hace falta `pip install` nada, ni red, para construir ni para consultar el
índice.

## Requisito para ejecutar estos scripts localmente

Un checkout hermano de `apptolast/DockerSwarmDocs`, junto a este repo:

```
apptolast/
├── DockerSwarmMemoria/   (este repo)
└── DockerSwarmDocs/      (checkout hermano — corpus real)
```

Esto es exactamente lo que hace `.github/workflows/rag-pilot.yml` en CI
(checkout de ambos repos a rutas separadas dentro del runner).

## Uso

Construir el índice desde el corpus real:

```bash
cd scripts/rag
python3 build_index.py \
  --docs-path ../../../DockerSwarmDocs/src/content/docs \
  --output ../../rag/index.json
```

Consultar el índice ya construido:

```bash
python3 query.py --index ../../rag/index.json --question "¿Qué hostname usa el servicio kropia?"
```

Salida como JSON crudo (para consumo programático):

```bash
python3 query.py --index ../../rag/index.json --question "..." --json
```

## Contrato de la respuesta

- Toda cita usa el formato `[source: path/al/fichero.md#seccion@commitsha]`
  — el mismo formato ya usado por `apptolast/sistema-central-admin-servidor`
  (ver ADR-0001, "Formato de citación").
- Si el mejor resultado no supera el umbral calibrado (`DEFAULT_THRESHOLD =
  6.0`) o no alcanza el mínimo de términos distintos coincidentes
  (`MIN_MATCHED_TERMS = 2`), la respuesta es literalmente **"No encuentro
  evidencia documentada sobre eso."** — nunca se sintetiza una respuesta con
  conocimiento general del modelo. Ver ADR-0001, "Calibración del umbral",
  para el razonamiento de esos dos valores y el caso real ("pablo") que
  motivó el segundo umbral.
- Este script **solo recupera** (retrieval); no invoca ningún LLM para
  redactar una respuesta en prosa a partir de los chunks. Ver ADR-0001, "Qué
  no incluye esta primera vuelta".

## Limitación conocida (documentada, no oculta)

Una pregunta legítima sobre contenido que NO está en el corpus, pero que
menciona por nombre un sustantivo compuesto que sí aparece como enlace
incidental en algún chunk (p. ej. el nombre de otro repo de la
organización), puede devolver `CITED` con chunks irrelevantes. Ver ADR-0001,
"Limitaciones conocidas", para el caso real documentado y por qué no se
"arregla" con un parche ad-hoc. `test_calibration.py` ejecuta e informa este
caso explícitamente, pero no cuenta como fallo del test — ver
`KNOWN_LIMITATION_CASE` en ese fichero.

## Verificación

```bash
python3 test_calibration.py
```

Reconstruye el índice desde el corpus real y comprueba 7 casos de
calibración ya verificados a mano (4 `CITED` con el chunk correcto exacto, 3
`NO_EVIDENCE` correctos). Si el checkout hermano de `DockerSwarmDocs` no
existe, el test se salta con aviso explícito y sale con código 0 — no
fabrica un resultado que no puede verificar de verdad (mismo criterio que
`program.md` §6 de este repo).

## Ficheros

| Fichero | Qué hace |
| --- | --- |
| `build_index.py` | Construye `rag/index.json` desde los `.md` de `DockerSwarmDocs`: tokeniza, trocea por sección H2, calcula frecuencias de término. |
| `query.py` | Consulta el índice con BM25 (parámetros Okapi estándar, k1=1.5, b=0.75), aplica el doble umbral anti-alucinación, y formatea las citas. |
| `test_calibration.py` | Regresión ejecutable de la calibración descrita en ADR-0001. |

`rag/index.json` es un artefacto generado, no comprometido a git (ver
`.gitignore`) — se regenera bajo demanda o en CI (ver
`.github/workflows/rag-pilot.yml`).
