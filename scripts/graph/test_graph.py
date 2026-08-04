#!/usr/bin/env python3
"""test_graph.py — Prueba de regresión para el grafo declarativo (Capa 1).

Mismo criterio que scripts/rag/test_calibration.py (ver ese fichero): no es
una suite unitaria exhaustiva de cada función, es la constancia ejecutable
de los valores ya verificados a mano contra el corpus real de
`DockerSwarmDocs` en docs/adrs/0002-graph-assembly-declarative-layer.md —
para que un cambio futuro a `build_graph.py`/`query_graph.py` no rompa en
silencio lo que ya se comprobó.

Cubre en particular el caso de regresión de un bug real encontrado y
corregido en esta misma sesión: `impact()` y `path()` etiquetaban la
dirección de la relación DEPENDS_ON/MENTIONS con el orden del RECORRIDO en
vez de con la dirección verdadera declarada en el frontmatter (ver
docs/adrs/0002-graph-assembly-declarative-layer.md, "Bug encontrado y
corregido"). Los casos `test_impact_direction_is_the_true_declared_direction`
y `test_path_reports_true_direction_not_traversal_order` existen
específicamente para que ese bug no pueda volver sin que este test falle.

Requiere un checkout de `apptolast/DockerSwarmDocs` como carpeta hermana de
`DockerSwarmMemoria` (`../../../DockerSwarmDocs` desde este fichero) — igual
que espera `build_graph.py` por defecto. Si no existe, el test se salta con
aviso explícito en vez de fallar en rojo por una causa ajena a este código
(mismo criterio que `test_calibration.py` y que `program.md` §6: no simular
un resultado que no se pudo verificar de verdad).

Uso:
    python3 test_graph.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build_graph import build_graph, never_referenced_entities  # noqa: E402
from query_graph import children, depends_on_closure, impact, leaves, path  # noqa: E402

DEFAULT_DOCS_PATH = Path(__file__).parent / "../../../DockerSwarmDocs/src/content/docs"

# Valores esperados, todos verificados a mano contra el corpus real en el
# momento de escribir este test (commit 8eb4497 de DockerSwarmDocs) — ver
# docs/adrs/0002-graph-assembly-declarative-layer.md para el razonamiento
# completo de por qué el grafo tiene esta forma exacta.
EXPECTED_NODE_COUNT = 21
EXPECTED_EDGE_COUNT = 44
EXPECTED_NEVER_REFERENCED = {"architecture:adopcion-templatessd", "runbook:observabilidad-backup"}
EXPECTED_LEAVES = [
    "alert:ApplicationBackupStale", "alert:BackupLastRunFailed", "alert:BackupMetricsMissing",
    "architecture:adopcion-templatessd", "architecture:agentes-operadores", "architecture:introduccion",
    "infrastructure:estado-observado", "network:topologia-red", "runbook:observabilidad-backup",
]
EXPECTED_IMPACT_COMPUERTAS = {
    "runbook:observabilidad-backup", "architecture:agentes-operadores",
    "service:catalogo-servicios", "network:topologia-red",
}
EXPECTED_CHILDREN_COMPUERTAS = {
    "architecture:agentes-operadores", "service:catalogo-servicios", "runbook:observabilidad-backup",
}
EXPECTED_DEPENDS_ON_TOPOLOGIA = {"policy:compuertas-abiertas", "service:catalogo-servicios"}


def main() -> int:
    docs_path = DEFAULT_DOCS_PATH.resolve()
    if not docs_path.exists():
        print(f"AVISO: no existe {docs_path} (checkout hermano de DockerSwarmDocs) — "
              "test omitido, no se puede verificar sin el corpus real.", file=sys.stderr)
        return 0

    graph, dangling = build_graph(docs_path, "apptolast/DockerSwarmDocs")
    print(f"Grafo reconstruido: {graph.number_of_nodes()} nodos, {graph.number_of_edges()} aristas")

    checks: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        checks.append((name, ok, detail))

    check("node_count == 21", graph.number_of_nodes() == EXPECTED_NODE_COUNT,
          f"obtenido {graph.number_of_nodes()}")
    check("edge_count == 44", graph.number_of_edges() == EXPECTED_EDGE_COUNT,
          f"obtenido {graph.number_of_edges()}")
    check("0 referencias colgantes", dangling == [], f"obtenido {dangling}")

    never_ref = set(never_referenced_entities(graph))
    check("entidades nunca referenciadas == {adopcion-templatessd, observabilidad-backup}",
          never_ref == EXPECTED_NEVER_REFERENCED, f"obtenido {sorted(never_ref)}")

    check("leaves() == 9 entidades esperadas",
          leaves(graph) == EXPECTED_LEAVES, f"obtenido {leaves(graph)}")

    check("children(policy:compuertas-abiertas) == 3 esperadas",
          {c["entity"] for c in children(graph, "policy:compuertas-abiertas")} == EXPECTED_CHILDREN_COMPUERTAS,
          f"obtenido {[c['entity'] for c in children(graph, 'policy:compuertas-abiertas')]}")

    check("depends-on(network:topologia-red) == 2 esperadas",
          set(depends_on_closure(graph, "network:topologia-red")["depends_on"]) == EXPECTED_DEPENDS_ON_TOPOLOGIA,
          f"obtenido {depends_on_closure(graph, 'network:topologia-red')['depends_on']}")

    # --- Regresión del bug real: dirección de la relación en impact() ---
    impact_result = impact(graph, "policy:compuertas-abiertas")
    impacted_ids = {e["entity"] for e in impact_result["impacted"]}
    check("impact(policy:compuertas-abiertas) == 4 entidades esperadas (cascada completa)",
          impacted_ids == EXPECTED_IMPACT_COMPUERTAS, f"obtenido {sorted(impacted_ids)}")

    obs_entry = next((e for e in impact_result["impacted"] if e["entity"] == "runbook:observabilidad-backup"), None)
    obs_hop_ok = bool(obs_entry) and obs_entry["path"][0].startswith("runbook:observabilidad-backup -DEPENDS_ON-> policy:compuertas-abiertas")
    check("impact(): el salto de observabilidad-backup dice 'observabilidad-backup DEPENDS_ON compuertas-abiertas' "
          "(dirección REAL declarada en su frontmatter, no la del recorrido)",
          obs_hop_ok, f"obtenido {obs_entry['path'] if obs_entry else None}")

    # --- Regresión del bug real: dirección de la relación en path() ---
    # Este par se eligió a propósito porque SOLO existe la arista real en un
    # sentido (runbook:observabilidad-backup -> policy:compuertas-abiertas,
    # nunca al revés) — es el caso que de verdad exponía el bug antiguo
    # (que reportaba "from": policy:compuertas-abiertas, "to":
    # runbook:observabilidad-backup, exactamente al revés de lo declarado).
    path_result = path(graph, "policy:compuertas-abiertas", "runbook:observabilidad-backup")
    relations = path_result["hops"][0]["relations"] if path_result.get("hops") else []
    path_direction_ok = bool(relations) and all(
        r["from"] == "runbook:observabilidad-backup" and r["to"] == "policy:compuertas-abiertas"
        for r in relations
    )
    check("path(compuertas-abiertas, observabilidad-backup): toda relación real va "
          "observabilidad-backup -> compuertas-abiertas (nunca al revés)",
          path_direction_ok, f"obtenido {relations}")

    # --- Regresión del bug real: claim_source correcto para aristas derivadas de used-by ---
    # diagnosticos-conocidos.md declara `used-by: [architecture:agentes-operadores]` —
    # la arista resultante va agentes-operadores -> diagnosticos-conocidos, pero
    # quien DECLARA la relación es diagnosticos-conocidos (no agentes-operadores).
    # Un citado ingenuo por posición del nodo habría citado el fichero equivocado.
    diag_impact = impact(graph, "runbook:diagnosticos-conocidos")
    diag_entry = next((e for e in diag_impact["impacted"] if e["entity"] == "architecture:agentes-operadores"), None)
    diag_citation_ok = bool(diag_entry) and "diagnosticos-conocidos.md" in diag_entry["path"][0]
    check("impact(diagnosticos-conocidos): la cita del salto used-by apunta a "
          "diagnosticos-conocidos.md (quien declara), no a agentes-operadores.md",
          diag_citation_ok, f"obtenido {diag_entry['path'] if diag_entry else None}")

    # --- Caso de error: entidad inexistente ---
    try:
        children(graph, "entity:no-existe-nunca")
        error_case_ok = False
        error_detail = "no lanzó SystemExit"
    except SystemExit as exc:
        error_case_ok = "no-existe-nunca" in str(exc) or "No existe la entidad" in str(exc)
        error_detail = str(exc)[:80]
    check("consultar una entidad inexistente termina con SystemExit y mensaje claro",
          error_case_ok, error_detail)

    failures = [name for name, ok, _ in checks if not ok]
    for name, ok, detail in checks:
        mark = "OK " if ok else "FAIL"
        print(f"[{mark}] {name}" + (f" — {detail}" if detail and not ok else ""))

    if failures:
        print(f"\n{len(failures)} de {len(checks)} comprobaciones fallaron.", file=sys.stderr)
        return 1

    print(f"\nTodas las {len(checks)} comprobaciones del grafo pasaron.")
    return 0


def test_graph_regression() -> None:
    """Envoltorio pytest sobre `main()` — mismo motivo que
    `test_calibration_regression` en scripts/rag/test_calibration.py: permite
    que herramientas basadas en pytest (`mutmut`) ejecuten esta regresión sin
    reescribirla. `main()` ya devuelve 0 tanto si las 12 comprobaciones pasan
    como si se salta por falta del checkout hermano de DockerSwarmDocs."""
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
