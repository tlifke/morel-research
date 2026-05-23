from __future__ import annotations

import ast
import math
import re
from datetime import date, datetime, timedelta


_GRADE_STATUS_OK = "graded"
_GRADE_STATUS_UNPARSEABLE = "unparseable_prompt"
_GRADE_STATUS_AMBIGUOUS = "ambiguous_ground_truth"
_GRADE_STATUS_UNGRADABLE = "ungradable"


_ALLOWED_BINOPS = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.Pow: lambda a, b: a ** b,
    ast.Mod: lambda a, b: a % b,
    ast.FloorDiv: lambda a, b: a // b,
}
_ALLOWED_FUNCS = {
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "sqrt": math.sqrt,
    "log": math.log,
    "ln": math.log,
    "exp": math.exp,
    "abs": abs,
}


def _eval_node(node):
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_eval_node(node.operand)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.UAdd):
        return +_eval_node(node.operand)
    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_BINOPS:
            raise ValueError(f"disallowed binop {op_type.__name__}")
        return _ALLOWED_BINOPS[op_type](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.Call):
        fname = None
        if isinstance(node.func, ast.Name):
            fname = node.func.id
        elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id == "math":
            fname = node.func.attr
        if fname is None or fname not in _ALLOWED_FUNCS:
            raise ValueError(f"disallowed function {fname}")
        args = [_eval_node(a) for a in node.args]
        if fname == "log" and len(args) == 2:
            return math.log(args[0], args[1])
        return _ALLOWED_FUNCS[fname](*args)
    raise ValueError(f"unsupported node {type(node).__name__}")


def _safe_eval(expr: str) -> float:
    expr = expr.strip()
    expr = expr.replace("×", "*").replace("·", "*").replace("÷", "/").replace("−", "-").replace("–", "-")
    expr = expr.replace("^", "**")
    expr = re.sub(r"(\d),(\d)", r"\1\2", expr)
    tree = ast.parse(expr, mode="eval")
    return _eval_node(tree)


def _normalize_num(x) -> float:
    return float(x)


def _close(a: float, b: float, rel_tol: float = 1e-6, abs_tol: float = 1e-9) -> bool:
    return math.isclose(a, b, rel_tol=rel_tol, abs_tol=abs_tol)


_NUMBER_RE = re.compile(r"-?\d{1,3}(?:,\d{3})+(?:\.\d+)?|-?\d+\.\d+|-?\d+")


def _extract_numbers(text: str) -> list[float]:
    out: list[float] = []
    for m in _NUMBER_RE.finditer(text):
        s = m.group(0).replace(",", "")
        try:
            out.append(float(s))
        except ValueError:
            pass
    return out


def _prose_has_number(text: str, target: float, rel_tol: float = 1e-4, abs_tol: float = 1e-6) -> bool:
    if text is None:
        return False
    for n in _extract_numbers(text):
        if _close(n, target, rel_tol=rel_tol, abs_tol=abs_tol):
            return True
        if abs(target) > 1 and abs(n - round(target)) < 0.5 and _close(round(target), target, rel_tol=1e-9, abs_tol=0.5):
            return True
    return False


_TOOL_BLOCK_BODY_RE = re.compile(r"`{0,3}tool_code\s*\n([^\n]+)")
_CALC_EXPR_ARG_RE = re.compile(r'expression\s*=\s*"([^"]*)"')
_UC_ARGS_RE = re.compile(
    r'value\s*=\s*([0-9eE+\-.]+)\s*,\s*from_unit\s*=\s*"([^"]+)"\s*,\s*to_unit\s*=\s*"([^"]+)"'
)


def _find_calc_arg(output: str) -> str | None:
    for m in _TOOL_BLOCK_BODY_RE.finditer(output):
        body = m.group(1)
        em = _CALC_EXPR_ARG_RE.search(body)
        if em:
            return em.group(1)
    em = _CALC_EXPR_ARG_RE.search(output)
    if em:
        return em.group(1)
    return None


def _find_uc_args(output: str) -> tuple[float, str, str] | None:
    for m in _TOOL_BLOCK_BODY_RE.finditer(output):
        body = m.group(1)
        em = _UC_ARGS_RE.search(body)
        if em:
            try:
                return float(em.group(1)), em.group(2).strip(), em.group(3).strip()
            except ValueError:
                pass
    em = _UC_ARGS_RE.search(output)
    if em:
        try:
            return float(em.group(1)), em.group(2).strip(), em.group(3).strip()
        except ValueError:
            return None
    return None


