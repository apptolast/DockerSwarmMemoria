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
- [ ] **Para `scripts/rag/` y `scripts/graph/` (Python real, añadido en el
      pilot de RAG + grafo de esta sesión): intentado de verdad con una
      herramienta real, bloqueado por una incompatibilidad de estructura
      concreta — no simplemente omitido.** Este repo dejó de estar cubierto
      por la razón de arriba en cuanto ganó código fuente propio en un
      lenguaje de propósito general (exactamente el disparador que esta
      misma sección pedía vigilar — ver nota al final de este documento).
      Antes de escribir esta casilla como "no aplica" otra vez, se intentó
      de verdad:
      - Se instaló `mutmut` 3.7.0 (PyPI, la misma familia de herramienta que
        StrykerJS/gremlins/cargo-mutants/PIT para Python) — instala limpio
        en este sandbox (a diferencia de `actionlint` vía `go install`, ver
        `docs/adopcion-templatessd.md`).
      - `source_paths` (config real, `setup.cfg`) localiza y muta
        correctamente los 4 módulos reales (`build_index.py`, `query.py`,
        `build_graph.py`, `query_graph.py`) — verificado, no simulado.
      - Se añadieron envoltorios pytest triviales (`test_calibration_regression`,
        `test_graph_regression`) sobre los `main()` ya existentes, para que
        una herramienta basada en pytest pudiera ejecutar la regresión real
        sin reescribirla — estos envoltorios SÍ se conservan en el repo
        (son útiles por sí mismos con cualquier runner pytest, no solo con
        `mutmut`) aunque `mutmut` en sí no se haya adoptado.
      - **Bloqueo real encontrado** (reproducido, no hipotético): `mutmut`
        ejecuta los tests dentro de una copia aislada del repo
        (`mutants/`), y solo copia a esa copia los ficheros de test que
        vivan en una carpeta `tests/`/`test/` o que coincidan con el patrón
        `test*.py` **en la raíz del repo** (código fuente de `mutmut`,
        `configuration.py`, lista `also_copy`) — no descubre tests
        anidados junto a su propio código fuente, que es exactamente cómo
        vive `test_calibration.py`/`test_graph.py` en este repo (junto a
        `build_index.py`/`build_graph.py`, no en una carpeta `tests/`
        separada). Añadir esos ficheros a mano vía `also_copy` resuelve la
        copia, pero expone un segundo problema: `DEFAULT_DOCS_PATH` en
        ambos tests localiza el checkout hermano de `DockerSwarmDocs` con
        una ruta relativa a `Path(__file__).parent` de profundidad fija
        (`../../../DockerSwarmDocs/...`) — profundidad que asume que el
        fichero vive exactamente 3 niveles bajo el repo. Dentro de
        `mutants/`, `mutmut` inserta un nivel adicional de anidamiento, así
        que esa misma ruta relativa deja de apuntar al checkout real.
      - **Por qué no se fuerza un arreglo aquí**: solucionarlo exigiría o
        bien reestructurar dónde viven los tests de este repo (mover
        `test_calibration.py`/`test_graph.py` a una carpeta `tests/`
        separada, rompiendo la convención ya usada en el resto de esta
        entrega y en `AGENTS.md`/los dos READMEs de `scripts/`), o bien
        cambiar cómo estos tests localizan el corpus hermano (p. ej. una
        variable de entorno en vez de una ruta relativa de profundidad
        fija) — ambos cambios modificarían código de producción de este
        pilot solo para acomodar el modelo de sandboxing de una herramienta
        de desarrollo concreta, exactamente la clase de sobre-ingeniería
        que `docs/adrs/0001-*.md` y `0002-*.md` ya deciden evitar en otros
        puntos de este mismo pilot.
      - **Disparador de revisión**: si `scripts/rag`/`scripts/graph` crecen
        lo suficiente como para que la ausencia de mutation testing deje de
        ser proporcional, o si este repo adopta una carpeta `tests/`
        convencional por otro motivo (con lo que el primer bloqueo
        desaparecería solo), revisar esta casilla primero.

---

**Cómo usar este archivo:** quien revise un cambio a este repo (humano o
agente) recorre C1-C7. A diferencia de la plantilla original, C6 y C7 aquí
documentan una ausencia **deliberada y justificada** (o, para C7 en
`scripts/rag`/`scripts/graph` desde el pilot de RAG + grafo, un intento real
y un bloqueo concreto documentado — no un "no aplica" reflejo), no una
casilla vacía por descuido. El disparador que este párrafo pedía vigilar
("el bot gana código fuente propio en un `src/` genuino") ya se activó una
vez, con ese pilot, y C7 se actualizó en consecuencia en vez de dejarse
desactualizado — la próxima vez que algo similar ocurra (nueva herramienta
de mutación real para Actions, o este mismo bloqueo de estructura
desaparece), **actualiza esta sección primero**, no la dejes desactualizada.
