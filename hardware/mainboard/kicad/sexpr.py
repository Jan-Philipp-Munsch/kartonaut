"""Minimal S-expression reader/writer for KiCad files (symbols, schematics, footprints).

Lists are Python lists, atoms are str; quoted strings are kept as Q (a str subclass) so they are
written back quoted. Numbers stay strings, so nothing is lost or reformatted on the way through.
"""


class Q(str):
    """A quoted string atom."""


def parse(text):
    pos, n = 0, len(text)
    stack, cur = [], []
    while pos < n:
        c = text[pos]
        if c in " \t\r\n":
            pos += 1
        elif c == "(":
            stack.append(cur)
            cur = []
            pos += 1
        elif c == ")":
            done = cur
            cur = stack.pop()
            cur.append(done)
            pos += 1
        elif c == '"':
            pos += 1
            buf = []
            while text[pos] != '"':
                if text[pos] == "\\":
                    pos += 1
                    buf.append({"n": "\n", "t": "\t"}.get(text[pos], text[pos]))
                else:
                    buf.append(text[pos])
                pos += 1
            pos += 1
            cur.append(Q("".join(buf)))
        else:
            start = pos
            while pos < n and text[pos] not in ' \t\r\n()"':
                pos += 1
            cur.append(text[start:pos])
    assert not stack, "unbalanced parentheses"
    return cur[0] if len(cur) == 1 else cur


def _atom(a):
    if isinstance(a, Q):
        return '"' + a.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'
    if isinstance(a, float):
        return f"{a:.4f}".rstrip("0").rstrip(".") if a != int(a) else str(int(a))
    if isinstance(a, int):
        return str(a)
    return str(a)


SHORT = {"at", "xy", "size", "start", "end", "mid", "center", "font", "stroke", "width", "type", "uuid",
         "length", "offset", "justify", "color", "fill", "pts", "effects", "reference", "unit", "page", "path",
         "layer", "layers", "drill", "net", "diameter", "radius", "thickness", "hide", "in_bom", "on_board",
         "exclude_from_sim", "dnp", "fields_autoplaced", "pin_names", "pin_numbers", "property", "number",
         "name", "lib_id", "mirror", "convert", "rotate", "scale", "model", "tstamp", "id"}


def dumps(node, indent=0):
    if not isinstance(node, list):
        return _atom(node)
    if not node:
        return "()"
    flat = all(not isinstance(x, list) for x in node)
    head = node[0] if not isinstance(node[0], list) else ""
    if flat or (head in SHORT and sum(isinstance(x, list) for x in node) <= 2 and len(str(node)) < 160):
        return "(" + " ".join(dumps(x) for x in node) + ")"
    pad = "\t" * (indent + 1)
    parts = []
    i = 0
    while i < len(node) and not isinstance(node[i], list):
        parts.append(_atom(node[i]))
        i += 1
    out = "(" + " ".join(parts)
    for x in node[i:]:
        out += "\n" + pad + dumps(x, indent + 1)
    return out + "\n" + "\t" * indent + ")"


def find(node, key):
    """First child list whose head is key."""
    for x in node:
        if isinstance(x, list) and x and x[0] == key:
            return x
    return None


def findall(node, key):
    return [x for x in node if isinstance(x, list) and x and x[0] == key]


def prop(node, name):
    for p in findall(node, "property"):
        if p[1] == name:
            return p
    return None