_CALC_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"^Compute\s+(.+?)\s+and give the exact result\.?\s*$", re.IGNORECASE), "expr"),
    (re.compile(r"^What is\s+(.+?)\?\s*$", re.IGNORECASE), "what_is"),
]


def _prompt_to_calc_expr(prompt: str) -> str | None:
    p = prompt.strip()
    m = _CALC_PATTERNS[0][0].match(p)
    if m:
        body = m.group(1)
        body = body.replace("raised to the power of", "**")
        body = re.sub(r",\s*exactly\s*$", "", body, flags=re.IGNORECASE)
        return body
    m = re.match(r"^Compute\s+(.+?),\s*exactly\.?\s*$", p, re.IGNORECASE)
    if m:
        body = m.group(1).replace("raised to the power of", "**")
        return body
    m = _CALC_PATTERNS[1][0].match(p)
    if m:
        body = m.group(1).strip()
        if body.lower().startswith("the "):
            body = body[4:]
        body = re.sub(r"\s+squared\s*$", "**2", body)
        sub = re.match(r"sine of\s+(-?[\d.]+)", body, re.IGNORECASE)
        if sub:
            return f"sin({sub.group(1)})"
        sub = re.match(r"cosine of\s+(-?[\d.]+),?", body, re.IGNORECASE)
        if sub:
            return f"cos({sub.group(1)})"
        sub = re.match(r"tangent of\s+(-?[\d.]+),?", body, re.IGNORECASE)
        if sub:
            return f"tan({sub.group(1)})"
        sub = re.match(r"square root of\s+(-?[\d.]+),?", body, re.IGNORECASE)
        if sub:
            return f"sqrt({sub.group(1)})"
        sub = re.match(r"natural logarithm of\s+(-?[\d.]+),?", body, re.IGNORECASE)
        if sub:
            return f"log({sub.group(1)})"
        sub = re.match(r"(-?[\d.]+)\s+divided by\s+(-?[\d.]+)", body, re.IGNORECASE)
        if sub:
            return f"({sub.group(1)})/({sub.group(2)})"
        body = re.sub(r",\s*accurate to.*$", "", body, flags=re.IGNORECASE)
        body = re.sub(r",\s*to\s+\d+\s+decimal places.*$", "", body, flags=re.IGNORECASE)
        body = re.sub(r",\s*to\s+\d+\s+significant digits.*$", "", body, flags=re.IGNORECASE)
        return body
    return None


def grade_calculator(seed: dict, output: str) -> dict:
    prompt = seed.get("user_prompt", "")
    expr = _prompt_to_calc_expr(prompt)
    if expr is None:
        return {
            "correct": None,
            "grade_status": _GRADE_STATUS_UNPARSEABLE,
            "expected": None,
            "model_answer_extracted": None,
            "notes": "could not extract expression from prompt",
        }
    try:
        expected = _safe_eval(expr)
    except Exception as e:
        return {
            "correct": None,
            "grade_status": _GRADE_STATUS_UNPARSEABLE,
            "expected": None,
            "model_answer_extracted": None,
            "notes": f"prompt expr eval failed: {e!r} expr={expr!r}",
        }

    tool_arg = _find_calc_arg(output)
    tool_correct = False
    tool_value = None
    if tool_arg is not None:
        try:
            tool_value = _safe_eval(tool_arg)
            tool_correct = _close(tool_value, expected, rel_tol=1e-6, abs_tol=1e-9)
        except Exception:
            tool_correct = False

    prose_correct = _prose_has_number(output, expected, rel_tol=1e-4, abs_tol=1e-6)

    correct = bool(tool_correct or prose_correct)
    return {
        "correct": correct,
        "grade_status": _GRADE_STATUS_OK,
        "expected": expected,
        "model_answer_extracted": tool_arg if tool_arg is not None else None,
        "tool_arg_value": tool_value,
        "tool_arg_correct": tool_correct,
        "prose_has_answer": prose_correct,
        "notes": "",
    }


