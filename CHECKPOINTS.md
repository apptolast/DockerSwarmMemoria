# CHECKPOINTS — Evaluación del estado final

> Adaptación de `TemplateSSDUncleBob` para `DockerSwarmMemoria` — ver
> `docs/adopcion-templatessd.md` para el razonamiento de cada adaptación.
> Igual que en la plantilla original: no se evalúa el camino, se evalúa el
> destino. Mismos siete checkpoints (C1-C7); contenido adaptado al stack
> real de este bot (YAML + bash de GitHub Actions gobernado por
> `program.md`, sin `src/` en un lenguaje de propósito general).

## C1 — La capa de gobernanza del arnés está completa

- [ ] Existen `AGENTS.md`, `CLAUDE.md`, `CHECKPOINTS.md`,
      `harness.config.json`, `harness.schema.json` y
      `docs/adopcion-templatessd.md`.
- [ ] `harness.config.json` es JSON válido y valida contra
      `harness.schema.json`.
- [ ] `AGENTS.md` cita a `program.md` como contrato prioritario — no lo
      duplica ni lo contradice.

## C2 — El estado es coherente

- [ ] Como mucho una feature en `in_progress` **si** este repo llega a usar
      `feature_list.json` (ver C6). A fecha de esta adopción ese fichero no
      existe porque no hay ninguna feature estructural del bot en curso —
      ausencia esperada, no un hueco sin resolver.
- [ ] `memoria/logs/` y `memoria/estado/` siguen reflejando únicamente
      ejecuciones reales del workflow (nadie los ha editado a mano para
      simular estado).
- [ ] Ningún cambio de gobernanza del arnés modificó el contenido de
      `program.md`, `schema/graph-vocabulary.md` ni
      `.github/workflows/daily-memory.yml` (ver C3).

## C3 — El arnés respeta la arquitectura ya existente del bot

- [ ] `program.md` (contrato), `schema/graph-vocabulary.md` (vocabulario) y
      `.github/workflows/daily-memory.yml` (única lógica ejecutable) siguen
      exactamente como estaban antes de la adopción: el arnés documenta y
      estructura alrededor, no reescribe comportamiento de producción (ver
      `docs/adopcion-templatessd.md`).
- [ ] Ningún fichero nuevo de esta adopción se declara "mutable" ni
      "protegido" en contradicción con lo que ya fija `program.md` §3.

## C4 — La verificación es real

- [ ] `harness.config.json` → `commands.test` es `actionlint` (el linter
      real y estándar para workflows de GitHub Actions) — no una cadena
      vacía disfrazada de verde, ni un script inventado sin herramienta real
      detrás.
- [ ] Cualquier cambio futuro a `.github/workflows/daily-memory.yml` pasa
      `actionlint` limpio antes de proponerse en un PR.
- [ ] Se reconoce la verificación de nivel más alto que ya existe en
      producción: los gates propios del workflow (circuit-breaker,
      PR-única-abierta, `verify-build`) y la revisión humana de cada PR. El
      arnés no la sustituye, la nombra y se apoya en ella.

## C5 — La sesión se cerró bien

- [ ] No quedan archivos temporales de la sesión (p. ej. `.memoria-cache/`
      sin trackear, si el paso 2bis llegó a ejecutarse).
- [ ] `.gitignore` excluye `.memoria-cache/`.
- [ ] Los cambios están en una rama propia (`feat/...`), con commits en
      Conventional Commits, sin tocar `main` directamente.

## C6 — Contrato Gherkin (BDD) — condicional, hoy no aplica

