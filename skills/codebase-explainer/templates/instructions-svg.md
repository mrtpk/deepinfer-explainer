# SVG Explainer Diagrams — Style & Construction Guide

Instructions for producing clean, flat, technical explainer diagrams as standalone SVG files.

> **Site rules override this guide** (see STYLE.md section 10): canvas width **1100**, no text smaller
> than **11**, at most **3 boxes side by side**, at most **3 panels** per diagram (split big diagrams),
> captions start with "Figure: ". Coordinates in the snippets below are illustrative.
The look: white canvas, numbered panels read top-to-bottom, soft tinted boxes with crisp
colored outlines, monospace for every number/identifier, color-keyed arrows, and no decoration
that doesn't carry meaning.

---

## 1. Principles

1. **Flat and quiet.** No gradients, shadows, filters, blur, 3-D, or clip-art. Hierarchy comes from
   type weight, tint, and stroke — never effects.
2. **One color = one meaning.** Every accent is bound to a role (a stage, a location, a category).
   That role's box outline, tint, arrows, labels and legend swatch all use the same accent.
3. **Neutral by default.** Most ink is near-black and gray. Accents are reserved for what the
   reader must track. Use 3–5 role accents per diagram (a categorical series is the exception).
4. **Sans for prose, mono for data.** Titles and explanations in a sans stack; numbers, sizes,
   identifiers, formulas, and aligned tables in a mono stack.
5. **Numbered reading order.** Panels and steps carry numbered circular badges so the reader
   never wonders where to look next.
6. **Concrete over abstract.** Show a worked example (actual values, a few sample rows/cells)
   next to the general structure.
7. **Light theme, explicit background.** Always paint a white background rect so the file looks
   identical in any viewer, including dark-mode ones.

---

## 2. Color template

### 2.1 Neutrals

| Token        | Hex       | Use                                                         |
|--------------|-----------|-------------------------------------------------------------|
| `INK`        | `#111827` | Primary text, neutral arrows, panel badges, operator glyphs |
| `MUTE`       | `#6b7280` | Subtitles, secondary text, axis labels, annotations         |
| `GRAY_MID`   | `#9ca3af` | Outline of "inactive / baseline" blocks                     |
| `LINE`       | `#d1d5db` | Grid-cell strokes, hairlines, default box stroke            |
| `BORDER`     | `#e5e7eb` | Panel borders, inactive block fill                          |
| `PANEL_BG`   | `#fafafa` | Panel (section card) background                             |
| `CELL_EMPTY` | `#f9fafb` | Empty / unselected grid cells                               |
| `WHITE`      | `#ffffff` | Canvas, box interiors, pill backgrounds, text on solid fills|

Never use pure black (`#000`).

### 2.2 Role accents (stroke + tint pairs)

Each accent has a **strong** value (stroke, arrows, label text, solid header bands) and a
**tint** (box fill). Pick one per role and keep it for the whole diagram.

| Name    | Strong    | Tint      | Extra-pale (lane bg) | Typical feel              |
|---------|-----------|-----------|----------------------|---------------------------|
| Blue    | `#2563eb` | `#eff6ff` | `#f8fbff`            | primary flow / main path  |
| Amber   | `#d97706` | `#fffbeb` | `#fffdf6`            | transfer, always-on, warn |
| Violet  | `#7c3aed` | `#f5f3ff` | —                    | parameters, control logic |
| Teal    | `#0d9488` | `#f0fdfa` (strong tint `#ccfbf1`) | —        | the thing being explained |
| Emerald | `#059669` | `#ecfdf5` | `#f6fdf9`            | second location / output  |
| Pink    | `#db2777` | `#fdf2f8` | —                    | contrast / alternate path |

The "feel" column is a suggestion, not a rule. Bind meaning per diagram and state it in the legend.

### 2.3 Categorical series (up to 8 items)

For coloring N parallel items (groups, samples, series) in order:

```
#2563eb  #db2777  #16a34a  #ea580c  #7c3aed  #0891b2  #ca8a04  #dc2626
 blue     pink     green    orange   violet   cyan     yellow   red
```

For 4 or fewer items use the first four. Selected items get a color; everything else stays neutral.

### 2.4 Opacity usage

- Column/row **band highlight** behind a grid: accent at `fill-opacity="0.1"` for selected,
  `0.03` for unselected. Bands use `rx="0"` and no stroke.
