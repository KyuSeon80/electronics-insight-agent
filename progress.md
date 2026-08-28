# Progress — 불량-매출 영향도 우선조치 대시보드 (docs/prd.md)

## 1. 지표 집계 (domain.py) — 완료 (2026-08-28)
- [x] product_id별 수량가중 불량률 집계 함수 (`get_defect_rate_by_product`)
- [x] equipment_id별 수량가중 불량률 집계 함수 (`get_defect_rate_by_equipment`)
- [x] factory_code별 수량가중 불량률 집계 함수 (`get_defect_rate_by_factory`)
- [x] severity 가중 "가중 불량 지수" 집계 함수 (`get_weighted_defect_index`,
      가중치는 `config.DEFECT_SEVERITY_WEIGHTS`)
- [x] fact_production_run(월 집계) x fact_market_sales(월별) product_id 조인
      함수 (`get_monthly_defect_vs_sales`)
- [x] `tests/test_domain.py`에 7개 단위 테스트 추가, synthetic fixture로 전부
      통과 확인
- [x] `load_tables()`가 `{name}.csv`를 우선 찾고 없으면 `{name}.xlsx`를 읽도록
      `_read_table()` 헬퍼로 확장 (`dataset_1`이 xlsx로만 배포되는 경우 대응).
      csv/xlsx 우선순위·xlsx 전용 로딩·미존재 예외 4개 테스트 추가
- [x] 실제 `dataset_1`(xlsx 7개)을 `domain.load_tables()`로 직접 로드해 행수
      일치(100/54/1200/2400/1200/12000) 및 `get_defect_rate_by_factory` 등
      신규 함수 정상 동작 확인 — 더 이상 `pd.read_excel` 우회 불필요
- pytest 27 passed (기존 23 + xlsx 겸용 로딩 4개)

## 2. 영향도 점수 — 완료 (2026-08-28)
- [x] 제품별 월별 불량률 vs 상관계수 계산 (`get_market_impact_score_by_product`)
- [x] 영향도 점수(|상관계수| x 누적매출) 산출
- [x] equipment_id/factory_code 단위 롤업 (`get_market_impact_score_by_equipment/factory`)
- **결정 필요해서 사람에게 확인한 것 (2건)**:
  1. 상관계수 기준 지표: PRD 4.2절이 operating_profit_krw/operating_margin_pct/
     market_share_est_pct 중 무엇을 쓸지 열어뒀음 → operating_margin_pct로
     결정(생산량과 무관하게 수익성만 보는 지표라서).
  2. **그런데 실제 dataset_1을 붙여보니 100개 제품 전부
     operating_margin_pct의 월별 표준편차가 0**이었다(target_margin_rate가
     그대로 고정 반영됨) — 상관계수가 전부 미정의(NaN)로 나와 랭킹이
     무의미해짐. 이 사실을 다시 보고하고 `market_share_est_pct`로 교체하기로
     재확인 받음. 교체 후 실데이터에서 100개 중 99개 제품이 상관계수를 갖고,
     영향도 점수가 제품/설비/공장별로 유의미하게 갈림을 확인함
     (docs/prd.md 4.2절·7절에 기록).
- 표본 부족(매칭 월 < `config.MIN_MONTHS_FOR_CORRELATION`, 기본 3개월) 또는
  불량률 무변동 시 correlation/impact_score는 None 처리.

## 3. MCP / 에이전트 — 완료 (2026-08-28)
- [x] mymcp/server.py에 `get_market_impact_score_by_product/equipment/factory`
      3개 @mcp.tool로 노출
- [x] tests/test_mcp_roundtrip.py에 신규 케이스 추가
- [x] **신규 멀티에이전트 `agents/priority_agent.py` 추가** (기존
      integration_agent에 얹지 않고 별도 에이전트로 분리 — 우선조치 랭킹은
      product_id 인과 리포트와 책임이 달라서). harness 적용: TraceLogger로
      `priority_agent.<tool>`/`priority_agent.top_n` 두 단계 트레이스 기록,
      MCP 호출은 `run_with_retry`로 감쌈, 출력은 `validate_priority_ranking`
      가드레일 통과 후 반환.
- [x] orchestrator.ROUTING_TABLE에 "priority" 도메인 추가
      (키워드: 우선조치/우선순위/랭킹/top/impact), route()에서 분기 연결,
      trace가 다른 도메인과 동일하게 공유됨을 테스트로 확인

## 4. 가드레일 / 설정 — 완료 (2026-08-28)
- [x] harness/guardrails.py에 `validate_priority_ranking` 추가 (impact_score
      음수 금지·None 허용, cumulative_revenue_krw 음수 금지)
