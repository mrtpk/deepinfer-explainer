"""svglib: helper library for codebase explainer diagrams.

Follows instructions-svg.md (sections 2-9) exactly:
  - canvas width 1100 (site rule, STYLE.md section 10), white background rect, width/height/viewBox match content
  - tokens from section 2, font stacks from section 3
  - inline presentation attributes only (no CSS, no <style>, no classes)
  - coordinates formatted to one decimal, all text escaped
  - one arrow marker per color, created lazily

Usage in a diagram script (see diagrams/_template.py):

    from svglib import Diagram, BLUE, EMERALD, INK, MUTE
    d = Diagram()
    d.header("Title", "Scope  ·  assumptions  ·  summary")
    y = 104
    d.panel(y, 200, 1, "Question?", "One-sentence answer.")
    ...
    d.save(height=y + 20)          # path comes from sys.argv[1]

The Diagram object tracks the right and bottom edge of everything it draws.
save() prints a warning on stderr if something passes the canvas edge
(checklist item "nothing overlaps or clips at the right/bottom edge").
"""

from __future__ import annotations

import sys
from html import escape

# ---- 2.1 Neutrals ----------------------------------------------------------
INK = "#111827"
MUTE = "#6b7280"
GRAY_MID = "#9ca3af"
LINE = "#d1d5db"
BORDER = "#e5e7eb"
PANEL_BG = "#fafafa"
CELL_EMPTY = "#f9fafb"
WHITE = "#ffffff"

# ---- 2.2 Role accents: (strong, tint, extra-pale or None) -----------------
BLUE = ("#2563eb", "#eff6ff", "#f8fbff")
AMBER = ("#d97706", "#fffbeb", "#fffdf6")
VIOLET = ("#7c3aed", "#f5f3ff", "#faf8ff")
TEAL = ("#0d9488", "#f0fdfa", "#f7fefc")
TEAL_STRONG_TINT = "#ccfbf1"
EMERALD = ("#059669", "#ecfdf5", "#f6fdf9")
PINK = ("#db2777", "#fdf2f8", "#fef8fb")
# Neutral "role" for inactive / baseline items: (stroke, fill, pale)
NEUTRAL = (GRAY_MID, BORDER, CELL_EMPTY)

# ---- 2.3 Categorical series ------------------------------------------------
SERIES = ["#2563eb", "#db2777", "#16a34a", "#ea580c", "#7c3aed", "#0891b2", "#ca8a04", "#dc2626"]

# ---- 3 Typography ----------------------------------------------------------
SANS = "Inter,Segoe UI,Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"

W = 1100


def _c(col):
    """Accept a role tuple or a hex string; return the strong color."""
    return col[0] if isinstance(col, tuple) else col


def _t(col):
    """Return the tint of a role tuple (white for a plain hex color)."""
    return col[1] if isinstance(col, tuple) else WHITE


def text_width(s: str, size: float, mono: bool = False, bold: bool = False) -> float:
    """Approximate rendered width of a string (good enough for layout)."""
    if mono:
        return len(s) * size * 0.602
    w = 0.0
    for ch in s:
        if ch in "il.,:;'|!()[]{} ":
            w += 0.30
        elif ch in "mwMW@%":
            w += 0.85
        elif ch.isupper() or ch.isdigit():
            w += 0.64
        else:
            w += 0.53
    return w * size * (1.06 if bold else 1.0)


