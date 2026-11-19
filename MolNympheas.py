'''
==============================================================================
MolNympheas: A Smart Color Palette Picker for ChimeraX & PyMOL
==============================================================================

DESCRIPTION
    MolNympheas is a universal plugin designed to bring mathematically "perfect"
    palettes to your structural biology figures.
    Named in honor of Claude Monet's "Nymphéas" (Water Lilies), this tool
    uses Matplotlib to generate perceptually uniform colors (Viridis, Magma,
    etc.) and automatically calculates harmonious color schemes.
    It automatically detects whether it is running inside PyMOL or ChimeraX
    and adapts its commands accordingly.

FEATURES
    - Universal Environment Detection (PyMOL / ChimeraX). (Thanks To Florian Chenavier)
    - Four tabs:
        Colormaps : every Matplotlib colormap (+ cmcrameri / cmocean if installed),
                    grouped, searchable, with gradient previews, reverse and range.
        Harmony   : 33 rules in 4 families, hue wheel, perceptual (OKLCH) engine.
        Custom    : free-form palette, edited colour by colour.
        Render    : PyMeraX one-click rendering presets (PyMOL only).
    - Compact colour tiles: click to apply, hover for Copy / Edit / More,
      right-click for every action, label showing where each colour was applied.
    - Colour-vision check (Machado 2009 simulation) and live contrast readout.
    - Undo/Redo per tab, JSON / ASE / PyMOL / ChimeraX export.

USAGE
    In ChimeraX: open /path/to/MolNympheas-v6.py
    In PyMOL:    run /path/to/MolNympheas-v6.py
    (Matplotlib is recommended: pip install matplotlib. Without it, a small
     built-in set of colormaps is used.)

INSPIRATION
    Initially inspired by the `pymol_viridis` script by Shyam Saladi.
    Orsay Museum Paris for the fantastic collections.

VERSIONING:

03-03-2026: v3.0.0
    One script to rule them all !! ChimeraX and PyMol.

13-03-2026: V3.1.0
    Added Color picker for the main color, gradient generator.

22-06-2026: V4.0.0 (The "Universal Workspace" Update)
    - Refactored into three independent workspaces (Matplotlib/Harmony/Custom).
    - Added automated Color Clash Detection (Delta-E math) in CVD Matrix.
    - Added Okabe-Ito colorblind-safe preset.
    - Added Smart-Paste functionality for Hex codes.
    - Fixed UI rendering for macOS and cross-platform Qt compatibility.
    - Added Illustrator palette export .ase

04-07-2026: V5.0.0 (The PyMeraX Integration)
    - Integrated the PyMeraX engine to bring ChimeraX-like rendering directly into PyMOL.
    - Added a dynamic "Tab D: PyMeraX" that exclusively loads in PyMOL or Standalone modes.
    - Included 1-click GUI buttons for Cartoon, Surface, Publication, and Ligand rendering presets.

19-11-2026: V6.0.0 (The "Water Lily" Redesign)
    - New light, flat, compact interface with one global stylesheet.
    - Colormaps: all Matplotlib maps grouped by family (incl. berlin, managua, vanimo),
      cmcrameri / cmocean when installed, search field, gradient previews,
      reverse toggle and range slider.
    - Harmony: 33 rules in 4 families (wheel, light & shade, mood, for structures),
      draggable hue wheel, spread / variation / lightness / vibrance, perceptual
      OKLCH or classic HSV engine, 4 orderings, "Vary", presets.
    - Compact tiles with hover actions, right-click menu, keyboard control and
      a label showing which target each colour was applied to.
    - Status bar with exact commands, live contrast readout, colour-vision popup.
    - Help panel for each tab. Exports to PyMOL (.pml) and ChimeraX (.cxc) scripts.
==============================================================================
'''
import sys
import json
import math
import random
import struct
import importlib

# ==========================================
# ENVIRONMENT DETECTION
# ==========================================
ENV = "standalone"
try:
    import pymol
    from pymol import cmd
    ENV = "pymol"
except ImportError:
    pass

try:
    from chimerax.core.commands import run
    ENV = "chimerax"
except ImportError:
    pass

# ==========================================
# QT IMPORT (pymol.Qt / PyQt5 / PyQt6)
# ==========================================
QtCore = QtGui = QtWidgets = None
if ENV == "pymol":
    try:
        from pymol.Qt import QtCore, QtGui, QtWidgets
    except Exception:
        QtWidgets = None
if QtWidgets is None:
    _order = ["PyQt6", "PyQt5"] if ENV == "chimerax" else ["PyQt5", "PyQt6"]
    for _pkg in _order:
        try:
            QtCore = importlib.import_module(_pkg + ".QtCore")
            QtGui = importlib.import_module(_pkg + ".QtGui")
            QtWidgets = importlib.import_module(_pkg + ".QtWidgets")
            break
        except ImportError:
            QtWidgets = None
    if QtWidgets is None:
        raise ImportError("MolNympheas Error: neither PyQt5 nor PyQt6 was found.")

QtSvg = None
try:
    QtSvg = importlib.import_module(QtCore.__name__.split(".")[0] + ".QtSvg")
except Exception:
    QtSvg = None

Qt = QtCore.Qt
Signal = getattr(QtCore, "pyqtSignal", None) or getattr(QtCore, "Signal")
QShortcut = getattr(QtGui, "QShortcut", None) or getattr(QtWidgets, "QShortcut")


def _e(owner, scope, name):
    """Enum lookup that works with both scoped (Qt6) and flat (Qt5) enums."""
    sc = getattr(owner, scope, None)
    if sc is not None and hasattr(sc, name):
        return getattr(sc, name)
    return getattr(owner, name)


def _exec(obj, *args):
    fn = getattr(obj, "exec_", None) or getattr(obj, "exec")
    return fn(*args)


def _pos(ev):
    return ev.position().toPoint() if hasattr(ev, "position") else ev.pos()


AlignCenter = _e(Qt, "AlignmentFlag", "AlignCenter")
AlignLeft = _e(Qt, "AlignmentFlag", "AlignLeft")
AlignRight = _e(Qt, "AlignmentFlag", "AlignRight")
AlignVCenter = _e(Qt, "AlignmentFlag", "AlignVCenter")
AlignTop = _e(Qt, "AlignmentFlag", "AlignTop")
AlignBottom = _e(Qt, "AlignmentFlag", "AlignBottom")
PointingHand = _e(Qt, "CursorShape", "PointingHandCursor")
OpenHand = _e(Qt, "CursorShape", "OpenHandCursor")
ClosedHand = _e(Qt, "CursorShape", "ClosedHandCursor")
LeftButton = _e(Qt, "MouseButton", "LeftButton")
StrongFocus = _e(Qt, "FocusPolicy", "StrongFocus")
NoFocus = _e(Qt, "FocusPolicy", "NoFocus")
Horizontal = _e(Qt, "Orientation", "Horizontal")
NoPen = _e(Qt, "PenStyle", "NoPen")
NoBrush = _e(Qt, "BrushStyle", "NoBrush")
RoundCap = _e(Qt, "PenCapStyle", "RoundCap")
ElideRight = _e(Qt, "TextElideMode", "ElideRight")
Transparent = _e(Qt, "GlobalColor", "transparent")
UserRole = _e(Qt, "ItemDataRole", "UserRole")
NoItemFlags = _e(Qt, "ItemFlag", "NoItemFlags")
PopupFlag = _e(Qt, "WindowType", "Popup")
TransparentForMouse = _e(Qt, "WidgetAttribute", "WA_TransparentForMouseEvents")
ScrollOff = _e(Qt, "ScrollBarPolicy", "ScrollBarAlwaysOff")
ShiftMod = _e(Qt, "KeyboardModifier", "ShiftModifier")
CtrlMod = _e(Qt, "KeyboardModifier", "ControlModifier")
MetaMod = _e(Qt, "KeyboardModifier", "MetaModifier")
K = lambda n: _e(Qt, "Key", n)
Antialias = _e(QtGui.QPainter, "RenderHint", "Antialiasing")
SmoothPix = _e(QtGui.QPainter, "RenderHint", "SmoothPixmapTransform")
FixedFont = _e(QtGui.QFontDatabase, "SystemFont", "FixedFont")
StateSelected = _e(QtWidgets.QStyle, "StateFlag", "State_Selected")
StateHover = _e(QtWidgets.QStyle, "StateFlag", "State_MouseOver")
IconNormal = _e(QtGui.QIcon, "Mode", "Normal")
IconActive = _e(QtGui.QIcon, "Mode", "Active")
IconDisabled = _e(QtGui.QIcon, "Mode", "Disabled")
SPExpanding = _e(QtWidgets.QSizePolicy, "Policy", "Expanding")
SPPreferred = _e(QtWidgets.QSizePolicy, "Policy", "Preferred")
SPFixed = _e(QtWidgets.QSizePolicy, "Policy", "Fixed")
ScrollPerPixel = _e(QtWidgets.QAbstractItemView, "ScrollMode", "ScrollPerPixel")
AbsSpacing = _e(QtGui.QFont, "SpacingType", "AbsoluteSpacing")
WDemi = _e(QtGui.QFont, "Weight", "DemiBold")
WMedium = _e(QtGui.QFont, "Weight", "Medium")
QRectF, QPointF, QSize, QPoint = QtCore.QRectF, QtCore.QPointF, QtCore.QSize, QtCore.QPoint

# ==========================================
# MATPLOTLIB (optional)
# ==========================================
HAS_MATPLOTLIB = False
try:
    import matplotlib
    try:
        matplotlib.use("Agg")
    except Exception:
        pass
    import matplotlib.colors as mcolors
    HAS_MATPLOTLIB = True
except Exception as _err:
    print(f"MolNympheas Warning: Matplotlib disabled, using built-in colormaps. Reason: {_err}")

for _extra in ("cmcrameri.cm", "cmocean"):
    if HAS_MATPLOTLIB:
        try:
            importlib.import_module(_extra)
        except Exception:
            pass

# ==========================================
# DESIGN TOKENS
# ==========================================
WIN = "#FFFFFF"
SURFACE = "#F2EFF7"
LINE = "#E6E1EE"
INK = "#1F1B2D"
MUTED = "#6E6883"
ACCENT = "#D63F79"
ACCENT_SOFT = "#FBE6EE"
OK = "#178A5B"
WARN = "#B07800"
BAD = "#C93636"

QSS = f"""
QMainWindow#mnRoot, QFrame#mnCentral, QScrollArea#mnScroll, QWidget#mnBody {{ background:{WIN}; }}
QFrame#mnCentral QLabel {{ color:{INK}; background:transparent; }}
QLabel[cls="lbl"] {{ color:{MUTED}; font-size:10px; font-weight:600; }}
QLabel[cls="hint"], QLabel[cls="cap"] {{ color:{MUTED}; }}
QLabel[cls="cap"] {{ font-size:11px; }}
QLabel[cls="env"] {{ color:{MUTED}; background:{SURFACE}; border-radius:9px; padding:2px 9px; font-size:11px; }}
QLabel[cls="metric"] {{ background:{SURFACE}; border-radius:10px; padding:3px 9px; font-size:11px; }}
QLabel[cls="msg"] {{ color:{MUTED}; font-size:12px; }}
QLabel[cls="val"] {{ font-size:11px; }}
QToolButton[cls="ib"] {{ border:0; border-radius:8px; padding:5px; background:transparent; }}
QToolButton[cls="ib"]:hover {{ background:{SURFACE}; }}
QToolButton[cls="ib"]:checked {{ background:{ACCENT_SOFT}; }}
QToolButton[cls="ib"]::menu-indicator {{ image:none; width:0; }}
QPushButton[cls="btn"] {{ border:0; border-radius:8px; background:{SURFACE}; padding:6px 11px; color:{INK}; font-weight:500; }}
QPushButton[cls="btn"]:hover {{ background:{LINE}; }}
QFrame[cls="tabs"], QFrame[cls="seg"], QFrame[cls="stepper"], QFrame[cls="seedbox"] {{ background:{SURFACE}; border-radius:9px; }}
QPushButton[cls="tab"], QPushButton[cls="segb"] {{ border:0; border-radius:7px; padding:6px 10px; color:{MUTED}; background:transparent; font-weight:500; }}
QPushButton[cls="segb"] {{ padding:4px 10px; font-size:12px; }}
QPushButton[cls="tab"]:hover, QPushButton[cls="segb"]:hover {{ color:{INK}; }}
QPushButton[cls="tab"]:checked, QPushButton[cls="segb"]:checked {{ background:{WIN}; color:{INK}; }}
QPushButton[cls="chip"] {{ border:1px solid {LINE}; border-radius:12px; padding:3px 10px; background:transparent; color:{INK}; font-size:12px; }}
QPushButton[cls="chip"]:hover {{ border-color:{ACCENT}; }}
QPushButton[cls="link"] {{ border:0; background:transparent; color:{MUTED}; text-decoration:underline; font-size:12px; padding:2px 4px; }}
QPushButton[cls="link"]:hover {{ color:{INK}; }}
QPushButton[cls="card"] {{ border:1px solid transparent; border-radius:10px; background:{SURFACE}; text-align:left; padding:0; }}
QPushButton[cls="card"]:hover {{ border-color:{ACCENT}; }}
QPushButton[cls="swatch"] {{ border:0; border-radius:6px; }}
QLineEdit[cls="fld"], QComboBox[cls="fld"] {{ background:{SURFACE}; border:1px solid transparent; border-radius:8px; padding:4px 8px; color:{INK}; selection-background-color:{ACCENT}; min-height:20px; }}
QLineEdit[cls="fld"]:focus, QComboBox[cls="fld"]:focus {{ border-color:{ACCENT}; background:{WIN}; }}
QLineEdit[cls="seedhex"] {{ background:transparent; border:0; color:{INK}; padding:0 4px; }}
QLineEdit[cls="tileedit"] {{ background:{WIN}; border:1px solid {ACCENT}; border-radius:5px; color:{INK}; padding:0; }}
QComboBox[cls="fld"]::drop-down {{ border:0; width:24px; subcontrol-origin:padding; subcontrol-position:center right; }}
QComboBox QAbstractItemView {{ background:{WIN}; border:1px solid {LINE}; selection-background-color:{SURFACE}; selection-color:{INK}; color:{INK}; outline:0; }}
QSlider::groove:horizontal {{ height:4px; background:{LINE}; border-radius:2px; }}
QSlider::sub-page:horizontal {{ background:{ACCENT}; border-radius:2px; }}
QSlider::handle:horizontal {{ background:{WIN}; border:2px solid {ACCENT}; width:10px; height:10px; margin:-5px 0; border-radius:7px; }}
QSlider::sub-page:horizontal:disabled {{ background:{LINE}; }}
QSlider::handle:horizontal:disabled {{ border-color:{LINE}; }}
QFrame[cls="help"] {{ background:{ACCENT_SOFT}; border-radius:10px; }}
QFrame[cls="hline"] {{ background:{LINE}; max-height:1px; min-height:1px; }}
QFrame[cls="vline"] {{ background:{LINE}; max-width:1px; min-width:1px; }}
QFrame[cls="footer"] {{ border-top:1px solid {LINE}; background:{WIN}; }}
QFrame[cls="popup"] {{ background:{WIN}; border:1px solid {LINE}; border-radius:10px; }}
QFrame[cls="popup"] QLabel {{ color:{INK}; background:transparent; }}
QLineEdit[cls="search"] {{ border:0; border-bottom:1px solid {LINE}; background:{WIN}; padding:6px 8px; color:{INK}; }}
QLineEdit[cls="search"]:focus {{ border-bottom-color:{ACCENT}; }}
QListWidget {{ border:0; background:transparent; outline:0; }}
QMenu {{ background:{WIN}; border:1px solid {LINE}; border-radius:8px; padding:5px; color:{INK}; }}
QMenu::item {{ padding:6px 24px 6px 10px; border-radius:5px; }}
QMenu::item:selected {{ background:{SURFACE}; color:{INK}; }}
QMenu::item:disabled {{ color:{MUTED}; }}
QMenu::separator {{ height:1px; background:{LINE}; margin:4px 2px; }}
QToolTip {{ background:{INK}; color:{WIN}; border:0; padding:4px 6px; }}
QScrollBar:vertical {{ background:transparent; width:8px; margin:2px; }}
QScrollBar::handle:vertical {{ background:{LINE}; border-radius:3px; min-height:24px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
"""

# ==========================================
# COLOUR MATH
# ==========================================
def clamp(x, a, b):
    return max(a, min(b, x))


def wrap360(h):
    return h % 360.0


