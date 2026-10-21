"""Diagram: sliding-window attention in DeepInfer (window, per-sequence ring, prefill index).

Used by: src/concepts/sliding-window-attention.html ("The picture")
Sources (commit 9bd9cf2):
  csrc/engine/input_metadata/prepare_tensor_input_v4.cpp:98-108    ring store slot = state_id*134 + pos%134, last 134 rows only
  csrc/engine/input_metadata/prepare_tensor_input_v4.cpp:639-651   decode window [cur-127, cur] as (offset, len)
  deepinfer/model_executor/layers/tilelang_ops/get_kv_index.py:80-94  decode slot expansion (ring wrap)
  deepinfer/worker/cache_engine.py:88-110                           ring size = window + DEEPINFER_MAX_BACKTRACKING_TOKENS (+ extra-state part)
  deepinfer/environ.py:132                                          backtracking >= DEEPINFER_USE_NEXTN_DECODE + 1 = 6
  csrc/engine/input_metadata/prepare_tensor_input_v4.cpp:487-527   prefill pivots: section 1 (history) + section 2 (new)
  deepinfer/model_executor/layers/tilelang_ops/swa_index.py:10-32    expand pivots to int32 [T, window]
  doc/inference_deployment_qa.md:191                                window 128 + 6 backtracking = 134
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, BORDER, GRAY_MID, INK, LINE, MUTE, PINK, VIOLET, WHITE, Diagram  # noqa: E402

d = Diagram(width=1100)
d.header(
    "Sliding-window attention: the window, the ring and the prefill index",
    "One sequence  ·  default settings (5 draft tokens)  ·  window 128 is the value in the docs, not in the repo",
    params="window W = 128   ring = W + 6 = 134 slots   one slot = 528 B (FP8 + scales)   per layer, per sequence",
)

# ============================================================================
# Panel 1: what one query reads
# ============================================================================
y0 = 112
P1_H = 222
d.panel(y0, P1_H, 1, "Which keys does one decode query read?",
        "The last 128 positions from the ring, plus compressed entries from the whole history.")

AX0, AX1 = 70, 1030
N = 1006


def px(pos):
    return AX0 + (AX1 - AX0) * pos / N


ay = y0 + 128
d.line(AX0, ay, AX1, ay, INK, 1.2)
# window band 873..1000
d.rect(px(873), ay - 20, px(1001) - px(873), 40, fill=BLUE[1], stroke=BLUE, rx=3, sw=1.4)
d.text((px(873) + px(1001)) / 2, ay - 28, "window", 13, BLUE[0], "bold", "middle")
# compressed entries (example)
for p in (36, 118, 230, 301, 395, 452, 540, 611, 702, 765, 820):
    d.circle(px(p), ay, 5, VIOLET[0])
# query marker
d.text(px(1000), ay - 46, "▼ query", 12, AMBER[0], "bold", "middle")
for p, lab in ((0, "0"), (500, "500"), (873, "873"), (1000, "1000")):
    d.line(px(p), ay + 21, px(p), ay + 27, MUTE, 1)
    d.text(px(p), ay + 42, lab, 12, MUTE, anchor="middle", mono=True)
d.text(70, ay + 66, "Query at position 1000 reads positions 873..1000 (128 keys, itself included) from the window.", 12.5, INK)
d.text(70, ay + 84, "A compressed layer also reads compressed entries (dots: an example top-k choice of a sparse layer).", 12.5, MUTE)

# ============================================================================
# Panel 2: the ring
# ============================================================================
y1 = y0 + P1_H + 20
P2_H = 300
d.panel(y1, P2_H, 2, "Where does the window live? In a ring of 134 slots",
        "Decode step at positions 1000..1005 (1 token + 5 drafts). slot = state_id × 134 + position % 134.")

CELL, PITCH = 13, 14.5
CX0 = 60
rows_y = [y1 + 100, y1 + 178]


def cell_role(r):
    if r == 62:
        return "query"
    if 63 <= r <= 67:
        return "draft"
    if r == 68:
        return "spare"
    return "window"


for row in range(2):
    ry = rows_y[row]
    d.text(CX0, ry - 12, f"ring slots {row * 67}..{row * 67 + 66}", 12, MUTE, "bold", mono=True)
    for i in range(67):
        r = row * 67 + i
        x = CX0 + i * PITCH
        role = cell_role(r)
        if role == "window":
            d.rect(x, ry, CELL, CELL, fill=BLUE[1], stroke=BLUE, rx=2, sw=0.9)
        elif role == "query":
            d.rect(x, ry, CELL, CELL, fill=AMBER[1], stroke=AMBER, rx=2, sw=2.4)
        elif role == "draft":
            d.rect(x, ry, CELL, CELL, fill=PINK[1], stroke=PINK, rx=2, sw=1.2)
        else:
            d.rect(x, ry, CELL, CELL, fill=BORDER, stroke=GRAY_MID, rx=2, sw=1.2)
        if i % 10 == 0:
            d.text(x + CELL / 2, ry + CELL + 15, str(r), 11, MUTE, anchor="middle", mono=True)

# call-outs for row 0 (slots 62..68)
cx62 = CX0 + 62 * PITCH + CELL / 2
d.text(cx62 - 20, rows_y[0] - 30, "62 = pos 1000", 12, AMBER[0], "bold", "end", mono=True)
d.line(cx62 - 16, rows_y[0] - 34, cx62, rows_y[0] - 2, AMBER[0], 1)

ty = rows_y[1] + 52
d.text(60, ty, "Blue: window of the query at 1000 = positions 873..1000 (slots 69..133, then 0..62, the ring wraps).", 12.5, INK)
d.text(60, ty + 19, "Pink: drafts 1001..1005 in slots 63..67. Grey: slot 68 still holds position 872, which no query of this step needs.", 12.5, INK)
d.text(60, ty + 38, "Example: state_id 3, position 1000 → 3 × 134 + 62 = slot 464 of swa_cache.   (prepare_tensor_input_v4.cpp:104)", 12.5, MUTE,
       mono=False)

# ============================================================================
# Panel 3: prefill index
# ============================================================================
y2 = y1 + P2_H + 20
P3_H = 284
d.panel(y2, P3_H, 3, "Prefill: how does a query find its window?",
        "One sequence: 2,048 cached tokens, 300 new tokens. Keys come from two sections of one gathered buffer.")

S = 1.9
HX = 230
NX = HX + 128 * S + 14
by = y2 + 82
d.text(46, by + 15, "buffer", 13, INK, "bold")
d.rect(HX, by, 128 * S, 22, fill=VIOLET[1], stroke=VIOLET, rx=3, sw=1.2)
d.text(HX + 64 * S, by + 15.5, "section 1: history 1920..2047", 12, VIOLET[0], "bold", "middle")
d.rect(NX, by, 300 * S, 22, fill=WHITE, stroke=GRAY_MID, rx=3, sw=1.2)
d.text(NX + 150 * S, by + 15.5, "section 2: new tokens 2048..2347 (this chunk)", 12, INK, "bold", "middle")


def qrow(yy, label, h_lo, h_len, n_lo, n_len, piv):
    d.text(46, yy + 13, label, 12.5, AMBER[0], "bold", mono=True)
    d.rect(HX, yy, 128 * S, 18, fill=WHITE, stroke=LINE, rx=2, sw=0.8)
    d.rect(NX, yy, 300 * S, 18, fill=WHITE, stroke=LINE, rx=2, sw=0.8)
    if h_len:
        d.rect(HX + h_lo * S, yy, h_len * S, 18, fill=BLUE[1], stroke=BLUE, rx=2, sw=1.2)
    if n_len:
        d.rect(NX + n_lo * S, yy, n_len * S, 18, fill=BLUE[1], stroke=BLUE, rx=2, sw=1.2)
    d.text(NX + 300 * S + 0, yy + 36, piv, 12, MUTE, anchor="end", mono=True)


qrow(by + 40, "query 2048", 1, 127, 0, 1, "127 history keys + 1 new key (itself)")
qrow(by + 100, "query 2248", 0, 0, 73, 128, "0 history keys + 128 new keys (2121..2248)")
d.text(46, by + 168, "C++ writes 4 numbers per query (pivots: start and length in each section). The TileLang kernel", 12.5, INK)
d.text(46, by + 186, "expand_swa_index turns them into int32 [T, 128] key indices, with −1 for unused columns.", 12.5, INK)

y = y2 + P3_H + 22
d.legend(30, y, [(BLUE, "window keys"), (AMBER, "query token"), (PINK, "draft tokens"),
                 (VIOLET, "history / compressed"), ((GRAY_MID, BORDER, None), "not needed")])
y += 34
y = d.footnotes(30, y, [
    "Simplified: one layer and one sequence. Every layer has its own ring in the sequence's state slot; the ring is 134 slots",
    "  only with the defaults (DEEPINFER_PREFILL_STORE_EXTRA_STATE off, DEEPINFER_USE_NEXTN_DECODE = 5).",
])
d.save(height=y + 10)
