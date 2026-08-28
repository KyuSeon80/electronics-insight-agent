"""domain.py의 조회 함수가 올바르게 동작하는지 확인.

실제 dataset_1이 아니라 tests/fixtures/의 소형 synthetic 데이터로 돈다 --
fresh clone에서 dataset_1 없이도 unit test가 통과해야 한다. dataset_1을 쓰는
엔드투엔드 데모/골든셋 이밸류에이션은 README의 실행 섹션에서 별도로 다룬다.
"""
from pathlib import Path

import pandas as pd
import pytest

from insight_agent import domain

FIXTURES_DIR = Path(__file__).parent / "fixtures"
PRIORITY_FIXTURES_DIR = Path(__file__).parent / "fixtures_priority"


def test_load_tables_row_counts():
    tables = domain.load_tables(FIXTURES_DIR)
    assert len(tables.dim_company_product) == 3
    assert len(tables.dim_equipment) == 2
    assert len(tables.fact_production_run) == 4
    assert len(tables.fact_equipment_sensor) == 4
    assert len(tables.fact_quality_defect) == 4
    assert len(tables.fact_market_sales) == 4


def test_get_quality_defects_severity_filter():
    tables = domain.load_tables(FIXTURES_DIR)
    critical = domain.get_quality_defects(tables, severity="Critical")
    assert len(critical) == 2
    assert set(critical["product_id"]) == {"PRD-F001", "PRD-F003"}
    assert set(critical["severity"]) == {"Critical"}


def test_get_production_anomalies_oee_and_sensor_flag():
    tables = domain.load_tables(FIXTURES_DIR)
    anomalies = domain.get_production_anomalies(tables)
    # RUN-F002: OEE 82.0 (<90) + 센서 anomaly_flag=1 -- 둘 다 걸려도 한 번만 잡힘
    # RUN-F003: OEE 95.0(정상)이지만 센서 anomaly_flag=1 -- OR 조건으로 잡혀야 함
    assert set(anomalies["run_id"]) == {"RUN-F002", "RUN-F003"}


def test_build_causal_report_known_product():
    tables = domain.load_tables(FIXTURES_DIR)
    report = domain.build_causal_report(tables, "PRD-F001")
    assert report["product_id"] == "PRD-F001"
    assert report["production_run_count"] == 2
    assert report["anomaly_run_count"] == 1  # RUN-F002만 PRD-F001 소속
    assert report["critical_defect_count"] == 1
    assert report["latest_market_share_pct"] == 15.0  # 2024-02(가장 최근) 값
    assert isinstance(report["market_share_trend"], list)
    assert len(report["market_share_trend"]) == 2


def test_build_causal_report_unknown_product_raises():
    tables = domain.load_tables(FIXTURES_DIR)
    try:
        domain.build_causal_report(tables, "PRD-9999")
        assert False, "should have raised ValueError"
    except ValueError:
        pass


# --- 우선조치 대시보드 (docs/prd.md) 집계 함수 ------------------------------


def test_get_defect_rate_by_product():
    tables = domain.load_tables(FIXTURES_DIR)
    rates = domain.get_defect_rate_by_product(tables)
    by_product = rates.set_index("product_id")
    # PRD-F001: RUN-F001(actual 980, defect 10) + RUN-F002(actual 800, defect 50)
    assert by_product.loc["PRD-F001", "actual_qty"] == 1780
    assert by_product.loc["PRD-F001", "defect_qty"] == 60
    assert by_product.loc["PRD-F001", "defect_rate_pct"] == 3.37
    # 가장 불량률이 높은 제품이 첫 행이어야 한다
    assert rates.iloc[0]["product_id"] == "PRD-F001"


def test_get_defect_rate_by_equipment():
    tables = domain.load_tables(FIXTURES_DIR)
    rates = domain.get_defect_rate_by_equipment(tables)
    by_equipment = rates.set_index("equipment_id")
    assert by_equipment.loc["EQ-F02", "actual_qty"] == 1680  # RUN-F003 + RUN-F004
    assert by_equipment.loc["EQ-F02", "defect_qty"] == 15


