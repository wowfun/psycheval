from __future__ import annotations

import io
import unittest
import zipfile
from xml.etree import ElementTree

from psycheval.serve.errors import HttpError
from psycheval.serve.exports import xlsx_summary
from psycheval.serve.payloads import summary_export_payload
from psycheval.serve.summary_xlsx import SummaryWorksheet, summary_workbook


def metric(key: str, value_type: str, mean: float | None) -> dict:
    distribution = None
    if mean is not None:
        distribution = {
            "min": mean,
            "q1": mean,
            "p50": mean,
            "q3": mean,
            "p95": mean,
            "max": mean,
        }
    return {
        "key": key,
        "type": value_type,
        "count": 1 if mean is not None else 0,
        "mean": mean,
        "distribution": distribution,
    }


def summary_groups() -> list[dict]:
    return [
        {
            "key": "agent-a",
            "label": "=agent-a",
            "count": 1,
            "metrics": [
                metric("duration_ms", "duration", 1_000),
                metric("ttft_ms", "duration", 250),
                metric("tps", "number", 40),
                metric("tokens", "number", 0),
                metric("cache_hit_rate", "percent", 0.25),
                metric("turns", "number", None),
                metric("model_duration_ms", "duration", 500),
                metric("total_tool_calls", "number", 2),
                metric("tool_success_rate", "percent", 0),
            ],
        }
    ]


