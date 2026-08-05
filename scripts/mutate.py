#!/usr/bin/env python3
"""mutate.py — Mutador mínimo y sin dependencias externas para scripts/rag/
y scripts/graph/, adaptado de
`examples/python-notes-cli/tools/mutate.py` de
`Cenit-Digital/TemplateSSDUncleBob` (MIT license, Copyright (c) 2026 Cenit
Digital — ver ese repo para el original completo).

Por qué este mutador y no una herramienta de terceros (`mutmut`, PyPI): se
intentó primero `mutmut` de verdad (instala limpio en este sandbox) y se
encontró un bloqueo real, reproducido, no hipotético — su modelo de
sandboxing (`mutants/`, una copia aislada del repo) solo copia a esa copia
los ficheros de test que vivan en `tests/`/`test/` o que coincidan con
`test*.py` **en la raíz del repo**, no anidados junto a su propio código
fuente (que es como viven `test_calibration.py`/`test_graph.py` aquí); y
aunque se resuelva copiándolos a mano (`also_copy`), la ruta relativa de
profundidad fija que usan para localizar el checkout hermano de
`DockerSwarmDocs` deja de apuntar al sitio correcto dentro de esa copia
anidada. Ver `docs/adrs/0002-graph-assembly-declarative-layer.md` y
`CHECKPOINTS.md` (C7) para el relato completo de ese intento.

Este mutador evita esa clase entera de problema por diseño: NO crea ninguna
copia aislada del repo. Muta el fichero real en su sitio, corre el comando
de test que se le indique, y restaura el original siempre (bloque
`finally`) — sin sandboxing, sin asunciones sobre dónde viven los tests ni
sobre qué framework los ejecuta. A diferencia del original de
`python-notes-cli` (que asume `python -m unittest discover -s tests`, fijo),
aquí `--test-cmd` es obligatorio: este repo no usa unittest, sus tests son
scripts propios (`test_calibration.py`, `test_graph.py`) que ya devuelven
0/1 por código de salida — el mismo principio que ya declara
`harness.config.json` de la plantilla original ("el arnés no impone un
mutador: cada stack declara el suyo"), aplicado aquí a nivel de invocación
en vez de config, porque este repo no vendoriza `harness.config.json` →
`commands.mutate` con un único comando fijo (dos test suites distintas,
una por área mutada).

Diseño (idéntico al original, ver docs/mutation-testing.md de la plantilla):
- Trabaja a nivel de *token* (módulo `tokenize`): nunca muta el contenido de
  strings ni comentarios, solo operadores, palabras clave, números y
  sentencias `return`.
- Descarta los mutantes que no compilan (no inflan la puntuación).
- Restaura SIEMPRE el archivo original, incluso ante Ctrl-C.
- Difiere del original en un punto añadido tras un bloqueo real encontrado
  en este sandbox (no en la plantilla, que muta un único fichero por
  ejecución de CI limpia y no lo sufre igual): fuerza
  `PYTHONDONTWRITEBYTECODE=1` en cada subproceso de test y borra
  `__pycache__` antes de empezar (ver `run_tests()`/`clear_pycache()`) para
  que el caché de bytecode de CPython nunca esconda el mutante que
  realmente está en disco. Sin esto, la puntuación medida puede ser
  drásticamente más baja que la real (18/44 detectados de verdad frente a
  3/44 con caché habilitado en la primera corrida de `scripts/rag/query.py`
  — ver docs/adrs/0001-rag-pilot-lexical-retrieval.md, "Prueba de
  mutación").

Uso:
    python3 scripts/mutate.py scripts/rag/query.py \
        --test-cmd "python3 scripts/rag/test_calibration.py"
    python3 scripts/mutate.py scripts/graph/query_graph.py \
        --test-cmd "python3 scripts/graph/test_graph.py" --max 60
"""
from __future__ import annotations

import argparse
import io
import os
import shlex
import shutil
import subprocess
import sys
import tokenize
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

OP_MUTATIONS = {
    "<=": "<",
    ">=": ">",
    "<": "<=",
    ">": ">=",
    "==": "!=",
    "!=": "==",
    "+": "-",
    "-": "+",
}

NAME_MUTATIONS = {
    "and": "or",
    "or": "and",
    "True": "False",
    "False": "True",
}


class Mutant:
    """Una única mutación: reemplaza un span (línea, col) del fuente."""

    def __init__(self, row: int, col_start: int, col_end: int,
                 original: str, replacement: str, label: str):
        self.row = row
        self.col_start = col_start
        self.col_end = col_end
        self.original = original
        self.replacement = replacement
        self.label = label

    def apply(self, lines: list[str]) -> str:
        out = list(lines)
        line = out[self.row - 1]
        out[self.row - 1] = line[: self.col_start] + self.replacement + line[self.col_end:]
        return "".join(out)

    def describe(self, path: str) -> str:
        return f"{path}:{self.row}  {self.label}  ({self.original!r} -> {self.replacement!r})"


def _int_mutation(literal: str) -> str | None:
    try:
        value = int(literal, 0)
    except ValueError:
        return None
    return str(value + 1)