- **Container outlines** (lanes): accent stroke at `stroke-opacity="0.35"`, dashed.
- Everything else is fully opaque.

---

## 3. Typography

```
SANS = "Inter,Segoe UI,Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"
```

Every `<text>` carries `xml:space="preserve" style="white-space:pre"` so runs of spaces in mono
text keep their width. That's how aligned columns are made without tables.

| Role                       | Font | Size      | Weight | Color            |
|----------------------------|------|-----------|--------|------------------|
| Diagram title              | sans | 22–26     | bold   | `INK`            |
| Diagram subtitle / scope   | sans | 13–13.5   | normal | `MUTE`           |
| Parameter strip under title| mono | 12.5      | normal | `MUTE`           |
| Panel title                | sans | 17        | bold   | `INK`            |
| Panel subtitle             | sans | 12.5      | normal | `MUTE`           |
| Lane header (on solid band)| sans | 15 / 11.5 | bold / normal | `#fff`    |
| Box / card title           | sans | 13–13.5   | bold   | role accent or `INK` |
| Body data lines            | mono | 11.5–12   | normal | `INK`            |
| Row keys (`in`, `out`…)    | mono | 11        | bold   | `MUTE` (or accent) |
| Pill / tag text            | mono | 11        | bold   | role accent      |
| Axis / index labels        | mono | 11        | normal/bold | `MUTE` or series color |
| Arrow labels               | sans | 11.5      | bold   | `INK` or arrow color |
| Annotations / asides       | sans | 11.5      | normal, *italic* | `MUTE` |
| Footnotes                  | sans | 12        | normal | `MUTE`           |
| Operator glyphs (`+ ⊙ ×`)  | sans | 18–20     | bold   | `INK`            |

Unicode helpers that render well: `→ ← ↓ ▼ · × ≈ ≤ ‖ Σ ⊙ ■ ●` and `—` for separators.
Separate metadata items in subtitles with `  ·  ` (two spaces either side).

---

## 4. Geometry scales

**Corner radius**

| Element                         | `rx`        |
|---------------------------------|-------------|
| Panel (section card)            | 14          |
| Lane (column container)         | 12          |
| Box / card                      | 8           |
| Small result chip               | 6           |
| Small blocks, legend swatch, accent bar | 3–4 |
| Grid cell                       | 2           |
| Pill / tag                      | height / 2  |
| Background bands                | 0           |

**Stroke width**

| Element                           | width |
|-----------------------------------|-------|
| Grid cells (hairline)             | 0.8   |
| Panel border                      | 1     |
| Small blocks, chips, selected cell| 1.2   |
| Default box                       | 1.3–1.5 |
| Arrows                            | 1.6 (emphasis 2) |
| "This one" highlight on a block   | 2.6   |

**Dash patterns:** `4 4` lanes, `4 3` callout/footnote boxes, `5 4` secondary/skip arrows,
`3 3` faint guides.

---

## 5. Layout

- **Canvas width 1100** (site rule). Height is computed after content is placed (track a running `y`).
  Set `width`, `height`, and `viewBox="0 0 W H"` to match.
- **Outer margin:** title at `x=30`; panels span `x=20 … W-20`; panel content starts at `x=46`.
- **Header block:** title baseline ≈ 40, subtitle ≈ 66, optional mono parameter strip ≈ 84,
  optional scope note ≈ 104. First panel begins ≈ 90–124.
- **Panels** stack vertically with ~20 px gaps. Inside a panel: badge + title at `y+26/31`,
  subtitle at `y+50`, content from `y+66`.
- **Vertical rhythm:** 15 px line pitch for compact mono lines, 17 px for card rows;
  10 px inner padding; 16–18 px gap between stacked cards with a short arrow bridging them.
- **Lanes** (side-by-side columns for places/actors) run the full content height and are
  separated by ~20 px gutters. Widths are proportional to content, not equal.
- Flow runs **left→right** within a panel and **top→bottom** across panels.
- Prefer **orthogonal routing** (horizontal/vertical segments with right-angle turns) for
  arrows. Use straight diagonals only for short hops between lanes.
- Align related elements on shared x/y lines; place the legend and footnotes at the bottom.

---

## 6. Component library

