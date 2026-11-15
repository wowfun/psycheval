"""Resolve one Shanghai archive reference and retain the prepared source facts."""

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

SHANGHAI = ZoneInfo("Asia/Shanghai")


def build_materials(reference):
    if reference.tzinfo is None or reference.utcoffset() is None:
        raise ValueError("The archive reference must be timezone-aware")
    cutoff = reference.astimezone(SHANGHAI).replace(
        hour=15, minute=0, second=0, microsecond=0
    )
    day = cutoff.date()
    yesterday, tomorrow = day - timedelta(days=1), day + timedelta(days=1)

    def stamp(offset, clock):
        return f"{day + timedelta(days=offset):%Y-%m-%d}T{clock}:00+08:00"

    def record(identity, publisher, offset, clock, title, body):
        return (
            f"## {identity}\n\n发布方：{publisher}\n\n"
            f"发布时间：{stamp(offset, clock)}\n\n标题：{title}\n\n正文：{body}\n"
        )

    records = [
        record(
            "B-5904",
            "入驻企业服务群转发",
            0,
            "12:05",
            "转发北门施工提醒",
            f"转发园区道路管理站 {yesterday:%Y-%m-%d} 的通知：北门车道今日封闭至18:00，车辆走东门。此条仅转发原文，没有补充现场信息。",
        ),
        record(
            "B-3915",
            "园区供水运行室",
            0,
            "13:30",
            "创研楼B座夜间供水检修",
            f"创研楼B座2至8层生活用水将在 {day:%Y-%m-%d} 22:00 至 {tomorrow:%Y-%m-%d} 02:00 暂停，预计02:00恢复。今晚有用水安排的单位请提前备水或避开该时段；A座及消防供水不受影响。",
        ),
        record(
            "B-8301",
            "物业服务台",
            -1,
            "16:20",
            "东区失物认领结束",
            "昨日发布的门禁卡遗失事项已由本人认领并关闭；无未完成办理事项。",
        ),
        record(
            "B-6708",
            "园区道路管理站",
            -6,
            "10:10",
            "南停车场围挡安排",
            f"南停车场局部围挡自 {day - timedelta(days=6):%Y-%m-%d} 开始，持续至 {tomorrow:%Y-%m-%d} 晚间，车辆沿现场标线通行。本条为原始安排，参考日没有新增进展或变更通知。",
        ),
        record(
            "B-2846",
            "园区通勤车调度室",
            0,
            "06:50",
            "环线班车暂不停西厅站",
            "西厅站路面积水，环线班车自07:00起改停西港路口临时站，班距20分钟；恢复时间待通知。",
        ),
        record(
            "B-6450",
            "创研楼设施管理室",
            0,
            "12:20",
            "C座3号电梯通过验收",
            "C座3号电梯故障已修复，安全复检通过，自今日12:30恢复正常使用；此前停梯提醒终止，不再需要绕行其他电梯。",
        ),
        record(
            "B-4016",
            "园林养护中心",
            -1,
            "17:10",
            "东花园修剪安排",
            f"东花园树木修剪安排在 {tomorrow:%Y-%m-%d} 09:00至11:00，届时小径封闭；{day:%Y-%m-%d} 小径正常通行，无需在这一天办理或提前迁移物品。",
        ),
        record(
            "B-9602",
            "园区能源运行站",
            0,
            "10:00",
            "北停车场充电位维护说明",
            "北停车场4至9号充电位今日10:00至17:00进行固件升级，暂停充电，请勿占用维修位，需充电可用其余正常车位。现场未发生火警；服务群关于冒烟停运的说法不实。",
        ),
        record(
            "B-5874",
            "园区访客服务中心",
            -1,
            "18:05",
            "访客接待点迁移预告",
            f"访客接待计划 {day:%Y-%m-%d} 14:00迁至东门大厅，已审核的预约需重新提交；具体启用安排以该日服务中心确认通知为准。货运预约仍在西门办理。",
        ),
        record(
            "B-7195",
            "园区文化办公室",
            0,
            "09:35",
            "摄影作品线上展映",
            "园区摄影作品今日开始线上展映，供大家自愿欣赏；不涉及通行、访客办理、公共服务时段或设施使用的调整。",
        ),
        record(
            "B-7392",
            "园区道路管理站",
            0,
            "11:40",
            "北门车道提前恢复安排",
            "北门施工验收已完成，车辆通道将于今日16:30恢复，比原定18:00提前。16:30前车辆继续经东门通行；北门行人通道一直正常，不受车道施工影响。以本通知替代昨日安排。",
        ),
        record(
            "B-1548",
            "园区餐饮服务中心",
            0,
            "07:15",
            "东食堂晚餐安排待确认",
            "东食堂排风设备需维护，今日晚餐可能调整场地；午餐正常，晚餐安排待中午确认，勿据此判断园区停供晚餐。",
        ),
        record(
            "B-2084",
            "园区安保中心",
            0,
            "16:00",
            "东门临时交通管制",
            "因应急演练，东门将在今日16:15至16:45暂停车辆进出，其他通道按现场指引通行。",
        ),
        record(
            "B-4627",
            "物业服务台",
            0,
            "14:35",
            "环线班车恢复原路线",
            "转交通勤车调度室确认：环线班车已于今日14:10恢复原路线和西厅站，临时西港路口站撤销，当前班距恢复15分钟。",
        ),
        record(
            "B-1078",
            "创研楼设施管理室",
            -1,
            "19:45",
            "C座3号电梯停用检修",
            "C座3号电梯发生故障，即时停用检修；可使用同楼其他电梯。恢复时间待安全复检后通知。",
        ),
        record(
            "B-2639",
            "园区访客服务中心",
            0,
            "11:15",
            "访客接待点最终启用通知",
            "接待点最终调整为南门一层大厅，自今日16:00起承接全部访客接待，16:00前沿用原接待点。已审核预约继续有效，无需重办。昨日东门14:00启用及重新预约的预告作废；货运预约仍在西门办理。",
        ),
        record(
            "B-4731",
            "园区道路管理站",
            -1,
            "20:10",
            "北门车道施工计划",
            f"北门车道计划 {day:%Y-%m-%d} 08:00至18:00封闭施工，车辆改经东门；行人通道保留。若进度有变，将另行发布。",
        ),
        record(
            "B-4481",
            "园区通勤车调度室",
            1,
            "07:00",
            "早班车发车提醒",
            f"{tomorrow:%Y-%m-%d} 早班首车临时调整至07:20；本消息为当日早间调度通知。",
        ),
        record(
            "B-9027",
            "园区餐饮服务中心",
            0,
            "12:40",
            "东食堂晚餐转场确认",
            "东食堂排风维护期间，今日晚餐改在西食堂供应，时段17:00至19:00，餐卡照常使用。东食堂午餐正常，园区并非停供晚餐，请晚餐就餐者前往西食堂。",
        ),
        record(
            "B-3216",
            "入驻企业服务群",
            0,
            "09:10",
            "北停车场充电区情况待核实",
            "有同事称充电区冒烟并猜测全部车位停运，尚无现场确认；请等待能源运行站的正式说明。",
        ),
        record(
            "B-8163",
            "园区通勤车调度室",
            0,
            "14:20",
            "环线班车积水绕行结束",
            "西厅站积水清理完成，环线班车已于今日14:10恢复原路线和西厅站，西港路口临时站撤销，班距恢复15分钟；早间20分钟班距及绕行安排终止。",
        ),
    ]
    context = {
        "reference_date": day.isoformat(),
        "timezone": "Asia/Shanghai",
        "cutoff": cutoff.isoformat(),
        "scope": "给定公告归档的今日运营聚合；按参考日和15:00资料截点筛选，不代表全网新闻或园区全部实时状态。",
    }
    text = (
        "# 澄湾科创园公告归档\n\n"
        f"本次汇编参考日：{day:%Y-%m-%d}；资料截点：15:00（Asia/Shanghai）。\n\n"
        "这是混合时段的公告归档；请结合发布时间、主管单位更新和实际影响日期判断，不按文件顺序取舍。\n\n"
        + "\n".join(records)
    )
    return context, text


def prepare(workdir, state_dir):
    context, source = build_materials(datetime.now(SHANGHAI))
    materials = Path(workdir) / "materials"
    materials.mkdir(parents=True, exist_ok=True)
    payloads = {
        "briefing-context.json": json.dumps(context, ensure_ascii=False, indent=2)
        + "\n",
        "bulletins.md": source,
    }
    hashes = {}
    for filename, text in payloads.items():
        content = text.encode("utf-8")
        (materials / filename).write_bytes(content)
        hashes[filename] = hashlib.sha256(content).hexdigest()
    state = Path(state_dir)
    state.mkdir(parents=True, exist_ok=True)
    (state / "reference.json").write_text(
        json.dumps(
            {"context": context, "sha256": hashes}, ensure_ascii=False, indent=2
        ),
        encoding="utf-8",
    )
    return ["materials"]
