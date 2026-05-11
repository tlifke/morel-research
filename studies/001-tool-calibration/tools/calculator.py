"""calculator — evaluate an arithmetic expression via a restricted AST.

Supports +, -, *, /, **, //, %, parentheses, and the math module's
single-argument functions (sqrt, log, exp, sin, cos, tan, etc.). Does
not evaluate names or function calls outside the allow-list — so no
`__import__`, `open`, etc. Sufficient for the arithmetic prompts in
the A1 seed corpus.
"""

from __future__ import annotations

import ast
import math
import operator
from decimal import Decimal, getcontext

getcontext().prec = 50

_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

_NAMES = {
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau,
}

_FUNCS = {
    "sqrt": math.sqrt,
    "log": math.log,
    "log10": math.log10,
    "log2": math.log2,
    "exp": math.exp,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "abs": abs,
    "floor": math.floor,
    "ceil": math.ceil,
    "round": round,
}


def _eval(node):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"unsupported constant: {node.value!r}")
    if isinstance(node, ast.BinOp):
        op = _BIN_OPS.get(type(node.op))
        if op is None:
            raise ValueError(f"unsupported binary op: {ast.dump(node.op)}")
        return op(_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp):
        op = _UNARY_OPS.get(type(node.op))
        if op is None:
            raise ValueError(f"unsupported unary op: {ast.dump(node.op)}")
        return op(_eval(node.operand))
    if isinstance(node, ast.Name):
        if node.id in _NAMES:
            return _NAMES[node.id]
        raise ValueError(f"unknown name: {node.id}")
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _FUNCS:
            raise ValueError(f"unsupported call: {ast.dump(node)}")
        return _FUNCS[node.func.id](*[_eval(a) for a in node.args])
    raise ValueError(f"unsupported node: {ast.dump(node)}")


def calculator(expression: str) -> str:
    tree = ast.parse(expression, mode="eval")
    result = _eval(tree.body)
    if isinstance(result, float) and result.is_integer():
        return str(int(result))
    return str(result)
