#!/usr/bin/env python3
"""build_index.py — Construye un índice de recuperación léxica (BM25) sobre
un corpus Markdown (por defecto, `apptolast/DockerSwarmDocs`).

Ver `docs/adrs/0001-rag-pilot-lexical-retrieval.md` para el razonamiento
completo de por qué recuperación léxica (BM25) y no embeddings neuronales en
esta primera vuelta del pilot, y qué se necesitaría para pasar a embeddings
más adelante.

Cero dependencias externas: solo la librería estándar de Python 3. No hace
falta `pip install` nada, ni red, para construir ni para consultar el índice
(ver `query.py`).

Uso:
    python3 build_index.py --docs-path ../DockerSwarmDocs --output ../../rag/index.json

El índice resultante es texto plano (JSON), pensado para poder revisarse y
diffearse en git como cualquier otro documento del repo — no es un blob de
embeddings opacos.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# Palabras vacías (stopwords) en español + inglés técnico mínimo. Lista corta
# a propósito: en un corpus tan pequeño (ver ADR-0001) una lista de stopwords
# larga o "inteligente" no aporta precisión medible y sí puede filtrar por
# accidente un término que en realidad es relevante (p. ej. nombres propios
# cortos). Se mantiene deliberadamente conservadora.
STOPWORDS = {
    "a", "al", "algo", "algunas", "algunos", "ante", "antes", "como", "con",
    "contra", "cual", "cuando", "de", "del", "desde", "donde", "durante",
    "e", "el", "ella", "ellas", "ellos", "en", "entre", "era", "erais",
    "eran", "eres", "es", "esa", "esas", "ese", "eso", "esos", "esta",
    "estas", "este", "esto", "estos", "fue", "fueron", "ha", "hay", "la",
    "las", "lo", "los", "más", "mas", "mi", "mis", "mucho", "muchos", "muy",
    "ni", "no", "nos", "nosotros", "o", "os", "otra", "otras", "otro",
    "otros", "para", "pero", "poco", "por", "porque", "que", "quien",
    "se", "sea", "sean", "ser", "si", "sido", "sin", "sobre", "su", "sus",
    "también", "tambien", "te", "ti", "tiene", "todo", "todos", "tu", "tus",
    "un", "una", "uno", "unos", "y", "ya", "yo",
    "the", "is", "are", "was", "were", "of", "in", "on", "for", "with",
    "and", "or", "to", "this", "that",
}

TOKEN_RE = re.compile(r"[0-9a-záéíóúñü]+", re.IGNORECASE)


def strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def tokenize(text: str) -> list[str]:
    """Minúsculas, sin acentos, solo alfanumérico, sin stopwords cortas.

    Deliberadamente simple (sin stemming/lematización): para un corpus de
    técnico en español con identificadores exactos (hostnames, nombres de
    servicio, flags de CLI), el stemming agresivo puede fusionar términos
    que en este dominio SÍ conviene distinguir. Ver ADR-0001.
    """
    folded = strip_accents(text.lower())
    tokens = TOKEN_RE.findall(folded)
    return [t for t in tokens if t not in STOPWORDS and len(t) > 1]


def git_short_sha(repo_path: Path) -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except Exception as exc:  # noqa: BLE001 — reportar y seguir, no inventar un sha
        print(f"AVISO: no se pudo determinar el commit de {repo_path}: {exc}", file=sys.stderr)
        return "TODO: verificar"


def slugify(text: str) -> str:
    folded = strip_accents(text.lower())
    slug = re.sub(r"[^a-z0-9]+", "-", folded).strip("-")
    return slug or "seccion"


FRONTMATTER_FIELD_RE = re.compile(r'^(title|type|source-of-truth):\s*"?(.*?)"?\s*$')


def parse_frontmatter(raw: str) -> dict:
    """Extrae solo los 3 campos de frontmatter que necesitamos para citar
    (title, type, source-of-truth) — no un parser YAML completo a propósito:
    build_index.py no necesita el resto de los 13 campos del contrato para
    esta tarea, y un parser YAML completo sería una dependencia (PyYAML) que
    este repo hoy no tiene ni necesita para nada más (ver harness.config.json:
    "sin package.json ni src/ en un lenguaje de propósito general").
    """
    fields = {"title": "", "type": "", "source-of-truth": ""}
    if not raw.startswith("---"):
        return fields
    end = raw.find("\n---", 3)
    if end == -1:
        return fields
    for line in raw[3:end].splitlines():
        m = FRONTMATTER_FIELD_RE.match(line.strip())
        if m:
            fields[m.group(1)] = m.group(2)
    return fields


def split_body(raw: str) -> str:
    if not raw.startswith("---"):
        return raw
    end = raw.find("\n---", 3)
    if end == -1:
        return raw
    return raw[end + 4:]


def chunk_markdown(body: str) -> list[tuple[str, str]]:
    """Divide el cuerpo (ya sin frontmatter) en secciones por encabezado H2
    (`## `), igual que ya hace `rag-ingestor` de sistema-central-admin-servidor
    ("Chunkea cada markdown por sección H2/H3", ver docs/services/rag-ingestor.md).
    Todo lo anterior al primer H2 (normalmente el H1 + una frase de contexto)
    se guarda como sección "preambulo".

    Devuelve una lista de (nombre_seccion, texto_seccion).
    """
    lines = body.splitlines()
    sections: list[tuple[str, list[str]]] = []
    current_name = "preambulo"
    current_lines: list[str] = []
    for line in lines:
        h2 = re.match(r"^##\s+(.*)", line)
        if h2:
            sections.append((current_name, current_lines))
            current_name = h2.group(1).strip()
            current_lines = []
        else:
            current_lines.append(line)
    sections.append((current_name, current_lines))
    return [(name, "\n".join(text_lines).strip()) for name, text_lines in sections if "\n".join(text_lines).strip()]


def git_repo_root(path: Path) -> Path:
    """Resuelve la raíz real del repo git que contiene `path` preguntando a
    git (`rev-parse --show-toplevel`), en vez de calcularlo contando niveles
    de carpetas a mano — eso se rompería en silencio si la estructura interna
    de `DockerSwarmDocs` cambia (p. ej. si algún día deja de vivir bajo
    `src/content/docs/`). Si `path` no está dentro de un repo git (caso de
    prueba con una carpeta suelta), se usa `path` mismo como raíz.
    """
    try:
        out = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        )
        return Path(out.stdout.strip())
    except Exception:  # noqa: BLE001 — no es un repo git; degradar sin fallar
        return path


def build_index(docs_path: Path, corpus_repo: str) -> dict:
    md_files = sorted(docs_path.rglob("*.md"))
    if not md_files:
        raise SystemExit(f"No se encontró ningún .md bajo {docs_path} — ¿ruta correcta?")

    corpus_sha = git_short_sha(docs_path)
    repo_root = git_repo_root(docs_path)
    chunks = []
    for path in md_files:
        raw = path.read_text(encoding="utf-8")
        fm = parse_frontmatter(raw)
        body = split_body(raw)
        rel_path = path.relative_to(repo_root)
        for section_name, section_text in chunk_markdown(body):
            tokens = tokenize(f"{fm.get('title', '')} {section_name} {section_text}")
            if not tokens:
                continue
            chunk_id = f"{path.name}#{slugify(section_name)}"
            chunks.append({
                "chunk_id": chunk_id,
                "source_path": str(rel_path),
                "section": section_name,
                "doc_title": fm.get("title", ""),
                "doc_type": fm.get("type", ""),
                "doc_source_of_truth": fm.get("source-of-truth", ""),
                "text": section_text,
                "term_freq": dict(Counter(tokens)),
                "length": len(tokens),
            })

    if not chunks:
        raise SystemExit("Se leyeron ficheros .md pero no se extrajo ningún chunk con contenido — revisa el chunker.")

    avgdl = sum(c["length"] for c in chunks) / len(chunks)

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "corpus_repo": corpus_repo,
        "corpus_commit": corpus_sha,
        "bm25_params": {"k1": 1.5, "b": 0.75},
        "avgdl": round(avgdl, 2),
        "chunk_count": len(chunks),
        "chunks": chunks,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docs-path", type=Path, default=Path("../DockerSwarmDocs/src/content/docs"),
                         help="Carpeta con los .md a indexar (por defecto, el checkout hermano de DockerSwarmDocs)")
    parser.add_argument("--corpus-repo", default="apptolast/DockerSwarmDocs",
                         help="Nombre del repo fuente, para dejarlo registrado en el índice")
    parser.add_argument("--output", type=Path, default=Path("../../rag/index.json"))
    args = parser.parse_args()

    docs_path = args.docs_path.resolve()
    index = build_index(docs_path, args.corpus_repo)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(index, ensure_ascii=False, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    print(f"Índice escrito en {args.output}")
    print(f"  corpus_commit: {index['corpus_commit']}")
    print(f"  chunks: {index['chunk_count']}")
    print(f"  avgdl: {index['avgdl']} tokens/chunk")


if __name__ == "__main__":
    main()
