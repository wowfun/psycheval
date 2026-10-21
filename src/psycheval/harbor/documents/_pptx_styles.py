"""Private OOXML style resolution; no rendering or application automation."""

import colorsys
import math
from dataclasses import dataclass
from functools import cached_property
from itertools import chain

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}
FILL_TAGS = {"solidFill", "gradFill", "noFill", "blipFill", "pattFill", "grpFill"}
COLOR_TAGS = {"srgbClr", "schemeClr", "sysClr", "prstClr", "scrgbClr", "hslClr"}
WHITE = [(255, 255, 255)]
IDENTITY = (1, 0, 0, 1, 0, 0)


class StyleError(ValueError):
    """An effective color cannot be established from the retained OOXML."""


def local(node):
    return node.tag.rsplit("}", 1)[-1]


def child_of(node, names):
    return (
        next((child for child in node if local(child) in names), None)
        if node is not None
        else None
    )


def clamp(value):
    return min(1.0, max(0.0, value))


def distinct(colors, budget):
    retained = {}
    for color in colors:
        budget.color()
        retained[color] = None
    return list(retained)


def compose(front, backs, budget):
    for rgb in backs:
        budget.color()
        yield tuple(
            round(channel * front[3] * 255 + back * (1 - front[3]), 9)
            for channel, back in zip(front[:3], rgb, strict=True)
        )