All snippets assume the tokens above. Coordinates are illustrative. For brevity, `<text>` snippets
omit `font-family` when it is `SANS` and write `font-family="MONO"` as a placeholder for the mono
stack. Substitute the full stacks (and the `xml:space` attributes) in real output, as the helper
functions in section 9 do.

### 6.1 Panel (numbered section card)
```xml
<rect x="20" y="90" width="1460" height="162" rx="14" fill="#fafafa" stroke="#e5e7eb" stroke-width="1"/>
<circle cx="46" cy="116" r="13" fill="#111827"/>
<text x="46" y="121" font-size="13" fill="#fff" font-weight="bold" text-anchor="middle">1</text>
<text x="68" y="121" font-size="17" fill="#111827" font-weight="bold">Panel title as a question or claim</text>
<text x="68" y="140" font-size="12.5" fill="#6b7280">One-sentence takeaway for this panel.</text>
```

### 6.2 Box (centered title + mono detail lines)
Tinted fill, accent stroke 1.5, `rx=8`. Title bold, centered at `y+20`; mono lines at `y+38+15i`.
```xml
<rect x="412" y="270" width="250" height="56" rx="8" fill="#f5f3ff" stroke="#7c3aed" stroke-width="1.5"/>
<text x="537" y="290" font-size="13.5" fill="#7c3aed" font-weight="bold" text-anchor="middle">Component</text>
<text x="537" y="308" font-family="MONO" font-size="11.5" fill="#111827" text-anchor="middle">detail [n, m]</text>
```

### 6.3 Step card (left accent bar + badge + tag pill + keyed rows)
For a sequence of operations. Tint fill, accent stroke 1.4, a 6 px solid accent bar on the left,
a small numbered badge (r=10), a bold title, a pill tag at top-right, and rows of
`key   value   comment` in mono with aligned columns.
```xml
<rect x="44" y="220" width="662" height="85" rx="8" fill="#eff6ff" stroke="#2563eb" stroke-width="1.4"/>
<rect x="44" y="220" width="6" height="85" rx="3" fill="#2563eb"/>
<circle cx="66" cy="237" r="10" fill="#2563eb"/>
<text x="66" y="241" font-size="11" fill="#fff" font-weight="bold" text-anchor="middle">1</text>
<text x="82" y="242" font-size="13.5" fill="#111827" font-weight="bold">Step title</text>
<rect x="562" y="228" width="136" height="19" rx="9.5" fill="#fff" stroke="#2563eb"/>
<text x="630" y="241.5" font-family="MONO" font-size="11" fill="#2563eb" font-weight="bold" text-anchor="middle">tag · where</text>
<text x="82"  y="262" font-family="MONO" font-size="11" fill="#6b7280" font-weight="bold">in</text>
<text x="116" y="262" font-family="MONO" font-size="12" fill="#111827">name         [a, b]     note</text>
```
Row keys: neutral (`MUTE`) for inputs/outputs; give one row type its own accent (key *and*
value) when it is a distinct category the reader should spot at a glance.
Connect consecutive cards with a short vertical arrow (16 px) in the card's accent.

### 6.4 Lane (full-height column container)
Extra-pale fill, dashed accent outline at 35 % opacity, and a solid accent header band
(64 px tall, rounded top only) holding white text.
```xml
<rect x="30" y="124" width="690" height="1552" rx="12" fill="#f8fbff" stroke="#2563eb" stroke-opacity="0.35" stroke-dasharray="4 4"/>
<rect x="30" y="124" width="690" height="64" rx="12" fill="#2563eb"/>
<rect x="30" y="164" width="690" height="24" fill="#2563eb"/>   <!-- squares off the bottom corners -->
<text x="44" y="147" font-size="15" fill="#fff" font-weight="bold">Lane name</text>
<text x="44" y="165" font-size="11.5" fill="#fff">first detail line</text>
<text x="44" y="181" font-size="11.5" fill="#fff">second detail line</text>
```
Section labels inside a lane: mono 12 bold in the lane accent, placed just above the cards.

### 6.5 Pill / chip
`rx = height/2`, white fill, accent stroke 1, mono 11 bold accent text. Result chips: `rx=6`,
height 30, white fill, accent stroke 1.4, mono 12 bold accent text.