def test_get_defect_rate_by_factory():
    tables = domain.load_tables(FIXTURES_DIR)
    rates = domain.get_defect_rate_by_factory(tables)
    assert len(rates) == 1  # fixture는 FAC-TEST-01 단일 공장
    assert rates.iloc[0]["factory_code"] == "FAC-TEST-01"
    assert rates.iloc[0]["actual_qty"] == 3460
    assert rates.iloc[0]["defect_qty"] == 75


def test_get_weighted_defect_index_by_product():
    tables = domain.load_tables(FIXTURES_DIR)
    index = domain.get_weighted_defect_index(tables, "product_id")
    by_product = index.set_index("product_id")
    # PRD-F001: DEF-F001(20, Critical=3) + DEF-F002(5, Minor=1) = 60 + 5 = 65
    assert by_product.loc["PRD-F001", "weighted_defect_index"] == 65
    assert by_product.loc["PRD-F001", "critical_defect_count"] == 1
    # 가중 지수가 가장 높은 제품이 첫 행
    assert index.iloc[0]["product_id"] == "PRD-F001"


def test_get_weighted_defect_index_by_factory_joins_via_equipment():
    tables = domain.load_tables(FIXTURES_DIR)
    index = domain.get_weighted_defect_index(tables, "factory_code")
    assert len(index) == 1
    assert index.iloc[0]["factory_code"] == "FAC-TEST-01"
    # 전체 4건 defect의 가중합: 60 + 5 + 10 + 30 = 105
    assert index.iloc[0]["weighted_defect_index"] == 105


def test_get_monthly_defect_vs_sales_inner_joins_on_product_and_month():
    tables = domain.load_tables(FIXTURES_DIR)
    merged = domain.get_monthly_defect_vs_sales(tables)
    # production: (PRD-F001,2024-01) (PRD-F002,2024-02) (PRD-F003,2024-02)
    # sales:      (PRD-F001,2024-01) (PRD-F001,2024-02) (PRD-F002,2024-01) (PRD-F003,2024-02)
    # 교집합은 PRD-F001/2024-01과 PRD-F003/2024-02 두 건뿐이다.
    assert len(merged) == 2
    row = merged[merged["product_id"] == "PRD-F001"].iloc[0]
    assert row["defect_rate_pct"] == 3.37
    assert row["revenue_krw"] == 45000000
    assert row["operating_margin_pct"] == 33.33


def test_get_monthly_defect_vs_sales_filters_by_product_id():
    tables = domain.load_tables(FIXTURES_DIR)
    merged = domain.get_monthly_defect_vs_sales(tables, product_id="PRD-F003")
    assert set(merged["product_id"]) == {"PRD-F003"}
    assert len(merged) == 1


# --- CSV/xlsx 겸용 로딩 (dataset_1이 xlsx로만 배포되는 경우 대응) -----------


def test_read_table_falls_back_to_xlsx_when_csv_missing(tmp_path):
    df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    df.to_excel(tmp_path / "dummy.xlsx", index=False)
    loaded = domain._read_table(tmp_path, "dummy.csv")
    pd.testing.assert_frame_equal(loaded, df)


def test_read_table_prefers_csv_over_xlsx_when_both_exist(tmp_path):
    pd.DataFrame({"a": [1]}).to_csv(tmp_path / "dummy.csv", index=False)
    pd.DataFrame({"a": [999]}).to_excel(tmp_path / "dummy.xlsx", index=False)
    loaded = domain._read_table(tmp_path, "dummy.csv")
    assert loaded["a"].iloc[0] == 1


def test_read_table_raises_when_neither_csv_nor_xlsx_exists(tmp_path):
    try:
        domain._read_table(tmp_path, "missing.csv")
        assert False, "should have raised FileNotFoundError"
    except FileNotFoundError:
        pass


