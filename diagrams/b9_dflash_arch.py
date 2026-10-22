"""Diagram: the DFlash draft model - main-cache update and one draft pass.

Used by: src/concepts/dspark.html ("The picture"), src/code/dflash.html ("Where it sits")
Sources (commit 9bd9cf2):
  deepinfer/model_executor/models/decoder_layer.py:92-95, 143-145  target layers store the mean of the mHC trunk streams (after attn mHC pre + norm, before attention)
  deepinfer/model_executor/models/deepseek.py:172-174, 219-223      dflash_input buffer; update_main_cache after the last layer
  deepinfer/model_executor/models/mtp/dflash.py:198-228             projection -> norm -> main_kv_proj -> SWA cache write
  deepinfer/model_executor/models/mtp/dflash.py:230-269             draft block [golden, noise x4], DFlash layers
  deepinfer/model_executor/models/mtp/dflash.py:279-345             per-step logits + Markov, confidence head, sample (tag mtp), pool store
  deepinfer/model_executor/layers/tilelang_ops/get_kv_index.py:151-206  draft positions accepted_pos+1.., keys = window + block
  deepinfer/model_executor/layers/tilelang_ops/dflash.py:10-28      confidence = sigmoid(cat(h, markov_emb) @ w / T)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, MUTE, PINK, TEAL, VIOLET, Diagram  # noqa: E402

d = Diagram(width=1100)
_box = d.box
d.box = lambda *a, **k: _box(*a, mono_size=12, **k)
W = d.W

d.header(
    "DFlash: the draft model of DSpark",
    "Part 1 runs inside the main forward pass  ·  part 2 runs inside the sampler, once per decode step  ·  nextn = 5",
    params="dflash_input [total_q, hidden × n_target]  ·  draft block [req, 5]  ·  drafts int32 [req, 5]  ·  confidence fp32 [req, 5]",
)

# ---------------------------------------------------------------- panel 1
y0 = 112
P1 = 220
d.panel(y0, P1, 1, "Where do the draft keys come from? From the target model's own layers",
        "Some main layers store the mean of their mHC trunk streams. DFlash turns these features into one key per DFlash layer and token.")
by = y0 + 72
bw, bh = 300, 112
xs = [46, 400, 754]
d.box(xs[0], by, bw, bh, "Target layers (main model)", [
    "layers in dspark_target_layer_ids", "before attention: mean of the", "mHC trunk streams → one slice",
    "decoder_layer.py:143-145"], col=BLUE)
d.box(xs[1], by, bw, bh, "update_main_cache", [
    "projection → RMSNorm", "main_kv_proj → main_k", "[total_q, n_layers, head_dim]", "dflash.py:219-220"], col=VIOLET)
d.box(xs[2], by, bw, bh, "DFlash SWA cache", [
    "one cache per DFlash layer", "slot = state_id·134 + pos % 134", "keys for every input token,", "also rejected drafts"], col=TEAL)
d.arrow(xs[0] + bw, by + bh / 2, xs[1] - 2, by + bh / 2, BLUE)
d.arrow_label((xs[0] + bw + xs[1]) / 2, by + bh / 2, "features", BLUE)
d.arrow(xs[1] + bw, by + bh / 2, xs[2] - 2, by + bh / 2, VIOLET)
d.arrow_label((xs[1] + bw + xs[2]) / 2, by + bh / 2, "keys", VIOLET)

# ---------------------------------------------------------------- panel 2
y1 = y0 + P1 + 20
P2 = 444
d.panel(y1, P2, 2, "How does DFlash make 5 drafts? One pass over a block of 5 positions",
        "The block starts with the token that the sampler just made. The other 4 inputs are a fixed noise token.")
by = y1 + 72
bh2 = 128
d.box(xs[0], by, bw, bh2, "Draft block input", [
    "row 0: golden token g", "rows 1-4: dspark_noise_token_id", "positions a+1 … a+5", "a = last accepted position", "dflash.py:230-239"],
      col=PINK)
d.box(xs[1], by, bw, bh2, "DFlash decoder layers", [
    "attention: same keys for all", "5 rows: 128 main keys + the", "5 draft keys (dflash_kv_index)",
    "then MLP / MoE", "dflash.py:241-269"], col=VIOLET)
d.box(xs[2], by, bw, bh2, "Heads, for step i = 0 … 4", [
    "logits_i = lm_head(norm(h_i))", "  + markov_w2(markov_w1(prev))", "c_(i+1) = sigmoid([h_i, w1]·w / T)",
    "d_(i+1) = sample(logits_i), tag mtp", "dflash.py:308-334"], col=EMERALD)
d.arrow(xs[0] + bw, by + bh2 / 2, xs[1] - 2, by + bh2 / 2, PINK)
d.arrow(xs[1] + bw, by + bh2 / 2, xs[2] - 2, by + bh2 / 2, VIOLET)

# chain of drafts with the Markov dependency
cy = by + bh2 + 50
d.text(46, cy - 14, "The Markov term links each draft to the draft before it (prev = g for step 0):", 13, INK, "bold")
cw, cg = 134, 33
chain = ["g", "d1", "d2", "d3", "d4", "d5"]
for i, s in enumerate(chain):
    x = 46 + i * (cw + cg)
    col = PINK if i == 0 else EMERALD
    d.rect(x, cy, cw, 36, fill=col[1], stroke=col[0], rx=6, sw=1.4)
    d.text(x + cw / 2, cy + 23, s if i == 0 else f"{s}  (c{i})", 13, col[0], "bold", "middle", mono=True)
    if i > 0:
        d.arrow(x - cg, cy + 18, x - 2, cy + 18, EMERALD)
d.aside(46, cy + 60, [
    "All 5 rows come from one pass of the layers. Only the small Markov term is sequential: step i adds logits that",
    "depend on the token sampled at step i-1. The confidence c_i also reads markov_w1(prev).",
])

oy = cy + 104
d.text(46, oy, "Stored in the MTP info pool slot of the request:", 13, INK, "bold")
d.text(46, oy + 22, "token_ids int32 [req, 5]   logprobs fp32 [req, 5, V or force_topk]   confidence fp32 [req, 5]",
       12.5, INK, mono=True)
d.text(46, oy + 42, "The next decode step reads them to verify the drafts (dflash.py:339-344).", 12.5, MUTE)

y = y1 + P2 + 24
d.legend(30, y, [(BLUE, "main model"), (VIOLET, "DFlash weights"), (TEAL, "DFlash cache"), (PINK, "draft input"),
                 (EMERALD, "draft output")])
y += 36
y = d.footnotes(30, y, [
    "134 = 128-token window + 6 tokens of backtracking, with default settings (cache_engine.py:88-110). The number of DFlash layers is",
    "  num_nextn_predict_layers from the checkpoint config; it does not depend on DEEPINFER_USE_NEXTN_DECODE (dflash.py:99-110).",
    "Not shown: hyper-connection (HC) streams, CUDA graph replay, context-parallel broadcast of golden tokens.",
])
d.save(height=y + 10)
