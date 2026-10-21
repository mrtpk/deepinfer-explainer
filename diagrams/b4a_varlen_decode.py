"""Diagram: the input metadata of one decode step, padded to a captured CUDA graph size (worked example).

Used by: src/concepts/input-metadata.html, src/concepts/cuda-graphs.html
Sources (commit 9bd9cf2):
  deepinfer/worker/cuda_graph_runner.py:41-51,143-148          graph sizes and select (smallest size >= total_q)
  deepinfer/worker/model_runner.py:184-191                      padding sequences fill the rows up to the graph size
  deepinfer/worker/model_runner.py:386-403                      placeholder: seqlen_q 1, seqlen_k 1, block_table [0]
  csrc/engine/pybind_sequence.cpp:152                            default state_id 0 (the placeholder does not set it)
  csrc/engine/input_metadata/prepare_tensor_input_base.cpp:173-182   valid_token_mask
  csrc/engine/input_metadata/prepare_tensor_input_base.cpp:189-205   context_lens
  csrc/engine/input_metadata/prepare_tensor_input_base.cpp:232-251   query_indices (998244353 for placeholders)
  csrc/engine/input_metadata/prepare_tensor_input_v4.cpp:70-95       decode positions_c / slot_mapping_store_ca
  csrc/engine/input_metadata/prepare_tensor_input_v4.cpp:98-126      slot_mapping_store_swa, state_block_idx
  csrc/engine/input_metadata/prepare_tensor_input_v4.cpp:639-652     kv_swa_index_offset_len
Numbers: max_num_seqs 4, nextn 5 -> sizes [1, 2, 4, 8, 16, 24]. Illustrative sequences C (k 306, blocks [5,6,8],
state slot 3) and D (k 134, blocks [10,11], state slot 4); ZOS off, so C++ writes every row.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, MUTE, NEUTRAL, PINK, VIOLET, Diagram  # noqa: E402

d = Diagram(width=1100)
W = d.W
d.header(
    "Input metadata of one decode step",
    "Two sequences send 1 + 5 tokens each  ·  12 real rows, padded to the captured graph size 16  ·  ZOS off",
    params="sizes [1, 2, 4, 8, 16, 24]   C: k 306, blocks [5,6,8], slot 3   D: k 134, blocks [10,11], slot 4",
)

X0 = 46
KEYW = 214
CX = X0 + KEYW          # first cell x
CW = 51                 # cell width
NC = 16


def cell_col(i):
    return BLUE if i < 6 else (PINK if i < 12 else NEUTRAL)


def row(y, key, vals, keycol=INK, size=11.5):
    d.text(X0, y + 15, key, 12, keycol, "bold", mono=True)
    for i, v in enumerate(vals):
        col = cell_col(i)
        d.rect(CX + i * CW, y, CW - 3, 22, fill=col[1], stroke=col[0], rx=2, sw=0.9)
        d.text(CX + i * CW + (CW - 3) / 2, y + 15, str(v), size, INK, anchor="middle", mono=True)


# ============================================================================
# Panel 1: rows
# ============================================================================
y0 = 112
P1_H = 238
d.panel(y0, P1_H, 1, "Which rows does the step have?",
        "select(12) picks the graph of size 16. Four placeholder sequences of one row each fill the rest.")
y = y0 + 66
d.text(CX + 3 * CW - 1, y + 10, "C: rows 0-5", 12, BLUE[0], "bold", "middle")
d.text(CX + 9 * CW - 1, y + 10, "D: rows 6-11", 12, PINK[0], "bold", "middle")
d.text(CX + 14 * CW - 1, y + 10, "padding: 12-15", 12, MUTE, "bold", "middle")
y += 20
row(y, "positions", [300, 301, 302, 303, 304, 305, 128, 129, 130, 131, 132, 133, 0, 0, 0, 0])
y += 28
row(y, "valid_token_mask", ["T"] * 12 + ["F"] * 4)
y += 28
row(y, "query_indices", [0] * 6 + [1] * 6 + ["big"] * 4)
y += 28
row(y, "context_lens", [301, 302, 303, 304, 305, 306, 129, 130, 131, 132, 133, 134, 1, 1, 1, 1])
y += 28
row(y, "state_block_idx", [3] * 6 + [4] * 6 + [0] * 4)

# ============================================================================
# Panel 2: cache writes and reads
# ============================================================================
y1 = y0 + P1_H + 20
P2_H = 232
d.panel(y1, P2_H, 2, "Where do the rows write, and what do they read?",
        "Each row writes its own SWA entry. Only odd positions finish a C2 entry. Padding writes only to slot 0 and block 0.")
y = y1 + 70
row(y, "slot_..._swa", [434, 435, 436, 437, 438, 439, 664, 665, 666, 667, 668, 669, 0, 0, 0, 0], EMERALD[0])
y += 28
row(y, "slot_..._ca[\"2\"]", [-1, 534, -1, 535, -1, 536, -1, 704, -1, 705, -1, 706, -1, -1, -1, -1], VIOLET[0])
y += 28
row(y, "slot_..._ca[\"1\"]", [1068, 1069, 1070, 1071, 1072, 1073, 1408, 1409, 1410, 1411, 1412, 1413, 0, 0, 0, 0],
    VIOLET[0], size=11)
y += 34
d.text(X0, y + 12, "block_tables  [16, 320]", 12, INK, "bold", mono=True)
d.text(X0 + KEYW, y + 12, "C rows: [5, 6, 8, ...]    D rows: [10, 11, ...]    padding rows: [0, ...]", 12, INK, mono=True)
y += 22
d.text(X0, y + 12, "kv_swa_index_offset_len", 12, INK, "bold", mono=True)
d.text(X0 + KEYW, y + 12, "C row 0: [441, 128]   D row 0: [537, 128]   padding: [0, 1]", 12, INK, mono=True)
y += 22
d.text(X0 + KEYW, y + 12, "[first ring slot of the window, window length];  441 = 3 * 134 + (300 - 127) % 134", 11.5, MUTE,
       italic=True)

# ============================================================================
# Panel 3: where the values land
# ============================================================================
y2 = y1 + P2_H + 20
P3_H = 128
d.panel(y2, P3_H, 3, "Where does C++ write these values?",
        "Straight into the input buffers of the graph. A replay copies them to the device and runs the model.")
d.box(46, y2 + 66, 300, 46, "out_dict", ["views [:16] of the size-24 buffers"], col=AMBER)
d.arrow(348, y2 + 89, 398, y2 + 89, AMBER)
d.box(400, y2 + 66, 300, 46, "graph of size 16", ["copy to device, then the model"], col=EMERALD)
d.arrow(702, y2 + 89, 752, y2 + 89, EMERALD)
d.box(754, y2 + 66, 300, 46, "output [16, ...]", ["sampler reads rows 0-11 only"], col=BLUE)

y = y2 + P3_H + 24
d.legend(30, y, [(BLUE, "sequence C"), (PINK, "sequence D"), (NEUTRAL, "padding row"), (EMERALD, "SWA ring"),
                 (VIOLET, "compressed cache")])
y += 40
y = d.footnotes(30, y, [
    "slot_... = slot_mapping_store_...  ·  big = 998244353, the padding sentinel  ·  T/F = True/False  ·  ... = not written by C++",
    "The example assumes a model with C1 and C2 layers; block_tables use the smallest ratio (here 1, so 128 tokens per block).",
    "With ZOS on (the default), C++ packs only per-sequence values, and the kernel prepare_v4_decode_metadata fills these rows.",
])
d.save(height=y + 14)
