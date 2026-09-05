from __future__ import annotations

from app.graph import break_cycles, chain_edges, compute_stats
from app.schemas import Edge, SubQuery


def _nodes(n: int) -> list[SubQuery]:
    return [SubQuery(id=f"s{i}", text=f"q{i}") for i in range(1, n + 1)]


def test_flat_graph_is_all_parallel():
    nodes = _nodes(4)
    stats = compute_stats(nodes, [], decomposed=True)
    assert stats.is_dag
    assert stats.depth == 1
    assert stats.max_width == 4
    assert stats.roots == 4 and stats.leaves == 4


def test_linear_chain_depth_and_width():
    nodes = _nodes(4)
    stats = compute_stats(nodes, chain_edges(nodes), decomposed=True)
    assert stats.depth == 4
    assert stats.max_width == 1
    assert stats.roots == 1 and stats.leaves == 1


def test_diamond_dag():
    nodes = _nodes(4)
    edges = [
        Edge(from_="s1", to="s2"),
        Edge(from_="s1", to="s3"),
        Edge(from_="s2", to="s4"),
        Edge(from_="s3", to="s4"),
    ]
    stats = compute_stats(nodes, edges, decomposed=True)
    assert stats.is_dag
    assert stats.depth == 3          # s1 -> s2 -> s4
    assert stats.max_width == 2      # {s2, s3}
    assert stats.roots == 1 and stats.leaves == 1


def test_break_cycles_removes_min_edges():
    nodes = _nodes(3)
    edges = [
        Edge(from_="s1", to="s2"),
        Edge(from_="s2", to="s3"),
        Edge(from_="s3", to="s1"),
    ]
    survivors, removed = break_cycles(nodes, edges)
    assert removed
    stats = compute_stats(nodes, survivors, decomposed=True)
    assert stats.is_dag
    assert len(survivors) == 2