# --- 영향도 점수 (docs/prd.md 4.2절) ---------------------------------------


def test_get_market_impact_score_by_product_marks_insufficient_months_as_none():
    # tests/fixtures의 각 product_id는 매칭 월이 1개뿐이라(min_months=3 미만)
    # 상관계수/영향도 점수를 계산하지 않고 None으로 남겨야 한다.
    tables = domain.load_tables(FIXTURES_DIR)
    scores = domain.get_market_impact_score_by_product(tables)
    by_product = scores.set_index("product_id")
    assert by_product["correlation"].isnull().all()
    assert by_product["impact_score"].isnull().all()
    # 누적 매출액은 매칭 월 수와 무관하게 정상 계산돼야 한다
    assert by_product.loc["PRD-F001", "cumulative_revenue_krw"] == 85_500_000.0


def test_get_market_impact_score_by_product_computes_perfect_negative_correlation():
    tables = domain.load_tables(PRIORITY_FIXTURES_DIR)
    scores = domain.get_market_impact_score_by_product(tables)
    by_product = scores.set_index("product_id")

    # PRD-P001: 불량률 1,2,3,4% <-> 시장점유율 20,15,10,5% -> 완벽한 음의 상관(-1.0)
    assert by_product.loc["PRD-P001", "matched_months"] == 4
    assert by_product.loc["PRD-P001", "correlation"] == -1.0
    assert by_product.loc["PRD-P001", "cumulative_revenue_krw"] == 400_000_000.0
    assert by_product.loc["PRD-P001", "impact_score"] == 400_000_000.0

    # PRD-P002: 불량률이 매달 2%로 고정 -> 분산이 없어 상관계수가 정의되지 않음(None/NaN)
    # correlation 컬럼에 -1.0(PRD-P001)과 None(PRD-P002)이 섞여 있으면 pandas가
    # None을 NaN으로 승격시키므로, `is None`이 아니라 pd.isna로 확인한다.
    assert pd.isna(by_product.loc["PRD-P002", "correlation"])
    assert pd.isna(by_product.loc["PRD-P002", "impact_score"])
    assert by_product.loc["PRD-P002", "cumulative_revenue_krw"] == 200_000_000.0

    # impact_score 내림차순 정렬 (None은 뒤로)
    assert scores.iloc[0]["product_id"] == "PRD-P001"


def test_get_market_impact_score_by_equipment_rollup():
    tables = domain.load_tables(PRIORITY_FIXTURES_DIR)
    by_equipment = domain.get_market_impact_score_by_equipment(tables).set_index("equipment_id")

    # EQ-P01은 PRD-P001만 생산 -> impact_score 그대로 이어받음
    assert by_equipment.loc["EQ-P01", "impact_score"] == 400_000_000.0
    assert by_equipment.loc["EQ-P01", "scored_product_count"] == 1

    # EQ-P02는 PRD-P002만 생산하는데 PRD-P002는 점수가 None -> 0으로 합산
    assert by_equipment.loc["EQ-P02", "impact_score"] == 0.0
    assert by_equipment.loc["EQ-P02", "scored_product_count"] == 0


def test_get_market_impact_score_by_factory_rollup():
    tables = domain.load_tables(PRIORITY_FIXTURES_DIR)
    by_factory = domain.get_market_impact_score_by_factory(tables).set_index("factory_code")

    # FAC-P01은 EQ-P01/EQ-P02를 모두 포함 -> 두 제품 모두 집계되지만 PRD-P002는 0
    assert by_factory.loc["FAC-P01", "product_count"] == 2
    assert by_factory.loc["FAC-P01", "scored_product_count"] == 1
    assert by_factory.loc["FAC-P01", "impact_score"] == 400_000_000.0


# --- 매출 영향 what-if 분석 (get_revenue_projection) ------------------------


