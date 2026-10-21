"""Diagram: the places where the hardware platform changes the code path.

Used by: src/concepts/hardware-platforms.html
Sources (commit 9bd9cf2):
  deepinfer/model_executor/layers/tilelang_ops/ops.py:13-32
  deepinfer/model_executor/layers/tilelang_ops/swa_index.py:31
  deepinfer/model_executor/layers/tilelang_ops/cuda/swa_index.py:7-8
  deepinfer/model_executor/layers/tilelang_ops/asc/swa_index.py:3-12
  deepinfer/platform.py:120-141
  deepinfer/npu_ops/__init__.py:3-12, deepinfer/npu_ops/patch_imports.py:96-142
  setup.py:12, 38-72
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, MUTE, TEAL, VIOLET, Diagram  # noqa: E402

d = Diagram()
d.header(
    "Where the platform changes the code path",
    "Shared code is written once. Four switch points send it to NVIDIA or Ascend code  ·  commit 9bd9cf2",
    params="PLATFORM.tilelang_ops_backend = \"cuda\" | \"asc\"     setup.py: IS_NPU = accelerator_kind() == \"ascend\"",
)

# ============================================================================
# Panel 1: kernel dispatch
# ============================================================================
y0 = 112
top = y0 + 72
P1_H = 290
d.panel(y0, P1_H, 1, "Kernels: ops.py loads one backend folder",
        "Interface files call ops.<name>_tl. Only ops.py knows which folder (cuda/ or asc/) the factories come from.")

rx, rw = 1000, 454
bh = 78
b_y = top
e_y = top + bh + 22
mid_y = (b_y + e_y + bh) / 2

tx, tw, th = 46, 360, 96
d.box(tx, mid_y - th / 2, tw, th, "Interface file (hardware-neutral)", [
    "tilelang_ops/swa_index.py:31",
    "ops.expand_swa_index_tl(width)",
    "    (pivots, out)",
], col=TEAL)

vx, vw, vh = 466, 420, 112
d.box(vx, mid_y - vh / 2, vw, vh, "Dispatcher: tilelang_ops/ops.py", [
    "pkg = <package>.<PLATFORM.tilelang_ops_backend>",
    "import every module in pkg",
    "re-export each public name that ends in _tl",
    "unknown name  →  KernelUnavailableError",
], col=VIOLET)
d.arrow(tx + tw, mid_y, vx - 2, mid_y, TEAL)
d.arrow_label((tx + tw + vx) / 2, mid_y, "call", TEAL)

jx = 930
d.line(vx + vw, mid_y, jx, mid_y, INK, 1.6)
d.circle(jx, mid_y, 4, INK)
d.path_arrow(f"M {jx},{mid_y:.1f} L {jx},{b_y + bh / 2:.1f} L {rx - 2},{b_y + bh / 2:.1f}", BLUE)
d.path_arrow(f"M {jx},{mid_y:.1f} L {jx},{e_y + bh / 2:.1f} L {rx - 2},{e_y + bh / 2:.1f}", EMERALD)
d.text((jx + rx) / 2, b_y + bh / 2 - 10, '"cuda"', 11.5, BLUE, "bold", "middle", mono=True)
d.text((jx + rx) / 2, e_y + bh / 2 - 10, '"asc"', 11.5, EMERALD, "bold", "middle", mono=True)

d.box(rx, b_y, rw, bh, "tilelang_ops/cuda/swa_index.py", [
    '@tilelang.jit(out_idx=None, target="cuda")',
    "import tilelang.language as T  ·  128 threads",
], col=BLUE)
d.box(rx, e_y, rw, bh, "tilelang_ops/asc/swa_index.py", [
    "@tilelang.jit(out_idx=None, pass_configs={...})",
    "import tilelang.ascend.language as T  ·  vector cores",
], col=EMERALD)
d.aside(46, e_y + bh + 30, [
    "Both folders define the same name, expand_swa_index_tl. The interface file never imports cuda/ or asc/ itself.",
])

# ============================================================================
# Panel 2: three more switch points
# ============================================================================
y0 = y0 + P1_H + 20
sx, sw = 46, 340          # source column
wx, ww = 446, 420         # switch column
ox, ow = 926, 528         # result column
LH, GAP = 52, 10          # line box height, gap between the two lines
ROW_H = 2 * LH + GAP
ROW_GAP = 26
rows = [
    dict(
        src=("Shared code calls torch.cuda.*", ["streams, events, memory calls", "(written once, CUDA style)"]),
        sw=("transfer_to_npu", ["torch_npu.contrib, imported by", "PlatformNPU.__init__ (platform.py:121)"], AMBER),
        nv=("torch.cuda.* runs on CUDA, no patch", ["the normal PyTorch CUDA API"]),
        npu=("torch.cuda.* is mapped onto torch.npu.*", ["and Stream.cuda_stream → npu_stream"]),
        both=False,
    ),
    dict(
        src=("Vendor imports in shared code", ["from deep_select.interface import topk", "from flash_attn.cute.interface ..."]),
        sw=("npu_ops import hook", ["builtins.__import__ = _hooked_import", "npu_ops/patch_imports.py:96-142"], AMBER),
        nv=("Vendor functions are used as they are", ["deep_select topk, flash_attn _flash_attn_fwd"]),
        npu=("npu_ops versions are used", ["deep_select.topk  ·  vit_attn._flash_attn_fwd"]),
        both=False,
    ),
    dict(
        src=("C++ extension deepinfer._C", ["11 common sources in csrc/", "(engine, scheduler, ZOS, ...)"]),
        sw=("setup.py, at build time", ['IS_NPU = accelerator_kind() == "ascend"', "setup.py:12"], VIOLET),
        nv=("CUDAExtension + cuda_utils.cpp", ["graph_timer_cuda.cpp  →  _so/nvidia-<arch>/"]),
        npu=("NpuExtension + asc_utils.cpp, -DWITH_NPU", ["graph_timer_asc.cpp  →  _so/ascend-<arch>/"]),
        both=True,
    ),
]
P2_H = 80 + len(rows) * ROW_H + (len(rows) - 1) * ROW_GAP + 34
d.panel(y0, P2_H, 2, "Three more switch points",
        "On NVIDIA the shared code runs as written. On Ascend, two patches redirect it. The C++ build picks its sources once.")

r = y0 + 80
for row in rows:
    up_c = r + LH / 2
    lo_c = r + LH + GAP + LH / 2
    title, lines = row["src"]
    d.box(sx, r, sw, ROW_H, title, lines, col=TEAL)
    s_title, s_lines, s_col = row["sw"]
    if row["both"]:
        bw = 320
        d.box(wx, r, bw, ROW_H, s_title, s_lines, col=s_col, mono_size=11)
        d.arrow(sx + sw, r + ROW_H / 2, wx - 2, r + ROW_H / 2, TEAL)
        d.path_arrow(f"M {wx + bw},{up_c:.1f} L {ox - 2},{up_c:.1f}", BLUE)
        d.path_arrow(f"M {wx + bw},{lo_c:.1f} L {ox - 2},{lo_c:.1f}", EMERALD)
        d.arrow_label((wx + bw + ox) / 2, up_c, "IS_NPU is False", BLUE)
        d.arrow_label((wx + bw + ox) / 2, lo_c, "IS_NPU is True", EMERALD)
    else:
        d.box(wx, r + LH + GAP, ww, LH, s_title, s_lines[:1], col=s_col)
        d.text(wx + ww / 2, r + LH + GAP + LH + 15, s_lines[1], 11.5, MUTE, anchor="middle", mono=True)
        d.arrow(sx + sw, up_c, ox - 2, up_c, BLUE)
        d.arrow_label((wx + ww / 2), up_c, "NVIDIA: no patch", BLUE)
        d.arrow(sx + sw, lo_c, wx - 2, lo_c, EMERALD)
        d.arrow(wx + ww, lo_c, ox - 2, lo_c, EMERALD)
        d.arrow_label((sx + sw + wx) / 2, lo_c, "Ascend", EMERALD)
    nt, nl = row["nv"]
    d.box(ox, r, ow, LH, nt, nl, col=BLUE)
    et, el = row["npu"]
    d.box(ox, r + LH + GAP, ow, LH, et, el, col=EMERALD)
    r += ROW_H + ROW_GAP

y = y0 + P2_H + 24
d.legend(30, y, [
    (TEAL, "shared, hardware-neutral code"),
    (VIOLET, "selection logic"),
    (AMBER, "Ascend-only patch"),
    (BLUE, "NVIDIA path"),
    (EMERALD, "Ascend path"),
])
y += 40
y = d.footnotes(30, y, [
    "Not shown: 47 smaller \"PLATFORM.is_npu / is_gpu\" checks in 23 Python files (for example tilelang_ops/norm.py and store_kv_cache.py).",
    "Not every kernel exists on both sides: cuda/ exports 43 *_tl factories, asc/ exports 42. Only cuda/ has detect_outlier_and_abort_tl (a debug check).",
    "  Some file names differ between the folders; ops.py only uses the factory names. A missing name raises KernelUnavailableError (an AttributeError).",
    "The _so/<accelerator>-<arch>/ folder name comes from DEEPINFER_ACCELERATOR in scripts/build.sh, not from setup.py.",
])
d.save(height=y + 14)
