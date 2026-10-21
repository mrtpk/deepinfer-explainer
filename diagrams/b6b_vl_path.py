"""Diagram: the VL (image) path end to end.

Used by: src/concepts/vision-encoder.html, src/code/ve.html, src/code/deepseek-vl.html
Sources (commit 9bd9cf2):
  deepinfer/entrypoints/llm.py:158-159                 dict with empty image lists for every text request
  deepinfer/engine/llm_engine.py:542-551, 618-625       overwrite_prompt, add_sequence, multi_modal_processor.add
  csrc/engine/pybind_sequence.cpp:35                    schedulable = multi_modal_data.is_none()
  deepinfer/ve/multimodal_processor.py:93-103, 164-217  forked worker process runs multi_modal_mapper, pool handles
  deepinfer/ve/multimodal_processor.py:281-305          fetch(): copy result back, set_schedulable
  deepinfer/engine/llm_engine.py:939-945                fetch() runs after schedule() in step()
  csrc/engine/scheduler.hpp:214-260, 487-493            chunk never ends inside an image
  deepinfer/ve/prepare_tensor_input_vl.py:77-138        per-chunk slicing of the image metadata
  deepinfer/model_executor/models/deepseek_vl.py:194-234   get_input_embeddings in every prefill
  deepinfer/model_executor/models/vision_encoder/vl_aligner.py:96-141   pad -> ViT -> downsample -> projector -> replace
  deepinfer/ve/processor/image_processor.py:76-92, 155-242   geometry: n_vit, n_llm, token layout
Example image 640x480 with patch 14 and downsample ratio 3 (the ratio is an example value; the comment at
prepare_tensor_input_vl.py:155 names p=14, r=3). It assumes max_image_tokens >= 206, min_pixels <= 307200 and max_wh_ratio null or >= 4/3.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, INK, MUTE, PINK, TEAL, VIOLET, Diagram  # noqa: E402

d = Diagram(width=1100)
d.header(
    "The vision path: from image bytes to embeddings in the prompt",
    "One DP rank  ·  the vision encoder runs inside the prefill forward  ·  no separate encoder machine in this release",
    params="example: one 640x480 image  ·  patch 14  ·  downsample ratio 3 (example)  ·  V = vocab_size",
)

BW = 300
XS = [46, 400, 754]


def card(x, y, w, h, title, lines, col, thick=1.5, mute_from=None):
    d.rect(x, y, w, h, fill=col[1], stroke=col, sw=thick)
    d.text(x + 14, y + 24, title, 14, col[0], "bold")
    for i, s in enumerate(lines):
        c = MUTE if (mute_from is not None and i >= mute_from) else INK
        d.text(x + 14, y + 48 + i * 18, s, 12.5, c, mono=True)


# ============================================================================
# Panel 1: admission and the worker process
# ============================================================================
y0 = 112
by = y0 + 72
BH = 150
P1_H = 72 + BH + 46
d.panel(y0, P1_H, 1, "Why does every request wait first?",
        "Each request has a multimodal dict, so it starts not schedulable until the worker process answers.")
card(XS[0], by, BW, BH, "Engine: add_request", [
    "placeholder -> V+2, V+1 x 205",
    "scheduler.add_sequence(seq)",
    "  schedulable = False",
    "mm_processor.add(id, dict)",
    "llm_engine.py:542-625",
], BLUE, mute_from=4)
card(XS[1], by, BW, BH, "Worker process (fork)", [
    "multi_modal_mapper(dict)",
    "mm_token_type, crops, pos ids",
    "decode + resize -> RGB bytes",
    "tensors -> shared pool (if on)",
    "multimodal_processor.py:197-217",
], VIOLET, mute_from=4)
card(XS[2], by, BW, BH, "Engine: step() -> fetch()", [
    "after schedule() of the step",
    "copy result into the dict",
    "scheduler.set_schedulable(id)",
    "prefill at a later step",
    "llm_engine.py:939-945",
], BLUE, mute_from=4)
d.arrow(XS[0] + BW, by + BH / 2, XS[1] - 2, by + BH / 2, VIOLET)
d.arrow_label(XS[0] + BW + 27, by + BH / 2, "queue", VIOLET)
d.arrow(XS[1] + BW, by + BH / 2, XS[2] - 2, by + BH / 2, VIOLET)
d.arrow_label(XS[1] + BW + 27, by + BH / 2, "queue", VIOLET)
d.text(46, by + BH + 28, "A text-only request also gets {\"image_bytes\": [], \"image_sizes\": []} (llm.py:158-159) and goes the same way.",
       12.5, INK)

# ============================================================================
# Panel 2: the prefill forward
# ============================================================================
y0 = y0 + P1_H + 20
r1 = y0 + 72
CH = 112
r2 = r1 + CH + 30
P2_H = 72 + CH + 30 + CH + 24
d.panel(y0, P2_H, 2, "What does a prefill with an image compute?",
        "DeepseekVLForCausalLM.get_input_embeddings, before the first decoder layer. Decode never runs it.")
card(XS[0], r1, BW, CH, "1. Scheduler + prepare", [
    "chunk never ends in an image",
    "slice image data per chunk",
    "cu_seqlens_vit, crops",
], AMBER)
card(XS[1], r1, BW, CH, "2. Embed the ids", [
    "embed_tokens(input_ids)",
    "ids >= V: zero rows (comment)",
    "[T, hidden] bf16",
], BLUE)
card(XS[2], r1, BW, CH, "3. rgb_pad_to_patches", [
    "RGB bytes -> [1610, 3, 14, 14]",
    "centre pad, (x/255 - mean) / std",
    "bf16, on the device",
], TEAL)
card(XS[2], r2, BW, CH, "4. ViT (32 blocks)", [
    "[1610, 1024]",
    "2-D RoPE, full attention",
    "inside each image",
], TEAL)
card(XS[1], r2, BW, CH, "5. Downsample + projector", [
    "3x3 concat: [192, 9216]",
    "Linear, GELU, Linear",
    "-> [192, hidden]",
], TEAL)
card(XS[0], r2, BW, CH, "6. replace_input_embeds", [
    "IMAGE rows   <- 192 vectors",
    "START/NEW_LINE/END rows",
    "  <- 3 learned vectors",
], PINK, thick=2)
d.arrow(XS[0] + BW, r1 + CH / 2, XS[1] - 2, r1 + CH / 2, INK)
d.arrow(XS[1] + BW, r1 + CH / 2, XS[2] - 2, r1 + CH / 2, INK)
d.arrow(XS[2] + BW / 2, r1 + CH, XS[2] + BW / 2, r2 - 2, TEAL)
d.arrow(XS[2], r2 + CH / 2, XS[1] + BW + 2, r2 + CH / 2, TEAL)
d.arrow(XS[1], r2 + CH / 2, XS[0] + BW + 2, r2 + CH / 2, TEAL)

# ============================================================================
# Panel 3: one image as tokens
# ============================================================================
y0 = y0 + P2_H + 20
P3_H = 72 + 150
d.panel(y0, P3_H, 3, "What does one 640x480 image become?",
        "1610 ViT patches, 192 image vectors, and 206 prompt positions.")
rows = [
    ("resize", "best size 644x490 = 46 x 35 patches of 14 px  ->  n_vit = 1610"),
    ("grid", "n_llm_w = ceil(46/3) = 16,  n_llm_h = ceil(35/3) = 12  ->  192 IMAGE tokens"),
    ("tokens", "12 x (16 + 1) + 2 = 206 positions in the prompt"),
    ("input_ids", "[V+2, V+1, V+1, ... V+1]   (1 + 205 ids; what the scheduler sees)"),
    ("mm_token_type", "[START, (IMAGE x 16, NEW_LINE) x 12, END]   (what the merge uses)"),
]
for i, (k, v) in enumerate(rows):
    yy = y0 + 84 + i * 26
    d.text(46, yy, k, 12.5, MUTE, "bold", mono=True)
    d.text(176, yy, v, 12.5, INK, mono=True)

y = y0 + P3_H + 22
d.legend(30, y, [(BLUE, "engine process"), (VIOLET, "worker process"), (AMBER, "scheduling"), (TEAL, "vision encoder"), (PINK, "merge")])
y += 38
y = d.footnotes(30, y, [
    "The downsample ratio 3, the hidden size and max_image_tokens come from the checkpoint config.json (not in the repo).",
    "  Patch size 14, 1024 channels, 32 blocks and 16 heads are constants in vit.py:27-31.",
    "Simplified: CP mirror layouts, cached-image prefixes and the NPU attention replacement are not shown.",
])
d.save(height=y + 10)
