"""Count assertions plus text-only, hash-bound visual-reference evidence."""

import argparse
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

from harbor.models.trajectories import Trajectory

from psycheval.harbor.documents import inspect_document
from psycheval.harbor.evidence import EvidenceWriter
from psycheval.harbor.verifier import final_answer_text

REGIONS = ("西侧暂存区", "中央集货区", "东侧月台边")
LABEL = re.compile(
    r"西侧(?:暂存区)?|中央(?:集货区)?|东侧(?:月台边)?|"
    r"总共|一共|共计|总计|合计|总数|总托数|总量|共"
)
NUMBER = re.compile(
    r"(?<![0-9A-Za-z_.])[+\-−]?(?:[0-9]+(?:\.[0-9]+)?|[零〇一二两三四五六七八九十百]+)"
    r"(?![0-9A-Za-z_.])"
)
DIGITS = {char: number for number, char in enumerate("零一二三四五六七八九")}
DIGITS.update({"〇": 0, "两": 2})


def number(text):
    if text[:1].isdigit() or text[:1] in {"+", "-", "−"}:
        value = float(text.replace("−", "-"))
        return int(value) if value.is_integer() and value >= 0 else None
    if text in DIGITS:
        return DIGITS[text]
    if text.count("十") == 1:
        tens, units = text.split("十")
        if (not tens or tens in DIGITS) and (not units or units in DIGITS):
            return DIGITS.get(tens, 1) * 10 + DIGITS.get(units, 0)
    return None


def label_key(text):
    return next((region for region in REGIONS if region.startswith(text[:2])), "total")


def assertions(answer):
    """Collect counts tied to labels, preserving conflicting repeated assertions."""
    answer = unicodedata.normalize("NFKC", answer).translate(
        str.maketrans("", "", "*_`#")
    )

    def excluded_subject(text):
        return bool(re.search(r"待检|空托|图例", text)) and not (
            re.search(r"(?<![不未])(?:可|能)装车", text)
            or re.search(r"(?:排除|扣除|去掉|除去).*(?:之后|后)", text)
        )

    def parenthetical(match):
        subject = re.split(r"[\n。；;，,、]", answer[: match.start()])[-1]
        # A breakdown of excluded objects retains its subject across commas.
        if excluded_subject(subject) or re.search(r"待检|空托|图例", match[1]):
            return " "
        return " " + match[1] + " "

    answer = re.sub(r"\(([^()]*)\)", parenthetical, answer)
    found = {key: [] for key in (*REGIONS, "total")}
    for segment in re.split(r"[\n。；;，,、]", answer):
        if excluded_subject(segment):
            continue
        labels = list(LABEL.finditer(segment))
        if not labels and (
            re.search(r"(?:可|待|能)装车", segment)
            or re.fullmatch(
                r"\s*(?:[0-9]+|[零〇一二两三四五六七八九十]+)\s*托\s*", segment
            )
        ):
            found["total"].extend(
                number(value[0]) for value in NUMBER.finditer(segment)
            )
        for index, match in enumerate(labels):
            right = (
                labels[index + 1].start() if index + 1 < len(labels) else len(segment)
            )
            values = list(NUMBER.finditer(segment[match.end() : right]))
            if not values:
                left = labels[index - 1].end() if index else 0
                values = list(NUMBER.finditer(segment[left : match.start()]))
            if values:
                found[label_key(match[0])].extend(number(value[0]) for value in values)
    # Also accept a horizontal Markdown table instead of prose/vertical rows.
    rows = [
        line.strip().strip("|").split("|")
        for line in answer.splitlines()
        if "|" in line
    ]
    for header, separator, values in zip(rows, rows[1:], rows[2:]):
        if len(header) != len(values) or not all(
            re.fullmatch(r"[\s:-]+", cell) for cell in separator
        ):
            continue
        for heading, value in zip(header, values):
            match, numbers = LABEL.search(heading), list(NUMBER.finditer(value))
            if match and numbers:
                found[label_key(match[0])].extend(number(item[0]) for item in numbers)
    if not found["total"] and re.fullmatch(
        r"\s*(?:[0-9]+|[零〇一二两三四五六七八九十]+)\s*(?:托|托货物)?[。.!！]?\s*",
        answer,
    ):
        found["total"] = [number(NUMBER.search(answer)[0])]
    return found