def generate_mutants(source: str) -> list[Mutant]:
    mutants: list[Mutant] = []
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except tokenize.TokenError:
        return mutants

    for tok in tokens:
        if tok.start[0] != tok.end[0]:
            continue
        row = tok.start[0]
        col_start, col_end = tok.start[1], tok.end[1]
        text = tok.string

        if tok.type == tokenize.OP and text in OP_MUTATIONS:
            mutants.append(Mutant(row, col_start, col_end, text,
                                  OP_MUTATIONS[text], "operador"))
        elif tok.type == tokenize.NAME and text in NAME_MUTATIONS:
            mutants.append(Mutant(row, col_start, col_end, text,
                                  NAME_MUTATIONS[text], "palabra"))
        elif tok.type == tokenize.NUMBER:
            repl = _int_mutation(text)
            if repl is not None:
                mutants.append(Mutant(row, col_start, col_end, text,
                                      repl, "número"))

    lines = source.splitlines(keepends=True)
    for idx, raw in enumerate(lines, start=1):
        stripped = raw.lstrip()
        if not stripped.startswith("return "):
            continue
        rest = stripped[len("return "):].strip()
        if rest in ("", "None"):
            continue
        indent = len(raw) - len(stripped)
        content = raw.rstrip("\n")
        mutants.append(
            Mutant(idx, indent, len(content),
                   content[indent:], "return None", "retorno")
        )
    return mutants


def compiles(source: str, path: str) -> bool:
    try:
        compile(source, path, "exec")
        return True
    except SyntaxError:
        return False


def run_tests(test_cmd: list[str]) -> bool:
    """Ejecuta la suite en un subproceso nuevo (aislamiento real de estado en
    memoria: cada mutante se evalúa en un intérprete Python distinto).

    `PYTHONDONTWRITEBYTECODE=1` es obligatorio aquí, no cosmético: cada
    iteración del bucle en `main()` reescribe `args.path` en el sitio y
    vuelve a invocar `test_cmd` en milisegundos. Si el subproceso escribe
    `__pycache__/*.pyc`, el chequeo de validez de ese caché (mtime del
    fuente) puede no distinguir dos mutantes sucesivos cuando la resolución
    de mtime del filesystem es más gruesa que el tiempo entre escrituras —
    visto de verdad en este sandbox: sin esta variable, un mutante ya
    confirmado a mano como detectable (el `or`→`and` de
    `scripts/rag/query.py:128`, ver docs/adrs/0001-rag-pilot-lexical-
    retrieval.md, "Prueba de mutación") aparecía como "SOBREVIVE" (18/44
    detectados, 40.9%, subían a 41/44 sobrevivientes, 6.8%, con caché
    habilitado) porque el subproceso cargaba bytecode de un mutante anterior
    en vez del que `main()` acababa de escribir. `clear_pycache()` (ver
    abajo) cubre el caso complementario: un `.pyc` que ya existiera ANTES de
    empezar esta ejecución, que esta variable por sí sola no invalida.
    """
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    result = subprocess.run(test_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
    return result.returncode == 0


def clear_pycache(target: str) -> None:
    """Borra `__pycache__/` junto al fichero mutado antes de empezar.

    Complementa (no sustituye) `PYTHONDONTWRITEBYTECODE=1` en `run_tests()`:
    esa variable evita que se ESCRIBAN cachés nuevos durante el bucle de
    mutación, pero no invalida uno que ya existiera de una ejecución normal
    previa (p. ej. alguien corrió `python3 scripts/rag/test_calibration.py`
    a mano antes de mutar). Sin este borrado, ese `.pyc` preexistente podría
    seguir pareciendo válido para el chequeo de mtime del importador incluso
    con la variable puesta, y el primer mutante evaluado partiría de
    bytecode que no es el suyo.
    """
    cache_dir = Path(target).resolve().parent / "__pycache__"
    if cache_dir.is_dir():
        shutil.rmtree(cache_dir)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", help="Archivo a mutar (scripts/rag/*.py o scripts/graph/*.py).")
    parser.add_argument("--test-cmd", required=True,
                        help='Comando que corre la suite relevante, p. ej. "python3 scripts/rag/test_calibration.py"')
    parser.add_argument("--max", type=int, default=200,
                        help="Máximo de mutantes a evaluar (default 200).")
    args = parser.parse_args(argv)
    test_cmd = shlex.split(args.test_cmd)

    with open(args.path, "r", encoding="utf-8") as f:
        original = f.read()
    lines = original.splitlines(keepends=True)

    clear_pycache(args.path)

    if not run_tests(test_cmd):
        print("[FAIL] La suite está roja sin mutar. Arregla los tests primero.",
              file=sys.stderr)
        return 2

    mutants = generate_mutants(original)
    valid = [m for m in mutants if compiles(m.apply(lines), args.path)]
    skipped_noncompile = len(mutants) - len(valid)

    truncated = 0
    if len(valid) > args.max:
        truncated = len(valid) - args.max
        valid = valid[: args.max]

    killed: list[Mutant] = []
    survived: list[Mutant] = []

    print(f"── Mutando {args.path} ─ {len(valid)} mutantes válidos "
          f"({skipped_noncompile} descartados por no compilar)")
    try:
        for i, m in enumerate(valid, start=1):
            with open(args.path, "w", encoding="utf-8") as f:
                f.write(m.apply(lines))
            if run_tests(test_cmd):
                survived.append(m)
                mark = "SOBREVIVE"
            else:
                killed.append(m)
                mark = "muerto"
            print(f"  [{i}/{len(valid)}] {mark:9} {m.describe(args.path)}")
    finally:
        with open(args.path, "w", encoding="utf-8") as f:
            f.write(original)

    total = len(valid)
    score = (len(killed) / total * 100) if total else 100.0

    print("\n── Resumen ──────────────────────────────────────")
    print(f"  total:    {total}")
    print(f"  killed:   {len(killed)}")
    print(f"  survived: {len(survived)}")
    print(f"  score:    {score:.1f}%")
    if truncated:
        print(f"  [WARN] {truncated} mutantes válidos NO evaluados "
              f"(límite --max={args.max}). Sube --max para cobertura total.")
    if survived:
        print("\n  Mutantes sobrevivientes (agujeros en la red):")
        for m in survived:
            print(f"   - {m.describe(args.path)}")

    return 0 if not survived else 1


if __name__ == "__main__":
    sys.exit(main())