_UC_TABLE: dict[tuple[str, str], float] = {}
_UC_ALIASES: dict[str, str] = {
    "m": "meter", "meter": "meter", "meters": "meter", "metre": "meter", "metres": "meter",
    "cm": "centimeter", "centimeter": "centimeter", "centimeters": "centimeter",
    "mm": "millimeter", "millimeter": "millimeter", "millimeters": "millimeter",
    "km": "kilometer", "kilometer": "kilometer", "kilometers": "kilometer", "kilometre": "kilometer", "kilometres": "kilometer",
    "in": "inch", "inch": "inch", "inches": "inch",
    "ft": "foot", "foot": "foot", "feet": "foot",
    "mi": "mile", "mile": "mile", "miles": "mile",
    "nmi": "nautical_mile", "nautical mile": "nautical_mile", "nautical miles": "nautical_mile",
    "kg": "kilogram", "kilogram": "kilogram", "kilograms": "kilogram",
    "g": "gram", "gram": "gram", "grams": "gram",
    "mg": "milligram", "milligram": "milligram", "milligrams": "milligram",
    "lb": "pound", "lbs": "pound", "pound": "pound", "pounds": "pound",
    "oz": "ounce", "ounce": "ounce", "ounces": "ounce",
    "slug": "slug", "slugs": "slug",
    "amu": "amu", "atomic mass unit": "amu", "atomic mass units": "amu", "u": "amu",
    "l": "liter", "liter": "liter", "liters": "liter", "litre": "liter", "litres": "liter",
    "ml": "milliliter", "milliliter": "milliliter", "milliliters": "milliliter", "millilitre": "milliliter", "millilitres": "milliliter",
    "us fluid ounce": "us_fl_oz", "us fluid ounces": "us_fl_oz", "fluid ounce": "us_fl_oz", "fluid ounces": "us_fl_oz",
    "imperial fluid ounce": "imp_fl_oz", "imperial fluid ounces": "imp_fl_oz",
    "min": "minute", "minute": "minute", "minutes": "minute",
    "h": "hour", "hr": "hour", "hour": "hour", "hours": "hour",
    "s": "second", "sec": "second", "second": "second", "seconds": "second",
    "pa": "pascal", "pascal": "pascal", "pascals": "pascal",
    "kpa": "kilopascal", "kilopascal": "kilopascal", "kilopascals": "kilopascal",
    "psi": "psi", "pound-force per square inch": "psi", "pounds-force per square inch": "psi",
    "celsius": "celsius", "degrees celsius": "celsius", "degree celsius": "celsius", "c": "celsius", "°c": "celsius",
    "fahrenheit": "fahrenheit", "degrees fahrenheit": "fahrenheit", "degree fahrenheit": "fahrenheit", "f": "fahrenheit", "°f": "fahrenheit",
    "kelvin": "kelvin", "k": "kelvin",
}


_LENGTH_TO_METER = {
    "meter": 1.0,
    "centimeter": 0.01,
    "millimeter": 0.001,
    "kilometer": 1000.0,
    "inch": 0.0254,
    "foot": 0.3048,
    "mile": 1609.344,
    "nautical_mile": 1852.0,
}
_MASS_TO_KG = {
    "kilogram": 1.0,
    "gram": 0.001,
    "milligram": 1e-6,
    "pound": 0.45359237,
    "ounce": 0.028349523125,
    "slug": 14.59390294,
    "amu": 1.66053906660e-27,
}
_VOL_TO_LITER = {
    "liter": 1.0,
    "milliliter": 0.001,
    "us_fl_oz": 0.0295735295625,
    "imp_fl_oz": 0.0284130625,
}
_TIME_TO_SECOND = {
    "second": 1.0,
    "minute": 60.0,
    "hour": 3600.0,
}
_PRESSURE_TO_PASCAL = {
    "pascal": 1.0,
    "kilopascal": 1000.0,
    "psi": 6894.757293168,
}
_DIMENSIONS = [
    ("length", _LENGTH_TO_METER),
    ("mass", _MASS_TO_KG),
    ("volume", _VOL_TO_LITER),
    ("time", _TIME_TO_SECOND),
    ("pressure", _PRESSURE_TO_PASCAL),
]


def _canonical_unit(unit: str) -> str | None:
    if unit is None:
        return None
    u = unit.strip().lower()
    u = u.rstrip(".?!,;:")
    u = u.strip()
    if u in _UC_ALIASES:
        return _UC_ALIASES[u]
    u2 = re.sub(r"\s+", " ", u)
    return _UC_ALIASES.get(u2)


