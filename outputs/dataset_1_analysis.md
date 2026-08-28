# dataset_1 분석 요약

`dataset_1/` 폴더의 xlsx 7개 파일을 열어 스키마·행수·컬럼별 분포를 집계한 결과. 통합 워크북(`electronics_manufacturing_market_data_3yr.xlsx`)의 `Executive_Summary` 시트에 있는 공식 KPI와 대조하여 검증함.

## 1. dim_company_product.xlsx — 제품 마스터 (차원)
- 100행 × 10열, PK: `product_id`, FK 없음(마스터 기준)
- 기업 5개(각 20개 제품): NexaCore, AuraVision, Solis, Veloce, Zenith
- 카테고리 4종(각 25개): 모바일 / 태블릿 / 스마트 홈가전 / 스마트 전자기기
- 출고가 145,000~1,850,000원, 목표마진율 22.0~37.8%, 출시연도 2023~2025
- 라이프사이클: Active 80 / Mature 13 / EOL 7

## 2. dim_equipment.xlsx — 설비 마스터 (차원)
- 54행 × 10열, PK: `equipment_id`, FK 없음
- 공장 3곳(각 18대): FAC-KR-01(화성) / FAC-KR-02(구미) / FAC-VN-01(박닌), 라인 3개씩
- 설비유형 6종(각 9대): SMT/CNC/USW/AVI/AGB/ASM
- 정격전력 4.5~15kWh, 정비주기 30/60/90일, status 전량 `Operational`

## 3. fact_production_run.xlsx — 배치별 생산 실적 (팩트)
- 1,200행 × 17열, PK: `run_id`, FK: `product_id`, `equipment_id`
- 기간 2023-Q3~2026-Q3(약 3년), 공장별 실행수 KR-02(412) > VN-01(405) > KR-01(383)
- 비가동시간 0~129분, OEE 63.11~97.83%(평균 88.8%), 불량률 0.73~9.4%
- 3개년 총 실적수량 1,299,241EA, 양품률 97.0% (Executive_Summary 기준)

## 4. fact_equipment_sensor.xlsx — 설비 IoT 센서 로그 (팩트)
- 2,400행 × 10열, PK: `sensor_log_id`, FK: `run_id`(배치당 2건), `equipment_id`
- 온도 34.9~128.28℃, 진동 0.023~11.232mm/s, 압력 5.45~7.03bar, 토크 28.37~41.78Nm, 피크전류 13.87~26.78A
- `anomaly_flag` 0/1 이진값(생산 이상 탐지용)

## 5. fact_quality_defect.xlsx — 품질 불량 (팩트)
- 1,200행 × 11열, PK: `defect_id`, FK: `run_id`, `product_id`, `equipment_id` (배치당 1건, 1:1)
- 불량유형 18종(외관 단차 81건, 치수 오차 76건 등 비교적 고르게 분포)
- 심각도: Major 559 / Minor 489 / Critical 152
- 원인 6종(작업툴 마모 222건 최다), 조치 5종, 검사자 14명
- 총 감지 불량 1,200건 · 불량수량 39,425EA (Executive_Summary 기준)

## 6. fact_market_sales.xlsx — 월별 시장 판매 (팩트)
- 12,000행 × 16열, PK: `sales_id`, FK: `product_id`
- 지역 4곳(한국/북미/유럽/동남아, 각 3,000건 균등), 채널 4종, 기간 2023-09~2026-08(36개월)
- 판매수량 97~1,406개/건, 매출 14.67M~2.36B원
- 3개년 누적 매출 약 5조 1,064.7억원, 영업이익률 29.6%
- 카테고리별 영업이익률: 스마트전자기기 31.06% > 모바일 30.49% > 스마트홈가전 30.2% > 태블릿 27.48%

## 7. electronics_manufacturing_market_data_3yr.xlsx — 통합 워크북
- 위 6개 팩트/차원 테이블 + `Executive_Summary` 시트(스키마 설명·핵심 KPI 문서화)를 하나로 묶은 번들 파일
- 데이터 내용은 개별 파일들과 동일

## 데이터 특이사항
개별 xlsx(`dim_equipment`, `fact_production_run` 등)의 날짜/타임스탬프 컬럼은 엑셀 일련번호(예: `install_date=44903`)로 저장되어 있는 반면, 통합 워크북 안의 동일 시트는 `2022-12-08` 같은 문자열로 표시된다. 값 자체는 같은 날짜이며, `insight_agent/domain.py`의 `check_source_consistency()`가 바로 이런 소스 간 불일치를 검증하려는 가드레일이다.

## 전체 스키마 구조
2개 차원(`dim_*`) + 4개 팩트(`fact_*`)로 구성된 스타 스키마이며, `product_id` / `run_id` / `equipment_id`를 통해 생산 → 품질 → 시장 성과를 연결해 분석할 수 있다.