### 6.6 Cell grid (matrices, tables of slots, sequences)
- Cell 11–17 px square, gap ≈ 2 px, `rx=2`, stroke `LINE` 0.8.
- Empty cell: fill `#ffffff` or `CELL_EMPTY`.
- Selected cell: fill white, stroke `INK` 1.2, plus a centered dot (`r ≈ 0.2 × cell`) in the
  item's series color.
- Row/column labels: mono 10, right-aligned (`text-anchor="end"`) to the left of rows,
  colored with the series color when rows are categorical.
- Emphasize whole rows/columns with background bands (section 2.4) drawn *before* the cells.

### 6.7 Block strip (a long sequence of items)
Narrow tall blocks (e.g. 21 × 40, gap 1.6, `rx=3`, stroke 1.2). Baseline items: fill `BORDER`,
stroke `GRAY_MID`. Highlighted kind: strong tint fill, accent stroke. "This specific one":
same, stroke width 2.6, with a `▼ label` above in accent bold 11.5. Index labels in mono 10 `MUTE`
every 5th item plus endpoints.

### 6.8 Junctions and operators
- Split point: small filled circle `r=4` in `INK`, with branches leaving orthogonally.
- Merge/operation: a bold glyph (`+`, `⊙`, `×`) at size 18–20, centered, with arrows
  converging on it from the sides/top.

### 6.9 Legend
One row at the bottom: bold "Legend" (sans 13), then for each role a 14×14 swatch (`rx=3`,
tint fill, accent stroke 1.4) followed by a sans 12 label. Inline color keys can also be written
as text: `■ label` in the accent color, bold 12.

### 6.10 Callout / footnote
- **Callout box:** full content width, height ~34, `rx=8`, white fill, accent stroke 1.2, dash `4 3`.
  Bold accent lead-in phrase (sans 12.5), then plain `INK` text (sans 12).
- **Footnotes:** sans 12 `MUTE`, 18 px pitch, below the legend. Indent continuation lines with
  two spaces.
- **Plain-language asides** next to a figure: sans 11.5 italic `MUTE`, 17 px pitch.

---

## 7. Arrows

