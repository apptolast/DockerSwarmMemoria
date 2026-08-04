#!/usr/bin/env python3
"""test_calibration.py — Prueba de regresión para el pilot de RAG.

No es una suite de tests unitarios exhaustiva de cada función: es la
constancia ejecutable de la calibración descrita en
`docs/adrs/0001-rag-pilot-lexical-retrieval.md` ("Calibración del umbral").
Reconstruye el índice desde el corpus real de `DockerSwarmDocs` y verifica
que las preguntas de calibración devuelven el estado (`CITED` /
`NO_EVIDENCE`) esperado — para que un cambio futuro al chunker, al umbral o
a los parámetros BM25 no rompa en silencio los casos ya verificados a mano.

Requiere un checkout de `apptolast/DockerSwarmDocs` como carpeta hermana
(`../DockerSwarmDocs`) — igual que espera `build_index.py` por defecto. Si no
existe, el test se salta con aviso explícito en vez de fallar en rojo por una
causa ajena a este código (mismo criterio que `program.md` §6: no simular
un resultado que no se pudo verificar de verdad).

Uso:
    python3 test_calibration.py
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build_index import build_index  # noqa: E402
from query import answer  # noqa: E402

DEFAULT_DOCS_PATH = Path(__file__).parent / "../../../DockerSwarmDocs/src/content/docs"

# (pregunta, estado_esperado, chunk_id_top_esperado_o_None)
# chunk_id_top_esperado se comprueba solo cuando el estado esperado es CITED,
# y solo para los casos donde ya se verificó a mano que ese es el chunk
# correcto (ver docs/adrs/0001-rag-pilot-lexical-retrieval.md).
CASES = [
    ("¿Qué VPS y proveedor usa la infraestructura Docker Swarm de apptolast?",
     "CITED", "src/content/docs/introduccion.md#resumen"),
    ("¿Qué resultado tuvo el playbook platform el 28 de julio de 2026?",
     "CITED", "src/content/docs/estado-observado.md#instantanea-vigente-28-de-julio-de-2026"),
    ("¿Cuál es la capital de Australia y cuántos habitantes tiene?",
     "NO_EVIDENCE", None),
    ("¿Qué modelo de coche conduce Pablo y de qué color es?",
     "NO_EVIDENCE", None),  # caso "pablo" — ver ADR, un solo término coincidente
    ("¿Qué hostname usa el servicio kropia y qué estrategia de despliegue tiene?",
     "CITED", "src/content/docs/catalogo-servicios.md#servicios-aprobados"),
    ("¿Cuántas compuertas (STOP gates) hay documentadas y cuál es su estado?",
     "CITED", "src/content/docs/compuertas-abiertas.md#resumen"),
    ("¿Qué receta de cocina recomienda este documento para hacer paella?",
     "NO_EVIDENCE", None),
]

# Limitación conocida y documentada (ver ADR, "Limitaciones conocidas"): una
# pregunta legítima sobre contenido que NO está en este corpus, pero que
# menciona por nombre un sustantivo compuesto que sí aparece como enlace
# incidental, puede devolver CITED con chunks irrelevantes. No se "arregla"
# aquí con un parche ad-hoc — se deja como caso conocido, fuera de las
# aserciones de este test, para no fingir una robustez que el código no
# tiene todavía.
KNOWN_LIMITATION_CASE = (
    "¿Qué framework de frontend usa el proyecto sistema-central-admin-servidor?"
)


def main() -> int:
    docs_path = DEFAULT_DOCS_PATH.resolve()
    if not docs_path.exists():
        print(f"AVISO: no existe {docs_path} (checkout hermano de DockerSwarmDocs) — "
              "test omitido, no se puede verificar sin el corpus real.", file=sys.stderr)
        return 0

    index = build_index(docs_path, "apptolast/DockerSwarmDocs")
    print(f"Índice reconstruido: {index['chunk_count']} chunks, corpus_commit={index['corpus_commit']}")

    failures = []
    for question, expected_status, expected_top_chunk in CASES:
        result = answer(index, question, top_k=5, threshold=6.0, min_matched_terms=2)
        status = result["status"]
        ok = status == expected_status
        top_chunk = None
        if status == "CITED" and result["body"]:
            # citation formato [source: path#section@sha] -> extraemos path#section
            citation = result["body"][0]["citation"]
            top_chunk = citation.split("source: ")[1].rsplit("@", 1)[0]
        if ok and expected_top_chunk is not None:
            ok = top_chunk == expected_top_chunk

        mark = "OK " if ok else "FAIL"
        print(f"[{mark}] {question!r} -> {status} (esperado {expected_status})"
              + (f", top={top_chunk!r} (esperado {expected_top_chunk!r})" if expected_top_chunk else ""))
        if not ok:
            failures.append(question)

    # Caso de limitación conocida: se ejecuta e informa, pero NO participa en
    # el criterio de éxito/fallo del test — ver comentario de
    # KNOWN_LIMITATION_CASE arriba.
    known_result = answer(index, KNOWN_LIMITATION_CASE, top_k=3, threshold=6.0, min_matched_terms=2)
    print(f"[INFO, limitación conocida] {KNOWN_LIMITATION_CASE!r} -> {known_result['status']} "
          f"(ver ADR-0001, 'Limitaciones conocidas' — no cuenta como fallo de este test)")

    if failures:
        print(f"\n{len(failures)} caso(s) de calibración fallaron.", file=sys.stderr)
        return 1

    print(f"\nTodos los {len(CASES)} casos de calibración pasaron.")
    return 0


def test_calibration_regression() -> None:
    """Envoltorio pytest sobre `main()` — sin él, herramientas que solo saben
    ejecutar pytest (p. ej. `mutmut`, ver docs/adrs/0001-rag-pilot-lexical-
    retrieval.md sección 'Prueba de mutación') no podrían usar esta misma
    regresión sin reescribirla. No duplica la lógica: `main()` ya devuelve 0
    tanto si los 7 casos pasan como si se salta por falta del checkout
    hermano de DockerSwarmDocs (ver su docstring) — nunca hace falta
    distinguir aquí los dos casos, solo propagar el código de salida real.
    """
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