def norm_hex(text):
    """Accepts '#abc', 'abc', 'AABBCC', '0xAABBCC'. Returns '#AABBCC' or None."""
    if not text:
        return None
    v = text.strip()
    if v.lower().startswith("0x"):
        v = v[2:]
    v = v.lstrip("#")
    if len(v) == 3:
        v = "".join(c * 2 for c in v)
    if len(v) != 6 or any(c not in "0123456789abcdefABCDEF" for c in v):
        return None
    return "#" + v.upper()


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def rgb_to_hex(r, g, b):
    return "#{:02X}{:02X}{:02X}".format(*(int(round(clamp(v, 0, 1) * 255)) for v in (r, g, b)))


def _to_lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _to_srgb(c):
    c = clamp(c, 0, 1)
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def _cbrt(x):
    return math.copysign(abs(x) ** (1 / 3), x)


def lin_to_oklab(r, g, b):
    l = _cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b)
    m = _cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b)
    s = _cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b)
    return (0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s)


def oklab_to_lin(L, a, b):
    l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    return (4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
            -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
            -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s)


def hex_to_oklab(h):
    return lin_to_oklab(*(_to_lin(c) for c in hex_to_rgb(h)))


def hex_to_oklch(h):
    L, a, b = hex_to_oklab(h)
    return L, math.hypot(a, b), wrap360(math.degrees(math.atan2(b, a)))


def oklch_to_hex(L, C, h):
    L = clamp(L, 0, 1)
    C = max(0.0, C)
    hr = math.radians(h)

    def in_gamut(c):
        return all(-1e-4 <= v <= 1 + 1e-4 for v in oklab_to_lin(L, c * math.cos(hr), c * math.sin(hr)))

    if not in_gamut(C):  # reduce chroma until the colour fits in sRGB
        lo, hi = 0.0, C
        for _ in range(22):
            mid = (lo + hi) / 2
            if in_gamut(mid):
                lo = mid
            else:
                hi = mid
        C = lo
    r, g, b = oklab_to_lin(L, C * math.cos(hr), C * math.sin(hr))
    return rgb_to_hex(_to_srgb(r), _to_srgb(g), _to_srgb(b))


def hex_to_hsv(h):
    r, g, b = hex_to_rgb(h)
    mx, mn = max(r, g, b), min(r, g, b)
    d = mx - mn
    hue = 0.0
    if d:
        if mx == r:
            hue = ((g - b) / d) % 6
        elif mx == g:
            hue = (b - r) / d + 2
        else:
            hue = (r - g) / d + 4
        hue = wrap360(hue * 60)
    return hue, (d / mx if mx else 0.0), mx


def hsv_to_hex(h, s, v):
    h = wrap360(h)
    s, v = clamp(s, 0, 1), clamp(v, 0, 1)
    c = v * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = v - c
    if h < 60:
        r, g, b = c, x, 0
    elif h < 120:
        r, g, b = x, c, 0
    elif h < 180:
        r, g, b = 0, c, x
    elif h < 240:
        r, g, b = 0, x, c
    elif h < 300:
        r, g, b = x, 0, c
    else:
        r, g, b = c, 0, x
    return rgb_to_hex(r + m, g + m, b + m)


ENGINES = {
    "oklch": {"base": lambda hx: hex_to_oklch(hx), "make": oklch_to_hex, "cmax": 0.32},
    "hsv": {"base": lambda hx: (lambda h, s, v: (v, s * 0.25, h))(*hex_to_hsv(hx)),
            "make": lambda L, C, h: hsv_to_hex(h, C / 0.25, L), "cmax": 0.25},
}

# Machado, Oliveira & Fernandes (2009), severity 1.0, applied in linear RGB
CVD_MATRICES = {
    "deutan": ((0.367322, 0.860646, -0.227968), (0.280085, 0.672501, 0.047413), (-0.011820, 0.042940, 0.968881)),
    "protan": ((0.152286, 1.052583, -0.204868), (0.114503, 0.786281, 0.099216), (-0.003882, -0.048116, 1.051998)),
    "tritan": ((1.255528, -0.076749, -0.178779), (-0.078411, 0.930809, 0.147602), (0.004733, 0.691367, 0.303900)),
}


def simulate_cvd(hex_color, kind):
    m = CVD_MATRICES.get(kind)
    if not m:
        return hex_color
    c = [_to_lin(v) for v in hex_to_rgb(hex_color)]
    return rgb_to_hex(*(_to_srgb(clamp(row[0] * c[0] + row[1] * c[1] + row[2] * c[2], 0, 1)) for row in m))


def delta_e(a, b):
    """Perceptual distance (OKLab Euclidean x100). <6 hard to tell apart, >10 clear."""
    p, q = hex_to_oklab(a), hex_to_oklab(b)
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(p, q))) * 100


def min_pair(pal):
    best, pair = float("inf"), None
    for i in range(len(pal)):
        for j in range(i + 1, len(pal)):
            d = delta_e(pal[i], pal[j])
            if d < best:
                best, pair = d, (i, j)
    return best, pair


def rgb01(hx):
    return "[" + ", ".join(f"{v:.3f}" for v in hex_to_rgb(hx)) + "]"


# ==========================================
# HARMONY RULES
# ==========================================
def _lin(i, n):
    return i / (n - 1) if n > 1 else 0.5


def _cycle(b, n, anchors, o):
    k = len(anchors)
    out = []
    for i in range(n):
        p = i // k
        step = 0 if p == 0 else (1 if p % 2 else -1) * math.ceil(p / 2) * (0.06 + 0.14 * o["variation"])
        out.append((b[0] + step, b[1] * (0.85 if p else 1), b[2] + anchors[i % k]))
    return out


def _even(k):
    return [i * 360.0 / k for i in range(k)]


def _vary(i, o, a=0.05):
    return (-1 if i % 2 else 1) * a * o["variation"]


def _r_mono(b, n, o):
    amp = 0.15 + 0.3 * o["variation"]
    hi, lo = min(0.95, b[0] + amp), max(0.22, b[0] - amp)
    return [(hi + (lo - hi) * _lin(i, n), b[1] * (1 - 0.5 * abs(_lin(i, n) - 0.5)), b[2]) for i in range(n)]


def _r_analog(b, n, o):
    return [(b[0] + _vary(i, o, 0.06), b[1], b[2] + (i - (n - 1) / 2) * o["spread"]) for i in range(n)]


def _r_accent(b, n, o):
    out = []
    for i in range(n):
        if i == n - 1 and n > 2:
            out.append((b[0], b[1] * 1.1, b[2] + 180))
        else:
            out.append((b[0] + _vary(i, o, 0.06), b[1], b[2] + (i - (n - 2) / 2) * o["spread"]))
    return out


def _r_golden(b, n, o):
    return [(b[0] + (0, 0.1, -0.1)[i % 3] * o["variation"] * 1.5, b[1], b[2] + i * 137.508) for i in range(n)]


def _t(i, n):
    return _lin(i, n) if n > 1 else 0.0


def _r_shades(b, n, o):
    return [(b[0] - (b[0] - 0.2) * _t(i, n), b[1] * (1 - 0.4 * _t(i, n)), b[2]) for i in range(n)]


def _r_tints(b, n, o):
    return [(b[0] + (0.96 - b[0]) * _t(i, n), b[1] * (1 - 0.8 * _t(i, n)), b[2]) for i in range(n)]


def _r_tones(b, n, o):
    return [(b[0] + (0.6 - b[0]) * _t(i, n) * 0.6, b[1] * (1 - 0.85 * _t(i, n)), b[2]) for i in range(n)]


def _r_ramp(b, n, o):
    return [(0.95 - 0.75 * _lin(i, n), b[1] * math.sin(math.pi * (0.12 + 0.76 * _lin(i, n))), b[2]) for i in range(n)]


def _mood(L, C, a=0.05):
    def f(b, n, o):
        return [(L + _vary(i, o, a), C, b[2] + i * 360.0 / n) for i in range(n)]
    return f


def _r_earthy(b, n, o):
    return [((0.45, 0.62, 0.76)[i % 3] + _vary(i, o, 0.03), 0.085, 30 + _lin(i, n) * 85) for i in range(n)]


def _r_warm(b, n, o):
    return [(0.74 - (i % 2) * 0.1 * (0.4 + o["variation"]), 0.16, 15 + _lin(i, n) * 85) for i in range(n)]


def _r_cool(b, n, o):
    return [(0.68 - (i % 2) * 0.1 * (0.4 + o["variation"]), 0.13, 160 + _lin(i, n) * 140) for i in range(n)]


def _r_distinct(b, n, o):
    return [((0.58, 0.78, 0.68, 0.48)[i % 4], 0.15, b[2] + i * 137.508) for i in range(n)]


def _r_equal(b, n, o):
    return [(clamp(b[0], 0.55, 0.8), clamp(b[1], 0.08, 0.14), b[2] + i * 360.0 / n) for i in range(n)]


def _r_seq(b, n, o):
    out = []
    for i in range(n):
        t = _lin(i, n)
        out.append((0.95 - 0.7 * t, max(b[1], 0.1) * (0.25 + 0.75 * min(1, t * 1.4)), b[2] + (t - 0.5) * o["spread"]))
    return out


def _r_div(b, n, o):
    out = []
    for i in range(n):
        t = _lin(i, n)
        d = abs(2 * t - 1)
        out.append((0.95 - 0.48 * d, max(b[1], 0.1) * d, b[2] if t < 0.5 else b[2] + 180))
    return out


