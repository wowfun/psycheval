"""Primary-data pairing and source-grounded static HTML report verification."""

import asyncio
import copy
import json
import runpy
import shutil
from html import escape
from pathlib import Path

import pytest

from psycheval.harbor.documents import inspect_document
from psycheval.harbor.evidence import SourceSnapshot
from psycheval.harbor.runtime_config import (
    EffectiveRuntimeConfig,
    RuntimePaths,
    VerifierInvocation,
)
from psycheval.harbor.tasks import load_harbor_task
from psycheval.harbor.verifier import (
    JudgeSettings,
    build_scoring_plan,
    load_judge_config,
    run_verifier,
)
from tests.fixtures.judge_server import judge_server

TASK = (
    Path(__file__).resolve().parents[2]
    / "datasets/pbench-v1.0/museum-attendance-review-01"
)
GRADER = runpy.run_path(str(TASK / "tests/test_outputs.py"))
LABELS = {
    "attendance_visits": "总到馆人次（人次）",
    "open_days": "实际开放日数（天）",
    "open_hours": "实际开放小时（小时）",
    "online_reserved_orders": "线上预约发出量（份）",
    "online_checkedin_visits": "线上核销到馆人次（人次）",
    "night_checkedin_visits": "夜场到馆人次（人次）",
    "response_count": "问卷答卷数（份）",
    "crowded_responses": "选择拥挤人数（人）",
}


def reference():
    data = TASK / "environment/data"
    return GRADER["reference"](
        {
            "stats_2025": (data / "2025-q1-statistics.csv").read_text(encoding="utf-8"),
            "stats_2026": (data / "2026-q1-statistics.csv").read_text(encoding="utf-8"),
            "survey": (data / "survey-results.csv").read_text(encoding="utf-8"),
        }
    )


def report_html(values, *, orientation="wide", units=False):
    def formatted(field, year):
        value = values[year][field]
        return f"{value / 10000:g}万" if units and value >= 10000 else f"{value:,}"

    if orientation == "wide":
        rows = [["指标", "2025年第一季度", "2026Q1"]] + [
            [label, formatted(field, "2025"), formatted(field, "2026")]
            for field, label in LABELS.items()
        ]
    else:
        rows = [["季度", *LABELS.values()]] + [
            [year + "Q1", *(formatted(field, year) for field in LABELS)]
            for year in ("2025", "2026")
        ]
    table = (
        "<table>"
        + "".join(
            "<tr>" + "".join("<td>" + escape(cell) + "</td>" for cell in row) + "</tr>"
            for row in rows
        )
        + "</table>"
    )
    return (
        """<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>栖潮馆季度运营核查</title><body>
<h1>栖潮城市博物馆季度运营复盘</h1><h2>原始数据</h2>"""
        + table
        + """
<p>以上按正式月表汇总。来源：<a href="../2025-q1-statistics.csv">2025正式月表第2至4行</a>、<a href="../2026-q1-statistics.csv">2026正式月表第2至4行</a>、<a href="../survey-results.csv">问卷汇总</a>；口径见TJ-2026-0415、YY-2026-0328及DY-2026-0416。</p>
<h2>宣传断言核查</h2><p>正式到馆总量增长25%，而非旧快报对应的30%；人次不是去重人数。日均1333.33至1388.89人次，增加约4.17%；每开放小时190.48至173.61人次，下降约8.85%，并未增加30%。</p>
<p>线上核销到馆占比由48000/80000=60%变为64000/100000=64%，九成把9万发出预约和10万到馆人次混作分子分母。夜场4000人次已在10万内，只有总增量2万的20%这一算术关系，不能当因果贡献，更不能说唯一原因。</p>
<h2>解释边界及改写建议</h2><p>拥挤答卷比例由126/420=30%变为140/500=28%，下降2个百分点。自愿二维码样本不能代表全体观众；平均入馆流量不等于高峰同时在馆密度，缺少分时到离馆、停留和面积资料，不能认定实际更不拥挤。</p>
<p>延长开放、夜场、主题展和渠道调整同期发生，没有反事实，不宜把预算全部转夜场或各时段统一减名额。宣传可改为“到馆人次增长25%，线上实际核销占64%，试行夜场拓展服务时段”；先补充分时流量与停留记录、改进反馈抽样，再讨论高峰预约配置。</p></body></html>"""
    )


