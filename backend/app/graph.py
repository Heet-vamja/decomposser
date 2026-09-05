"""Normalisation, validation and structural statistics for decomposition graphs."""
from __future__ import annotations

import networkx as nx

from .schemas import Edge, GraphStats, SubQuery


def chain_edges(subqueries: list[SubQuery]) -> list[Edge]:
    """Linear dependency chain: each subquery depends on the previous one."""
    return [
        Edge(from_=subqueries[i].id, to=subqueries[i + 1].id)
        for i in range(len(subqueries) - 1)
    ]


def dedupe_edges(edges: list[Edge]) -> list[Edge]:
    seen: set[tuple[str, str]] = set()
    out: list[Edge] = []
    for e in edges:
        key = (e.from_, e.to)
        if e.from_ != e.to and key not in seen:
            seen.add(key)
            out.append(e)
    return out


def prune_edges_to_nodes(subqueries: list[SubQuery], edges: list[Edge]) -> list[Edge]:
    ids = {s.id for s in subqueries}
    return [e for e in dedupe_edges(edges) if e.from_ in ids and e.to in ids]


def break_cycles(subqueries: list[SubQuery], edges: list[Edge]) -> tuple[list[Edge], bool]:
    """Drop the minimum-ish set of edges needed to make the graph acyclic.

    Returns the surviving edges and whether anything was removed.
    """
    g = nx.DiGraph()
    g.add_nodes_from(s.id for s in subqueries)
    for e in edges:
        g.add_edge(e.from_, e.to)
    removed = False
    while not nx.is_directed_acyclic_graph(g):
        try:
            cycle = nx.find_cycle(g, orientation="original")
        except nx.NetworkXNoCycle:  # pragma: no cover - loop guard
            break
        u, v = cycle[-1][0], cycle[-1][1]
        g.remove_edge(u, v)
        removed = True
    survivors = [e for e in edges if g.has_edge(e.from_, e.to)]
    return survivors, removed


def compute_stats(subqueries: list[SubQuery], edges: list[Edge], *, decomposed: bool) -> GraphStats:
    g = nx.DiGraph()
    g.add_nodes_from(s.id for s in subqueries)
    for e in edges:
        g.add_edge(e.from_, e.to)

    is_dag = nx.is_directed_acyclic_graph(g)
    if is_dag and g.number_of_nodes():
        # longest path in nodes
        depth = nx.dag_longest_path_length(g) + 1
        # width = largest antichain, via minimum path cover on the transitive closure
        tc = nx.transitive_closure_dag(g) if g.number_of_edges() else g
        max_width = _max_antichain(tc)
    else:
        depth = 1 if g.number_of_nodes() else 0
        max_width = g.number_of_nodes()

    roots = sum(1 for n in g.nodes if g.in_degree(n) == 0)
    leaves = sum(1 for n in g.nodes if g.out_degree(n) == 0)

    return GraphStats(
        node_count=g.number_of_nodes(),
        edge_count=g.number_of_edges(),
        is_dag=is_dag,
        depth=depth,
        max_width=max_width,
        roots=roots,
        leaves=leaves,
        decomposed=decomposed,
    )


def _max_antichain(tc: nx.DiGraph) -> int:
    """Largest set of pairwise-incomparable nodes (Dilworth via bipartite matching)."""
    nodes = list(tc.nodes)
    if not nodes:
        return 0
    b = nx.Graph()
    left = {n: f"L::{n}" for n in nodes}
    right = {n: f"R::{n}" for n in nodes}
    b.add_nodes_from(left.values(), bipartite=0)
    b.add_nodes_from(right.values(), bipartite=1)
    for u, v in tc.edges:
        b.add_edge(left[u], right[v])
    matching = nx.bipartite.maximum_matching(b, top_nodes=set(left.values()))
    left_ids = set(left.values())
    match_size = len([k for k in matching if k in left_ids])
    return len(nodes) - match_size
