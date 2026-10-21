"""Diagram: zero-overhead scheduling (ZOS) - the device idle gap without ZOS, the overlap with ZOS,
and what the device must correct because the CPU is one step behind.

Used by: src/concepts/zero-overhead-scheduling.html
Sources (commit 9bd9cf2):
  doc/inference_deployment_qa.md:270-274        the problem (GPU idle in post-process + schedule) and the overlap
  deepinfer/worker/worker.py:113-189            forward N -> post-process N-1 -> sample N -> keep N (ZOS) or post-process N now
  deepinfer/worker/worker.py:259-263            post-process waits on sample_end_evt of its step
  csrc/engine/scheduler.hpp:697, 726            seqlen_k = num_tokens + in-flight + seqlen_q; then in-flight += nextn + 1
  csrc/engine/zos.cpp:188                       seqlens_k sent to the device = seqlen_k - seqlen_q
  deepinfer/model_executor/layers/tilelang_ops/compute_seqlens_k_zos.py:18-23   k += q - (nextn - accepted)
  deepinfer/model_executor/layers/tilelang_ops/gather_input_ids_zos.py:21-29    input ids from step N outputs
Panels 1 and 2 use toy times (schedule+prepare 2, post-process 1.5, forward 4, sample 1); the order of the
phases follows worker.py. Panel 3 uses request A of the tours: 50 tokens, 49 in the cache, 2 of 5 drafts accepted.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, MUTE, NEUTRAL, VIOLET, WHITE, Diagram  # noqa: E402

d = Diagram(width=1100)
W = d.W
d.header(
    "Zero-overhead scheduling: the CPU works one step ahead",
    "One decode step = CPU schedule + prepare, device forward + sample, CPU post-process  ·  toy times  ·  commit 9bd9cf2",
    params="toy units: schedule+prepare 2 · post-process 1.5 · forward 4 · sample 1",
)

X0 = 176          # x of time 0
U = 47            # px per time unit
LANE_H = 34


def tx(t):
    return X0 + t * U


def blk(t0, t1, y, label, col, dash=None, idle=False):
    x0, x1 = tx(t0), tx(t1)
    if idle:
        d.rect(x0 + 1, y, x1 - x0 - 2, LANE_H, fill=NEUTRAL[2], stroke=NEUTRAL[0], rx=4, sw=1.2, dash="4 3")
        d.text((x0 + x1) / 2, y + LANE_H / 2 + 4.5, label, 12, MUTE, "normal", "middle", italic=True)
    else:
        d.rect(x0 + 1, y, x1 - x0 - 2, LANE_H, fill=col[1], stroke=col, rx=4, sw=1.4, dash=dash)
        d.text((x0 + x1) / 2, y + LANE_H / 2 + 4.5, label, 12.5, col, "bold", "middle", mono=True)


def lanes(y, end_t):
    d.text(46, y + 22, "CPU", 13.5, INK, "bold")
    d.text(46, y + LANE_H + 14 + 22, "device", 13.5, INK, "bold")
    d.line(X0, y + 2 * LANE_H + 26, tx(end_t), y + 2 * LANE_H + 26, MUTE, 1)
    for t in range(0, int(end_t) + 1, 2):
        d.line(tx(t), y + 2 * LANE_H + 22, tx(t), y + 2 * LANE_H + 30, MUTE, 1)
        d.text(tx(t), y + 2 * LANE_H + 44, str(t), 11, MUTE, anchor="middle", mono=True)


# ============================================================================
# Panel 1: without ZOS
# ============================================================================
y0 = 112
P1_H = 200
d.panel(y0, P1_H, 1, "Without ZOS: why does the device wait?",
        "The CPU waits for sample N, then post-processes N and schedules N+1. The device has no work in that time.")
ly = y0 + 70
lanes(ly, 18)
cpu_y, dev_y = ly, ly + LANE_H + 14
# step 1
blk(0, 2, cpu_y, "S1", BLUE)
blk(2, 6, dev_y, "F1", EMERALD)
blk(6, 7, dev_y, "s1", AMBER)
blk(7, 8.5, cpu_y, "P1", VIOLET)
blk(8.5, 10.5, cpu_y, "S2", BLUE)
blk(10.5, 14.5, dev_y, "F2", EMERALD)
blk(14.5, 15.5, dev_y, "s2", AMBER)
blk(15.5, 17, cpu_y, "P2", VIOLET)
blk(0, 2, dev_y, "idle", None, idle=True)
blk(7, 10.5, dev_y, "idle 3.5", None, idle=True)
blk(15.5, 17, dev_y, "idle", None, idle=True)
d.text(tx(17) + 10, cpu_y + 22, "2 steps", 12.5, INK, "bold")
d.text(tx(17) + 10, dev_y + 22, "in 17", 12.5, MUTE)

# ============================================================================
# Panel 2: with ZOS
# ============================================================================
y1 = y0 + P1_H + 20
P2_H = 200
d.panel(y1, P2_H, 2, "With ZOS: what does the CPU do while the device runs?",
        "It schedules and prepares N+1 and post-processes N-1. The device runs one step after the other.")
ly = y1 + 70
lanes(ly, 18)
cpu_y, dev_y = ly, ly + LANE_H + 14
blk(0, 2, cpu_y, "S1", BLUE)
blk(2, 4, cpu_y, "S2", BLUE)
blk(4, 7, cpu_y, "wait", None, idle=True)
blk(7, 8.5, cpu_y, "P1", VIOLET)
blk(8.5, 10.5, cpu_y, "S3", BLUE)
blk(10.5, 12, cpu_y, "wait", None, idle=True)
blk(12, 13.5, cpu_y, "P2", VIOLET)
blk(13.5, 15.5, cpu_y, "S4", BLUE)
blk(15.5, 17, cpu_y, "wait", None, idle=True)
blk(0, 2, dev_y, "idle", None, idle=True)
blk(2, 6, dev_y, "F1", EMERALD)
blk(6, 7, dev_y, "s1", AMBER)
blk(7, 11, dev_y, "F2", EMERALD)
blk(11, 12, dev_y, "s2", AMBER)
blk(12, 16, dev_y, "F3", EMERALD)
blk(16, 17, dev_y, "s3", AMBER)
d.text(tx(17) + 10, cpu_y + 22, "3 steps", 12.5, INK, "bold")
d.text(tx(17) + 10, dev_y + 22, "in 17", 12.5, MUTE)

# ============================================================================
# Panel 3: what the device corrects
# ============================================================================
y2 = y1 + P2_H + 20
P3_H = 204
d.panel(y2, P3_H, 3, "What must the device correct?",
        "The CPU schedules N+1 before it knows how many drafts N accepted. A kernel fixes the length; the inputs come from N.")
by = y2 + 70
bw, bh = 316, 100
xs = [46, 392, 738]
d.box(xs[0], by, bw, bh, "1  CPU guess (scheduler)", [
    "cache 49 · in flight 6 · q 6",
    "seqlen_k = 49 + 6 + 6 = 61",
    "sent to device: 61 - 6 = 55",
    "scheduler.hpp:697 · zos.cpp:188",
], col=BLUE, align="start", mono_size=12)
d.box(xs[1], by, bw, bh, "2  device fix (seqlens_k)", [
    "step N accepted 2 of 5 drafts",
    "k = 55 + 6 - (5 - 2) = 58",
    "real: 52 cached + 6 new = 58",
    "compute_seqlens_k_zos.py:18-23",
], col=EMERALD, align="start", mono_size=12)
d.box(xs[2], by, bw, bh, "3  device inputs (input_ids)", [
    "[r, e1, e2, e3, e4, e5]",
    "r: token sampled in step N",
    "e1..e5: drafts made in step N",
    "gather_input_ids_zos.py:21-29",
], col=AMBER, align="start", mono_size=12)
d.arrow(xs[0] + bw, by + bh / 2, xs[1] - 2, by + bh / 2, BLUE)
d.arrow(xs[1] + bw, by + bh / 2, xs[2] - 2, by + bh / 2, EMERALD)
d.text(46, by + bh + 20, "Without ZOS the CPU knows the result of step N before it schedules N+1, so nothing needs a correction.",
       12, MUTE, italic=True)

y = y2 + P3_H + 22
d.legend(30, y, [(BLUE, "S: schedule + prepare (CPU)"), (VIOLET, "P: post-process (CPU)"),
                 (EMERALD, "F: forward (device)"), (AMBER, "s: sample (device)")])
y += 34
y = d.footnotes(30, y, [
    "Toy times. Real times depend on the batch, the model and the CPU. The order of the phases follows worker.py:113-189.",
    "Simplified: launch costs, the launch of the sampler (after P) and DP all-reduces are not drawn. The first ZOS step has nothing to post-process.",
])
d.save(height=y + 10)