def _r_paired(b, n, o):
    k = math.ceil(n / 2)
    return [(0.5 if i % 2 else 0.82, 0.15 if i % 2 else 0.08, b[2] + (i // 2) * 360.0 / k) for i in range(n)]


def _r_cvd(b, n, o):
    return [(0.32 + 0.6 * _lin(i, n), 0.13, (255, 65, 330, 200)[i % 4]) for i in range(n)]


def _r_chainlig(b, n, o):
    out = []
    for i in range(n):
        if i == n - 1 and n > 1:
            out.append((0.72, 0.2, b[2] + 180))
        else:
            out.append((0.78 - (i % 2) * 0.1, 0.07, b[2] + (i - (n - 2) / 2) * o["spread"]))
    return out


_W, _LS, _MO, _ST = "Colour wheel", "Light & shade", "Mood", "For structures"
RULES = [
    (_W, "mono", "Monochromatic", "One hue in light-to-dark steps", ("variation",), _r_mono),
    (_W, "analog", "Analogous", "Neighbouring hues on the wheel", ("spread", "variation"), _r_analog),
    (_W, "accent", "Analogous + accent", "Neighbours plus one opposite accent", ("spread", "variation"), _r_accent),
    (_W, "compl", "Complementary", "Seed and its opposite", ("variation",), lambda b, n, o: _cycle(b, n, [0, 180], o)),
    (_W, "split", "Split complementary", "Seed plus the two neighbours of its opposite", ("spread", "variation"),
     lambda b, n, o: _cycle(b, n, [0, 180 - o["spread"], 180 + o["spread"]], o)),
    (_W, "dsplit", "Double split", "Two hues each side of the seed–opposite axis", ("spread", "variation"),
     lambda b, n, o: _cycle(b, n, [-o["spread"] / 2, o["spread"] / 2, 180 - o["spread"] / 2, 180 + o["spread"] / 2], o)),
    (_W, "triad", "Triadic", "Three hues 120° apart", ("variation",), lambda b, n, o: _cycle(b, n, _even(3), o)),
    (_W, "rect", "Rectangle", "Two opposite pairs, set apart by the spread", ("spread", "variation"),
     lambda b, n, o: _cycle(b, n, [0, o["spread"] * 2, 180, 180 + o["spread"] * 2], o)),
    (_W, "square", "Square", "Four hues 90° apart", ("variation",), lambda b, n, o: _cycle(b, n, _even(4), o)),
    (_W, "penta", "Pentadic", "Five hues 72° apart", ("variation",), lambda b, n, o: _cycle(b, n, _even(5), o)),
    (_W, "hexa", "Hexadic", "Six hues 60° apart", ("variation",), lambda b, n, o: _cycle(b, n, _even(6), o)),
    (_W, "golden", "Golden angle", "Each hue 137.5° after the previous one", ("variation",), _r_golden),
    (_W, "clash", "Clash", "Seed with hues 90° either side: bold, energetic", ("variation",),
     lambda b, n, o: _cycle(b, n, [0, 90, 270], o)),
    (_LS, "shades", "Shades", "Seed mixed toward black", (), _r_shades),
    (_LS, "tints", "Tints", "Seed mixed toward white", (), _r_tints),
    (_LS, "tones", "Tones", "Seed mixed toward grey", (), _r_tones),
    (_LS, "ramp", "Tint to shade", "Full light-to-dark ramp through the seed", (), _r_ramp),
    (_MO, "pastel", "Pastel", "Soft and light. Good for surfaces", ("variation",), _mood(0.88, 0.075, 0.03)),
    (_MO, "vivid", "Vivid", "Saturated and bright. Good for cartoons", ("variation",), _mood(0.7, 0.19)),
    (_MO, "muted", "Muted", "Calm, greyed colours", ("variation",), _mood(0.62, 0.055)),
    (_MO, "earthy", "Earthy", "Browns, ochres and olives (ignores the seed hue)", ("variation",), _r_earthy),
    (_MO, "neon", "Neon", "Electric colours for dark backgrounds", ("variation",), _mood(0.82, 0.3, 0.04)),
    (_MO, "jewel", "Jewel tones", "Deep, rich colours", ("variation",), _mood(0.5, 0.16)),
    (_MO, "candy", "Candy", "Bright pinks, mints and lemons", ("variation",), _mood(0.85, 0.14, 0.03)),
    (_MO, "warm", "Warm", "Reds, oranges and yellows only (ignores the seed hue)", ("variation",), _r_warm),
    (_MO, "cool", "Cool", "Greens, blues and violets only (ignores the seed hue)", ("variation",), _r_cool),
    (_ST, "distinct", "Maximally distinct", "Golden-angle hues, stepped lightness. For many chains", (), _r_distinct),
    (_ST, "equalL", "Equal lightness", "Same brightness, only the hue differs", (), _r_equal),
    (_ST, "seq", "Sequential", "Light to dark with a hue drift. For B-factor or pLDDT", ("spread",), _r_seq),
    (_ST, "div", "Diverging", "Seed to its opposite through a light centre. For charge or ΔΔG", (), _r_div),
    (_ST, "paired", "Paired", "A light and a dark of each hue. For domains within chains", (), _r_paired),
    (_ST, "cvd", "Colour-blind friendly", "Blue, orange and magenta with large lightness steps (ignores the seed hue)", (), _r_cvd),
    (_ST, "chainlig", "Chain & ligand", "Calm protein chains plus one vivid ligand accent", ("spread",), _r_chainlig),
]
RULE = {r[1]: r for r in RULES}


def harmony_points(seed, rule_id, n, s, no_jitter=False):
    """Returns [{'L','C','h','hex'}] for a rule. `s` holds the harmony settings."""
    eng = ENGINES[s["engine"]]
    L0, C0, h0 = eng["base"](seed)
    if C0 < 0.02:
        C0 = 0.1
    o = {"spread": s["spread"], "variation": s["variation"]}
    rnd = random.Random(s["jitter"] or 1)
    pts = []
    for L, C, h in RULE[rule_id][5]((L0, C0, h0), n, o):
        L, C = L + s["light"], max(0.0, C * s["vib"])
        if s["jitter"] and not no_jitter:
            h += (rnd.random() - 0.5) * 24
            L += (rnd.random() - 0.5) * 0.08
        L, h = clamp(L, 0.12, 0.97), wrap360(h)
        pts.append({"L": L, "C": C, "h": h, "hex": eng["make"](L, C, h)})
    return order_points(pts, "gen" if no_jitter else s["order"])


def order_points(pts, mode):
    if mode == "hue":
        return sorted(pts, key=lambda p: p["h"])
    if mode == "light":
        return sorted(pts, key=lambda p: -hex_to_oklab(p["hex"])[0])
    if mode == "contrast" and len(pts) > 2:
        left, out = list(pts[1:]), [pts[0]]
        while left:
            last = out[-1]["hex"]
            j = max(range(len(left)), key=lambda k: delta_e(last, left[k]["hex"]))
            out.append(left.pop(j))
        return out
    return pts


# ==========================================
# COLORMAP CATALOGUE
# ==========================================
OKABE_ITO = ["#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2", "#D55E00", "#CC79A7", "#000000"]
TOL_BRIGHT = ["#4477AA", "#EE6677", "#228833", "#CCBB44", "#66CCEE", "#AA3377", "#BBBBBB"]

# Used only when Matplotlib is not installed.
FALLBACK_STOPS = {
    "viridis": "#440154 #482878 #3E4A89 #31688E #26828E #1F9E89 #35B779 #6DCD59 #B4DE2C #FDE725",
    "plasma": "#0D0887 #46039F #7201A8 #9C179E #BD3786 #D8576B #ED7953 #FB9F3A #FDCA26 #F0F921",
    "magma": "#000004 #180F3D #440F76 #721F81 #9E2F7F #CD4071 #F1605D #FD9668 #FECA8D #FCFDBF",
    "cividis": "#00224E #123570 #3B496C #575D6D #707173 #8A8779 #A69D75 #C4B56C #E4CF5B #FEE838",
    "coolwarm": "#3B4CC0 #6889EE #9ABBFF #C9D7F0 #EDD1C2 #F7A889 #E26952 #B40426",
    "RdBu": "#67001F #B2182B #D6604D #F4A582 #FDDBC7 #F7F7F7 #D1E5F0 #92C5DE #4393C3 #2166AC #053061",
    "Spectral": "#9E0142 #D53E4F #F46D43 #FDAE61 #FEE08B #FFFFBF #E6F598 #ABDDA4 #66C2A5 #3288BD #5E4FA2",
    "Blues": "#F7FBFF #DEEBF7 #C6DBEF #9ECAE1 #6BAED6 #4292C6 #2171B5 #08519C #08306B",
}
FALLBACK_LISTS = {
    "tab10": "#1F77B4 #FF7F0E #2CA02C #D62728 #9467BD #8C564B #E377C2 #7F7F7F #BCBD22 #17BECF",
    "Set2": "#66C2A5 #FC8D62 #8DA0CB #E78AC3 #A6D854 #FFD92F #E5C494 #B3B3B3",
}

MPL_GROUPS = [
    ("Perceptually uniform", ["viridis", "plasma", "inferno", "magma", "cividis"]),
    ("Sequential", ["Greys", "Purples", "Blues", "Greens", "Oranges", "Reds", "YlOrBr", "YlOrRd", "OrRd", "PuRd",
                    "RdPu", "BuPu", "GnBu", "PuBu", "YlGnBu", "PuBuGn", "BuGn", "YlGn"]),
    ("Sequential (2)", ["binary", "gist_yarg", "gist_gray", "gray", "bone", "pink", "spring", "summer", "autumn",
                        "winter", "cool", "Wistia", "hot", "afmhot", "gist_heat", "copper"]),
    ("Diverging", ["PiYG", "PRGn", "BrBG", "PuOr", "RdGy", "RdBu", "RdYlBu", "RdYlGn", "Spectral", "coolwarm",
                   "bwr", "seismic"]),
    ("Diverging · dark centre", ["berlin", "managua", "vanimo"]),
    ("Cyclic", ["twilight", "twilight_shifted", "hsv"]),
    ("Qualitative", ["Pastel1", "Pastel2", "Paired", "Accent", "Dark2", "Set1", "Set2", "Set3", "tab10", "tab20",
                     "tab20b", "tab20c"]),
    ("Miscellaneous", ["turbo", "cubehelix", "terrain", "ocean", "gist_earth", "gist_stern", "gnuplot", "gnuplot2",
                       "CMRmap", "brg", "gist_rainbow", "rainbow", "jet", "nipy_spectral", "gist_ncar", "flag", "prism"]),
]
CMAP_ALIASES = {"Grays", "grey", "gist_grey", "gist_yerg"}
CVD_SAFE = {"viridis", "plasma", "inferno", "magma", "cividis", "Okabe-Ito", "Tol bright"}
NEW_310 = {"berlin", "managua", "vanimo"}


class CmapEntry:
    def __init__(self, name, group, kind, data=None, qual=False):
        self.name, self.group, self.kind, self.data, self.qual = name, group, kind, data, qual
        self.badges = []
        if name in CVD_SAFE or name.startswith("cmc."):
            self.badges.append("CVD-safe")
        if name in NEW_310:
            self.badges.append("New · mpl 3.10")
        if name.startswith("cmc."):
            self.badges.append("cmcrameri")
        if name.startswith("cmo."):
            self.badges.append("cmocean")


def _mpl_cmap(name):
    try:
        return matplotlib.colormaps[name]
    except Exception:
        import matplotlib.cm as mcm
        return mcm.get_cmap(name)


def build_catalogue():
    cat = [CmapEntry("Okabe-Ito", "Colour-blind safe", "list", OKABE_ITO, True),
           CmapEntry("Tol bright", "Colour-blind safe", "list", TOL_BRIGHT, True)]
    if not HAS_MATPLOTLIB:
        for n, s in FALLBACK_STOPS.items():
            cat.append(CmapEntry(n, "Built-in", "stops", s.split()))
        for n, s in FALLBACK_LISTS.items():
            cat.append(CmapEntry(n, "Built-in", "list", s.split(), True))
        return cat
    try:
        registered = [n for n in matplotlib.colormaps if not n.endswith("_r")]
    except Exception:
        import matplotlib.pyplot as plt
        registered = [n for n in plt.colormaps() if not n.endswith("_r")]
    reg = set(registered)
    used = set()
    for group, names in MPL_GROUPS:
        for n in names:
            if n in reg:
                cat.append(_mpl_entry(n, group))
                used.add(n)
    extra = {"cmc.": "Scientific · cmcrameri", "cmo.": "Scientific · cmocean"}
    for n in sorted(reg - used - CMAP_ALIASES, key=str.lower):
        group = next((g for p, g in extra.items() if n.startswith(p)), "Other")
        cat.append(_mpl_entry(n, group))
    group_order = ["Colour-blind safe"] + [g for g, _ in MPL_GROUPS] + list(extra.values()) + ["Other"]
    cat.sort(key=lambda e: group_order.index(e.group) if e.group in group_order else 99)
    return cat


def _mpl_entry(name, group):
    cm = _mpl_cmap(name)
    qual = isinstance(cm, mcolors.ListedColormap) and cm.N <= 24
    return CmapEntry(name, group, "mpl", cm, qual)


def cmap_sample(entry, t):
    if entry.kind == "mpl":
        # float() matters: matplotlib treats an int 1 as a lookup-table index, not the end of the map
        return mcolors.to_hex(entry.data(float(clamp(t, 0.0, 1.0)))).upper()
    s = entry.data
    x = clamp(t, 0, 1) * (len(s) - 1)
    i = min(int(x), len(s) - 2)
    f = x - i
    a, b = hex_to_rgb(s[i]), hex_to_rgb(s[i + 1])
    return rgb_to_hex(*(u + (v - u) * f for u, v in zip(a, b)))


def cmap_list(entry):
    if entry.kind == "mpl":
        return [mcolors.to_hex(c).upper() for c in entry.data.colors]
    return list(entry.data)


def cmap_colors(entry, n, a=0.0, b=1.0, rev=False):
    if entry.qual:
        lst = cmap_list(entry)
        out = [lst[i % len(lst)] for i in range(n)]
        return out[::-1] if rev else out
    out = []
    for i in range(n):
        t = a + (b - a) * _lin(i, n)
        out.append(cmap_sample(entry, 1 - t if rev else t))
    return out


def cmap_preview(entry, rev=False, k=40):
    if entry.qual:
        lst = cmap_list(entry)
        return lst[::-1] if rev else lst
    return [cmap_sample(entry, 1 - i / (k - 1) if rev else i / (k - 1)) for i in range(k)]


# ==========================================
# PAINT HELPERS & ICONS
# ==========================================
ICONS = {
    "copy": '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"/>',
    "check": '<path d="M20 6 9 17l-5-5"/>',
    "more": '<circle cx="5" cy="12" r="1.6" fill="currentColor" stroke="none"/><circle cx="12" cy="12" r="1.6" fill="currentColor" stroke="none"/><circle cx="19" cy="12" r="1.6" fill="currentColor" stroke="none"/>',
    "edit": '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/>',
    "undo": '<path d="M9 14 4 9l5-5"/><path d="M4 9h10.5a5.5 5.5 0 0 1 0 11H11"/>',
    "redo": '<path d="m15 14 5-5-5-5"/><path d="M20 9H9.5a5.5 5.5 0 0 0 0 11H13"/>',
    "eye": '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>',
    "download": '<path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M5 21h14"/>',
    "upload": '<path d="M12 15V3"/><path d="m7 8 5-5 5 5"/><path d="M5 21h14"/>',
    "refresh": '<path d="M21 12a9 9 0 1 1-3-6.7L21 8"/><path d="M21 3v5h-5"/>',
    "swap": '<path d="M7 4 3 8l4 4"/><path d="M3 8h18"/><path d="m17 20 4-4-4-4"/><path d="M21 16H3"/>',
    "shuffle": '<path d="M16 3h5v5"/><path d="M4 20 21 3"/><path d="M21 16v5h-5"/><path d="m15 15 6 6"/><path d="m4 4 5 5"/>',
    "paste": '<rect x="8" y="2" width="8" height="4" rx="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "minus": '<path d="M5 12h14"/>',
    "chev": '<path d="m6 9 6 6 6-6"/>',
    "help": '<circle cx="12" cy="12" r="9.5"/><path d="M9.3 9.2a2.8 2.8 0 0 1 5.4 1c0 1.9-2.7 2.6-2.7 2.6"/><path d="M12 17h.01"/>',
    "x": '<path d="M18 6 6 18M6 6l12 12"/>',
}
GLYPHS = {"copy": "⧉", "check": "✓", "more": "⋯", "edit": "✎", "undo": "↶", "redo": "↷", "eye": "◉",
          "download": "⤓", "upload": "⤒", "refresh": "⟳", "swap": "⇄", "shuffle": "⤨", "paste": "⎘",
          "plus": "+", "minus": "−", "chev": "▾", "help": "?", "x": "✕"}
_ICON_CACHE = {}


def _dpr():
    app = QtWidgets.QApplication.instance()
    try:
        return max(1.0, float(app.devicePixelRatio()))
    except Exception:
        return 2.0


def _new_pixmap(w, h):
    d = _dpr()
    pm = QtGui.QPixmap(int(math.ceil(w * d)), int(math.ceil(h * d)))
    pm.setDevicePixelRatio(d)
    pm.fill(Transparent)
    return pm


def icon_pixmap(name, color=INK, size=16):
    key = (name, color, size)
    if key in _ICON_CACHE:
        return _ICON_CACHE[key]
    pm = _new_pixmap(size, size)
    p = QtGui.QPainter(pm)
    p.setRenderHint(Antialias)
    if QtSvg is not None:
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="%s" stroke-width="2" '
               'stroke-linecap="round" stroke-linejoin="round">%s</svg>') % (color, ICONS[name].replace("currentColor", color))
        QtSvg.QSvgRenderer(QtCore.QByteArray(svg.encode("utf-8"))).render(p, QRectF(0, 0, size, size))
    else:
        f = p.font()
        f.setPixelSize(int(size * 0.9))
        p.setFont(f)
        p.setPen(QtGui.QColor(color))
        p.drawText(QRectF(0, 0, size, size), AlignCenter, GLYPHS.get(name, "?"))
    p.end()
    _ICON_CACHE[key] = pm
    return pm


def make_icon(name, size=16):
    ic = QtGui.QIcon()
    ic.addPixmap(icon_pixmap(name, MUTED, size), IconNormal)
    ic.addPixmap(icon_pixmap(name, INK, size), IconActive)
    ic.addPixmap(icon_pixmap(name, LINE, size), IconDisabled)
    return ic


def gradient_pixmap(colors, w, h, hard=False, radius=3):
    pm = _new_pixmap(w, h)
    p = QtGui.QPainter(pm)
    p.setRenderHint(Antialias)
    path = QtGui.QPainterPath()
    path.addRoundedRect(QRectF(0, 0, w, h), radius, radius)
    p.setClipPath(path)
    if hard or len(colors) == 1:
        seg = w / float(len(colors))
        for i, c in enumerate(colors):
            p.fillRect(QRectF(i * seg, 0, seg + 0.6, h), QtGui.QColor(c))
    else:
        g = QtGui.QLinearGradient(0, 0, w, 0)
        for i, c in enumerate(colors):
            g.setColorAt(i / (len(colors) - 1), QtGui.QColor(c))
        p.fillRect(QRectF(0, 0, w, h), QtGui.QBrush(g))
    p.setClipping(False)
    p.setPen(QtGui.QPen(QtGui.QColor(31, 27, 45, 22), 1))
    p.setBrush(NoBrush)
    p.drawRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), radius, radius)
    p.end()
    return pm


def dots_pixmap(colors, d=12, gap=2, round_=False):
    w = len(colors) * d + max(0, len(colors) - 1) * gap
    pm = _new_pixmap(max(w, 1), d)
    p = QtGui.QPainter(pm)
    p.setRenderHint(Antialias)
    p.setPen(NoPen)
    for i, c in enumerate(colors):
        p.setBrush(QtGui.QColor(c))
        r = QRectF(i * (d + gap), 0, d, d)
        if round_:
            p.drawEllipse(r)
        else:
            p.drawRoundedRect(r, 3, 3)
    p.end()
    return pm


def ui_font(px, weight=None, base=None):
    f = QtGui.QFont(base) if base is not None else QtWidgets.QApplication.font()
    f.setPixelSize(px)
    if weight is not None:
        f.setWeight(weight)
    return f


def mono_font(px, bold=False):
    f = QtGui.QFontDatabase.systemFont(FixedFont)
    f.setPixelSize(px)
    f.setBold(bold)
    return f


def mk_label(text, cls=None, wrap=False):
    lab = QtWidgets.QLabel(text)
    if cls:
        lab.setProperty("cls", cls)
    if cls == "lbl":
        f = ui_font(10, WDemi)
        f.setLetterSpacing(AbsSpacing, 0.8)
        lab.setFont(f)
        lab.setText(text.upper())
    lab.setWordWrap(wrap)
    return lab


def mk_ib(icon, tip, checkable=False, size=16):
    b = QtWidgets.QToolButton()
    b.setProperty("cls", "ib")
    b.setIcon(make_icon(icon, size))
    b.setIconSize(QSize(size, size))
    b.setToolTip(tip)
    b.setCheckable(checkable)
    b.setCursor(PointingHand)
    b.setAutoRaise(True)
    return b


def mk_btn(text, cls="btn", icon=None):
    b = QtWidgets.QPushButton(text)
    b.setProperty("cls", cls)
    b.setCursor(PointingHand)
    if icon:
        b.setIcon(make_icon(icon, 15))
        b.setIconSize(QSize(15, 15))
    return b


def mk_frame(cls):
    f = QtWidgets.QFrame()
    f.setProperty("cls", cls)
    return f


def hbox(*items, margins=(0, 0, 0, 0), spacing=8):
    lay = QtWidgets.QHBoxLayout()
    lay.setContentsMargins(*margins)
    lay.setSpacing(spacing)
    for it in items:
        if it is None:
            lay.addStretch(1)
        elif isinstance(it, int):
            lay.addSpacing(it)
        elif isinstance(it, QtWidgets.QLayout):
            lay.addLayout(it)
        else:
            lay.addWidget(it)
    return lay


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


