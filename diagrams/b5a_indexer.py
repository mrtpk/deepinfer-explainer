"""Diagram: the sparse-attention indexer (class MQA in index_attn.py).

Used by: src/concepts/sparse-attention-indexer.html ("The picture"), src/code/v4-index-attn.html
Sources (commit 9bd9cf2):
  deepinfer/model_executor/models/v4_modules/attn.py:292-304   index q_B merged into q_b_proj
  deepinfer/model_executor/models/v4_modules/attn.py:354-364   index weights_proj merged into current_hidden_proj
  deepinfer/model_executor/models/v4_modules/attn.py:525-587   pre-RoPE KV from the Compressor feeds the indexer
  deepinfer/model_executor/models/v4_modules/index_attn.py:133-179  store index K (KProject), FP4 Q
  deepinfer/model_executor/models/v4_modules/index_attn.py:327-376  prefill: chunks, logits, topk (+ks offset)
  deepinfer/model_executor/models/v4_modules/index_attn.py:456-514  decode: paged logits, topk, convert_kv_index
  deepinfer/model_executor/layers/tilelang_ops/cache_common.py:129-137  FP4 index format: 128 values, 1 scale / 32
  deepinfer/model_executor/layers/tilelang_ops/flash_mla_utils.py:40-51  logical -> physical slot (reference)
  deepinfer/model_executor/layers/tilelang_ops/kv_index_cat.py:10-51     prefill index = [swa | topk + offset]
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, LINE, MUTE, PINK, TEAL, WHITE, Diagram  # noqa: E402

d = Diagram(width=1100)
d.header(
    "The sparse-attention indexer: which compressed keys does a query read?",
    "class MQA (index_attn.py)  ·  one sparse layer, one step  ·  commit 9bd9cf2",
    params="T tokens  Tc compressed entries  nh = index_n_heads  dh = index_head_dim  topk = index_topk  (sizes: config.json)",
)

TS, MS = 14, 12.5


def card(x, y, w, h, title, lines, col, sub=None):
    d.rect(x, y, w, h, fill=col[1], stroke=col, sw=1.5)
    d.text(x + 12, y + 23, title, TS, col[0], "bold")
    yy = y + 23
    if sub:
        d.text(x + 12, y + 41, sub, 12, MUTE)
        yy = y + 41
    for i, s in enumerate(lines):
        d.text(x + 12, yy + 20 + i * 18, s, MS, INK, mono=True)


# ============================================================================
# Panel 1: inputs
# ============================================================================
y0 = 112
P1_H = 430
d.panel(y0, P1_H, 1, "Where do the indexer's Q, K and weights come from?",
        "All three reuse work of the main attention. Q and K are cast to FP4 before the dot products.")
cw, ch, cg = 318, 86, 27
xs = [46, 46 + cw + cg, 46 + 2 * (cw + cg)]
cols = [
    ("Index Q", BLUE, [
        ("q_a (shared with main q)", ["[T, rq]"], None),
        ("q_b_proj: index part", ["[T, nh·dh]", "attn.py:458-461"], None),
        ("RoPE + FP4 cast", ["q_fp4, q_sf", "index_attn.py:164-179"], None),
    ]),
    ("Index K", EMERALD, [
        ("pre-RoPE compressed KV", ["[Tc, D] from Compressor", "attn.py:546-557"], None),
        ("KProject: k_proj", ["D → dh", "compress.py:32-53"], None),
        ("k_norm + RoPE + FP4", ["→ ica_cache (paged)", "68 B per key if dh=128"], None),
    ]),
    ("Weights", AMBER, [
        ("hidden bf16", ["[T, hidden]"], None),
        ("weights_proj", ["in current_hidden_proj", "attn.py:364"], None),
        ("weights", ["bf16 [T, nh]", "attn.py:504-506"], None),
    ]),
]
ty = y0 + 76
for x, (head, col, steps) in zip(xs, cols):
    d.text(x, ty + 4, head, 13.5, col[0], "bold")
    yy = ty + 16
    for i, (title, lines, sub) in enumerate(steps):
        card(x, yy, cw, ch, title, lines, col, sub=sub)
        if i < len(steps) - 1:
            d.arrow(x + cw / 2, yy + ch, x + cw / 2, yy + ch + 28 - 2, col, sw=1.8)
        yy += ch + 28

# ============================================================================
# Panel 2: score and top-k
# ============================================================================
y0b = y0 + P1_H + 22
P2_H = 296
d.panel(y0b, P2_H, 2, "How does it choose the keys?",
        "One score per (query, key): relu(q·k) weighted per head. DeepSelect keeps the topk best keys of each query.")
fy = y0b + 74
d.text(46, fy, "p_sum[t, j]  from relu(q[t]·k[j]) · weights[t]      bf16 [rows, max_kv_len]   (index_attn.py:3, 284-325)",
       12.5, INK, "bold", mono=True)
# worked example: one query, 12 keys, topk = 4
scores = [0.1, 2.3, 0.0, 1.7, 0.4, 3.1, 0.0, 0.9, 2.8, 0.2, 1.1, 0.5]
chosen = sorted(range(12), key=lambda i: -scores[i])[:4]
gx0, gy0, cwid, chgt = 186, fy + 40, 66, 44
d.text(46, gy0 + 18, "example query t", 12.5, MUTE)
d.text(46, gy0 + 36, "(12 valid keys)", 12, MUTE)
for j, s in enumerate(scores):
    x = gx0 + j * (cwid + 4)
    sel = j in chosen
    d.rect(x, gy0, cwid, chgt, fill=TEAL[1] if sel else WHITE, stroke=TEAL if sel else LINE, rx=4, sw=2 if sel else 1)
    d.text(x + cwid / 2, gy0 + 19, f"k{j}", 11.5, MUTE, anchor="middle", mono=True)
    d.text(x + cwid / 2, gy0 + 36, f"{s:.1f}", 12.5, TEAL[0] if sel else INK, "bold" if sel else "normal", "middle", mono=True)
d.text(46, gy0 + chgt + 30,
       "topk = 4 (example): the selected set is {1, 3, 5, 8}. Values are made up; the real topk comes from config.json.",
       12, MUTE, italic=True)
cy = gy0 + chgt + 48
d.rect(46, cy, 1008, 64, fill=WHITE, stroke=INK, sw=1.2)
d.text(60, cy + 24, "topk(p_sum, topk_tokens, sorted=False, end=lens, indices_type=int32, sorted_index=True,", 12.5, INK, mono=True)
d.text(60, cy + 44, "     idx_oob_fill_value=-1, return_value=False)  →  int32 [T, topk]   (fewer valid keys: rest is -1)", 12.5, INK, mono=True)

# ============================================================================
# Panel 3: what the index means
# ============================================================================
y0c = y0b + P2_H + 22
P3_H = 256
d.panel(y0c, P3_H, 3, "What does an index point to?",
        "Prefill: a row in the gathered BF16 buffer. Decode: a physical slot in the paged ca_cache.")
bw, bh = 489, 172
by_ = y0c + 70
card(46, by_, bw, bh, "Prefill", [
    "topk adds ks[t] (output_idx_offset)",
    "→ row in the gathered compressed keys",
    "kv_index_cat adds the SWA length:",
    "index = [swa (window) | topk + offset]",
    "→ int32 [T, window + topk]",
], PINK, sub="index_attn.py:361-372  ·  attn.py:603-610")
card(46 + bw + 30, by_, bw, bh, "Decode (example: C2 layer)", [
    "logical entry i in the sequence",
    "block = i // 64, offset = i % 64",
    "slot = block_tables[block]·64 + offset",
    "i = 130, block_tables = [7, 3, 12]",
    "→ 12·64 + 2 = 770   (-1 stays -1)",
], PINK, sub="convert_kv_index  ·  index_attn.py:508-513")

y = y0c + P3_H + 24
d.legend(30, y, [(BLUE, "index Q"), (EMERALD, "index K"), (AMBER, "weights"), (TEAL, "selected key"),
                 (PINK, "index meaning")])
y += 40
y = d.footnotes(30, y, [
    "64 = compressed entries per KV block for C2 (128 tokens / ratio 2). Kernels: DeepGEMM *_mqa_logits, DeepSelect topk.",
    "Simplified: candidate blocks (a first coarse pick that later layers reuse) and index sharing between layers are not shown.",
])
d.save(height=y + 10)