def inspect(markup):
    pytest.importorskip("html5lib")
    pytest.importorskip("tinycss2")
    return inspect_document(SourceSnapshot(Path("review.html"), markup.encode("utf-8")))


def test_retained_raw_data_supports_different_denominators_and_cannot_double_count_night():
    expected, facts = reference()
    assert expected["2025"]["attendance_visits"] == 80000
    assert expected["2026"]["attendance_visits"] == 100000
    assert expected["2025"]["open_hours"] == 420
    assert expected["2026"]["open_hours"] == 576
    assert facts["attendance_growth_percent"] == 25
    assert facts["daily_flow_change_percent"] == pytest.approx(4.1666667)
    assert facts["hourly_flow_change_percent"] == pytest.approx(-8.8541667)
    assert facts["checkedin_online_share_percent"] == {"2025": 60, "2026": 64}
    assert facts["crowded_among_respondents_percent"] == {"2025": 30, "2026": 28}
    assert facts["night_entries_divided_by_total_increment_percent_not_causal"] == 20


@pytest.mark.parametrize(
    "orientation, units",
    [("wide", False), ("wide", True), ("tall", False), ("tall", True)],
)
def test_comparison_accepts_both_table_orientations_and_natural_numeric_units(
    orientation, units
):
    expected, _ = reference()
    report = inspect(report_html(expected, orientation=orientation, units=units))
    assert GRADER["assess"](report, expected)[0]


@pytest.mark.parametrize(
    "change",
    [
        "old_flash",
        "swapped_periods",
        "reservation_is_attendance",
        "night_added_again",
        "survey_denominator",
        "missing_metric",
    ],
)
def test_wrong_primary_values_or_missing_required_data_are_not_rescued_by_keywords(
    change,
):
    expected, _ = reference()
    actual = copy.deepcopy(expected)
    if change == "old_flash":
        actual["2026"]["attendance_visits"] = 104000
    elif change == "swapped_periods":
        actual = {"2025": actual["2026"], "2026": actual["2025"]}
    elif change == "reservation_is_attendance":
        actual["2026"]["online_checkedin_visits"] = 90000
    elif change == "night_added_again":
        actual["2026"]["attendance_visits"] += 4000
    elif change == "survey_denominator":
        actual["2026"]["response_count"] = 100000
    markup = report_html(actual)
    if change == "missing_metric":
        markup = markup.replace("线上核销到馆人次（人次）", "未提供该项")
    assert not GRADER["assess"](inspect(markup), expected)[0]


@pytest.mark.parametrize(
    "kind", ["blank", "keywords", "script_only", "unpaired_numbers"]
)
def test_no_credit_for_blank_keyword_or_script_payloads_and_unbound_number_stuffing(
    kind,
):
    expected, _ = reference()
    full = report_html(expected)
    markup = {
        "blank": "<!doctype html><meta charset=utf-8>",
        "keywords": "<!doctype html><meta charset=utf-8><h1>增长 拥挤 线上 夜场 数据 分析</h1>",
        "script_only": "<!doctype html><meta charset=utf-8><script type='application/json'>"
        + full
        + "</script>",
        "unpaired_numbers": "<!doctype html><meta charset=utf-8><p>"
        + " ".join(str(value) for year in expected.values() for value in year.values())
        + "</p>",
    }[kind]
    assert not GRADER["assess"](inspect(markup), expected)[0]


@pytest.mark.parametrize("context", ["caption", "heading"])
def test_q1_table_context_supports_year_only_headers_and_natural_crowding_label(
    context,
):
    expected, _ = reference()
    markup = (
        report_html(expected)
        .replace("2025年第一季度", "2025年")
        .replace("2026Q1", "2026年")
        .replace("选择拥挤人数（人）", "认为拥挤（人）")
    )
    if context == "caption":
        markup = markup.replace(
            "<table>", "<table><caption>第一季度原始数据对照</caption>"
        )
    else:
        markup = markup.replace("<h2>原始数据</h2>", "<h2>第一季度原始数据</h2>")
    assert GRADER["assess"](inspect(markup), expected)[0]


