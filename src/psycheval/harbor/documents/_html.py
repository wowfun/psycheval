"""HTML tree and CSS syntax facts; no resource loading or layout evaluation."""

from ._limits import DocumentLimitError, InspectionBudget
from .models import (
    CssDeclaration,
    CssRule,
    HtmlCell,
    HtmlHeading,
    HtmlLink,
    HtmlNode,
    HtmlReport,
    HtmlTable,
    _html_text,
)


def inspect(snapshot, backend, css, limits):
    budget = InspectionBudget(limits)
    budget.pages(1)
    parser = backend.HTMLParser(namespaceHTMLElements=False)
    document = parser.parse(snapshot.content)
    encoding = parser.tokenizer.stream.charEncoding[0]
    decoded = snapshot.content.decode(encoding.codec_info.name, errors="replace")
    diagnostics = []
    for position, code, _ in parser.errors:
        budget.fact()
        diagnostic = f"HTML {position[0]}:{position[1]}: {code}"
        budget.text(diagnostic)
        diagnostics.append(diagnostic)

    elements, ids, parents = [], {}, {}
    pending = [(document, None)]
    while pending:
        element, parent = pending.pop()
        budget.fact()
        if not isinstance(element.tag, str):
            continue
        identity = len(elements) + 1
        ids[element], parents[element] = identity, parent
        elements.append(element)
        budget.fact(len(element.attrib))
        pending.extend((child, identity) for child in reversed(element))
    nodes = []
    for element in elements:
        content = [element.text] if element.text else []
        for child in element:
            if child in ids:
                content.append(ids[child])
            if child.tail:
                content.append(child.tail)
        budget.fact(len(content))
        nodes.append(
            HtmlNode(
                ids[element],
                parents[element],
                element.tag,
                tuple(element.attrib.items()),
                tuple(content),
            )
        )
    nodes = tuple(nodes)
    body_id = next((node.id for node in nodes if node.tag == "body"), nodes[0].id)
    by_id = {node.id: node for node in nodes}

    def text(identity):
        value = _html_text(by_id, identity, limits.text_bytes)
        budget.text(value)
        return value

    def ancestor(identity, tags):
        parent = by_id[identity].parent_id
        while parent is not None:
            budget.fact()
            node = by_id[parent]
            if node.tag in tags:
                return node.id
            parent = node.parent_id
        return None

    def span(attributes, name):
        raw = attributes.get(name, "1")
        try:
            value = int(raw)
        except ValueError:
            return None
        return value if value >= 0 else None

    headings, links, styles, tables = [], [], [], {}
    for node in nodes:
        attributes = dict(node.attributes)
        if node.tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            headings.append(HtmlHeading(node.id, int(node.tag[1]), text(node.id)))
        if node.tag in {"a", "area"} and "href" in attributes:
            links.append(HtmlLink(node.id, attributes["href"], text(node.id)))
        if node.tag == "table":
            tables.setdefault(node.id, [])
        if node.tag in {"td", "th"}:
            table_id = ancestor(node.id, {"table"})
            if table_id is not None:
                tables.setdefault(table_id, []).append(
                    HtmlCell(
                        node.id,
                        ancestor(node.id, {"tr"}),
                        span(attributes, "rowspan"),
                        span(attributes, "colspan"),
                        text(node.id),
                    )
                )
        if node.tag == "style":
            styles.extend(_styles(css, node.text, node.id, budget))
        if "style" in attributes:
            styles.extend(
                _styles(css, attributes["style"], node.id, budget, inline=True)
            )
    text(body_id)
    return HtmlReport(
        snapshot,
        decoded,
        encoding.name,
        nodes,
        body_id,
        tuple(headings),
        tuple(links),
        tuple(HtmlTable(identity, tuple(cells)) for identity, cells in tables.items()),
        tuple(styles),
        tuple(diagnostics),
        limits.text_bytes,
    )


def _styles(css, source, node_id, budget, *, inline=False):
    tokens = css.parse_component_value_list(source)
    pending = list(tokens)
    while pending:
        token = pending.pop()
        budget.fact()
        pending.extend(getattr(token, "content", ()) or ())
        pending.extend(getattr(token, "arguments", ()) or ())

    def serialize(tokens):
        value = css.serialize(tokens).strip()
        budget.text(value)
        return value

    def syntax_errors(tokens):
        pending, errors = list(tokens), []
        while pending:
            token = pending.pop()
            budget.fact()
            if token.type == "error":
                message = (
                    f"CSS {token.source_line}:{token.source_column}: {token.message}"
                )
                budget.text(message)
                errors.append(message)
            pending.extend(getattr(token, "content", ()) or ())
            pending.extend(getattr(token, "arguments", ()) or ())
        return errors

    # Limit parser recursion independently of the browser's much deeper DOM limit.
    def contents(items, depth):
        if depth > 64:
            raise DocumentLimitError("CSS rule nesting exceeds 64 levels")
        declarations, rules, errors = [], [], []
        for item in items:
            budget.fact()
            if item.type == "declaration":
                invalid = syntax_errors(item.value)
                if invalid:
                    errors.extend(invalid)
                    continue
                declarations.append(
                    CssDeclaration(item.name, serialize(item.value), item.important)
                )
            elif item.type in {"qualified-rule", "at-rule"}:
                invalid = syntax_errors(item.prelude)
                if invalid:
                    errors.extend(invalid)
                    continue
                nested = (
                    contents(
                        css.parse_blocks_contents(
                            item.content, skip_comments=True, skip_whitespace=True
                        ),
                        depth + 1,
                    )
                    if item.content is not None
                    else ((), (), ())
                )
                rules.append(
                    CssRule(
                        node_id,
                        getattr(item, "lower_at_keyword", "rule"),
                        serialize(item.prelude),
                        *nested,
                    )
                )
            elif item.type == "error":
                message = f"CSS {item.source_line}:{item.source_column}: {item.message}"
                budget.text(message)
                errors.append(message)
        return tuple(declarations), tuple(rules), tuple(errors)

    if inline:
        return (
            CssRule(
                node_id,
                "inline",
                "",
                *contents(
                    css.parse_blocks_contents(
                        tokens, skip_comments=True, skip_whitespace=True
                    ),
                    0,
                ),
            ),
        )
    _, rules, errors = contents(
        css.parse_stylesheet(tokens, skip_comments=True, skip_whitespace=True), 0
    )
    if errors:
        return (*rules, CssRule(node_id, "stylesheet", "", (), (), errors))
    return rules