def test_get_revenue_projection_fits_perfect_linear_relationship():
    tables = domain.load_tables(PRIORITY_FIXTURES_DIR)
    # PRD-P003: 불량률 1,2,3,4% <-> 매출 190M,180M,170M,160M -> 완벽한 직선(기울기 -1000만원/%p)
    result = domain.get_revenue_projection(tables, "PRD-P003")

    assert result["matched_months"] == 4
    assert result["slope_krw_per_pp"] == -10_000_000.0
    assert result["intercept_krw"] == 200_000_000.0
    assert result["r_squared"] == 1.0
    assert result["current_avg_defect_rate_pct"] == 2.5
    assert result["current_avg_revenue_krw"] == 175_000_000.0
    # target 미지정 시 과거 최저 불량률(1.0%)을 목표로 삼는다
    assert result["target_defect_rate_pct"] == 1.0
    assert result["projected_revenue_krw"] == 190_000_000.0
    assert result["revenue_delta_krw"] == 15_000_000.0
    assert result["revenue_delta_pct"] == pytest.approx(8.57, abs=0.01)


def test_get_revenue_projection_with_explicit_target():
    tables = domain.load_tables(PRIORITY_FIXTURES_DIR)
    result = domain.get_revenue_projection(tables, "PRD-P003", target_defect_rate_pct=0.0)
    assert result["target_defect_rate_pct"] == 0.0
    assert result["projected_revenue_krw"] == 200_000_000.0  # 회귀선의 절편(외삽)
    assert result["revenue_delta_krw"] == 25_000_000.0


def test_get_revenue_projection_flat_line_when_revenue_has_no_variance():
    # PRD-P001은 불량률은 변하지만(1~4%) 매출은 매달 100,000,000원으로 고정돼
    # 있다 -- 최소자승 적합 결과는 기울기 0(수평선)이 되고, 분산이 없어(ss_tot=0)
    # 결정계수(r_squared)만 정의되지 않는다(None). 기울기 자체는 "불량률이
    # 이 제품 매출에 영향을 주지 않는다"는 유효한 정보라 None으로 숨기지 않는다.
    tables = domain.load_tables(PRIORITY_FIXTURES_DIR)
    result = domain.get_revenue_projection(tables, "PRD-P001")
    assert result["matched_months"] == 4
    assert result["slope_krw_per_pp"] == pytest.approx(0.0, abs=1e-6)
    assert result["r_squared"] is None
    assert result["projected_revenue_krw"] == pytest.approx(100_000_000.0, abs=1.0)
    assert result["current_avg_revenue_krw"] == 100_000_000.0


def test_get_revenue_projection_insufficient_months():
    # tests/fixtures의 PRD-F001은 매칭 월이 1개뿐이라 회귀선을 적합할 수 없다.
    tables = domain.load_tables(FIXTURES_DIR)
    result = domain.get_revenue_projection(tables, "PRD-F001")
    assert result["matched_months"] == 1
    assert result["slope_krw_per_pp"] is None
    assert result["current_avg_revenue_krw"] == 45_000_000.0


def test_get_revenue_projection_unknown_product_returns_empty():
    tables = domain.load_tables(PRIORITY_FIXTURES_DIR)
    result = domain.get_revenue_projection(tables, "PRD-9999")
    assert result["matched_months"] == 0
    assert result["current_avg_revenue_krw"] is None


# --- equipment_id/factory_code 단위 월별 추이 & what-if -----------------------


def test_get_monthly_defect_vs_sales_by_group_product_id_matches_direct_call():
    tables = domain.load_tables(PRIORITY_FIXTURES_DIR)
    direct = domain.get_monthly_defect_vs_sales(tables, product_id="PRD-P001")
    via_group = domain.get_monthly_defect_vs_sales_by_group(tables, "product_id", "PRD-P001")
    pd.testing.assert_frame_equal(direct, via_group)


