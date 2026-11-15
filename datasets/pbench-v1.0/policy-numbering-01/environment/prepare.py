"""Prepare one release-policy draft and retain its execution-specific reference."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls


def prepare(workdir: str, state_dir: str) -> list[str]:
    workdir, state_dir = Path(workdir), Path(state_dir)
    effective_date = datetime.now(timezone(timedelta(hours=8))).date().isoformat()
    document = Document()
    document.core_properties.title = "青岚数据发布审批流程"
    document.core_properties.author = "青岚数据运营办公室"
    document.core_properties.comments = ""
    numbering = document.part.numbering_part.element
    numbering.append(
        parse_xml(f"""<w:abstractNum {nsdecls("w")} w:abstractNumId="44">
      <w:multiLevelType w:val="multilevel"/>
      <w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="decimal"/>
        <w:pStyle w:val="ProcedureStep"/><w:lvlText w:val="%1."/></w:lvl>
      <w:lvl w:ilvl="1"><w:start w:val="1"/><w:numFmt w:val="lowerLetter"/>
        <w:lvlText w:val="%2)"/><w:lvlRestart w:val="1"/></w:lvl>
    </w:abstractNum>""")
    )
    numbering.append(
        parse_xml(f"""<w:num {nsdecls("w")} w:numId="44">
      <w:abstractNumId w:val="44"/></w:num>""")
    )
    numbering.append(
        parse_xml(f"""<w:abstractNum {nsdecls("w")} w:abstractNumId="45">
      <w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="upperLetter"/>
        <w:pStyle w:val="ExceptionStep"/><w:lvlText w:val="%1)"/></w:lvl>
    </w:abstractNum>""")
    )
    numbering.append(
        parse_xml(f"""<w:num {nsdecls("w")} w:numId="45">
      <w:abstractNumId w:val="45"/>
      <w:lvlOverride w:ilvl="0"><w:startOverride w:val="3"/></w:lvlOverride>
    </w:num>""")
    )
    for name, num_id in (("Procedure Step", 44), ("Exception Step", 45)):
        style = document.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
        style.base_style = document.styles["Normal"]
        style.element.get_or_add_pPr().append(
            parse_xml(f'<w:numPr {nsdecls("w")}><w:numId w:val="{num_id}"/></w:numPr>')
        )
    document.add_heading("青岚数据发布审批流程", 0)
    document.add_paragraph("生效日期：待审批")
    document.add_paragraph("适用范围：数据看板和数据接口的计划发布。")
    document.add_paragraph(
        "申请提交：发布负责人至少提前 1 个工作日提交审批，附变更清单和影响范围。",
        "Procedure Step",
    )
    document.add_paragraph(
        "数据复核：数据负责人核对数据口径；涉及敏感数据时在团队群告知。",
        "Procedure Step",
    )
    for text in (
        "口径检查：核对指标定义、样本期间和去重规则，并记录复核人。",
        "权限检查：检查访问授权清单，发布前由数据负责人确认。",
    ):
        paragraph = document.add_paragraph(text)
        paragraph._p.get_or_add_pPr().append(
            parse_xml(
                f'<w:numPr {nsdecls("w")}><w:ilvl w:val="1"/>'
                '<w:numId w:val="44"/></w:numPr>'
            )
        )
    document.add_paragraph(
        "发布执行：发布负责人完成部署，在团队群发送结果，并记录版本号。",
        "Procedure Step",
    )
    document.add_heading("例外处理", 1)
    document.add_paragraph(
        "紧急修复：生产故障可由值班负责人先行批准，次日补齐审批记录。",
        "Exception Step",
    )
    document.add_paragraph(
        "延期发布：审批未完成时暂停发布，由发布负责人在团队群通知新的计划。",
        "Exception Step",
    )
    document.add_paragraph("说明：流程责任人每季度检查一次执行记录。")
    document.save(workdir / "release-approval.docx")
    change = f"""# 发布审批流程变更单

签发部门：青岚数据运营办公室
生效日期：{effective_date}（按本次准备时的上海日期）

本次仅调整以下要求，其他条目继续有效：

- “申请提交”：提前量从 1 个工作日改为 3 个工作日；材料中追加数据分类和回滚负责人，原有变更清单及影响范围继续保留。
- “数据复核”：涉及敏感数据时，必须在发布前获得安全负责人批准；仅在团队群告知不能代替批准。数据负责人核对口径的职责不变。
- “发布执行”：部署后先观察 30 分钟的错误率；达到 2% 时由回滚负责人执行回滚。原有团队群结果通知和版本号记录继续保留。
- “紧急修复”：先行批准仍由值班负责人负责，补齐记录的期限改为 24 小时内。

审批人：运营负责人林予安
"""
    (workdir / "change-request.md").write_text(change, encoding="utf-8")
    (state_dir / "reference.json").write_text(
        json.dumps({"effective_date": effective_date}, ensure_ascii=False),
        encoding="utf-8",
    )
    return ["release-approval.docx", "change-request.md"]
