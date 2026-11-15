"""Effective DOCX numbering definitions, without counter or label evaluation."""

from dataclasses import replace

from ._limits import DocumentLimitError
from .models import ParagraphNumbering

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
VAL = "{" + NS["w"] + "}val"


def _value(parent, name):
    node = parent.find("w:" + name, NS) if parent is not None else None
    return node.get(VAL) if node is not None else None


def _number(value, *, nonnegative=True):
    if value is None:
        return None
    result = int(value)
    if nonnegative and result < 0:
        raise ValueError("negative numbering value")
    return result


class Numbering:
    def __init__(self, document, budget):
        from docx.opc.constants import RELATIONSHIP_TYPE as RT

        self.budget = budget
        self.defaults = document.styles.element.find(
            "w:docDefaults/w:pPrDefault/w:pPr", NS
        )
        self.nums, self.abstract = {}, {}
        try:
            root = document.part.part_related_by(RT.NUMBERING).element
        except KeyError:
            return
        for node in root.iter():
            budget.fact()
        for tag, attribute, target in (
            ("num", "numId", self.nums),
            ("abstractNum", "abstractNumId", self.abstract),
        ):
            for node in root.findall("w:" + tag, NS):
                identity = node.get("{" + NS["w"] + "}" + attribute)
                try:
                    identity = _number(identity)
                except ValueError:
                    continue
                if identity is None:
                    continue
                identity = str(identity)
                target[identity] = node if identity not in target else None

    def read(self, paragraph):
        fact = ParagraphNumbering(None)
        try:
            num_id = level = style_level = None
            properties = [paragraph._p.pPr]
            style, seen = paragraph.style, set()
            style_ids = []
            while style is not None:
                self.budget.fact()
                if style.style_id in seen:
                    raise ValueError("cyclic paragraph style inheritance")
                seen.add(style.style_id)
                style_ids.append(style.style_id)
                properties.append(style.element.find("w:pPr", NS))
                style = style.base_style
            properties.append(self.defaults)
            for index, properties_node in enumerate(properties):
                num = (
                    properties_node.find("w:numPr", NS)
                    if properties_node is not None
                    else None
                )
                if num is None:
                    continue
                if num_id is None:
                    num_id = _value(num, "numId")
                if index == 0:
                    level = _value(num, "ilvl")
                elif style_level is None:
                    style_level = _value(num, "ilvl")
            if num_id is None and level is None and style_level is None:
                return None
            fact = replace(
                fact,
                num_id=_number(num_id),
                level=_number(level) if level is not None else 0,
            )
            if fact.num_id == 0:
                return fact
            if fact.num_id is None:
                raise ValueError("numbering properties have no numId")
            if fact.level > 8:
                raise ValueError("numbering level is outside 0..8")
            concrete = self.nums.get(str(fact.num_id))
            if concrete is None:
                raise ValueError("missing or duplicate numbering instance")
            abstract_id = _number(_value(concrete, "abstractNumId"))
            fact = replace(fact, abstract_num_id=abstract_id)
            definition = self.abstract.get(str(abstract_id))
            if definition is None:
                raise ValueError("missing or duplicate abstract numbering definition")
            if definition.find("w:numStyleLink", NS) is not None:
                raise ValueError("numbering-style links are unsupported")
            if level is None:
                linked = {}
                for node in definition.findall("w:lvl", NS):
                    self.budget.fact()
                    style_id = _value(node, "pStyle")
                    if style_id is not None:
                        if style_id in linked:
                            raise ValueError(
                                "ambiguous paragraph style numbering level"
                            )
                        linked[style_id] = _number(node.get("{" + NS["w"] + "}ilvl"))
                resolved = next(
                    (linked[identity] for identity in style_ids if identity in linked),
                    None,
                )
                if resolved is not None:
                    fact = replace(fact, level=resolved)
                elif style_level is not None:
                    fact = replace(fact, level=None)
                    raise ValueError("style numbering level has no pStyle binding")
                if fact.level > 8:
                    raise ValueError("numbering level is outside 0..8")
            levels = [
                node
                for node in definition.findall("w:lvl", NS)
                if _number(node.get("{" + NS["w"] + "}ilvl")) == fact.level
            ]
            overrides = [
                node
                for node in concrete.findall("w:lvlOverride", NS)
                if _number(node.get("{" + NS["w"] + "}ilvl")) == fact.level
            ]
            if len(levels) > 1 or len(overrides) > 1:
                raise ValueError("duplicate numbering level or override")
            effective = levels[0] if levels else None
            override = overrides[0] if overrides else None
            if override is not None:
                replacement = override.find("w:lvl", NS)
                if replacement is not None:
                    effective = replacement
            if effective is None:
                raise ValueError("missing numbering level definition")
            start = _value(override, "startOverride")
            fact = replace(
                fact,
                num_format=_value(effective, "numFmt"),
                level_text=_value(effective, "lvlText"),
                start=_number(
                    start if start is not None else _value(effective, "start"),
                    nonnegative=False,
                ),
                restart=_number(_value(effective, "lvlRestart")),
            )
            self.budget.text(fact.num_format)
            self.budget.text(fact.level_text)
            return fact
        except ValueError as error:
            if isinstance(error, DocumentLimitError):
                raise
            return replace(fact, error=str(error))