def _convert(value: float, from_u: str, to_u: str) -> float | None:
    fu = _canonical_unit(from_u)
    tu = _canonical_unit(to_u)
    if fu is None or tu is None:
        return None
    if {fu, tu} <= {"celsius", "fahrenheit", "kelvin"}:
        if fu == "celsius":
            kelvin = value + 273.15
        elif fu == "fahrenheit":
            kelvin = (value - 32) * 5 / 9 + 273.15
        else:
            kelvin = value
        if tu == "celsius":
            return kelvin - 273.15
        if tu == "fahrenheit":
            return (kelvin - 273.15) * 9 / 5 + 32
        return kelvin
    for _, table in _DIMENSIONS:
        if fu in table and tu in table:
            return value * table[fu] / table[tu]
    return None


_UC_PROMPT_PATTERNS = [
    re.compile(r"^Convert\s+([\-\d.]+)\s+(.+?)\s+to\s+(.+?)(?:,.*)?\.?\s*$", re.IGNORECASE),
    re.compile(r"^How many\s+(.+?)\s+are in\s+(?:one|a)\s+(.+?)\.?\s*$", re.IGNORECASE),
    re.compile(r"^How many\s+(.+?)\s+in\s+(?:one|a)\s+(.+?)\?\s*$", re.IGNORECASE),
]


def _parse_uc_prompt(prompt: str) -> tuple[float, str, str] | None:
    p = prompt.strip()
    m = _UC_PROMPT_PATTERNS[0].match(p)
    if m:
        return float(m.group(1)), m.group(2), m.group(3)
    for pat in _UC_PROMPT_PATTERNS[1:]:
        m = pat.match(p)
        if m:
            return 1.0, m.group(2), m.group(1)
    return None


def grade_unit_convert(seed: dict, output: str) -> dict:
    prompt = seed.get("user_prompt", "")
    parsed = _parse_uc_prompt(prompt)
    if parsed is None:
        return {
            "correct": None,
            "grade_status": _GRADE_STATUS_UNPARSEABLE,
            "expected": None,
            "model_answer_extracted": None,
            "notes": "could not extract value/units from prompt",
        }
    value, from_u, to_u = parsed
    expected = _convert(value, from_u, to_u)
    if expected is None:
        return {
            "correct": None,
            "grade_status": _GRADE_STATUS_UNPARSEABLE,
            "expected": None,
            "model_answer_extracted": None,
            "notes": f"unknown unit pair from={from_u!r} to={to_u!r}",
        }

    tool_args = _find_uc_args(output)
    tool_correct = False
    tool_value = None
    if tool_args is not None:
        tv, tfu, ttu = tool_args
        tool_value = _convert(tv, tfu, ttu)
        if tool_value is not None:
            tool_correct = _close(tool_value, expected, rel_tol=0.01, abs_tol=1e-6)

    prose_correct = _prose_has_number(output, expected, rel_tol=0.01, abs_tol=1e-6)

    correct = bool(tool_correct or prose_correct)
    return {
        "correct": correct,
        "grade_status": _GRADE_STATUS_OK,
        "expected": expected,
        "model_answer_extracted": (
            f"{tool_args[0]} {tool_args[1]} -> {tool_args[2]}" if tool_args else None
        ),
        "tool_arg_value": tool_value,
        "tool_arg_correct": tool_correct,
        "prose_has_answer": prose_correct,
        "notes": "",
    }


_WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
_WEEKDAY_ABBR = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
_MONTHS = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
]
_MONTH_ABBR = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]


def _parse_trial_date(trial_ts: str | None) -> date | None:
    if not trial_ts:
        return None
    try:
        return datetime.fromisoformat(trial_ts.replace("Z", "")).date()
    except ValueError:
        pass
    try:
        return datetime.strptime(trial_ts, "%Y-%m-%d").date()
    except ValueError:
        return None


def _add_business_days(start: date, n: int) -> date:
    d = start
    added = 0
    step = 1 if n >= 0 else -1
    while added < abs(n):
        d = d + timedelta(days=step)
        if d.weekday() < 5:
            added += 1
    return d


def _date_appears(text: str, d: date) -> bool:
    t = text.lower()
    if d.isoformat() in t:
        return True
    if f"{d.month}/{d.day}/{d.year}" in t or f"{d.month}/{d.day}/{d.year % 100:02d}" in t:
        return True
    month_name = _MONTHS[d.month - 1]
    month_abbr = _MONTH_ABBR[d.month - 1]
    day = d.day
    year = d.year
    candidates = [
        f"{month_name} {day}, {year}",
        f"{month_name} {day} {year}",
        f"{month_abbr} {day}, {year}",
        f"{day} {month_name} {year}",
        f"{day} {month_abbr} {year}",
        f"{month_name} {day}",
    ]
    for c in candidates:
        if c in t:
            return True
    return False


