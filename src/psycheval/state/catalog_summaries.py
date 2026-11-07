from __future__ import annotations

import json
import math
import sqlite3
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Iterable, Iterator, Sequence

from psycheval.harbor.measurements import METRICS
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
    provenance_rows = iter(
        connection.execute(
            f"SELECT source_key, json_extract(row_json, '$.metric_provenance') AS provenance FROM cells WHERE {where} ORDER BY source_key",
            parameters,
        )
    )
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
            provenance_row = next(provenance_rows, None)
            if (
                provenance_row is None
                or provenance_row["source_key"] != current["source_key"]
            ):
                raise RuntimeError("summary generation changed during read")
            current["metric_provenance"] = json.loads(
                provenance_row["provenance"] or "{}"
            )
        if record["metric_id"] is not None:
            current["metric_values"][record["metric_id"]] = record["value"]
    if current is not None:
        yield current


@dataclass
class _SummaryGroupValues:
    count: int = 0
    metrics: dict[str, list[float]] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)


def _identity(value):
    """Hashable JSON identity without serializing every metric of every Trial."""
    if isinstance(value, dict):
        return tuple((key, _identity(item)) for key, item in sorted(value.items()))
    if isinstance(value, list):
        return tuple(_identity(item) for item in value)
    return value


class _ProvenanceSummary:
    def __init__(self):
        self.variants = {}
        self.other = {"trials": 0, "available": 0, "missing": 0}
        self.first_basis = self.first_source = None
        self.mixed_basis = self.mixed_sources = False
        self.trials = self.available = 0

    def add(self, provenance, available, budget):
        self.trials += 1
        self.available += available
        provenance = provenance or {
            "source": "unknown",
            "basis_id": "unknown",
            "contract_version": "unknown",
            "method": "unknown",
            "missing_reason": "missing_provenance",
        }
        source = (
            provenance.get("source"),
            _identity(provenance.get("producer")),
        )
        basis = (
            provenance.get("contract_version"),
            provenance.get("basis_id"),
            provenance.get("method"),
        )
        if self.first_basis is None:
            self.first_basis, self.first_source = basis, source
        self.mixed_basis |= basis != self.first_basis
        self.mixed_sources |= source != self.first_source
        key = (
            source,
            basis,
            provenance.get("quality"),
            provenance.get("missing_reason"),
        )
        item = self.variants.get(key)
        if item is None and (len(self.variants) >= 16 or budget[0] < 128):
            item = self.other
        if item is None:
            compact = {
                k: v
                for k, v in provenance.items()
                if k
                in {
                    "source",
                    "producer",
                    "contract_version",
                    "basis_id",
                    "method",
                    "quality",
                    "scope",
                    "sample_unit",
                    "start_boundary",
                    "end_boundary",
                    "retry_policy",
                    "token_basis",
                    "cost_kinds",
                    "missing_reason",
                    "clock",
                }
            }
            size = len(json.dumps(compact, ensure_ascii=False).encode()) + 128
            if len(self.variants) < 16 and budget[0] >= size:
                budget[0] -= size
                item = {**compact, "trials": 0, "available": 0, "missing": 0}
                self.variants[key] = item
            else:
                item = self.other
        item["trials"] += 1
        item["available"] += available
        item["missing"] += not available

    def result(self):
        return {
            "trials": self.trials,
            "available": self.available,
            "missing": self.trials - self.available,
            "mixed_basis": self.mixed_basis,
            "mixed_sources": self.mixed_sources,
            "variants": list(self.variants.values()),
            **(
                {"other": self.other, "details_truncated": True}
                if self.other["trials"]
                else {}
            ),
        }


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
    provenance_budget = [8 * 1024 * 1024 - SUMMARY_GROUP_LIMIT * len(METRICS) * 256]
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
            if metric_key in METRICS:
                values.provenance.setdefault(metric_key, _ProvenanceSummary()).add(
                    (row.get("metric_provenance") or {}).get(metric_key),
                    metric_value is not None,
                    provenance_budget,
                )
    groups = [
        {
            "key": key,
            "label": "-" if key is None else key,
            "count": group_values.count,
            "metrics": [
                {
                    **metric,
                    "provenance": group_values.provenance[metric["key"]].result(),
                }
                if metric["key"] in group_values.provenance
                else metric
                for metric in _saved_view_metric_rows(group_values.metrics, metric_ids)
            ],
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