# ==========================================
# FLOW LAYOUT (wrapping rows)
# ==========================================
class FlowLayout(QtWidgets.QLayout):
    def __init__(self, parent=None, hspace=8, vspace=10):
        super().__init__(parent)
        self._items, self._h, self._v = [], hspace, vspace
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, i):
        return self._items[i] if 0 <= i < len(self._items) else None

    def takeAt(self, i):
        return self._items.pop(i) if 0 <= i < len(self._items) else None

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, w):
        return self._do(QtCore.QRect(0, 0, w, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        s = QSize()
        for it in self._items:
            s = s.expandedTo(it.minimumSize())
        return s

    def clear(self):
        while self._items:
            it = self._items.pop()
            w = it.widget()
            if w is not None:
                w.hide()
                w.deleteLater()

    def _do(self, rect, test):
        x, y, line_h = rect.x(), rect.y(), 0
        for it in self._items:
            hint = it.sizeHint()
            nx = x + hint.width() + self._h
            if nx - self._h > rect.right() + 1 and line_h > 0:
                x, y = rect.x(), y + line_h + self._v
                nx, line_h = x + hint.width() + self._h, 0
            if not test:
                it.setGeometry(QtCore.QRect(QPoint(x, y), hint))
            x, line_h = nx, max(line_h, hint.height())
        return y + line_h - rect.y()


# ==========================================
# SMALL CUSTOM WIDGETS
# ==========================================
def chimerax_session():
    """The ChimeraX session: injected into this script's globals by `open script.py`."""
    ses = globals().get("session")
    if ses is None:
        try:
            import chimerax
            ses = getattr(chimerax, "app_session", None)
        except Exception:
            ses = None
    return ses


def arrow_qss():
    """A stylesheet-styled QComboBox loses its native arrow, so draw one from a file."""
    import os
    import tempfile
    path = os.path.join(tempfile.gettempdir(), "molnympheas_chevron.png")
    try:
        icon_pixmap("chev", MUTED, 14).save(path, "PNG")
    except Exception:
        return ""
    path = path.replace("\\", "/")
    return ('QComboBox[cls="fld"]::down-arrow { image: url("%s"); width:14px; height:14px; }\n'
            'QComboBox[cls="fld"]::down-arrow:on { top:1px; }\n') % path


class TargetCombo(QtWidgets.QComboBox):
    """Editable combo that re-reads the session's objects every time its list opens."""

    def __init__(self, on_open):
        super().__init__()
        self._on_open = on_open

    def showPopup(self):
        try:
            self._on_open()
        except Exception as e:
            print(f"MolNympheas Warning: could not refresh targets. {e}")
        super().showPopup()


class FitBody(QtWidgets.QWidget):
    """Scroll-area content that keeps the height its wrapping rows need (QScrollArea ignores heightForWidth)."""

    def fit(self):
        lay = self.layout()
        if lay is None:
            return
        h = lay.heightForWidth(self.width()) if lay.hasHeightForWidth() else lay.minimumSize().height()
        if h > 0 and h != self.minimumHeight():
            self.setMinimumHeight(h)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.fit()


class Ribbon(QtWidgets.QWidget):
    """Thin band across the top of the window showing the current palette."""

    def __init__(self):
        super().__init__()
        self.setFixedHeight(5)
        self.colors = []

    def set_colors(self, c):
        self.colors = list(c)
        self.update()

    def paintEvent(self, _):
        if not self.colors:
            return
        p = QtGui.QPainter(self)
        w = self.width() / float(len(self.colors))
        for i, c in enumerate(self.colors):
            p.fillRect(QRectF(i * w, 0, w + 1, self.height()), QtGui.QColor(c))
        p.end()


class Logo(QtWidgets.QWidget):
    """Six-petal water lily painted in the current palette."""

    def __init__(self):
        super().__init__()
        self.setFixedSize(22, 22)
        self.colors = ["#D63F79"]

    def set_colors(self, c):
        self.colors = list(c) or ["#D63F79"]
        self.update()

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.setRenderHint(Antialias)
        p.translate(11, 11)
        p.setPen(NoPen)
        for i in range(6):
            p.save()
            p.rotate(i * 60)
            col = QtGui.QColor(self.colors[i % len(self.colors)])
            col.setAlphaF(0.92)
            p.setBrush(col)
            p.drawEllipse(QRectF(-3.3, -11.2, 6.6, 12))
            p.restore()
        p.setBrush(QtGui.QColor(self.colors[len(self.colors) // 2]))
        p.setPen(QtGui.QPen(QtGui.QColor(WIN), 1.2))
        p.drawEllipse(QPointF(0, 0), 2.6, 2.6)
        p.end()


class HexEdit(QtWidgets.QLineEdit):
    cancelled = Signal()

    def keyPressEvent(self, e):
        if e.key() == K("Key_Escape"):
            self.cancelled.emit()
            return
        super().keyPressEvent(e)


class RangeSlider(QtWidgets.QWidget):
    """Two-handle slider drawn over the colormap gradient."""
    changed = Signal(float, float, bool)  # a, b, final

    def __init__(self):
        super().__init__()
        self.setFixedHeight(22)
        self.setMinimumWidth(160)
        self.a, self.b = 0.0, 1.0
        self.colors = ["#000000", "#FFFFFF"]
        self.hard = False
        self._drag = None
        self.setCursor(PointingHand)

    def set_values(self, a, b):
        self.a, self.b = a, b
        self.update()

    def set_colors(self, colors, hard):
        self.colors, self.hard = colors, hard
        self.update()

    def _x(self, t):
        return 7 + t * (self.width() - 14)

    def _t(self, x):
        return clamp((x - 7) / float(max(1, self.width() - 14)), 0, 1)

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.setRenderHint(Antialias)
        if not self.isEnabled():
            p.setOpacity(0.35)
        tw = self.width() - 14
        p.drawPixmap(QPoint(7, 7), gradient_pixmap(self.colors, tw, 8, self.hard, 4))
        shade = QtGui.QColor(WIN)
        shade.setAlphaF(0.72)
        p.setPen(NoPen)
        p.setBrush(shade)
        p.drawRect(QRectF(7, 7, self._x(self.a) - 7, 8))
        p.drawRect(QRectF(self._x(self.b), 7, self.width() - 7 - self._x(self.b), 8))
        for t in (self.a, self.b):
            p.setBrush(QtGui.QColor(WIN))
            p.setPen(QtGui.QPen(QtGui.QColor(INK), 2))
            p.drawEllipse(QPointF(self._x(t), 11), 6, 6)
        p.end()

    def mousePressEvent(self, e):
        x = _pos(e).x()
        self._drag = "a" if abs(x - self._x(self.a)) <= abs(x - self._x(self.b)) else "b"
        self.mouseMoveEvent(e)

    def mouseMoveEvent(self, e):
        if not self._drag:
            return
        t = self._t(_pos(e).x())
        if self._drag == "a":
            self.a = min(t, self.b - 0.05)
        else:
            self.b = max(t, self.a + 0.05)
        self.a, self.b = clamp(self.a, 0, 1), clamp(self.b, 0, 1)
        self.update()
        self.changed.emit(self.a, self.b, False)

    def mouseReleaseEvent(self, e):
        if self._drag:
            self._drag = None
            self.changed.emit(self.a, self.b, True)


class HueWheel(QtWidgets.QWidget):
    """Hue ring with the palette's colours as dots. Drag to turn the seed."""
    dragged = Signal(float)
    released = Signal()

    def __init__(self):
        super().__init__()
        self.setFixedSize(128, 128)
        self.setCursor(OpenHand)
        self.pts, self.engine, self.seed_h, self.seed_hex = [], "oklch", 0.0, "#D63F79"
        self._ring = {}
        self._drag = False

    def set_data(self, pts, engine, seed_hex):
        self.pts, self.engine, self.seed_hex = pts, engine, seed_hex
        self.seed_h = ENGINES[engine]["base"](seed_hex)[2]
        self.update()

    def _ring_pm(self):
        if self.engine in self._ring:
            return self._ring[self.engine]
        W = self.width()
        c, R, T = W / 2.0, W / 2.0 - 2, 11
        pm = _new_pixmap(W, W)
        p = QtGui.QPainter(pm)
        p.setRenderHint(Antialias)
        g = QtGui.QConicalGradient(c, c, 90)
        for k in range(73):
            t = k / 72.0
            hue = wrap360((1 - t) * 360)
            col = oklch_to_hex(0.78, 0.13, hue) if self.engine == "oklch" else hsv_to_hex(hue, 0.7, 0.98)
            g.setColorAt(t, QtGui.QColor(col))
        ring = QtGui.QPainterPath()
        ring.addEllipse(QPointF(c, c), R, R)
        inner = QtGui.QPainterPath()
        inner.addEllipse(QPointF(c, c), R - T, R - T)
        p.fillPath(ring.subtracted(inner), QtGui.QBrush(g))
        p.setPen(NoPen)
        p.setBrush(QtGui.QColor(SURFACE))
        p.drawEllipse(QPointF(c, c), R - T - 1, R - T - 1)
        p.end()
        self._ring[self.engine] = pm
        return pm

    def _pos(self, h, r):
        c = self.width() / 2.0
        a = math.radians(h - 90)
        return QPointF(c + r * math.cos(a), c + r * math.sin(a))

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.setRenderHint(Antialias)
        p.drawPixmap(0, 0, self._ring_pm())
        c, R, T = self.width() / 2.0, self.width() / 2.0 - 2, 11
        inner = R - T - 9
        cmax = ENGINES[self.engine]["cmax"]
        p.setPen(QtGui.QPen(QtGui.QColor(LINE), 1.2))
        pos = [self._pos(pt["h"], inner * (0.2 + 0.8 * min(1, pt["C"] / cmax))) for pt in self.pts]
        for q in pos:
            p.drawLine(QPointF(c, c), q)
        for q, pt in zip(pos, self.pts):
            p.setPen(QtGui.QPen(QtGui.QColor(WIN), 2))
            p.setBrush(QtGui.QColor(pt["hex"]))
            p.drawEllipse(q, 5.5, 5.5)
        s = self._pos(self.seed_h, R - T / 2.0)
        p.setPen(QtGui.QPen(QtGui.QColor(WIN), 2.5))
        p.setBrush(QtGui.QColor(self.seed_hex))
        p.drawEllipse(s, 8, 8)
        p.setPen(QtGui.QPen(QtGui.QColor(INK), 1.5))
        p.setBrush(NoBrush)
        p.drawEllipse(s, 9.5, 9.5)
        p.end()

    def _hue(self, e):
        q = _pos(e)
        c = self.width() / 2.0
        return wrap360(math.degrees(math.atan2(q.y() - c, q.x() - c)) + 90)

    def mousePressEvent(self, e):
        self._drag = True
        self.setCursor(ClosedHand)
        self.dragged.emit(self._hue(e))

    def mouseMoveEvent(self, e):
        if self._drag:
            self.dragged.emit(self._hue(e))

    def mouseReleaseEvent(self, e):
        if self._drag:
            self._drag = False
            self.setCursor(OpenHand)
            self.released.emit()


# ==========================================
# PICKER (grouped, searchable list with previews)
# ==========================================
class PickerDelegate(QtWidgets.QStyledItemDelegate):
    def sizeHint(self, opt, idx):
        d = idx.data(UserRole) or {}
        if d.get("header"):
            return QSize(100, 26)
        return QSize(100, 40 if d.get("desc") else 28)

    def paint(self, p, opt, idx):
        d = idx.data(UserRole) or {}
        r = QRectF(opt.rect)
        p.save()
        p.setRenderHint(Antialias)
        if d.get("header"):
            f = ui_font(10, WDemi)
            f.setLetterSpacing(AbsSpacing, 0.8)
            p.setFont(f)
            p.setPen(QtGui.QColor(MUTED))
            p.drawText(r.adjusted(8, 0, -8, -4), AlignLeft | AlignBottom, d["name"].upper())
            p.restore()
            return
        if opt.state & StateSelected or opt.state & StateHover:
            p.setPen(NoPen)
            p.setBrush(QtGui.QColor(SURFACE))
            p.drawRoundedRect(r.adjusted(2, 1, -2, -1), 7, 7)
        x, right = r.left() + 10, r.right() - 8
        if d.get("pix") is not None:
            pm = d["pix"]
            pw = pm.width() / pm.devicePixelRatio()
            ph = pm.height() / pm.devicePixelRatio()
            p.drawPixmap(QPointF(x, r.center().y() - ph / 2), pm)
            x += pw + 10
        if d.get("dots") is not None:
            pm = d["dots"]
            pw = pm.width() / pm.devicePixelRatio()
            right -= pw
            p.drawPixmap(QPointF(right, r.center().y() - 6), pm)
            right -= 10
        for badge in reversed(d.get("badges", [])):
            f = ui_font(9, WDemi)
            p.setFont(f)
            bw = QtGui.QFontMetrics(f).horizontalAdvance(badge.upper()) + 10
            br = QRectF(right - bw, r.center().y() - 8, bw, 16)
            p.setPen(NoPen)
            p.setBrush(QtGui.QColor(ACCENT_SOFT))
            p.drawRoundedRect(br, 4, 4)
            p.setPen(QtGui.QColor(ACCENT))
            p.drawText(br, AlignCenter, badge.upper())
            right -= bw + 6
        cur = d.get("current")
        f = ui_font(13, WDemi if cur else WMedium)
        p.setFont(f)
        p.setPen(QtGui.QColor(ACCENT if cur else INK))
        tw = int(right - x)
        if d.get("desc"):
            p.drawText(QRectF(x, r.top() + 4, tw, 17), AlignLeft | AlignVCenter,
                       QtGui.QFontMetrics(f).elidedText(d["name"], ElideRight, tw))
            f2 = ui_font(11)
            p.setFont(f2)
            p.setPen(QtGui.QColor(MUTED))
            p.drawText(QRectF(x, r.top() + 20, tw, 16), AlignLeft | AlignVCenter,
                       QtGui.QFontMetrics(f2).elidedText(d["desc"], ElideRight, tw))
        else:
            p.drawText(QRectF(x, r.top(), tw, r.height()), AlignLeft | AlignVCenter,
                       QtGui.QFontMetrics(f).elidedText(d["name"], ElideRight, tw))
        p.restore()


class SearchEdit(QtWidgets.QLineEdit):
    nav = Signal(str)

    def keyPressEvent(self, e):
        k = e.key()
        if k in (K("Key_Down"), K("Key_Up")):
            self.nav.emit("down" if k == K("Key_Down") else "up")
        elif k in (K("Key_Return"), K("Key_Enter")):
            self.nav.emit("enter")
        elif k == K("Key_Escape"):
            self.nav.emit("esc")
        else:
            super().keyPressEvent(e)


class PickerPopup(QtWidgets.QFrame):
    chosen = Signal(str)

    def __init__(self, parent, entries_fn, search=None, width=400):
        super().__init__(parent, PopupFlag)
        self.setProperty("cls", "popup")
        self.entries_fn = entries_fn
        self.setFixedSize(width, 380)
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(4)
        self.search = None
        if search:
            self.search = SearchEdit()
            self.search.setProperty("cls", "search")
            self.search.setPlaceholderText(search)
            self.search.textChanged.connect(self.rebuild)
            self.search.nav.connect(self._nav)
            lay.addWidget(self.search)
        self.list = QtWidgets.QListWidget()
        self.list.setItemDelegate(PickerDelegate(self.list))
        self.list.setMouseTracking(True)
        self.list.setVerticalScrollMode(ScrollPerPixel)
        self.list.setHorizontalScrollBarPolicy(ScrollOff)
        self.list.itemClicked.connect(self._clicked)
        self.list.itemActivated.connect(self._clicked)
        lay.addWidget(self.list)
        self.empty = mk_label("", "hint", wrap=True)
        self.empty.hide()
        lay.addWidget(self.empty)

    def open_below(self, widget):
        if self.search:
            self.search.blockSignals(True)
            self.search.clear()
            self.search.blockSignals(False)
        self.rebuild()
        g = widget.mapToGlobal(QPoint(0, widget.height() + 4))
        scr = QtWidgets.QApplication.screenAt(g) if hasattr(QtWidgets.QApplication, "screenAt") else None
        if scr is not None:
            av = scr.availableGeometry()
            x = min(g.x(), av.right() - self.width() - 8)
            y = g.y() if g.y() + self.height() < av.bottom() else widget.mapToGlobal(QPoint(0, 0)).y() - self.height() - 4
            g = QPoint(max(av.left() + 8, x), max(av.top() + 8, y))
        self.move(g)
        self.show()
        (self.search or self.list).setFocus()

    def rebuild(self):
        q = self.search.text().strip().lower() if self.search else ""
        self.list.clear()
        cur_row, group = -1, None
        for d in self.entries_fn():
            if q and q not in (d["name"] + " " + d["group"] + " " + " ".join(d.get("badges", []))).lower():
                continue
            if d["group"] != group:
                group = d["group"]
                h = QtWidgets.QListWidgetItem()
                h.setData(UserRole, {"header": True, "name": group})
                h.setFlags(NoItemFlags)
                self.list.addItem(h)
            it = QtWidgets.QListWidgetItem()
            it.setData(UserRole, d)
            self.list.addItem(it)
            if d.get("current"):
                cur_row = self.list.count() - 1
        has = self.list.count() > 0
        self.list.setVisible(has)
        self.empty.setVisible(not has)
        self.empty.setText(f"Nothing matches “{esc(q)}”. Try a family such as “diverging”.")
        if cur_row < 0:
            cur_row = self._step(-1, 1)
        if cur_row >= 0:
            self.list.setCurrentRow(cur_row)
            self.list.scrollToItem(self.list.item(cur_row))

    def _selectable(self, row):
        it = self.list.item(row)
        return it is not None and not (it.data(UserRole) or {}).get("header")

    def _step(self, row, d):
        r = row + d
        while 0 <= r < self.list.count():
            if self._selectable(r):
                return r
            r += d
        return row if self._selectable(row) else -1

    def _nav(self, what):
        if what == "esc":
            self.close()
        elif what == "enter":
            it = self.list.currentItem()
            if it is not None:
                self._clicked(it)
        else:
            r = self._step(self.list.currentRow(), 1 if what == "down" else -1)
            if r >= 0:
                self.list.setCurrentRow(r)

    def _clicked(self, it):
        d = it.data(UserRole) or {}
        if d.get("header"):
            return
        self.close()
        self.chosen.emit(d["id"])


class PickerButton(QtWidgets.QPushButton):
    """Flat button that shows the current choice with its preview."""

    def __init__(self):
        super().__init__()
        self.setCursor(PointingHand)
        self.setFixedHeight(34)
        self.setMinimumWidth(180)
        self.setSizePolicy(SPExpanding, SPFixed)
        self.pix, self.prefix, self.name, self.suffix, self.badges = None, "", "", "", []

    def set_content(self, name, pix=None, prefix="", suffix="", badges=()):
        self.name, self.pix, self.prefix, self.suffix, self.badges = name, pix, prefix, suffix, list(badges)
        self.update()

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.setRenderHint(Antialias)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setBrush(QtGui.QColor(SURFACE))
        p.setPen(QtGui.QPen(QtGui.QColor(ACCENT if self.hasFocus() else (LINE if self.underMouse() else SURFACE)), 1))
        p.drawRoundedRect(r, 8, 8)
        x = 10.0
        if self.pix is not None:
            pw = self.pix.width() / self.pix.devicePixelRatio()
            ph = self.pix.height() / self.pix.devicePixelRatio()
            p.drawPixmap(QPointF(x, (self.height() - ph) / 2), self.pix)
            x += pw + 10
        if self.prefix:
            f = ui_font(10, WDemi)
            f.setLetterSpacing(AbsSpacing, 0.8)
            p.setFont(f)
            p.setPen(QtGui.QColor(MUTED))
            t = self.prefix.upper()
            p.drawText(QRectF(x, 0, 200, self.height()), AlignLeft | AlignVCenter, t)
            x += QtGui.QFontMetrics(f).horizontalAdvance(t) + 2 + 10
        right = self.width() - 30.0
        f = ui_font(13, WMedium)
        p.setFont(f)
        p.setPen(QtGui.QColor(INK))
        text = self.name + (("  " + self.suffix) if self.suffix else "")
        bw_total = 0
        fb = ui_font(9, WDemi)
        for b in self.badges:
            bw_total += QtGui.QFontMetrics(fb).horizontalAdvance(b.upper()) + 16
        tw = int(right - x - bw_total)
        el = QtGui.QFontMetrics(f).elidedText(text, ElideRight, max(20, tw))
        p.drawText(QRectF(x, 0, tw, self.height()), AlignLeft | AlignVCenter, el)
        x += QtGui.QFontMetrics(f).horizontalAdvance(el) + 8
        for b in self.badges:
            p.setFont(fb)
            bw = QtGui.QFontMetrics(fb).horizontalAdvance(b.upper()) + 10
            br = QRectF(x, self.height() / 2 - 8, bw, 16)
            p.setPen(NoPen)
            p.setBrush(QtGui.QColor(ACCENT_SOFT))
            p.drawRoundedRect(br, 4, 4)
            p.setPen(QtGui.QColor(ACCENT))
            p.drawText(br, AlignCenter, b.upper())
            x += bw + 6
        p.drawPixmap(QPointF(self.width() - 24, (self.height() - 14) / 2), icon_pixmap("chev", MUTED, 14))
        p.end()

    def enterEvent(self, e):
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.update()
        super().leaveEvent(e)


# ==========================================
# COLOUR TILE
# ==========================================
class ColorTile(QtWidgets.QWidget):
    TW, SW, SH = 72, 64, 56

    def __init__(self, owner, index, hexv, editable, label="", label_tip=""):
        super().__init__()
        self.owner, self.i, self.hex, self.editable = owner, index, hexv, editable
        self.label, self.label_tip = label, label_tip
        self.setFixedSize(self.TW, 100)
        self.setMouseTracking(True)
        self.setFocusPolicy(StrongFocus)
        self.setCursor(PointingHand)
        self.hover, self.hot, self.menu_open, self.copied = False, None, False, False
        self.actions = ["copy", "edit", "more"] if editable else ["copy", "more"]
        self._click = QtCore.QTimer(self)
        self._click.setSingleShot(True)
        self._click.setInterval(QtWidgets.QApplication.doubleClickInterval())
        self._click.timeout.connect(lambda: self.owner.apply_color(self.hex, self.i))
        self._copied_t = QtCore.QTimer(self)
        self._copied_t.setSingleShot(True)
        self._copied_t.timeout.connect(self._uncopy)
        self.editor = None
        self.setAccessibleName(f"{hexv}. Enter applies, C copies.")
        self.setToolTip(f"{hexv} · click to apply")

    def _active(self):
        return self.hover or self.hasFocus() or self.menu_open

    def swatch_rect(self):
        lift = -2 if self._active() else 0
        return QRectF((self.TW - self.SW) / 2.0, 6 + lift, self.SW, self.SH)

    def action_rects(self):
        sw = self.swatch_rect()
        bar = QRectF(sw.left() + 4, sw.bottom() - 26, sw.width() - 8, 22)
        k = len(self.actions)
        out = {}
        for j, a in enumerate(self.actions):
            x = bar.left() + 2 + j * (bar.width() - 4 - 18) / float(k - 1)
            out[a] = QRectF(x, bar.top() + 2, 18, 18)
        return bar, out

    def _act_at(self, pt):
        if not self._active():
            return None
        _, rects = self.action_rects()
        for a, r in rects.items():
            if r.adjusted(-1, -2, 1, 2).contains(QPointF(pt)):
                return a
        return None

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.setRenderHint(Antialias)
        p.setRenderHint(SmoothPix)
        sw = self.swatch_rect()
        active = self._active()
        if active:
            shadow = QtGui.QColor(31, 27, 45, 40)
            p.setPen(NoPen)
            p.setBrush(shadow)
            p.drawRoundedRect(sw.adjusted(3, 6, -3, 4), 10, 10)
            p.setBrush(NoBrush)
            p.setPen(QtGui.QPen(QtGui.QColor(ACCENT), 2))
            p.drawRoundedRect(sw.adjusted(-3, -3, 3, 3), 12, 12)
        p.setBrush(QtGui.QColor(self.hex))
        p.setPen(QtGui.QPen(QtGui.QColor(31, 27, 45, 22), 1))
        p.drawRoundedRect(sw.adjusted(0.5, 0.5, -0.5, -0.5), 10, 10)
        if active:
            bar, rects = self.action_rects()
            p.setPen(NoPen)
            p.setBrush(QtGui.QColor(255, 255, 255, 225))
            p.drawRoundedRect(bar, 7, 7)
            for a, r in rects.items():
                if a == self.hot:
                    p.setBrush(QtGui.QColor(31, 27, 45, 30))
                    p.drawRoundedRect(r, 5, 5)
                name = "check" if (a == "copy" and self.copied) else a
                p.drawPixmap(QPointF(r.left() + 2.5, r.top() + 2.5), icon_pixmap(name, INK, 13))
        if self.editor is None:
            p.setFont(mono_font(11))
            p.setPen(QtGui.QColor(INK if active else MUTED))
            p.drawText(QRectF(0, 66, self.TW, 15), AlignCenter, self.hex[1:])
        if self.label:
            f = ui_font(10, WDemi)
            p.setFont(f)
            p.setPen(QtGui.QColor(ACCENT))
            p.drawText(QRectF(0, 81, self.TW, 15), AlignCenter,
                       QtGui.QFontMetrics(f).elidedText(self.label, ElideRight, self.TW))
        p.end()

    # --- interaction
    def enterEvent(self, e):
        self.hover = True
        self.owner.hint_tile(self.i)
        self.update()

    def leaveEvent(self, e):
        self.hover, self.hot = False, None
        self.owner.hint()
        self.update()

    def focusInEvent(self, e):
        self.owner.hint_tile(self.i)
        self.update()

    def focusOutEvent(self, e):
        self.update()

    def mouseMoveEvent(self, e):
        a = self._act_at(_pos(e))
        if a != self.hot:
            self.hot = a
            tips = {"copy": f"Copy {self.hex}", "edit": "Edit hex", "more": "More actions"}
            self.setToolTip(tips.get(a, f"{self.hex} · click to apply" + (f" · on {self.label_tip}" if self.label_tip else "")))
            self.update()

    def mousePressEvent(self, e):
        if e.button() == LeftButton:
            self.setFocus()

    def mouseReleaseEvent(self, e):
        if e.button() != LeftButton:
            return
        pt = _pos(e)
        a = self._act_at(pt)
        if a:
            self._click.stop()
            self.do_action(a)
        elif self.swatch_rect().contains(QPointF(pt)):
            self._click.start()

    def mouseDoubleClickEvent(self, e):
        if self._act_at(_pos(e)):
            return
        self._click.stop()
        self.owner.tile_double(self.i)

    def contextMenuEvent(self, e):
        self._click.stop()
        self.owner.tile_menu(self.i, e.globalPos())

    def keyPressEvent(self, e):
        k = e.key()
        if k in (K("Key_Return"), K("Key_Enter")):
            self.owner.apply_color(self.hex, self.i)
        elif k == K("Key_C") and not (e.modifiers() & (CtrlMod | MetaMod)):
            self.do_action("copy")
        elif k in (K("Key_Delete"), K("Key_Backspace")) and self.editable:
            self.owner.remove_color(self.i)
        elif k == K("Key_Menu") or (k == K("Key_F10") and e.modifiers() & ShiftMod):
            self.owner.tile_menu(self.i, self.mapToGlobal(QPoint(0, self.height())))
        elif k in (K("Key_Right"), K("Key_Left")):
            self.owner.focus_tile(self.i + (1 if k == K("Key_Right") else -1))
        else:
            super().keyPressEvent(e)

    def do_action(self, a):
        if a == "copy":
            self.owner.copy_text(self.hex)
            self.copied = True
            self._copied_t.start(1200)
            self.update()
        elif a == "edit":
            self.start_edit()
        elif a == "more":
            sw = self.swatch_rect()
            self.owner.tile_menu(self.i, self.mapToGlobal(QPoint(int(sw.left()), int(sw.bottom()) + 4)))

    def _uncopy(self):
        self.copied = False
        self.update()

    def start_edit(self):
        if self.editor is not None:
            return
        ed = HexEdit(self)
        ed.setProperty("cls", "tileedit")
        ed.setFont(mono_font(11))
        ed.setAlignment(AlignCenter)
        ed.setMaxLength(8)
        ed.setText(self.hex)
        ed.setGeometry(0, 65, self.TW, 18)
        self.editor = ed
        self._done = False
        ed.returnPressed.connect(lambda: self._finish(True))
        ed.editingFinished.connect(lambda: self._finish(True))
        ed.cancelled.connect(lambda: self._finish(False))
        ed.show()
        ed.setFocus()
        ed.selectAll()
        self.update()

    def _finish(self, ok):
        if self._done:
            return
        self._done = True
        text = self.editor.text() if self.editor else ""
        self.owner.commit_tile_edit(self.i, text if ok else None)


class AddTile(QtWidgets.QWidget):
    clicked = Signal()

    def __init__(self):
        super().__init__()
        self.setFixedSize(ColorTile.TW, 100)
        self.setCursor(PointingHand)
        self.setToolTip("Add a colour")
        self.hover = False

    def enterEvent(self, e):
        self.hover = True
        self.update()

    def leaveEvent(self, e):
        self.hover = False
        self.update()

    def mouseReleaseEvent(self, e):
        if e.button() == LeftButton:
            self.clicked.emit()

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.setRenderHint(Antialias)
        r = QRectF(4, 6, 64, 56)
        col = QtGui.QColor(ACCENT if self.hover else LINE)
        pen = QtGui.QPen(col, 1.5)
        p.setPen(pen)
        p.setBrush(NoBrush)
        p.drawRoundedRect(r.adjusted(0.75, 0.75, -0.75, -0.75), 10, 10)
        p.drawPixmap(QPointF(r.center().x() - 9, r.center().y() - 9), icon_pixmap("plus", ACCENT if self.hover else MUTED, 18))
        p.end()


# ==========================================
# COLOUR-VISION POPUP
# ==========================================
class Strip(QtWidgets.QWidget):
    def __init__(self, colors, clashes):
        super().__init__()
        self.colors, self.clashes = colors, clashes
        self.setFixedHeight(20)
        self.setMinimumWidth(200)

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.setRenderHint(Antialias)
        path = QtGui.QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 5, 5)
        p.setClipPath(path)
        w = self.width() / float(max(1, len(self.colors)))
        for i, c in enumerate(self.colors):
            p.fillRect(QRectF(i * w, 0, w + 1, self.height()), QtGui.QColor(c))
            if i in self.clashes:
                p.setPen(QtGui.QPen(QtGui.QColor("#000000"), 1.5))
                p.setBrush(QtGui.QColor("#FFFFFF"))
                p.drawEllipse(QPointF(i * w + w / 2, self.height() / 2.0), 3, 3)
        p.end()


class CvdPopup(QtWidgets.QFrame):
    def __init__(self, parent, pal):
        super().__init__(parent, PopupFlag)
        self.setProperty("cls", "popup")
        self.setFixedWidth(400)
        g = QtWidgets.QGridLayout(self)
        g.setContentsMargins(12, 10, 12, 12)
        g.setHorizontalSpacing(10)
        g.setVerticalSpacing(6)
        g.addWidget(mk_label("Colour-vision check", "lbl"), 0, 0, 1, 2)
        note = mk_label("● too close to tell apart", "cap")
        note.setAlignment(AlignRight | AlignVCenter)
        g.addWidget(note, 0, 1, 1, 2)
        rows = [("normal", "Normal"), ("deutan", "Deutan"), ("protan", "Protan"), ("tritan", "Tritan")]
        for r, (k, name) in enumerate(rows, start=1):
            sim = [simulate_cvd(h, k) for h in pal]
            m, _ = min_pair(sim)
            bad = set()
            for i in range(len(sim)):
                for j in range(i + 1, len(sim)):
                    if delta_e(sim[i], sim[j]) < 6:
                        bad.update((i, j))
            col = BAD if m < 6 else (WARN if m < 10 else OK)
            g.addWidget(QtWidgets.QLabel(name), r, 0)
            g.addWidget(Strip(sim, bad), r, 1)
            de = QtWidgets.QLabel(f"ΔE {m:.0f}" if m != float("inf") else "ΔE –")
            de.setFont(mono_font(11, True))
            de.setStyleSheet(f"color:{col};")
            de.setAlignment(AlignRight | AlignVCenter)
            g.addWidget(de, r, 2)
        g.setColumnStretch(1, 1)


# ==========================================
# PYMERAX ENGINE (PyMOL Only)
# ==========================================
def _pmx_set_bg():
    cmd.set_color("pymerax_bg", [0.84, 0.84, 0.84])
    cmd.bg_color("pymerax_bg")


def _pmx_base():
    for k, v in {"orthoscopic": 1, "antialias": 2, "ray_trace_mode": 0, "ray_trace_gain": 0.12, "ray_trace_fog": 0,
                 "ray_opaque_background": 0, "depth_cue": 0, "hash_max": 300}.items():
        cmd.set(k, v)


def _pmx_lights():
    for k, v in {"ambient": 0.40, "direct": 0.40, "reflect": 0.20, "specular": 0.08, "shininess": 8,
                 "spec_direct": 0, "light_count": 8}.items():
        cmd.set(k, v)
    cmd.set("light", (-0.4, -0.3, -1.0))
    cmd.set("light2", (-0.8, -0.2, 0.2))
    cmd.set("light3", (0.6, -0.7, -0.1))


def _pmx_ao(mode, scale, smooth):
    try:
        cmd.set("ambient_occlusion_mode", mode)
        cmd.set("ambient_occlusion_scale", scale)
        cmd.set("ambient_occlusion_smooth", smooth)
    except Exception:
        pass


def _pmx_cartoon():
    cmd.hide("everything")
    cmd.show("cartoon")
    for k, v in {"cartoon_fancy_helices": 1, "cartoon_oval_length": 1.2, "cartoon_oval_width": 1.1,
                 "cartoon_sampling": 20, "cartoon_smooth_loops": 1, "cartoon_flat_sheets": 0,
                 "cartoon_highlight_color": -1}.items():
        cmd.set(k, v)
    _pmx_ao(1, 10, 8)


def _pmx_surface():
    cmd.hide("everything")
    for k, v in {"surface_quality": 1, "surface_smooth_edges": 1, "surface_solvent": 0, "transparency": 0,
                 "transparency_mode": 2, "two_sided_lighting": 1, "ambient": 0.46, "direct": 0.30, "reflect": 0.34,
                 "specular": 0.02, "shininess": 2, "ray_shadows": 1, "ray_shadow_decay_factor": 0.08,
                 "ray_shadow_decay_range": 4.5}.items():
        cmd.set(k, v)
    cmd.set("light", (-0.3, -0.2, -1.0))
    cmd.set("light2", (-1.0, 0.0, 0.4))
    cmd.set("light3", (0.8, -0.5, 0.2))
    _pmx_ao(2, 14, 14)
    cmd.show("surface", "polymer")


def _pmx_ligand():
    cmd.hide("everything")
    cmd.show("cartoon")
    cmd.show("sticks", "organic")
    cmd.set("cartoon_transparency", 0.6)
    try:
        cmd.zoom("organic", buffer=4.0, animate=-1)
    except Exception:
        pass
    for k, v in {"stick_radius": 0.18, "stick_ball": 1, "stick_ball_ratio": 1.5, "valence": 1,
                 "specular": 0.20, "shininess": 18}.items():
        cmd.set(k, v)


def pymerax_apply(mode="cartoon"):
    if ENV != "pymol":
        print("MolNympheas: PyMeraX features are only active inside PyMOL.")
        return False
    cmd.reinitialize("settings")
    mode = mode.lower().strip()
    _pmx_set_bg()
    _pmx_base()
    _pmx_lights()
    if mode == "cartoon":
        _pmx_cartoon()
    elif mode == "surface":
        _pmx_surface()
    elif mode == "publication":
        _pmx_cartoon()
        cmd.bg_color("white")
        cmd.set("ray_trace_mode", 1)
        cmd.set("ray_trace_color", "black")
        cmd.set("ray_trace_gain", 0.08)
        cmd.set("ambient", 0.55)
        cmd.set("direct", 0.25)
    elif mode == "ligand":
        _pmx_cartoon()
        _pmx_ligand()
    print(f"MolNympheas: PyMeraX [{mode.upper()}] mode applied!")
    return True


# ==========================================
# HELP TEXTS
# ==========================================
_GEST = ("<p style='color:%s;font-size:11px;margin-top:6px'><b>On every colour:</b> click to apply to the target · "
         "hover for Copy / Edit / ⋯ · double-click to edit · right-click for all actions. "
         "The pink name under a colour shows where you applied it.</p>") % MUTED
HELP = {
    "cmap": "<b>Colormaps</b><p>Takes evenly spaced colours from a scientific colormap. Use the Colours counter to choose how many.</p><ul>"
            "<li><b>Sequential</b>: values that only go up, such as B-factor, pLDDT or residue number.</li>"
            "<li><b>Diverging</b>: values with a meaningful middle, such as charge or a difference between two states. "
            "The <b>dark centre</b> maps (berlin, managua, vanimo) work best on a black background.</li>"
            "<li><b>Qualitative</b>: separate things such as chains, domains or ligands. The colours are taken in order.</li>"
            "<li><b>Range</b> trims the ends of the map, useful when the palest or darkest colours disappear against "
            "your background. <b>⇄</b> reverses the map.</li>"
            "<li>Type in the list to search by name or family. <b>CVD-safe</b> maps stay readable for colour-blind viewers.</li></ul>" + _GEST,
    "harm": "<b>Harmony</b><p>Builds a palette from one <b>seed</b> colour and a <b>rule</b>. Drag the seed around the wheel or type a hex code.</p><ul>"
            "<li><b>Colour wheel</b> rules place hues at fixed angles. <b>Light &amp; shade</b> keeps one hue. "
            "<b>Mood</b> sets the overall feel. <b>For structures</b> rules are built for chains, domains and data.</li>"
            "<li><b>Spread</b>: how far apart neighbouring hues are. <b>Variation</b>: how much the lightness changes "
            "between colours. Sliders that don't apply to the rule are greyed out.</li>"
            "<li><b>Lightness</b> and <b>Vibrance</b> shift the whole palette. The presets set both for common uses.</li>"
            "<li><b>Perceptual</b> makes every colour look equally strong. <b>Classic HSV</b> is the v5 behaviour.</li>"
            "<li><b>Order → Max contrast</b> puts very different colours side by side, useful when neighbouring chains "
            "touch. <b>Vary</b> gives a new variant of the same rule.</li></ul>" + _GEST,
    "custom": "<b>Custom</b><p>Your own palette, edited colour by colour.</p><ul>"
              "<li><b>+</b> adds a colour. Double-click a colour, or use its pencil icon, to type or paste a hex code.</li>"
              "<li>Right-click a colour to pick it from a colour dialog, paste from the clipboard, duplicate or delete it.</li>"
              "<li>From Colormaps or Harmony, double-click any colour to copy that whole palette here for editing.</li>"
              "<li><b>Load JSON</b> opens a saved palette. Export (download icon) saves JSON, Adobe ASE, or PyMOL / "
              "ChimeraX scripts.</li></ul>" + _GEST,
    "render": "<b>Render</b><p>Rendering presets for the whole PyMOL session, inspired by ChimeraX's look. They change "
              "lighting, shadows and background, not your colours.</p><ul>"
              "<li><b>Cartoon</b> and <b>Surface</b> are for working on screen.</li>"
              "<li><b>Publication</b> switches to a white background with outlines. Then type <code>ray 2400</code> in PyMOL.</li>"
              "<li><b>Ligand highlight</b> greys the protein so the ligand stands out.</li>"
              "<li>Each mode replaces your current lighting settings.</li></ul>",
}

PRESETS = [("Surfaces · pastel", 0.12, 0.6), ("Cartoon · vivid", 0.0, 1.25), ("Print · muted", -0.05, 0.7),
           ("Dark background", 0.15, 1.15), ("Reset", 0.0, 1.0)]


# ==========================================
# MAIN WINDOW
# ==========================================
class MolNympheasUI(QtWidgets.QMainWindow):
    TABS = ("cmap", "harm", "custom", "render")

    def __init__(self):
        super().__init__()
        self.setObjectName("mnRoot")
        self.setWindowTitle(f"MolNympheas v6 — {ENV.capitalize() if ENV != 'chimerax' else 'ChimeraX'}")
        self.setStyleSheet(QSS + arrow_qss())
        self.setMinimumWidth(640)

        # --- state
        self.tab = "cmap"
        self.pal = {"cmap": [], "harm": [], "custom": OKABE_ITO[:6]}
        self.hist = {k: {"u": [], "r": []} for k in ("cmap", "harm", "custom")}
        self.n = {"cmap": 7, "harm": 6}
        self.catalogue = build_catalogue()
        self.cat_by_name = {e.name: e for e in self.catalogue}
        first = "viridis" if "viridis" in self.cat_by_name else self.catalogue[0].name
        self.cm = {"name": first, "rev": False, "a": 0.0, "b": 1.0}
        self.hs = {"seed": "#D63F79", "rule": "split", "engine": "oklch", "spread": 30, "variation": 0.5,
                   "light": 0.0, "vib": 1.0, "order": "gen", "jitter": 0}
        self.pts = []
        self.assign = {}
        self._snap = None
        self._pix_cache = {}
        self._msg_timer = QtCore.QTimer(self)
        self._msg_timer.setSingleShot(True)
        self._msg_timer.timeout.connect(lambda: (setattr(self, "_flash", False), self.hint()))
        self._flash = False

        self._build()
        self.refresh_targets()
        self.gen_cmap(False)
        self.pts = harmony_points(self.hs["seed"], self.hs["rule"], self.n["harm"], self.hs)
        self.pal["harm"] = [p["hex"] for p in self.pts]
        self.sync_cmap_ui()
        self.sync_harm_ui()
        self.switch_tab("cmap")
        self.resize(760, 640)

    # ------------------------------------------------------------------ build
    def _build(self):
        central = QtWidgets.QFrame()
        central.setObjectName("mnCentral")
        self.setCentralWidget(central)
        root = QtWidgets.QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.ribbon = Ribbon()
        root.addWidget(self.ribbon)

        # header
        self.logo = Logo()
        title = QtWidgets.QLabel("MolNympheas")
        title.setFont(ui_font(15, WDemi))
        env = mk_label({"pymol": "PyMOL", "chimerax": "ChimeraX"}.get(ENV, "Standalone"), "env")
        self.target = TargetCombo(lambda: self.refresh_targets(quiet=True))
        self.target.setProperty("cls", "fld")
        self.target.setEditable(True)
        self.target.setMaxVisibleItems(20)
        self._target_timer = QtCore.QTimer(self)
        self._target_timer.timeout.connect(self.auto_refresh_targets)
        self._target_timer.start(3000)
        self.target.setMinimumWidth(170)
        self.target.setToolTip("Object or selection the colours are applied to. You can type any selection.")
        self.target.currentTextChanged.connect(lambda _: self.hint())
        ref = mk_ib("refresh", "Refresh objects and selections")
        ref.clicked.connect(lambda: self.refresh_targets(announce=True))
        root.addLayout(hbox(self.logo, title, env, None, mk_label("Target", "lbl"), self.target, ref,
                            margins=(16, 12, 16, 10), spacing=8))

        # tabs + help
        tabs = mk_frame("tabs")
        tl = hbox(margins=(4, 4, 4, 4), spacing=4)
        tabs.setLayout(tl)
        self.tab_group = QtWidgets.QButtonGroup(self)
        self.tab_btns = {}
        for key, name in zip(self.TABS, ("Colormaps", "Harmony", "Custom", "Render")):
            b = mk_btn(name, "tab")
            b.setCheckable(True)
            b.clicked.connect(lambda _=False, k=key: self.switch_tab(k))
            self.tab_group.addButton(b)
            tl.addWidget(b, 1)
            self.tab_btns[key] = b
        if ENV == "chimerax":
            self.tab_btns["render"].hide()
        self.help_btn = mk_ib("help", "Help for this tab", checkable=True, size=18)
        self.help_btn.toggled.connect(self.render_help)
        row = hbox(tabs, self.help_btn, margins=(16, 0, 16, 0), spacing=6)
        row.setStretch(0, 1)
        root.addLayout(row)

        # everything below the tabs scrolls, so nothing gets squeezed on small screens
        scroll = QtWidgets.QScrollArea()
        scroll.setObjectName("mnScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(_e(QtWidgets.QFrame, "Shape", "NoFrame"))
        scroll.setHorizontalScrollBarPolicy(ScrollOff)
        body = FitBody()
        body.setObjectName("mnBody")
        self.body = body
        scroll.setWidget(body)
        top = root
        root = QtWidgets.QVBoxLayout(body)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        top.addWidget(scroll, 1)

        self.help = mk_frame("help")
        self.help_text = QtWidgets.QLabel()
        self.help_text.setWordWrap(True)
        self.help_text.setOpenExternalLinks(False)
        close = mk_ib("x", "Close help", size=14)
        close.clicked.connect(lambda: self.help_btn.setChecked(False))
        hl = hbox(self.help_text, margins=(14, 10, 8, 10), spacing=6)
        hl.addWidget(close, 0, AlignTop)
        hl.setStretch(0, 1)
        self.help.setLayout(hl)
        self.help.hide()
        wrap = QtWidgets.QVBoxLayout()
        wrap.setContentsMargins(16, 10, 16, 0)
        wrap.addWidget(self.help)
        root.addLayout(wrap)

        # panels
        self.panels = {"cmap": self._panel_cmap(), "harm": self._panel_harm(),
                       "custom": self._panel_custom(), "render": self._panel_render()}
        for p in self.panels.values():
            root.addWidget(p)

        # workspace
        self.work = QtWidgets.QWidget()
        wl = QtWidgets.QVBoxLayout(self.work)
        wl.setContentsMargins(16, 6, 16, 12)
        wl.setSpacing(6)
        wl.addWidget(mk_frame("hline"))
        stepper = mk_frame("stepper")
        self.n_minus = mk_ib("minus", "One colour fewer", size=14)
        self.n_plus = mk_ib("plus", "One colour more", size=14)
        self.n_val = QtWidgets.QLabel("7")
        self.n_val.setFont(ui_font(13, WDemi))
        self.n_val.setMinimumWidth(22)
        self.n_val.setAlignment(AlignCenter)
        stepper.setLayout(hbox(self.n_minus, self.n_val, self.n_plus, margins=(2, 2, 2, 2), spacing=0))
        self.n_minus.clicked.connect(lambda: self.step_count(-1))
        self.n_plus.clicked.connect(lambda: self.step_count(1))
        self.undo_btn = mk_ib("undo", "Undo (Ctrl+Z)")
        self.redo_btn = mk_ib("redo", "Redo (Ctrl+Shift+Z)")
        self.undo_btn.clicked.connect(lambda: self.history(-1))
        self.redo_btn.clicked.connect(lambda: self.history(1))
        self.cvd_btn = mk_ib("eye", "Colour-vision check")
        self.cvd_btn.clicked.connect(self.show_cvd)
        copy_all = mk_ib("copy", "Copy the whole palette as a Python list")
        copy_all.clicked.connect(self.copy_all)
        self.export_btn = mk_ib("download", "Export palette")
        self.export_btn.clicked.connect(self.export_menu)
        wl.addLayout(hbox(mk_label("Colours", "lbl"), stepper, None, self.undo_btn, self.redo_btn,
                          mk_frame("vline"), self.cvd_btn, copy_all, self.export_btn, spacing=4))
        self.tiles_host = QtWidgets.QWidget()
        self.tiles = FlowLayout(self.tiles_host, 8, 6)
        wl.addWidget(self.tiles_host)
        self.session_host = QtWidgets.QWidget()
        self.session = FlowLayout(self.session_host, 6, 6)
        wl.addWidget(self.session_host)
        root.addWidget(self.work)
        root.addStretch(1)
        root = top

        # footer / status
        foot = mk_frame("footer")
        self.msg = mk_label("", "msg", wrap=True)
        self.metric = mk_label("", "metric")
        self.metric.setToolTip("Smallest perceptual distance between two colours (OKLab ΔE), in normal vision and "
                               "for deuteranopia. Below 6 they are hard to tell apart.")
        fl = hbox(self.msg, self.metric, margins=(16, 8, 16, 8), spacing=12)
        fl.setStretch(0, 1)
        foot.setLayout(fl)
        root.addWidget(foot)

        z = QShortcut(QtGui.QKeySequence(_e(QtGui.QKeySequence, "StandardKey", "Undo")), self)
        z.activated.connect(lambda: self.history(-1))
        y = QShortcut(QtGui.QKeySequence(_e(QtGui.QKeySequence, "StandardKey", "Redo")), self)
        y.activated.connect(lambda: self.history(1))

    def _panel(self):
        w = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(w)
        lay.setContentsMargins(16, 14, 16, 6)
        lay.setSpacing(12)
        return w, lay

    def _panel_cmap(self):
        w, lay = self._panel()
        self.cmap_btn = PickerButton()
        self.cmap_popup = PickerPopup(self, self.cmap_entries, search=f"Search {len(self.catalogue)} colormaps")
        self.cmap_popup.chosen.connect(self.choose_cmap)
        self.cmap_btn.clicked.connect(lambda: self.cmap_popup.open_below(self.cmap_btn))
        self.rev_btn = mk_ib("swap", "Reverse the colormap", checkable=True)
        self.rev_btn.toggled.connect(self.toggle_reverse)
        lay.addLayout(hbox(self.cmap_btn, self.rev_btn))
        self.range = RangeSlider()
        self.range.changed.connect(self.on_range)
        self.range_lbl = QtWidgets.QLabel("0.00 – 1.00")
        self.range_lbl.setFont(mono_font(11))
        self.range_lbl.setMinimumWidth(90)
        r = hbox(mk_label("Range", "lbl"), self.range, self.range_lbl, spacing=10)
        r.setStretch(1, 1)
        lay.addLayout(r)
        return w

    def _panel_harm(self):
        w, lay = self._panel()
        seed = mk_frame("seedbox")
        self.seed_sw = QtWidgets.QPushButton()
        self.seed_sw.setProperty("cls", "swatch")
        self.seed_sw.setFixedSize(28, 28)
        self.seed_sw.setCursor(PointingHand)
        self.seed_sw.setToolTip("Pick the seed colour")
        self.seed_sw.clicked.connect(self.pick_seed)
        self.seed_hex = QtWidgets.QLineEdit()
        self.seed_hex.setProperty("cls", "seedhex")
        self.seed_hex.setFont(mono_font(13))
        self.seed_hex.setFixedWidth(82)
        self.seed_hex.setMaxLength(9)
        self.seed_hex.setToolTip("Seed hex code. Press Enter to apply.")
        self.seed_hex.editingFinished.connect(self.seed_typed)
        paste = mk_ib("paste", "Paste a hex code from the clipboard", size=14)
        paste.clicked.connect(self.paste_seed)
        seed.setLayout(hbox(self.seed_sw, self.seed_hex, paste, margins=(3, 3, 3, 3), spacing=1))
        self.rule_btn = PickerButton()
        self.rule_popup = PickerPopup(self, self.rule_entries, width=420)
        self.rule_popup.chosen.connect(self.choose_rule)
        self.rule_btn.clicked.connect(lambda: self.rule_popup.open_below(self.rule_btn))
        r1 = hbox(seed, self.rule_btn)
        r1.setStretch(1, 1)
        lay.addLayout(r1)

        self.wheel = HueWheel()
        self.wheel.dragged.connect(self.wheel_drag)
        self.wheel.released.connect(self.wheel_release)
        cap = mk_label("Drag to turn the seed", "cap")
        cap.setAlignment(AlignCenter)
        wb = QtWidgets.QVBoxLayout()
        wb.setSpacing(4)
        wb.addWidget(self.wheel, 0, AlignCenter)
        wb.addWidget(cap)

        grid = QtWidgets.QGridLayout()
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(10)
        self.sliders = {}
        specs = [("spread", "Spread", 10, 90, 1, lambda v: f"{v}°"),
                 ("variation", "Variation", 0, 100, 100.0, lambda v: f"{v}%"),
                 ("light", "Lightness", -25, 25, 100.0, lambda v: f"{v:+d}" if v else "0"),
                 ("vib", "Vibrance", 30, 160, 100.0, lambda v: f"{v}%")]
        for idx, (key, name, lo, hi, scale, fmt) in enumerate(specs):
            box = QtWidgets.QWidget()
            bl = QtWidgets.QVBoxLayout(box)
            bl.setContentsMargins(0, 0, 0, 0)
            bl.setSpacing(4)
            nl = mk_label(name, "hint")
            nl.setFont(ui_font(12))
            vl = mk_label("", "val")
            vl.setFont(mono_font(11))
            s = QtWidgets.QSlider(Horizontal)
            s.setRange(lo, hi)
            s.setCursor(PointingHand)
            s.valueChanged.connect(lambda v, k=key: self.on_slider(k, v))
            s.sliderPressed.connect(self.snapshot)
            s.sliderReleased.connect(lambda: self.gen_harm(True, base=self._take_snap()))
            bl.addLayout(hbox(nl, None, vl))
            bl.addWidget(s)
            grid.addWidget(box, idx // 2, idx % 2)
            self.sliders[key] = (s, vl, scale, fmt, box)
        hg = hbox(spacing=18)
        hg.addLayout(wb)
        hg.addLayout(grid, 1)
        lay.addLayout(hg)

        seg = mk_frame("seg")
        sl = hbox(margins=(2, 2, 2, 2), spacing=0)
        seg.setLayout(sl)
        self.eng_btns = {}
        eg = QtWidgets.QButtonGroup(self)
        for key, name, tip in (("oklch", "Perceptual", "Hue steps that look even to the eye (OKLCH)"),
                               ("hsv", "Classic HSV", "Classic HSV maths, as in v5")):
            b = mk_btn(name, "segb")
            b.setCheckable(True)
            b.setToolTip(tip)
            b.clicked.connect(lambda _=False, k=key: self.set_harm("engine", k))
            eg.addButton(b)
            sl.addWidget(b)
            self.eng_btns[key] = b
        self.order = QtWidgets.QComboBox()
        self.order.setProperty("cls", "fld")
        for key, name in (("gen", "As generated"), ("contrast", "Max contrast between neighbours"),
                          ("hue", "By hue"), ("light", "Light to dark")):
            self.order.addItem(name, key)
        self.order.setSizeAdjustPolicy(_e(QtWidgets.QComboBox, "SizeAdjustPolicy",
                                          "AdjustToMinimumContentsLengthWithIcon"))
        self.order.setMinimumContentsLength(14)
        self.order.currentIndexChanged.connect(lambda i: self.set_harm("order", self.order.itemData(i)))
        vary = mk_btn("Vary", icon="shuffle")
        vary.setToolTip("Small random shifts in hue and lightness. Undo to go back.")
        vary.clicked.connect(self.vary)
        lay.addLayout(hbox(seg, 6, mk_label("Order", "lbl"), self.order, vary, None, spacing=8))

        self.preset_btns = []
        host = QtWidgets.QWidget()
        flow = FlowLayout(host, 6, 6)
        plab = mk_label("Presets", "lbl")
        plab.setFixedHeight(26)
        flow.addWidget(plab)
        for name, light, vib in PRESETS:
            b = mk_btn(name, "chip")
            b.setIconSize(QSize(28, 8))
            b.clicked.connect(lambda _=False, l=light, v=vib, nm=name: self.apply_preset(l, v, nm))
            flow.addWidget(b)
            self.preset_btns.append((b, light, vib))
        lay.addWidget(host)
        return w

    def _panel_custom(self):
        w, lay = self._panel()
        load = mk_btn("Load JSON", icon="upload")
        load.clicked.connect(self.load_json)
        lay.addLayout(hbox(mk_label("Build a palette tile by tile. Double-click a tile to type a hex code.", "hint"),
                           None, load))
        return w

    def _panel_render(self):
        w, lay = self._panel()
        lay.addWidget(mk_label("One-click ChimeraX-style rendering for the PyMOL session. "
                               "This resets your current lighting settings.", "hint", wrap=True))
        grid = QtWidgets.QGridLayout()
        grid.setSpacing(10)
        self.render_glyphs = []
        cards = [("cartoon", "Cartoon", "Soft ambient occlusion, matte ribbons"),
                 ("surface", "Surface", "Shaded solvent-accessible surface"),
                 ("publication", "Publication", "White background, outlines, ready to ray"),
                 ("ligand", "Ligand highlight", "Greyed protein, glowing ligand")]
        for i, (mode, name, desc) in enumerate(cards):
            b = QtWidgets.QPushButton()
            b.setProperty("cls", "card")
            b.setCursor(PointingHand)
            b.setMinimumHeight(62)
            glyph = QtWidgets.QLabel()
            glyph.setFixedSize(36, 36)
            self.render_glyphs.append(glyph)
            t = QtWidgets.QLabel(f"<b>{name}</b><br><span style='color:{MUTED};font-size:12px'>{desc}</span>")
            for x in (glyph, t):
                x.setAttribute(TransparentForMouse)
            b.setLayout(hbox(glyph, t, None, margins=(12, 10, 12, 10), spacing=12))
            b.clicked.connect(lambda _=False, m=mode, nm=name: self.render_mode(m, nm))
            grid.addWidget(b, i // 2, i % 2)
        lay.addLayout(grid)
        lay.addWidget(mk_label("After Publication, type <code>ray 2400</code> in the PyMOL console for the final image.",
                               "hint", wrap=True))
        return w

    # ------------------------------------------------------------ status bar
    def hint(self, html=None):
        if self._flash:
            return
        if html is None:
            html = ("Pick a rendering mode. It applies to the whole PyMOL session." if self.tab == "render" else
                    f"Click a colour to apply it to <b>{esc(self.target_text())}</b> · hover for actions · "
                    f"right-click for more")
        self.msg.setStyleSheet(f"color:{MUTED};")
        self.msg.setText(html)

    def say(self, html):
        self._flash = True
        self.msg.setStyleSheet(f"color:{INK};")
        self.msg.setText(html)
        self._msg_timer.start(3200)

    def hint_tile(self, i):
        pal = self.pal.get(self.tab) or []
        if i >= len(pal):
            return
        hx = pal[i]
        tg = self.targets_for(hx)
        on = f" · on <b style='color:{ACCENT}'>{esc(', '.join(tg))}</b>" if tg else ""
        dbl = "edit" if self.tab == "custom" else "edit in Custom"
        self.hint(f"<b style='color:{INK}'>{hx}</b>{on} · Click: apply to <b>{esc(self.target_text())}</b> · "
                  f"Double-click: {dbl} · Right-click: more")

    def update_metric(self):
        pal = self.cur_pal()
        if len(pal) < 2:
            self.metric.setText("One colour")
            return
        a, _ = min_pair(pal)
        d, _ = min_pair([simulate_cvd(h, "deutan") for h in pal])
        w = min(a, d)
        col, word = (BAD, "too close") if w < 6 else ((WARN, "tight") if w < 10 else (OK, "clear"))
        self.metric.setText(f"<span style='color:{col}'>●</span> Closest pair ΔE {a:.0f} · deutan {d:.0f} · {word}")

    # ------------------------------------------------------------- palettes
    def cur_pal(self):
        return self.pal["harm"] if self.tab == "render" else self.pal[self.tab]

    def set_pal(self, tab, arr, record=True, base=None):
        prev = base if base is not None else self.pal[tab]
        if record and prev and list(prev) != list(arr):
            h = self.hist[tab]
            h["u"].append(list(prev))
            del h["u"][:-60]
            h["r"] = []
        self.pal[tab] = list(arr)
        if tab == self.tab:
            self.render_tiles()

    def history(self, d):
        if self.tab not in self.hist:
            return
        h = self.hist[self.tab]
        src, dst = (h["u"], h["r"]) if d < 0 else (h["r"], h["u"])
        if not src:
            return
        dst.append(list(self.pal[self.tab]))
        self.pal[self.tab] = src.pop()
        self.render_tiles()
        self.say("Undone" if d < 0 else "Redone")

    def snapshot(self):
        self._snap = list(self.pal[self.tab]) if self.tab in self.pal else None

    def _take_snap(self):
        s, self._snap = self._snap, None
        return s

    def step_count(self, d):
        if self.tab == "custom":
            if d > 0:
                self.add_color()
            else:
                self.remove_color(len(self.pal["custom"]) - 1)
            return
        self.n[self.tab] = int(clamp(self.n[self.tab] + d, 2, 30))
        self.regen(True)

    def regen(self, record=True):
        if self.tab == "cmap":
            self.gen_cmap(record)
        elif self.tab == "harm":
            self.gen_harm(record)

    def gen_cmap(self, record=True, base=None):
        e = self.cat_by_name[self.cm["name"]]
        self.set_pal("cmap", cmap_colors(e, self.n["cmap"], self.cm["a"], self.cm["b"], self.cm["rev"]), record, base)

    def gen_harm(self, record=True, base=None):
        self.pts = harmony_points(self.hs["seed"], self.hs["rule"], self.n["harm"], self.hs)
        self.set_pal("harm", [p["hex"] for p in self.pts], record, base)
        self.wheel.set_data(self.pts, self.hs["engine"], self.hs["seed"])

    # ---------------------------------------------------------------- tiles
    def render_tiles(self):
        if self.tab == "render":
            self.paint_chrome()
            return
        pal = self.pal[self.tab]
        editable = self.tab == "custom"
        self.tiles.clear()
        for i, hx in enumerate(pal):
            tg = self.targets_for(hx)
            label = (tg[0] + (f" +{len(tg) - 1}" if len(tg) > 1 else "")) if tg else ""
            self.tiles.addWidget(ColorTile(self, i, hx, editable, label, ", ".join(tg)))
        if editable:
            add = AddTile()
            add.clicked.connect(self.add_color)
            self.tiles.addWidget(add)
        self.tiles_host.updateGeometry()
        self.n_val.setText(str(len(pal)))
        self.n_minus.setToolTip("Remove the last colour" if editable else "One colour fewer")
        self.n_plus.setToolTip("Add a colour" if editable else "One colour more")
        h = self.hist[self.tab]
        self.undo_btn.setEnabled(bool(h["u"]))
        self.redo_btn.setEnabled(bool(h["r"]))
        self.paint_chrome()
        self.update_metric()
        self.render_session()
        if self.tab == "harm":
            self.refresh_presets()
        self.refit()

    def refit(self):
        QtCore.QTimer.singleShot(0, self.body.fit)

    def tile_widget(self, i):
        for k in range(self.tiles.count()):
            w = self.tiles.itemAt(k).widget()
            if isinstance(w, ColorTile) and w.i == i:
                return w
        return None

    def focus_tile(self, i):
        w = self.tile_widget(i)
        if w is not None:
            w.setFocus()

    def tile_double(self, i):
        if self.tab == "custom":
            w = self.tile_widget(i)
            if w:
                w.start_edit()
        else:
            self.send_to_custom()

    def commit_tile_edit(self, i, text):
        if text is None:
            self.render_tiles()
            self.focus_tile(i)
            return
        v = norm_hex(text)
        if v is None:
            self.say("That is not a hex code. Try <b>#3B528B</b> or <b>3B528B</b>.")
            QtCore.QTimer.singleShot(0, self.render_tiles)
        elif v != self.pal["custom"][i]:
            arr = list(self.pal["custom"])
            arr[i] = v
            QtCore.QTimer.singleShot(0, lambda: (self.set_pal("custom", arr), self.focus_tile(i)))
            self.say(f"Colour {i + 1} set to {v}")
        else:
            QtCore.QTimer.singleShot(0, self.render_tiles)

    def set_custom(self, i, v):
        arr = list(self.pal["custom"])
        arr[i] = v
        self.set_pal("custom", arr)

    def add_color(self):
        p = self.pal["custom"]
        # try hues and lightnesses, keep the candidate farthest from every existing colour
        cands = [oklch_to_hex(L, 0.14, h) for L in (0.5, 0.65, 0.8) for h in range(0, 360, 15)]
        new = max(cands, key=lambda c: min((delta_e(c, q) for q in p), default=100))
        self.set_pal("custom", p + [new])
        self.say("Colour added. Double-click it to edit.")

    def remove_color(self, i):
        if len(self.pal["custom"]) <= 1:
            self.say("A palette needs at least one colour.")
            return
        arr = list(self.pal["custom"])
        gone = arr.pop(i)
        self.set_pal("custom", arr)
        self.say(f"Removed {gone} · Undo brings it back")
        self.focus_tile(min(i, len(arr) - 1))

    def send_to_custom(self):
        self.set_pal("custom", list(self.pal[self.tab]))
        self.switch_tab("custom")
        self.say("Palette copied to Custom. Double-click a tile to edit it.")

    def tile_menu(self, i, gpos):
        pal = self.pal[self.tab]
        if i >= len(pal):
            return
        hx = pal[i]
        tile = self.tile_widget(i)
        m = QtWidgets.QMenu(self)
        head = m.addAction(QtGui.QIcon(dots_pixmap([hx], 10, round_=True)), f"{hx} · colour {i + 1}")
        head.setEnabled(False)
        m.addSeparator()
        m.addAction(f"Apply to {self.target_text()}\tEnter").triggered.connect(lambda: self.apply_color(hx, i))
        m.addSeparator()
        m.addAction("Copy HEX\tC").triggered.connect(lambda: self.copy_text(hx))
        m.addAction("Copy RGB (0–1)").triggered.connect(lambda: self.copy_text(rgb01(hx)))
        m.addAction("Copy PyMOL set_color").triggered.connect(
            lambda: self.copy_text(f"set_color mn_{hx[1:].lower()}, {rgb01(hx)}"))
        m.addAction("Copy ChimeraX command").triggered.connect(
            lambda: self.copy_text(f"color {self.target_text() if ENV == 'chimerax' else 'sel'} {hx}"))
        m.addSeparator()
        m.addAction("Use as Harmony seed").triggered.connect(lambda: self.use_as_seed(hx))
        if self.tab == "custom":
            m.addAction("Edit hex\tDouble-click").triggered.connect(lambda: tile and tile.start_edit())
            m.addAction("Pick colour…").triggered.connect(lambda: self.pick_for(i))
            m.addAction("Paste hex from clipboard").triggered.connect(lambda: self.paste_into(i))
            m.addAction("Duplicate").triggered.connect(
                lambda: self.set_pal("custom", pal[:i + 1] + [hx] + pal[i + 1:]))
            m.addAction("Delete\tDel").triggered.connect(lambda: self.remove_color(i))
        else:
            m.addAction("Edit palette in Custom\tDouble-click").triggered.connect(self.send_to_custom)
        tg = self.targets_for(hx)
        if tg:
            m.addSeparator()
            m.addAction(f"Forget label ({', '.join(tg)})").triggered.connect(lambda: self.forget(tg))
        if tile:
            tile.menu_open = True
            tile.update()
        _exec(m, gpos)
        if tile is not None:
            try:
                tile.menu_open = False
                tile.update()
            except RuntimeError:
                pass

    def pick_for(self, i):
        c = QtWidgets.QColorDialog.getColor(QtGui.QColor(self.pal["custom"][i]), self, "Pick a colour")
        if c.isValid():
            self.set_custom(i, c.name().upper())

    def paste_into(self, i):
        v = norm_hex(QtWidgets.QApplication.clipboard().text())
        if v:
            self.set_custom(i, v)
            self.say(f"Pasted {v}")
        else:
            self.say("The clipboard doesn't contain a hex code.")

    # ------------------------------------------------------ apply & labels
    def target_text(self):
        return self.target.currentText().strip() or "all"

    def targets_for(self, hx):
        return [t for t, c in self.assign.items() if c == hx]

    def forget(self, tg):
        for t in tg:
            self.assign.pop(t, None)
        self.render_tiles()

    def apply_color(self, hx, i=None):
        sele = self.target_text()
        command = None
        try:
            if ENV == "pymol":
                name = f"mn_{hx[1:].lower()}"
                cmd.set_color(name, list(hex_to_rgb(hx)))
                cmd.color(name, sele)
                command = f"color {name}, {sele}"
            elif ENV == "chimerax":
                command = f"color {sele} {hx}"
                run(globals().get("session"), command)
            else:
                command = f"color {hx}, {sele}"
        except Exception as e:
            self.say(f"<span style='color:{BAD}'>Could not colour <b>{esc(sele)}</b>: {esc(e)}</span>")
            return
        if sele == "all":
            self.assign = {}
        self.assign[sele] = hx
        if self.tab != "render":
            self.render_tiles()
            if i is not None:
                self.focus_tile(i)
        self.say(f"Applied <b>{hx}</b> to <b>{esc(sele)}</b> · <code>{esc(command)}</code>")

    def render_session(self):
        self.session.clear()
        if not self.assign:
            self.session_host.hide()
            return
        self.session_host.show()
        self.session.addWidget(mk_label("Applied", "lbl"))
        for t, hx in self.assign.items():
            b = mk_btn(f"{t}  {hx[1:]}", "chip")
            b.setIcon(QtGui.QIcon(dots_pixmap([hx], 14, round_=True)))
            b.setIconSize(QSize(14, 14))
            b.setToolTip(f"Make {t} the target")
            b.clicked.connect(lambda _=False, tt=t: self.select_target(tt))
            self.session.addWidget(b)
        clr = mk_btn("Clear", "link")
        clr.setToolTip("Clear the labels. Colours in the session are unchanged.")
        clr.clicked.connect(self.clear_labels)
        self.session.addWidget(clr)

    def clear_labels(self):
        self.assign = {}
        self.render_tiles()
        self.say("Labels cleared. Colours in the session are unchanged.")

    def select_target(self, t):
        self.target.setCurrentText(t)
        self.say(f"Target is now <b>{esc(t)}</b>")

    def auto_refresh_targets(self):
        """Quiet periodic check: only touches the list when the session really changed."""
        if not self.isVisible() or self.target.view().isVisible() or self.target.lineEdit().hasFocus():
            return
        self.refresh_targets(quiet=True)

    def refresh_targets(self, announce=False, quiet=False):
        current = self.target.currentText() or ("chain A" if ENV == "standalone" else "all")
        names = ["all"]
        try:
            if ENV == "pymol":
                objs = cmd.get_names("public_objects") or []
                for n in cmd.get_names("public") or []:
                    if n not in names:
                        names.append(n)
                for o in objs:
                    try:
                        chains = [c for c in cmd.get_chains(o) if c]
                    except Exception:
                        chains = []
                    for c in chains:
                        names.append(f"chain {c}" if len(objs) == 1 else f"{o} and chain {c}")
                try:
                    if cmd.count_atoms("organic") > 0:
                        names.append("organic")
                except Exception:
                    pass
            elif ENV == "chimerax":
                ses = chimerax_session()
                names.append("sel")
                if ses is None:
                    raise RuntimeError("no ChimeraX session found")
                for m in ses.models.list():
                    chains = getattr(m, "chains", None)
                    if chains is None and "." in m.id_string:
                        continue  # skip sub-models such as surfaces and labels
                    names.append(f"#{m.id_string}")
                    for ch in chains or []:
                        names.append(f"#{m.id_string}/{ch.chain_id}")
                if len(names) > 2:
                    names += ["protein", "nucleic", "ligand"]  # built-in ChimeraX specifiers
            else:
                names += ["1hsg", "chain A", "chain B", "organic", "sele"]
        except Exception as e:
            if not quiet:
                print(f"MolNympheas Warning: could not list targets. {e}")
        seen, uniq = set(), []
        for n in names:
            if n not in seen:
                seen.add(n)
                uniq.append(n)
        old = [self.target.itemText(i) for i in range(self.target.count())]
        if uniq != old:
            self.target.blockSignals(True)
            self.target.clear()
            self.target.addItems(uniq)
            self.target.setCurrentText(current)
            self.target.blockSignals(False)
        if quiet:
            return
        if announce:
            self.say(f"Found {len(uniq)} objects, chains and selections.")
        else:
            self.hint()

    # -------------------------------------------------------- tab handling
    def switch_tab(self, key):
        self.tab = key
        self.tab_btns[key].setChecked(True)
        for k, p in self.panels.items():
            p.setVisible(k == key)
        self.work.setVisible(key != "render")
        if key == "harm":
            self.sync_harm_ui()
            self.wheel.set_data(self.pts, self.hs["engine"], self.hs["seed"])
        self.render_tiles()
        self.render_help(self.help_btn.isChecked())
        self._flash = False
        self.hint()

    def render_help(self, on):
        self.help.setVisible(bool(on))
        if on:
            self.help_text.setText(HELP[self.tab])
        self.metric.setVisible(self.tab != "render")
        self.refit()

    def paint_chrome(self):
        pal = self.cur_pal() or ["#D63F79"]
        self.ribbon.set_colors(pal)
        self.logo.set_colors(pal)
        for i, g in enumerate(self.render_glyphs):
            a, b = pal[i % len(pal)], pal[(i + 2) % len(pal)]
            pm = _new_pixmap(36, 36)
            p = QtGui.QPainter(pm)
            p.setRenderHint(Antialias)
            grad = QtGui.QRadialGradient(12, 11, 30)
            grad.setColorAt(0, QtGui.QColor("#FFFFFF" if i == 2 else a))
            grad.setColorAt(0.75, QtGui.QColor(a if i == 2 else b))
            p.setPen(NoPen)
            p.setBrush(QtGui.QBrush(grad))
            p.drawEllipse(QRectF(0, 0, 36, 36))
            p.end()
            g.setPixmap(pm)

    # ------------------------------------------------------------ colormaps
    def _cm_pix(self, e, rev, w, h):
        key = (e.name, rev, w, h)
        if key not in self._pix_cache:
            self._pix_cache[key] = gradient_pixmap(cmap_preview(e, rev), w, h, e.qual)
        return self._pix_cache[key]

    def cmap_entries(self):
        return [{"id": e.name, "group": e.group, "name": e.name, "badges": e.badges,
                 "pix": self._cm_pix(e, self.cm["rev"], 88, 12), "current": e.name == self.cm["name"]}
                for e in self.catalogue]

    def sync_cmap_ui(self):
        e = self.cat_by_name[self.cm["name"]]
        self.cmap_btn.set_content(e.name, self._cm_pix(e, self.cm["rev"], 130, 14),
                                  suffix="reversed" if self.cm["rev"] else "", badges=e.badges)
        self.range.set_colors(cmap_preview(e, self.cm["rev"]), e.qual)
        self.range.set_values(self.cm["a"], self.cm["b"])
        self.range.setEnabled(not e.qual)
        self.range.setToolTip("A qualitative set has no range: its colours are taken in order." if e.qual else
                              "Drag the handles to skip the ends of the map")
        self.range_lbl.setText("whole set" if e.qual else f"{self.cm['a']:.2f} – {self.cm['b']:.2f}")
        self.rev_btn.blockSignals(True)
        self.rev_btn.setChecked(self.cm["rev"])
        self.rev_btn.blockSignals(False)

    def choose_cmap(self, name):
        self.cm["name"] = name
        self.sync_cmap_ui()
        self.gen_cmap(True)

    def toggle_reverse(self, on):
        self.cm["rev"] = bool(on)
        self.sync_cmap_ui()
        self.gen_cmap(True)

    def on_range(self, a, b, final):
        if not final and self._snap is None:
            self.snapshot()
        self.cm["a"], self.cm["b"] = a, b
        self.range_lbl.setText(f"{a:.2f} – {b:.2f}")
        self.gen_cmap(final, base=self._take_snap() if final else None)

    # -------------------------------------------------------------- harmony
    def rule_entries(self):
        return [{"id": r[1], "group": r[0], "name": r[2], "desc": r[3], "current": r[1] == self.hs["rule"],
                 "dots": dots_pixmap([p["hex"] for p in harmony_points(self.hs["seed"], r[1], 5, self.hs, True)])}
                for r in RULES]

    def sync_harm_ui(self):
        hs = self.hs
        r = RULE[hs["rule"]]
        self.seed_sw.setStyleSheet(f"background:{hs['seed']}; border-radius:6px;")
        if not self.seed_hex.hasFocus():
            self.seed_hex.setText(hs["seed"])
        self.rule_btn.set_content(r[2], prefix=r[0])
        vals = {"spread": hs["spread"], "variation": round(hs["variation"] * 100),
                "light": round(hs["light"] * 100), "vib": round(hs["vib"] * 100)}
        for key, (s, vl, scale, fmt, box) in self.sliders.items():
            s.blockSignals(True)
            s.setValue(int(vals[key]))
            s.blockSignals(False)
            vl.setText(fmt(int(vals[key])))
            on = key not in ("spread", "variation") or key in r[4]
            s.setEnabled(on)
            box.setToolTip("" if on else f"Not used by {r[2]}")
        self.eng_btns[hs["engine"]].setChecked(True)
        self.order.blockSignals(True)
        self.order.setCurrentIndex(max(0, self.order.findData(hs["order"])))
        self.order.blockSignals(False)

    def refresh_presets(self):
        saved = (self.hs["light"], self.hs["vib"])
        for b, light, vib in self.preset_btns:
            self.hs["light"], self.hs["vib"] = light, vib
            cols = [p["hex"] for p in harmony_points(self.hs["seed"], self.hs["rule"], 3, self.hs, True)]
            b.setIcon(QtGui.QIcon(dots_pixmap(cols, 8, 2, round_=True)))
        self.hs["light"], self.hs["vib"] = saved

    def on_slider(self, key, v):
        s, vl, scale, fmt, _ = self.sliders[key]
        vl.setText(fmt(v))
        self.hs[key] = v if key == "spread" else v / scale
        if s.isSliderDown():
            self.gen_harm(False)
        else:
            self.gen_harm(True)

    def set_harm(self, key, value):
        if value is None or self.hs.get(key) == value:
            return
        self.hs[key] = value
        self.sync_harm_ui()
        self.gen_harm(True)

    def choose_rule(self, rid):
        self.hs["rule"], self.hs["jitter"] = rid, 0
        self.sync_harm_ui()
        self.gen_harm(True)

    def apply_preset(self, light, vib, name):
        self.hs["light"], self.hs["vib"] = light, vib
        self.sync_harm_ui()
        self.gen_harm(True)
        self.say(f"Preset: {esc(name)}")

    def vary(self):
        self.hs["jitter"] = random.randint(1, 10 ** 6)
        self.gen_harm(True)
        self.say("New variation of the same rule. Undo to go back.")

    def set_seed(self, hx, record=True):
        self.hs["seed"] = hx
        self.sync_harm_ui()
        self.gen_harm(record)

    def seed_typed(self):
        v = norm_hex(self.seed_hex.text())
        if v and v != self.hs["seed"]:
            self.set_seed(v)
        elif not v:
            self.say("Type a hex code such as <b>#D63F79</b> or <b>D63F79</b>.")
            self.seed_hex.setText(self.hs["seed"])

    def paste_seed(self):
        v = norm_hex(QtWidgets.QApplication.clipboard().text())
        if v:
            self.set_seed(v)
            self.say(f"Seed set to {v}")
        else:
            self.say("The clipboard doesn't contain a hex code.")

    def pick_seed(self):
        c = QtWidgets.QColorDialog.getColor(QtGui.QColor(self.hs["seed"]), self, "Seed colour")
        if c.isValid():
            self.set_seed(c.name().upper())

    def use_as_seed(self, hx):
        self.switch_tab("harm")
        self.set_seed(hx)
        self.say(f"Seed set to {hx}")

    def wheel_drag(self, hue):
        if self._snap is None:
            self.snapshot()
            L, C, _ = ENGINES[self.hs["engine"]]["base"](self.hs["seed"])
            self._drag_lc = (L, max(C, 0.08))
        L, C = self._drag_lc
        self.hs["seed"] = ENGINES[self.hs["engine"]]["make"](L, C, hue)
        self.sync_harm_ui()
        self.gen_harm(False)

    def wheel_release(self):
        self.gen_harm(True, base=self._take_snap())
        self.say(f"Seed moved to {self.hs['seed']}")

    # ------------------------------------------------------------ toolbar
    def copy_text(self, text, label=None):
        QtWidgets.QApplication.clipboard().setText(text)
        self.say(f"Copied <code>{esc(label or text)}</code>")

    def copy_all(self):
        pal = self.cur_pal()
        self.copy_text("[" + ", ".join(f"'{h}'" for h in pal) + "]", f"{len(pal)} colours as a Python list")

    def show_cvd(self):
        pop = CvdPopup(self, self.cur_pal())
        pop.adjustSize()
        g = self.cvd_btn.mapToGlobal(QPoint(self.cvd_btn.width() - pop.width(), self.cvd_btn.height() + 4))
        pop.move(g)
        pop.show()

    def export_menu(self):
        m = QtWidgets.QMenu(self)
        m.addAction("JSON\t.json").triggered.connect(self.save_json)
        m.addAction("Adobe swatches\t.ase").triggered.connect(self.export_ase)
        m.addSeparator()
        m.addAction("PyMOL script\t.pml").triggered.connect(lambda: self.export_script("pml"))
        m.addAction("ChimeraX script\t.cxc").triggered.connect(lambda: self.export_script("cxc"))
        m.addSeparator()
        m.addAction("Copy as Python list").triggered.connect(self.copy_all)
        _exec(m, self.export_btn.mapToGlobal(QPoint(self.export_btn.width() - 200, self.export_btn.height() + 4)))

    def render_mode(self, mode, name):
        if pymerax_apply(mode):
            self.say(f"{name} rendering applied to the session.")
        else:
            self.say(f"{name} rendering needs PyMOL. Nothing was changed.")

    # ---------------------------------------------------------------- files
    def _save_path(self, title, default, filt):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, title, default, filt)
        return path

    def save_json(self):
        path = self._save_path("Save palette", "molnympheas_palette.json", "JSON Files (*.json);;All Files (*)")
        if not path:
            return
        try:
            with open(path, "w") as f:
                json.dump({"colors": self.cur_pal(), "palette_name": f"molnympheas_{self.tab}"}, f, indent=4)
            self.say(f"Saved {len(self.cur_pal())} colours to {esc(path)}")
        except Exception as e:
            self.say(f"<span style='color:{BAD}'>Could not save: {esc(e)}</span>")

    def load_json(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Load palette", "", "JSON Files (*.json);;All Files (*)")
        if not path:
            return
        try:
            with open(path) as f:
                data = json.load(f)
            cols = [norm_hex(c) for c in data.get("colors", [])]
            cols = [c for c in cols if c]
            if not cols:
                raise ValueError("no hex colours found under 'colors'")
            self.set_pal("custom", cols)
            self.say(f"Loaded {len(cols)} colours into Custom.")
        except Exception as e:
            self.say(f"<span style='color:{BAD}'>Could not load {esc(path)}: {esc(e)}</span>")

    def export_script(self, kind):
        pal = self.cur_pal()
        if kind == "pml":
            path = self._save_path("Export PyMOL script", "molnympheas_palette.pml", "PyMOL scripts (*.pml)")
            lines = ["# MolNympheas palette"] + [f"set_color mn_{i + 1}, {rgb01(h)}  # {h}" for i, h in enumerate(pal)]
        else:
            path = self._save_path("Export ChimeraX script", "molnympheas_palette.cxc", "ChimeraX scripts (*.cxc)")
            lines = ["# MolNympheas palette"] + [f"color name mn_{i + 1} {h}" for i, h in enumerate(pal)]
        if not path:
            return
        try:
            with open(path, "w") as f:
                f.write("\n".join(lines) + "\n")
            self.say(f"Exported {len(pal)} colours to {esc(path)}")
        except Exception as e:
            self.say(f"<span style='color:{BAD}'>Could not export: {esc(e)}</span>")

    def export_ase(self):
        colors = self.cur_pal()
        path = self._save_path("Export as Adobe Swatch (.ase)", "molnympheas_palette.ase", "ASE Files (*.ase)")
        if not path:
            return
        if not path.lower().endswith(".ase"):
            path += ".ase"
        try:
            blocks = b""
            for hx in colors:
                r, g, b = hex_to_rgb(hx)
                name = f"MolNympheas_{hx}".encode("utf-16be") + b"\x00\x00"
                payload = (struct.pack(">H", len(name) // 2) + name + b"RGB " +
                           struct.pack(">fff", r, g, b) + struct.pack(">H", 0))
                blocks += struct.pack(">H", 0x0001) + struct.pack(">I", len(payload)) + payload
            header = b"ASEF" + struct.pack(">HHI", 1, 0, len(colors))
            with open(path, "wb") as f:
                f.write(header + blocks)
            self.say(f"Saved Adobe swatches to {esc(path)}")
        except Exception as e:
            self.say(f"<span style='color:{BAD}'>ASE export failed: {esc(e)}</span>")


# ==========================================
# LAUNCHER
# ==========================================
def launch_app():
    app = QtWidgets.QApplication.instance()
    standalone = app is None
    if standalone:
        app = QtWidgets.QApplication(sys.argv)
    global main_window
    main_window = MolNympheasUI()
    app._molnym_window = main_window  # keep a reference so ChimeraX doesn't garbage-collect it
    main_window.show()
    main_window.raise_()
    if standalone:
        sys.exit(_exec(app))


if __name__ in ("__main__", "pymol") or ENV == "chimerax":
    launch_app()

if ENV == "pymol":
    def __init_plugin__(app=None):
        from pymol.plugins import addmenuitemqt
        addmenuitemqt("MolNympheas", launch_app)