@pytest.mark.parametrize("period", ["第二季度", "全年", "未说明统计期"])
def test_q1_cannot_be_inferred_from_year_only_headers_without_applicable_q1_scope(
    period,
):
    expected, _ = reference()
    markup = (
        report_html(expected)
        .replace("2025年第一季度", "2025年")
        .replace("2026Q1", "2026年")
        .replace("<table>", f"<table><caption>{period}原始数据对照</caption>")
    )
    assert not GRADER["assess"](inspect(markup), expected)[0]


def test_percent_unit_cannot_masquerade_as_a_required_raw_count():
    expected, _ = reference()
    markup = report_html(expected).replace("<td>100,000</td>", "<td>100,000%</td>")
    assert not GRADER["assess"](inspect(markup), expected)[0]


def test_heading_in_an_unrelated_closed_section_does_not_supply_table_period():
    expected, _ = reference()
    markup = (
        report_html(expected)
        .replace("2025年第一季度", "2025年")
        .replace("2026Q1", "2026年")
    )
    markup = markup.replace(
        "<h2>原始数据</h2>",
        "<section><h2>第一季度历史摘要</h2><p>此节结束。</p></section><section><h2>另一统计表</h2>",
    )
    markup = markup.replace("</table>", "</table></section>")
    assert not GRADER["assess"](inspect(markup), expected)[0]


@pytest.mark.parametrize("label", ["拥挤问卷答卷数", "有效答卷数"])
def test_survey_total_label_does_not_become_the_crowded_subset(label):
    expected, _ = reference()
    markup = report_html(expected).replace("问卷答卷数（份）", label + "（份）")
    assert GRADER["assess"](inspect(markup), expected)[0]


def test_correct_supplemental_quantities_and_derived_table_do_not_conflict_with_raw_totals():
    expected, _ = reference()
    markup = (
        report_html(expected)
        .replace(
            "</table>",
            "<tr><td>现场核销到馆人次</td><td>32000</td><td>36000</td></tr>"
            "<tr><td>夜场开放小时</td><td>0</td><td>16</td></tr></table>",
            1,
        )
        .replace(
            "</body>",
            "<table><tr><td>指标</td><td>算式</td><td>2025 Q1</td><td>2026 Q1</td></tr>"
            "<tr><td>线上渠道占实际到馆比</td><td>线上核销到馆人次 ÷ 总到馆人次</td><td>60%</td><td>64%</td></tr>"
            "<tr><td>夜场人次占本季总量比</td><td>夜场到馆人次 ÷ 总到馆人次</td><td>0%</td><td>4%</td></tr></table></body>",
        )
    )
    assert GRADER["assess"](inspect(markup), expected)[0]


def test_source_prose_and_data_rows_are_not_reinterpreted_as_table_headers():
    expected, _ = reference()
    markup = report_html(expected).replace(
        "<body>",
        "<body><h1>第一季度复核</h1><table><tr><td>事项</td><td>约定内容</td><td>来源</td></tr>"
        "<tr><td>当前版本</td><td>2026年一季度正式总量；对照2025-q1-statistics.csv</td><td>TJ-2026-0415</td></tr>"
        "<tr><td>开放时长</td><td>含延长和夜场</td><td>YY-2026-0328</td></tr></table>",
    )
    assert GRADER["assess"](inspect(markup), expected)[0]


@pytest.mark.parametrize(
    "text",
    ["2025-q1-statistics.csv", "TJ-2026-0415", "2025-01", "2026-03", "来源2025Q1月表"],
)
def test_period_labels_exclude_filenames_notice_ids_and_statistical_months(text):
    assert GRADER["quarter"](text, allow_year=True) is None


def test_long_metric_period_value_table_is_a_valid_comparison():
    expected, _ = reference()
    rows = [
        "<tr><td>指标</td><td>时期</td><td>单位</td><td>数值</td><td>来源</td></tr>"
    ]
    for field, label in LABELS.items():
        for year in ("2025", "2026"):
            rows.append(
                f"<tr><td>{label}</td><td>{year}Q1（1—3月）</td><td>原始数量</td><td>{expected[year][field]}</td><td>{year}-q1-statistics.csv</td></tr>"
            )
    markup = '<!doctype html><meta charset="utf-8"><table>' + "".join(rows) + "</table>"
    assert GRADER["assess"](inspect(markup), expected)[0]


