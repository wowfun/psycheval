from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Iterable, Iterator, Sequence

from psycheval.metric_contract import SAVED_VIEW_METRIC_IDS, finite_number
from psycheval.report.metrics import tool_success_rate

if TYPE_CHECKING:
    from psycheval.state.catalog import CatalogQuery

SUMMARY_GROUP_LIMIT = 1_000


class CatalogSummaryCapacityError(ValueError):
    pass


def summary_query_scope(query: CatalogQuery) -> tuple[Any, ...]:
    return (
        query.state,
        query.search,
        tuple(sorted(query.categories)),
        tuple(sorted(query.tags)),
        tuple(sorted(query.agents)),
        tuple(sorted(query.models)),
        tuple(sorted(query.results)),
        tuple(sorted(query.tasks)),
        tuple(sorted(query.jobs)),
        tuple(sorted(query.providers)),
        tuple(sorted(query.datasets)),
        query.include_unreadable,
    )


def summary_rows(
    connection: sqlite3.Connection,
    where: str,
    parameters: Sequence[Any],
) -> Iterator[dict[str, Any]]:
    records = connection.execute(
        f"""SELECT cells.source_key, category AS source_category, agent AS agent_name,
                   model, task AS task_name, job AS job_name, provider AS model_provider,
                   metric_id, value
            FROM cells LEFT JOIN metric_values USING(source_key)
            WHERE {where} ORDER BY cells.source_key""",
        parameters,
    )
    current = None
    for record in records:
        if current is None or current["source_key"] != record["source_key"]:
            if current is not None:
                yield current
            current = dict(record)
            current["metric_values"] = {}
        if record["metric_id"] is not None:
            current["metric_values"][record["metric_id"]] = record["value"]
    if current is not None:
        yield current


@dataclass
class _SummaryGroupValues:
    count: int = 0
    metrics: dict[str, list[float]] = field(default_factory=dict)


def summarize_rows(
    name: str,
    group_by: str,
    rows: Iterable[dict[str, Any]],
    metric_ids: Sequence[str] = SAVED_VIEW_METRIC_IDS,
) -> dict[str, Any]:
    grouped: dict[str | None, _SummaryGroupValues] = {}
    if group_by == "overall":
        grouped["overall"] = _SummaryGroupValues()
    matched_count = 0
    for row in rows:
        matched_count += 1
        key = _saved_view_group_key(row, group_by)
        values = grouped.get(key)
        if values is None:
            if len(grouped) >= SUMMARY_GROUP_LIMIT:
                raise CatalogSummaryCapacityError(
                    f"grouped summaries support at most {SUMMARY_GROUP_LIMIT} groups; "
                    "refine the query or use an overall summary"
                )
            values = _SummaryGroupValues()
            grouped[key] = values
        values.count += 1
        for metric_key in metric_ids:
            metric_value = _saved_view_metric_value(row, metric_key)
            if metric_value is not None:
                values.metrics.setdefault(metric_key, []).append(metric_value)
    groups = [
        {
            "key": key,
            "label": "-" if key is None else key,
            "count": group_values.count,
            "metrics": _saved_view_metric_rows(group_values.metrics, metric_ids),
        }
        for key, group_values in sorted(
            grouped.items(),
            key=lambda item: (
                ("-" if item[0] is None else item[0]).casefold(),
                item[0] is not None,
            ),
        )
    ]
    return {
        "name": name,
        "group_by": group_by,
        "matched_count": matched_count,
        "groups": groups,
    }


def _saved_view_group_key(row: dict[str, Any], group_by: str) -> str | None:
    if group_by == "overall":
        return "overall"
    if group_by == "model":
        return str(row.get("model") or "-")
    if group_by == "category":
        category = str(row.get("source_category") or "").strip()
        return category or None
    if group_by == "task":
        return str(row.get("task_name") or "-")
    if group_by == "job":
        return str(row.get("job_name") or "-")
    if group_by == "provider":
        return str(row.get("model_provider") or "-")
    return str(row.get("agent_name") or row.get("adapter") or "-")


def _saved_view_metric_rows(
    metric_values: dict[str, list[float]],
    metric_ids: Sequence[str],
) -> list[dict[str, Any]]:
    metrics: list[dict[str, Any]] = []
    for key in metric_ids:
        values = metric_values.get(key, [])
        metrics.append(
            {
                "key": key,
                "count": len(values),
                "mean": math.fsum(value / len(values) for value in values)
                if values
                else None,
                "distribution": _saved_view_distribution(values),
            }
        )
    return metrics


def _saved_view_metric_value(row: dict[str, Any], key: str) -> float | None:
    if "metric_values" in row:
        return finite_number(row["metric_values"].get(key))
    if key != "tool_success_rate":
        return finite_number(row.get(key))
    return tool_success_rate(row.get("total_tool_calls"), row.get("total_tool_errors"))


def _saved_view_distribution(values: list[float]) -> dict[str, float] | None:
    if not values:
        return None
    ordered = sorted(values)
    return {
        "min": ordered[0],
        "q1": _saved_view_percentile(ordered, 25),
        "p50": _saved_view_percentile(ordered, 50),
        "q3": _saved_view_percentile(ordered, 75),
        "p95": _saved_view_percentile(ordered, 95),
        "max": ordered[-1],
    }


def _saved_view_percentile(ordered: list[float], percentile: int) -> float:
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * (percentile / 100)
    lower = int(position)
    upper = min(len(ordered) - 1, lower + 1)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction
