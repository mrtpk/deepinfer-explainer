"""Diagram: the ViT, the downsample and the projector with shapes.

Used by: src/code/vit.html, src/concepts/vision-encoder.html
Sources (commit 9bd9cf2):
  deepinfer/model_executor/models/vision_encoder/vit.py:27-34      fixed constants (patch 14, dim 1024, depth 32, 16 heads, 2.7, 128)
  deepinfer/model_executor/models/vision_encoder/vit.py:69-76      PatchEmbedFlatten: Linear(3*14*14 -> 1024)
  deepinfer/model_executor/models/vision_encoder/vit.py:90-123     Attention: qkv Linear, 2-D RoPE, varlen non-causal flash-attn
  deepinfer/model_executor/models/vision_encoder/vit.py:126-136    SwiGLU: hidden rounded up to a multiple of 128 (2764 -> 2816)
  deepinfer/model_executor/models/vision_encoder/vit.py:139-165    Block: norm, attn, norm, mlp; residual added in the next norm
  deepinfer/model_executor/models/vision_encoder/vit.py:196-230    rope table, forward, fc_norm
  deepinfer/hugging_face/config.py:221-233                         recomputing_every_layer=2, projector depth 2
  deepinfer/model_executor/layers/tilelang_ops/image_embed_ops.py:485-552  batch_downsample: r x r channel concat
  deepinfer/model_executor/models/vision_encoder/mlp_projector.py:10-23    Linear, GELU, Linear
The example (one 640x480 image, r = 3) uses example values; r and the LLM hidden size come from config.json.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, INK, MUTE, TEAL, VIOLET, Diagram  # noqa: E402

d = Diagram(width=1100)
d.header(
    "Inside the vision encoder: ViT, downsample, projector",
    "VisionTransformer (vit.py) and MlpProjector (mlp_projector.py)  ·  shapes for one 640x480 image",
    params="patch 14  ·  dim 1024  ·  32 blocks  ·  16 heads x 64  ·  MLP 2816  ·  r = 3 (example)  ·  H = LLM hidden size",
)

BW = 300
XS = [46, 400, 754]


def card(x, y, w, h, title, lines, col, thick=1.5):
    d.rect(x, y, w, h, fill=col[1], stroke=col, sw=thick)
    d.text(x + 14, y + 24, title, 14, col[0], "bold")
    for i, s in enumerate(lines):
        d.text(x + 14, y + 48 + i * 18, s, 12.5, INK, mono=True)


# Panel 1: the ViT
y0 = 112
by = y0 + 72
BH = 132
P1_H = 72 + BH + 64
d.panel(y0, P1_H, 1, "What does the ViT compute for each patch?",
        "A flat linear patch embedding, then 32 pre-norm blocks with 2-D RoPE. Patches see only their own image.")
card(XS[0], by, BW, BH, "Patch embedding", [
    "in  [1610, 3, 14, 14] bf16",
    "Linear 588 -> 1024",
    "out [1610, 1024]",
    "vit.py:69-76",
], BLUE)
card(XS[1], by, BW, BH, "Block x 32", [
    "RMSNorm -> Attention",
    "  qkv 1024 -> 3072, 16 x 64",
    "RMSNorm -> SwiGLU",
    "  1024 -> 2 x 2816 -> 1024",
], TEAL, thick=2)
card(XS[2], by, BW, BH, "fc_norm", [
    "RMSNorm, eps 1e-6",
    "out [1610, 1024]",
    "one row per patch",
    "vit.py:230",
], BLUE)
d.arrow(XS[0] + BW, by + BH / 2, XS[1] - 2, by + BH / 2, INK)
d.arrow(XS[1] + BW, by + BH / 2, XS[2] - 2, by + BH / 2, INK)
d.text(46, by + BH + 26, "Attention: cu_seqlens_vit splits the batch per image, causal=False (vit.py:107-122). RoPE position = (row, column) of the patch.",
       12.5, INK)
d.text(46, by + BH + 44, "Every 2nd block adds the residual itself; the others leave it to the next RMSNorm kernel (vit.py:189, config.py:223).",
       12.5, MUTE)

# Panel 2: downsample and projector
y0 = y0 + P1_H + 20
by = y0 + 72
P2_H = 72 + BH + 30
d.panel(y0, P2_H, 2, "How do 1610 patches become 192 LLM vectors?",
        "Each 3 x 3 block of patches is joined into one long row; a 2-layer MLP maps it to the LLM width.")
card(XS[0], by, BW, BH, "Patch grid", [
    "35 rows x 46 columns",
    "pad to 36 x 48 with zeros",
    "(multiple of r = 3)",
    "image_embed_ops.py:573-576",
], AMBER)
card(XS[1], by, BW, BH, "batch_downsample", [
    "3 x 3 blocks: 12 x 16 = 192",
    "concat channels:",
    "  [192, 1024 * 9 = 9216]",
    "mode downsample_mlp_gelu",
], AMBER)
card(XS[2], by, BW, BH, "MlpProjector (depth 2)", [
    "Linear 9216 -> H",
    "GELU",
    "Linear H -> H",
    "out [192, H] = image tokens",
], VIOLET, thick=2)
d.arrow(XS[0] + BW, by + BH / 2, XS[1] - 2, by + BH / 2, AMBER)
d.arrow(XS[1] + BW, by + BH / 2, XS[2] - 2, by + BH / 2, AMBER)

y = y0 + P2_H + 22
d.legend(30, y, [(BLUE, "per-patch layers"), (TEAL, "transformer blocks"), (AMBER, "downsample"), (VIOLET, "projector")])
y += 38
y = d.footnotes(30, y, [
    "flash-attn, DeepGEMM and tile_kernels are not in this repo. The TileLang image kernels are (tilelang_ops/cuda|asc/image_embed_ops.py).",
    "On Ascend the attention call is replaced (npu_ops/vit_attn.py).",
    "The concat order inside one 3 x 3 block follows F.unfold in the reference function (image_embed_ops.py:577-580).",
])
d.save(height=y + 10)
