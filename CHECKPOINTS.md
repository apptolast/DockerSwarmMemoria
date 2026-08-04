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

## C7 — Prueba de mutación — no aplica, con razón explícita

- [ ] `harness.config.json` → `rules.require_mutation_to_close` es `false`
      y `commands.mutate` está vacío, **a propósito**: no existe una
      herramienta de mutación real para YAML/bash de GitHub Actions (a
      diferencia de StrykerJS, gremlins, cargo-mutants o PIT en lenguajes de
      propósito general) y este repo no tiene código fuente propio que
      mutar. Ver `docs/adopcion-templatessd.md`, sección "Por qué no hay
      mutación", antes de "arreglar" esta casilla con un comando inventado.

---

**Cómo usar este archivo:** quien revise un cambio a este repo (humano o
agente) recorre C1-C7. A diferencia de la plantilla original, C6 y C7 aquí
documentan una ausencia **deliberada y justificada**, no una casilla vacía
por descuido. Si alguna vez dejan de estar justificadas — por ejemplo, si
aparece una herramienta de mutación real para Actions, o el bot gana código
fuente propio en un `src/` genuino — **actualiza esta sección primero**, no
la dejes desactualizada.
