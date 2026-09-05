from __future__ import annotations

from app.decomposers.base import NO_INVENTION, DecomposerContext
from app.decomposers.hybridflow import HybridFlowDecomposer
from app.decomposers.naive import NaiveLargeDecomposer
from app.decomposers.r2_reasoner import R2ReasonerDecomposer
from app.decomposers.uno_orchestra import UnoOrchestraDecomposer

VALID_PLAN = (
    '<plan>'
    '<subtask id="1" role="Explain" parents="">find A</subtask>'
    '<subtask id="2" role="Analyze" parents="1">find B</subtask>'
    '<subtask id="3" role="Generate" parents="1,2">answer</subtask>'
    '</plan>'
)
CYCLIC_PLAN = (
    '<plan>'
    '<subtask id="1" role="Explain" parents="2">a</subtask>'
    '<subtask id="2" role="Analyze" parents="1">b</subtask>'
    '</plan>'
)


def test_naive_large_parses_list_and_deps(fake_pool):
    pool = fake_pool(["1. pop of Canada\n2. pop of Poland\n3. compare (depends on: 1,2)"])
    res = NaiveLargeDecomposer().run("compare Canada and Poland", DecomposerContext(pool=pool))
    assert res.error is None
    assert [s.id for s in res.subqueries] == ["s1", "s2", "s3"]
    assert ("s1", "s3") in {(e.from_, e.to) for e in res.edges}
    assert res.stats.is_dag


def test_no_invention_rule_is_in_every_llm_system_prompt(fake_pool):
    pool = fake_pool(["1. a\n2. b"])
    NaiveLargeDecomposer().run("q", DecomposerContext(pool=pool))
    system_msg = pool.calls[0]["messages"][0]
    assert system_msg["role"] == "system"
    assert NO_INVENTION in system_msg["content"]


def test_cyclic_deps_are_forced_acyclic_and_noted(fake_pool):
    # model claims 2 depends on 3 and 3 depends on 2 -> a cycle
    pool = fake_pool(["1. base\n2. step two (depends on: 3)\n3. step three (depends on: 2)"])
    res = NaiveLargeDecomposer().run("q", DecomposerContext(pool=pool))
    assert res.stats.is_dag is True
    assert any("acyclic" in n for n in res.notes)


def test_hybridflow_valid_plan_first_try(fake_pool):
    pool = fake_pool([VALID_PLAN])
    res = HybridFlowDecomposer().run("q", DecomposerContext(pool=pool))
    assert res.error is None
    assert len(res.subqueries) == 3
    assert res.stats.is_dag and res.stats.depth == 3
    assert res.subqueries[2].model_tier == "large"  # Generate -> large
    assert len(pool.calls) == 1


def test_hybridflow_ignores_hallucinated_parent_id(fake_pool):
    plan = (
        '<plan>'
        '<subtask id="1" role="Explain" parents="">a</subtask>'
        '<subtask id="2" role="Generate" parents="1,9">b</subtask>'  # 9 does not exist
        '</plan>'
    )
    pool = fake_pool([plan])
    res = HybridFlowDecomposer().run("q", DecomposerContext(pool=pool))
    assert res.error is None
    assert res.stats.is_dag
    assert {(e.from_, e.to) for e in res.edges} == {("s1", "s2")}
    assert len(pool.calls) == 1  # accepted on first try, no repair needed


def test_hybridflow_repairs_then_falls_back_to_chain(fake_pool):
    # every attempt returns a cyclic plan -> 3 calls, then chain fallback
    pool = fake_pool([CYCLIC_PLAN, CYCLIC_PLAN, CYCLIC_PLAN])
    res = HybridFlowDecomposer().run("q", DecomposerContext(pool=pool))
    assert len(pool.calls) == 3
    assert res.stats.is_dag
    assert any("fallback" in n for n in res.notes)


def test_r2_reasoner_parses_markdown_colon_steps(fake_pool):
    pool = fake_pool(
        [
            "1: **Identify the company that makes the iPhone**\n"
            "2: **Determine its founding date**\n"
            "3: **Find and compare the US president at that date**"
        ]
    )
    res = R2ReasonerDecomposer().run("q", DecomposerContext(pool=pool))
    assert res.error is None
    assert [s.text for s in res.subqueries] == [
        "Identify the company that makes the iPhone",
        "Determine its founding date",
        "Find and compare the US president at that date",
    ]
    assert res.stats.depth == 3  # linear chain
    assert res.subqueries[2].model_tier == "large"  # "compare" cue


def test_uno_orchestra_respects_no_decompose(fake_pool):
    pool = fake_pool(['{"decompose": false, "subtasks": [{"id": 1, "text": "q", "deps": []}]}'])
    res = UnoOrchestraDecomposer().run("what is 2+2", DecomposerContext(pool=pool))
    assert res.stats.decomposed is False
    assert len(res.subqueries) == 1
    assert any("NOT to decompose" in n for n in res.notes)


def test_uno_orchestra_builds_dag_when_decomposing(fake_pool):
    pool = fake_pool(
        [
            '{"decompose": true, "subtasks": ['
            '{"id": 1, "text": "a", "deps": [], "model": "small"},'
            '{"id": 2, "text": "b", "deps": [], "model": "small"},'
            '{"id": 3, "text": "c", "deps": [1, 2], "model": "large"}]}'
        ]
    )
    res = UnoOrchestraDecomposer().run("compositional", DecomposerContext(pool=pool))
    assert res.stats.decomposed is True
    assert {(e.from_, e.to) for e in res.edges} == {("s1", "s3"), ("s2", "s3")}
    assert res.stats.max_width == 2
