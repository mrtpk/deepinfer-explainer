"""Diagram: the EPLB rebalance policy on a worked example (6 experts, 2 extra slots, 2 ranks, 2 steps).

Used by: src/concepts/eplb.html, src/code/eplb.html
Sources (commit 9bd9cf2):
  deepinfer/model_executor/eplb/policy.py:73-140   rebalance_experts_global: greedy replication, then placement
  deepinfer/model_executor/eplb/policy.py:12-70    _batch_greedy_indices: placement objective sum_step max_rank load
  deepinfer/model_executor/eplb/__init__.py:31-39  initial layout [0..L-1, then e % L]
The numbers below are computed by a pure-Python copy of policy.py in this script (one layer).
It gives the same result as the five placement cases in tests/models/test_eplb_policy.py:97-117.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from svglib import AMBER, BLUE, EMERALD, INK, MUTE, VIOLET, WHITE, Diagram  # noqa: E402

# ---- pure-Python copy of policy.py (one layer) --------------------------------
TOK = [[48, 6, 10, 4, 24, 4], [40, 8, 12, 6, 28, 6]]   # [step][logical expert], the window
L, P, CAP = 6, 8, 4                                     # logical, physical slots, slots per rank
S = len(TOK)


def replicate():
    count = [1] * L
    phy = list(range(L))
    rounds = []
    diff = [[TOK[s][e] + e * 1e-4 for e in range(L)] for s in range(S)]
    for _ in range(P - L):
        sums = [0.0] * L
        for s in range(S):
            score = [diff[s][e] / count[e] for e in range(L)]
            m = max(range(L), key=lambda e: score[e])
            mx = score[m]
            score[m] = TOK[s][m] / (count[m] + 1)
            nm = max(score)
            for j in range(L):
                sums[j] += nm if j == m else mx
        r = min(range(L), key=lambda j: (sums[j], j))
        rounds.append(([round(x) for x in sums], r))
        phy.append(r)
        count[r] += 1
    return phy, count, rounds


def place(phy, count):
    w = [sum(TOK[s][e] for s in range(S)) / count[e] for e in range(L)]
    order = sorted(range(P), key=lambda p: -w[phy[p]])
    loads = [[0.0] * S for _ in range(P // CAP)]
    peaks = [0.0] * S
    occ = [0] * (P // CAP)
    idx = [None] * P
    jobs = []
    for p in order:
        e = phy[p]
        v = [TOK[s][e] / count[e] for s in range(S)]
        sc = [None if occ[r] == CAP else sum(max(loads[r][s] + v[s], peaks[s]) for s in range(S)) for r in range(P // CAP)]
        r = min((i for i in range(P // CAP) if sc[i] is not None), key=lambda i: (sc[i], i))
        idx[r * CAP + occ[r]] = p
        occ[r] += 1
        for s in range(S):
            loads[r][s] += v[s]
            peaks[s] = max(peaks[s], loads[r][s])
        jobs.append((e, v, sc, r))
    return [phy[k] for k in idx], jobs


def rank_loads(phy):
    cnt = [phy.count(e) for e in range(L)]
    return [[sum(TOK[s][phy[p]] / cnt[phy[p]] for p in range(r * CAP, (r + 1) * CAP)) for r in range(P // CAP)] for s in range(S)]


def lb(phy):
    ls = rank_loads(phy)
    return sum(max(x) for x in ls) / sum(sum(x) / len(x) for x in ls)


PHY0, COUNT, ROUNDS = replicate()
NEW, JOBS = place(PHY0, COUNT)
OLD = [0, 1, 2, 3, 4, 5, 0, 1]   # initial layout: eplb/__init__.py:31-39

# ---- drawing ------------------------------------------------------------------
d = Diagram(width=1100)
d.header(
    "EPLB policy: copy the hot experts, then place the copies",
    "rebalance_experts_global() in eplb/policy.py  ·  one MoE layer  ·  numbers computed with the same algorithm",
    params="6 logical experts   2 extra slots -> 8 slots   2 EP ranks x 4 slots   window = 2 steps",
)

y0 = 112
ROW = 21
P1_H = 76 + ROW * 3 + 30 + ROW * 3 + 24
d.panel(y0, P1_H, 1, "Step A: which experts get the extra slots?",
        "Each round copies the expert that most lowers the sum over steps of the largest per-copy load.")
ty = y0 + 82
d.text(46, ty, "tokens per expert", 12.5, MUTE, "bold")
for e in range(L):
    d.text(260 + e * 70, ty, f"e{e}", 12.5, MUTE, "bold", mono=True)
for s in range(S):
    d.text(46, ty + (s + 1) * ROW, f"step {s + 1}", 12.5, INK, mono=True)
    for e in range(L):
        d.text(260 + e * 70, ty + (s + 1) * ROW, f"{TOK[s][e]}", 12.5, INK, mono=True)
ty2 = ty + 3 * ROW + 16
d.text(46, ty2, "score if this expert", 12.5, MUTE, "bold")
d.text(46, ty2 + 16, "gets one more copy", 12.5, MUTE, "bold")
for i, (sums, r) in enumerate(ROUNDS):
    yy = ty2 + 16 + (i + 1) * ROW
    d.text(46, yy, f"round {i}", 12.5, INK, mono=True)
    for e in range(L):
        hit = e == r
        if hit:
            d.rect(252 + e * 70, yy - 15, 52, ROW - 2, fill=AMBER[1], stroke=AMBER, rx=4, sw=1.2)
        d.text(260 + e * 70, yy, f"{sums[e]}", 12.5, AMBER[0] if hit else INK, "bold" if hit else "normal", mono=True)
    d.text(700, yy, f"-> copy e{r} into slot {L + i}", 12.5, AMBER[0], "bold", mono=True)
d.text(700, ty2 + 16, "lower score = better", 12, MUTE, italic=True)
d.text(700, ty + 2 * ROW, f"copies: e0 x{COUNT[0]}, e4 x{COUNT[4]}, others x1", 12.5, INK, mono=True)

# ---- panel 2: placement --------------------------------------------------------
y0 = y0 + P1_H + 20
P2_H = 76 + ROW * (len(JOBS) + 1) + 20
d.panel(y0, P2_H, 2, "Step B: which rank gets each copy?",
        "Copies go in order of load. Each goes to the rank with the lowest score; a full rank is skipped; a tie picks rank 0.")
ty = y0 + 82
hdr = [(46, "order"), (110, "copy of"), (200, "load per step"), (360, "score rank 0"), (500, "score rank 1"), (640, "-> rank")]
for x, h in hdr:
    d.text(x, ty, h, 12.5, MUTE, "bold", mono=True)
for j, (e, v, sc, r) in enumerate(JOBS):
    yy = ty + (j + 1) * ROW
    d.text(46, yy, f"{j + 1}", 12.5, INK, mono=True)
    d.text(110, yy, f"e{e}", 12.5, INK, "bold", mono=True)
    d.text(200, yy, f"({v[0]:g}, {v[1]:g})", 12.5, INK, mono=True)
    for k in range(2):
        txt = "full" if sc[k] is None else f"{sc[k]:g}"
        d.text(360 + 140 * k, yy, txt, 12.5, VIOLET[0] if k == r else MUTE, "bold" if k == r else "normal", mono=True)
    d.text(640, yy, f"{r}", 12.5, VIOLET[0], "bold", mono=True)
ax = 740
d.text(ax, ty + ROW, "score(rank r) =", 12.5, INK, "bold")
d.text(ax, ty + 2 * ROW, "sum over steps of", 12.5, INK)
d.text(ax, ty + 3 * ROW, "max(load of r + this copy,", 12.5, INK, mono=True)
d.text(ax, ty + 4 * ROW, "    current peak)", 12.5, INK, mono=True)
d.text(ax, ty + 6 * ROW, "load per copy = tokens of", 12, MUTE, italic=True)
d.text(ax, ty + 7 * ROW, "the expert / its copy count", 12, MUTE, italic=True)

# ---- panel 3: before / after ----------------------------------------------------
y0 = y0 + P2_H + 20
CH = 34
P3_H = 76 + 2 * (CH + 40) + 8
d.panel(y0, P3_H, 3, "Result: the busiest rank gets less work",
        "moe_lb = sum over steps of the slowest rank / sum over steps of the mean rank (stats_logger.py:238-241).")


def layout_row(y, label, phy, col):
    d.text(46, y + 22, label, 13.5, INK, "bold")
    loads = rank_loads(phy)
    for r in range(2):
        x0 = 170 + r * 380
        d.text(x0, y - 6, f"rank {r}   load {loads[0][r]:g} / {loads[1][r]:g}", 12.5, MUTE, mono=True)
        for k in range(CAP):
            e = phy[r * CAP + k]
            x = x0 + k * 84
            hot = e in (0, 4)
            d.rect(x, y, 76, CH, fill=col[1] if hot else WHITE, stroke=col, rx=6, sw=1.4)
            d.text(x + 38, y + 22, f"e{e}", 13, col[0] if hot else INK, "bold", "middle", mono=True)
    d.text(940, y + 22, f"moe_lb {lb(phy):.3f}", 13.5, col[0], "bold", mono=True)


ry = y0 + 92
layout_row(ry, "before", OLD, BLUE)
layout_row(ry + CH + 40, "after", NEW, EMERALD)

y = y0 + P3_H + 22
d.legend(30, y, [(AMBER, "replication (step A)"), (VIOLET, "placement (step B)"), (BLUE, "old layout"), (EMERALD, "new layout")])
y += 38
y = d.footnotes(30, y, [
    "Loads assume that the tokens of an expert split evenly over its copies, as the policy and the EPLB log do (policy.py:31, eplb/__init__.py:298).",
    "The policy starts from 1 copy per expert every time. It does not look at the old layout. Step A adds e x 1e-4 to each count, so no two scores are equal.",
    "Moves for this example: e4 and e5 go to rank 0, e3 goes to rank 1. The other slots keep their weights (shuffle.py).",
])
d.save(height=y + 10)
