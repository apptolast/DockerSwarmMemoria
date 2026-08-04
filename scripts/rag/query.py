#!/usr/bin/env python3
"""query.py — Consulta el índice BM25 construido por `build_index.py`.

Aplica las mismas 2 reglas anti-alucinación que ya rigen el RAG de
`apptolast/sistema-central-admin-servidor` (ADR-0004, capas 3 y 5 — ver
`docs/adrs/0001-rag-pilot-lexical-retrieval.md` para el mapeo completo):

  1. Toda respuesta cita su origen exacto: `[source: path#section@commitsha]`.
  2. Si el mejor score no supera el umbral calibrado, la respuesta es
     literalmente "No encuentro evidencia documentada sobre eso." — igual
     que el contrato ya documentado de `rag-query` en sistema-central-admin-
     servidor (`docs/services/rag-query.md`) — nunca se sintetiza una
     respuesta con conocimiento general del modelo.

Este script SOLO recupera (retrieval); no invoca ningún LLM para redactar
una respuesta en prosa a partir de los chunks. Ver `docs/adrs/
0001-rag-pilot-lexical-retrieval.md`, sección "Qué no incluye esta primera
vuelta", para el razonamiento de por qué el paso de generación queda
diseñado pero no conectado en este pilot.

Cero dependencias externas: solo la librería estándar de Python 3.

Uso:
    python3 query.py --index ../../rag/index.json --question "¿Qué hostname usa n8n?"
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

# Importa las funciones de tokenizado de build_index.py para garantizar que
# la consulta se tokeniza EXACTAMENTE igual que el índice — cualquier
# divergencia (p. ej. una lista de stopwords distinta) rompería el score de
# forma silenciosa.
sys.path.insert(0, str(Path(__file__).parent))
from build_index import tokenize  # noqa: E402

NO_EVIDENCE_MESSAGE = "No encuentro evidencia documentada sobre eso."

# Ambos umbrales calibrados empíricamente contra el corpus real de
# DockerSwarmDocs (9 páginas, 75 chunks) — ver
# docs/adrs/0001-rag-pilot-lexical-retrieval.md, sección "Calibración del
# umbral", para las preguntas de prueba usadas y los scores observados.
# No son valores de librería ni inventados sin más:
#   DEFAULT_THRESHOLD: por debajo del score más bajo observado entre las
#   preguntas dentro de alcance probadas (10.24) y por encima del score más
#   alto observado en una pregunta fuera de alcance con UN término
#   incidental coincidente (3.47, ver MIN_MATCHED_TERMS abajo).
#   MIN_MATCHED_TERMS: el caso "pablo" (ver bm25_scores) demostró que un
#   único término raro coincidente puede superar un umbral de score
#   razonable. Exigir 2+ términos distintos de la consulta presentes en el
#   chunk reduce ese riesgo sin penalizar preguntas cortas y precisas (las 2
#   preguntas de prueba dentro de alcance coinciden en 4-6 términos).
DEFAULT_THRESHOLD = 6.0
MIN_MATCHED_TERMS = 2


def bm25_scores(query_tokens: list[str], chunks: list[dict], avgdl: float, k1: float, b: float) -> list[tuple[float, int]]:
    """Devuelve, por chunk, (score BM25, nº de términos DISTINTOS de la
    consulta que aparecen en ese chunk).

    El segundo valor existe por un caso real encontrado al calibrar este
    script (ver docs/adrs/0001-rag-pilot-lexical-retrieval.md, "Calibración
    del umbral — el caso 'pablo'"): una consulta totalmente fuera de alcance
    puede coincidir en UN ÚNICO término raro (p. ej. un nombre propio que
    aparece de forma incidental en una URL) y aun así sacar un score BM25
    no trivial, porque el IDF de un término raro es alto. Exigir un mínimo
    de términos distintos coincidentes (ver MIN_MATCHED_TERMS en answer())
    filtra ese falso positivo sin depender solo de ajustar el umbral
    numérico, que por sí solo es frágil.
    """
    n = len(chunks)
    doc_freq: dict[str, int] = {}
    for term in set(query_tokens):
        doc_freq[term] = sum(1 for c in chunks if term in c["term_freq"])

    idf: dict[str, float] = {}
    for term, df in doc_freq.items():
        # BM25 IDF estilo Lucene/Elasticsearch (+1 dentro del log evita valores
        # negativos cuando un término aparece en más de la mitad del corpus).
        idf[term] = math.log(((n - df + 0.5) / (df + 0.5)) + 1)

    results = []
    for chunk in chunks:
        score = 0.0
        matched = 0
        length = chunk["length"] or 1
        for term in set(query_tokens):
            f = chunk["term_freq"].get(term, 0)
            if f == 0:
                continue
            matched += 1
            numerator = f * (k1 + 1)
            denominator = f + k1 * (1 - b + b * (length / avgdl))
            score += idf.get(term, 0.0) * (numerator / denominator)
        results.append((score, matched))
    return results


def format_citation(chunk: dict, corpus_commit: str) -> str:
    return f"[source: {chunk['source_path']}#{chunk['chunk_id'].split('#', 1)[1]}@{corpus_commit}]"


def answer(index: dict, question: str, top_k: int, threshold: float,
           min_matched_terms: int = MIN_MATCHED_TERMS) -> dict:
    query_tokens = tokenize(question)
    distinct_query_terms = len(set(query_tokens))
    if not query_tokens:
        return {
            "status": "NO_EVIDENCE",
            "body": None,
            "warning": NO_EVIDENCE_MESSAGE,
            "citations": [],
            "chunks_considered": 0,
        }

    chunks = index["chunks"]
    scored = bm25_scores(query_tokens, chunks, index["avgdl"], **index["bm25_params"])
    ranked = sorted(zip(scored, chunks), key=lambda pair: pair[0][0], reverse=True)

    (best_score, best_matched) = ranked[0][0] if ranked else (0.0, 0)
    # Umbral doble e independiente (ver DEFAULT_THRESHOLD/MIN_MATCHED_TERMS):
    # el score por sí solo es frágil ante un único término raro coincidente.
    effective_min_matched = min(min_matched_terms, distinct_query_terms)
    if best_score < threshold or best_matched < effective_min_matched:
        return {
            "status": "NO_EVIDENCE",
            "body": None,
            "warning": NO_EVIDENCE_MESSAGE,
            "best_score": round(best_score, 4),
            "best_matched_terms": best_matched,
            "threshold": threshold,
            "min_matched_terms": effective_min_matched,
            "citations": [],
            "chunks_considered": len(chunks),
        }

    top = [(score, matched, chunk) for (score, matched), chunk in ranked[:top_k] if score > 0]
    citations = [format_citation(chunk, index["corpus_commit"]) for _, _, chunk in top]
    return {
        "status": "CITED",
        "body": [
            {"section": chunk["section"], "doc_title": chunk["doc_title"], "text": chunk["text"],
             "score": round(score, 4), "matched_terms": matched,
             "citation": format_citation(chunk, index["corpus_commit"])}
            for score, matched, chunk in top
        ],
        "warning": None,
        "best_score": round(best_score, 4),
        "best_matched_terms": best_matched,
        "threshold": threshold,
        "min_matched_terms": effective_min_matched,
        "citations": citations,
        "chunks_considered": len(chunks),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=Path("../../rag/index.json"))
    parser.add_argument("--question", required=True)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument("--min-matched-terms", type=int, default=MIN_MATCHED_TERMS)
    parser.add_argument("--json", action="store_true", help="Imprime el resultado como JSON crudo")
    args = parser.parse_args()

    if not args.index.exists():
        raise SystemExit(f"No existe el índice {args.index} — ejecuta build_index.py primero.")

    index = json.loads(args.index.read_text(encoding="utf-8"))
    result = answer(index, args.question, args.top_k, args.threshold, args.min_matched_terms)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print(f"Pregunta: {args.question}")
    print(f"Estado: {result['status']}  (best_score={result.get('best_score')}, "
          f"terminos_coincidentes={result.get('best_matched_terms')}, umbral={result.get('threshold')})")
    if result["status"] == "NO_EVIDENCE":
        print(result["warning"])
        return
    for item in result["body"]:
        print(f"\n[{item['score']}] {item['doc_title']} — {item['section']}")
        print(f"  {item['citation']}")
        excerpt = item["text"].replace("\n", " ")
        print(f"  {excerpt[:220]}{'...' if len(excerpt) > 220 else ''}")


if __name__ == "__main__":
    main()