class Styles:
    def __init__(self, presentation, slide, options, budget):
        from lxml import etree

        self.options = options
        self.budget = budget
        self._chains = {}
        self._fills = {}
        self.presentation, self.slide = presentation, slide
        self.layout, self.master = slide.slide_layout, slide.slide_layout.slide_master
        self.theme = None
        for relation in self.master.part.rels.values():
            if not relation.is_external and relation.reltype.endswith("/theme"):
                self.theme = etree.fromstring(
                    relation.target_part.blob,
                    etree.XMLParser(resolve_entities=False, no_network=True),
                )
                break
        self.color_map = {"bg1": "lt1", "tx1": "dk1", "bg2": "lt2", "tx2": "dk2"}
        mapping = self.master._element.find("p:clrMap", NS)
        if mapping is not None:
            self.color_map.update(mapping.attrib)
        for owner in (self.layout, slide):
            mapping = owner._element.find("p:clrMapOvr/a:overrideClrMapping", NS)
            if mapping is not None:
                self.color_map.update(mapping.attrib)

    def color(self, node, placeholder=None, seen=()):
        self.budget.color()
        if node is None:
            raise StyleError("missing color")
        kind, value = local(node), node.get("val")
        if kind in {"srgbClr", "sysClr"}:
            value = node.get("lastClr") if kind == "sysClr" else value
            if value is None or len(value) != 6:
                raise StyleError("invalid RGB color")
            rgb = tuple(int(value[index : index + 2], 16) / 255 for index in (0, 2, 4))
            alpha = 1.0
        elif kind == "schemeClr":
            if value == "phClr":
                if placeholder is None:
                    raise StyleError("unresolved placeholder color")
                rgb, alpha = placeholder[:3], placeholder[3]
            else:
                value = self.color_map.get(value, value)
                if value in seen or self.theme is None:
                    raise StyleError(f"unresolved theme color {value}")
                parent = self.theme.find(f"a:themeElements/a:clrScheme/a:{value}", NS)
                if parent is None:
                    raise StyleError(f"unresolved theme color {value}")
                resolved = self.color(child_of(parent, COLOR_TAGS), seen=(*seen, value))
                rgb, alpha = resolved[:3], resolved[3]
        elif kind == "prstClr":
            presets = {
                "white": "FFFFFF",
                "black": "000000",
                "blue": "0000FF",
                "navy": "000080",
                "red": "FF0000",
                "green": "008000",
            }
            if value not in presets:
                raise StyleError(f"unsupported preset color {value}")
            rgb = tuple(
                int(presets[value][index : index + 2], 16) / 255 for index in (0, 2, 4)
            )
            alpha = 1.0
        elif kind == "scrgbClr":
            rgb = tuple(
                clamp(int(node.get(channel)) / 100000) for channel in ("r", "g", "b")
            )
            alpha = 1.0
        else:
            raise StyleError(f"unsupported color {kind}")
        for transform in node:
            self.budget.color()
            name = local(transform)
            amount = int(transform.get("val", "0")) / 100000
            if name == "alpha":
                alpha = amount
            elif name == "alphaMod":
                alpha *= amount
            elif name == "alphaOff":
                alpha += amount
            elif name in {"lumMod", "lumOff", "satMod", "satOff"}:
                hue, light, saturation = colorsys.rgb_to_hls(*rgb)
                if name == "lumMod":
                    light *= amount
                elif name == "lumOff":
                    light += amount
                elif name == "satMod":
                    saturation *= amount
                else:
                    saturation += amount
                rgb = colorsys.hls_to_rgb(hue, clamp(light), clamp(saturation))
            elif name == "shade":
                rgb = tuple(channel * amount for channel in rgb)
            elif name == "tint":
                rgb = tuple(channel + (1 - channel) * amount for channel in rgb)
            else:
                raise StyleError(f"unsupported color transform {name}")
        return (*map(clamp, rgb), clamp(alpha))

    def style_fill(self, reference, placeholder=None):
        if self.theme is None:
            raise StyleError("missing theme fill styles")
        index = int(reference.get("idx", "0"))
        if index == 0:
            return None, placeholder
        path = "bgFillStyleLst" if index >= 1001 else "fillStyleLst"
        index = index - 1001 if index >= 1001 else index - 1
        styles = self.theme.find(f"a:themeElements/a:fmtScheme/a:{path}", NS)
        if styles is None or not 0 <= index < len(styles):
            raise StyleError("invalid theme fill reference")
        color = child_of(reference, COLOR_TAGS)
        return styles[index], self.color(color) if color is not None else placeholder

    def fill(self, node, backs, placeholder=None):
        if node is None or local(node) == "noFill":
            return backs, False
        kind = local(node)
        if kind == "solidFill":
            colors = [self.color(child_of(node, COLOR_TAGS), placeholder)]
        elif kind == "gradFill":
            colors = [
                self.color(child_of(stop, COLOR_TAGS), placeholder)
                for stop in node.iterfind("a:gsLst/a:gs", NS)
            ]
            if not colors:
                raise StyleError("empty gradient")
        else:
            raise StyleError(f"unsupported fill {kind}")
        return distinct(
            (rgb for color in colors for rgb in compose(color, backs, self.budget)),
            self.budget,
        ), all(color[3] == 1 for color in colors)

    def background(self):
        owners = (self.slide, self.layout, self.master)

        def inherited(index):
            if index == len(owners):
                return WHITE
            owner = owners[index]
            background = owner._element.find("p:cSld/p:bg", NS)
            if background is None:
                return inherited(index + 1)
            properties = background.find("p:bgPr", NS)
            placeholder = None
            if properties is not None:
                fill = child_of(properties, FILL_TAGS)
                if fill is None:
                    raise StyleError("background has no fill")
            else:
                reference = background.find("p:bgRef", NS)
                if reference is None:
                    raise StyleError("background has no properties or reference")
                fill, placeholder = self.style_fill(reference)
            colors, opaque = self.fill(fill, WHITE, placeholder)
            if opaque:
                return colors
            return self.fill(fill, inherited(index + 1), placeholder)[0]

        return inherited(0)

    def shape_fill(self, shape, backs):
        key = shape._element
        if key not in self._fills:
            self._fills[key] = self._shape_fill(shape)
        fill, placeholder = self._fills[key]
        return self.fill(fill, backs, placeholder)

    def _shape_fill(self, shape):
        # Missing placeholder fills inherit; explicit noFill is transparent.
        for source in self.shape_chain(shape):
            picture_fill = source._element.find("p:blipFill", NS)
            if picture_fill is not None:
                return picture_fill, None
            properties = source._element.find("p:spPr", NS)
            fill = child_of(properties, FILL_TAGS)
            if fill is not None:
                return fill, None
            reference = source._element.find("p:style/a:fillRef", NS)
            if reference is not None:
                return self.style_fill(reference)
        return None, None

    def shape_chain(self, shape):
        if shape._element not in self._chains:
            self._chains[shape._element] = self._shape_chain(shape)
        return self._chains[shape._element]

    def _shape_chain(self, shape):
        chain = [shape]
        if not shape.is_placeholder:
            return chain
        for placeholder in self.layout.placeholders:
            if placeholder.placeholder_format.idx == shape.placeholder_format.idx:
                if placeholder._element is not shape._element:
                    chain.append(placeholder)
                break
        kind = placeholder_kind(shape)
        for placeholder in self.master.placeholders:
            if placeholder_kind(placeholder) == kind:
                if placeholder._element is not shape._element:
                    chain.append(placeholder)
                break
        return chain

    def text_properties(self, shape, paragraph, run_properties=None, *, defaults=True):
        if run_properties is not None:
            yield run_properties
        level = paragraph.level + 1
        own = paragraph._p.find("a:pPr/a:defRPr", NS)
        if own is not None:
            yield own
        for index, source in enumerate(self.shape_chain(shape)):
            if index:
                candidates = source._element.findall("p:txBody/a:p", NS)
                for candidate in candidates:
                    properties = candidate.find("a:pPr", NS)
                    if (
                        properties is None
                        or int(properties.get("lvl", "0")) != level - 1
                    ):
                        continue
                    default = properties.find("a:defRPr", NS)
                    if default is not None:
                        yield default
                    break
            default = source._element.find(
                f"p:txBody/a:lstStyle/a:lvl{level}pPr/a:defRPr", NS
            )
            if default is not None:
                yield default
        if not defaults:
            return
        style = (
            "titleStyle"
            if placeholder_kind(shape) == "title"
            else "bodyStyle"
            if shape.is_placeholder
            else "otherStyle"
        )
        default = self.master._element.find(
            f"p:txStyles/p:{style}/a:lvl{level}pPr/a:defRPr", NS
        )
        if default is not None:
            yield default
        default = self.presentation._element.find(
            f"p:defaultTextStyle/a:lvl{level}pPr/a:defRPr", NS
        )
        if default is not None:
            yield default

    def font_size(self, shape, paragraph, run_properties=None):
        for properties in self.text_properties(shape, paragraph, run_properties):
            if properties.get("sz") is not None:
                return int(properties.get("sz")) / 100
        return self.options.fallback_font_size

    def font_colors(self, shape, paragraph, properties, backs):
        def filled(fill):
            colors, opaque = self.fill(fill, backs or WHITE)
            if not backs and not opaque:
                raise StyleError("translucent title ink has an unresolved background")
            return colors

        for source in self.text_properties(
            shape, paragraph, properties, defaults=False
        ):
            fill = child_of(source, FILL_TAGS)
            if fill is not None:
                return filled(fill)
        for source in self.shape_chain(shape):
            reference = source._element.find("p:style/a:fontRef", NS)
            if reference is not None:
                color = self.color(child_of(reference, COLOR_TAGS))
                if not backs and color[3] != 1:
                    raise StyleError(
                        "translucent title ink has an unresolved background"
                    )
                return compose(color, backs or WHITE, self.budget)
        for source in self.text_properties(shape, paragraph, properties):
            fill = child_of(source, FILL_TAGS)
            if fill is not None:
                return filled(fill)
        raise StyleError("unresolved font color")


