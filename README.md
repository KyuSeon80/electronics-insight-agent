<p align="center">
  <img src="./assets/readme/hero.svg" width="100%" alt="electronics-insight-agent — product_id 하나로 설비·품질 이상이 시장 성과에 영향을 줬는지 추적하고, Critical 결함이 임계치를 넘으면 사람 승인을 거쳐 리포트를 발행하는 멀티에이전트 실습 키트">
</p>

`dataset_1`(생산·설비·품질·시장 통합 3개년 스타 스키마 데이터)을 기반으로 만든
멀티에이전트 + 커스텀 MCP + 하네스 엔지니어링 + HITL/HOTL 실습 패키지입니다.
MVP(제품 1개 인과 리포트) 위에, 어떤 제품/설비/공장의 불량을 먼저 조치해야
매출 손실을 줄일 수 있는지 자동으로 랭킹하는 **우선조치 대시보드**를 얹었습니다.

## 핵심 시나리오

1. **인과 리포트** — "이 제품의 설비/품질 이상이 시장 성과에 영향을 줬는가?"를
   `product_id` 하나로 추적해, Critical 등급 결함이 임계치 이상 누적된 경우에만
   사람 승인을 거쳐 리포트를 발행합니다.
2. **우선조치 대시보드** — 100개 제품·54개 설비·3개 공장 전체를 대상으로
   "불량률-시장점유율 상관관계 × 누적매출"로 영향도 점수를 매겨 Top N 랭킹을
   보여주고, 특정 제품/설비를 골라 "불량률을 목표치까지 낮추면 매출이 얼마나
   바뀌는지"를 회귀분석으로 추정합니다. 자세한 배경은 `docs/prd.md`(이 repo에는
   포함되지 않음, 아래 "참고 문서" 절 참고)와 [progress.md](progress.md)에 있습니다.

## 빠른 시작

```bash
cd /path/to/electronics-insight-agent
pip install -r requirements.txt

# 자동 발행 경로 (Critical 결함 2건 -> 임계치 미만)
python -m insight_agent.scripts.run_pipeline --product-id PRD-1076

# HITL 승인 대기 경로 (Critical 결함 4건 -> 임계치 이상, 승인 큐로 이동)
python -m insight_agent.scripts.run_pipeline --product-id PRD-1013
```

내부적으로 (1) CSV/xlsx 소스 정합성 검사 -> (2) 통합 에이전트가 MCP 서버에
`build_causal_report` 호출 -> (3) 가드레일 검증 -> (4) HITL 게이트 판단
(Critical 결함 3건 이상이면 승인 대기, 아니면 자동 발행) -> (5) HOTL 스냅샷 생성
순서로 동작하며, `runs/<run_id>.jsonl`에 전체 트레이스가 남습니다. 두 product_id로
자동 발행/승인 대기 두 경로를 각각 실습할 수 있습니다.

## HITL vs HOTL

<p align="center">
  <img src="./assets/readme/hitl-hotl.svg" width="100%" alt="HITL은 Critical 결함이 임계치를 넘으면 발행을 멈추고 사람 승인을 기다리고, HOTL은 항상 시장점유율을 계산하며 급락 구간만 표시합니다">
</p>

- **HITL** (`insight_agent/hitl/`): 통합 에이전트가 만든 리포트에서 Critical 결함이
  `CRITICAL_DEFECT_HITL_THRESHOLD`(기본 3건) 이상이면 자동 발행을 멈추고
  `approvals/pending/`에 대기시킵니다. 사람이 승인해야 `outputs/`에 최종 리포트가
  생성됩니다.
- **HOTL** (`insight_agent/hotl/`): 승인 대기 없이 항상 계산·노출되는 시장점유율
  스냅샷입니다. 전분기 대비 `MARKET_SHARE_DROP_ALERT_PP`(기본 -2.0%p) 이하로
  하락한 리전x카테고리만 `alerts`에 표시되고, 사람은 필요할 때만 개입합니다.

## 우선조치 대시보드

