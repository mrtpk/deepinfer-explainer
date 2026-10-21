"""Diagram: cross-layer KV sharing (share-KV, share-index-K, share-index) with an example config.

Used by: src/concepts/cross-layer-kv-sharing.html ("The picture"), src/code/v4-cross-layer.html ("Where it sits")
Sources (commit 9bd9cf2):
  deepinfer/hugging_face/config.py:62-85                              source id lists -> segment maps
  deepinfer/model_executor/models/v4_modules/cross_layer.py:143-155   normalized map, self-reference for missing layers
  deepinfer/model_executor/models/v4_modules/cross_layer.py:89-118    validation (segments, refinement, YOCO boundary)
  deepinfer/worker/cache_engine.py:406-465                            SWA per layer; ica_cache / ca_cache / ca_state only for sources
  deepinfer/model_executor/models/v4_modules/attn.py:345-364          Compressor only in KV source, MQA only in index source
  deepinfer/model_executor/models/v4_modules/cross_layer.py:276-336   CrossLayerRuntime fields
Example config (made up, not from a checkpoint): 8 main layers, compress_ratios [0,2,2,2,2,1,2,2],
  kv_source_layer_ids [1,3,5,6] (index-K sources default to the same list), index_source_layer_ids [1,2,3,5,6].
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, BORDER, EMERALD, GRAY_MID, INK, MUTE, VIOLET, WHITE, Diagram  # noqa: E402

d = Diagram(width=1100)
d.header(
    "Cross-layer KV sharing: which layer's cache does each layer read?",
    "Example config (made up)  ·  8 main layers  ·  a source owns the cache, its consumers read it",
    params="kv_source_layer_ids [1,3,5,6]   index_k sources = kv sources (loader default)   index_source_layer_ids [1,2,3,5,6]",
)

ratios = [0, 2, 2, 2, 2, 1, 2, 2]
kv_map = [0, 1, 1, 3, 3, 5, 6, 6]
ik_map = [0, 1, 1, 3, 3, 5, 6, 6]
ix_map = [0, 1, 2, 3, 3, 5, 6, 6]

# ============================================================================
# Panel 1: the maps
# ============================================================================
y0 = 112
P1_H = 382
d.panel(y0, P1_H, 1, "Which layer is the source of each value?",
        "\"own\" = the layer computes and stores the value. \"← n\" = the layer reads the value of layer n.")

LX = 46
LW = 214
CX0 = LX + LW
CWID, CHT, CG = 96, 34, 6
gy = y0 + 70
# column headers
for i in range(8):
    x = CX0 + i * (CWID + CG)
    d.text(x + CWID / 2, gy + 14, f"layer {i}", 13, INK, "bold", "middle", mono=True)

rows = [
    ("compress ratio", None, None),
    ("KV  (ca_cache)", kv_map, BLUE),
    ("index K  (ica_cache)", ik_map, EMERALD),
    ("top-k  (indexer)", ix_map, VIOLET),
    ("SWA ring", "own", AMBER),
]
for r, (label, mp, col) in enumerate(rows):
    ry = gy + 28 + r * (CHT + 10)
    d.text(LX, ry + 22, label, 13, INK if col is None else col[0], "bold")
    for i in range(8):
        x = CX0 + i * (CWID + CG)
        if mp is None:
            d.rect(x, ry, CWID, CHT, fill=WHITE, stroke=GRAY_MID, rx=4, sw=1)
            lab = {0: "0 (SWA)", 1: "1 (C1)", 2: "2 (C2)"}[ratios[i]]
            d.text(x + CWID / 2, ry + 22, lab, 12.5, INK, "bold", "middle", mono=True)
        elif mp == "own":
            d.rect(x, ry, CWID, CHT, fill=col[1], stroke=col, rx=4, sw=1.3)
            d.text(x + CWID / 2, ry + 22, "own", 12.5, col[0], "bold", "middle", mono=True)
        elif ratios[i] == 0:
            d.rect(x, ry, CWID, CHT, fill=BORDER, stroke=GRAY_MID, rx=4, sw=1)
            d.text(x + CWID / 2, ry + 22, "none", 12.5, MUTE, "bold", "middle", mono=True)
        elif mp[i] == i:
            d.rect(x, ry, CWID, CHT, fill=col[1], stroke=col, rx=4, sw=1.6)
            d.text(x + CWID / 2, ry + 22, "own", 12.5, col[0], "bold", "middle", mono=True)
        else:
            d.rect(x, ry, CWID, CHT, fill=WHITE, stroke=col, rx=4, sw=1.2, dash="4 3")
            d.text(x + CWID / 2, ry + 22, f"← {mp[i]}", 12.5, col[0], "bold", "middle", mono=True)

ny = gy + 28 + 5 * (CHT + 10) + 16
d.text(LX, ny, "Rules (checked at start-up): a segment is one source and the layers right after it. Each top-k segment lies inside one", 12.5, INK)
d.text(LX, ny + 19, "index-K segment, and each index-K segment inside one KV segment. Layer 5 is the first YOCO consumer, so it must be a KV source.", 12.5, INK)
d.text(LX, ny + 38, "Layer 0 has ratio 0: it has no compressed KV and no indexer. Every layer keeps its own SWA ring and its own query.", 12.5, MUTE)

# ============================================================================
# Panel 2: one forward
# ============================================================================
y1 = y0 + P1_H + 20
P2_H = 256
d.panel(y1, P2_H, 2, "How does a value get from layer 3 to layer 4 in one forward?",
        "Caches: the consumer gets the same tensor view. Per-step values: they go through one CrossLayerRuntime object.")

bw, bh, bg = 302, 136, 59
bx = [40, 40 + bw + bg, 40 + 2 * (bw + bg)]
by = y1 + 72


def big_box(x, title, lines, col):
    """Box with larger text than d.box: title sans 14.5 bold, mono lines 12.5, 18 px pitch."""
    d.rect(x, by, bw, bh, fill=col[1], stroke=col, sw=1.5)
    d.text(x + 10, by + 24, title, 14.5, col[0], "bold")
    for i, s in enumerate(lines):
        d.text(x + 10, by + 48 + i * 18, s, 12.5, INK, mono=True)


big_box(bx[0], "Layer 3: KV, index-K and index source",
        ["Compressor → writes ca_cache, ca_state", "KProject → writes ica_cache", "MQA indexer → topk_indices",
         "prefill: loads KV into a BF16 buffer", "attn.py:345-364"], BLUE)
big_box(bx[1], "CrossLayerRuntime (one per forward)",
        ["pre_rope_kv", "topk_indices", "loaded_prefill_kv (+ offset)", "loaded_prefill_index_kv",
         "cross_layer.py:276-336"], VIOLET)
big_box(bx[2], "Layer 4: consumer of all three",
        ["no Compressor, no indexer", "ca_cache, ica_cache = views of layer 3", "reads topk_indices",
         "prefill: reuses the KV buffer", "cache_engine.py:429-449"], EMERALD)
ay = by + bh / 2 + 10
d.arrow(bx[0] + bw + 2, ay, bx[1] - 3, ay, BLUE, sw=1.8)
d.text(bx[0] + bw + bg / 2, ay - 9, "write", 13, BLUE, "bold", "middle")
d.arrow(bx[1] + bw + 2, ay, bx[2] - 3, ay, VIOLET, sw=1.8)
d.text(bx[1] + bw + bg / 2, ay - 9, "read", 13, VIOLET, "bold", "middle")
d.text(40, by + bh + 28, "Layer 4 still computes its own query, its own SWA KV and its own attention output.", 13, MUTE)

y = y1 + P2_H + 22
d.legend(30, y, [(BLUE, "KV"), (EMERALD, "index K / consumer"), (VIOLET, "top-k / runtime"), (AMBER, "SWA (never shared)")])
y += 34
y = d.footnotes(30, y, [
    "Simplified: the candidate-block map (layer_candidate_source_map) is not shown. Source ids and ratios are example values;",
    "  the real ones come from the checkpoint's config.json and are not in the repo.",
])
d.save(height=y + 10)
