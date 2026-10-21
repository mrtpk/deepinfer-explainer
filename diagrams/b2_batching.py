"""Diagram: static vs continuous batching, padded vs packed batches, and DeepInfer's two step kinds.

Used by: src/learn/batching.html
Toy numbers (5 requests, 3 batch slots) so every cell is visible.
Sources (commit 9bd9cf2):
  csrc/engine/scheduler.hpp:288-341     NORMAL engine: one step is a prefill step OR a decode step
  csrc/engine/scheduler.hpp:467-475     prompt cut to the remaining token budget (chunk)
  csrc/engine/scheduler.hpp:543-545     NORMAL engine: a chunked prompt is the last one in the step
  csrc/engine/mtp_varlen.hpp:153-157    decode: seqlen_q = 1 + number of draft tokens
  deepinfer/environ.py:129              DEEPINFER_USE_NEXTN_DECODE default 5
  deepinfer/model_executor/input_metadata/input_metadata.py:261-264   cu_seqlens_q = cumsum(seqlen_q)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import (  # noqa: E402
    BLUE, BORDER, GRAY_MID, INK, LINE, MUTE, NEUTRAL, SERIES, TEAL, WHITE, Diagram,
)

TINT = {SERIES[0]: "#eff6ff", SERIES[1]: "#fdf2f8", SERIES[2]: "#f0fdf4", SERIES[3]: "#fff7ed", SERIES[4]: "#f5f3ff"}
REQ = {k: SERIES[i] for i, k in enumerate("ABCDE")}

d = Diagram(width=1100)
W = d.W
d.header("Batching: which tokens run together in one step",
         "Toy example: 5 requests, 3 batch slots  ·  one column = one engine step  ·  prefill of new requests not shown",
         params="output tokens:  A=3  B=7  C=4  D=5  E=2        prompt lengths (panel 2):  A=5  B=2  C=3")

CELL, GAP = 30, 3


def cell(x, y, label, w=CELL, h=CELL):
    if label is None:
        d.rect(x, y, w, h, fill=WHITE, stroke=LINE, rx=3, sw=0.9, dash="3 3")
        return
    if label == "pad":
        d.rect(x, y, w, h, fill=BORDER, stroke=GRAY_MID, rx=3, sw=1.1)
        d.text(x + w / 2, y + h / 2 + 4, "0", 11, MUTE, "bold", "middle", mono=True)
        return
    col = REQ[label[0]]
    d.rect(x, y, w, h, fill=TINT[col], stroke=col, rx=3, sw=1.3)
    d.text(x + w / 2, y + h / 2 + 4.5, label, 12, col, "bold", "middle", mono=True)


def grid(x0, y0, rows, n_steps, title, sub, col_title):
    d.text(x0, y0, title, 14, col_title, "bold")
    d.text(x0, y0 + 18, sub, 12, MUTE)
    gy = y0 + 46
    gx = x0 + 52
    for s in range(n_steps):
        d.text(gx + s * (CELL + GAP) + CELL / 2, gy - 6, str(s + 1), 11, MUTE, anchor="middle", mono=True)
    for r, row in enumerate(rows):
        ry = gy + r * (CELL + GAP)
        d.text(x0, ry + CELL / 2 + 4, f"slot {r + 1}", 12, MUTE, mono=True)
        for s in range(n_steps):
            cell(gx + s * (CELL + GAP), ry, row[s] if s < len(row) else None)
    return gy + len(rows) * (CELL + GAP)


# ============================================================================
# Panel 1: static vs continuous batching
# ============================================================================
y0 = 112
P1_H = 300
d.panel(y0, P1_H, 1, "Static or continuous: when can a new request join?",
        "Static batching waits for the whole batch to finish. Continuous batching refills a slot at the next step.")

static_rows = [
    list("AAA") + [None] * 4 + list("DDDDD"),
    list("BBBBBBB") + list("EE") + [None] * 3,
    list("CCCC") + [None] * 3 + [None] * 5,
]
cont_rows = [
    list("AAA") + list("DDDDD"),
    list("BBBBBBB") + [None],
    list("CCCC") + list("EE") + [None] * 2,
]
gx_left, gx_right = 46, 600
gb = grid(gx_left, y0 + 86, static_rows, 12, "Static batching", "Batch 2 (D, E) starts after B ends at step 7.", INK)
grid(gx_right, y0 + 86, cont_rows, 8, "Continuous batching", "D takes A's slot at step 4; E takes C's slot at step 5.", TEAL[0])
d.text(gx_left, gb + 22, "12 steps  ·  21 of 36 slot-steps used = 58 %", 12.5, INK, "bold", mono=True)
d.text(gx_right, gb + 22, "8 steps  ·  21 of 24 slot-steps used = 88 %", 12.5, TEAL[0], "bold", mono=True)
d.text(gx_left, gb + 42, "Dashed cell = an idle slot: the device does no useful work there.", 11.5, MUTE, italic=True)

# ============================================================================
# Panel 2: padded vs packed
# ============================================================================
y1 = y0 + P1_H + 20
P2_H = 250
d.panel(y1, P2_H, 2, "Padded or packed: how is the batch stored?",
        "A padded batch fills every row to the longest prompt. A packed (varlen) batch puts the tokens end to end.")

px, py = 46, y1 + 92
d.text(px, py - 16, "Padded: tensor [3, 5]", 14, INK, "bold")
lens = {"A": 5, "B": 2, "C": 3}
for r, (k, n) in enumerate(lens.items()):
    ry = py + r * (CELL + GAP)
    d.text(px, ry + CELL / 2 + 4, k, 12, REQ[k], "bold", mono=True)
    for i in range(5):
        cell(px + 24 + i * (CELL + GAP), ry, f"{k}{i}" if i < n else "pad")
d.text(px, py + 3 * (CELL + GAP) + 20, "15 slots, 5 are padding (33 % waste)", 12.5, INK, "bold", mono=True)

qx = 380
d.text(qx, py - 16, "Packed (varlen): tensor [10] + cu_seqlens_q", 14, TEAL[0], "bold")
toks = [f"A{i}" for i in range(5)] + [f"B{i}" for i in range(2)] + [f"C{i}" for i in range(3)]
for i, t in enumerate(toks):
    cell(qx + i * (CELL + GAP), py, t)
for i in range(10):
    d.text(qx + i * (CELL + GAP) + CELL / 2, py + CELL + 16, str(i), 11, MUTE, anchor="middle", mono=True)
# boundaries
for b in (0, 5, 7, 10):
    bx = qx + b * (CELL + GAP) - (GAP / 2 if b else 0) - (0 if b < 10 else 0)
    if b == 10:
        bx = qx + 10 * (CELL + GAP) - GAP / 2
    d.line(bx, py - 4, bx, py + CELL + 36, col=TEAL[0], sw=1.6)
    d.text(bx, py + CELL + 52, str(b), 12, TEAL[0], "bold", "middle", mono=True)
d.text(qx, py + CELL + 76, "cu_seqlens_q = [0, 5, 7, 10]   →   sequence i owns tokens cu[i] … cu[i+1] − 1", 12.5, INK, mono=True)
d.text(qx, py + CELL + 96, "10 slots, 0 padding. Kernels read the boundaries from cu_seqlens_q.", 12.5, MUTE)

# ============================================================================
# Panel 3: DeepInfer step kinds
# ============================================================================
y2 = y1 + P2_H + 20
P3_H = 262
d.panel(y2, P3_H, 3, "In DeepInfer, one step is a prefill step or a decode step",
        "The NORMAL engine does not mix the two kinds in one step. Both kinds use a packed batch.")

bx0, bx1 = 46, W - 46
bw = bx1 - bx0
# prefill bar (budget 4096, illustrative)
by = y2 + 98
d.text(bx0, by - 14, "Prefill step  ·  token budget max_num_batched_tokens (4,096 here, illustrative)", 14, BLUE[0], "bold")
segs = [("P1: 1,000 tokens", 1000, SERIES[0], "#eff6ff", None),
        ("P2: 2,000 tokens", 2000, SERIES[1], "#fdf2f8", None),
        ("P3: first 1,096 of 3,000 (chunk)", 1096, SERIES[2], "#f0fdf4", "5 4")]
x = bx0
for label, n, col, tint, dash in segs:
    w = bw * n / 4096
    d.rect(x, by, w - 3, 40, fill=tint, stroke=col, rx=4, sw=1.6, dash=dash)
    d.text(x + 10, by + 25, label, 12.5, col, "bold", mono=True)
    x += w
d.text(bx0, by + 60, "The rest of P3 (1,904 tokens) waits for a later prefill step. In a NORMAL engine, a chunked prompt ends the step.",
       12, MUTE)

# decode row
dy = by + 100
d.text(bx0, dy - 14, "Decode step  ·  every running sequence sends 1 token + 5 draft tokens (DEEPINFER_USE_NEXTN_DECODE = 5)", 14,
       BLUE[0], "bold")
x = bx0
for si, k in enumerate("ABCD"):
    col = REQ[k]
    for t in range(6):
        lab = f"{k}" if t == 0 else f"d{t}"
        d.rect(x, dy, 31, 30, fill=TINT[col], stroke=col, rx=3, sw=1.4 if t == 0 else 1.0, dash=None if t == 0 else "3 2")
        d.text(x + 15.5, dy + 19.5, lab, 11.5, col, "bold", "middle", mono=True)
        x += 34
    x += 12
d.text(x + 6, dy + 20, "4 × 6 = 24 tokens", 12.5, INK, "bold", mono=True)

y = y2 + P3_H + 24
d.legend(30, y, [(BLUE, "DeepInfer step kind"), (TEAL, "the better choice in panels 1-2"), (NEUTRAL, "padding (wasted work)")])
y += 36
y = d.footnotes(30, y, [
    "One colour = one request. Dashed box = a prompt chunk (panel 3, top) or a draft token d1-d5 (panel 3, bottom).",
    "Simplified: a joining request first needs a prefill step. Panel 1 leaves it out, so the grid shows decode work only.",
    "Panel 3 sources: csrc/engine/scheduler.hpp:288-341, 467-475, 543-545; csrc/engine/mtp_varlen.hpp:153-157.",
])
d.save(height=y + 10)