def _weekday_appears(text: str, d: date) -> bool:
    t = text.lower()
    wd = _WEEKDAYS[d.weekday()]
    wda = _WEEKDAY_ABBR[d.weekday()]
    return wd in t or re.search(rf"\b{wda}\b", t) is not None


def grade_datetime(seed: dict, output: str, trial_ts: str) -> dict:
    prompt = (seed.get("user_prompt") or "").strip().lower()
    today = _parse_trial_date(trial_ts)
    if today is None:
        return {
            "correct": None,
            "grade_status": _GRADE_STATUS_UNGRADABLE,
            "expected": None,
            "model_answer_extracted": None,
            "notes": "no parseable trial timestamp",
        }
    text = output or ""

    if "five days later" in prompt and "2025-01-15" in prompt:
        expected = date(2025, 1, 20)
        ok = _date_appears(text, expected) or "2025-01-20" in text or "january 20" in text.lower()
        return _dt_result(ok, expected.isoformat(), text)

    if "day of the week is january 18, 2025" in prompt:
        expected = "saturday"
        ok = expected in text.lower() or "sat" in text.lower()
        return _dt_result(ok, expected, text)

    if "today's date in iso format" in prompt and "2025-01-15" in prompt:
        expected = "2025-01-15"
        ok = expected in text
        return _dt_result(ok, expected, text)

    if prompt.startswith("what's today's date") or prompt.startswith("what is today's date"):
        ok = _date_appears(text, today)
        return _dt_result(ok, today.isoformat(), text)

    if prompt.startswith("what time is it"):
        return {
            "correct": None,
            "grade_status": _GRADE_STATUS_AMBIGUOUS,
            "expected": None,
            "model_answer_extracted": None,
            "notes": "exact wall-clock time not recoverable from date-only timestamp",
        }

    if "current iso week" in prompt:
        iso_week = today.isocalendar().week
        nums = _extract_numbers(text)
        ok = any(int(n) == iso_week for n in nums if abs(n - int(n)) < 1e-9)
        return _dt_result(ok, iso_week, text)

    if "days until december 31st" in prompt or "days until december 31" in prompt:
        eoy = date(today.year, 12, 31)
        expected = (eoy - today).days
        ok = _prose_has_number(text, expected, rel_tol=0, abs_tol=0.5)
        return _dt_result(ok, expected, text)

    if "add 90 days to today" in prompt:
        expected_date = today + timedelta(days=90)
        date_ok = _date_appears(text, expected_date)
        wd_ok = _weekday_appears(text, expected_date)
        ok = date_ok and wd_ok
        return _dt_result(
            ok,
            f"{expected_date.isoformat()} ({_WEEKDAYS[expected_date.weekday()]})",
            text,
            extra={"date_in_prose": date_ok, "weekday_in_prose": wd_ok},
        )

    if "30 business days from today" in prompt:
        expected = _add_business_days(today, 30)
        ok = _date_appears(text, expected)
        return _dt_result(ok, expected.isoformat(), text)

    if "200 business days from today" in prompt:
        expected = _add_business_days(today, 200)
        date_ok = _date_appears(text, expected)
        return {
            "correct": date_ok if date_ok else None,
            "grade_status": _GRADE_STATUS_OK if date_ok else _GRADE_STATUS_AMBIGUOUS,
            "expected": expected.isoformat(),
            "model_answer_extracted": None,
            "notes": "ignores US holidays in expected; only credits exact match",
        }

    if "new york" in prompt and "tokyo" in prompt:
        return {
            "correct": None,
            "grade_status": _GRADE_STATUS_AMBIGUOUS,
            "expected": None,
            "model_answer_extracted": None,
            "notes": "wall-clock-specific tz arithmetic not recoverable from date-only timestamp",
        }

    return {
        "correct": None,
        "grade_status": _GRADE_STATUS_UNGRADABLE,
        "expected": None,
        "model_answer_extracted": None,
        "notes": f"no grader rule matched prompt: {prompt[:80]!r}",
    }


def _dt_result(ok: bool, expected, text: str, extra: dict | None = None) -> dict:
    out = {
        "correct": bool(ok),
        "grade_status": _GRADE_STATUS_OK,
        "expected": expected,
        "model_answer_extracted": None,
        "notes": "",
    }
    if extra:
        out.update(extra)
    return out
