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
from svglib import BLUE, EMERALD, INK, LINE, MUTE, NEUTRAL, VIOLET, Diagram, MONO, text_width  # noqa: E402,F401

W = 1100
d = Diagram(width=W)
d.header(
    "Two hardware platforms, one Platform object",
    "How DeepInfer picks NVIDIA or Ascend at start-up, and what the choice sets  ·  commit 9bd9cf2",
    params="accelerator_kind() → \"ascend\" | \"nvidia\" | \"cpu\"     PLATFORM = get_platform()   (lazy, cached)",
)

MS = 12.5     # mono data size
PITCH = 18    # mono line pitch


def wrap(s, size, max_w, indent="  "):
    """Wrap one line of sans text at word boundaries; continuation lines get an indent."""
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


def card_h(n):
    return 44 + PITCH * (n - 1) + 16


def card(x, y, w, title, lines, col, align="middle"):
    """Box with a 14 px title and 12.5 mono lines at 18 px pitch. Returns the height."""
    h = card_h(len(lines))
    d.rect(x, y, w, h, fill=col[1], stroke=col, sw=1.5)
    if align == "middle":
        d.text(x + w / 2, y + 22, title, 14, col, "bold", "middle")
        for i, s in enumerate(lines):
            d.text(x + w / 2, y + 44 + i * PITCH, s, MS, INK, anchor="middle", mono=True)
    else:
        d.text(x + 14, y + 22, title, 14, col, "bold")
        for i, s in enumerate(lines):
            d.text(x + 14, y + 44 + i * PITCH, s, MS, INK, mono=True)
    return h


# ============================================================================
# Panel 1: which platform?
# ============================================================================
y0 = 112
top = y0 + 92
# heights first, so the panel can be drawn before its content
a1h, a2h, oh = card_h(3), card_h(3), card_h(3)
a1y = top
a2y = a1y + a1h + 36
c3 = a2y + a2h + 46
gy, gh = a1y, c3 + 15 - a1y
oy = gy + gh + 44
P1_H = oy + oh + 24 - y0
d.panel(y0, P1_H, 1, "Which platform? The device files decide",
        "deep_cluster looks for device files. It does not import torch. get_platform() turns the answer into one object.")

# Ascend check
ax, aw = 46, 440
d.text(46, top - 10, "deep_cluster.hardware.accelerator_kind()", 12.5, VIOLET, "bold", mono=True)
card(ax, a1y, aw, "1st check: Ascend device files?", [
    "/dev/davinci_manager   or   /dev/davinci<N>",
    "or  /sys/class/ubcore/udma*/device/ub_totalues > 0",
    "ascend.py:61-68",
], VIOLET)
# NVIDIA check
card(ax, a2y, aw, "2nd check: NVIDIA device files?", [
    "/proc/driver/nvidia/gpus/<bus-id>/",
    "or   /dev/nvidia<N>",
    "nvidia.py:40-48",
], VIOLET)

# result chips
cx, cw = 530, 104
c1 = a1y + a1h / 2
c2 = a2y + a2h / 2
d.chip(cx, c1 - 15, cw, '"ascend"', EMERALD)
d.chip(cx, c2 - 15, cw, '"nvidia"', BLUE)
d.chip(cx, c3 - 15, cw, '"cpu"', NEUTRAL)

d.arrow(ax + aw, c1, cx - 2, c1, EMERALD)
d.arrow_label((ax + aw + cx) / 2, c1, "yes", EMERALD)
d.arrow(ax + aw, c2, cx - 2, c2, BLUE)
d.arrow_label((ax + aw + cx) / 2, c2, "yes", BLUE)
mid = ax + aw / 2
d.arrow(mid, a1y + a1h, mid, a2y - 2, INK)
d.text(mid + 10, a1y + a1h + 22, "no", 12, INK, "bold")
d.path_arrow(f"M {mid:.1f},{a2y + a2h:.1f} L {mid:.1f},{c3:.1f} L {cx - 2:.1f},{c3:.1f}", MUTE)
d.text(mid + 10, a2y + a2h + 22, "no", 12, INK, "bold")
d.text((mid + cx) / 2 + 30, c3 - 10, "no device found", 12, MUTE, "bold", "middle")

# get_platform box
gx = 676
gw = W - 46 - gx
d.rect(gx, gy, gw, gh, fill=VIOLET[1], stroke=VIOLET, sw=1.5)
d.text(gx + gw / 2, gy + 22, "get_platform()", 14, VIOLET, "bold", "middle")
d.text(gx + gw / 2, gy + 41, "deepinfer/platform.py:222-227", 12, MUTE, anchor="middle", mono=True)
rows = [
    ('"ascend"', "→  PlatformNPU()", EMERALD),
    ('"nvidia"', "→  PlatformGPU()", BLUE),
    ('"cpu"', "→  PlatformGPU()   (fallback)", MUTE),
]
for i, (k, v, col) in enumerate(rows):
    ry = gy + 74 + i * 23
    d.text(gx + 18, ry, k, MS, col, "bold", mono=True)
    d.text(gx + 110, ry, v, MS, INK, mono=True)