def placeholder_kind(shape):
    node = shape._element.find(".//p:ph", NS)
    kind = node.get("type", "obj") if node is not None else None
    return "title" if kind in {"title", "ctrTitle"} else kind


def runs(paragraph):
    return [
        (text, node.find("a:rPr", NS))
        for node in paragraph._p
        if local(node) in {"r", "fld"}
        and (text := node.findtext("a:t", default="", namespaces=NS)).strip()
    ]


def multiply(first, second):
    a, b, c, d, e, f = first
    g, h, i, j, k, offset_y = second
    return (
        a * g + c * h,
        b * g + d * h,
        a * i + c * j,
        b * i + d * j,
        a * k + c * offset_y + e,
        b * k + d * offset_y + f,
    )


def point(matrix, x, y):
    a, b, c, d, e, f = matrix
    return a * x + c * y + e, b * x + d * y + f


def orientation(x, y, width, height, rotation, flip_h=False, flip_v=False):
    cosine, sine = math.cos(math.radians(rotation)), math.sin(math.radians(rotation))
    horizontal, vertical = -1 if flip_h else 1, -1 if flip_v else 1
    a, b, c, d = (
        cosine * horizontal,
        sine * horizontal,
        -sine * vertical,
        cosine * vertical,
    )
    cx, cy = x + width / 2, y + height / 2
    return a, b, c, d, cx - a * cx - c * cy, cy - b * cx - d * cy


