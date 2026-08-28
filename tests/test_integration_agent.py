"""integration_agent -- force_approval 게이트 테스트.

FE의 "분석 실행"/"원인 리포트 발행 요청" 버튼이 쓰는 force_approval=True
경로가 Critical 결함 수와 무관하게 항상 승인 대기로 보내는지 확인한다.
"""
import json
from pathlib import Path

import pytest

from insight_agent.agents import integration_agent
from insight_agent.config import APPROVALS_DIR

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def _use_fixture_dataset(monkeypatch):
    monkeypatch.setenv("DATASET_DIR", str(FIXTURES_DIR))


def test_default_threshold_still_auto_publishes_low_critical_count():
    # PRD-F001: Critical 결함 1건 -> 기본 임계치(3) 미만 -> 종전과 동일하게 자동 발행
    outcome = integration_agent.run("PRD-F001")
    assert outcome["status"] == "published"


def test_force_approval_overrides_threshold_for_low_critical_count():
    # 동일한 PRD-F001(Critical 1건)이라도 force_approval=True면 승인 대기로 간다
    outcome = integration_agent.run("PRD-F001", force_approval=True)
    assert outcome["status"] == "pending_approval"


def test_force_approval_writes_to_pending_queue():
    outcome = integration_agent.run("PRD-F001", force_approval=True)
    pending_files = list((APPROVALS_DIR / "pending").glob("*.json"))
    matching = [
        p for p in pending_files
        if json.loads(p.read_text(encoding="utf-8"))["report"]["product_id"] == "PRD-F001"
    ]
    assert matching, f"no pending approval file found for outcome={outcome}"
