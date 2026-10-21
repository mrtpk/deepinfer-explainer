"""Diagram: CacheEngine - who makes the two cache buffers at start-up, and how KVCacheManager.process()
cuts one block row and one state row into per-layer views (worked example with a toy 3-layer config).

Used by: src/code/cache-engine.html
Sources (commit 9bd9cf2):
  deepinfer/engine/llm_engine.py:437, 453     _init_cache: profile, then init_cache_engine on every rank
  deepinfer/worker/base.py:211-268            profile_num_available_blocks (2 x state reserved, mean over ranks)
  deepinfer/worker/model_runner.py:498-511    profile_run: temporary CacheEngine(num_gpu_blocks=num_blocks), zeroed
  deepinfer/worker/base.py:270-272            init_cache_engine -> CacheEngine(...); gpu_cache
  deepinfer/worker/cache_engine.py:918-966    allocate_gpu_cache: gpu_blocks, gpu_states, GPUCacheInterface
  deepinfer/worker/cache_engine.py:376-477    process(): SWA view, index K view, main view, fp32 state
  deepinfer/worker/cache_engine.py:479-484    finalize(): row padded to lcm(128, bytes_per_token)
  deepinfer/worker/cache_engine.py:41-43, 88-93, 130-133, 201-202   state bytes, ring sizes, slot count
Toy config (example values, not from the repo): 3 layers; L0 SWA only; L1 ratio 1 with indexer
(index_head_dim 128 -> 68 B per entry); L2 ratio 2 dense; all three have a sliding window of 128;
FP4 main entry 288 B; SWA entry 528 B; nextn 5 -> backtracking 6.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, MUTE, NEUTRAL, VIOLET, WHITE, Diagram  # noqa: E402

d = Diagram(width=1100)
W = d.W
d.header(
    "CacheEngine: two raw buffers, many per-layer views",
    "Start-up order (top) and the byte layout that process() gives each layer (bottom)  ·  commit 9bd9cf2",
    params="gpu_blocks uint8 [num_gpu_blocks, bytes_per_block]   ·   gpu_states uint8 [num_state_slots, bytes_per_slot]",
)

# ============================================================================
# Panel 1: start-up flow
# ============================================================================
y0 = 112
P1_H = 330
d.panel(y0, P1_H, 1, "Who makes the cache, and when?",
        "A temporary cache serves the profile run. Then every rank makes the real CacheEngine with the agreed block count.")
bw, bh = 316, 96
xs = [46, 392, 738]
r1 = y0 + 72
r2 = r1 + bh + 44
d.box(xs[0], r1, bw, bh, "1  profile_num_available_blocks", [
    "LLMEngine._init_cache, line 437",
    "base.py:211-268",
    "on every rank",
], col=BLUE, align="start", mono_size=12)
d.box(xs[1], r1, bw, bh, "2  profile_run", [
    "temporary CacheEngine",
    "num_gpu_blocks = blocks of dummies",
    "zero_(), run once, then freed",
], col=BLUE, align="start", mono_size=12)
d.box(xs[2], r1, bw, bh, "3  how many blocks?", [
    "free = total*util - peak",
    "free -= 2 * state bytes",
    "mean over ranks, even",
], col=BLUE, align="start", mono_size=12)
d.box(xs[0], r2, bw, bh, "4  init_cache_engine", [
    "LLMEngine._init_cache, line 453",
    "CacheEngine(cache_config, cfg,",
    "            max_num_seqs)",
], col=VIOLET, align="start", mono_size=12)
d.box(xs[1], r2, bw, bh, "5  allocate_gpu_cache", [
    "cuMemAlloc (not torch)",
    "gpu_blocks [blocks, row bytes]",
    "gpu_states [slots, slot bytes]",
], col=VIOLET, align="start", mono_size=12)
d.box(xs[2], r2, bw, bh, "6  GPUCacheInterface", [
    "_kvcache_layout: for each layer",
    "KVCacheManager.process()",
    "cache_list[i] = KVCache(views)",
], col=VIOLET, align="start", mono_size=12)
for a, b in ((0, 1), (1, 2)):
    d.arrow(xs[a] + bw, r1 + bh / 2, xs[b] - 2, r1 + bh / 2, BLUE)
    d.arrow(xs[a] + bw, r2 + bh / 2, xs[b] - 2, r2 + bh / 2, VIOLET)
d.path_arrow(f"M {xs[2] + bw / 2},{r1 + bh} L {xs[2] + bw / 2},{r1 + bh + 22} L {xs[0] + bw / 2},{r1 + bh + 22} L {xs[0] + bw / 2},{r2 - 2}", BLUE)
d.text(xs[1] + bw / 2, r1 + bh + 16, "cache_config.num_gpu_blocks", 11.5, BLUE, "bold", "middle", mono=True)

# ============================================================================
# Panel 2: byte layout
# ============================================================================
y1 = y0 + P1_H + 20
P2_H = 300
d.panel(y1, P2_H, 2, "Where does each layer find its bytes?",
        "process() walks the layers in order and moves two offsets: one in the block row, one in the state row.")
BX, BWID = 46, 1008


def bar(y, total, segs, title):
    d.text(BX, y - 10, title, 12.5, INK, "bold")
    x = BX
    for nbytes, label, col in segs:
        w = BWID * nbytes / total
        fill = col[1] if isinstance(col, tuple) else WHITE
        d.rect(x, y, w, 40, fill=fill, stroke=col, rx=3, sw=1.3)
        if w > 70:
            d.text(x + w / 2, y + 17, label, 12, col if isinstance(col, str) else col[0], "bold", "middle", mono=True)
            d.text(x + w / 2, y + 33, f"{nbytes:,} B", 11.5, INK, "normal", "middle", mono=True)
        x += w
    return x


r = y1 + 88
bar(r, 64512, [
    (8704, "L1 ica_cache", VIOLET),
    (36864, "L1 ca_cache (128 x 288)", BLUE),
    (18432, "L2 ca_cache (64 x 288)", BLUE),
    (512, "", NEUTRAL),
], "one row of gpu_blocks = one block for all layers: 64,512 B (64,000 padded to a multiple of lcm(128, 288) = 1,152)")
r2 = r + 100
bar(r2, 241296, [
    (70752, "L0 swa_cache", EMERALD),
    (70752, "L1 swa_cache", EMERALD),
    (70752, "L2 swa_cache", EMERALD),
    (28672, "L2 ca_state", AMBER),
    (368, "", NEUTRAL),
], "one row of gpu_states = one state slot: 241,296 B (240,928 padded to a multiple of lcm(32, 528) = 528)")
d.text(BX, r2 + 64, "swa: (128 + 6) x 528 = 70,752 B per layer   ·   ca_state: fp32 [7, 2, 512] = 28,672 B (ring 2 + 6 - 1 = 7)   ·   L0 uses no block bytes",
       12, MUTE, mono=False)

y = y1 + P2_H + 22
d.legend(30, y, [(BLUE, "main KV (paged)"), (VIOLET, "indexer keys (paged)"), (EMERALD, "SWA ring (state)"),
                 (AMBER, "fp32 compression state")])
y += 34
y = d.footnotes(30, y, [
    "Toy config: layer kinds, index_head_dim 128 and the window 128 are example values; the formulas are the code's (cache_engine.py:376-484).",
    "Bars are to scale inside each row; the two rows use different scales. Shared layers (layer maps) add no bytes and are not shown.",
])
d.save(height=y + 10)
