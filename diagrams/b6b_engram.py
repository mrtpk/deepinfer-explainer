"""Diagram: Engram n-gram memory -- from token ids to table rows, and where the layer uses them.

Used by: src/concepts/engram.html, src/code/v4-engram.html
Sources (commit 9bd9cf2):
  deepinfer/model_executor/models/v4_modules/engram.py:35-66            CompressedTokenizer (lookup table, IMAGE_SENTINEL -1)
  deepinfer/model_executor/models/v4_modules/engram_metadata.py:16-52   CompressedVocabulary: normalize text, merge equal keys
  deepinfer/model_executor/models/v4_modules/engram_metadata.py:67-95   EngramLayout: one distinct prime per (layer, n-gram size, head)
  deepinfer/model_executor/models/v4_modules/engram_metadata.py:98-116  NgramHashMapping: odd int64 multipliers, sizes, offsets
  csrc/engine/input_metadata/prepare_tensor_input_base.cpp:10-35        fill_engram_row: column r = token at pos - r
  deepinfer/model_executor/models/v4_modules/engram_parameters.py:26-31    rows padded to lcm(256, enp), split evenly
  deepinfer/model_executor/models/deepseek.py:177-188                   engram_hash once per forward, fetch -> hooks
  deepinfer/model_executor/models/decoder_layer.py:111-118              hook after mHC post, before attention pre/norm
  deepinfer/model_executor/models/v4_modules/hc.py:220-227              intervention point
  deepinfer/model_executor/models/v4_modules/engram.py:139-161          Engram.forward
  deepinfer/model_executor/parallel_utils/userbuffer.py:148             CPU storage unless FORCE_GPU_STORAGE
  deepinfer/environ.py:147                                              FORCE_GPU_STORAGE always on for Ascend
  deepinfer/model_executor/input_metadata/prepare_tensor_input_zos.py:215-274  ZOS: C++ rows without overlap, device kernel with overlap
The toy numbers (vocab 1000, 2 heads, max n-gram 3, enp 8, multipliers 3/5/7, ids 17/42/7) are illustrative.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, MUTE, PINK, VIOLET, WHITE, Diagram  # noqa: E402

d = Diagram(width=1100)
d.header(
    "Engram: a learned vector for each recent n-gram",
    "Toy example with illustrative numbers  ·  the real hash formula is inside tile_kernels (not in this repo)",
    params="toy: engram_vocab_size 1000  ·  2 heads  ·  max_ngram_size 3 (2-grams, 3-grams)  ·  enp = 8 ranks",
)

# ============================================================================
# Panel 1: token -> compressed ids -> n-gram row -> 4 hashes
# ============================================================================
y0 = 112
BW, BH = 300, 150
XS = [46, 400, 754]
by = y0 + 72
P1_H = 72 + BH + 24
d.panel(y0, P1_H, 1, "Which rows does one token read?",
        "Compressed ids of the last 1-3 tokens give one hash per (n-gram size, head): 4 rows here.")

d.rect(XS[0], by, BW, BH, fill=BLUE[1], stroke=BLUE, sw=1.5)
d.text(XS[0] + 14, by + 24, "A. Compress the ids", 14, BLUE[0], "bold")
for i, s in enumerate(["\"Hello\"  -> 17", "\" hello\" -> 17", "\"HELLO\"  -> 17", "image id -> -1 (sentinel)"]):
    d.text(XS[0] + 14, by + 50 + i * 19, s, 12.5, INK, mono=True)
d.text(XS[0] + 14, by + 136, "CompressedTokenizer.encode", 12, MUTE, mono=True)

d.rect(XS[1], by, BW, BH, fill=VIOLET[1], stroke=VIOLET, sw=1.5)
d.text(XS[1] + 14, by + 24, "B. One row per query token", 14, VIOLET[0], "bold")
d.text(XS[1] + 14, by + 50, "ngram_token_ids [T, 3] int32", 12.5, INK, mono=True)
d.text(XS[1] + 14, by + 72, "r:      0    1    2", 12.5, MUTE, mono=True)
d.text(XS[1] + 14, by + 92, "row = [17,  42,   7]", 12.5, INK, mono=True)
d.text(XS[1] + 14, by + 112, "column r = token at pos - r", 12, MUTE, mono=True)
d.text(XS[1] + 14, by + 136, "fill_engram_row (C++) or ZOS kernel", 12, MUTE, mono=True)

d.rect(XS[2], by, BW, BH, fill=PINK[1], stroke=PINK, sw=1.5)
d.text(XS[2] + 14, by + 24, "C. Hash: 4 sub-table rows", 14, PINK[0], "bold")
for i, s in enumerate(["2-gram h0 % 1009 -> 225", "2-gram h1 % 1013 -> 225", "3-gram h0 % 1019 -> 208", "3-gram h1 % 1021 -> 208"]):
    d.text(XS[2] + 14, by + 50 + i * 19, s, 12.5, INK, mono=True)
d.text(XS[2] + 14, by + 136, "tile_kernels.engram.engram_hash", 12, MUTE, mono=True)

for x in (XS[0] + BW, XS[1] + BW):
    d.arrow(x, by + BH / 2, x + 52, by + BH / 2, INK)

# ============================================================================
# Panel 2: the sharded table
# ============================================================================
y0 = y0 + P1_H + 20
cells_y = y0 + 96
CW, CH, GAP = 118, 46, 7
P2_H = 96 + CH + 30 + 84
d.panel(y0, P2_H, 2, "Where are the rows stored?",
        "All sub-tables of one layer form one table: 4062 rows, padded to 4096, 512 rows per enp rank.")
d.text(46, y0 + 80, "global row = sub-table offset + hash:   0 + 225 = 225    1009 + 225 = 1234    2022 + 208 = 2230    3041 + 208 = 3249",
       12, INK, mono=True)
hits = {0: "225", 2: "1234", 4: "2230", 6: "3249"}
for r in range(8):
    x = 46 + r * (CW + GAP)
    hit = r in hits
    d.rect(x, cells_y, CW, CH, fill=EMERALD[1] if hit else WHITE, stroke=EMERALD if hit else "#d1d5db", sw=2 if hit else 1.2, rx=6)
    d.text(x + CW / 2, cells_y + 19, f"rank {r}", 12.5, EMERALD[0] if hit else MUTE, "bold", "middle")
    d.text(x + CW / 2, cells_y + 37, f"rows {r * 512}-{r * 512 + 511}", 11.5, INK, anchor="middle", mono=True)
    if hit:
        d.text(x + CW / 2, cells_y + CH + 18, "row " + hits[r], 12, EMERALD[0], "bold", "middle", mono=True)
d.text(46, cells_y + CH + 46, "EngramRuntime.fetch(hashes) gets the 4 rows of every token from their ranks. Each row is [head_dim]; the 4 rows",
       12.5, INK)
d.text(46, cells_y + CH + 64, "go into fused_kv_projection. Storage: on NVIDIA, host (CPU) memory by default, device memory with",
       12.5, INK)
d.text(46, cells_y + CH + 82, "DEEPINFER_ENGRAM_FORCE_GPU_STORAGE. On Ascend, that variable is always on, so the shards are in device memory.",
       12.5, INK)

# ============================================================================
# Panel 3: where in the layer
# ============================================================================
y0 = y0 + P2_H + 20
sy = y0 + 72
SH = 96
P3_H = 72 + SH + 24
d.panel(y0, P3_H, 3, "Where does Engram change the hidden states?",
        "Only in layers listed in engram_layer_ids: on the mHC trunk, before the attention norm.")
d.rect(XS[0], sy, BW, SH, fill=WHITE, stroke=INK, sw=1.3)
d.text(XS[0] + 14, sy + 24, "mHC post of the previous", 14, INK, "bold")
d.text(XS[0] + 14, sy + 44, "sub-layer", 14, INK, "bold")
d.text(XS[0] + 14, sy + 70, "trunk [T, hc_mult, hidden]", 12.5, INK, mono=True)
d.rect(XS[1], sy, BW, SH, fill=AMBER[1], stroke=AMBER, sw=2)
d.text(XS[1] + 14, sy + 24, "Engram.forward", 14, AMBER[0], "bold")
d.text(XS[1] + 14, sy + 46, "kv = proj(embed_hook())", 12.5, INK, mono=True)
d.text(XS[1] + 14, sy + 64, "   [T, hc_mult + 1, hidden]", 12.5, INK, mono=True)
d.text(XS[1] + 14, sy + 84, "trunk = engram_gate_fwd(...)", 12.5, INK, mono=True)
d.rect(XS[2], sy, BW, SH, fill=WHITE, stroke=INK, sw=1.3)
d.text(XS[2] + 14, sy + 24, "mHC pre + attention norm", 14, INK, "bold")
d.text(XS[2] + 14, sy + 46, "then V4Attention, MoE", 12.5, INK, mono=True)
d.text(XS[2] + 14, sy + 70, "no mega_mhc fusion here", 12.5, MUTE, mono=True)
d.arrow(XS[0] + BW, sy + SH / 2, XS[1] - 2, sy + SH / 2, INK)
d.arrow(XS[1] + BW, sy + SH / 2, XS[2] - 2, sy + SH / 2, AMBER)

y = y0 + P3_H + 22
d.legend(30, y, [(BLUE, "token ids"), (VIOLET, "n-gram rows"), (PINK, "hashes"), (EMERALD, "table shards"), (AMBER, "Engram in the layer")])
y += 38
y = d.footnotes(30, y, [
    "Illustrative: the toy hash is (17·3 XOR 42·5 [XOR 7·7]) mod prime. The code passes per-layer odd 64-bit multipliers, prime",
    "  sizes and offsets to the kernel (engram_metadata.py:98-116); the formula and the offsets kernel are not in this repo.",
    "An image token stops the n-gram: it and all older columns become the pad id (prepare_tensor_input_base.cpp:29-32).",
])
d.save(height=y + 10)
