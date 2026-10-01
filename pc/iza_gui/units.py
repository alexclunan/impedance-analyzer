"""units.py — Qt-free parsing and formatting of frequencies with SI suffixes.

Shared by the tone frequency boxes and the Rec-rate field so both accept the
same syntax: '750000', '500k', '500 kHz', '1.5M', '1.5 MHz', '2e6'.  Matching
is case-insensitive, a bare number is Hz, and 'm' means mega (milli has no
meaning for these fields).
"""

import re
from decimal import Decimal, Overflow, localcontext

# Decimal so '1.0125 MHz' is exactly 1012500 Hz, not 1012500.0000000001
_SCALE = {"": Decimal(1), "k": Decimal(10**3), "m": Decimal(10**6),
          "g": Decimal(10**9)}
_NUM = r"(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?"

# These are matched against stripped text and never put two '\s*' side by
# side: adjacent '\s*' backtrack polynomially on a long run of spaces followed
# by a bad character, which would freeze the GUI thread inside validate().
# a complete entry: number, optional k/M/G, optional 'Hz'
_FULL = re.compile(r"^(" + _NUM + r")\s*(?:([kmg])\s*)?(?:hz)?$", re.I)
# the first number (+ optional prefix) anywhere, e.g. in '100 kHz  (÷2)'
_ANY = re.compile(r"(" + _NUM + r")\s*([kmg]?)", re.I)
# a prefix of a complete entry, i.e. still being typed: '', '1.', '2e', '5 kH'
_PARTIAL = re.compile(r"^(?:\d+(?:\.\d*)?|\.\d*)?(?:e[+-]?\d*)?\s*(?:[kmg]\s*)?(?:hz?)?$",
                      re.I)


def _to_hz(num, prefix):
    # Never raise: an absurd exponent ('1e9999999') becomes inf, which every
    # caller already treats as out of range (clamped or capped).
    try:
        with localcontext() as ctx:
            ctx.traps[Overflow] = False
            return float(Decimal(num) * _SCALE[prefix.lower()])
    except ArithmeticError:            # exponent too large to even represent
        mant, _, exp = num.lower().partition("e")
        if not mant.strip("0."):       # zero stays zero at any exponent
            return 0.0
        return 0.0 if exp.startswith("-") else float("inf")


def parse_hz(text):
    """The whole of `text` as a frequency in Hz, or None if it isn't one."""
    m = _FULL.match(text.strip())
    return _to_hz(m.group(1), m.group(2) or "") if m else None


def search_hz(text):
    """The first frequency found anywhere in `text`, in Hz, or None."""
    m = _ANY.search(text)
    return _to_hz(m.group(1), m.group(2)) if m else None


def is_partial_hz(text):
    """True if `text` could still become a valid entry with more typing."""
    return bool(_PARTIAL.match(text.strip()))


def format_hz(hz, decimals=0):
    """Hz -> '750 Hz', '500 kHz', '1.0125 MHz', dropping trailing zeros.

    `decimals` is the Hz resolution to keep (0 = whole Hz), so the text always
    round-trips through parse_hz to the same value at that resolution."""
    hz = round(hz, decimals)
    a = abs(hz)
    if a >= 1e6:
        scale, unit, d = 1e6, "MHz", decimals + 6
    elif a >= 1e3:
        scale, unit, d = 1e3, "kHz", decimals + 3
    else:
        scale, unit, d = 1.0, "Hz", decimals
    s = f"{hz / scale:.{d}f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return f"{s} {unit}"