@dataclass
class Leaf:
    shape: object
    bounds: tuple | None
    order: int
    geometry_error: str | None = None


def _group_matrix(shape):
    transform = shape._element.find("p:grpSpPr/a:xfrm", NS)
    if transform is None:
        return IDENTITY

    def pair(name, first, second):
        node = transform.find(f"a:{name}", NS)
        if node is None:
            raise StyleError("group transform is incomplete")
        return int(node.get(first)), int(node.get(second))

    x, y = pair("off", "x", "y")
    width, height = pair("ext", "cx", "cy")
    child_x, child_y = pair("chOff", "x", "y")
    child_width, child_height = pair("chExt", "cx", "cy")
    if child_width == 0 or child_height == 0:
        raise StyleError("group transform has zero child extent")
    sx, sy = width / child_width, height / child_height
    scale = (sx, 0, 0, sy, x - child_x * sx, y - child_y * sy)
    orient = orientation(
        x,
        y,
        width,
        height,
        int(transform.get("rot", "0")) / 60000,
        transform.get("flipH") in {"1", "true"},
        transform.get("flipV") in {"1", "true"},
    )
    return multiply(orient, scale)


def leaves(shapes, matrix=IDENTITY, geometry_error=None, *, budget):
    result = []
    for shape in shapes:
        budget.fact()
        if hasattr(shape, "shapes"):
            child_matrix, problem = matrix, geometry_error
            if matrix is not None:
                try:
                    child_matrix = multiply(matrix, _group_matrix(shape))
                except (ValueError, TypeError) as error:
                    child_matrix, problem = None, str(error)
            result.extend(leaves(shape.shapes, child_matrix, problem, budget=budget))
        elif matrix is None:
            result.append(Leaf(shape, None, 0, geometry_error))
        else:
            x, y, width, height = (
                shape.left or 0,
                shape.top or 0,
                shape.width or 0,
                shape.height or 0,
            )
            transform = multiply(
                matrix, orientation(x, y, width, height, shape.rotation)
            )
            corners = [
                point(transform, xx, yy)
                for xx, yy in (
                    (x, y),
                    (x + width, y),
                    (x, y + height),
                    (x + width, y + height),
                )
            ]
            result.append(
                Leaf(
                    shape,
                    (
                        min(p[0] for p in corners),
                        min(p[1] for p in corners),
                        max(p[0] for p in corners),
                        max(p[1] for p in corners),
                    ),
                    0,
                )
            )
    for index, leaf in enumerate(result):
        leaf.order = index
    return result


def paragraphs(shape):
    if shape.has_text_frame:
        return [
            paragraph
            for paragraph in shape.text_frame.paragraphs
            if paragraph.text.strip()
        ]
    if shape.has_table:
        return [
            paragraph
            for row in shape.table.rows
            for cell in row.cells
            if not cell.is_spanned
            for paragraph in cell.text_frame.paragraphs
            if paragraph.text.strip()
        ]
    return []


