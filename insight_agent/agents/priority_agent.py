"""우선조치 에이전트 -- docs/prd.md 대시보드용 영향도 점수 랭킹을 만든다.

product_id/equipment_id/factory_code 중 하나의 축으로 "불량이 매출/이익률에
얼마나 영향을 줬는가"(impact_score) 랭킹을 조회해 상위 N개를 돌려준다.
domain.py의 집계 로직에는 직접 접근하지 않고, 다른 에이전트와 동일하게
mymcp.client.McpClient를 거친다.
"""
from __future__ import annotations

from typing import Optional

from insight_agent.harness.guardrails import validate_priority_ranking
from insight_agent.harness.loop import run_with_retry
from insight_agent.harness.trace import TraceLogger
from insight_agent.mymcp.client import McpClient

_TOOL_BY_GROUP = {
    "product_id": "get_market_impact_score_by_product",
    "equipment_id": "get_market_impact_score_by_equipment",
    "factory_code": "get_market_impact_score_by_factory",
}


def run(
    group_by: str = "product_id",
    top_n: int = 10,
    trace: Optional[TraceLogger] = None,
) -> dict:
    trace = trace or TraceLogger()
    if group_by not in _TOOL_BY_GROUP:
        raise ValueError(f"group_by must be one of {sorted(_TOOL_BY_GROUP)}, got {group_by!r}")

    tool_name = _TOOL_BY_GROUP[group_by]

    def _call() -> list[dict]:
        with McpClient() as client:
            return client.call_tool(tool_name, {})

    ranking = run_with_retry(_call)
    trace.log(f"priority_agent.{tool_name}", {"group_by": group_by}, ranking)

    validate_priority_ranking(ranking)

    top = ranking[:top_n]
    trace.log("priority_agent.top_n", {"group_by": group_by, "top_n": top_n}, top)

    return {"group_by": group_by, "top_n": top_n, "ranking": top}
