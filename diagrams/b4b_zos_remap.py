"""Diagram: the three C++ functions of csrc/engine/zos.cpp on one worked example
(3 decode sequences A, B, C; nextn 5; a CUDA graph of 24 tokens).

Used by: src/code/zos-cpp.html, src/tours/engine-step.html
Sources (commit 9bd9cf2):
  csrc/engine/zos.cpp:147-173     remap: same-order fast path, else a hash map seq_id -> previous index
  csrc/engine/zos.cpp:178-195     pinned remap / seqlens_q / seqlens_k; k = seqlen_k - seqlen_q; padding rows -1, 1, 1
  deepinfer/worker/worker.py:203-205   n_seq_with_padding = n_seq + graph size - total_q
  deepinfer/model_executor/layers/tilelang_ops/compute_seqlens_k_zos.py:18-23   k += q - (nextn - accepted[remap])
  csrc/engine/zos.cpp:84-137      prepare_token_inputs with overlap: only fresh rows are filled on the CPU
  deepinfer/model_executor/layers/tilelang_ops/gather_input_ids_zos.py:21-29     matched rows read step N outputs
  csrc/engine/zos.cpp:279-305     update_metadata_for_sampling_zos: seqlen_k = seqlen_q + cache.num_tokens
  csrc/engine/scheduler.hpp:697, 726   CPU seqlen_k = num_tokens + in-flight + seqlen_q
Example values are illustrative (cache sizes, accepted counts); the formulas are the code's.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, CELL_EMPTY, EMERALD, INK, MUTE, VIOLET, WHITE, Diagram  # noqa: E402

d = Diagram(width=1100)
W = d.W
d.header(
    "zos.cpp on one example: match, correct, refresh",
    "Step N ran B, A, C (in this order). Step N+1 schedules A, B, C before step N is post-processed  ·  nextn = 5",
    params="total_q = 3 x 6 = 18  ->  CUDA graph of 24 tokens  ->  n_seq_with_padding = 3 + 24 - 18 = 9",
)

# ============================================================================
# Panel 1: remap
# ============================================================================
y0 = 112
P1_H = 212
d.panel(y0, P1_H, 1, "Which row of step N belongs to each sequence of step N+1?",
        "prepare_zos_inputs compares seq_id. The order changed, so it builds a hash map (zos.cpp:160-173).")
r = y0 + 72
cw, ch, gap = 92, 34, 10
d.text(46, r + 22, "step N", 13, INK, "bold")
d.text(46, r + 104, "step N+1", 13, INK, "bold")
prev = ["B", "A", "C"]
curr = ["A", "B", "C"]
cols = {"A": BLUE, "B": VIOLET, "C": EMERALD}
px0 = 170
for j, s in enumerate(prev):
    x = px0 + j * (cw + gap)
    d.rect(x, r, cw, ch, fill=cols[s][1], stroke=cols[s], rx=6, sw=1.4)
    d.text(x + cw / 2, r + 22, f"{j}: {s}", 13, cols[s], "bold", "middle", mono=True)
for i, s in enumerate(curr):
    x = px0 + i * (cw + gap)
    d.rect(x, r + 82, cw, ch, fill=cols[s][1], stroke=cols[s], rx=6, sw=1.4)
    d.text(x + cw / 2, r + 104, f"{i}: {s}", 13, cols[s], "bold", "middle", mono=True)
    j = prev.index(s)
    d.arrow(px0 + j * (cw + gap) + cw / 2, r + ch, x + cw / 2, r + 80, cols[s], sw=1.4)
# padding rows
xp = px0 + 3 * (cw + gap)
d.rect(xp, r + 82, 200, ch, fill=WHITE, stroke=MUTE, rx=6, sw=1.2, dash="4 3")
d.text(xp + 100, r + 104, "3..8: graph padding", 12.5, MUTE, "bold", "middle", mono=True)
# result
rx0 = 700
d.text(rx0, r + 14, "result (pinned int32 [9])", 12.5, INK, "bold")
d.text(rx0, r + 36, "remap = [1, 0, 2, -1, -1, -1, -1, -1, -1]", 12.5, INK, mono=True)
d.text(rx0, r + 58, "has_overlap = True", 12.5, INK, mono=True)
d.aside(rx0, r + 86, ["Same order and same length: remap[i] = i,",
                      "no hash map (zos.cpp:148-157).",
                      "No common sequence: return (None, ..., False)."])

# ============================================================================
# Panel 2: seqlens sent and corrected
# ============================================================================
y1 = y0 + P1_H + 20
P2_H = 212
d.panel(y1, P2_H, 2, "Which lengths go to the device, and how does a kernel fix them?",
        "C++ sends seqlen_k - seqlen_q. compute_seqlens_k_zos adds seqlen_q and removes the drafts that step N rejected.")
ty = y1 + 80
hdr = "  i  seq   CPU seqlen_k        sent k  accepted(N)  device k = sent + 6 - (5 - acc)"
d.rect(46, ty - 18, W - 92, 26, fill="#f3f4f6", stroke=None, rx=4)
d.text(56, ty, hdr, 12.5, INK, "bold", mono=True)
rows = [
    ("  0  A     100 + 6 + 6 = 112   106     2            106 + 6 - 3 = 109", BLUE),
    ("  1  B      96 + 6 + 6 = 108   102     5            102 + 6 - 0 = 108", VIOLET),
    ("  2  C      35 + 6 + 6 =  47    41     0             41 + 6 - 5 =  42", EMERALD),
    ("3-8  pad                         1     -              1   (the kernel gets only rows 0-2)", MUTE),
]
for i, (s, c) in enumerate(rows):
    d.text(56, ty + 26 + i * 22, s, 12.5, c if c == MUTE else INK, mono=True)
d.text(56, ty + 26 + 4 * 22 + 8, "CPU seqlen_k = cache.num_tokens + in-flight (6, step N) + seqlen_q (6)   (scheduler.hpp:697)",
       12, MUTE, italic=True)

# ============================================================================
# Panel 3: inputs and refresh
# ============================================================================
y2 = y1 + P2_H + 20
P3_H = 204
d.panel(y2, P3_H, 3, "Where do the input tokens come from, and what does the CPU fix later?",
        "Matched rows read step N outputs on the device. After the post-process of N, the CPU sets seqlen_k from the cache.")
by = y2 + 70
bw, bh = 316, 96
xs = [46, 392, 738]
d.box(xs[0], by, bw, bh, "1  CPU tokens (fresh rows only)", [
    "fresh_input_ids [9, 6] pinned",
    "rows 0-2 matched: left as 0",
    "a fresh row: last token + drafts",
    "zos.cpp:84-137",
], col=INK, fill=CELL_EMPTY, align="start", mono_size=12)
d.box(xs[1], by, bw, bh, "2  device gather (row A)", [
    "j = 0: prev_sampled[remap=1]",
    "j > 0: prev_predict[1, j - 1]",
    "-> [r_A, e1, e2, e3, e4, e5]",
    "gather_input_ids_zos.py:21-29",
], col=AMBER, align="start", mono_size=12)
d.box(xs[2], by, bw, bh, "3  before sampling (CPU)", [
    "post-process N: A cache 103",
    "seqlen_k = 6 + 103 = 109",
    "remap >= 0: refresh_for_sampling",
    "zos.cpp:297-302",
], col=INK, fill=CELL_EMPTY, align="start", mono_size=12)
d.arrow(xs[0] + bw, by + bh / 2, xs[1] - 2, by + bh / 2, INK)
d.arrow(xs[1] + bw, by + bh / 2, xs[2] - 2, by + bh / 2, AMBER)

y = y2 + P3_H + 22
d.legend(30, y, [(BLUE, "request A"), (VIOLET, "request B"), (EMERALD, "request C"), (AMBER, "device kernel"), ((INK, CELL_EMPTY), "CPU (C++)")])
y += 34
y = d.footnotes(30, y, [
    "Illustrative cache sizes and accepted counts. With DEEPINFER_ENABLE_MTP_VARLEN=1 a second kernel also changes seqlens_q first (worker.py:218-219).",
    "Padding rows: CUDA graph rows of the placeholder sequence; seqlens_q = seqlens_k = 1 (zos.cpp:190-194). The worker passes [:n_seq] to the kernel.",
])
d.save(height=y + 10)
