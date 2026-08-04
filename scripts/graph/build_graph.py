#!/usr/bin/env python3
"""build_graph.py — Construye el grafo de conocimiento DECLARATIVO (Capa 1)
de `apptolast/DockerSwarmDocs`, materializando en un grafo real (NetworkX
MultiDiGraph, ver docs/adrs/0002-graph-assembly-declarative-layer.md) las
relaciones que YA existen hoy, a mano, en el frontmatter YAML de cada
página — sin ninguna llamada a modelo, 100% determinista.

Vocabulario de nodos/aristas: `schema/graph-vocabulary.md` (ya existente en
este repo). Invariantes aplicados aquí (ver ADR-0002 para el mapeo completo
a los 4 invariantes del documento fuente):
  1. Toda Claim (aquí: cada relación declarada) cita su Source (el propio
     frontmatter del documento que la declara) — nunca se infiere una
     relación que no esté escrita.
  2. Todo Artifact (cada Entity de este grafo) tiene su fichero de origen
     (source_doc) y su `last-verified` como versión.
  3. No aplica en esta capa (no hay Evaluation todavía — ver "Qué NO
     construye esta primera vuelta" en el ADR).
  4. `superseded-by` se traduce en una arista SUPERSEDES explícita — ningún
     nodo reemplazado se elimina del grafo.

Esta es la Capa 1 ("declarativa, 100% determinista, cero LLM") que ya
describe `sistema-central-admin-servidor` en su ADR-0004. Las Capas 2
(extraída vía LLM) y 3 (inferida multi-hop) NO se implementan aquí — ver
docs/adrs/0002-graph-assembly-declarative-layer.md, "Qué NO construye esta
primera vuelta", para el razonamiento de por qué no se simulan con un
sustituto improvisado.

Cero dependencias externas salvo `networkx` (PyPI, licencia BSD-3-Clause) — la misma
librería que usa el "Anthropic Knowledge Graph Construction Cookbook" para
el paso de ensamblado, según la síntesis independiente que motivó esta
implementación (ver ADR-0002, referencias).

Uso:
    python3 build_graph.py --docs-path ../DockerSwarmDocs/src/content/docs --output ../../rag/graph.json
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import networkx as nx

FRONTMATTER_LIST_FIELDS = [
    "depends-on", "used-by", "related-runbooks", "related-dashboards",
    "related-alerts", "see-also",
]
FRONTMATTER_SCALAR_FIELDS = [
    "title", "type", "owner", "source-of-truth", "last-verified", "status",
    "superseded-by",
]


def git_repo_root(path: Path) -> Path:
    try:
        out = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        )
        return Path(out.stdout.strip())
    except Exception:  # noqa: BLE001
        return path


def git_short_sha(repo_path: Path) -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip()
    except Exception as exc:  # noqa: BLE001
        print(f"AVISO: no se pudo determinar el commit de {repo_path}: {exc}", file=sys.stderr)
        return "TODO: verificar"


def parse_frontmatter_yaml_lite(raw: str) -> dict | None:
    """Parser de frontmatter deliberadamente mínimo (no PyYAML): este repo no
    tiene esa dependencia hoy y el frontmatter real de DockerSwarmDocs usa un
    subconjunto simple y consistente de YAML (escalares con comillas
    opcionales + listas `- "tipo:slug"` o `- CADENA`). Un documento tipo
    "splash" (la portada, `index.md`) no lleva el contrato de 13 campos por
    diseño (ver CHECKPOINTS.md de DockerSwarmDocs, C2) — se detecta por la
    ausencia del campo `type` y se devuelve None para excluirlo del grafo,
    no para tratarlo como un error.
    """
    if not raw.startswith("---"):
        return None
    end = raw.find("\n---", 3)
    if end == -1:
        return None
    fm_text = raw[3:end]

    result: dict = {"tags": []}
    for field in FRONTMATTER_LIST_FIELDS:
        result[field] = []

    lines = fm_text.splitlines()
    current_list_field = None
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        list_item = re.match(r"^-\s+(.*)$", stripped)
        if list_item and current_list_field:
            value = list_item.group(1).strip().strip('"')
            result[current_list_field].append(value)
            continue
        current_list_field = None

        m = re.match(r"^([a-zA-Z-]+):\s*(.*)$", stripped)
        if not m:
            continue
        key, value = m.group(1), m.group(2).strip()
        if key in FRONTMATTER_LIST_FIELDS:
            if value in ("", "[]"):
                current_list_field = key if value == "" else None
                if value == "[]":
                    result[key] = []
            continue
        if key in FRONTMATTER_SCALAR_FIELDS:
            value = value.strip('"')
            result[key] = None if value in ("null", "~", "") else value

    if not result.get("type"):
        return None  # página no factual (splash) — excluida del grafo por diseño
    return result


def build_graph(docs_path: Path, corpus_repo: str) -> tuple[nx.MultiDiGraph, list[str]]:
    md_files = sorted(docs_path.glob("*.md"))
    if not md_files:
        raise SystemExit(f"No se encontró ningún .md bajo {docs_path} — ¿ruta correcta?")

    repo_root = git_repo_root(docs_path)
    corpus_sha = git_short_sha(docs_path)

    docs_by_id: dict[str, dict] = {}
    for path in md_files:
        raw = path.read_text(encoding="utf-8")
        fm = parse_frontmatter_yaml_lite(raw)
        if fm is None:
            continue
        slug = path.stem
        entity_id = f"{fm['type']}:{slug}"
        fm["_entity_id"] = entity_id
        fm["_source_path"] = str(path.relative_to(repo_root))
        docs_by_id[entity_id] = fm

    graph = nx.MultiDiGraph()
    dangling: list[str] = []

    for entity_id, fm in docs_by_id.items():
        graph.add_node(
            entity_id,
            node_kind="Entity",
            entity_type=fm["type"],
            name=fm.get("title", entity_id),
            owner=fm.get("owner", "TODO: verificar"),
            status=fm.get("status", "TODO: verificar"),
            last_verified=fm.get("last-verified", "TODO: verificar"),
            source_doc=fm["_source_path"],
        )
        # Un nodo Source por documento, con el texto completo (a menudo
        # libre: rutas, comandos, commits) de su source-of-truth. No se
        # intenta trocear ese texto en múltiples fuentes estructuradas —
        # sería inventar una estructura que el frontmatter real no tiene.
        source_id = f"source:{entity_id}"
        graph.add_node(
            source_id,
            node_kind="Source",
            source_of_truth=fm.get("source-of-truth", "TODO: verificar"),
        )
        graph.add_edge(source_id, entity_id, edge_type="SUPPORTS",
                        last_verified=fm.get("last-verified", "TODO: verificar"),
                        claim_source=fm["_source_path"])

    def resolve_or_flag(ref: str, referring_from: str, field: str) -> str | None:
        if ref in docs_by_id:
            return ref
        dangling.append(f"{referring_from} declara {field}={ref!r}, pero no existe ninguna "
                         f"página con ese id en este corpus (commit {corpus_sha}).")
        return None

    # `claim_source` en cada arista: el `_source_path` del documento cuyo
    # FRONTMATTER declara literalmente esa relación — no necesariamente el
    # nodo origen de la arista (ver caso `used-by` abajo). Se fija aquí, en
    # el único punto donde de verdad se sabe qué documento hizo la
    # declaración, en vez de re-inferirlo más tarde por la posición de los
    # nodos en un recorrido (eso fue exactamente el bug real que corrigió
    # esta misma sesión en query_graph.py — ver docs/adrs/
    # 0002-graph-assembly-declarative-layer.md, "Bug encontrado y corregido:
    # dirección de la relación en impact()/path()").
    for entity_id, fm in docs_by_id.items():
        for ref in fm.get("depends-on", []):
            target = resolve_or_flag(ref, entity_id, "depends-on")
            if target:
                graph.add_edge(entity_id, target, edge_type="DEPENDS_ON",
                                claim_source=fm["_source_path"])

        # graph-vocabulary.md: "used-by -> Aristas DEPENDS_ON inversas, o
        # PARENT_OF según el caso". Se materializa como DEPENDS_ON invertida
        # (X en used-by de P => X depende de P), igual que ya declara ese
        # documento — no se inventa un edge_type nuevo. IMPORTANTE: quien
        # declara esta relación es P (=entity_id, el documento que tiene el
        # campo `used-by`), aunque en la arista resultante P sea el destino
        # (target -> entity_id) y no el origen — por eso claim_source es
        # fm["_source_path"] (el de entity_id/P) y NO el de target, aunque
        # target sea el nodo origen de esta arista concreta.
        for ref in fm.get("used-by", []):
            target = resolve_or_flag(ref, entity_id, "used-by")
            if target:
                graph.add_edge(target, entity_id, edge_type="DEPENDS_ON",
                                claim_source=fm["_source_path"])

        for ref in fm.get("related-runbooks", []) + fm.get("related-dashboards", []) + fm.get("see-also", []):
            target = resolve_or_flag(ref, entity_id, "related-runbooks/related-dashboards/see-also")
            if target:
                graph.add_edge(entity_id, target, edge_type="MENTIONS",
                                claim_source=fm["_source_path"])

        # related-alerts NO son referencias a otras páginas de este corpus
        # (son nombres de alertas Prometheus, cadena libre) — se modelan como
        # Entity de tipo "alert" propio, nunca resueltas contra docs_by_id.
        for alert_name in fm.get("related-alerts", []):
            alert_id = f"alert:{alert_name}"
            if alert_id not in graph:
                graph.add_node(alert_id, node_kind="Entity", entity_type="alert", name=alert_name)
            graph.add_edge(entity_id, alert_id, edge_type="MENTIONS",
                            claim_source=fm["_source_path"])

        # superseded-by: quien declara la relación es entity_id ("yo quedé
        # obsoleto, ver target"), aunque la arista vaya target -> entity_id
        # (SUPERSEDES: target reemplaza a entity_id) — mismo caso que
        # used-by: claim_source es el de quien declara el campo, no el
        # origen geométrico de la arista.
        superseded_by = fm.get("superseded-by")
        if superseded_by:
            target = resolve_or_flag(superseded_by, entity_id, "superseded-by")
            if target:
                graph.add_edge(target, entity_id, edge_type="SUPERSEDES",
                                claim_source=fm["_source_path"])

    return graph, dangling


def graph_to_jsonable(graph: nx.MultiDiGraph, corpus_repo: str, corpus_commit: str) -> dict:
    data = nx.node_link_data(graph, edges="edges")
    return {
        "corpus_repo": corpus_repo,
        "corpus_commit": corpus_commit,
        "node_count": graph.number_of_nodes(),
        "edge_count": graph.number_of_edges(),
        "graph": data,
    }


def never_referenced_entities(graph: nx.MultiDiGraph) -> list[str]:
    """Entidades "aisladas" en un sentido más preciso que degree<=1: una
    entidad sin NINGUNA arista entrante desde OTRA página de este corpus
    (DEPENDS_ON o MENTIONS) — sí puede tener su propia arista SUPPORTS de
    Source y aristas salientes propias. Es la métrica que el propio
    documento fuente (ver ADR-0002) señala como señal real de salud del
    grafo ("a sudden increase in isolated nodes may signal resolution
    regression"). Factorizada como función propia (no solo inline en
    `main()`) para que `test_graph.py` pueda comprobar la función real en
    vez de una copia suya que podría divergir en silencio.
    """
    entity_nodes = [n for n, d in graph.nodes(data=True) if d.get("node_kind") == "Entity" and d.get("entity_type") != "alert"]
    never_referenced = []
    for n in entity_nodes:
        incoming_from_other_entities = [
            u for u, _, d in graph.in_edges(n, data=True)
            if d.get("edge_type") in ("DEPENDS_ON", "MENTIONS") and graph.nodes[u].get("node_kind") == "Entity"
        ]
        if not incoming_from_other_entities:
            never_referenced.append(n)
    return never_referenced


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docs-path", type=Path, default=Path("../DockerSwarmDocs/src/content/docs"))
    parser.add_argument("--corpus-repo", default="apptolast/DockerSwarmDocs")
    parser.add_argument("--output", type=Path, default=Path("../../rag/graph.json"))
    parser.add_argument("--fail-on-dangling", action="store_true",
                         help="Termina con código de salida 1 si hay referencias colgantes")
    args = parser.parse_args()

    docs_path = args.docs_path.resolve()
    graph, dangling = build_graph(docs_path, args.corpus_repo)
    corpus_sha = git_short_sha(docs_path)

    output_data = graph_to_jsonable(graph, args.corpus_repo, corpus_sha)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Grafo escrito en {args.output}")
    print(f"  corpus_commit: {corpus_sha}")
    print(f"  nodos: {graph.number_of_nodes()}  aristas: {graph.number_of_edges()}")

    never_referenced = never_referenced_entities(graph)
    if never_referenced:
        print(f"  AVISO (no es un error, es un hallazgo real): {len(never_referenced)} entidad(es) que "
              f"ninguna otra página de este corpus referencia todavía (depends-on/see-also/related-*): "
              f"{never_referenced}")

    if dangling:
        print(f"\n{len(dangling)} referencia(s) colgante(s) encontradas:", file=sys.stderr)
        for d in dangling:
            print(f"  - {d}", file=sys.stderr)
        if args.fail_on_dangling:
            sys.exit(1)
    else:
        print("  0 referencias colgantes (toda referencia depends-on/used-by/see-also/superseded-by resuelve a una entidad real).")


if __name__ == "__main__":
    main()