def title(slide, entries, styles):
    placeholder = slide.shapes.title
    if placeholder is not None:
        for entry in entries:
            if entry.shape._element is placeholder._element and paragraphs(entry.shape):
                return entry, paragraphs(entry.shape)
    candidates = []
    for entry in entries:
        if not entry.shape.has_text_frame:
            continue
        for paragraph_index, paragraph in enumerate(paragraphs(entry.shape)):
            size = max(
                (
                    styles.font_size(entry.shape, paragraph, properties)
                    for _, properties in runs(paragraph)
                ),
                default=styles.font_size(entry.shape, paragraph),
            )
            candidates.append(
                (
                    not any(character.isalpha() for character in paragraph.text),
                    -size,
                    entry.bounds[1] if entry.bounds else float("inf"),
                    entry.order,
                    paragraph_index,
                    entry,
                    paragraph,
                )
            )
    if not candidates:
        return None, []
    chosen = min(candidates, key=lambda candidate: candidate[:5])
    return chosen[-2], [chosen[-1]]


def overlap(first, second):
    return max(0, min(first[2], second[2]) - max(first[0], second[0])) * max(
        0, min(first[3], second[3]) - max(first[1], second[1])
    )


def background_shapes(slide, entries, budget):
    result = []
    if slide._element.get("showMasterSp", "1") not in {"0", "false"}:
        if slide.slide_layout._element.get("showMasterSp", "1") not in {"0", "false"}:
            result.extend(
                entry
                for entry in leaves(
                    slide.slide_layout.slide_master.shapes, budget=budget
                )
                if not entry.shape.is_placeholder
            )
        result.extend(
            entry
            for entry in leaves(slide.slide_layout.shapes, budget=budget)
            if not entry.shape.is_placeholder
        )
    return result, entries


class Backgrounds:
    """Slide-scoped style facts; only region intersection tests repeat."""

    def __init__(self, presentation, slide, entries, styles, budget):
        self.styles = styles
        self.inherited, self.own = background_shapes(slide, entries, budget)
        self.canvas = (0, 0, presentation.slide_width, presentation.slide_height)
        self.first_text = next(
            (entry.order for entry in entries if paragraphs(entry.shape)), len(entries)
        )
        self._regions = {}

    @cached_property
    def base(self):
        return self.styles.background()

    @cached_property
    def page(self):
        canvas_area = self.canvas[2] * self.canvas[3]
        colors = self.base
        for entry in [*self.inherited, *self.own[: self.first_text]]:
            if entry.bounds is None:
                raise StyleError(entry.geometry_error)
            coverage = overlap(entry.bounds, self.canvas) / canvas_area
            if coverage >= self.styles.options.background_coverage:
                overlaid, opaque = self.styles.shape_fill(entry.shape, colors)
                if opaque:
                    colors = (
                        overlaid
                        if coverage >= 1 - 1e-9
                        else distinct(chain(colors, overlaid), self.styles.budget)
                    )
        return colors

    def region(self, target):
        if target.order not in self._regions:
            self._regions[target.order] = self._region(target)
        return self._regions[target.order]

    def _region(self, target):
        region = target.bounds
        if region is None:
            raise StyleError(target.geometry_error)
        area = max(0, region[2] - region[0]) * max(0, region[3] - region[1])
        colors = self.base
        for entry in [*self.inherited, *self.own[: target.order]]:
            if entry.bounds is None:
                raise StyleError(entry.geometry_error)
            covered = overlap(region, entry.bounds)
            if covered > 0:
                overlaid, _ = self.styles.shape_fill(entry.shape, colors)
                colors = (
                    overlaid
                    if area and covered / area >= 1 - 1e-9
                    else distinct(chain(colors, overlaid), self.styles.budget)
                )
        return self.styles.shape_fill(target.shape, colors)[0]
