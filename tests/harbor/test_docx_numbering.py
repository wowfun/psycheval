"""Numbering definitions retain source facts without synthesizing display labels."""

import io
from pathlib import Path

import pytest

from psycheval.harbor.documents import inspect_document
from psycheval.harbor.evidence import SourceSnapshot

pytest.importorskip("docx")


def document():
    docx = pytest.importorskip("docx")
    from docx.oxml import parse_xml
    from docx.oxml.ns import nsdecls

    result = docx.Document()
    root = result.part.numbering_part.element
    root.append(
        parse_xml(f"""<w:abstractNum {nsdecls("w")} w:abstractNumId="42">
      <w:lvl w:ilvl="1"><w:start w:val="1"/><w:numFmt w:val="decimal"/>
      <w:lvlText w:val="%1.%2"/><w:lvlRestart w:val="1"/></w:lvl>
    </w:abstractNum>""")
    )
    root.append(
        parse_xml(f"""<w:num {nsdecls("w")} w:numId="42">
      <w:abstractNumId w:val="42"/>
      <w:lvlOverride w:ilvl="1"><w:startOverride w:val="7"/></w:lvlOverride>
    </w:num>""")
    )
    return result


def numbering(owner, num_id="42", level="1"):
    from docx.oxml import parse_xml
    from docx.oxml.ns import nsdecls

    owner.get_or_add_pPr().append(
        parse_xml(f'''<w:numPr {nsdecls("w")}>
       <w:numId w:val="{num_id}"/><w:ilvl w:val="{level}"/></w:numPr>''')
    )


def inspect(document):
    stream = io.BytesIO()
    document.save(stream)
    return inspect_document(SourceSnapshot(Path("numbered.docx"), stream.getvalue()))


def test_docx_numbering_inherits_style_and_preserves_overrides_cancellation_and_text():
    from docx.enum.style import WD_STYLE_TYPE
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    doc = document()
    base = doc.styles.add_style("NumberedBase", WD_STYLE_TYPE.PARAGRAPH)
    numbering(base.element, level="0")  # The abstract pStyle binding selects level 1.
    definition = doc.part.numbering_part.element.find(
        "w:abstractNum[@w:abstractNumId='42']/w:lvl",
        {"w": qn("w:num").split("}")[0][1:]},
    )
    binding = OxmlElement("w:pStyle")
    binding.set(qn("w:val"), "NumberedBase")
    definition.append(binding)
    child = doc.styles.add_style("NumberedChild", WD_STYLE_TYPE.PARAGRAPH)
    child.base_style = base
    doc.add_paragraph("Inherited", style=child)
    direct = doc.add_paragraph("Direct")
    numbering(direct._p)
    cancelled = doc.add_paragraph("Cancelled", style=child)
    numbering(cancelled._p, "0")
    doc.add_paragraph("Ordinary")
    report = inspect(doc)
    first, second, third, fourth = report.blocks
    assert first.numbering == second.numbering
    fact = first.numbering
    assert (fact.num_id, fact.level, fact.abstract_num_id) == (42, 1, 42)
    assert (fact.num_format, fact.level_text, fact.start, fact.restart) == (
        "decimal",
        "%1.%2",
        7,
        1,
    )
    assert fact.error is None
    assert third.numbering.num_id == 0 and third.numbering.error is None
    assert fourth.numbering is None
    assert first.text == "Inherited" and "7 Inherited" not in report.to_markdown()


@pytest.mark.parametrize(
    "failure", ["instance", "level", "abstract", "style_link", "cycle", "invalid"]
)
def test_docx_unresolved_numbering_keeps_body_text_and_diagnostic(failure):
    from docx.enum.style import WD_STYLE_TYPE
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    doc = document()
    paragraph = doc.add_paragraph("Readable text")
    numbering(
        paragraph._p,
        "999" if failure == "instance" else "bad" if failure == "invalid" else "42",
        "8" if failure == "level" else "1",
    )
    abstract = doc.part.numbering_part.element.find(
        ".//" + qn("w:abstractNum") + "[@" + qn("w:abstractNumId") + "='42']"
    )
    if failure == "abstract":
        abstract.getparent().remove(abstract)
    elif failure == "style_link":
        link = OxmlElement("w:numStyleLink")
        link.set(qn("w:val"), "LinkedStyle")
        abstract.append(link)
    elif failure == "cycle":
        style = doc.styles.add_style("Cyclic", WD_STYLE_TYPE.PARAGRAPH)
        style.base_style = style
        paragraph.style = style
    report = inspect(doc)
    assert report.blocks[0].text == "Readable text"
    assert report.blocks[0].numbering.error


def test_docx_concrete_level_replaces_abstract_definition_and_absent_values_stay_absent():
    from docx.oxml import parse_xml
    from docx.oxml.ns import nsdecls, qn

    doc = document()
    paragraph = doc.add_paragraph("Item")
    numbering(paragraph._p)
    root = doc.part.numbering_part.element
    instance = root.find("w:num[@w:numId='42']", {"w": qn("w:num").split("}")[0][1:]})
    override = instance.find(qn("w:lvlOverride"))
    override.remove(override.find(qn("w:startOverride")))
    override.append(
        parse_xml(f"""<w:lvl {nsdecls("w")} w:ilvl="1">
      <w:numFmt w:val="upperRoman"/><w:lvlText w:val="%2)"/>
    </w:lvl>""")
    )
    fact = inspect(doc).blocks[0].numbering
    assert fact.num_format == "upperRoman" and fact.level_text == "%2)"
    assert fact.start is None and fact.restart is None and fact.error is None


def test_docx_numeric_id_spelling_and_negative_start_are_preserved_as_values():
    from docx.oxml.ns import qn

    doc = document()
    paragraph = doc.add_paragraph("Item")
    numbering(paragraph._p, "042", "01")
    root = doc.part.numbering_part.element
    ns = {"w": qn("w:num").split("}")[0][1:]}
    root.find("w:num[@w:numId='42']", ns).set(qn("w:numId"), "+42")
    root.find("w:num[@w:numId='+42']/w:lvlOverride/w:startOverride", ns).set(
        qn("w:val"), "-1"
    )
    fact = inspect(doc).blocks[0].numbering
    assert (fact.num_id, fact.level, fact.start, fact.error) == (42, 1, -1, None)


def test_docx_style_level_without_binding_is_explicitly_unresolved():
    from docx.enum.style import WD_STYLE_TYPE

    doc = document()
    style = doc.styles.add_style("Unbound", WD_STYLE_TYPE.PARAGRAPH)
    numbering(style.element)
    doc.add_paragraph("Body", style=style)
    fact = inspect(doc).blocks[0].numbering
    assert fact.num_id == 42 and fact.level is None
    assert "pStyle binding" in fact.error
