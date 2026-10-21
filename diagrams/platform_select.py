"""Diagram: how DeepInfer picks a hardware platform, and what each Platform sets.

Used by: src/concepts/hardware-platforms.html
Sources (commit 9bd9cf2):
  deep_cluster/hardware/device.py:17-23   accelerator_kind()
  deep_cluster/hardware/ascend.py:61-68   ascend.is_available()
  deep_cluster/hardware/nvidia.py:40-48   nvidia device_ids() / is_available()
  deepinfer/platform.py:55-227            PlatformGPU, PlatformNPU, get_platform()
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import BLUE, EMERALD, INK, LINE, MUTE, NEUTRAL, VIOLET, Diagram, MONO  # noqa: E402,F401

d = Diagram()
d.header(
    "Two hardware platforms, one Platform object",
    "How DeepInfer picks NVIDIA or Ascend at start-up, and what the choice sets  ·  commit 9bd9cf2",
    params="accelerator_kind() → \"ascend\" | \"nvidia\" | \"cpu\"     PLATFORM = get_platform()   (lazy, cached)",
)

# ============================================================================
# Panel 1: which platform?
# ============================================================================
y0 = 112
P1_H = 372
d.panel(y0, P1_H, 1, "Which platform? The device files decide",
        "deep_cluster looks for device files. It does not import torch. get_platform() turns the answer into one object.")

top = y0 + 92
d.text(46, top - 10, "deep_cluster.hardware.accelerator_kind()", 12, VIOLET, "bold", mono=True)

# Ascend check
ax, aw = 46, 420
a1y, a1h = top, 88
d.box(ax, a1y, aw, a1h, "1st check: Ascend device files?", [
    "/dev/davinci_manager   or   /dev/davinci<N>",
    "or  /sys/class/ubcore/udma*/device/ub_totalues > 0",
    "ascend.py:61-68",
], col=VIOLET)
# NVIDIA check
a2y, a2h = a1y + a1h + 34, 74
d.box(ax, a2y, aw, a2h, "2nd check: NVIDIA device files?", [
    "/proc/driver/nvidia/gpus/<bus-id>/   or   /dev/nvidia<N>",
    "nvidia.py:40-48",
], col=VIOLET)

# result chips
cx, cw = 540, 130
c1 = a1y + a1h / 2
c2 = a2y + a2h / 2
c3 = a2y + a2h + 44
d.chip(cx, c1 - 15, cw, '"ascend"', EMERALD)
d.chip(cx, c2 - 15, cw, '"nvidia"', BLUE)
d.chip(cx, c3 - 15, cw, '"cpu"', NEUTRAL)

d.arrow(ax + aw, c1, cx - 2, c1, EMERALD)
d.arrow_label((ax + aw + cx) / 2, c1, "yes", EMERALD)
d.arrow(ax + aw, c2, cx - 2, c2, BLUE)
d.arrow_label((ax + aw + cx) / 2, c2, "yes", BLUE)
mid = ax + aw / 2
d.arrow(mid, a1y + a1h, mid, a2y - 2, INK)
d.text(mid + 10, a1y + a1h + 21, "no", 11.5, INK, "bold")
d.path_arrow(f"M {mid:.1f},{a2y + a2h:.1f} L {mid:.1f},{c3:.1f} L {cx - 2:.1f},{c3:.1f}", MUTE)
d.text(mid + 10, a2y + a2h + 21, "no", 11.5, INK, "bold")
d.text((mid + cx) / 2 + 30, c3 - 10, "no device found", 11.5, MUTE, "bold", "middle")

# get_platform box
gx, gw = 740, 400
gy, gh = a1y, c3 + 15 - a1y
d.rect(gx, gy, gw, gh, fill=VIOLET[1], stroke=VIOLET, sw=1.5)
d.text(gx + gw / 2, gy + 22, "get_platform()", 13.5, VIOLET, "bold", "middle")
d.text(gx + gw / 2, gy + 40, "deepinfer/platform.py:222-227", 11.5, MUTE, anchor="middle", mono=True)
rows = [
    ('"ascend"', "→  PlatformNPU()", EMERALD),
    ('"nvidia"', "→  PlatformGPU()", BLUE),
    ('"cpu"', "→  PlatformGPU()   (fallback)", MUTE),
]
for i, (k, v, col) in enumerate(rows):
    ry = gy + 76 + i * 22
    d.text(gx + 24, ry, k, 12, col, "bold", mono=True)
    d.text(gx + 118, ry, v, 12, INK, mono=True)
d.line(gx + 20, gy + 150, gx + gw - 20, gy + 150, LINE, 0.8)
d.text(gx + 24, gy + 176, "@functools.cache  →  one object per process", 12, INK, mono=True)
d.text(gx + 24, gy + 198, "deepinfer.PLATFORM  →  calls it on first use", 12, INK, mono=True)
d.text(gx + 24, gy + 220, "(deepinfer/__init__.py:53-64)", 11.5, MUTE, mono=True)

for c, col in ((c1, EMERALD), (c2, BLUE), (c3, MUTE)):
    d.arrow(cx + cw, c, gx - 2, c, col)

# outputs
ox, ow = 1210, 244
o1y, oh = a1y + 8, 92
o2y = o1y + oh + 50
d.box(ox, o1y, ow, oh, "PlatformNPU", ['backend dir  "asc"', 'comm         "hccl"', "fp8_sf_type  int16"], col=EMERALD, align="start")
d.box(ox, o2y, ow, oh, "PlatformGPU", ['backend dir  "cuda"', 'comm         "nccl"', "fp8_sf_type  int32"], col=BLUE, align="start")
d.arrow(gx + gw, o1y + oh / 2, ox - 2, o1y + oh / 2, EMERALD)
d.arrow(gx + gw, o2y + oh / 2, ox - 2, o2y + oh / 2, BLUE)

# ============================================================================
# Panel 2: what each Platform sets
# ============================================================================
y0 = y0 + P1_H + 20
d_rows = [
    ("tilelang_ops_backend", '"cuda"  →  tilelang_ops/cuda/', '"asc"  →  tilelang_ops/asc/'),
    ("distributed_backend", '"nccl"  (NVIDIA NCCL)', '"hccl"  (Huawei HCCL)'),
    ("get_distributed_options()", "NCCL options: max_ctas = min_ctas = 32", "ProcessGroupHCCL.Options()  (defaults)"),
    ("fp8_sf_type", "torch.int32", "torch.int16"),
    ("pin_host_memory()", "cudart().cudaHostRegister(...)", "aclrtHostRegisterV2(...)  via ctypes"),
    ("is_gpu  /  is_npu", "True  /  False", "False  /  True"),
]
npu_steps = [
    "CUDA_VISIBLE_DEVICES ← ASCEND_RT_VISIBLE_DEVICES",
    "PYTORCH_NPU_ALLOC_CONF=expandable_segments:True",
    "TASK_QUEUE_ENABLE=0,  HCCL_BUFFSIZE=16, HCCL_* timeouts",
    "import torch_npu, transfer_to_npu  (cuda → npu)",
    "TILELANG_DEFAULT_TARGET=ascend   (if not set)",
    "torch.npu.Stream.cuda_stream = npu_stream",
    "import deepinfer.npu_ops   (import hook)",
    "load aclrtHostRegisterV2 from libascendcl.so",
]
ROW_H = 34
lane_y = y0 + 70
header_h = 64
rows_y = lane_y + header_h + 12
steps_y = rows_y + len(d_rows) * ROW_H + 30
lane_h = steps_y - lane_y + 26 + len(npu_steps) * 22 + 14
P2_H = lane_h + 90
d.panel(y0, P2_H, 2, "What does each Platform object set?",
        "Both classes fill the same names. Shared code reads PLATFORM.<name>; some code also checks PLATFORM.is_npu.")

kx, kw = 46, 330
nx, nw = 396, 500
sx, sw_ = 916, 538
d.lane(nx, lane_y, nw, lane_h, BLUE, "PlatformGPU  ·  NVIDIA SM100 GPUs",
       ["deepinfer/platform.py:55-83", "constructor sets only fp8_sf_type"])
d.lane(sx, lane_y, sw_, lane_h, EMERALD, "PlatformNPU  ·  Huawei Ascend 950 NPUs",
       ["deepinfer/platform.py:86-219", "constructor also changes the process (see below)"])
d.text(kx, lane_y + 23, "Name on Platform", 15, INK, "bold")
d.text(kx, lane_y + 41, "base class: platform.py:19-52", 11.5, MUTE)

for i, (k, v1, v2) in enumerate(d_rows):
    ry = rows_y + i * ROW_H
    if i:
        d.line(kx, ry - 12, sx + sw_ - 12, ry - 12, LINE, 0.8)
    d.text(kx, ry + 9, k, 12, INK, "bold", mono=True)
    d.text(nx + 14, ry + 9, v1, 12, INK, mono=True)
    d.text(sx + 14, ry + 9, v2, 12, INK, mono=True)

d.text(nx + 14, steps_y, "NVIDIA: no extra start-up steps", 12, BLUE, "bold", mono=True)
d.aside(nx + 14, steps_y + 26, [
    "PlatformGPU.__init__ imports torch and",
    "sets fp8_sf_type = torch.int32. Nothing else.",
    "",
    "The NCCL SM limit comes from the env var",
    "DEEPINFER_NCCL_NUM_SMS (default 32).",
])
d.text(sx + 14, steps_y, "Ascend only: extra start-up steps in __init__", 12, EMERALD, "bold", mono=True)
for i, s in enumerate(npu_steps):
    ry = steps_y + 26 + i * 22
    d.badge(sx + 24, ry - 4, i + 1, EMERALD, r=8, size=10)
    d.text(sx + 40, ry, s, 11.5, INK, mono=True)

y = y0 + P2_H + 24
d.legend(30, y, [
    (VIOLET, "selection logic (deep_cluster, get_platform)"),
    (BLUE, "NVIDIA path"),
    (EMERALD, "Ascend path"),
    (NEUTRAL, "no accelerator found"),
])
y += 40
y = d.footnotes(30, y, [
    "Simplified: the NCCL option names are config.max_ctas and config.min_ctas (platform.py:80-82). HCCL_CONNECT_TIMEOUT=240 and HCCL_EXEC_TIMEOUT=200 are",
    "  defaults (setdefault); HCCL_BUFFSIZE=16, PYTORCH_NPU_ALLOC_CONF and TASK_QUEUE_ENABLE=0 always overwrite. Step 1 raises RuntimeError when CUDA_VISIBLE_DEVICES is set and differs.",
    "Not shown: TORCH_NPU_DEVICE_CAPABILITY=9.0 (a temporary torch_npu work-around, platform.py:117-118) and set_compile_mode(jit_compile=False).",
])
d.save(height=y + 14)