- [ ] **No aplica todavía, y esa ausencia es intencional.** Este repo no
      vendoriza `feature_list.json` / `project-spec.md` / `features/` /
      `progress/` (ver `docs/adopcion-templatessd.md`, "Qué no se
      vendoriza"). El día que una feature estructural de este bot use el
      pipeline completo, esos ficheros se toman de `TemplateSSDUncleBob` en
      ese momento — con sus escenarios `@s1..@sn` y el mapa
      `@s → verificación` que exige la plantilla original — no se
      fabrican de antemano solo para marcar esta casilla.

## C7 — Prueba de mutación

- [x] **Para `.github/workflows/daily-memory.yml` (YAML + bash, producción):
      sigue sin aplicar, sin cambios.** No existe una herramienta de
      mutación real para YAML/bash de GitHub Actions (a diferencia de
      StrykerJS, gremlins, cargo-mutants o PIT en lenguajes de propósito
      general). Ver `docs/adopcion-templatessd.md`, sección "Por qué no hay
      mutación".
- [x] **Para `scripts/rag/` y `scripts/graph/` (Python real, añadido en el
      pilot de RAG + grafo): implementada de verdad y corriendo, con
      `scripts/mutate.py` — no `mutmut`.** Este repo dejó de estar cubierto
      por la razón de arriba en cuanto ganó código fuente propio en un
      lenguaje de propósito general (el disparador que esta misma sección
      pedía vigilar — ver nota al final de este documento). El primer
      intento real fue con `mutmut` 3.7.0 (PyPI): instala limpio en este
      sandbox, pero se encontró un bloqueo de estructura real y reproducido
      (su sandboxing en `mutants/` no descubre tests anidados junto a su
      propio código fuente, y la ruta relativa de profundidad fija que usan
      esos tests para localizar el checkout hermano de `DockerSwarmDocs` se
      rompe dentro de esa copia anidada). En vez de reestructurar el repo
      para acomodar una herramienta de terceros concreta, se adaptó el
      mutador propio que ya prescribe `TemplateSSDUncleBob`
      (`examples/python-notes-cli/tools/mutate.py`: mutación a nivel de
      token, sin sandboxing, muta el fichero real en su sitio y lo restaura
      siempre) como `scripts/mutate.py` de este repo — sin ese sandboxing no
      hay clase de bloqueo que evitar. Resultados reales, verificados
      (detalle completo, incluida la triage de cada superviviente, en
      `docs/adrs/0001-rag-pilot-lexical-retrieval.md` y
      `docs/adrs/0002-graph-assembly-declarative-layer.md`, sección "Prueba
      de mutación" de cada una):
      | Fichero | Mutantes | Muertos | Score |
      | --- | --- | --- | --- |
      | `scripts/rag/query.py` | 44 | 18 | 40.9% |
      | `scripts/rag/build_index.py` | 47 | 19 | 40.4% |
      | `scripts/graph/build_graph.py` | 42 | 19 | 45.2% |
      | `scripts/graph/query_graph.py` | 43 | 20 | 46.5% |

      No se persigue el 100%: la mayoría de los supervivientes son código
      solo-CLI que esta suite (deliberadamente ligera, no exhaustiva por
      diseño — ver docstring de cada test) no ejercita, ramas defensivas
      para frontmatter malformado que el corpus real nunca produce, o
      precisión de redondeo/reporting nunca comprobada byte a byte. El único
      hallazgo de alto valor real (la doble guarda anti-alucinación de
      `answer()` en `query.py` podía degradarse de `or` a `and` sin que
      ningún test lo notara) sí se cerró con un caso de calibración nuevo —
      ver las ADR.

## C7bis — Bug real encontrado en el propio mutador

Durante esta implementación, `scripts/mutate.py` reportó al principio una
puntuación mucho más baja de la real (6.8%, 3/44, en `query.py`) que
contradecía una verificación manual independiente de uno de los mutantes.
Investigado a fondo (no descartado como ruido): el bytecode cacheado por
CPython (`__pycache__/*.pyc`) podía sobrevivir entre dos mutantes sucesivos
cuando la resolución de mtime del filesystem de este sandbox es más gruesa
que el tiempo entre dos escrituras del bucle de mutación — el subproceso de
test cargaba código de un mutante anterior en vez del que `main()` acababa
de escribir. Corregido en el propio `scripts/mutate.py`
(`PYTHONDONTWRITEBYTECODE=1` forzado en cada subproceso de test +
`__pycache__` borrado antes de empezar) — puntuación real tras el arreglo:
40.9%, no 6.8%. Ver el docstring de `run_tests()`/`clear_pycache()` en
`scripts/mutate.py` para el detalle completo. Se documenta aquí porque es
exactamente el tipo de hallazgo que C7 existe para forzar a encontrar: sin
correr la herramienta de verdad contra un caso ya verificado a mano, este
falso negativo habría quedado sin detectar.

---

**Cómo usar este archivo:** quien revise un cambio a este repo (humano o
agente) recorre C1-C7. A diferencia de la plantilla original, C6 aquí
documenta una ausencia **deliberada y justificada** (no una casilla vacía
por descuido), y C7 en `scripts/rag`/`scripts/graph` documenta una prueba de
mutación real, implementada y corriendo (no un "no aplica" reflejo, ni un
bloqueo sin resolver). El disparador que este párrafo pedía vigilar ("el bot
gana código fuente propio en un `src/` genuino") ya se activó, con ese
pilot, y C7 se actualizó en consecuencia dos veces — primero documentando el
bloqueo real de `mutmut`, después reemplazando esa entrada al comprobar que
el mutador propio de la plantilla sí funciona aquí — en vez de dejarse
desactualizada. La próxima vez que algo similar ocurra (nueva herramienta de
mutación real para Actions, o `scripts/rag`/`scripts/graph` crecen lo
bastante como para que valga la pena perseguir más supervivientes),
**actualiza esta sección primero**, no la dejes desactualizada.
