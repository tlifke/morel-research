"""unit_convert — convert numeric quantities between units.

A small unit table covering the dimensions the A1 seed corpus exercises
(mass, length, volume, temperature). Extend the table as the corpus
grows. Returns a string for consistency with the palette signature.
"""

from __future__ import annotations

# Factor-to-base for each unit. Base units chosen arbitrarily but
# consistently within each dimension.
_BASE_FACTORS = {
    # mass (base: kg)
    "kg": 1.0,
    "g": 0.001,
    "mg": 1e-6,
    "lb": 0.45359237,
    "pound": 0.45359237,
    "pounds": 0.45359237,
    "oz": 0.028349523125,
    # length (base: m)
    "m": 1.0,
    "meter": 1.0,
    "meters": 1.0,
    "cm": 0.01,
    "mm": 0.001,
    "km": 1000.0,
    "in": 0.0254,
    "inch": 0.0254,
    "inches": 0.0254,
    "ft": 0.3048,
    "feet": 0.3048,
    "mi": 1609.344,
    # volume (base: L)
    "l": 1.0,
    "liter": 1.0,
    "liters": 1.0,
    "ml": 0.001,
    "milliliter": 0.001,
    "milliliters": 0.001,
    "fl_oz": 0.0295735295625,
    "fluid_ounce": 0.0295735295625,
    "fluid_ounces": 0.0295735295625,
    "us_fl_oz": 0.0295735295625,
    "gal": 3.785411784,
    "gallon": 3.785411784,
}

# Dimension classification — only same-dimension conversions are valid.
_DIMENSIONS = {
    "mass": {"kg", "g", "mg", "lb", "pound", "pounds", "oz"},
    "length": {"m", "meter", "meters", "cm", "mm", "km", "in", "inch", "inches",
               "ft", "feet", "mi"},
    "volume": {"l", "liter", "liters", "ml", "milliliter", "milliliters",
               "fl_oz", "fluid_ounce", "fluid_ounces", "us_fl_oz", "gal",
               "gallon"},
}

_TEMP_UNITS = {"c", "celsius", "f", "fahrenheit", "k", "kelvin"}


def _dimension(unit: str) -> str | None:
    for dim, members in _DIMENSIONS.items():
        if unit in members:
            return dim
    return None


def _normalize(unit: str) -> str:
    return unit.strip().lower().replace(" ", "_").replace("°", "")


def _convert_temperature(value: float, src: str, dst: str) -> float:
    src, dst = src[0], dst[0]
    if src == "c":
        k = value + 273.15
    elif src == "f":
        k = (value - 32) * 5 / 9 + 273.15
    elif src == "k":
        k = value
    else:
        raise ValueError(f"unknown temp unit: {src}")
    if dst == "c":
        return k - 273.15
    if dst == "f":
        return (k - 273.15) * 9 / 5 + 32
    if dst == "k":
        return k
    raise ValueError(f"unknown temp unit: {dst}")


def unit_convert(value: float, from_unit: str, to_unit: str) -> str:
    src = _normalize(from_unit)
    dst = _normalize(to_unit)

    if src in _TEMP_UNITS and dst in _TEMP_UNITS:
        return str(_convert_temperature(value, src, dst))

    src_dim = _dimension(src)
    dst_dim = _dimension(dst)
    if src_dim is None or dst_dim is None:
        raise ValueError(f"unknown unit: {from_unit!r} or {to_unit!r}")
    if src_dim != dst_dim:
        raise ValueError(
            f"incompatible dimensions: {from_unit} ({src_dim}) → "
            f"{to_unit} ({dst_dim})"
        )
    base = value * _BASE_FACTORS[src]
    converted = base / _BASE_FACTORS[dst]
    return str(converted)
