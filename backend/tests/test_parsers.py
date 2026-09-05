from __future__ import annotations

from app.decomposers.base import DecomposerContext, parse_numbered_list
from app.decomposers.deterministic import DeterministicDecomposer
from app.decomposers.hybridflow import _parse_plan
from app.decomposers.uno_orchestra import _load_json


def test_parse_numbered_list_with_deps():
    text = """
    1. Find the population of Canada
    2. Find the population of Poland
    3. Compare the two (depends on: 1, 2)
    """
    items = parse_numbered_list(text)
    assert [it.index for it in items] == [1, 2, 3]
    assert items[2].deps == [1, 2]
    assert "depends on" not in items[2].text.lower()


def test_parse_numbered_list_bullets():
    items = parse_numbered_list("- first thing\n- second thing\n")
    assert len(items) == 2
    assert items[0].text == "first thing"


def test_parse_numbered_list_dedupes_indices_and_stays_contiguous():
    # model repeats "1." and skips 3
    items = parse_numbered_list("1. a\n1. b\n4. c (depends on: 1)\n\n  \n5. \n")
    assert [it.index for it in items] == [1, 2, 3]
    assert [it.text for it in items] == ["a", "b", "c"]
    assert items[2].deps == [1]  # "1" remapped to first item


def test_deterministic_splits_on_and_then_and_links_anaphora():
    dec = DeterministicDecomposer()
    ctx = DecomposerContext(pool=None)
    res = dec.run(
        "Find the tallest mountain in Africa and then say how much shorter it is than Everest",
        ctx,
    )
    assert len(res.subqueries) == 2
    assert res.edges and res.edges[0].from_ == "s1" and res.edges[0].to == "s2"


def test_deterministic_atomic_query_single_subquery():
    dec = DeterministicDecomposer()
    res = dec.run("What is the capital of Australia?", DecomposerContext(pool=None))
    assert len(res.subqueries) == 1
    assert res.stats.decomposed is False


def test_hybridflow_parse_plan_roles_and_edges():
    xml = (
        '<plan>'
        '<subtask id="1" role="Explain" parents="">identify entities</subtask>'
        '<subtask id="2" role="Analyze" parents="1">work out the gap</subtask>'
        '<subtask id="3" role="Generate" parents="1,2">compose answer</subtask>'
        '</plan>'
    )
    parsed = _parse_plan("blah blah " + xml + " trailing")
    assert parsed is not None
    subqueries, edges = parsed
    assert [s.id for s in subqueries] == ["s1", "s2", "s3"]
    assert subqueries[0].role == "Explain"
    assert {(e.from_, e.to) for e in edges} == {("s1", "s2"), ("s1", "s3"), ("s2", "s3")}


def test_uno_load_json_tolerates_fences_and_prose():
    raw = 'Sure!\n```json\n{"decompose": false, "subtasks": [{"id":1,"text":"x","deps":[]}]}\n```'
    data = _load_json(raw)
    assert data and data["decompose"] is False
