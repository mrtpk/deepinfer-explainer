"""Diagram: KV compression (C2) in DeepInfer: the math, the decode state ring, the entry formats.

Used by: src/concepts/kv-compression.html ("The picture"), src/code/v4-compress.html ("Where it sits")
Sources (commit 9bd9cf2):
  deepinfer/model_executor/models/v4_modules/mla_attn.py:63-97        A (values) and Gate (logits); C1 has no Gate
  deepinfer/model_executor/models/v4_modules/compress.py:95-120       score, latent = chunk(2); prefill / decode kernels
  deepinfer/model_executor/models/v4_modules/compress.py:131-167      norm + RoPE(positions_c) + cast + store
  deepinfer/model_executor/layers/tilelang_ops/compress.py:199,248    softmax over the 2 tokens, weighted sum of latent
  deepinfer/model_executor/layers/tilelang_ops/compress.py:227-247    decode: write ring slot (ctx-1) % 7, compress at odd positions
  csrc/engine/input_metadata/prepare_tensor_input_v4.cpp:59,82-86      entry position = j * n; decode makes an entry when (pos+1) % n == 0
  deepinfer/worker/cache_engine.py:130-133                            ring = ratio + max(0, backtracking - 1) = 7
  deepinfer/model_executor/layers/tilelang_ops/cache_common.py:109-128 528 B (FP8) and 288 B (FP4) entries
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, MUTE, PINK, VIOLET, WHITE, Diagram  # noqa: E402

d = Diagram(width=1100)
d.header(
    "KV compression: how 2 tokens become 1 cache entry (C2)",
    "One C2 layer, one sequence  ·  C1 skips the softmax and keeps one entry per token",
    params="D = 512 values per entry   ca_state fp32 [slots, 7, 2, 512]   entry: 288 B (FP4) or 528 B (FP8)",
)

TS, MS = 14, 12.5


def card(x, y, w, h, title, lines, col):
    d.rect(x, y, w, h, fill=col[1], stroke=col, sw=1.5)
    d.text(x + 12, y + 22, title, TS, col[0], "bold")
    for i, s in enumerate(lines):
        d.text(x + 12, y + 42 + i * 17, s, MS, INK, mono=True)


# ============================================================================
# Panel 1: the math
# ============================================================================
y0 = 112
P1_H = 330
d.panel(y0, P1_H, 1, "What happens to tokens 2j and 2j+1?",
        "Per value: softmax of the 2 scores, then the weighted sum of the 2 latents. Then norm, RoPE, cast, store.")

cw, ch, gap = 312, 86, 34
xs = [46, 46 + cw + gap, 46 + 2 * (cw + gap)]
r1 = y0 + 72
card(xs[0], r1, cw, ch, "1  Project (BF16 weights)", ["[Gate ‖ A] → fp32 [2, 1024]", "attn.py:345-371"], BLUE)
card(xs[1], r1, cw, ch, "2  Split", ["score  = [2, 512]  (Gate)", "latent = [2, 512]  (A)", "compress.py:96"], BLUE)
card(xs[2], r1, cw, ch, "3  Mix the 2 tokens", ["w = softmax(score, over tokens)", "e = w[0]·latent[0] + w[1]·latent[1]", "→ bf16 [512]"], VIOLET)
for i in range(2):
    d.arrow(xs[i] + cw, r1 + ch / 2, xs[i + 1] - 2, r1 + ch / 2, BLUE, sw=1.8)

r2 = r1 + ch + 42
card(xs[0], r2, cw, ch, "4  RMSNorm", ["norm weight of PackedWkv", "pre_rope_kv → indexer (KProject)"], EMERALD)
card(xs[1], r2, cw, ch, "5  RoPE on the last 64 values", ["position = 2j  (positions_c)", "prepare_tensor_input_v4.cpp:59"], EMERALD)
card(xs[2], r2, cw, ch, "6  Cast and store", ["FP4: 256 B + 32 scales = 288 B", "→ ca_cache[slot_mapping_store_ca]", "compress.py:148-166"], EMERALD)
for i in range(2):
    d.arrow(xs[i] + cw, r2 + ch / 2, xs[i + 1] - 2, r2 + ch / 2, EMERALD, sw=1.8)
# connector from card 3 down-left to card 4 (orthogonal, below the cards)
mid_y = r1 + ch + 21
d.path_arrow(f"M {xs[2] + cw / 2:.1f},{r1 + ch:.1f} L {xs[2] + cw / 2:.1f},{mid_y:.1f} "
             f"L {xs[0] + cw / 2:.1f},{mid_y:.1f} L {xs[0] + cw / 2:.1f},{r2 - 2:.1f}", VIOLET, sw=1.8)
d.text(46, r2 + ch + 26, "Steps 4-6 are one fused kernel (fused_norm_rope_hadamard_cast_store_kvcache). C1: step 1 has no Gate (bf16 [1, 512]) and step 3 is skipped.",
       12, MUTE)

# ============================================================================
# Panel 2: the decode state ring
# ============================================================================
y1 = y0 + P1_H + 20
P2_H = 222
d.panel(y1, P2_H, 2, "Decode: where does the first token of a pair wait?",
        "In ca_state, a ring of 7 slots per sequence. Each token writes slot position % 7 (example: positions 999..1005).")

ring = {5: 999, 6: 1000, 0: 1001, 1: 1002, 2: 1003, 3: 1004, 4: 1005}
CW, CH, CG = 108, 54, 10
rx0 = 46
ry = y1 + 82
for s in range(7):
    x = rx0 + s * (CW + CG)
    pos = ring[s]
    col = AMBER if pos == 999 else PINK
    d.rect(x, ry, CW, CH, fill=col[1], stroke=col, rx=4, sw=1.4)
    d.text(x + CW / 2, ry + 21, f"slot {s}", 12, MUTE, "bold", "middle", mono=True)
    d.text(x + CW / 2, ry + 41, f"pos {pos}", 13, col[0], "bold", "middle", mono=True)
d.text(rx0 + 7 * (CW + CG) + 4, ry + 21, "each slot:", 12, MUTE)
d.text(rx0 + 7 * (CW + CG) + 4, ry + 39, "score[512]", 12, INK, mono=True)
d.text(rx0 + 7 * (CW + CG) + 4, ry + 55, "latent[512]", 12, INK, mono=True)

ey = ry + CH + 30
d.text(46, ey, "This step (positions 1000..1005) makes 3 entries, at the odd positions: (1000, 1001) → entry 500,", 12.5, INK)
d.text(46, ey + 19, "(1002, 1003) → entry 501, (1004, 1005) → entry 502. Position 999 is older; it paired with 998 in an earlier step.", 12.5, INK)
d.text(46, ey + 38, "Why 7 slots: the kernel asserts ring ≥ ratio + tokens per step − 1 = 2 + 6 − 1 = 7  (tilelang_ops/compress.py:98).", 12.5, MUTE)

# ============================================================================
# Panel 3: entry formats
# ============================================================================
y2 = y1 + P2_H + 20
P3_H = 196
d.panel(y2, P3_H, 3, "What does one entry cost?",
        "512 values plus scales, interleaved per token. FP4 is the HF loader default (use_fp4_sparse_kv = True).")

BX = 210
SC = 1.4
fy = y2 + 78
d.text(46, fy + 18, "FP4 (default)", 13, INK, "bold")
d.rect(BX, fy, 256 * SC, 26, fill=EMERALD[1], stroke=EMERALD, rx=3, sw=1.3)
d.text(BX + 128 * SC, fy + 18, "512 × e2m1 = 256 B", 12.5, EMERALD[0], "bold", "middle", mono=True)
d.rect(BX + 256 * SC + 4, fy, 32 * SC * 3, 26, fill=AMBER[1], stroke=AMBER, rx=3, sw=1.3)
d.text(BX + 256 * SC + 4 + 48 * SC, fy + 18, "32 × e4m3", 12, AMBER[0], "bold", "middle", mono=True)
d.text(BX + 256 * SC + 4 + 96 * SC + 14, fy + 18, "= 288 B  (1 scale per 16 values)", 12.5, INK, mono=True)

f2 = fy + 52
d.text(46, f2 + 18, "FP8 (MXFP8)", 13, INK, "bold")
d.rect(BX, f2, 430, 26, fill=BLUE[1], stroke=BLUE, rx=3, sw=1.3)
d.text(BX + 215, f2 + 18, "512 × e4m3 = 512 B", 12.5, BLUE[0], "bold", "middle", mono=True)
d.rect(BX + 434, f2, 100, 26, fill=AMBER[1], stroke=AMBER, rx=3, sw=1.3)
d.text(BX + 434 + 50, f2 + 18, "16 × ue8m0", 12, AMBER[0], "bold", "middle", mono=True)
d.text(BX + 434 + 100 + 14, f2 + 18, "= 528 B  (1 scale per 32 values)", 12.5, INK, mono=True)
d.text(46, f2 + 56, "Bars are not to scale. One block row per layer holds 128 // ratio entries: C1 = 128, C2 = 64 (cache_engine.py:452-453).", 12, MUTE)

y = y2 + P3_H + 22
d.legend(30, y, [(BLUE, "projection / FP8"), (VIOLET, "the mix"), (EMERALD, "norm, RoPE, FP4 store"),
                 (PINK, "tokens of this step"), (AMBER, "older token / scales")])
y += 34
y = d.footnotes(30, y, [
    "Simplified: one sequence, no context parallelism. The ring holds 7 slots only with the defaults (DEEPINFER_USE_NEXTN_DECODE = 5).",
    "  Prefill uses another kernel: it reads the first token of a pair from the ring when that token came in an earlier step.",
])
d.save(height=y + 10)
