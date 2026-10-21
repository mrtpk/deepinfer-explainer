"""Diagram: the transformer skeleton, one decoder layer, and what DeepSeek V4.1 changes.

Used by: src/learn/transformer.html (section "The picture")
Sources (commit 9bd9cf2):
  deepinfer/model_executor/models/deepseek.py:140-148   embedding: VocabParallelEmbedding(vocab_size, hidden_size)
  deepinfer/model_executor/models/deepseek.py:190-218   loop over the decoder layers
  deepinfer/model_executor/models/deepseek.py:239       final norm (output_norm)
  deepinfer/model_executor/models/deepseek.py:290-294   ParallelLMHead(vocab_size, hidden_size)
  deepinfer/model_executor/layers/sampler_utils.py:20-28 logits [rows, vocab] in float32, computed in the sampler
  deepinfer/model_executor/models/decoder_layer.py:143-173  norm -> attention -> norm -> MLP (MoE)
  deepinfer/model_executor/models/v4_modules/hc.py:1-4, 58 mHC: hc_mult residual paths
  deepinfer/worker/cache_engine.py:624                  num_key_value_heads == 1
  deepinfer/model_executor/layers/tilelang_ops/cache_common.py:109-111  KV entry of 512 elements
  deepinfer/model_executor/models/v4_modules/moe.py:1-8   routed experts, gate, shared expert
Shapes use T = tokens in the step, d = hidden size, V = vocabulary size (values come from the checkpoint config).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, MUTE, PINK, VIOLET, WHITE, Diagram  # noqa: E402

W = 1100
d = Diagram(width=W)
d.header("Inside a transformer: from token ids to logits",
         "Decoder-only model  ·  T = tokens in the step, d = hidden size, V = vocabulary size  ·  pre-norm layers")

# ---- panel 1: the skeleton -------------------------------------------------------------
y0 = 92
P1 = 214
d.panel(y0, P1, 1, "What does the model do with the ids?",
        "Embedding, then N decoder layers, then a final norm and the LM head. The shape stays [T, d] between layers.")
bw, bh = 300, 112
xs = [46, 400, 754]
by = y0 + 76
d.box(xs[0], by, bw, bh, "Embedding", [], col=BLUE, tsize=14)
for i, s in enumerate(["look up one row per id", "ids int [T]", "→ hidden [T, d]"]):
    d.text(xs[0] + bw / 2, by + 46 + i * 21, s, 13 if i else 12.5, INK if i else MUTE, anchor="middle", mono=bool(i))
d.box(xs[1], by, bw, bh, "N × decoder layer", [], col=VIOLET, tsize=14)
for i, s in enumerate(["attention + feed-forward", "[T, d] → [T, d]", "same shape, new content"]):
    d.text(xs[1] + bw / 2, by + 46 + i * 21, s, 13 if i == 1 else 12.5, INK if i == 1 else MUTE, anchor="middle",
           mono=(i == 1))
d.box(xs[2], by, bw, bh, "Final norm + LM head", [], col=EMERALD, tsize=14)
for i, s in enumerate(["one score per vocab token", "[T, d] × [d, V]", "→ logits [T, V]"]):
    d.text(xs[2] + bw / 2, by + 46 + i * 21, s, 13 if i else 12.5, INK if i else MUTE, anchor="middle", mono=bool(i))
for i in range(2):
    d.arrow(xs[i] + bw, by + bh / 2, xs[i + 1] - 2, by + bh / 2, INK)
d.arrow_label((xs[0] + bw + xs[1]) / 2, by + bh / 2, "[T, d]", INK)
d.arrow_label((xs[1] + bw + xs[2]) / 2, by + bh / 2, "[T, d]", INK)

# ---- panel 2: one decoder layer ------------------------------------------------------
y1 = y0 + P1 + 20
P2 = 202
d.panel(y1, P2, 2, "What is inside one decoder layer?",
        "Two blocks. Each block normalizes its input, does its work, and adds the result back to the residual stream.")
ry = y1 + 156            # residual line y
d.text(46, ry + 5, "x", 15, INK, "bold", mono=True)
# residual main line with two adds
add1, add2 = 548, 1000
d.line(64, ry, add1 - 14, ry, INK, sw=1.8)
d.arrow(add1 + 14, ry, add2 - 16, ry, INK, sw=1.8)
d.arrow(add2 + 14, ry, 1052, ry, INK, sw=1.8)
for ax in (add1, add2):
    d.circle(ax, ry, 13, WHITE, stroke=INK, sw=1.6)
    d.text(ax, ry + 6.5, "+", 19, INK, "bold", "middle")
d.text(1046, ry - 12, "out", 12.5, MUTE, anchor="end", mono=True)
# block 1: norm + attention, above the line
b1x, b1w = 110, 380
b2x, b2w = 590, 380
bt = y1 + 70
bh2 = 54
d.rect(b1x, bt, b1w, bh2, fill=AMBER[1], stroke=AMBER, rx=8, sw=1.5)
d.text(b1x + 16, bt + 22, "RMSNorm  →  Attention", 14, AMBER[0], "bold")
d.text(b1x + 16, bt + 42, "tokens look at earlier tokens", 12.5, MUTE)
d.rect(b2x, bt, b2w, bh2, fill=PINK[1], stroke=PINK, rx=8, sw=1.5)
d.text(b2x + 16, bt + 22, "RMSNorm  →  Feed-forward (MLP)", 14, PINK[0], "bold")
d.text(b2x + 16, bt + 42, "each token alone: [d] → [d]", 12.5, MUTE)
# branch arrows: up from residual into block, down from block into add
d.circle(90, ry, 4, INK)
d.path_arrow(f"M 90,{ry} L 90,{bt + bh2 / 2} L {b1x - 2},{bt + bh2 / 2}", AMBER)
d.path_arrow(f"M {b1x + b1w},{bt + bh2 / 2} L {add1},{bt + bh2 / 2} L {add1},{ry - 15}", AMBER)
d.circle(570, ry, 4, INK)
d.path_arrow(f"M 570,{ry} L 570,{bt + bh2 / 2} L {b2x - 2},{bt + bh2 / 2}", PINK)
d.path_arrow(f"M {b2x + b2w},{bt + bh2 / 2} L {add2},{bt + bh2 / 2} L {add2},{ry - 15}", PINK)
d.text(300, ry + 28, "residual stream: x passes straight through, the blocks only add to it", 12.5, MUTE, anchor="middle",
       italic=True)

# ---- panel 3: DeepSeek V4.1 -----------------------------------------------------------
y2 = y1 + P2 + 20
P3 = 196
d.panel(y2, P3, 3, "What does DeepSeek V4.1 change in DeepInfer?",
        "The same skeleton, with three changes. Each one has its own concept page.")
items = [
    ("MLA attention", ["one shared KV head", "512 numbers per entry", "compressed KV cache"], AMBER),
    ("MoE feed-forward", ["a gate picks a few", "routed experts per token,", "plus a shared expert"], PINK),
    ("mHC residual", ["the residual stream has", "hc_mult paths", "[T, hc_mult, d]"], VIOLET),
]
for i, (t, lines, col) in enumerate(items):
    bx = 46 + i * 354
    d.box(bx, y2 + 70, 300, 100, t, [], col=col, tsize=14)
    for j, s in enumerate(lines):
        d.text(bx + 150, y2 + 114 + j * 20, s, 12.5, INK, anchor="middle", mono=(j == 2 and i == 2))

y = y2 + P3 + 22
d.legend(30, y, [(BLUE, "embedding"), (VIOLET, "layers / mHC"), (AMBER, "attention"), (PINK, "feed-forward / MoE"),
                 (EMERALD, "output head")])
y += 36
y = d.footnotes(30, y, [
    "In DeepInfer, the model forward returns hidden states. The sampler computes the logits, only for the rows it samples.",
    "Panel 3 sources: cache_engine.py:624 (1 KV head), cache_common.py:109-111 (512), moe.py:1-8, hc.py:1-4 and 58.",
    "Not shown: positions (RoPE), the KV cache, sparse attention, Engram, and the split of work over devices.",
])
d.save(height=y + 8)