"어떤 product_id/equipment_id/factory_code의 불량을 먼저 고쳐야 매출 손실을
줄일 수 있는가"를 자동으로 답하는 대시보드입니다. 인과 리포트(위 시나리오 1)가
제품 1개를 사람이 직접 골라 조사하는 방식이라면, 이건 100개 제품 전체를 스캔해
"어디부터 봐야 하는지" 우선순위를 먼저 제시합니다.

- **영향도 점수**: 제품별 월별 불량률과 시장점유율의 상관계수(부호=방향성) ×
  3개년 누적매출(규모)을 곱해 산출. equipment_id/factory_code는 그 축을 거친
  product_id들의 점수를 합산해 롤업(단순화가 있음 — `domain.py` 문서 참고).
  매칭 월수가 `config.MIN_MONTHS_FOR_CORRELATION`(기본 3개월) 미만이거나 불량률
  변동이 없으면 표본 부족으로 표시.
- **매출 영향 what-if**: 월별 (불량률, 매출) 쌍에 최소자승 회귀를 적합해
  "불량률을 목표치까지 낮추면 매출이 얼마나 바뀌는지"를 원화로 추정. R²·매칭
  월수를 항상 함께 노출해 상관관계≠인과관계라는 한계를 명시.
- 새 에이전트 `agents/priority_agent.py`가 이 랭킹을 만들며, 다른 에이전트와
  동일하게 harness(trace/retry/guardrail)를 거칩니다. `orchestrator`에는
  "priority" 도메인으로 등록되어 있어 "우선조치 대상 알려줘" 같은 자연어 질의로도
  라우팅됩니다.

## 데이터

기본 경로는 `~/Desktop/dataset_1`(실행 사용자의 홈 디렉토리 기준)이며, 환경변수로 바꿀 수 있습니다.

```bash
export DATASET_DIR=/path/to/other/dataset
```

## 구조

```
insight_agent/
  config.py          # 경로/임계치 설정 (DEFECT_SEVERITY_WEIGHTS, MIN_MONTHS_FOR_CORRELATION 포함)
  domain.py          # 데이터 접근·조인·집계 로직 (스키마 지식은 전부 여기에)
                      #   - get_defect_rate_by_product/equipment/factory
                      #   - get_weighted_defect_index, get_monthly_defect_vs_sales(_by_group)
                      #   - get_market_impact_score_by_product/equipment/factory
                      #   - get_revenue_projection (매출 영향 what-if 회귀분석)
  mymcp/             # FastMCP 기반 MCP 서버/클라이언트 (로컬 stdio 전송), 툴 8개
    server.py
    client.py
  agents/            # 도메인 기반: 생산/품질/시장/통합(인과)/우선조치
    production_agent.py
    quality_agent.py
    market_agent.py
    integration_agent.py
    priority_agent.py  # 불량-매출 영향도 Top N 랭킹 (product_id/equipment_id/factory_code)
    orchestrator.py  # 키워드 기반 의도 분류 -> 도메인 에이전트 라우팅
  harness/
    trace.py         # JSONL 트레이스 로깅
    loop.py          # 재시도 루프
    guardrails.py     # 리포트/우선조치 랭킹 스키마 검증 + CSV/xlsx 소스 정합성 검증
  hitl/
    approvals.py      # 파일 기반 승인 큐 (pending/approved/rejected)
    cli.py             # 승인 큐 CLI
  hotl/
    monitor.py         # 리전x카테고리 시장점유율 상시 스냅샷 + 급락 알림
  evals/
    build_golden_set.py
    run_eval.py
  scripts/
    run_pipeline.py    # 엔드투엔드 데모 진입점
  fe/                  # 웹 FE (아래 "웹 FE" 절 참고)
```

## 더 알아보기

### HITL 승인 큐 확인/처리

```bash
python -m insight_agent.hitl.cli list
python -m insight_agent.hitl.cli approve appr-xxxxxxxx
python -m insight_agent.hitl.cli reject appr-xxxxxxxx --reason "원인 재확인 필요"
```

### MCP 서버 단독 실행 / Claude Code 자동 등록