def evaluate(answer, counts):
    observed = assertions(answer)
    expected_total = sum(counts.values())
    total_ok = bool(observed["total"]) and set(observed["total"]) == {expected_total}
    regions_ok = all(
        observed[key] and set(observed[key]) == {counts[key]} for key in REGIONS
    )
    # Contradictory regional/total assertions cannot independently earn credit.
    if any(observed[key] and set(observed[key]) != {counts[key]} for key in REGIONS):
        total_ok = False
    if observed["total"] and not total_ok:
        regions_ok = False
    return [
        {
            "id": key,
            "passed": bool(passed),
            "evidence": json.dumps(
                {"observed": observed, "expected_ready": counts}, ensure_ascii=False
            ),
        }
        for key, passed in (
            ("correct_total", total_ok),
            ("correct_region_bindings", regions_ok),
        )
    ]


def reference_facts(snapshot, image):
    facts = json.loads(snapshot.content.decode("utf-8"))
    if (
        facts.get("image_filename") != "loading-bay.png"
        or facts.get("image_sha256") != image.sha256
        or facts.get("regions") != list(REGIONS)
        or facts.get("legend_excluded") is not True
    ):
        raise ValueError("Visual reference does not match the retained original image")
    objects, seen = facts.get("objects"), set()
    if not isinstance(objects, list) or not objects:
        raise ValueError("Visual reference objects are unavailable")
    for item in objects:
        if item.get("region") not in REGIONS or item.get("category") not in {
            "ready",
            "empty",
            "quarantine",
        }:
            raise ValueError("Unknown visual reference object category or region")
        box = item.get("bbox")
        if (
            not isinstance(box, list)
            or len(box) != 4
            or not all(type(value) is int for value in box)
            or not 0 <= box[0] < box[2] <= facts["width"]
            or not 0 <= box[1] < box[3] <= facts["height"]
            or tuple(box) in seen
        ):
            raise ValueError("Invalid visual reference object bounds")
        seen.add(tuple(box))
    return facts


def reference_text(facts):
    lines = [
        "# 私有视觉复核基准",
        "构造后查看原图并逐区核对的静态基准；不是OCR结果、Agent作答或Agent看图记录。",
        "当前Judge仅支持文本，未直接接收图像；原PNG留存在同一证据manifest供人工复核。",
        f"原图：{facts['image_filename']}；SHA-256：{facts['image_sha256']}。",
        "计数单位为整托货物，不能把一个托上的多个纸箱拆开计数。",
        "三个分区各自下方的红色斜纹框是封存待检区；现场裸空托盘无纸箱；底部白框图例不属于现场。",
        "",
        "| 分区 | 可装车整托 | 待检区内整托 | 空托盘 |",
        "| --- | --- | --- | --- |",
    ]
    for region in REGIONS:
        counts = Counter(
            item["category"] for item in facts["objects"] if item["region"] == region
        )
        lines.append(
            f"| {region} | {counts['ready']} | {counts['quarantine']} | {counts['empty']} |"
        )
    lines.extend(
        [
            "",
            "逐个现场实物的像素包围盒（左、上、右、下；图例不在清单中）：",
            json.dumps(facts["objects"], ensure_ascii=False, indent=2),
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    paths = json.loads(args.context.read_text(encoding="utf-8"))["paths"]
    if not paths.get("inputs"):
        raise RuntimeError(
            "This Task requires ordinary Native Host retained initial inputs"
        )
    with EvidenceWriter(paths["verifier_logs"]) as writer:
        image = writer.capture("input_image", Path(paths["inputs"]) / "loading-bay.png")
        static = inspect_document(image)
        writer.add_text(
            "image_static_facts", static.to_markdown(), source_id="input_image"
        )
        private = writer.capture(
            "counting_reference", Path(paths["tests"]) / "gt/visual-reference.json"
        )
        facts = reference_facts(private, image)
        if (static.width, static.height) != (facts["width"], facts["height"]):
            raise ValueError(
                "Visual reference dimensions do not match the retained image"
            )
        counts = {
            region: sum(
                item["category"] == "ready" and item["region"] == region
                for item in facts["objects"]
            )
            for region in REGIONS
        }
        writer.add_text(
            "visual_reference", reference_text(facts), source_id="input_image"
        )
        try:
            trajectory = writer.capture(
                "retained_trajectory",
                Path(paths["agent_logs"]) / "trajectory.json",
                max_bytes=128 * 1024 * 1024,
            )
        except FileNotFoundError:
            answer = ""
            writer.unavailable("retained_trajectory", "No retained trajectory")
            writer.add_text("final_answer", answer)
        else:
            answer = final_answer_text(
                Trajectory.model_validate_json(trajectory.content)
            )
            writer.add_text("final_answer", answer, source_id="retained_trajectory")
        checks = evaluate(answer, counts)
    args.output.write_text(
        json.dumps({"checks": checks}, ensure_ascii=False), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
