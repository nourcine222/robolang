from __future__ import annotations

from dataclasses import is_dataclass, fields


def dump_ast(node, indent: int = 0) -> str:
    return _dump(node, indent)


def _dump(node, indent: int) -> str:
    pad = "  " * indent
    if isinstance(node, list):
        if not node:
            return pad + "[]"
        return "\n".join(_dump(item, indent) for item in node)
    if is_dataclass(node):
        name = type(node).__name__
        parts = []
        for f in fields(node):
            value = getattr(node, f.name)
            if is_dataclass(value) or isinstance(value, list):
                parts.append(f"{pad}{name}.{f.name}:")
                parts.append(_dump(value, indent + 1))
            else:
                parts.append(f"{pad}{name}.{f.name} = {value!r}")
        return "\n".join(parts)
    return pad + repr(node)
