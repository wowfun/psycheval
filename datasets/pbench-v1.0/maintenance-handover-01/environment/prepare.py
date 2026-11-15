"""Resolve one Shanghai handover reference and freeze the associated records."""

import csv
import hashlib
import io
import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TIMEZONE = ZoneInfo("Asia/Shanghai")
FIELDS = (
    "导出时间",
    "记录ID",
    "工单号",
    "记录类型",
    "记录时间",
    "发起人",
    "涉及人员",
    "主题",
    "记录正文",
)


def build_materials(reference):
    if reference.tzinfo is None:
        raise ValueError("Reference must be timezone-aware")
    reference = reference.astimezone(TIMEZONE).replace(microsecond=0)
    monday = reference.date() - timedelta(days=reference.weekday())

    def deadline(day, clock):
        return f"{monday + timedelta(days=day):%Y-%m-%d} {clock}"

    def event(identity, order, kind, hours_ago, author, participants, title, body):
        return dict(
            zip(
                FIELDS,
                (
                    reference.isoformat(),
                    identity,
                    order,
                    kind,
                    (reference - timedelta(hours=hours_ago)).isoformat(
                        timespec="minutes"
                    ),
                    author,
                    participants,
                    title,
                    body,
                ),
            )
        )

    rows = [
        event(
            "JL-8032",
            "WX-6653",
            "工单",
            25,
            "设备主管唐宁",
            "沈乐；郑川（知会）",
            "高架灯检查安排",
            f"高架灯区照度检查由沈乐负责，{deadline(4, '16:00')} 前上传照度记录。郑川只知会，不承担检查或提交动作。",
        ),
        event(
            "JL-7318",
            "WX-4726",
            "工单",
            216,
            "设备主管唐宁",
            "郑川",
            "P-07 振动复测安排",
            f"P-07 冷却泵检修后，请郑川完成振动复测并上传趋势图，原计划 {deadline(2, '16:00')} 前交回。当前未结。",
        ),
        event(
            "JL-7774",
            "WX-8421",
            "验收",
            6,
            "验收员吴彤",
            "郑川；沈乐",
            "A-02 润滑记录验收通过",
            "郑川提交的A-02空压机润滑记录已核验完整，签收完成，本交付项关闭；不需要重新提交。",
        ),
        event(
            "JL-7932",
            "WX-4726",
            "交接",
            96,
            "仓管陈佳",
            "郑川",
            "P-07 更换轴承领用核销",
            f"同一检修工单还欠更换轴承的领用核销。郑川需核对实际领用数量并回填领用台账，截止 {deadline(3, '12:00')}；这与振动复测是两个独立交付项，目前未结。",
        ),
        event(
            "JL-7584",
            "WX-6184",
            "交接",
            4,
            "组长顾航",
            "郑川；顾航",
            "消防水泵曲线复核移交",
            f"消防水泵联动试验的压力曲线复核改由郑川负责，不再由顾航负责。郑川需复核压力曲线并签署复核意见，截止更新为 {deadline(6, '22:00')}；未结。",
        ),
        event(
            "JL-7268",
            "WX-8421",
            "工单",
            180,
            "设备主管唐宁",
            "郑川",
            "A-02 润滑记录补交",
            f"请郑川于 {deadline(4, '14:00')} 前补齐A-02空压机润滑记录，等待验收。",
        ),
        event(
            "JL-7163",
            "WX-2907",
            "交接",
            78,
            "冷链主管许晏",
            "郑川",
            "冷库门封条验收",
            f"冷库门封条已更换，请郑川确认门封条验收并回传签收单，截止 {deadline(2, '16:00')}。目前尚未收到签收单，本项未结。",
        ),
        event(
            "JL-7984",
            "WX-1174",
            "看板同步",
            2,
            "班组助理姜芮",
            "维护组全员",
            "雨水回收泵巡检例会纪要",
            "本周巡检例会纪要已发布，供维护组了解运行情况。本条仅知会，没有新增待办，不需要回执。",
        ),
        event(
            "JL-7241",
            "WX-4726",
            "交接",
            12,
            "设备主管唐宁",
            "郑川",
            "P-07 振动复测改期",
            f"P-07振动复测仍由郑川完成，交付物仍是复测记录和趋势图；截止改为 {deadline(4, '17:30')}，替代原计划，不新增第二次复测。目前未结。",
        ),
        event(
            "JL-7516",
            "WX-3702",
            "工单",
            104,
            "设备主管唐宁",
            "郑川",
            "B-03 皮带更换",
            f"原安排郑川在 {deadline(5, '11:00')} 前完成B-03风机皮带更换并提交更换记录。",
        ),
        event(
            "JL-8286",
            "WX-6184",
            "工单",
            170,
            "组长顾航",
            "顾航；郑川（知会）",
            "消防水泵压力曲线复核",
            f"消防水泵联动试验压力曲线原由顾航复核，原截止 {deadline(5, '08:00')}；郑川先知会。",
        ),
        event(
            "JL-7405",
            "WX-3851",
            "工单",
            288,
            "电气主管杜衡",
            "郑川",
            "D-03 配电柜红外测温",
            f"郑川需完成D-03配电柜红外测温并提交异常点照片，截止 {deadline(1, '18:00')}。未见完成或取消记录，继续跟进。",
        ),
        event(
            "JL-7539",
            "WX-4815",
            "工单",
            18,
            "设备主管唐宁",
            "郑川",
            "下周期过滤器采样",
            f"郑川负责过滤器余量采样，截止 {deadline(8, '10:00')}。这是下一个维护周期任务，目前未结。",
        ),
        event(
            "JL-7821",
            "WX-3702",
            "交接",
            8,
            "设备主管唐宁",
            "郑川",
            "B-03 更换计划取消",
            "B-03风机皮带更换计划取消，设备改为整机更换。本次皮带更换及其记录提交均不再执行，也没有另行交给郑川的后续动作。",
        ),
        event(
            "JL-7439",
            "WX-4726",
            "看板同步",
            1,
            "班组助理姜芮",
            "维护组全员",
            "P-07 排期看板同步",
            "看板同步P-07复测事项，实际安排依JL-7241执行；仅同步，不产生新交付项。领用核销仍是独立事项。",
        ),
        event(
            "JL-7652",
            "WX-3728",
            "交接",
            240,
            "设备主管唐宁",
            "郑川",
            "旧周期仪表台账",
            f"郑川的仪表台账更新仍未结，原截止 {deadline(-3, '16:00')}。没有本周改期或新增任务。",
        ),
    ]
    todos = [
        {
            "id": "vibration",
            "order": "WX-4726",
            "deadline": deadline(4, "17:30"),
            "groups": [
                ["振动"],
                ["复测", "复查", "测试", "检测", "测量"],
                ["趋势图", "趋势曲线", "曲线图"],
            ],
            "sources": ["JL-7318", "JL-7241", "JL-7439"],
            "deadline_source": "JL-7241",
        },
        {
            "id": "bearing",
            "order": "WX-4726",
            "deadline": deadline(3, "12:00"),
            "groups": [["轴承"], ["领用", "领料", "出库"], ["核销", "台账", "数量"]],
            "sources": ["JL-7932"],
            "deadline_source": "JL-7932",
        },
        {
            "id": "infrared",
            "order": "WX-3851",
            "deadline": deadline(1, "18:00"),
            "groups": [
                ["红外", "测温", "温度测量"],
                ["异常点", "异常"],
                ["照片", "图像", "图片"],
            ],
            "sources": ["JL-7405"],
            "deadline_source": "JL-7405",
        },
        {
            "id": "pressure",
            "order": "WX-6184",
            "deadline": deadline(6, "22:00"),
            "groups": [
                ["压力"],
                ["曲线"],
                ["复核", "审核", "核验", "审查", "校核", "审阅", "核查"],
                ["意见", "签署", "签字", "签名"],
            ],
            "sources": ["JL-8286", "JL-7584"],
            "deadline_source": "JL-7584",
        },
        {
            "id": "door_seal",
            "order": "WX-2907",
            "deadline": deadline(2, "16:00"),
            "groups": [
                ["门封", "封条", "密封条"],
                ["验收", "核验"],
                ["签收单", "签收", "回执"],
            ],
            "sources": ["JL-7163"],
            "deadline_source": "JL-7163",
        },
    ]
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    content = buffer.getvalue().encode("utf-8")
    state = {
        "version": 1,
        "reference_time": reference.isoformat(),
        "week_start": monday.isoformat(),
        "week_end_exclusive": (monday + timedelta(days=7)).isoformat(),
        "source_sha256": hashlib.sha256(content).hexdigest(),
        "todos": todos,
    }
    return content, state


def prepare(workdir: str, state_dir: str) -> list[str]:
    content, state = build_materials(datetime.now(TIMEZONE))
    (Path(workdir) / "handover.csv").write_bytes(content)
    (Path(state_dir) / "reference.json").write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return ["handover.csv"]
