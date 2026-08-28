"""가드레일 -- (1) 통합 리포트 스키마 검증 (2) CSV/xlsx 소스 정합성 검증.

harness-engineering/harness/guardrails/output_validators.py 개념을 이 프로젝트에
맞게 옮긴 것. 여기서 걸러지지 않으면 HITL 승인 단계로도 나쁜 데이터가 넘어간다.
"""
from __future__ import annotations

from insight_agent import domain
from insight_agent.config import XLSX_PATH

REQUIRED_REPORT_FIELDS = {
    "product_id",
    "critical_defect_count",
    "anomaly_run_count",
    "market_share_trend",
}


def validate_report(report: dict) -> None:
    missing = REQUIRED_REPORT_FIELDS - report.keys()
    if missing:
        raise ValueError(f"report missing required fields: {missing}")
    if report["critical_defect_count"] < 0:
        raise ValueError("critical_defect_count must be >= 0")
    if report["anomaly_run_count"] < 0:
        raise ValueError("anomaly_run_count must be >= 0")


def check_source_consistency(tables: domain.Tables) -> list[dict]:
    return domain.check_source_consistency(tables, XLSX_PATH)


REQUIRED_PRIORITY_ROW_FIELDS = {"impact_score"}


def validate_priority_ranking(ranking: list[dict]) -> None:
    """우선조치 랭킹(domain.get_market_impact_score_by_*) 출력을 검증한다.

    impact_score는 표본 부족 시 None일 수 있으므로(docs/prd.md 7절) None 자체는
    허용하되, 값이 있으면 음수(상관계수 x 매출액이 음수가 될 수 없음)를
    허용하지 않는다. 매출액 필드가 있으면 마찬가지로 음수를 걸러낸다.
    """
    for row in ranking:
        missing = REQUIRED_PRIORITY_ROW_FIELDS - row.keys()
        if missing:
            raise ValueError(f"priority ranking row missing required fields: {missing}")

        score = row["impact_score"]
        if score is not None and score < 0:
            raise ValueError(f"impact_score must be >= 0 or None, got {score}")

        revenue = row.get("cumulative_revenue_krw")
        if revenue is not None and revenue < 0:
            raise ValueError(f"cumulative_revenue_krw must be >= 0, got {revenue}")
