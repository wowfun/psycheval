from __future__ import annotations

import io
import unittest
import zipfile

from peval_py.serve.errors import HttpError
from peval_py.serve.payloads import summary_export_payload
from peval_py.serve.summary_xlsx import SummaryWorksheet, summary_workbook


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
                metric("tokens", "number", 0),
                metric("turns", "number", None),
                metric("model_duration_ms", "duration", 500),
                metric("total_tool_calls", "number", 2),
                metric("tool_error_rate", "percent", 0),
            ],
        }
    ]


class SummaryXlsxTests(unittest.TestCase):
    def test_payload_validation_is_strict_and_ordered_deduplicated(self) -> None:
        request = summary_export_payload(
            {
                "scope": "leaderboard",
                "source_keys": ["b", "a", "b"],
                "group_by": "model",
                "statistic": "p95",
            }
        )
        self.assertEqual(request.source_keys, ("b", "a"))
        self.assertEqual(request.group_by, "model")
        self.assertEqual(request.statistic, "p95")
        views = summary_export_payload(
            {"scope": "saved_views", "views": ["B", "A", "B"]}
        )
        self.assertEqual(views.views, ("B", "A"))
        for invalid in (
            {"scope": "leaderboard", "source_keys": [], "group_by": "agent", "statistic": "mean"},
            {"scope": "leaderboard", "source_keys": ["a"], "group_by": "agent", "statistic": "median"},
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
            chart = archive.read("xl/charts/chart1.xml").decode("utf-8")
        self.assertIn("xl/charts/chart12.xml", names)
        self.assertIn("xl/drawings/drawing1.xml", names)
        self.assertIn('name="Unsafe_View"', workbook)
        self.assertIn('name="unsafe_view (2)"', workbook)
        self.assertIn("=1+1", shared_strings)
        self.assertIn("https://example.invalid", shared_strings)
        self.assertIn("tail", shared_strings)
        self.assertIn("Long Notes (cont.)", shared_strings)
        self.assertNotIn("<f>", first_sheet)
        self.assertIn("1.157407407407407E-05", first_sheet)
        self.assertRegex(first_sheet, r"<v>0</v>")
        self.assertIn("p95", chart.lower())
        self.assertIn("$I$", chart)

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


if __name__ == "__main__":
    unittest.main()
