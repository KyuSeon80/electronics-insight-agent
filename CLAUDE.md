# electronics-insight-agent

`docs/prd.md`에 정의된 "불량-매출 영향도 우선조치 대시보드"를 구현한다.
레이어 경계·작업 규칙·완료 체크리스트는 아래 파일을 따릅니다.

@AGENTS.md

---

## 진행 상태

진행 상태는 `progress.md`에 기록합니다. 이미 완료된 단계는 재실행하지
말고 다음 미완료 단계부터 이어갑니다.

## 참고 자료

- [docs/prd.md](docs/prd.md) — 대시보드 PRD (Day 1 실습 산출물, 저장소에는
  포함되지 않음 — `.gitignore` 참고)
- [outputs/dataset_1_analysis.md](outputs/dataset_1_analysis.md) — dataset_1
  파일별 분석 요약 (PRD의 근거 자료)
- `insight_agent/domain.py` — 데이터 스키마와 조인 로직의 유일한 출처