class SummaryXlsxTests(unittest.TestCase):
    def test_detailed_rate_cells_are_numeric_percentages_with_full_precision(self):
        content = xlsx_summary(
            [
                {"total_tool_calls": 15, "total_tool_errors": 1},
                {"total_tool_calls": 1, "total_tool_errors": 1},
                {"total_tool_calls": 0, "total_tool_errors": 0},
                {"total_tool_calls": 3},
            ]
        )
        ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            sheet = ElementTree.fromstring(archive.read("xl/worksheets/sheet1.xml"))
            rows = sheet.findall("s:sheetData/s:row", ns)
            index = next(
                i
                for i, cell in enumerate(rows[0])
                if cell.findtext("s:is/s:t", namespaces=ns) == "Tool Success Rate"
            )
            first, zero, no_calls, unknown = [list(row)[index] for row in rows[1:]]
            self.assertIsNone(first.get("t"))
            self.assertAlmostEqual(float(first.findtext("s:v", namespaces=ns)), 14 / 15)
            self.assertEqual(float(zero.findtext("s:v", namespaces=ns)), 0)
            self.assertIsNone(no_calls.find("s:v", ns))
            self.assertIsNone(unknown.find("s:v", ns))
            styles = ElementTree.fromstring(archive.read("xl/styles.xml"))
            style = styles.find("s:cellXfs", ns)[int(first.get("s"))]
            number_format = styles.find(
                f"s:numFmts/s:numFmt[@numFmtId='{style.get('numFmtId')}']", ns
            )
            self.assertEqual(number_format.get("formatCode"), "0.00%")

    def test_payload_validation_is_strict_and_ordered_deduplicated(self) -> None:
        query = {
            "state": "all",
            "search": "needle",
            "categories": [],
            "tags": [],
            "agents": [],
            "models": [],
            "tasks": [],
            "jobs": [],
            "providers": [],
            "datasets": [],
            "results": [],
            "views": ["B", "A", "B"],
            "browser_views": [],
        }
        request = summary_export_payload(
            {
                "scope": "leaderboard",
                "metrics": ["score", "duration_ms"],
                "query": query,
                "group_by": "model",
                "statistic": "p95",
            }
        )
        self.assertEqual(request.query.search, "needle")
        self.assertEqual(request.query_views, ("B", "A"))
        self.assertEqual(request.group_by, "model")
        self.assertEqual(request.statistic, "p95")
        category_request = summary_export_payload(
            {
                "scope": "leaderboard",
                "metrics": ["score", "duration_ms"],
                "query": query,
                "group_by": "category",
                "statistic": "mean",
            }
        )
        self.assertEqual(category_request.group_by, "category")
        views = summary_export_payload(
            {"scope": "saved_views", "views": ["B", "A", "B"]}
        )
        self.assertEqual(views.views, ("B", "A"))
        for invalid in (
            {
                "scope": "leaderboard",
                "metrics": ["score", "duration_ms"],
                "query": {**query, "page": 1},
                "group_by": "agent",
                "statistic": "mean",
            },
            {
                "scope": "leaderboard",
                "metrics": ["score", "duration_ms"],
                "query": query,
                "group_by": "agent",
                "statistic": "median",
            },
            {
                "scope": "leaderboard",
                "metrics": ["score", "duration_ms"],
                "query": query,
                "group_by": ["agent"],
                "statistic": "mean",
            },
            {
                "scope": "leaderboard",
                "metrics": ["score", "duration_ms"],
                "query": query,
                "group_by": "agent",
                "statistic": ["mean"],
            },
            {
                "scope": "leaderboard",
                "metrics": ["score", "duration_ms"],
                "query": {key: value for key, value in query.items() if key != "tags"},
                "group_by": "agent",
                "statistic": "mean",
            },
            {"scope": "saved_views", "views": ["a"], "extra": True},
        ):
            with self.subTest(invalid=invalid), self.assertRaises(HttpError):
                summary_export_payload(invalid)

    def test_workbook_has_native_charts_numeric_cells_and_literal_strings(self) -> None:
        content = summary_workbook(
            [
                SummaryWorksheet(
                    name="Unsafe/View",
                    group_by="agent",
                    matched_count=1,
                    groups=summary_groups(),
                    statistic="p95",
                    metadata=(
                        ("Configuration", "group_by: agent"),
                        ("Notes", "=1+1\nhttps://example.invalid"),
                        ("Long Notes", "x" * 33_000 + "tail"),
                    ),
                ),
                SummaryWorksheet(
                    name="unsafe:view",
                    group_by="agent",
                    matched_count=1,
                    groups=summary_groups(),
                ),
            ]
        )
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            names = set(archive.namelist())
            workbook = archive.read("xl/workbook.xml").decode("utf-8")
            first_sheet = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")
            shared_strings = archive.read("xl/sharedStrings.xml").decode("utf-8")
            charts = [
                archive.read(name).decode("utf-8")
                for name in names
                if name.startswith("xl/charts/") and name.endswith(".xml")
            ]
        self.assertEqual(len(charts), 16)
        self.assertIn("xl/drawings/drawing1.xml", names)
        self.assertIn('name="Unsafe_View"', workbook)
        self.assertIn('name="unsafe_view (2)"', workbook)
        self.assertIn("=1+1", shared_strings)
        self.assertIn("https://example.invalid", shared_strings)
        self.assertIn("tail", shared_strings)
        self.assertIn("Long Notes (cont.)", shared_strings)
        self.assertIn("Avg TTFT", shared_strings)
        self.assertIn("Decode TPS", shared_strings)
        self.assertIn("Cache Hit", shared_strings)
        self.assertIn("Tokens", shared_strings)
        self.assertIn("Tool Success Rate", shared_strings)
        self.assertNotIn("Reward", shared_strings)
        self.assertNotIn("Turns", shared_strings)
        self.assertNotIn("<f>", first_sheet)
        self.assertIn("1.157407407407407E-05", first_sheet)
        self.assertRegex(first_sheet, r"<v>0</v>")
        self.assertTrue(
            any("p95" in chart.lower() and "$I$" in chart for chart in charts)
        )

    def test_zero_match_sheet_has_headers_and_no_chart_parts(self) -> None:
        content = summary_workbook(
            [
                SummaryWorksheet(
                    name="Empty",
                    group_by="overall",
                    matched_count=0,
                    groups=[],
                    metadata=(("Notes", "Nothing here"),),
                )
            ]
        )
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            names = set(archive.namelist())
            sheet = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")
            strings = archive.read("xl/sharedStrings.xml").decode("utf-8")
        self.assertFalse(any(name.startswith("xl/charts/") for name in names))
        self.assertIn("Metric", strings)
        self.assertIn("No matching sessions", strings)
        self.assertIn("<pane", sheet)

    def test_category_group_uses_localized_heading_and_empty_label(self) -> None:
        groups = summary_groups()
        groups[0]["key"] = "-"
        groups[0]["label"] = "-"
        content = summary_workbook(
            [
                SummaryWorksheet(
                    name="Categories",
                    group_by="category",
                    matched_count=1,
                    groups=groups,
                )
            ],
            locale="zh-CN",
        )
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            strings = archive.read("xl/sharedStrings.xml").decode("utf-8")
        self.assertIn("分类", strings)
        self.assertIn("<t>-</t>", strings)

    def test_category_named_overall_is_not_localized_as_the_overall_scope(self) -> None:
        groups = summary_groups()
        groups[0]["key"] = "overall"
        groups[0]["label"] = "overall"
        category_content = summary_workbook(
            [
                SummaryWorksheet(
                    name="Categories",
                    group_by="category",
                    matched_count=1,
                    groups=groups,
                )
            ],
            locale="zh-CN",
        )
        with zipfile.ZipFile(io.BytesIO(category_content)) as archive:
            category_strings = archive.read("xl/sharedStrings.xml").decode("utf-8")
        self.assertIn("<t>overall</t>", category_strings)
        self.assertNotIn("<t>全部</t>", category_strings)

        overall_content = summary_workbook(
            [
                SummaryWorksheet(
                    name="Overall",
                    group_by="overall",
                    matched_count=1,
                    groups=groups,
                )
            ],
            locale="zh-CN",
        )
        with zipfile.ZipFile(io.BytesIO(overall_content)) as archive:
            overall_strings = archive.read("xl/sharedStrings.xml").decode("utf-8")
        self.assertIn("<t>全部</t>", overall_strings)


if __name__ == "__main__":
    unittest.main()
