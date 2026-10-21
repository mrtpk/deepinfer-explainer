"""Diagram: how a block table becomes the index tensors that the attention kernels read.

Used by: src/concepts/paged-kv-cache.html
Sources (commit 9bd9cf2):
  csrc/engine/sequence.hpp:349,379                         SequenceMetadata.block_table is a reference to the sequence's table
  csrc/engine/input_metadata/prepare_tensor_input_v4.cpp:41-61   prefill: slot_mapping_store_ca per compress ratio
  csrc/engine/input_metadata/prepare_tensor_input_v4.cpp:98-108  slot_mapping_store_swa: state_id * swa_block_size + pos % swa_block_size
  csrc/engine/input_metadata/prepare_tensor_input_v4.cpp:111-115 state_block_idx (prefill: one per sequence)
  csrc/engine/input_metadata/prepare_tensor_input_base.cpp:208-229  decode without ZOS: block_tables [total_q, max_num_blocks]
  csrc/engine/zos.cpp:242-270                              decode with ZOS: flat block_tables + offsets, state_ids
  deepinfer/model_executor/input_metadata/prepare_tensor_input_zos.py:336-367  device kernel prepare_v4_decode_metadata
  deepinfer/model_executor/model_metadata_utils.py:143     ZOS on -> prepare_decode_v4_zos
  deepinfer/worker/model_runner.py:115                     max_num_blocks = ceil(runtime_max_model_len / 128) rounded up to 64
Numbers: sequence B of the first diagram (1000-token prompt, block table [5,6,7,8,9,4,3,2], state slot 2),
SWA ring of 134 tokens (128 window + 6 backtracking), runtime_max_model_len 32784.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, MUTE, PINK, VIOLET, Diagram  # noqa: E402

d = Diagram(width=1100)
W = d.W
d.header(
    "From a block table to kernel indices",
    "C++ turns each sequence's block table and state slot into int32 index tensors  ·  one example sequence",
    params="block 128   C1: 128 entries/block   C2: 64 entries/block   SWA ring 134   B = [5,6,7,8,9,4,3,2], slot 2",
)

# ============================================================================
# Panel 1: prefill
# ============================================================================
y0 = 112
P1_H = 262
d.panel(y0, P1_H, 1, "Prefill: where does each new entry go?",
        "prepare_prompt_v4 computes one slot per new cache entry. -1 means: do not write.")
d.box(46, y0 + 74, 290, 112, "Sequence B (C++)", [
    "block_table [5,6,7,8,9,4,3,2]",
    "state_id    2",
    "seqlen_q    1000",
    "seqlen_k    1000",
], col=PINK, align="start", mono_size=12)
d.text(46, y0 + 210, "SequenceMetadata keeps a reference", 12, MUTE, italic=True)
d.text(46, y0 + 227, "to this table; it does not copy it.", 12, MUTE, italic=True)
d.arrow(338, y0 + 130, 396, y0 + 130, PINK)
d.arrow_label(367, y0 + 130, "C++", PINK)

rows = [
    (BLUE, "slot_mapping_store_ca[\"1\"]", "[1000]", "entry 999 -> table[7]=2 -> 2*128 + 103 = 359"),
    (VIOLET, "slot_mapping_store_ca[\"2\"]", "[500]", "entry 499 -> table[7]=2 -> 2*64 + 51 = 179"),
    (EMERALD, "slot_mapping_store_swa", "[1000]", "token 999 -> 2*134 + 999%134 = 329"),
    (EMERALD, "", "", "tokens 0-865 -> -1 (outside the ring)"),
    (AMBER, "state_block_idx", "[1]", "[2]: one state slot per sequence"),
]
for i, (col, name, shape, note) in enumerate(rows):
    yy = y0 + 92 + i * 30
    if name:
        d.text(400, yy, name, 12, col[0], "bold", mono=True)
        d.text(640, yy, shape, 12, INK, mono=True)
    d.text(700, yy, note, 12, INK, mono=True)
d.text(400, y0 + 250, "int32 tensors, one dict entry per compress ratio (prepare_tensor_input_v4.cpp:40-108)", 11.5, MUTE,
       italic=True)

# ============================================================================
# Panel 2: decode
# ============================================================================
y1 = y0 + P1_H + 20
P2_H = 246
d.panel(y1, P2_H, 2, "Decode: who copies the block tables?",
        "With ZOS (the default) C++ only packs the tables; a device kernel computes the slots.")

d.step_card(46, y1 + 70, 480, 132, 1, "ZOS off: C++ does all", BLUE, tag="base.cpp:208",
            rows=[("out", "block_tables int32 [total_q, 320]"),
                  ("why", "one row per query token"),
                  ("ex.", "4 seqs x 6 tokens = [24, 320]"),
                  ("", "= 30,720 bytes"),
                  ("+", "slot mappings, as in panel 1")], key_w=40)
d.step_card(560, y1 + 70, 494, 132, 2, "ZOS on (default): C++ packs", EMERALD, tag="zos.cpp:246",
            rows=[("out", "block_tables int32 [total_blocks]"),
                  ("", "offsets int32 [n_seq + 1]"),
                  ("ex.", "1 seq, 8 blocks: offsets [0, 8]"),
                  ("then", "device kernel"),
                  ("", "prepare_v4_decode_metadata")], key_w=40)
d.text(46, y1 + 226, "320 = ceil(32784 / 128) = 257, rounded up to a multiple of 64 (model_runner.py:115).", 12, MUTE)

y = y1 + P2_H + 24
d.legend(30, y, [(PINK, "sequence state"), (BLUE, "C1 cache"), (VIOLET, "C2 cache"), (EMERALD, "SWA ring"),
                 (AMBER, "state slot")])
y += 40
y = d.footnotes(30, y, [
    "Simplified: the dict has one tensor per compress ratio of the model. The indexer keys (ica_cache) are not shown.",
    "The decode slot of a C2 layer is -1 unless (position + 1) % 2 == 0 (prepare_tensor_input_v4.cpp:80-91).",
])
d.save(height=y + 14)
