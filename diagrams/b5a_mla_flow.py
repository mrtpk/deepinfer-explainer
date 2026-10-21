"""Diagram: MLA in DeepInfer, one attention layer (V4Attention), with shapes.

Used by: src/concepts/mla-attention.html ("The picture"), src/code/v4-attn.html
Example layer: a sparse C2 layer with SWA, a KV source, not a YOCO consumer.
Sources (commit 9bd9cf2):
  deepinfer/model_executor/models/v4_modules/attn.py:278-306   merged q_a_kv_swa_proj and q_b_proj
  deepinfer/model_executor/models/v4_modules/attn.py:386-400   split q_a | kv_swa
  deepinfer/model_executor/models/v4_modules/attn.py:402-451   SWA KV: norm + RoPE + FP8 cast (+ store in decode)
  deepinfer/model_executor/models/v4_modules/attn.py:453-463   q_b, RoPE on the last R values
  deepinfer/model_executor/models/v4_modules/compress.py:82-167 Compressor: C1 / C2, store into ca_cache
  deepinfer/model_executor/models/v4_modules/attn.py:589-670   prefill / decode kernel calls
  deepinfer/model_executor/models/v4_modules/attn.py:812-857   prefill KV buffer [swa cache | current swa | compressed]
  deepinfer/model_executor/models/v4_modules/attn.py:191-225   inverse RoPE, grouped Wv einsum, out_proj
  deepinfer/model_executor/layers/attention_backend.py:26-146  kernel wrappers and argument shapes
  deepinfer/hugging_face/config.py:287-293                     head_dim, kv_lora_rank = head_dim - qk_rope_head_dim
  deepinfer/worker/cache_engine.py:46-56                       kv_lora_rank + rope == 512 (cache format)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, MUTE, NEUTRAL, PINK, VIOLET, WHITE, Diagram  # noqa: E402

d = Diagram(width=1100)
d.header(
    "MLA in DeepInfer: one attention layer",
    "V4Attention.forward (attn.py:752-880)  ·  example: sparse C2 layer with SWA  ·  commit 9bd9cf2",
    params="T tokens  H heads  D = head_dim = 512  R = qk_rope_head_dim  rq = q_lora_rank  G = o_groups  ro = o_lora_rank",
)

TS, MS = 14, 12.5


def card(x, y, w, h, title, lines, col, sub=None):
    d.rect(x, y, w, h, fill=col[1], stroke=col, sw=1.5)
    d.text(x + 12, y + 23, title, TS, col[0] if col is not NEUTRAL else MUTE, "bold")
    yy = y + 23
    if sub:
        d.text(x + 12, y + 41, sub, 12, MUTE)
        yy = y + 41
    for i, s in enumerate(lines):
        d.text(x + 12, yy + 20 + i * 18, s, MS, INK, mono=True)


def row(y, h, items, col, gap=40, xs0=46, widths=(300, 330, 298)):
    x = xs0
    pos = []
    for (title, lines, sub, c), w in zip(items, widths):
        card(x, y, w, h, title, lines, c or col, sub=sub)
        pos.append((x, w))
        x += w + gap
    for (xa, wa), (xb, _) in zip(pos, pos[1:]):
        d.arrow(xa + wa, y + h / 2, xb - 2, y + h / 2, col, sw=1.8)


# ============================================================================
# Panel 1: projections
# ============================================================================
y0 = 112
P1_H = 556
d.panel(y0, P1_H, 1, "How does one layer make Q, K and V?",
        "Low-rank projections. K and V are the same 512-value latent vector, one per token: one KV head.")

ty = y0 + 70
d.rect(46, ty, 1008, 54, fill=WHITE, stroke=INK, sw=1.2)
d.text(60, ty + 22, "hidden (FP8 + scales)  [T, hidden]   →   q_a_kv_swa_proj = [Wq.A ‖ Wkv.A]   →   [T, rq + D]",
       12.5, INK, "bold", mono=True)
d.text(60, ty + 42, "split → q_a [T, rq]  and  kv_swa [T, D]       attn.py:281-288, 399", 12, MUTE, mono=True)

rh = 104
r1 = ty + 54 + 36
d.text(46, r1 - 10, "Query", 12.5, BLUE[0], "bold", mono=True)
row(r1, rh, [
    ("q_a", ["[T, rq]  (LoRA rank)"], "first half of the split", None),
    ("q_a_norm → q_b_proj", ["RMSNorm over rq", "Wq.B ‖ index q_B (merged)"], ":458", None),
    ("q", ["bf16 [T, H, D]", "RoPE on the last R values"], ":462-463, 158-172", None),
], BLUE)

r2 = r1 + rh + 36
d.text(46, r2 - 10, "Sliding-window KV", 12.5, VIOLET[0], "bold", mono=True)
row(r2, rh, [
    ("kv_swa", ["[T, D]  = [T, 512]", "one KV head"], "second half of the split", None),
    ("norm + RoPE + FP8 cast", ["one fused kernel", "fused_norm_rope_..._kvcache"], ":433-445", None),
    ("swa_cache (ring)", ["528 B per token", "decode: stored here at once"], ":429-432", None),
], VIOLET)

r3 = r2 + rh + 36
d.text(46, r3 - 10, "Compressed KV", 12.5, EMERALD[0], "bold", mono=True)
row(r3, rh, [
    ("current_hidden_proj", ["hidden bf16 → fp32 [T, 2·D]", "[Gate ‖ A] + index weights"], ":329-373", None),
    ("Compressor", ["C2: 2 tokens → 1 entry", "norm + RoPE + cast + store"], "compress.py:131-167", None),
    ("ca_cache (paged)", ["288 B (FP4) or 528 B", "per entry", "pre-RoPE copy → indexer"], None, None),
], EMERALD)

# ============================================================================
# Panel 2: kernels
# ============================================================================
y0b = y0 + P1_H + 22
P2_H = 368
d.panel(y0b, P2_H, 2, "What does the attention kernel read?",
        "Prefill reads one BF16 buffer. Decode reads the FP8 / FP4 caches directly. Both get index lists, not whole sequences.")

kw, kh = 489, 154
ky = y0b + 70
card(46, ky, kw, kh, "Prefill: prefill_attn_varlen_sparse", [
    "q             bf16  [T, H, D]",
    "kv            bf16  [total_kv, 1, D]",
    "index         int32 [T, window + topk]",
    "attn_sink     fp32  [H]",
    "→ FlashMLA flash_mla_sparse_fwd",
], AMBER, sub="attn.py:617-625  ·  attention_backend.py:26-74")
card(46 + kw + 30, ky, kw, kh, "Decode: decode_mla_mqa_sparse", [
    "q             bf16  [T, H, D]",
    "swa_cache  + kv_swa_index [T, window]",
    "ca_cache   + kv_ca_index  [T, topk]",
    "sched_meta, attn_sink, head_dim_v=D",
    "→ FlashMLA flash_mla_with_kvcache",
], PINK, sub="attn.py:660-669  ·  attention_backend.py:77-146")

sy = ky + kh + 46
d.text(46, sy - 12, "The prefill buffer kv (attn.py:813-857), one row = one key = one 512-value vector:", 12.5, INK, "bold")
segs = [("SWA history", "from swa_cache", VIOLET, 2.0), ("current SWA KV", "this step", VIOLET, 3.0),
        ("compressed KV", "from ca_cache", EMERALD, 3.2)]
x0, x1, bh = 46, 1054, 50
total = sum(s[3] for s in segs)
x = x0
for label, sub, col, w in segs:
    ww = (x1 - x0) * w / total
    d.rect(x, sy, ww - 4, bh, fill=col[1], stroke=col, rx=4, sw=1.4)
    d.text(x + 10, sy + 20, label, 12.5, col[0], "bold")
    d.text(x + 10, sy + 39, sub, 12, INK, mono=True)
    x += ww
d.text(46, sy + bh + 22, "total_kv = total_k_swa_cached + total_k_swa_cur + total_k_compressed[ratio]   (attn.py:814-817)",
       12, MUTE, mono=True)

# ============================================================================
# Panel 3: output projection
# ============================================================================
y0c = y0b + P2_H + 22
P3_H = 206
d.panel(y0c, P3_H, 3, "How does the output go back to hidden size?",
        "Undo the RoPE on the output, then a grouped low-rank projection (Wv) and out_proj.")
oy = y0c + 70
row(oy, 112, [
    ("context", ["[T, H, D]", "inverse RoPE on", "the last R values"], ":193", INK and NEUTRAL),
    ("Wv: fp8_einsum", ["\"bhr,hdr->bhd\"", "[T, G, H/G·D] → [T, G, ro]"], ":215-221", NEUTRAL),
    ("out_proj", ["[T, G·ro] → [T, hidden]", "back to the layer"], ":152-156, 225", NEUTRAL),
], INK, widths=(300, 330, 298))

y = y0c + P3_H + 24
d.legend(30, y, [(BLUE, "query"), (VIOLET, "SWA KV"), (EMERALD, "compressed KV"), (AMBER, "prefill"),
                 (PINK, "decode")])
y += 40
y = d.footnotes(30, y, [
    "Not in the repo: H, R, rq, G, ro and the window. D = 512 is fixed by the cache format (cache_engine.py:46-56).",
    "Simplified: on NVIDIA with 64 or 128 heads, a fused FlashMLA kernel also does the q norm, both RoPE steps and the FP8",
    "  cast of the output (attn.py:87-92). The indexer, YOCO and cross-layer sharing are on their own pages.",
])
d.save(height=y + 10)
