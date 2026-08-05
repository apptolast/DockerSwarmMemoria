#!/usr/bin/env python3
"""query_graph.py — Consultas de traversal sobre el grafo declarativo
construido por `build_graph.py`.

Vocabulario de consultas adaptado del propio `ah` CLI descrito en el
documento fuente (ver docs/adrs/0002-graph-assembly-declarative-layer.md,
Sección III.C de esa síntesis): `children`, `leaves`, `lineage`, `diff` —
aquí reinterpretados sobre DEPENDS_ON en vez de sobre un DAG de commits, y
`impact` que replica literalmente el ejemplo ya citado en el ADR-0004 de
`sistema-central-admin-servidor` ("si cae timescaledb-0, ¿qué se rompe en
cascada?").

Toda arista devuelta cita su documento de origen real (`source_doc`) —
ninguna consulta aquí "resuelve" una relación que no esté ya en el grafo
(que a su vez viene, sin excepción, de un frontmatter real — ver
build_graph.py). Si no hay camino entre dos entidades, se dice
explícitamente en vez de forzar una respuesta.

Cero dependencias externas salvo `networkx` (igual que build_graph.py).

Uso:
    python3 query_graph.py --graph ../../rag/graph.json impact policy:compuertas-abiertas
    python3 query_graph.py --graph ../../rag/graph.json path architecture:introduccion network:topologia-red
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import networkx as nx


def load_graph(path: Path) -> tuple[nx.MultiDiGraph, dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    graph = nx.node_link_graph(data["graph"], edges="edges", directed=True, multigraph=True)
    return graph, data


def require_node(graph: nx.MultiDiGraph, entity_id: str) -> None:
    if entity_id not in graph:
        raise SystemExit(f"No existe la entidad {entity_id!r} en el grafo. "
                          f"Entidades disponibles: {sorted(n for n in graph.nodes if graph.nodes[n].get('node_kind') == 'Entity')}")


def _real_edges_between(graph: nx.MultiDiGraph, x: str, y: str) -> list[dict]:
    """Todas las aristas REALES entre x e y, en cualquiera de los dos
    sentidos, cada una con su dirección verdadera y su `claim_source` real
    (el documento cuyo frontmatter declaró literalmente esa relación — ver
    `claim_source` en build_graph.py). Nunca se infiere la dirección a partir
    del orden de un recorrido (p. ej. el camino más corto sobre la vista no
    dirigida del grafo, que usa `path()` abajo): ese fue exactamente el bug
    real encontrado y corregido en esta misma sesión — `impact()`/`path()`
    etiquetaban la relación con la dirección del recorrido en vez de con la
    dirección real declarada en el frontmatter (ver
    docs/adrs/0002-graph-assembly-declarative-layer.md). Puede devolver 0, 1
    o varias entradas (p. ej. un DEPENDS_ON y un MENTIONS independientes
    entre el mismo par, o relaciones declaradas en ambos sentidos a la vez).
    """
    out = []
    for u, v in ((x, y), (y, x)):
        for d in graph.get_edge_data(u, v, default={}).values():
            out.append({"from": u, "to": v, "edge_type": d.get("edge_type", "?"),
                        "source": d.get("claim_source")})
    return out


def children(graph: nx.MultiDiGraph, entity_id: str) -> list[dict]:
    """Qué depende DIRECTAMENTE de esta entidad (una arista DEPENDS_ON entrante
    U -> entity_id significa "U depende de entity_id", ver build_graph.py) —
    equivalente a "qué se rompería si esto se rompe", primer salto.
    """
    require_node(graph, entity_id)
    out = []
    for u, _v, d in graph.in_edges(entity_id, data=True):
        if d.get("edge_type") == "DEPENDS_ON":
            out.append({"entity": u, "name": graph.nodes[u].get("name"), "source_doc": graph.nodes[u].get("source_doc")})
    return out


def impact(graph: nx.MultiDiGraph, entity_id: str) -> dict:
    """Cierre transitivo de 'qué se rompe en cascada' si `entity_id` falla —
    DFS sobre DEPENDS_ON inverso, replicando literalmente el ejemplo ya
    descrito en ADR-0004 de sistema-central-admin-servidor ("si cae
    timescaledb-0, ¿qué se rompe en cascada?").

    NOTA (bug real corregido en esta sesión): `depends_reverse` invierte la
    arista para poder recorrer la cascada de impacto (de "quién depende de
    mí" en vez de "de quién dependo"), pero eso NO cambia cuál es la
    relación DEPENDS_ON verdadera. Una versión anterior de esta función
    etiquetaba cada salto con la dirección del RECORRIDO (a -> b) en vez de
    con la dirección real declarada en el frontmatter (que es b depende de
    a) — se corrige aquí propagando `claim_source` desde la arista original
    y construyendo el texto del salto en la dirección real, no en la del
    recorrido. Ver docs/adrs/0002-graph-assembly-declarative-layer.md.
    """
    require_node(graph, entity_id)
    depends_reverse = nx.MultiDiGraph()
    for u, v, d in graph.edges(data=True):
        if d.get("edge_type") == "DEPENDS_ON":
            # invertido: de "depende de" a "afecta a" — pero se conserva el
            # claim_source de la arista ORIGINAL (u -> v), que es quien de
            # verdad declaró esta relación.
            depends_reverse.add_edge(v, u, claim_source=d.get("claim_source"))

    if entity_id not in depends_reverse:
        return {"entity": entity_id, "impacted": [], "note": "Ninguna entidad declara depender de esta (0 aristas DEPENDS_ON entrantes)."}

    reachable = nx.descendants(depends_reverse, entity_id)
    impacted = []
    for n in reachable:
        node_path = nx.shortest_path(depends_reverse, entity_id, n)
        hops = []
        for a, b in zip(node_path, node_path[1:]):
            edge_data = depends_reverse.get_edge_data(a, b, default={})
            claim_source = next((d.get("claim_source") for d in edge_data.values() if d.get("claim_source")), None)
            # La relación REAL va en sentido "b depende de a" (b -DEPENDS_ON-> a
            # en el frontmatter), aunque el recorrido de impacto vaya de a a b.
            hops.append(f"{b} -DEPENDS_ON-> {a} [source: {claim_source}]")
        impacted.append({"entity": n, "name": graph.nodes[n].get("name"), "path": hops})
    return {"entity": entity_id, "impacted": impacted}


def depends_on_closure(graph: nx.MultiDiGraph, entity_id: str) -> dict:
    """Lo contrario de impact(): de qué depende esta entidad, transitivamente
    (cierre hacia adelante sobre DEPENDS_ON)."""
    require_node(graph, entity_id)
    depends_fwd = nx.MultiDiGraph()
    for u, v, d in graph.edges(data=True):
        if d.get("edge_type") == "DEPENDS_ON":
            depends_fwd.add_edge(u, v)

    if entity_id not in depends_fwd:
        return {"entity": entity_id, "depends_on": [], "note": "Esta entidad no declara ningún DEPENDS_ON saliente."}
    reachable = nx.descendants(depends_fwd, entity_id)
    return {"entity": entity_id, "depends_on": sorted(reachable)}


def path(graph: nx.MultiDiGraph, from_id: str, to_id: str) -> dict:
    """Camino más corto (cualquier tipo de arista) entre dos entidades, con
    cita de fuente en cada salto — el equivalente de 'lineage' del CLI
    fuente, adaptado de ancestría de commits a relaciones declarativas.

    NOTA (bug real corregido en esta sesión): el camino más corto se calcula
    sobre una vista NO dirigida (`to_undirected`) porque a la persona que
    consulta le interesa "¿hay conexión entre estas dos entidades?"
    independientemente del sentido — pero el orden (a, b) de ese recorrido
    NO dirigido no dice nada sobre cuál es la dirección real de la relación
    declarada. Una versión anterior asumía que la arista real iba de a hacia
    b (o, como mucho, comprobaba b->a solo para decidir SI había datos, pero
    seguía reportando "from": a, "to": b incluso cuando la única arista real
    iba de b hacia a). Se corrige devolviendo, para cada salto, TODAS las
    relaciones reales entre ese par con su dirección y fuente verdaderas
    (`_real_edges_between`) — nunca una dirección re-inferida del recorrido.
    """
    require_node(graph, from_id)
    require_node(graph, to_id)
    undirected_view = graph.to_undirected(as_view=True)
    if not nx.has_path(undirected_view, from_id, to_id):
        return {"from": from_id, "to": to_id, "found": False,
                "note": "No existe ningún camino declarado entre estas dos entidades en este grafo."}
    node_path = nx.shortest_path(undirected_view, from_id, to_id)
    hops = []
    for a, b in zip(node_path, node_path[1:]):
        hops.append({"between": [a, b], "relations": _real_edges_between(graph, a, b)})
    return {"from": from_id, "to": to_id, "found": True, "path": node_path, "hops": hops}


def leaves(graph: nx.MultiDiGraph) -> list[str]:
    """Entidades de las que nada depende (sin aristas DEPENDS_ON entrantes) —
    hojas del grafo de dependencias, en el mismo sentido que 'ah leaves' del
    CLI fuente."""
    entity_nodes = [n for n, d in graph.nodes(data=True) if d.get("node_kind") == "Entity"]
    result = []
    for n in entity_nodes:
        has_dependent = any(d.get("edge_type") == "DEPENDS_ON" for _, _, d in graph.in_edges(n, data=True))
        if not has_dependent:
            result.append(n)
    return sorted(result)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", type=Path, default=Path("../../rag/graph.json"))
    sub = parser.add_subparsers(dest="command", required=True)

    p_children = sub.add_parser("children", help="Qué depende directamente de esta entidad")
    p_children.add_argument("entity_id")

    p_impact = sub.add_parser("impact", help="Cierre transitivo de qué se rompe en cascada")
    p_impact.add_argument("entity_id")

    p_depends = sub.add_parser("depends-on", help="De qué depende esta entidad, transitivamente")
    p_depends.add_argument("entity_id")

    p_path = sub.add_parser("path", help="Camino más corto entre dos entidades")
    p_path.add_argument("from_id")
    p_path.add_argument("to_id")

    sub.add_parser("leaves", help="Entidades de las que nada depende")

    args = parser.parse_args()
    if not args.graph.exists():
        raise SystemExit(f"No existe el grafo {args.graph} — ejecuta build_graph.py primero.")
    graph, _meta = load_graph(args.graph)

    if args.command == "children":
        print(json.dumps(children(graph, args.entity_id), ensure_ascii=False, indent=2))
    elif args.command == "impact":
        print(json.dumps(impact(graph, args.entity_id), ensure_ascii=False, indent=2))
    elif args.command == "depends-on":
        print(json.dumps(depends_on_closure(graph, args.entity_id), ensure_ascii=False, indent=2))
    elif args.command == "path":
        print(json.dumps(path(graph, args.from_id, args.to_id), ensure_ascii=False, indent=2))
    elif args.command == "leaves":
        print(json.dumps(leaves(graph), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
