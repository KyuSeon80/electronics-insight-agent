"""프로젝트 공통 설정 — 데이터 경로, 산출물 경로, HITL/HOTL 임계치."""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATASET_DIR = Path(os.environ.get("DATASET_DIR", str(Path.home() / "Desktop" / "dataset_1")))
XLSX_PATH = DATASET_DIR / "electronics_manufacturing_market_data_3yr.xlsx"

OUTPUTS_DIR = PROJECT_ROOT / "outputs"
RUNS_DIR = PROJECT_ROOT / "runs"
APPROVALS_DIR = PROJECT_ROOT / "approvals"

# HITL: product_id 하나에 Critical 결함이 이 값 이상 누적되면 자동 발행을 멈추고 사람 승인 대기
CRITICAL_DEFECT_HITL_THRESHOLD = 3

# HOTL: 리전×카테고리 시장점유율이 전분기 대비 이 값(퍼센트포인트) 이하로 떨어지면 알림
MARKET_SHARE_DROP_ALERT_PP = -2.0

# 우선조치 대시보드: severity 가중 불량 지수 계산용 가중치 (docs/prd.md 4.1절).
# 2026-08-28 확정값 (progress.md 오픈 이슈 처리 시 결정).
DEFECT_SEVERITY_WEIGHTS = {"Critical": 3.0, "Major": 2.0, "Minor": 1.0}

# 우선조치 대시보드: 월별 불량률-영업이익률 상관계수를 신뢰하려면 최소 몇 개월치
# 매칭 데이터가 필요한지. docs/prd.md 7절 "표본 크기" 캐비어트를 코드로 반영한
# 값이며, 확정 임계치가 아니라 담당자 검증 전 초안이다.
MIN_MONTHS_FOR_CORRELATION = 3