Define one marker per color in `<defs>` (create lazily as colors are used):
```xml
<marker id="m0" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7"
        orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#2563eb"/></marker>
```
- Straight: `<line ... stroke="COLOR" stroke-width="1.6" marker-end="url(#mN)"/>`
- Routed: `<path d="M x,y L x,y2 L x2,y2" fill="none" stroke="COLOR" stroke-width="1.6" marker-end="url(#mN)"/>`
- **Arrow color = the role of what is flowing** (usually the source's accent). Neutral flow uses `INK`.
- **Dashed (`5 4`)** for bypass/skip/secondary paths so they read as "also, in parallel".
- End arrows 2 px short of the target edge so the head doesn't overlap the stroke.
- Labels: sans 11.5 bold, centered ~10 px above the horizontal segment's midpoint.
- Emphasis arrows (a key transition between stages): stroke 2.

---

## 8. Content rules

- **Title** states what the diagram explains; **subtitle** states scope, assumptions, and the
  one-line summary. A mono parameter strip lists the constants used.
- **Each panel answers one question.** Panel subtitles are the answer in one sentence.
- Progress from **context → single item → mechanism detail → many items at once**.
- Show **real example values** and keep them consistent across panels (seed any randomness).
- Explicitly say what is **not shown** in a footnote rather than leaving gaps unexplained.
- Prefer short labels on the drawing and put the explanation in muted text beside it.

---

## 9. How to generate (recommended)

Write a small Python script that builds the SVG as a list of strings. Hand-editing large SVGs
doesn't scale, and a script keeps spacing math exact.

```python
import sys
from html import escape

OUT = sys.argv[1]
W = 1100
INK, MUTE, LINE = "#111827", "#6b7280", "#d1d5db"
SANS = "Inter,Segoe UI,Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"
SERIES = ["#2563eb", "#db2777", "#16a34a", "#ea580c", "#7c3aed", "#0891b2", "#ca8a04", "#dc2626"]

P, MARK = [], {}
def add(s): P.append(s)

def text(x, y, s, size=12, color=INK, weight="normal", anchor="start", mono=False, italic=False):
    st = ' font-style="italic"' if italic else ""
    add(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{MONO if mono else SANS}" font-size="{size}" '
        f'fill="{color}" font-weight="{weight}" text-anchor="{anchor}" '
        f'xml:space="preserve" style="white-space:pre"{st}>{escape(s)}</text>')

def rect(x, y, w, h, fill="#fff", stroke=LINE, rx=8, sw=1.3, dash=None, op=1.0):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}" '
        f'fill-opacity="{op}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

def marker(col):
    return MARK.setdefault(col, f"m{len(MARK)}")

def arrow(x1, y1, x2, y2, col=INK, sw=1.6, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{col}" '
        f'stroke-width="{sw}"{d} marker-end="url(#{marker(col)})"/>')

def path_arrow(d, col=INK, sw=1.6, dash=None):
    ds = f' stroke-dasharray="{dash}"' if dash else ""
    add(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{sw}"{ds} '
        f'marker-end="url(#{marker(col)})"/>')

def badge(cx, cy, n, col=INK, r=13, size=13):
    add(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{col}"/>')
    text(cx, cy + size * 0.38, str(n), size, "#fff", "bold", "middle")

def box(x, y, w, h, title, lines=(), col=INK, fill="#fff", tsize=13.5):
    rect(x, y, w, h, fill=fill, stroke=col, sw=1.5)
    text(x + w / 2, y + 20, title, tsize, col, "bold", "middle")
    for i, s in enumerate(lines):
        text(x + w / 2, y + 38 + i * 15, s, 11.5, INK, anchor="middle", mono=True)

def pill(x, y, w, label, col, h=19):
    rect(x, y, w, h, fill="#fff", stroke=col, rx=h / 2, sw=1)
    text(x + w / 2, y + h * 0.71, label, 11, col, "bold", "middle", mono=True)

def panel(y, h, num, title, sub=None):
    rect(20, y, W - 40, h, fill="#fafafa", stroke="#e5e7eb", rx=14, sw=1)
    badge(46, y + 26, num)
    text(68, y + 31, title, 17, INK, "bold")
    if sub:
        text(68, y + 50, sub, 12.5, MUTE)

# ---- content -------------------------------------------------------------
text(30, 42, "Diagram title", 26, weight="bold")
text(30, 68, "Scope  ·  assumptions  ·  one-line summary", 13.5, MUTE)
y = 90
panel(y, 200, 1, "First question", "One-sentence answer.")
# ... place components, advancing y ...
y += 200 + 20
H = y + 20

# ---- assemble --------------------------------------------------------------
defs = "".join(
    f'<marker id="{mid}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
    f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{col}"/></marker>'
    for col, mid in MARK.items())
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">\n'
       f'<defs>{defs}</defs>\n<rect width="{W}" height="{H}" fill="#ffffff"/>\n'
       + "\n".join(P) + "\n</svg>\n")
open(OUT, "w", encoding="utf-8").write(svg)
```

Notes:
- Use inline presentation attributes, not CSS classes or `<style>`, so the file renders the same
  everywhere (browsers, IDE previews, docs tools, image converters).
- Always `escape()` text. Format coordinates to one decimal.
- No external fonts, images, or scripts. The font stacks fall back gracefully.
- Draw order: background bands → containers → boxes → cells → arrows → text on top.

---

## 10. Don'ts

- No gradients, drop shadows, glows, filters, or patterns.
- No rotated or vertical text; no text smaller than 11.
- No more than ~5 role accents, plus at most one 8-color series.
- Don't use color alone for meaning. Pair it with a label, legend entry, or position.
- Don't use a role's accent for an unrelated element (e.g. a decorative border).
- Don't center long prose; left-align everything except box titles, pills, and cell labels.
- Don't let arrows cross boxes. Reroute orthogonally around them.

---

## 11. Final checklist

- [ ] White background rect; `width`/`height`/`viewBox` match the computed content height
- [ ] Title + muted subtitle; panels numbered in reading order
- [ ] Every accent bound to one role and listed in the legend
- [ ] All numbers, sizes, ids in mono; prose in sans
- [ ] Mono columns align (spaces preserved)
- [ ] Arrows colored by what flows; secondary paths dashed; heads not overlapping strokes
- [ ] Nothing overlaps or clips at the right/bottom edge
- [ ] Footnotes state what is simplified or omitted
- [ ] Opens correctly in a browser at 100 % and zoomed out to fit