- [x] config.py에 `DEFECT_SEVERITY_WEIGHTS`, `MIN_MONTHS_FOR_CORRELATION`
      추가 — 둘 다 PRD에 명시한 대로 미확정 초안임을 주석에 남김

## 5. FE / 산출물 — 완료 (2026-08-28)
- [x] fe/에 "우선조치 대시보드" 탭 추가: product_id/equipment_id/factory_code
      셀렉터 + top_n 입력 + Top N 테이블(공통 1개, group_by에 따라 컬럼 의미
      전환) + product_id 전용 드릴다운(월별 불량률 vs 시장점유율)
- [x] **막대그래프 추가** — 표(숫자)만으로는 부족하다는 피드백에 따라, Top N
      영향도 점수를 순수 SVG 수평 막대그래프로도 렌더링(`renderPriorityBarChart`).
      드릴다운의 이중축 라인차트(`renderDualLineChart`)와 함께 외부 차트
      라이브러리 없이 vanilla JS로 구현 (기존 FE의 "빌드 도구 없음" 원칙 유지)
- [x] `GET /api/priority?group_by=&top_n=` — priority_agent 호출 후
      `outputs/priority_<group_by>.json`에 저장, `GET /api/priority/monthly/<product_id>`
      — 드릴다운용 월별 데이터
- [x] HITL 연동: product_id 행마다 "원인 리포트 발행 요청" 버튼 → 기존
      `/api/run`(integration_agent) 재사용 → HITL 임계치에 따라 자동발행/
      승인대기로 이어짐. 브라우저로 실제 클릭해 "완료: published" 확인
- [x] 실제 dataset_1로 브라우저에서 3개 축 전환, 드릴다운, HITL 버튼 모두
      동작 확인 (콘솔 에러 없음)
- **구현 중 발견/수정한 버그**: `get_monthly_defect_vs_sales`가 돌려주는
  `sales_month`가 pandas Timestamp라서 `df_to_records`의 JSON 직렬화가
  epoch 밀리초로 바꿔버려 드릴다운 차트 x축이 "1719792" 같은 잘린 숫자로
  깨졌다. `domain.py`에서 반환 직전에 `"YYYY-MM"` 문자열로 변환해 수정.

## 6. 검증 — 완료 (2026-08-28)
- [x] tests/fixtures(기존, 표본부족 케이스) + 신규 tests/fixtures_priority
      (수기 계산 가능한 완전 상관 케이스)로 단위 테스트 추가 — domain 11개,
      mcp roundtrip 1개, guardrails 4개, priority_agent 5개, orchestrator
      1개 = 총 22개 신규 테스트
- [x] insight_agent/evals/run_eval.py 통과 확인 — 골든셋 20/20 (100%),
      priority 기능은 기존 골든셋(quality_agent Critical 결함) 범위 밖이라
      항목 추가는 하지 않음
- [x] pytest 전체 통과 확인 — 42 passed

## 7. 추가 기능: 매출 영향 what-if 회귀분석 — 완료 (2026-08-28)

사용자 질문("불량 조치 시 매출에 어떤 효과가 있는지 수치/도식적으로 보여달라")에
답하기 위해 PRD 범위를 넘어 추가한 기능. 기존 영향도 점수(상관계수 기반 랭킹)는
"방향성"만 보여주고 "몇 원"인지는 답하지 못해, 별도의 회귀분석 함수를 추가했다.

- [x] `domain.get_revenue_projection(tables, product_id, target_defect_rate_pct=None)`
      — 월별 (defect_rate_pct, revenue_krw) 쌍에 최소자승 직선을 적합해
      기울기(원/%p), 절편, R², 목표 불량률에서의 예상 매출/증감액/증감률을 계산.
      target 미지정 시 그 제품이 과거에 실제 달성한 최저 불량률을 기본 목표로
      삼는다(임의값이 아닌 데이터 근거 시나리오)
- [x] `mymcp/server.py`에 `get_revenue_projection` 툴 노출,
      `fe/server.py`에 `GET /api/priority/revenue-projection/<product_id>` 추가
- [x] FE 드릴다운 섹션에 "불량률을 낮추면 매출은 어떻게 될까?" 패널 추가:
      목표 불량률 입력 + 재계산 버튼, 수치 요약(1%p당 원화 효과·목표 시나리오
      예상 매출·증감액/률), 산점도+회귀직선+목표지점 SVG 차트
      (`renderWhatIfChart`) — 표(숫자)와 그래프를 함께 제공
