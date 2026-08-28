"""통합(인과) 에이전트 -- 생산/품질/시장을 product_id로 엮고 HITL 게이트를 적용한다.

이 프로젝트의 핵심 시나리오: "이 제품의 설비/품질 이상이 시장 성과에
영향을 줬는가"를 하나의 리포트로 만들고, Critical 결함이 임계치 이상
누적된 경우에만 사람 승인을 기다린다.
"""
from __future__ import annotations

from typing import Optional

from insight_agent.config import CRITICAL_DEFECT_HITL_THRESHOLD
from insight_agent.harness.guardrails import validate_report
from insight_agent.harness.loop import run_with_retry
from insight_agent.harness.trace import TraceLogger
from insight_agent.hitl import approvals
from insight_agent.mymcp.client import McpClient
from insight_agent.agents import narrative


def run(
    product_id: str,
    trace: Optional[TraceLogger] = None,
    force_approval: bool = False,
) -> dict:
    """product_id 인과 리포트를 만들고 HITL 게이트를 적용한다.

    기본값(force_approval=False)은 Critical 결함이 CRITICAL_DEFECT_HITL_THRESHOLD
    이상일 때만 승인 대기로 보내고, 그 미만이면 auto_publish로 바로 발행한다.
    force_approval=True를 넘기면 Critical 결함 수와 무관하게 항상 승인 대기열로
    보낸다 -- FE의 "분석 실행"/"원인 리포트 발행 요청" 버튼이 이 경로를 쓴다
    (사람이 대시보드에서 직접 요청한 건은 전부 사람 검토를 거치게 하기 위해).
    CLI(`scripts/run_pipeline.py`)와 골든셋 이밸류에이션은 기존 임계치 기반
    분기를 그대로 쓴다.
    """
    trace = trace or TraceLogger()

    def _call() -> dict:
        with McpClient() as client:
            return client.call_tool("build_causal_report", {"product_id": product_id})

    report = run_with_retry(_call)
    trace.log("integration_agent.build_causal_report", {"product_id": product_id}, report)

    validate_report(report)

    report["narrative_summary"] = narrative.summarize(report)
    trace.log("integration_agent.narrative", {"product_id": product_id}, report["narrative_summary"])

    if force_approval or report["critical_defect_count"] >= CRITICAL_DEFECT_HITL_THRESHOLD:
        status = approvals.submit_for_approval(report)
        trace.log(
            "hitl.submit_for_approval",
            {"product_id": product_id, "force_approval": force_approval},
            {"status": status},
        )
    else:
        status = approvals.auto_publish(report)
        trace.log("hitl.auto_publish", {"product_id": product_id}, {"status": status})

    return {"report": report, "status": status}