class Diagram:
    def __init__(self, width: int = W) -> None:
        self.W = width
        self.P: list[str] = []
        self.MARK: dict[str, str] = {}
        self.max_x = 0.0
        self.max_y = 0.0
        self.min_x = float(width)

    # ---- low level -------------------------------------------------------
    def add(self, s: str) -> None:
        self.P.append(s)

    def _track(self, x0: float, y: float, x1: float) -> None:
        self.max_x = max(self.max_x, x1)
        self.min_x = min(self.min_x, x0)
        self.max_y = max(self.max_y, y)

    def text(self, x, y, s, size=12, color=INK, weight="normal", anchor="start",
             mono=False, italic=False):
        st = ' font-style="italic"' if italic else ""
        self.add(
            f'<text x="{x:.1f}" y="{y:.1f}" font-family="{MONO if mono else SANS}" font-size="{size}" '
            f'fill="{_c(color)}" font-weight="{weight}" text-anchor="{anchor}" '
            f'xml:space="preserve" style="white-space:pre"{st}>{escape(s)}</text>'
        )
        w = text_width(s, size, mono, weight == "bold")
        x0 = x if anchor == "start" else (x - w / 2 if anchor == "middle" else x - w)
        self._track(x0, y + size * 0.25, x0 + w)

    def rect(self, x, y, w, h, fill=WHITE, stroke=LINE, rx=8, sw=1.3, dash=None, op=1.0,
             stroke_op=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        so = f' stroke-opacity="{stroke_op}"' if stroke_op is not None else ""
        stroke_attr = f'stroke="{_c(stroke)}" stroke-width="{sw}"' if stroke else 'stroke="none"'
        self.add(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}" '
            f'fill-opacity="{op}" {stroke_attr}{so}{d}/>'
        )
        self._track(x, y + h, x + w)

    def line(self, x1, y1, x2, y2, col=LINE, sw=1, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                 f'stroke="{_c(col)}" stroke-width="{sw}"{d}/>')
        self._track(min(x1, x2), max(y1, y2), max(x1, x2))

    def circle(self, cx, cy, r, fill=INK, stroke=None, sw=1.2):
        s = f' stroke="{_c(stroke)}" stroke-width="{sw}"' if stroke else ""
        self.add(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="{_c(fill)}"{s}/>')
        self._track(cx - r, cy + r, cx + r)

    def marker(self, col) -> str:
        return self.MARK.setdefault(_c(col), f"m{len(self.MARK)}")

    # ---- 7 Arrows ----------------------------------------------------------
    def arrow(self, x1, y1, x2, y2, col=INK, sw=1.6, dash=None):
        """Straight arrow. End it 2 px short of the target edge yourself."""
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{_c(col)}" '
            f'stroke-width="{sw}"{d} marker-end="url(#{self.marker(col)})"/>'
        )
        self._track(min(x1, x2), max(y1, y2), max(x1, x2))

    def path_arrow(self, d, col=INK, sw=1.6, dash=None):
        """Routed arrow, e.g. d='M 10,10 L 10,40 L 80,40'. Prefer right angles."""
        ds = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(
            f'<path d="{d}" fill="none" stroke="{_c(col)}" stroke-width="{sw}"{ds} '
            f'marker-end="url(#{self.marker(col)})"/>'
        )

    def arrow_label(self, x, y, s, col=INK):
        """Arrow label: sans 11.5 bold, centered ~10 px above the segment."""
        self.text(x, y - 10, s, 11.5, col, "bold", "middle")

    # ---- 6 Components -----------------------------------------------------
    def badge(self, cx, cy, n, col=INK, r=13, size=13):
        self.circle(cx, cy, r, _c(col))
        self.text(cx, cy + size * 0.38, str(n), size, "#fff", "bold", "middle")

    def box(self, x, y, w, h, title, lines=(), col=INK, fill=None, tsize=13.5, mono_size=11.5,
            align="middle", sw=1.5):
        """6.2 Box: tinted fill, accent stroke, centered title, mono detail lines."""
        self.rect(x, y, w, h, fill=fill or _t(col), stroke=col, sw=sw)
        if align == "middle":
            self.text(x + w / 2, y + 20, title, tsize, _c(col), "bold", "middle")
            for i, s in enumerate(lines):
                self.text(x + w / 2, y + 38 + i * 15, s, mono_size, INK, anchor="middle", mono=True)
        else:
            self.text(x + 12, y + 20, title, tsize, _c(col), "bold")
            for i, s in enumerate(lines):
                self.text(x + 12, y + 38 + i * 15, s, mono_size, INK, mono=True)

    def pill(self, x, y, w, label, col, h=19):
        """6.5 Pill / tag: rx=h/2, white fill, accent stroke 1, mono 11 bold."""
        self.rect(x, y, w, h, fill=WHITE, stroke=col, rx=h / 2, sw=1)
        self.text(x + w / 2, y + h * 0.71, label, 11, _c(col), "bold", "middle", mono=True)

    def pill_auto(self, x, y, label, col, h=19, pad=10) -> float:
        """Pill sized to its label. Returns the width."""
        w = text_width(label, 11, mono=True) + 2 * pad
        self.pill(x, y, w, label, col, h)
        return w

    def chip(self, x, y, w, label, col, h=30):
        """6.5 Result chip: rx=6, white fill, accent stroke 1.4, mono 12 bold."""
        self.rect(x, y, w, h, fill=WHITE, stroke=col, rx=6, sw=1.4)
        self.text(x + w / 2, y + h / 2 + 4.2, label, 12, _c(col), "bold", "middle", mono=True)

    def panel(self, y, h, num, title, sub=None):
        """6.1 Panel: numbered section card spanning x=20 .. W-20."""
        self.rect(20, y, self.W - 40, h, fill=PANEL_BG, stroke=BORDER, rx=14, sw=1)
        self.badge(46, y + 26, num)
        self.text(68, y + 31, title, 17, INK, "bold")
        if sub:
            self.text(68, y + 50, sub, 12.5, MUTE)

    def step_card(self, x, y, w, h, num, title, col, tag=None, rows=(), key_w=34):
        """6.3 Step card: left accent bar + badge + optional tag pill + keyed mono rows.

        rows: list of (key, value) or (key, value, color) tuples.
        """
        self.rect(x, y, w, h, fill=_t(col), stroke=col, sw=1.4)
        self.rect(x, y, 6, h, fill=_c(col), stroke=None, rx=3)
        self.badge(x + 22, y + 17, num, col, r=10, size=11)
        self.text(x + 38, y + 22, title, 13.5, INK, "bold")
        if tag:
            tw = text_width(tag, 11, mono=True) + 20
            self.pill(x + w - tw - 8, y + 8, tw, tag, col)
        for i, row in enumerate(rows):
            key, val = row[0], row[1]
            kc = row[2] if len(row) > 2 else MUTE
            vc = row[2] if len(row) > 2 else INK
            ry = y + 42 + i * 17
            self.text(x + 38, ry, key, 11, kc, "bold", mono=True)
            self.text(x + 38 + key_w, ry, val, 12, vc, mono=True)

    def lane(self, x, y, w, h, col, name, details=(), header_h=64):
        """6.4 Lane: pale fill, dashed accent outline, solid header band with white text."""
        pale = col[2] if isinstance(col, tuple) and col[2] else WHITE
        self.rect(x, y, w, h, fill=pale, stroke=col, rx=12, sw=1.2, dash="4 4", stroke_op=0.35)
        self.rect(x, y, w, header_h, fill=_c(col), stroke=None, rx=12)
        self.rect(x, y + header_h - 24, w, 24, fill=_c(col), stroke=None, rx=0)
        self.text(x + 14, y + 23, name, 15, "#fff", "bold")
        for i, s in enumerate(details):
            self.text(x + 14, y + 41 + i * 16, s, 11.5, "#fff")

    def legend(self, x, y, items, title="Legend"):
        """6.9 Legend row: bold title, then 14x14 swatch + label per role.

        items: list of (role_color, label). Returns the x after the last label.
        """
        self.text(x, y + 11, title, 13, INK, "bold")
        cx = x + text_width(title, 13, bold=True) + 22
        for col, label in items:
            self.rect(cx, y, 14, 14, fill=_t(col), stroke=col, rx=3, sw=1.4)
            self.text(cx + 21, y + 11.5, label, 12, INK)
            cx += 21 + text_width(label, 12) + 26
        return cx

    def callout(self, x, y, w, lead, body, col, h=34):
        """6.10 Callout box: white fill, dashed accent stroke, bold lead-in + plain text."""
        self.rect(x, y, w, h, fill=WHITE, stroke=col, rx=8, sw=1.2, dash="4 3")
        self.text(x + 14, y + h / 2 + 4.5, lead, 12.5, col, "bold")
        lw = text_width(lead, 12.5, bold=True)
        self.text(x + 14 + lw + 8, y + h / 2 + 4.5, body, 12, INK)

    def footnotes(self, x, y, lines) -> float:
        """6.10 Footnotes: sans 12 MUTE, 18 px pitch. Returns the y after the last line."""
        for i, s in enumerate(lines):
            self.text(x, y + i * 18, s, 12, MUTE)
        return y + len(lines) * 18

    def aside(self, x, y, lines, pitch=17):
        """Plain-language aside: sans 11.5 italic MUTE, 17 px pitch."""
        for i, s in enumerate(lines):
            self.text(x, y + i * pitch, s, 11.5, MUTE, italic=True)

    def header(self, title, subtitle=None, params=None, scope=None):
        """Header block: title ~40, subtitle ~66, mono parameter strip ~84, scope ~104."""
        self.text(30, 42, title, 26, INK, "bold")
        if subtitle:
            self.text(30, 68, subtitle, 13.5, MUTE)
        if params:
            self.text(30, 88, params, 12.5, MUTE, mono=True)
        if scope:
            self.text(30, 106, scope, 12.5, MUTE)

    # ---- assemble -----------------------------------------------------------
    def svg(self, height: float) -> str:
        H = int(round(height))
        defs = "".join(
            f'<marker id="{mid}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
            f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{col}"/></marker>'
            for col, mid in self.MARK.items()
        )
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.W}" height="{H}" viewBox="0 0 {self.W} {H}">\n'
            f'<defs>{defs}</defs>\n<rect width="{self.W}" height="{H}" fill="#ffffff"/>\n'
            + "\n".join(self.P)
            + "\n</svg>\n"
        )

    def save(self, height: float, out: str | None = None) -> None:
        out = out or (sys.argv[1] if len(sys.argv) > 1 else None)
        if not out:
            raise SystemExit("usage: python3 <diagram>.py OUTPUT.svg")
        if self.max_x > self.W - 4:
            print(f"warning: content reaches x={self.max_x:.0f}, past the canvas width {self.W}", file=sys.stderr)
        if self.min_x < 4:
            print(f"warning: content starts at x={self.min_x:.0f}, near the left edge", file=sys.stderr)
        if self.max_y > height - 4:
            print(f"warning: content reaches y={self.max_y:.0f}, past the canvas height {height:.0f}", file=sys.stderr)
        with open(out, "w", encoding="utf-8") as f:
            f.write(self.svg(height))
