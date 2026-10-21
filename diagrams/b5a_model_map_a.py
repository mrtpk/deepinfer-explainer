"""Diagram: the whole DeepSeek-V4.1-Flash model as DeepInfer runs it (one forward).

Used by: src/concepts/model-map.html ("The picture"), src/code/deepseek.html ("Where it sits")
Sources (commit 9bd9cf2):
  deepinfer/model_executor/models/deepseek_vl.py:194-234   VL prefill: embeddings + vision features
  deepinfer/model_executor/models/deepseek.py:140-148       embed_tokens = VocabParallelEmbedding
  deepinfer/model_executor/models/deepseek.py:161-162       embedding when no hidden states are passed
  deepinfer/model_executor/models/deepseek.py:177-188       Engram hashes once per forward
  deepinfer/model_executor/models/deepseek.py:190-218       loop over DeepseekDecoderLayer, CrossLayerRuntime
  deepinfer/model_executor/models/deepseek.py:220-223       DFlash main cache after the layers
  deepinfer/model_executor/models/deepseek.py:225-239       final mHC mix, output_norm
  deepinfer/model_executor/models/deepseek.py:383-400       sample(): lm_head weight goes to the sampler
  deepinfer/model_executor/models/v4_modules/builder.py:105-125   module order: emb, blocks, head, DFlash heads
  deepinfer/hugging_face/config.py:146-161                  compress_ratios -> layer kinds, n_prefill_layer
  deepinfer/model_executor/models/v4_modules/yoco.py:19-21  consumer layers [n_prefill_layer, n_layer)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, MUTE, NEUTRAL, PINK, VIOLET, WHITE, Diagram  # noqa: E402

d = Diagram(width=1100)
d.header(
    "DeepSeek-V4.1-Flash in DeepInfer: the whole model",
    "One forward = one engine step  ·  the forward returns hidden states, not logits  ·  commit 9bd9cf2",
    params="T = tokens in the step   hidden = hidden_size   hc = hc_mult   N = num_hidden_layers  (sizes: config.json)",
)

TS, MS = 14, 12.5


def card(x, y, w, h, title, lines, col, sub=None, tag=None):
    d.rect(x, y, w, h, fill=col[1], stroke=col, sw=1.5)
    d.text(x + 14, y + 24, title, TS, col[0] if col is not NEUTRAL else MUTE, "bold")
    if tag:
        tw = len(tag) * 11 * 0.602 + 20
        d.pill(x + w - tw - 10, y + 9, tw, tag, col if col is not NEUTRAL else MUTE)
    yy = y + 24
    if sub:
        d.text(x + 14, y + 43, sub, 12, MUTE)
        yy = y + 43
    for i, s in enumerate(lines):
        d.text(x + 14, yy + 21 + i * 18, s, MS, INK, mono=True)


# ============================================================================
# Panel 1: one forward, top to bottom
# ============================================================================
y0 = 112
P1_H = 698
d.panel(y0, P1_H, 1, "What runs in one forward?",
        "Top to bottom: tokens, embedding, N decoder layers, final mix and norm. The sampler uses the lm head later.")

MX, MW = 46, 600          # main column
SX, SW = 676, 378         # side notes column
top = y0 + 72
gap = 30
H1, H2, H3, H4, H5 = 86, 112, 122, 104, 86
y1 = top
y2 = y1 + H1 + gap
y3 = y2 + H2 + gap
y4 = y3 + H3 + gap
y5 = y4 + H4 + gap

card(MX, y1, MW, H1, "Input of the step", [
    "input_ids              int32 [T]",
    "images (prefill only)  raw bytes, VL path",
], BLUE, tag="InputMetadataV4")
card(MX, y2, MW, H2, "Embedding", [
    "embed_tokens(input_ids) → bf16 [T, hidden]",
    "VL prefill: vision_language_tuner adds image features",
], BLUE, sub="deepseek.py:140-148, 161-162  ·  deepseek_vl.py:194-234")
card(MX, y3, MW, H3, "Decoder layers 0 … N−1", [
    "for i in range(N): layers[i](hidden, kv_caches[i], ...)",
    "between layers the trunk is [T, hc, hidden] (mHC)",
    "one CrossLayerRuntime goes through all layers",
], VIOLET, sub="DeepseekDecoderLayer  ·  deepseek.py:190-218")
card(MX, y4, MW, H4, "Final mix and norm", [
    "mHC: mix the hc paths into one → [T, hidden]",
    "output_norm (RMSNorm) → hidden states bf16 [T, hidden]",
], BLUE, sub="deepseek.py:225-239")
card(MX, y5, MW, H5, "Sampler (separate call: sample())", [
    "lm_head.weight [vocab, hidden] → fp32 logits",
    "only for the rows that it samples",
], EMERALD, tag="deepseek.py:383-400")

cx = MX + MW / 2
for ya, yb, col in ((y1 + H1, y2, BLUE), (y2 + H2, y3, BLUE), (y3 + H3, y4, VIOLET), (y4 + H4, y5, EMERALD)):
    d.arrow(cx, ya, cx, yb - 2, col, sw=2)
d.text(cx + 10, y4 + H4 + 19, "CausalLMForwardOutput.hidden_states", 12, EMERALD[0], "bold", mono=True)

# side notes: optional parts
card(SX, y2, SW, H2, "Engram (if configured)", [
    "engram_hash(ngram_token_ids)",
    "once per forward, before the loop",
    "the engram layers read the result",
], AMBER, sub="deepseek.py:177-188")
card(SX, y3, SW, H3, "DFlash draft head", [
    "target layers write one feature",
    "each into dflash_input [T, k·hidden]",
    "update_main_cache() after the loop",
], PINK, sub="deepseek.py:172-175, 220-223")
card(SX, y4, SW, H4, "Context parallelism (prefill)", [
    "gather before the loop",
    "all_gather + gather after the norm",
], NEUTRAL, sub="deepseek.py:168-170, 241-244")
d.arrow(SX, y3 + H3 / 2, MX + MW + 2, y3 + H3 / 2, PINK, dash="5 4")
d.path_arrow(f"M {SX + SW / 2:.1f},{y2 + H2:.1f} L {SX + SW / 2:.1f},{y2 + H2 + 12:.1f} L {MX + MW + 14:.1f},{y2 + H2 + 12:.1f} L {MX + MW + 14:.1f},{y3 + 24:.1f} L {MX + MW + 2:.1f},{y3 + 24:.1f}", AMBER, dash="5 4")
d.arrow(SX, y4 + H4 / 2, MX + MW + 2, y4 + H4 / 2, MUTE, dash="5 4")

# ============================================================================
# Panel 2: module order and layer kinds
# ============================================================================
y0b = y0 + P1_H + 22
P2_H = 386
d.panel(y0b, P2_H, 2, "How are the N layers arranged?",
        "The config list compress_ratios fixes the kind of each layer. The first ratio-1 layer starts the YOCO consumer side.")

sy = y0b + 74
d.text(46, sy + 4, "Module list that V41Builder makes (builder.py:105-125):", 13, INK, "bold")
by_ = sy + 20
segs = [
    ("emb", "embedding", BLUE, 1.0),
    ("0 … n_prefill_layer−1", "producer side", VIOLET, 3.0),
    ("n_prefill_layer … N−1", "YOCO consumer side", VIOLET, 3.0),
    ("head", "lm head", EMERALD, 1.0),
    ("DFlash 1 … nextn", "draft layers", PINK, 2.0),
]
x0, x1, bh = 46, 1054, 50
total = sum(s[3] for s in segs)
x = x0
for label, sub, col, w in segs:
    ww = (x1 - x0) * w / total
    d.rect(x, by_, ww - 4, bh, fill=col[1], stroke=col, rx=4, sw=1.4)
    d.text(x + 10, by_ + 20, label, 12.5, col[0], "bold", mono=True)
    d.text(x + 10, by_ + 39, sub, 12, INK)
    x += ww
d.text(46, by_ + bh + 22, "n_prefill_layer = index of the first layer with ratio 1 (hugging_face/config.py:158-161).",
       12, MUTE)
d.text(46, by_ + bh + 40, "Consumer layers: n_prefill_layer ≤ i < N (yoco.py:19-21). Their compressed KV comes from one shared hidden state.",
       12, MUTE)

ky = by_ + bh + 62
kw, kh, kg = 323, 172, 19
kinds = [
    ("ratio 0: SWA only", BLUE, [
        "sliding-window KV only",
        "no compressed KV, no indexer",
        "_win_spec(), sparse_stage=0",
        "",
        "cache: swa_cache ring",
    ]),
    ("ratio 1: C1", VIOLET, [
        "SWA KV + compressed KV",
        "1 entry per token",
        "indexer if index_topk > 0",
        "",
        "cache: swa + ca (+ ica)",
    ]),
    ("ratio 2: C2", VIOLET, [
        "SWA KV + compressed KV",
        "1 entry per 2 tokens (gated)",
        "indexer if index_topk > 0",
        "fp32 state: ca_state",
        "cache: swa + ca (+ ica)",
    ]),
]
for i, (title, col, lines) in enumerate(kinds):
    card(46 + i * (kw + kg), ky, kw, kh, title, lines, col, sub="hugging_face/config.py:99-133")

y = y0b + P2_H + 24
d.legend(30, y, [(BLUE, "input, embedding, output"), (VIOLET, "decoder layers"), (EMERALD, "sampling"),
                 (AMBER, "Engram"), (PINK, "DFlash")])
y += 40
y = d.footnotes(30, y, [
    "Not in the repo: N, hidden, hc, vocab size and the compress_ratios list. They come from the checkpoint's config.json.",
    "Simplified: one decoder layer is shown on the second diagram. Ratios other than 0, 1 and 2 raise ValueError",
    "  (model_metadata_utils.py:52-53). Cross-layer sharing can make a layer reuse the KV or the indexer of an earlier layer.",
])
d.save(height=y + 10)
