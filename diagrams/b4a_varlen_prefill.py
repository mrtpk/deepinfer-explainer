"""Diagram: the input metadata of one prefill step with two chunks (worked example).

Used by: src/concepts/input-metadata.html
Sources (commit 9bd9cf2):
  csrc/engine/input_metadata/prepare_tensor_input_base.cpp:88-96    positions = seqlen_k - seqlen_q ... seqlen_k - 1
  csrc/engine/input_metadata/prepare_tensor_input_v4.cpp:407-418    cu_seqlens_q / cu_seqlens_k (num_seqs + 1 values)
  csrc/engine/input_metadata/prepare_tensor_input_v4.cpp:46-69      prefill positions_c / slot_mapping_store_ca
  csrc/engine/input_metadata/prepare_tensor_input_v4.cpp:98-115     slot_mapping_store_swa, state_block_idx
  csrc/engine/input_metadata/prepare_tensor_input_v4.cpp:362-389    load_segments_swa (block load plan of the SWA history)
  csrc/engine/input_metadata/prepare_tensor_input_v4.cpp:487-527    kv_swa_full_index_pivots
  deepinfer/worker/cache_engine.py:88-93                              swa_block_size = window + DEEPINFER_MAX_BACKTRACKING_TOKENS
Numbers: illustrative sequences A (last chunk of a 260-token prompt: q 60, k 260, blocks [7,2,9], state slot 2) and
B (first chunk of a 400-token prompt: q 200, k 200, blocks [3,4,5,6], state slot 1); window 128, ring 134,
ratio 2 -> 64 entries per block. B is last because the scheduler stops after a cut chunk (scheduler.hpp:543-545).
Every array value is computed with the rules above.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, MUTE, NEUTRAL, PINK, VIOLET, Diagram  # noqa: E402

d = Diagram(width=1100)
W = d.W
d.header(
    "Input metadata of one prefill step",
    "Two prompt chunks packed into one list of 260 rows  ·  values follow the real C++ rules  ·  sequences are illustrative",
    params="A: q 60, k 260, blocks [7,2,9], slot 2   B: q 200, k 200, blocks [3,4,5,6], slot 1   ring 134",
)

X0 = 46
XW = 1008  # strip width
SCALE = XW / 260.0

# ============================================================================
# Panel 1: packing
# ============================================================================
y0 = 112
P1_H = 222
d.panel(y0, P1_H, 1, "How are the two chunks packed?",
        "The rows follow each other with no gaps. Offset arrays mark where each chunk starts.")
sy = y0 + 74
wa = 60 * SCALE
d.rect(X0, sy, wa, 34, fill=BLUE[1], stroke=BLUE[0], rx=4, sw=1.4)
d.text(X0 + wa / 2, sy + 22, "A: rows 0-59", 12.5, BLUE[0], "bold", "middle")
d.rect(X0 + wa, sy, XW - wa, 34, fill=PINK[1], stroke=PINK[0], rx=4, sw=1.4)
d.text(X0 + wa + (XW - wa) / 2, sy + 22, "B: rows 60-259  (first chunk of a 400-token prompt, cut at 200)", 12.5, PINK[0],
       "bold", "middle")
for r, lab in [(0, "0"), (60, "60"), (260, "260")]:
    xx = X0 + r * SCALE
    d.text(xx, sy + 50, lab, 11, MUTE, anchor="middle" if 0 < r < 260 else ("start" if r == 0 else "end"), mono=True)

rows1 = [
    ("positions", "[260]", "A: 200, 201, ..., 259      B: 0, 1, ..., 199"),
    ("cu_seqlens_q", "[3]", "[0, 60, 260]      running sum of seqlen_q"),
    ("cu_seqlens_k", "[3]", "[0, 260, 460]     running sum of seqlen_k"),
    ("state_block_idx", "[2]", "[2, 1]            one state slot per sequence"),
]
for i, (k, shape, v) in enumerate(rows1):
    yy = sy + 76 + i * 20
    d.text(X0, yy, k, 12, INK, "bold", mono=True)
    d.text(X0 + 170, yy, shape, 12, MUTE, mono=True)
    d.text(X0 + 230, yy, v, 12, INK, mono=True)

# ============================================================================
# Panel 2: cache writes
# ============================================================================
y1 = y0 + P1_H + 20
P2_H = 236
d.panel(y1, P2_H, 2, "Where do the new cache entries go?",
        "One slot per new entry. The value -1 means: do not write.")
sy = y1 + 72
d.text(X0, sy, "slot_mapping_store_swa  [260]   state_id * 134 + position % 134, only for the last 134 rows of a chunk",
       12, EMERALD[0], "bold", mono=True)
segs = [
    (0, 60, "334 ... 393", EMERALD),
    (60, 126, "-1", NEUTRAL),
    (126, 194, "200 ... 267", EMERALD),
    (194, 260, "134 ... 199", EMERALD),
]
for a, b, lab, col in segs:
    xa = X0 + a * SCALE
    xb = X0 + b * SCALE
    d.rect(xa, sy + 12, xb - xa, 28, fill=col[1], stroke=col[0], rx=3, sw=1.2)
    d.text((xa + xb) / 2, sy + 31, lab, 12, INK, anchor="middle", mono=True)
d.text(X0, sy + 58, "B rows 60-125 (positions 0-65) are older than the ring keeps.  Position 134 wraps to ring row 0.", 11.5,
       MUTE, italic=True)

sy2 = sy + 86
d.text(X0, sy2, "slot_mapping_store_ca[\"2\"]  [130]   one entry per 2 tokens: block_table[j / 64] * 64 + j % 64",
       12, VIOLET[0], "bold", mono=True)
SC2 = XW / 130.0
segs2 = [
    (0, 28, "A: block 2 -> 164 ... 191", BLUE),
    (28, 30, "", BLUE),
    (30, 94, "B j 0-63: block 3 -> 192 ... 255", PINK),
    (94, 130, "B j 64-99: block 4 -> 256 ... 291", PINK),
]
for a, b, lab, col in segs2:
    xa = X0 + a * SC2
    xb = X0 + b * SC2
    d.rect(xa, sy2 + 12, xb - xa, 28, fill=VIOLET[1], stroke=col[0], rx=3, sw=1.2)
    if lab:
        d.text((xa + xb) / 2, sy2 + 31, lab, 11.5, INK, anchor="middle", mono=True)
d.text(X0, sy2 + 58, "A j 128-129: block 9 -> 576, 577", 11.5, BLUE[0], "bold", mono=True)
d.text(X0 + XW, sy2 + 58, "positions_c[\"2\"] = 2 * j:  200, 202, ..., 258 | 0, 2, ..., 198", 11.5, MUTE, anchor="end",
       mono=True)

# ============================================================================
# Panel 3: SWA reads
# ============================================================================
y2 = y1 + P2_H + 20
P3_H = 290
d.panel(y2, P3_H, 3, "What does each row read from the sliding window?",
        "A gather builds one buffer: 128 history rows per chunk, then all new rows. Pivots describe each row's window.")
sy = y2 + 72
SC3 = XW / 516.0
bufs = [
    (0, 128, "A history: positions 72-199", BLUE),
    (128, 256, "B history: zero fill", NEUTRAL),
    (256, 516, "new rows of this step (A 256-315, B 316-515)", AMBER),
]
for a, b, lab, col in bufs:
    xa = X0 + a * SC3
    xb = X0 + b * SC3
    d.rect(xa, sy, xb - xa, 30, fill=col[1], stroke=col[0], rx=3, sw=1.2)
    d.text((xa + xb) / 2, sy + 20, lab, 12, INK, anchor="middle")
for r in (0, 128, 256, 516):
    d.text(X0 + r * SC3, sy + 46, str(r), 11, MUTE, anchor="middle" if 0 < r < 516 else ("start" if r == 0 else "end"),
           mono=True)

d.text(X0, sy + 74, "load_segments_swa  [3, 4]   rows: [src slot, src_begin, src_end, dst_offset]", 12, INK, "bold", mono=True)
d.text(X0 + 18, sy + 94, "[2, 72, 134, 0]   [2, 0, 66, 62]   [-1, 0, 128, 128]        -1 = fill with zeros",
       12, INK, mono=True)

d.text(X0, sy + 124, "kv_swa_full_index_pivots  [260, 4]   [history start, history count, new start, new count]",
       12, INK, "bold", mono=True)
piv = [
    ("A row 0   (pos 200)", "[  1, 127, 256,   1]", "127 history rows (73-199) + itself"),
    ("A row 59  (pos 259)", "[ 60,  68, 256,  60]", "68 history rows (132-199) + 60 new rows"),
    ("B row 60  (pos 0)  ", "[256,   0, 316,   1]", "no history: sees only itself"),
    ("B row 259 (pos 199)", "[256,   0, 388, 128]", "128 new rows: positions 72-199"),
]
for i, (a, b, c) in enumerate(piv):
    yy = sy + 144 + i * 17
    col = BLUE[0] if a.startswith("A") else PINK[0]
    d.text(X0 + 18, yy, a, 12, col, "bold", mono=True)
    d.text(X0 + 200, yy, b, 12, INK, mono=True)
    d.text(X0 + 400, yy, c, 12, MUTE)

y = y2 + P3_H + 24
d.legend(30, y, [(BLUE, "sequence A"), (PINK, "sequence B"), (EMERALD, "SWA ring slot"), (VIOLET, "C2 cache slot"),
                 (AMBER, "new rows")])
y += 40
y = d.footnotes(30, y, [
    "Simplified: only ratio 2 is shown. The dicts have one entry per compress ratio of the model (C1 and/or C2).",
    "Not shown: input_ids, ks/ke, kv_ca_index_offset_len, load_segments_ca, cu_compressed_seqlens_q (see the deep dive).",
])
d.save(height=y + 14)
