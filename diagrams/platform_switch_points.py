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
from svglib import AMBER, BLUE, EMERALD, INK, MUTE, TEAL, VIOLET, Diagram, text_width  # noqa: E402

W = 1100
d = Diagram(width=W)
d.header(
    "Where the platform changes the code path",
    "Shared code is written once. Four switch points send it to NVIDIA or Ascend code  ·  commit 9bd9cf2",
    params="PLATFORM.tilelang_ops_backend = \"cuda\" | \"asc\"     setup.py: IS_NPU = accelerator_kind() == \"ascend\"",
)

MS = 12.5     # mono data size
PITCH = 18    # mono line pitch
R = W - 46    # right edge of panel content


def card_h(n):
    return 44 + PITCH * (n - 1) + 16 if n else 36


def card(x, y, w, title, lines, col, h=None, sub=None):
    """Box: 14 px title, 12.5 mono lines at 18 px pitch, optional muted mono last line."""
    allx = list(lines) + ([sub] if sub else [])
    h = h or card_h(len(allx))
    d.rect(x, y, w, h, fill=col[1], stroke=col, sw=1.5)
    d.text(x + w / 2, y + 22, title, 14, col, "bold", "middle")
    for i, s in enumerate(lines):
        d.text(x + w / 2, y + 44 + i * PITCH, s, MS, INK, anchor="middle", mono=True)
    if sub:
        d.text(x + w / 2, y + 44 + len(lines) * PITCH, sub, 12, MUTE, anchor="middle", mono=True)
    return h


def wrap(s, size, max_w, indent="  "):
    out, cur = [], ""
    for w in s.split(" "):
        t = (cur + " " + w) if cur else w
        if cur and text_width(t, size) > max_w:
            out.append(cur)
            cur = indent + w
        else:
            cur = t
    out.append(cur)
    return out


# ============================================================================
# Panel 1: kernel dispatch
# ============================================================================
y0 = 112
top = y0 + 76
vh = card_h(4)
bh = card_h(2)
jy = top + vh + 34            # junction row
b_y = jy + 40                 # backend boxes
P1_H = b_y + bh + 52 - y0
d.panel(y0, P1_H, 1, "Kernels: ops.py loads one backend folder",
        "Interface files call ops.<name>_tl. Only ops.py knows which folder (cuda/ or asc/) the factories come from.")

tx, tw = 46, 320
th = card_h(3)
t_y = top + (vh - th) / 2
card(tx, t_y, tw, "Interface file (hardware-neutral)", [
    "tilelang_ops/swa_index.py:31",
    "ops.expand_swa_index_tl(width)",
    "    (pivots, out)",
], TEAL)

vx, vw = 440, 440
card(vx, top, vw, "Dispatcher: tilelang_ops/ops.py", [
    "pkg = <package>.<PLATFORM.tilelang_ops_backend>",
    "import every module in pkg",
    "re-export each public name that ends in _tl",
    "unknown name  →  KernelUnavailableError",
], VIOLET)
mid_y = top + vh / 2
d.arrow(tx + tw, mid_y, vx - 2, mid_y, TEAL)
d.arrow_label((tx + tw + vx) / 2, mid_y, "call", TEAL)

bw = (R - 46 - 28) / 2
bx1, bx2 = 46, 46 + bw + 28
jx = vx + vw / 2
d.line(jx, top + vh, jx, jy, INK, 1.6)
d.circle(jx, jy, 4, INK)
c1, c2 = bx1 + bw / 2, bx2 + bw / 2
d.path_arrow(f"M {jx:.1f},{jy:.1f} L {c1:.1f},{jy:.1f} L {c1:.1f},{b_y - 2:.1f}", BLUE)
d.path_arrow(f"M {jx:.1f},{jy:.1f} L {c2:.1f},{jy:.1f} L {c2:.1f},{b_y - 2:.1f}", EMERALD)
d.text((jx + c1) / 2, jy - 9, '"cuda"', 12, BLUE, "bold", "middle", mono=True)
d.text((jx + c2) / 2, jy - 9, '"asc"', 12, EMERALD, "bold", "middle", mono=True)

