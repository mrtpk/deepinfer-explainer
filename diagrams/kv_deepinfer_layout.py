"""Diagram: what one DeepInfer KV block and one state slot hold (byte layout).

Used by: src/learn/kv-cache.html (deep dive)
Sources (commit 9bd9cf2):
  deepinfer/model_executor/model_metadata_utils.py:133-140    128 tokens per block, 128-byte alignment
  deepinfer/model_executor/layers/tilelang_ops/cache_common.py:109-128  V41 formats: 512 values, 528 B (MXFP8) / 288 B (FP4)
  deepinfer/hugging_face/config.py:302-303    HF loader default use_fp4_sparse_kv=True -> main cache 288 B (SWA stays 528 B)
  deepinfer/worker/cache_engine.py:123-127, 441-443   ica_state only without use_kproj; HF loader sets use_kproj=True (config.py:122)
  deepinfer/worker/cache_engine.py:205-218    KVCache fields and shapes
  deepinfer/worker/cache_engine.py:406-468    per-layer views: swa_cache, ica_cache, ca_cache
  deepinfer/worker/cache_engine.py:479-484    block total aligned to lcm(128, bytes_per_token)
  deepinfer/worker/cache_engine.py:41-43, 130-133   fp32 compression state, ring = ratio + backtracking - 1
  deepinfer/worker/cache_engine.py:88-93, 201-202   SWA ring = window + backtracking; slots = int(max_num_seqs * 1.2) + 1
  deepinfer/environ.py:129-132, 162           DEEPINFER_USE_NEXTN_DECODE=5, backtracking >= 6, slots ratio 1.2
  doc/inference_deployment_qa.md:163,169,191  window 128, 20 stored SWA layers, 134 tokens x 528 B
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, MUTE, NEUTRAL, VIOLET, WHITE, Diagram, text_width  # noqa: E402

d = Diagram(width=1100)
W = d.W
CX0, CX1 = 46, W - 46          # panel content x range


def wrap(s, size, maxw, mono=False, indent="  "):
    """Greedy word wrap; continuation lines are indented with two spaces."""
    out, cur = [], ""
    for w in s.split(" "):
        cand = (cur + " " + w) if cur else w
        if cur and text_width((indent if out else "") + cand, size, mono) > maxw:
            out.append(cur)
            cur = w
        else:
            cur = cand
    out.append(cur)
    return [out[0]] + [indent + t for t in out[1:]]


# header (drawn by hand: the parameter strip needs two lines at this width)
d.text(30, 42, "Inside DeepInfer's KV cache: one block and one state slot", 26, INK, "bold")
d.text(30, 68, "Byte layout of the two device buffers that CacheEngine allocates  ·  DeepSeek-V4.1 layer kinds  ·  commit 9bd9cf2",
       13.5, MUTE)
d.text(30, 90, "gpu_blocks: uint8 [num_gpu_blocks, bytes_per_block]      gpu_states: uint8 [num_state_slots, state_bytes]",
       12.5, MUTE, mono=True)
d.text(30, 108, "block_size = 128 tokens", 12.5, MUTE, mono=True)


def bar(y, segs, x0=CX0, x1=CX1, h=46):
    """Horizontal byte bar. segs: (label, sublabel, role, weight)."""
    total = sum(s[3] for s in segs)
    x = x0
    for label, sub, col, w in segs:
        ww = (x1 - x0) * w / total
        d.rect(x, y, ww - 3, h, fill=col[1], stroke=col[0], rx=4, sw=1.4)
        d.text(x + 10, y + 19, label, 14, MUTE if col is NEUTRAL else col[0], "bold")
        if sub:
            d.text(x + 10, y + 37, sub, 13, INK, mono=True)
        x += ww


CARD_PITCH = 19


def card(x, y, w, h, title, lines, col, tag=None):
    d.rect(x, y, w, h, fill=col[1], stroke=col[0], sw=1.5)
    d.text(x + 12, y + 24, title, 15, MUTE if col is NEUTRAL else col[0], "bold")
    for i, s in enumerate(lines):
        d.text(x + 12, y + 50 + i * CARD_PITCH, s, 12.5, INK, mono=True)
    if tag:
        tw = text_width(tag, 11, mono=True) + 20
        d.pill(x + w - 10 - tw, y + h - 29, tw, tag, MUTE if col is NEUTRAL else col[0])


# ============================================================================
# Panel 1: one KV block
# ============================================================================
y0 = 128
P1_H = 390
d.panel(y0, P1_H, 1, "What does one KV block hold? 128 tokens, for every layer that has a paged cache",
        "Block #b is one row of gpu_blocks. Each layer owns a fixed byte range in every row, so one block id serves all layers.")
d.text(46, y0 + 86, "gpu_blocks[b]  =  one row of bytes (layer ranges in layer order, each padded to 32 B)", 13, INK, "bold", mono=True)
bar(y0 + 98, [
    ("layer i (C1)", "ca", BLUE, 2.4),
    ("layer j (C2, sparse)", "ica | ca", VIOLET, 2.2),
    ("layer k (C2)", "ca", BLUE, 1.4),
    ("SWA-only layer", "0 B here", NEUTRAL, 1.6),
    ("…", "", NEUTRAL, 0.5),
    ("pad", "", NEUTRAL, 0.6),
])
cgap = 14
cy, ch, cw = y0 + 172, 196, (CX1 - CX0 - 2 * cgap) / 3
xs = [CX0, CX0 + cw + cgap, CX0 + 2 * (cw + cgap)]
card(xs[0], cy, cw, ch, "Main cache, ratio 1 (C1)", [
    "ca_cache[layer]:",
    "  uint8 [num_blocks, 128, 1, 288]",
    "1 entry per token, 512 values:",
    "  256 B FP4 data + 32 B scales",
    "= 128 × 288 = 36,864 B per block",
    "(FP8 option: 528 B → 67,584 B)",
], BLUE, "cache_engine.py:447-461")
card(xs[1], cy, cw, ch, "Ratio 2 (C2) and the indexer", [
    "ca_cache: [num_blocks, 64, 1, 288]",
    "1 entry per 2 tokens → 18,432 B",
    "ica_cache (sparse layers only):",
    "  [num_blocks, 64, 1, d/2 + d/32]",
    "  FP4 keys, d = index_head_dim",
    "Shared layers reuse another view.",
], VIOLET, "cache_engine.py:428-449")
card(xs[2], cy, cw, ch, "Row size and alignment", [
    "bytes_per_block = Σ layer ranges",
    "each range padded to 32 B",
    "row padded to lcm(128, 288)",
    "  = 1,152 B (FP4 main cache)",
    "Block 0 exists but is never used.",
    "Profile run sets num_gpu_blocks.",
], NEUTRAL, "cache_engine.py:479-484")

# ============================================================================
# Panel 2: one state slot
# ============================================================================
y1 = y0 + P1_H + 20
P2_H = 390
d.panel(y1, P2_H, 2, "What does one state slot hold? A fixed area per running sequence, not paged",
        "Slot s is one row of gpu_states. The sequence keeps it from start to end. Ring buffers overwrite old tokens.")
d.text(46, y1 + 86, "gpu_states[state_id]  =  [ stored region | dropped region ]   (StateBlock, cache_engine.py:221-241)", 13, INK, "bold", mono=True)
bar(y1 + 98, [
    ("stored: SWA rings", "one ring per stored SWA layer", EMERALD, 4.6),
    ("dropped: consumer SWA", "YOCO layers", EMERALD, 2.0),
    ("dropped: compression state", "fp32 ca_state", AMBER, 2.4),
    ("pad", "", NEUTRAL, 0.5),
])
cy = y1 + 172
card(xs[0], cy, cw, ch, "Sliding-window ring", [
    "uint8 [num_slots, 134, 1, 528]",
    "134 = window 128 + 6 backtrack",
    "token at pos p → ring row p % 134",
    "= 134 × 528 = 70,752 B per layer",
    "Doc: first 20 SWA layers are stored",
    "  → 1,415,040 B per sequence",
], EMERALD, "cache_engine.py:406-422")
card(xs[1], cy, cw, ch, "Compression state (C2 layers)", [
    "ca_state: fp32 [num_slots, 7, 2, 512]",
    "7 = ratio 2 + backtracking 6 − 1",
    "= 7 × 2 × 512 × 4 = 28,672 B",
    "Doc: boundary accumulators of",
    "  the compression window.",
    "ica_state: None (use_kproj=True)",
], AMBER, "cache_engine.py:441-465")
card(xs[2], cy, cw, ch, "How many slots?", [
    "num_slots = int(max_num_seqs × 1.2) + 1",
    "max_num_seqs 256 → 308 slots",
    "Slot 0 is never used (BlockManager",
    "  reserves index 0, as for blocks).",
    "No free slot → sequence waits.",
    "Fixed size: no growth per token.",
], NEUTRAL, "cache_engine.py:201-202")

y = y1 + P2_H + 24
d.legend(30, y, [
    (BLUE, "main compressed KV (ca_cache)"),
    (VIOLET, "indexer keys (ica_cache)"),
    (EMERALD, "sliding-window KV (swa_cache)"),
])
y += 26
d.legend(30, y, [
    (AMBER, "fp32 compression state"),
    (NEUTRAL, "no data / padding / reserved"),
], title=" " * 11)
y += 40
FN = []
for s in [
    "Main cache sizes use the HF loader default, FP4 with 288 B per entry (hugging_face/config.py:302-303). If config.json sets use_fp4_sparse_kv to false, an entry is 528 B (MXFP8). The SWA ring always uses 528 B.",
    "Byte widths in the two bars are not to scale. Which layer is C1, C2, sparse or SWA-only comes from the model config (attn_module_list), which is not in the repo.",
    "Defaults: DEEPINFER_USE_NEXTN_DECODE=5 → backtracking = max(value, 5 + 1) = 6 (environ.py:129-132); DEEPINFER_NUM_STATE_SLOTS_RATIO=1.2 (environ.py:162).",
    "Window 128 and the 20 stored layers are from doc/inference_deployment_qa.md:163,169,191. With DEEPINFER_PREFILL_STORE_EXTRA_STATE the rings are 128 tokens longer (plus the YOCO keep tokens if truncation is on).",
]:
    FN += wrap(s, 12, W - 70)
y = d.footnotes(30, y, FN)
d.save(height=y + 14)
