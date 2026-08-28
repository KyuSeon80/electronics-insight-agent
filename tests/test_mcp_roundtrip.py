"""커스텀 stdio MCP 서버/클라이언트 왕복 테스트.

fixtures 데이터를 DATASET_DIR로 지정해 dataset_1 없이도 통과해야 한다.
"""
from pathlib import Path

from insight_agent.mymcp.client import McpClient

FIXTURES_DIR = Path(__file__).parent / "fixtures"
PRIORITY_FIXTURES_DIR = Path(__file__).parent / "fixtures_priority"


def test_tools_list_and_call():
    with McpClient(data_dir=str(FIXTURES_DIR)) as client:
        tools = client.list_tools()
        names = {t["name"] for t in tools}
        assert "get_quality_defects" in names
        assert "build_causal_report" in names
        assert "get_market_impact_score_by_product" in names
        assert "get_market_impact_score_by_equipment" in names
        assert "get_market_impact_score_by_factory" in names

        defects = client.call_tool("get_quality_defects", {"severity": "Critical"})
        assert len(defects) == 2

        report = client.call_tool("build_causal_report", {"product_id": "PRD-F001"})
        assert report["critical_defect_count"] == 1


def test_market_impact_score_tools_roundtrip():
    with McpClient(data_dir=str(PRIORITY_FIXTURES_DIR)) as client:
        by_product = {
            row["product_id"]: row
            for row in client.call_tool("get_market_impact_score_by_product", {})
        }
        assert by_product["PRD-P001"]["correlation"] == -1.0
        assert by_product["PRD-P001"]["impact_score"] == 400_000_000.0
        assert by_product["PRD-P002"]["impact_score"] is None

        by_equipment = {
            row["equipment_id"]: row
            for row in client.call_tool("get_market_impact_score_by_equipment", {})
        }
        assert by_equipment["EQ-P01"]["impact_score"] == 400_000_000.0

        by_factory = {
            row["factory_code"]: row
            for row in client.call_tool("get_market_impact_score_by_factory", {})
        }
        assert by_factory["FAC-P01"]["impact_score"] == 400_000_000.0


def test_revenue_projection_tool_roundtrip():
    with McpClient(data_dir=str(PRIORITY_FIXTURES_DIR)) as client:
        result = client.call_tool("get_revenue_projection", {"product_id": "PRD-P003"})
        assert result["slope_krw_per_pp"] == -10_000_000.0
        assert result["projected_revenue_krw"] == 190_000_000.0

        result_custom = client.call_tool(
            "get_revenue_projection",
            {"product_id": "PRD-P003", "target_defect_rate_pct": 0.0},
        )
        assert result_custom["projected_revenue_krw"] == 200_000_000.0

        result_equipment = client.call_tool(
            "get_revenue_projection",
            {"product_id": "EQ-P03", "group_col": "equipment_id"},
        )
        assert result_equipment["slope_krw_per_pp"] == -10_000_000.0