def test_get_monthly_defect_vs_sales_by_group_equipment_single_product():
    tables = domain.load_tables(PRIORITY_FIXTURES_DIR)
    # EQ-P01은 PRD-P001만 생산하므로 product 단위와 동일한 수치가 나와야 한다
    df = domain.get_monthly_defect_vs_sales_by_group(tables, "equipment_id", "EQ-P01")
    assert len(df) == 4
    assert set(df["equipment_id"]) == {"EQ-P01"}
    assert df.iloc[0]["defect_rate_pct"] == 1.0
    assert df.iloc[0]["revenue_krw"] == 100_000_000.0


def test_get_monthly_defect_vs_sales_by_group_factory_aggregates_multiple_equipment():
    tables = domain.load_tables(PRIORITY_FIXTURES_DIR)
    # FAC-P01 = EQ-P01(PRD-P001) + EQ-P02(PRD-P002) -- 두 제품의 불량/실적이
    # 월별로 합산되고, 매출도 두 제품의 합(150,000,000원, 매달 고정)이 된다
    df = domain.get_monthly_defect_vs_sales_by_group(tables, "factory_code", "FAC-P01")
    assert len(df) == 4
    row_jan = df[df["sales_month"] == "2024-01"].iloc[0]
    assert row_jan["defect_rate_pct"] == 1.33  # (10+10)/(1000+500)*100
    assert row_jan["revenue_krw"] == 150_000_000.0


def test_get_monthly_defect_vs_sales_by_group_rejects_unknown_group_col():
    tables = domain.load_tables(PRIORITY_FIXTURES_DIR)
    with pytest.raises(ValueError):
        domain.get_monthly_defect_vs_sales_by_group(tables, "region", "X")


def test_get_revenue_projection_by_equipment():
    tables = domain.load_tables(PRIORITY_FIXTURES_DIR)
    result = domain.get_revenue_projection(tables, "EQ-P03", group_col="equipment_id")
    assert result["equipment_id"] == "EQ-P03"
    # EQ-P03은 PRD-P003만 생산하므로 product 단위 회귀와 동일한 결과가 나온다
    assert result["slope_krw_per_pp"] == -10_000_000.0
    assert result["r_squared"] == 1.0


def test_get_revenue_projection_by_factory_uses_aggregated_revenue():
    tables = domain.load_tables(PRIORITY_FIXTURES_DIR)
    result = domain.get_revenue_projection(tables, "FAC-P01", group_col="factory_code")
    assert result["factory_code"] == "FAC-P01"
    assert result["matched_months"] == 4
    # 매출이 매달 150,000,000원으로 고정돼 있어 기울기는 0(수평선)이어야 한다
    assert result["slope_krw_per_pp"] == pytest.approx(0.0, abs=1e-6)
    assert result["current_avg_revenue_krw"] == 150_000_000.0


def test_load_tables_reads_xlsx_only_dataset(tmp_path):
    # dataset_1이 xlsx로만 배포된 상황을 흉내낸다 -- 개별 xlsx는 CSV를 단일
    # 시트로 감싼 형태라, fixture csv를 그대로 xlsx로 옮겨써도 스키마는 같다.
    for filename in domain.TABLE_FILES.values():
        src = pd.read_csv(FIXTURES_DIR / filename, encoding="utf-8-sig")
        xlsx_name = Path(filename).with_suffix(".xlsx").name
        src.to_excel(tmp_path / xlsx_name, index=False)

    tables = domain.load_tables(tmp_path)
    assert len(tables.dim_company_product) == 3
    assert len(tables.fact_production_run) == 4
    assert len(tables.fact_market_sales) == 4

    # 로드된 xlsx 데이터로 신규 집계 함수도 그대로 동작해야 한다
    rates = domain.get_defect_rate_by_product(tables)
    assert rates.set_index("product_id").loc["PRD-F001", "defect_qty"] == 60