- [x] R²·매칭월수를 항상 함께 노출해 "상관관계≠인과관계, 표본 적으면 신뢰도
      낮음"을 매번 명시 (docs/prd.md 7절 한계와 동일 원칙)
- [x] tests/fixtures_priority에 PRD-P003(새 설비 EQ-P03/공장 FAC-P02, 불량률과
      매출이 완벽한 1차식 관계 — 기울기 -1,000만원/%p, R²=1.0)을 추가해
      회귀 계산을 손검산으로 검증. PRD-P001(매출 무변동 → 기울기 0, R² 없음),
      tests/fixtures의 PRD-F001(매칭 1개월 → 회귀 불가) 등 경계 케이스도 테스트
- [x] 실제 dataset_1(PRD-1002)로 브라우저 확인: "불량률 1%p당 매출 약
      2.3억원 감소 경향", "목표 불량률 2.18%로 낮추면 예상 매출 +1.66억원
      (+5.12%)", R²=10.7%·매칭 6개월 — 재계산 버튼으로 목표값 변경도 확인
- pytest 48 passed (기존 42 + 신규 6: domain 5, mcp roundtrip 1)

### 7.1 equipment_id도 선택해서 볼 수 있도록 확장 — 완료 (2026-08-28)

사용자 요청: "product_id뿐만 아니라 equipment_id의 매출 관련도도 확인할 수
있도록". 기존 what-if는 product_id 전용이었는데(fact_market_sales가
product_id와만 직접 연결됨), equipment_id/factory_code까지 일반화했다.

- [x] `domain.get_monthly_defect_vs_sales_by_group(tables, group_col, group_value)`
      추가 — equipment_id/factory_code는 그 축을 거친 product_id 집합을 구해
      그 제품들의 월별 매출 합계로 근사(특정 월 실제 생산 배정은 반영 안 함,
      기존 영향도 점수 롤업과 동일한 단순화). equipment_id 불량률 자체는
      fact_production_run에서 정확히 집계
- [x] `get_revenue_projection`에 `group_col` 파라미터 추가(기본 `product_id`,
      기존 호출 전부 하위호환 — 위치 인자만 쓰고 있어서 시그니처 확장이 안전했음)
- [x] `mymcp/server.py`/`fe/server.py`에 `group_col`/`group_by` 파라미터 전달,
      FE에서 세 축(product_id/equipment_id/factory_code) 모두 "월별 추이"
      버튼 노출("원인 리포트 발행 요청"은 product_id에서만 — 인과 리포트가
      product_id 기준이라)
- [x] equipment_id/factory_code 드릴다운에는 "이 축 매출은 근사값" 캐비어트를
      화면에 고정 노출
- [x] tests/fixtures_priority에서 EQ-P01/EQ-P02/EQ-P03(각기 다른 제품)와
      FAC-P01(EQ-P01+EQ-P02 합산) 케이스로 검증 — 단일 제품 설비는 product
      단위와 동일한 결과, 다중 제품 공장은 합산 로직 확인
- [x] 실제 dataset_1(EQ-032)로 브라우저 확인: 25개월 매칭, "1%p당 약
      9,600만원 증가 경향(R²=0.1%)" — 근사값 캐비어트 문구 정상 노출
- pytest 54 passed (기존 48 + 신규 6: domain 5, mcp roundtrip 1)

## 오픈 이슈 — 확정 완료 (2026-08-28, docs/prd.md §7·§9 참고)
- [x] 심각도 가중치: Critical=3/Major=2/Minor=1로 확정 (`config.DEFECT_SEVERITY_WEIGHTS`)
- [x] Top N 기본값 10 / 갱신 방식은 온디맨드(FE 새로고침 시 즉시 계산)로 확정
      — 배치 자동 갱신 도입 안 함
- [x] 설비/공장 롤업의 중복 집계 문제는 현재의 단순 합산 방식을 최종 설계로
      확정. 생산량 가중 분배안은 검토했으나 MVP 단계 해석 용이성을 우선해 기각
- [x] operating_margin_pct가 이 데이터셋에서 상수라 상관분석에 못 씀 (해결됨 —
      market_share_est_pct로 대체) — 실제 운영 데이터로 바뀌면 이 가정도 다시
      깨질 수 있어 데이터 소스 교체 시 재검증 필요
- **남은 제약 (결정 사항 아님)**: 공장↔리전 매핑 없음 — 데이터셋에 해당 FK가
  없어 리전 단위 인과분석은 범위 밖. 필요해지면 별도 마스터 데이터 확보 필요.

## 8. FE 표에 제품명/설비명 표기 — 완료 (2026-08-28)