저장소 루트의 [.mcp.json](.mcp.json)에 프로젝트 스코프로 이미 등록되어 있다.
`${CLAUDE_PROJECT_DIR}`를 사용하므로 절대경로 수정 없이, 이 저장소를 클론해서
Claude Code(CLI/Desktop)로 열기만 하면 자동으로 인식된다. 최초 1회 프로젝트
MCP 서버 승인 프롬프트만 확인하면 이후 계속 활성화된 상태로 유지된다.

```json
{
  "mcpServers": {
    "electronics-insight": {
      "type": "stdio",
      "command": "python3",
      "args": ["-m", "insight_agent.mymcp.server"],
      "cwd": "${CLAUDE_PROJECT_DIR:-.}"
    }
  }
}
```

### 골든셋 이밸류에이션

```bash
python -m insight_agent.evals.build_golden_set   # 최초 1회, golden_defects.jsonl 생성
python -m insight_agent.evals.run_eval           # 통과율 출력, 미달 시 non-zero exit
```

### 테스트

```bash
pytest -v
```

### 웹 FE

```bash
python -m insight_agent.fe.server
# -> http://127.0.0.1:8899
```

외부 프레임워크 없이 stdlib `http.server`만으로 만든 백엔드 + 바닐라 JS SPA입니다.
5개 탭(PRD / 트레이스 / HITL 승인 큐 / HOTL 모니터 / **우선조치 대시보드**)이
있습니다. 상단의 제품 선택 후 "분석 실행"을 누르면 통합 에이전트가 실제로
실행되고, 그 결과가 트레이스/승인 큐/HOTL 탭에 그대로 반영됩니다.

**우선조치 대시보드 탭**은 product_id/equipment_id/factory_code 축을 골라
Top N 랭킹을 막대그래프+표로 보여주고, 항목을 클릭하면 월별 불량률-시장점유율
드릴다운 차트와 매출 영향 what-if 패널(목표 불량률 입력 -> 예상 매출 재계산,
산점도+회귀직선 차트)이 열립니다. product_id 행에는 "원인 리포트 발행 요청"
버튼이 있어 기존 HITL 승인 큐로 바로 이어집니다. 차트는 전부 외부 차트
라이브러리 없이 순수 SVG로 그렸고, 로딩 중에는 스켈레톤 자리표시자를 보여줍니다.

## 참고 문서

- `docs/prd.md`은 이 repo에 포함하지 않습니다 — Day 1(데이터 분석 -> PRD 작성)
  실습으로 각자 직접 작성하는 문서이기 때문입니다. 위 "핵심 시나리오"와
  "데이터" 절, `insight_agent/domain.py`의 스키마를 참고해 본인만의 분석
  방향으로 작성해보세요. (우선조치 대시보드는 이 흐름으로 작성된 PRD 예시 하나를
  실제로 구현한 결과입니다.)
- [progress.md](progress.md) — 우선조치 대시보드를 구현하며 내린 결정과 근거
  (지표 선택, 사람 확인이 필요했던 항목, 발견한 버그/한계)를 항목별로 기록한
  진행 로그. Day 2(구현 -> 검증) 실습 산출물 예시로 참고할 수 있습니다.
- [docs/TOKEN_OPTIMIZATION.md](docs/TOKEN_OPTIMIZATION.md) — Claude Code 토큰 최적화 가이드

## 다음 단계 (이 MVP 이후)

1. `narrative.py`의 LLM 요약을 실제 운영 톤/포맷 가이드에 맞게 프롬프트 다듬기
2. 리전별/공장별 접근 권한 분리 (지금은 모든 사용자가 전체 데이터를 조회 가능)
3. equipment_id/factory_code 단위 매출 근사(그 축을 거친 제품군의 매출 합)를
   실제 월별 생산 배정 비율로 정교화 — 지금은 단순 합산이라 여러 축에 중복
   집계될 수 있음 (`progress.md` 참고)
4. 영향도 점수/what-if 회귀분석 결과를 `insight_agent/evals`의 골든셋 검증
   대상으로 편입 (현재 골든셋은 quality_agent Critical 결함 조회만 다룸)