d.line(gx + 16, gy + 150, gx + gw - 16, gy + 150, LINE, 0.8)
d.text(gx + 18, gy + 176, "@functools.cache  →  one object per process", MS, INK, mono=True)
d.text(gx + 18, gy + 199, "deepinfer.PLATFORM  →  calls it on first use", MS, INK, mono=True)
d.text(gx + 18, gy + 222, "(deepinfer/__init__.py:53-64)", 12, MUTE, mono=True)

for c, col in ((c1, EMERALD), (c2, BLUE), (c3, MUTE)):
    d.arrow(cx + cw, c, gx - 2, c, col)

# outputs, below get_platform()
ow = (gw - 20) / 2
o1x, o2x = gx, gx + ow + 20
card(o1x, oy, ow, "PlatformNPU", ['backend dir  "asc"', 'comm         "hccl"', "fp8_sf_type  int16"], EMERALD, align="start")
card(o2x, oy, ow, "PlatformGPU", ['backend dir  "cuda"', 'comm         "nccl"', "fp8_sf_type  int32"], BLUE, align="start")
d.arrow(o1x + ow / 2, gy + gh, o1x + ow / 2, oy - 2, EMERALD)
d.arrow(o2x + ow / 2, gy + gh, o2x + ow / 2, oy - 2, BLUE)


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
ROW_H = 36
lane_y = y0 + 70
header_h = 64
rows_y = lane_y + header_h + 14
steps_y = rows_y + len(d_rows) * ROW_H + 26
STEP_P = 23
lane_h = steps_y - lane_y + 28 + len(npu_steps) * STEP_P + 10
P2_H = lane_h + 90
d.panel(y0, P2_H, 2, "What does each Platform object set?",
        "Both classes fill the same names. Shared code reads PLATFORM.<name>; some code also checks PLATFORM.is_npu.")

kx = 46
nx, nw = 252, 322
sx = nx + nw + 14
sw_ = W - 46 - sx
d.lane(nx, lane_y, nw, lane_h, BLUE, "PlatformGPU  ·  NVIDIA SM100 GPUs",
       ["deepinfer/platform.py:55-83", "constructor sets only fp8_sf_type"])
d.lane(sx, lane_y, sw_, lane_h, EMERALD, "PlatformNPU  ·  Huawei Ascend 950 NPUs",
       ["deepinfer/platform.py:86-219", "constructor also changes the process (see below)"])
d.text(kx, lane_y + 23, "Name on Platform", 15, INK, "bold")
d.text(kx, lane_y + 41, "base class:", 11.5, MUTE)
d.text(kx, lane_y + 57, "platform.py:19-52", 11.5, MUTE)

for i, (k, v1, v2) in enumerate(d_rows):
    ry = rows_y + i * ROW_H
    if i:
        d.line(kx, ry - 13, sx + sw_ - 12, ry - 13, LINE, 0.8)
    d.text(kx, ry + 9, k, 12, INK, "bold", mono=True)
    d.text(nx + 12, ry + 9, v1, 12, INK, mono=True)
    d.text(sx + 12, ry + 9, v2, MS, INK, mono=True)

d.text(nx + 12, steps_y, "NVIDIA: no extra start-up steps", 12, BLUE, "bold", mono=True)
d.aside(nx + 12, steps_y + 28, [
    "PlatformGPU.__init__ imports torch and",
    "sets fp8_sf_type = torch.int32. Nothing else.",
    "",
    "The NCCL SM limit comes from the env var",
    "DEEPINFER_NCCL_NUM_SMS (default 32).",
], pitch=19)
d.text(sx + 12, steps_y, "Ascend only: extra start-up steps in __init__", 12, EMERALD, "bold", mono=True)
for i, s in enumerate(npu_steps):
    ry = steps_y + 28 + i * STEP_P
    d.badge(sx + 22, ry - 4, i + 1, EMERALD, r=9, size=11)
    d.text(sx + 38, ry, s, 12, INK, mono=True)

y = y0 + P2_H + 24
d.legend(30, y, [
    (VIOLET, "selection logic (deep_cluster, get_platform)"),
    (BLUE, "NVIDIA path"),
    (EMERALD, "Ascend path"),
    (NEUTRAL, "no accelerator found"),
])
y += 40
notes = []
for para in [
    "Simplified: the NCCL option names are config.max_ctas and config.min_ctas (platform.py:80-82). HCCL_CONNECT_TIMEOUT=240 and HCCL_EXEC_TIMEOUT=200 are "
    "defaults (setdefault); HCCL_BUFFSIZE=16, PYTORCH_NPU_ALLOC_CONF and TASK_QUEUE_ENABLE=0 always overwrite. Step 1 raises RuntimeError when CUDA_VISIBLE_DEVICES is set and differs.",
    "Not shown: TORCH_NPU_DEVICE_CAPABILITY=9.0 (a temporary torch_npu work-around, platform.py:117-118) and set_compile_mode(jit_compile=False).",
]:
    notes += wrap(para, 12, W - 70)
y = d.footnotes(30, y, notes)
d.save(height=y + 14)