def test_monthly_rows_do_not_overwrite_explicit_quarter_totals():
    expected, _ = reference()
    monthly = (
        "<table><tr><td>时期</td><td>到馆人次</td><td>开放日</td><td>开放小时</td></tr>"
    )
    for year, total in expected.items():
        monthly += f"<tr><td>{year}Q1 合计</td><td>{total['attendance_visits']}</td><td>{total['open_days']}</td><td>{total['open_hours']}</td></tr>"
        monthly += f"<tr><td>{year}-03</td><td>31000</td><td>22</td><td>154</td></tr>"
    markup = report_html(expected).replace("</body>", monthly + "</table></body>")
    assert GRADER["assess"](inspect(markup), expected)[0]


def test_actual_conflicting_raw_quarter_data_is_still_rejected():
    expected, _ = reference()
    contradictory = "<table><tr><td>指标</td><td>2025Q1</td><td>2026Q1</td></tr><tr><td>总到馆人次</td><td>80000</td><td>104000</td></tr></table>"
    assert not GRADER["assess"](
        inspect(report_html(expected).replace("</body>", contradictory + "</body>")),
        expected,
    )[0]


def test_csv_links_cannot_substitute_for_period_headers():
    expected, _ = reference()
    markup = (
        report_html(expected)
        .replace("2025年第一季度", "2025-q1-statistics.csv")
        .replace("2026Q1", "2026-q1-statistics.csv")
    )
    assert not GRADER["assess"](inspect(markup), expected)[0]


def test_public_verifier_binds_judge_to_initial_primary_slices_and_static_html(
    tmp_path,
):
    loaded = load_harbor_task(TASK, read_bytes=Path.read_bytes)
    assert loaded.config.agent.timeout_sec == 900
    assert build_scoring_plan(
        json.loads((TASK / "tests/grader.json").read_text())
    ).custom_ids == ("verified_comparison_data",)
    assert len(load_judge_config(TASK / "tests/judge.yaml").rubrics) == 3
    roots = {
        name: tmp_path / name
        for name in ("workdir", "inputs", "agent_logs", "verifier_logs", "artifacts")
    }
    for path in roots.values():
        path.mkdir()
    shutil.copytree(TASK / "environment/data", roots["inputs"], dirs_exist_ok=True)
    (roots["workdir"] / "2026-q1-statistics.csv").write_text(
        "Agent replaced this source copy", encoding="utf-8"
    )
    output = roots["workdir"] / "output"
    output.mkdir()
    (output / "committee-review.htm").write_text(
        report_html(reference()[0]), encoding="utf-8"
    )
    runtime = EffectiveRuntimeConfig(
        paths=RuntimePaths(
            tests=str(TASK / "tests"), **{key: str(path) for key, path in roots.items()}
        ),
        verifier=VerifierInvocation(
            (TASK / "instruction.md").read_text(encoding="utf-8")
        ),
    )
    with judge_server() as server:
        result = asyncio.run(
            run_verifier(
                TASK / "tests/grader.json",
                runtime=runtime,
                judge_settings=JudgeSettings(True, server["url"], "local-fixture"),
            )
        )
        assert len(server["requests"]) == 3
        for request in server["requests"]:
            prompt = request["messages"][-1]["content"]
            assert "2026-q1-statistics.csv; line numbers below are 1-based" in prompt
            assert "L2: 2026-01,32000" in prompt and "TJ-2026-0415" in prompt
            assert (
                "night_entries_divided_by_total_increment_percent_not_causal" in prompt
            )
            assert "Table node " in prompt and "cell node " in prompt
            assert "Agent replaced this source copy" not in prompt
            if "ID: substantive_claim_audit" in prompt:
                assert "所述必要条件不能导出相应结果" in prompt
            if "ID: analytical_limits" in prompt:
                assert "后文泛称" in prompt and "因果上界" in prompt
    assert result["reward"] == 1 and result["metadata"]["score_merge"]["applied"]
    manifest = json.loads(
        (roots["verifier_logs"] / "artifact_manifest.json").read_text(encoding="utf-8")
    )["artifacts"]
    by_id = {item["id"]: item for item in manifest}
    for identity in ("stats_2025", "stats_2026", "survey", "notices", "draft"):
        assert by_id[identity + "_text"]["source_artifact_id"] == identity
        assert by_id[identity]["source_path"].startswith(str(roots["inputs"]))
    assert by_id["report_text"]["source_artifact_id"] == "report_html"