사용자 요청: "production id와 equipment id의 제품명과 회사명도 표에 표기해달라"
— ID만으로는 어떤 제품/설비인지 알아보기 어렵다는 피드백.

- [x] `get_market_impact_score_by_product`가 `dim_company_product`에서
      `model_name`/`company_name`을 조인해 반환하도록 확장
- [x] `_rollup_impact_score`(equipment_id/factory_code 공통)가 `dim_equipment`
      에서 `equipment_name`/`factory_name`을 조인 — factory_code는 여러
      equipment_id에 걸쳐 있어 (factory_code, factory_name) 조합만 중복 제거
- [x] FE 우선조치 표에 "이름" 컬럼 추가 (`labelFor()`): product_id는
      "모델명 (회사명)", equipment_id는 "설비명 · 공장명", factory_code는
      "공장명"으로 표시
- [x] 실제 dataset_1로 브라우저 확인: product_id 모드에서
      "NX-Aura Phone 15 Prime (NexaCore Technologies)", equipment_id
      모드에서 "정밀 알루미늄 가공기 #3 · FAC-KR-02 (구미)" 정상 노출
- pytest 54 passed (기존 컬럼 유지 + 신규 컬럼 추가라 기존 테스트 영향 없음)

## 9. FE 요청은 임계치 무관 항상 승인 대기로 — 완료 (2026-08-28)

사용자 요청: "분석 실행/원인 리포트 발행 요청 버튼을 누르면 임계치와 무관하게
항상 승인 큐에 추가해달라". 기존에는 Critical 결함이
`CRITICAL_DEFECT_HITL_THRESHOLD`(3건) 미만이면 `auto_publish()`가 승인 큐를
건너뛰고 `outputs/`에 바로 썼다(README에 문서화된 의도된 동작) — 그래서
Critical이 적은 제품을 테스트하면 HITL 큐에 아무것도 안 뜨는 것처럼 보였다.

- [x] `integration_agent.run()`에 `force_approval: bool = False` 파라미터
      추가. `force_approval or critical_defect_count >= THRESHOLD`일 때
      승인 대기로 보낸다. 기본값 False라 CLI(`scripts/run_pipeline.py`)와
      골든셋/기존 테스트(`test_orchestrator.py`)의 임계치 기반 동작은
      그대로 유지됨 — **FE 전용 옵트인**으로 범위를 좁혔다.
- [x] `fe/server.py`의 `POST /api/run`이 `force_approval=True`로 호출하도록
      변경 — 상단 "분석 실행"과 우선조치 표의 "원인 리포트 발행 요청" 버튼은
      둘 다 이 엔드포인트 하나를 쓰므로 한 곳만 고치면 둘 다 적용됨
- [x] `tests/test_integration_agent.py` 신규: 기본값(임계치 기반) 유지 확인
      + force_approval=True가 Critical 1건짜리 제품도 승인 대기로 보내고
      실제 `approvals/pending/`에 파일이 생기는지 확인
- [x] 실제 dataset_1(PRD-1076, Critical 2건 — README의 "자동 발행" 예시
      그 자체)로 `/api/run` 직접 호출 + 브라우저 클릭 두 경로 모두
      `status: "pending_approval"`로 바뀐 것 확인
- pytest 57 passed (기존 54 + 신규 3)

## 10. "월별 추이" 버튼 제거, 행 클릭으로 대체 — 완료 (2026-08-28)

사용자 요청: "월별 추이 버튼은 삭제해도 됩니다." 버튼만 지우면 드릴다운
(라인차트+what-if)이 열 방법이 없어져 죽은 코드가 되므로, 사람에게 확인 후
"행(row) 클릭으로 드릴다운 유지"를 선택받았다.

- [x] `renderPriorityTable`에서 "월별 추이" 버튼 제거, 대신 `<tr>`에 클릭
      리스너를 달아 행을 클릭하면 `loadPriorityDrilldown()`이 열리게 함
      (`.row-clickable` 클래스로 `cursor: pointer` 부여)
- [x] 액션 셀(`.priority-actions`, "원인 리포트 발행 요청" 버튼) 클릭은
      `e.target.closest(".priority-actions")`로 걸러내 행 클릭 핸들러가
      같이 발동하지 않게 함 — 브라우저로 직접 확인(리포트 버튼 클릭 시
      드릴다운 타이틀이 안 바뀌는 것을 센티널 값으로 검증)
- equipment_id/factory_code 행은 이제 액션 셀이 완전히 비어 있고, 행 전체
  클릭으로만 드릴다운을 연다 (기존과 동일한 기능, 진입점만 변경)
