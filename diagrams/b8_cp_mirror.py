"""Diagram: the mirror-CP token layout and the data flow of one CP prefill step.

Used by: src/concepts/context-parallelism.html (also src/tours/multi-gpu-step.html)
Sources (commit 9bd9cf2):
  deepinfer/model_executor/layers/tilelang_ops/prepare_cp_mirror.py:126-157   reference: parts r and 2cp-1-r, reverse index
  csrc/engine/input_metadata/prepare_tensor_input_base.cpp:146-155            cp_mirror_len = 2 * sum(ceil(sq / 2cp))
  deepinfer/model_executor/models/deepseek.py:161-170                         embed full, gather mirror rows
  deepinfer/model_executor/models/v4_modules/attn.py:782-829                  CP session, all-gather KV, reorder with reverse index
  deepinfer/model_executor/models/deepseek.py:241-244                         final all-gather of hidden states
  deepinfer/model_executor/parallel_utils/cp.py:42-51                         CPManager.all_gather: [cp, rows, ...] -> flatten
Worked example (computed with prepare_cp_mirror_ref): one sequence of 8 prompt tokens, no cached context, cp = 2.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, MUTE, PINK, VIOLET, WHITE, Diagram  # noqa: E402

d = Diagram(width=1100)
d.header(
    "Mirror CP: which rank computes which tokens",
    "Prefill only  ·  one sequence of 8 tokens, no cached context  ·  cp = 2  ·  commit 9bd9cf2",
    params="parts = 2 x cp = 4   part size ps = ceil(8 / 4) = 2   cp_mirror_len = 2 x ps = 4 rows per rank",
)

# ---------------------------------------------------------------------------
# Panel 1: the layout
# ---------------------------------------------------------------------------
y0 = 112
P1_H = 330
d.panel(y0, P1_H, 1, "How are the 8 tokens split?",
        "Rank r takes part r and part 2cp-1-r. Each rank gets one early part and one late part.")

CELL = 52
GAP = 6
x0 = 200
row_y = y0 + 92
d.text(46, row_y + 33, "prompt tokens", 13, INK, "bold")
part_of = [0, 0, 1, 1, 2, 2, 3, 3]
rank_of_part = {0: 0, 3: 0, 1: 1, 2: 1}
RCOL = {0: BLUE, 1: PINK}
for i in range(8):
    x = x0 + i * (CELL + GAP)
    col = RCOL[rank_of_part[part_of[i]]]
    d.rect(x, row_y, CELL, CELL, fill=col[1], stroke=col, rx=4, sw=1.4)
    d.text(x + CELL / 2, row_y + 24, f"t{i}", 14, col[0], "bold", "middle", mono=True)
    d.text(x + CELL / 2, row_y + 42, f"{i + 1} key" + ("s" if i else ""), 11, MUTE, anchor="middle", mono=True)
for p in range(4):
    x = x0 + p * 2 * (CELL + GAP)
    w = 2 * CELL + GAP
    col = RCOL[rank_of_part[p]]
    d.line(x, row_y - 10, x + w, row_y - 10, col, sw=2)
    d.text(x + w / 2, row_y - 16, f"part {p} · r{rank_of_part[p]}", 11.5, col[0], "bold", "middle", mono=True)
d.text(x0 + 8 * (CELL + GAP) + 6, row_y + 24, "causal: token i", 11.5, MUTE, italic=True)
d.text(x0 + 8 * (CELL + GAP) + 6, row_y + 41, "reads i + 1 keys", 11.5, MUTE, italic=True)

# rank rows
ry = row_y + CELL + 40
BW = 480
for r, (rows, keys, naive) in enumerate((
    ("t0 t1 t6 t7", "1 + 2 + 7 + 8 = 18", "t0..t3: 1+2+3+4 = 10"),
    ("t2 t3 t4 t5", "3 + 4 + 5 + 6 = 18", "t4..t7: 5+6+7+8 = 26"),
)):
    col = RCOL[r]
    bx = 46 + r * (BW + 28)
    d.rect(bx, ry, BW, 110, fill=col[1], stroke=col, sw=1.5)
    d.text(bx + 14, ry + 22, f"rank {r} (cp_rank {r})", 14, col[0], "bold")
    d.text(bx + 14, ry + 46, f"mirror_cp_index = [{', '.join(rows.replace('t', '').split())}]", 12.5, INK, mono=True)
    d.text(bx + 14, ry + 66, f"query rows: {rows}", 12.5, INK, mono=True)
    d.text(bx + 14, ry + 86, f"keys read: {keys}", 12.5, INK, mono=True)
    d.text(bx + 14, ry + 103, f"plain split would be {naive}", 11.5, MUTE, mono=True)
d.text(46, ry + 136, "mirror_cp_reverse_index = [0, 1, 4, 5, 6, 7, 2, 3]: row of token i in the gathered tensor [rank 0 rows | rank 1 rows].",
       12, INK)

# ---------------------------------------------------------------------------
# Panel 2: the data flow of one CP prefill step
# ---------------------------------------------------------------------------
y1 = y0 + P1_H + 20
CARD_H = 52
CARD_GAP = 14
steps = [
    ("embed all tokens, then keep own rows", "input_ids [8] -> hidden [8, H] -> gather(mirror_cp_index) -> [4, H]", "deepseek.py:161-170", EMERALD),
    ("attention: project K/V for own rows", "projected KV [4, ...] on each rank", "attn.py:766-768", EMERALD),
    ("all-gather over the CP group (CPManager)", "[2 x 4, ...] -> reorder with reverse index -> full KV [8, ...]", "attn.py:782-829", AMBER),
    ("store full KV, attend for own 4 queries", "each CP rank keeps the whole KV; queries stay [4, heads, d]", "attn.py:830-869", EMERALD),
    ("MoE on own rows (EP dispatch / combine)", "[4, H] per rank; padding rows have valid_token_mask = False", "mlp.py:565-616", EMERALD),
    ("after the last layer: all-gather hidden", "[2 x 4, H] -> gather(mirror_cp_reverse_index) -> [8, H]", "deepseek.py:241-244", AMBER),
]
P2_H = 72 + len(steps) * (CARD_H + CARD_GAP) - CARD_GAP + 22
d.panel(y1, P2_H, 2, "What does each rank do in the step?",
        "Each rank computes its own rows. Two kinds of all-gather give every rank the full KV and the full output.")
cy = y1 + 72
for i, (title, row, cite, col) in enumerate(steps):
    d.rect(46, cy, 1008, CARD_H, fill=col[1], stroke=col, sw=1.4)
    d.rect(46, cy, 6, CARD_H, fill=col[0], stroke=None, rx=3)
    d.badge(70, cy + 17, i + 1, col, r=10, size=11)
    d.text(88, cy + 22, title, 13.5, INK, "bold")
    d.text(88, cy + 41, row, 12.5, INK, mono=True)
    d.pill_auto(1054 - 10 - (len(cite) * 11 * 0.602 + 20), cy + 8, cite, col[0])
    if i < len(steps) - 1:
        d.arrow(70, cy + CARD_H, 70, cy + CARD_H + CARD_GAP - 2, col)
    cy += CARD_H + CARD_GAP

y = y1 + P2_H + 22
d.legend(30, y, [(BLUE, "rank 0"), (PINK, "rank 1"), (EMERALD, "compute on own rows"), (AMBER, "CP all-gather")])
y += 38
y = d.footnotes(30, y, [
    "H = hidden size (from the checkpoint, not in the repo). Steps 2-4 run in every attention layer; one CP session per layer.",
    "With cached context or several sequences, each sequence is split the same way, one after the other (prepare_cp_mirror.py:143-156).",
    "Decode steps do not use this layout: every CP rank gets the same decode batch (attn.py:766).",
])
d.save(height=y + 10)
