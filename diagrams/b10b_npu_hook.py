"""Diagram: the npu_ops import hook: when it is installed, what a from-import returns, the two replacements.

Used by: src/code/npu-ops.html
Sources (commit 9bd9cf2):
  deepinfer/timer.py:13                         first PLATFORM access when the engine is imported
  deepinfer/__init__.py:53-64                   lazy PLATFORM
  deepinfer/platform.py:140-141                 PlatformNPU.__init__ imports deepinfer.npu_ops
  deepinfer/npu_ops/__init__.py:1-12            the patch map
  deepinfer/npu_ops/patch_imports.py:55-93      _hooked_import
  deepinfer/npu_ops/patch_imports.py:96-142     patch_imports (once only, replaces builtins.__import__)
  deepinfer/npu_ops/deep_select.py:20-26        topk replacement
  deepinfer/npu_ops/vit_attn.py:8-31           _flash_attn_fwd replacement
  deepinfer/model_executor/layers/sampler.py:12 an importer of deep_select.interface.topk
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, MUTE, VIOLET, Diagram  # noqa: E402

d = Diagram(width=1100)
d.header(
    "npu_ops: an import hook that swaps two vendor functions on Ascend",
    "deepinfer/npu_ops/  ·  runs only in a PlatformNPU process  ·  commit 9bd9cf2",
    params="patched: deep_select.interface.topk, flash_attn.cute.interface._flash_attn_fwd",
)

BW, GAP = 316, 30


def three_boxes(by, bh, boxes, arrows=True):
    for i, (title, col, lines) in enumerate(boxes):
        bx = 46 + i * (BW + GAP)
        d.rect(bx, by, BW, bh, fill=col[1], stroke=col, sw=1.5)
        d.text(bx + 14, by + 24, title, 14, col[0], "bold")
        for j, s in enumerate(lines):
            last = j == len(lines) - 1
            d.text(bx + 14, by + 48 + j * 17, s, 11.5 if last else 12, MUTE if last else INK, mono=True)
        if arrows and i < len(boxes) - 1:
            ax = bx + BW
            d.arrow(ax, by + bh / 2, ax + GAP - 2, by + bh / 2, INK)


# Panel 1: install
y0 = 112
BH1 = 150
P1_H = 72 + BH1 + 24
d.panel(y0, P1_H, 1, "When is the hook installed?",
        "At the first use of deepinfer.PLATFORM, and only when the platform is Ascend.")
three_boxes(y0 + 72, BH1, [
    ("1. first PLATFORM access", VIOLET, [
        "from deepinfer import PLATFORM",
        "  e.g. timer.py at import",
        "__getattr__ -> get_platform()",
        "accelerator_kind() == ascend",
        "  -> PlatformNPU()",
        "__init__.py:53-64",
    ]),
    ("2. PlatformNPU.__init__", VIOLET, [
        "env vars, torch_npu,",
        "  transfer_to_npu, ...",
        "# TODO(NPU): Intended",
        "#   to be removed.",
        "import deepinfer.npu_ops",
        "platform.py:140-141",
    ]),
    ("3. patch_imports(map)", VIOLET, [
        "map: target module ->",
        "  {name: source path}",
        "second call -> RuntimeError",
        "builtins.__import__ =",
        "  _hooked_import",
        "patch_imports.py:96-142",
    ]),
])

# Panel 2: what an import returns
y1 = y0 + P1_H + 20
BH2 = 150
P2_H = 72 + BH2 + 24
d.panel(y1, P2_H, 2, "What does `from X import a` return after that?",
        "_hooked_import decides for each statement. It never puts its own module object into sys.modules.")
three_boxes(y1 + 72, BH2, [
    ("a. not patched", BLUE, [
        "plain `import X`, or level != 0,",
        "  or X not in the map,",
        "  or no patched name in it",
        "-> the original import",
        "",
        "patch_imports.py:63-69",
    ]),
    ("b. caller is the source", EMERALD, [
        "caller __name__ starts with",
        "  deepinfer.npu_ops.deep_select",
        "  (or .vit_attn)",
        "-> the original vendor",
        "   object, no recursion",
        "patch_imports.py:86-89",
    ]),
    ("c. any other caller", AMBER, [
        "-> a new empty module object",
        "a = Lazy(target, source):",
        "  loads the NPU version",
        "  at the first call",
        "other names -> real module",
        "patch_imports.py:90-93",
    ]),
], arrows=False)

# Panel 3: replacements and the trap
y2 = y1 + P2_H + 20
BH3 = 150
P3_H = 72 + BH3 + 24
d.panel(y2, P3_H, 3, "What do the replacements do, and what can go wrong?",
        "Both files say TODO(NPU): to be removed. Order matters: the hook changes only later imports.")
three_boxes(y2 + 72, BH3, [
    ("topk  (deep_select.py)", AMBER, [
        "return_value missing / True:",
        "  torch.topk (sampler path)",
        "return_value=False:",
        "  vendor topk (indexer path)",
        "",
        "deep_select.py:20-26",
    ]),
    ("_flash_attn_fwd  (vit_attn.py)", AMBER, [
        "torch_npu.npu_fusion_attention",
        "layout TND, not causal",
        "scale 1 / sqrt(head_dim)",
        "kv lengths = q lengths",
        "returns (out, None)",
        "vit_attn.py:9-31",
    ]),
    ("import-order trap", AMBER, [
        "a module that ran its",
        "  `from ... import` before",
        "  step 2 keeps the vendor",
        "  object; nothing checks",
        "e.g. sampler.py:12",
        "timer.py:13",
    ]),
], arrows=False)

y = y2 + P3_H + 22
d.legend(30, y, [(VIOLET, "install path"), (BLUE, "normal import"), (EMERALD, "original vendor object"),
                 (AMBER, "Ascend-only patch / risk")])
y += 38
y = d.footnotes(30, y, [
    "In the normal engine start, deepinfer.timer creates PLATFORM before the model modules are imported (llm_engine -> profile_server -> utils -> timer).",
    "On NVIDIA nothing imports deepinfer.npu_ops, so the vendor functions stay unchanged.",
])
d.save(height=y + 10)
