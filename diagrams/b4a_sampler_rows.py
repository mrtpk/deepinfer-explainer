"""Diagram: which model-output rows the sampler reads (prepare_sampler_inputs), prefill and decode.

Used by: src/code/prepare-sample-cpp.html
Sources (commit 9bd9cf2):
  csrc/engine/prepare_sample.cpp:82-88      one temperature/top-p/top-k/seed per sequence (num_sampling_positions)
  csrc/engine/prepare_sample.cpp:163-200    prefill: last row of each chunk; sample_positions = seqlen_k; YOCO compact keep_len
  csrc/engine/prepare_sample.cpp:200-207    decode: every row; sample_positions = seqlen_k - seqlen_q + 1
  csrc/engine/prepare_sample.cpp:209-226    speculative: mtp_info_read_rows, write slots, stop tokens
Numbers: the same illustrative batches as the input-metadata page: prefill A (q 60, k 260) + B (q 200, k 200, prompt 400);
decode C (q 6, k 306, MTP slot 2) + D (q 6, k 134, MTP slot 1), graph size 16, nextn 5, EOS id 1.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, MUTE, NEUTRAL, PINK, VIOLET, Diagram  # noqa: E402

d = Diagram(width=1100)
W = d.W
d.header(
    "Which output rows does the sampler read?",
    "prepare_sampler_inputs turns the scheduled sequences into row indices and per-sequence values  ·  illustrative batches",
    params="prefill: A q 60 k 260, B q 200 k 200   decode: C k 306 slot 2, D k 134 slot 1, graph 16   nextn 5",
)
X0 = 46
XW = 1008

# ============================================================================
# Panel 1: prefill
# ============================================================================
y0 = 112
P1_H = 226
d.panel(y0, P1_H, 1, "Prefill: one sampled row per chunk",
        "The sampler reads the last row of each chunk. B is not the last chunk, so its token is dropped later.")
sy = y0 + 70
sc = XW / 260.0
d.rect(X0, sy, 60 * sc, 30, fill=BLUE[1], stroke=BLUE[0], rx=3, sw=1.2)
d.text(X0 + 30 * sc, sy + 20, "A rows 0-59", 12, BLUE[0], "bold", "middle")
d.rect(X0 + 60 * sc, sy, 200 * sc, 30, fill=PINK[1], stroke=PINK[0], rx=3, sw=1.2)
d.text(X0 + 160 * sc, sy + 20, "B rows 60-259", 12, PINK[0], "bold", "middle")
for r, col in [(59, BLUE), (259, PINK)]:
    xx = X0 + (r + 0.5) * sc
    d.rect(xx - 4, sy - 4, 8, 38, fill=AMBER[0], stroke=None, rx=2)
    d.text(xx, sy + 50, f"row {r}", 11.5, AMBER[0], "bold", "end" if r == 259 else "middle", mono=True)
lines = [
    ("selected_token_indices", "[59, 259]", "last row of each chunk"),
    ("sample_positions", "[260, 200]", "seqlen_k: the position of the next token"),
    ("temperatures, top_ps, ...", "[2]", "one value per sequence"),
    ("YOCO compact, keep 140", "[59, 60]", "B keeps 1 row, so the output has 61 rows"),
]
for i, (k, v, c) in enumerate(lines):
    yy = sy + 80 + i * 20
    d.text(X0, yy, k, 12, INK, "bold", mono=True)
    d.text(X0 + 250, yy, v, 12, AMBER[0] if i != 2 else INK, "bold", mono=True)
    d.text(X0 + 370, yy, c, 12, MUTE)

# ============================================================================
# Panel 2: decode
# ============================================================================
y1 = y0 + P1_H + 20
P2_H = 272
d.panel(y1, P2_H, 2, "Decode: every real row is sampled",
        "The sampler reads all 12 real rows. Padding rows 12-15 are not in the list, so it never reads them.")
sy = y1 + 72
CW = XW / 16.0
for i in range(16):
    col = BLUE if i < 6 else (PINK if i < 12 else NEUTRAL)
    d.rect(X0 + i * CW, sy, CW - 3, 26, fill=col[1], stroke=col[0], rx=2, sw=0.9)
    d.text(X0 + i * CW + (CW - 3) / 2, sy + 17, str(i), 11.5, INK, anchor="middle", mono=True)
d.text(X0 + 3 * CW, sy + 44, "C: last real token + 5 drafts", 12, BLUE[0], "bold", "middle")
d.text(X0 + 9 * CW, sy + 44, "D: last real token + 5 drafts", 12, PINK[0], "bold", "middle")
d.text(X0 + 14 * CW, sy + 44, "graph padding", 12, MUTE, "bold", "middle")
lines = [
    ("selected_token_indices", "[0, 1, ..., 11]", "12 rows, padding excluded"),
    ("mtp_first_token_positions", "[0, 6]", "first row of each sequence"),
    ("mtp_seqlens_q", "[6, 6]", "rows per sequence"),
    ("sample_positions", "[301, 129]", "seqlen_k - seqlen_q + 1"),
    ("mtp_info_read_rows", "[10..14, 0, 5..9, 0]", "slot * 5 + j; the last row of each reads slot 0"),
    ("stop_token_ids", "[[1, -1], [1, -1]]", "EOS, or -1 when ignore_eos"),
]
for i, (k, v, c) in enumerate(lines):
    yy = sy + 74 + i * 20
    d.text(X0, yy, k, 12, INK, "bold", mono=True)
    d.text(X0 + 250, yy, v, 12, EMERALD[0] if i < 4 else VIOLET[0], "bold", mono=True)
    d.text(X0 + 470, yy, c, 12, MUTE)

y = y1 + P2_H + 24
d.legend(30, y, [(AMBER, "prefill sample row"), (EMERALD, "decode rows"), (VIOLET, "speculative fields"),
                 (NEUTRAL, "padding")])
y += 40
y = d.footnotes(30, y, [
    "All arrays are int32 (seeds uint64, temperature and top-p float32) in pinned CPU memory, then copied without a wait.",
    "Simplified: prompt log-probabilities and golden tokens add more arrays (see the page).",
])
d.save(height=y + 14)
