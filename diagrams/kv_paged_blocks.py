"""Diagram: a paged KV cache - logical tokens -> block table -> physical blocks.

Used by: src/learn/kv-cache.html
Toy numbers (4 tokens per block, 12 blocks) so every slot is visible.
Sources (commit 9bd9cf2):
  deepinfer/model_executor/model_metadata_utils.py:133-135   DeepInfer block size = 128 tokens
  csrc/engine/block_manager.hpp:27-35                          block 0 is never handed out (0 = empty)
  csrc/engine/block_manager.hpp:73-86                          allocate() takes the head of the free list
  csrc/engine/sequence.hpp:200-207                             KvCacheState.block_table (std::vector<int>)
  csrc/engine/sequence.hpp:291-293                             blocks needed = ceil(tokens / block_size)
  csrc/engine/input_metadata/prepare_tensor_input_v4.cpp:58-60 slot = block_table[j / B] * B + j % B
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import (  # noqa: E402
    BORDER, CELL_EMPTY, GRAY_MID, INK, LINE, MUTE, NEUTRAL, PANEL_BG, SERIES, TEAL, WHITE, Diagram, text_width,
)

A = (SERIES[0], "#eff6ff")   # sequence A: blue
B = (SERIES[1], "#fdf2f8")   # sequence B: pink
BS = 4                        # toy block size

d = Diagram(width=1100)
W = d.W
CX0, CX1 = 46, W - 46          # panel content x range


def wrap(s, size, maxw, mono=False, indent="  "):
    """Greedy word wrap; continuation lines are indented with two spaces."""
    out, cur = [], ""
    for w in s.split(" "):
        cand = (cur + " " + w) if cur else w
        if cur and text_width((indent if out else "") + cand, size, mono) > maxw:
            out.append(cur)
            cur = w
        else:
            cur = cand
    out.append(cur)
    return [out[0]] + [indent + t for t in out[1:]]


d.header(
    "A paged KV cache: block table → physical blocks",
    "How a sequence finds the keys and values of its tokens  ·  toy numbers: 4 tokens per block, 12 blocks  ·  DeepInfer uses 128 tokens per block",
    params="blocks needed = ceil(tokens / block_size)     slot = block_table[pos // block_size] × block_size + pos % block_size",
)


def cells(x, y, n_used, start_idx, col, size=30, gap=4, n=BS, empty_style="dash"):
    """A row of n token cells; the first n_used are filled and numbered."""
    for i in range(n):
        cx = x + i * (size + gap)
        if i < n_used:
            d.rect(cx, y, size, size, fill=col[1], stroke=col[0], rx=3, sw=1.3)
            d.text(cx + size / 2, y + size / 2 + 4.5, str(start_idx + i), 13, col[0], "bold", "middle", mono=True)
        else:
            d.rect(cx, y, size, size, fill=WHITE, stroke=col[0] if empty_style == "dash" else LINE, rx=3, sw=1.1,
                   dash="3 3" if empty_style == "dash" else None)


# ============================================================================
# Panel 1: logical view, block table, physical pool
# ============================================================================
y0 = 124
P1_H = 556
d.panel(y0, P1_H, 1, "Where are the keys and values of a sequence? The block table says",
        "The sequence sees its tokens in order. Its block table maps each logical block to any physical block in the pool.")


def col_title(x, a, b):
    d.text(x, y0 + 84, a, 14, INK, "bold")
    d.text(x, y0 + 102, b, 13, MUTE)


# --- column 1: logical view
c1x = 46
col_title(c1x, "Logical view", "(what the sequence sees)")
ROW = 56
seqs = [
    ("A", A, 10, [5, 2, 9], y0 + 152),
    ("B", B, 6, [7, 3], y0 + 152 + 3 * ROW + 60),
]
blk_x = c1x + 76
blk_w = 4 * 30 + 3 * 4 + 16
row_centers = {}
for name, col, ntok, table, ys in seqs:
    d.text(c1x, ys - 14, f"Sequence {name}  ·  {ntok} tokens", 14, col[0], "bold")
    for lb in range(len(table)):
        ry = ys + lb * ROW
        used = max(0, min(BS, ntok - lb * BS))
        d.text(c1x, ry + 28, f"block {lb}", 13, MUTE, mono=True)
        d.rect(blk_x, ry, blk_w, 46, fill=WHITE, stroke=col[0], rx=6, sw=1.3)
        cells(blk_x + 8, ry + 8, used, lb * BS, col)
        row_centers[(name, lb)] = ry + 23

# --- column 2: block tables
c2x, c2w = 318, 232
col_title(c2x, "Block table", "(one per sequence)")
for name, col, ntok, table, ys in seqs:
    top = ys - 32
    bottom = ys + (len(table) - 1) * ROW + 46 + 4
    d.rect(c2x, top, c2w, bottom - top, fill=col[1], stroke=col[0], sw=1.5)
    d.text(c2x + 12, top + 20, f"{name}.block_table = [{', '.join(str(t) for t in table)}]", 13.5, col[0], "bold", mono=True)
    for lb, phys in enumerate(table):
        cy = row_centers[(name, lb)]
        d.text(c2x + 14, cy + 4.5, f"[{lb}]  →  block #{phys}", 13, INK, mono=True)
        d.arrow(blk_x + blk_w, cy, c2x - 2, cy, col[0])

# --- column 3: physical pool (3 columns x 4 rows)
bw, bh, gx, gy = 124, 76, 12, 16
c3w = 3 * bw + 2 * gx
c3x = CX1 - 14 - c3w
col_title(c3x, "Physical pool", "(device memory)")
pool_top = y0 + 124
pool_h = 4 * 92 + 22
d.rect(c3x - 14, pool_top - 8, c3w + 28, pool_h, fill="#fbfcfe", stroke=GRAY_MID, rx=12, sw=1.2, dash="4 4")
owner = {}
for name, col, ntok, table, ys in seqs:
    for lb, phys in enumerate(table):
        owner[phys] = (name, col, lb, max(0, min(BS, ntok - lb * BS)))
for k in range(12):
    r, c = divmod(k, 3)
    x = c3x + c * (bw + gx)
    y = pool_top + 6 + r * (bh + gy)
    if k == 0:
        d.rect(x, y, bw, bh, fill=BORDER, stroke=GRAY_MID, rx=6, sw=1.2)
        d.text(x + 10, y + 20, "#0", 13, MUTE, "bold", mono=True)
        d.text(x + 10, y + 42, "reserved", 12, MUTE, "bold")
        d.text(x + 10, y + 60, "0 = \"no block\"", 12, MUTE, mono=True)
        continue
    if k in owner:
        name, col, lb, used = owner[k]
        d.rect(x, y, bw, bh, fill=col[1], stroke=col[0], rx=6, sw=1.5)
        d.text(x + 10, y + 20, f"#{k}", 13, col[0], "bold", mono=True)
        d.text(x + bw - 10, y + 20, f"{name} · blk {lb}", 12, col[0], "bold", "end")
        for i in range(BS):
            cx = x + 10 + i * 27
            if i < used:
                d.rect(cx, y + 34, 23, 30, fill=col[0], stroke=col[0], rx=3, sw=1)
                d.text(cx + 11.5, y + 54, str(lb * BS + i), 11, WHITE, "bold", "middle", mono=True)
            else:
                d.rect(cx, y + 34, 23, 30, fill=WHITE, stroke=col[0], rx=3, sw=1.1, dash="3 3")
    else:
        d.rect(x, y, bw, bh, fill=WHITE, stroke=LINE, rx=6, sw=1.2)
        d.text(x + 10, y + 20, f"#{k}", 13, INK, "bold", mono=True)
        d.text(x + bw - 10, y + 20, "free", 12, MUTE, "bold", "end")
        for i in range(BS):
            d.rect(x + 10 + i * 27, y + 34, 23, 30, fill=CELL_EMPTY, stroke=LINE, rx=3, sw=0.8)
# arrows from the tables into the pool container
for name, col, ntok, table, ys in seqs:
    cy = ys - 8
    d.arrow(c2x + c2w, cy, c3x - 16, cy, col[0], sw=2)
    d.arrow_label((c2x + c2w + c3x - 14) / 2, cy, "look up", col[0])
d.text(c3x - 14, pool_top + pool_h + 14, "Free blocks: #1 #4 #6 #8 #10 #11.", 12.5, MUTE)
d.text(c3x - 14, pool_top + pool_h + 32, "The next allocation takes the first one (#1).", 12.5, MUTE)

# ============================================================================
# Panel 2: one decode step
# ============================================================================
y1 = y0 + P1_H + 20
P2_H = 232
d.panel(y1, P2_H, 2, "Where does the next token go? Divide the position by the block size",
        "Each decode step writes the keys and values of one more token. A new block is needed only every 4th token.")


def card(x, y, w, h, num, title, lines, col):
    d.rect(x, y, w, h, fill=col[1], stroke=col[0], sw=1.4)
    d.rect(x, y, 6, h, fill=col[0], stroke=None, rx=3)
    d.badge(x + 24, y + 20, num, col[0], r=11, size=12)
    d.text(x + 42, y + 25, title, 14, INK, "bold")
    for i, s in enumerate(lines):
        d.text(x + 22, y + 54 + i * 21, s, 13, INK, mono=True)


cgap = 30
cw, ch, cy = (CX1 - CX0 - 2 * cgap) / 3, 124, y1 + 70
xs = [CX0, CX0 + cw + cgap, CX0 + 2 * (cw + cgap)]
card(xs[0], cy, cw, ch, 1, "Token at position 10 (A)", [
    "logical block = 10 // 4 = 2",
    "offset        = 10 %  4 = 2",
    "(positions start at 0)",
], A)
card(xs[1], cy, cw, ch, 2, "Look up the block table", [
    "A.block_table[2] = #9",
    "slot = 9 × 4 + 2 = 38",
    "write K and V of token 10 there",
], A)
card(xs[2], cy, cw, ch, 3, "Token 12 needs logical block 3", [
    "the table has only 3 entries",
    "take the first free block: #1",
    "A.block_table = [5, 2, 9, 1]",
], (TEAL[0], TEAL[1]))
for i in range(2):
    d.arrow(xs[i] + cw, cy + ch / 2, xs[i + 1] - 2, cy + ch / 2, INK)
d.text(46, cy + ch + 28,
       "DeepInfer: the same rule with 128 tokens per block. Code: prepare_tensor_input_v4.cpp:58-60 (slot), block_manager.hpp:82-86 (take a free block).",
       12.5, MUTE)

# ============================================================================
# Panel 3: why paging
# ============================================================================
y2 = y1 + P2_H + 20
P3_H = 264
d.panel(y2, P3_H, 3, "Why blocks? Only the last block of a sequence can be partly empty",
        "Without paging, each sequence reserves its maximum length up front. With paging, the empty space is less than one block per sequence.")

sx = 46
cs, cg = 21, 3
CHIP_W = 150


def strip(y, groups, label, waste):
    d.text(46, y - 12, label, 13.5, INK, "bold")
    x = sx
    for kind, col, n in groups:
        for i in range(n):
            if kind == "used":
                d.rect(x, y, cs, cs, fill=col[0], stroke=col[0], rx=2, sw=1)
            elif kind == "waste":
                d.rect(x, y, cs, cs, fill=WHITE, stroke=col[0], rx=2, sw=1.2, dash="3 3")
            else:
                d.rect(x, y, cs, cs, fill=CELL_EMPTY, stroke=LINE, rx=2, sw=0.8)
            x += cs + cg
        x += 6
    d.chip(CX1 - CHIP_W, y - 4.5, CHIP_W, waste, ("#b45309", "#fffbeb") if "16" in waste else (INK, WHITE))


ya = y2 + 100
strip(ya, [("used", A, 10), ("waste", A, 6), ("used", B, 6), ("waste", B, 10)],
      "Reserve 16 tokens each", "wasted: 16 slots")
d.text(sx, ya + 42, "A reserves 16 slots and uses 10.  B reserves 16 slots and uses 6.  A third sequence must wait.", 12.5, MUTE)
yb = ya + 96
strip(yb, [("used", A, 4), ("used", A, 4), ("used", A, 2), ("waste", A, 2), ("used", B, 4), ("used", B, 2), ("waste", B, 2),
           ("free", None, 4), ("free", None, 4), ("free", None, 4)],
      "Paged: blocks of 4", "wasted: 4 slots")
d.text(sx, yb + 42, "A has 3 blocks, B has 2 blocks. 12 slots (3 blocks) stay free for other sequences.", 12.5, MUTE)

# ============================================================================
# Legend and footnotes
# ============================================================================
y = y2 + P3_H + 24
d.legend(30, y, [
    (A, "sequence A (key and value of one token per slot)"),
    (B, "sequence B"),
    (TEAL, "new block for a growing sequence"),
    (NEUTRAL, "block 0, never used"),
])
y += 40
FN = []
for s in [
    "Simplified: one slot here stands for the keys and values of one token in every layer. In DeepInfer one physical block holds 128 tokens for all layers that use paging"
    " (model_metadata_utils.py:133-135, cache_engine.py:937-938). The free blocks in panel 1 are scattered because other sequences finished earlier.",
    "Not shown: the sliding-window cache and the compression state. DeepInfer keeps them per sequence in a state slot, not in paged blocks (cache_engine.py:205-218).",
]:
    FN += wrap(s, 12, W - 70)
y = d.footnotes(30, y, FN)
d.save(height=y + 14)
