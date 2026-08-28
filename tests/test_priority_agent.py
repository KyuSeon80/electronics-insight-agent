"""priority_agent -- 우선조치 랭킹 에이전트 테스트.

harness(TraceLogger, run_with_retry, guardrails)가 실제로 경유되는지, 그리고
group_by 축마다 올바른 MCP 툴로 라우팅되는지 확인한다.
"""
from pathlib import Path

import pytest

from insight_agent.agents import priority_agent

FIXTURES_DIR = Path(__file__).parent / "fixtures_priority"


@pytest.fixture(autouse=True)
def _use_priority_fixture_dataset(monkeypatch):
    monkeypatch.setenv("DATASET_DIR", str(FIXTURES_DIR))


def test_run_ranks_by_product_and_traces():
    outcome = priority_agent.run(group_by="product_id", top_n=1)
    assert outcome["group_by"] == "product_id"
    assert len(outcome["ranking"]) == 1
    assert outcome["ranking"][0]["product_id"] == "PRD-P001"
    assert outcome["ranking"][0]["impact_score"] == 400_000_000.0


def test_run_ranks_by_equipment():
    outcome = priority_agent.run(group_by="equipment_id")
    equipment_ids = {row["equipment_id"] for row in outcome["ranking"]}
    assert equipment_ids == {"EQ-P01", "EQ-P02", "EQ-P03"}


def test_run_ranks_by_factory():
    outcome = priority_agent.run(group_by="factory_code")
    assert outcome["ranking"][0]["factory_code"] == "FAC-P01"


def test_run_rejects_unknown_group_by():
    with pytest.raises(ValueError):
        priority_agent.run(group_by="region")


def test_run_writes_trace_steps():
    from insight_agent.config import RUNS_DIR
    import json

    from insight_agent.harness.trace import TraceLogger

    trace = TraceLogger()
    priority_agent.run(group_by="product_id", trace=trace)

    path = RUNS_DIR / f"{trace.run_id}.jsonl"
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    steps = [r["step"] for r in records]
    assert "priority_agent.get_market_impact_score_by_product" in steps
    assert "priority_agent.top_n" in steps
