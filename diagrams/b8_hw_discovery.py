"""Diagram: deep_cluster hardware discovery: the decision, the derived values, and who calls it when.

Used by: src/concepts/hardware-discovery.html (also src/code/deep-cluster.html)
Sources (commit 9bd9cf2):
  deep_cluster/hardware/device.py:17-23        accelerator_kind: ascend first, then nvidia, else cpu
  deep_cluster/hardware/ascend.py:61-68        Ascend signals
  deep_cluster/hardware/nvidia.py:18-48        NVIDIA signals (/proc/driver/nvidia/gpus, /dev/nvidiaN)
  deep_cluster/hardware/device.py:26-43        device count, visible-device variable
  deep_cluster/hardware/nvidia.py:55-79        NUMA from /sys/bus/pci/devices/<bus>/numa_node
  deep_cluster/hardware/ascend.py:107-144      NUMA from npu-smi topo + lscpu, else ubcore numa
  deep_cluster/hardware/device.py:151-164      BF16 TFLOPS limit, SM major 10 through NVML
  setup.py:10-12, deepinfer/__init__.py:9-25, examples/_config.py:55-63, deepinfer/platform.py:222-227
  deepinfer/worker/base.py:182-191, 347-357    _bind_numa, set_device, bind_cpu
  deepinfer/utils.py:143-151                   bind_cpu: physical cores per device
  deepinfer/engine/llm_engine.py:298-305       tflops_limit for the statistics
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, MUTE, NEUTRAL, TEAL, VIOLET, WHITE, Diagram  # noqa: E402

d = Diagram(width=1100)
d.header(
    "deep_cluster: find the accelerator without PyTorch",
    "deep_cluster/hardware and deep_cluster/topology  ·  reads files and small system tools only  ·  commit 9bd9cf2",
    params="accelerator_kind() -> \"ascend\" | \"nvidia\" | \"cpu\"   (cached once per process)",
)

# ---------------------------------------------------------------------------
# Panel 1: the decision
# ---------------------------------------------------------------------------
y0 = 112
BW, BH, GAP = 316, 150, 30
P1_H = 72 + BH + 30
d.panel(y0, P1_H, 1, "Which accelerator does this host have?",
        "The first test that finds a device wins. Ascend is tested first.")
by = y0 + 72
boxes = [
    ("1. Ascend?  -> \"ascend\"", AMBER, [
        "/dev/davinci_manager exists",
        "or a /dev/davinci<N> file",
        "or /sys/class/ubcore/udma*/",
        "   device/ub_totalues > 0",
        "ascend.py:61-68",
    ]),
    ("2. NVIDIA?  -> \"nvidia\"", EMERALD, [
        "a folder in",
        "  /proc/driver/nvidia/gpus/",
        "  (one per GPU, PCI bus id)",
        "or a /dev/nvidia<N> file",
        "nvidia.py:40-48",
    ]),
    ("3. else  -> \"cpu\"", NEUTRAL, [
        "no device found",
        "count 0, no visible-device var",
        "get_platform() still makes",
        "  PlatformGPU (platform.py:226)",
        "device.py:23",
    ]),
]
for i, (title, col, lines) in enumerate(boxes):
    bx = 46 + i * (BW + GAP)
    d.rect(bx, by, BW, BH, fill=col[1], stroke=col, sw=1.5)
    d.text(bx + 14, by + 24, title, 14, col[0] if col is not NEUTRAL else INK, "bold", mono=True)
    for j, s in enumerate(lines):
        last = j == len(lines) - 1
        d.text(bx + 14, by + 50 + j * 19, s, 12 if not last else 11.5, INK if not last else MUTE, mono=True)
    if i < 2:
        ax = bx + BW
        d.arrow(ax, by + BH / 2, ax + GAP - 2, by + BH / 2, INK)
        d.text(ax + GAP / 2, by + BH / 2 - 8, "no", 11.5, INK, "bold", "middle")

# ---------------------------------------------------------------------------
# Panel 2: derived values
# ---------------------------------------------------------------------------
y1 = y0 + P1_H + 20
rows = [
    ("physical_device_count()", "ubcore devices with UEs, else davinci<N>", "entries in /proc/.../gpus, else nvidia<N>", "0"),
    ("visible_device_env_name()", "ASCEND_RT_VISIBLE_DEVICES", "CUDA_VISIBLE_DEVICES", "None"),
    ("device_numa_node(i)", "npu-smi topo + lscpu; else ubcore numa", "/sys/bus/pci/devices/<bus>/numa_node", "IndexError"),
    ("get_bf16_tflops_limit()", "432", "2250 (x86) / 2500 (Arm), SM 10.x only", "RuntimeError"),
]
RH = 34
TX = [46, 270, 580, 900]
P2_H = 72 + 30 + len(rows) * RH + 24
d.panel(y1, P2_H, 2, "What else does it compute from the same files?",
        "Every value follows the kind from panel 1. NVIDIA reads the compute capability through NVML, with no CUDA context.")
hy = y1 + 72
for x, h, col in zip(TX, ("function", "ascend", "nvidia", "cpu"), (INK, AMBER, EMERALD, MUTE)):
    d.text(x + 6, hy + 16, h, 13, col, "bold")
d.line(46, hy + 26, 1054, hy + 26, INK, sw=1)
for i, (fn, a, n, c) in enumerate(rows):
    ry = hy + 30 + i * RH
    if i % 2 == 0:
        d.rect(46, ry, 1008, RH, fill=WHITE, stroke=None, rx=0)
    d.text(TX[0] + 6, ry + 22, fn, 12, INK, "bold", mono=True)
    d.text(TX[1] + 6, ry + 22, a, 11.5, INK, mono=True)
    d.text(TX[2] + 6, ry + 22, n, 11.5, INK, mono=True)
    d.text(TX[3] + 6, ry + 22, c, 11.5, INK, mono=True)

# ---------------------------------------------------------------------------
# Panel 3: who calls it, and when
# ---------------------------------------------------------------------------
y2 = y1 + P2_H + 20
CARD_H = 50
CARD_GAP = 12
steps = [
    ("build: setup.py", "IS_NPU = accelerator_kind() == \"ascend\" -> NPU or CUDA extension", "setup.py:10-12", VIOLET),
    ("launcher: examples/_config.py", "picks devices, sets CUDA_VISIBLE_DEVICES before import deepinfer", "_config.py:55-63", BLUE),
    ("import deepinfer", "_so/<accelerator>-<arch> tag; accelerator_kind() only if the env var is empty", "__init__.py:15-25", BLUE),
    ("first use of PLATFORM", "PlatformNPU if \"ascend\", else PlatformGPU", "platform.py:222-227", BLUE),
    ("worker start-up", "_bind_numa(local_rank) -> torch.cuda.set_device -> bind_cpu(gpu_id)", "base.py:182-191", TEAL),
    ("engine start-up", "get_bf16_tflops_limit() x 2 = FP8 peak for the MFU statistic", "llm_engine.py:298-305", TEAL),
]
P3_H = 72 + len(steps) * (CARD_H + CARD_GAP) - CARD_GAP + 22
d.panel(y2, P3_H, 3, "Who calls deep_cluster, and when?",
        "Blue steps run before the device runtime starts. Teal steps run later, in the worker or engine process.")
cy = y2 + 72
for i, (title, row, cite, col) in enumerate(steps):
    d.rect(46, cy, 1008, CARD_H, fill=col[1], stroke=col, sw=1.4)
    d.rect(46, cy, 6, CARD_H, fill=col[0], stroke=None, rx=3)
    d.badge(70, cy + 17, i + 1, col, r=10, size=11)
    d.text(88, cy + 22, title, 13.5, INK, "bold")
    d.text(88, cy + 40, row, 12, INK, mono=True)
    d.pill_auto(1054 - 10 - (len(cite) * 11 * 0.602 + 20), cy + 8, cite, col[0])
    if i < len(steps) - 1:
        d.arrow(70, cy + CARD_H, 70, cy + CARD_H + CARD_GAP - 2, col)
    cy += CARD_H + CARD_GAP

y = y2 + P3_H + 22
d.legend(30, y, [(AMBER, "Ascend"), (EMERALD, "NVIDIA"), (NEUTRAL, "no accelerator"),
                 (VIOLET, "build time"), (BLUE, "before device init"), (TEAL, "worker / engine")])
y += 38
y = d.footnotes(30, y, [
    "Not shown: the multimodal worker binds itself too, from visible index 0 (multimodal_processor.py:173-191); kernel tests bind",
    "  each pytest-xdist worker to a GPU with get_actual_num_gpus() (tilelang_ops/conftest.py:30-44).",
    "get_actual_num_gpus() counts physical devices on the host, not the visible ones (device.py:139-140).",
])
d.save(height=y + 10)