card(bx1, b_y, bw, "tilelang_ops/cuda/swa_index.py", [
    '@tilelang.jit(out_idx=None, target="cuda")',
    "import tilelang.language as T  ·  128 threads",
], BLUE)
card(bx2, b_y, bw, "tilelang_ops/asc/swa_index.py", [
    "@tilelang.jit(out_idx=None, pass_configs={...})",
    "import tilelang.ascend.language as T  ·  vector cores",
], EMERALD)
d.aside(46, b_y + bh + 28, [
    "Both folders define the same name, expand_swa_index_tl. The interface file never imports cuda/ or asc/ itself.",
])

# ============================================================================
# Panel 2: three more switch points
# ============================================================================
# Each row: tier A = shared source code -> switch;  tier B = NVIDIA result | Ascend result.
y0 = y0 + P1_H + 20
sx, sw = 46, 400                        # source box
nx, nw = 46, (R - 46 - 28) / 2          # NVIDIA result
ex = nx + nw + 28                       # Ascend result
wx, ww = ex, nw                         # switch box, above the Ascend result
A_H = card_h(3)
B_H = card_h(1)
TIER_GAP = 50
ROW_H = A_H + TIER_GAP + B_H
ROW_GAP = 30
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
P2_H = 82 + len(rows) * ROW_H + (len(rows) - 1) * ROW_GAP + 26
d.panel(y0, P2_H, 2, "Three more switch points",
        "On NVIDIA the shared code runs as written. On Ascend, two patches redirect it. The C++ build picks its sources once.")

r = y0 + 82
for row in rows:
    a_mid = r + A_H / 2
    b_top = r + A_H + TIER_GAP
    title, lines = row["src"]
    card(sx, r, sw, title, lines, TEAL, h=A_H)
    s_title, s_lines, s_col = row["sw"]
    card(wx, r, ww, s_title, s_lines[:1], s_col, h=A_H, sub=s_lines[1])
    nc, ec = nx + nw / 2, ex + nw / 2
    if row["both"]:
        d.arrow(sx + sw, a_mid, wx - 2, a_mid, TEAL)
        # split below the switch box
        jx, jy = wx + 60, r + A_H + TIER_GAP / 2
        d.line(jx, r + A_H, jx, jy, INK, 1.6)
        d.circle(jx, jy, 4, INK)
        d.path_arrow(f"M {jx:.1f},{jy:.1f} L {nc:.1f},{jy:.1f} L {nc:.1f},{b_top - 2:.1f}", BLUE)
        d.path_arrow(f"M {jx:.1f},{jy:.1f} L {ec:.1f},{jy:.1f} L {ec:.1f},{b_top - 2:.1f}", EMERALD)
        d.arrow_label((nc + jx) / 2 + 20, jy, "IS_NPU is False", BLUE)
        d.arrow_label((jx + ec) / 2 + 30, jy, "IS_NPU is True", EMERALD)
    else:
        d.arrow(nc, r + A_H, nc, b_top - 2, BLUE)
        d.text(nc + 10, r + A_H + TIER_GAP / 2 + 4, "NVIDIA: no patch", 11.5, BLUE, "bold")
        d.arrow(sx + sw, a_mid, wx - 2, a_mid, EMERALD)
        d.arrow_label((sx + sw + wx) / 2, a_mid, "Ascend", EMERALD)
        d.arrow(ec, r + A_H, ec, b_top - 2, EMERALD)
    nt, nl = row["nv"]
    card(nx, b_top, nw, nt, nl, BLUE, h=B_H)
    et, el = row["npu"]
    card(ex, b_top, nw, et, el, EMERALD, h=B_H)
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
notes = []
for para in [
    "Not shown: 47 smaller \"PLATFORM.is_npu / is_gpu\" checks in 23 Python files (for example tilelang_ops/norm.py and store_kv_cache.py).",
    "Not every kernel exists on both sides: cuda/ exports 43 *_tl factories, asc/ exports 42. Only cuda/ has detect_outlier_and_abort_tl (a debug check). "
    "Some file names differ between the folders; ops.py only uses the factory names. A missing name raises KernelUnavailableError (an AttributeError).",
    "The _so/<accelerator>-<arch>/ folder name comes from DEEPINFER_ACCELERATOR in scripts/build.sh, not from setup.py.",
]:
    notes += wrap(para, 12, W - 70)
y = d.footnotes(30, y, notes)
d.save(height=y + 14)
