/* moe_router.js - MoE router + EPLB simulator (DeepInfer Explained, batch B7).
 *
 * Mounts into <x-viz id="moe-eplb">. Vanilla JS, no network, seeded and deterministic.
 * Toy sizes: 16 logical experts, 4 EP ranks, top-2, 64 tokens per step.
 * Rules copied from DeepInfer at commit 9bd9cf2:
 *   - extra slots: the lower bound is rounded up so that 16 + extra divides by the EP size
 *     (resolve_num_extra_experts, model_executor/eplb/__init__.py:21-28)
 *   - first layout: [0..15, then e % 16 for the extra slots] (eplb/__init__.py:31-39);
 *     slots split evenly over the ranks (v4_modules/mlp.py:199-205)
 *   - Rebalance = rebalance_experts_global (eplb/policy.py:73-140): greedy replication of the
 *     expert that most lowers sum_step max per-copy load (ties broken with + e * 1e-4), then
 *     _batch_greedy_indices (policy.py:12-70): copies in order of load, each to the rank with the
 *     lowest sum_step max(load + copy, peak); full ranks skipped; ties -> lowest rank id
 *   - moe_lb = sum over steps of the busiest rank / sum over steps of the mean rank
 *     (engine/stats_logger.py:238-241, eplb/__init__.py:189-193)
 * Simplified (labelled in the UI): one layer; the gate is replaced by seeded random choices from a
 * skewed popularity; the copies of an expert get its tokens in turn (the real choice is inside
 * the gate kernel); the window is "the steps since the last Rebalance" (at most 16).
 */
(function () {
  "use strict";

  var VIZ_ID = "moe-eplb";
  var L = 16;               // logical experts
  var R = 4;                // EP ranks
  var K = 2;                // top-k
  var T = 64;               // tokens per step
  var SKEW = 1.0;           // Zipf exponent of the popularity
  var MAX_WINDOW = 16;
  var SEED = 20261021;

  function mulberry32(a) {
    return function () {
      a |= 0; a = (a + 0x6d2b79f5) | 0;
      var t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  // ---- DeepInfer rules ------------------------------------------------------
  function resolveExtra(lower) {                       // eplb/__init__.py:21-28
    var pad = ((-(L + lower)) % R + R) % R;
    return lower + pad;
  }

  function initialLayout(extra) {                      // eplb/__init__.py:31-39
    var phy = [];
    for (var e = 0; e < L; e++) phy.push(e);
    for (var i = 0; i < extra; i++) phy.push(i % L);
    return phy;
  }

  function copyCounts(phy) {
    var c = []; for (var e = 0; e < L; e++) c.push(0);
    phy.forEach(function (e) { c[e]++; });
    return c;
  }

  // policy.py:12-70
  function batchGreedy(tok, phy, count, cap) {
    var S = tok.length, P = phy.length, nr = P / cap, s, r;
    var w = [];
    for (var e = 0; e < L; e++) { var sum = 0; for (s = 0; s < S; s++) sum += tok[s][e]; w.push(sum / count[e]); }
    var order = [];
    for (var p = 0; p < P; p++) order.push(p);
    order.sort(function (a, b) { var d = w[phy[b]] - w[phy[a]]; return d !== 0 ? d : a - b; });   // stable, descending
    var loads = [], peaks = [], occ = [], idx = new Array(P);
    for (r = 0; r < nr; r++) { loads.push(new Array(S).fill(0)); occ.push(0); }
    for (s = 0; s < S; s++) peaks.push(0);
    order.forEach(function (pp) {
      var ex = phy[pp], v = [];
      for (s = 0; s < S; s++) v.push(tok[s][ex] / count[ex]);
      var best = -1, bestScore = Infinity;
      for (r = 0; r < nr; r++) {
        if (occ[r] === cap) continue;
        var sc = 0;
        for (s = 0; s < S; s++) sc += Math.max(loads[r][s] + v[s], peaks[s]);
        if (sc < bestScore) { bestScore = sc; best = r; }
      }
      idx[best * cap + occ[best]] = pp;
      occ[best]++;
      for (s = 0; s < S; s++) { loads[best][s] += v[s]; peaks[s] = Math.max(peaks[s], loads[best][s]); }
    });
    return idx.map(function (k) { return phy[k]; });
  }

  // policy.py:73-140
  function rebalance(tok, P, cap) {
    var S = tok.length, extra = P - L, s, e, j;
    var count = []; for (e = 0; e < L; e++) count.push(1);
    var phy = []; for (e = 0; e < L; e++) phy.push(e);
    for (var i = 0; i < extra; i++) {
      var sums = new Array(L).fill(0);
      for (s = 0; s < S; s++) {
        var score = [];
        for (e = 0; e < L; e++) score.push((tok[s][e] + e * 1e-4) / count[e]);
        var m = 0;
        for (e = 1; e < L; e++) if (score[e] > score[m]) m = e;
        var mx = score[m];
        score[m] = tok[s][m] / (count[m] + 1);
        var nm = Math.max.apply(null, score);
        for (j = 0; j < L; j++) sums[j] += (j === m ? nm : mx);
      }
      var pick = 0;
      for (j = 1; j < L; j++) if (sums[j] < sums[pick]) pick = j;
      phy.push(pick);
      count[pick]++;
    }
    if (cap > 1) phy = batchGreedy(tok, phy, count, cap);
    return phy;
  }

  // ---- simulator ---------------------------------------------------------------
  function Sim(mount) {
    this.mount = mount;
    this.lower = 4;
    this.build();
    this.reset();
  }

  Sim.prototype.reset = function () {
    this.rng = mulberry32(SEED);
    this.extra = resolveExtra(this.lower);
    this.P = L + this.extra;
    this.cap = this.P / R;
    this.phy = initialLayout(this.extra);
    this.window = [];          // per step: tokens per logical expert
    this.rankHist = [];        // per step: rows per rank
    this.slotRows = new Array(this.P).fill(0);
    this.steps = 0;
    this.rebalances = 0;
    this.lastLb = null;
    this.predicted = null;
    this.makePopularity();
    this.say("Start: " + this.P + " slots (" + L + " experts + " + this.extra + " extra), " + this.cap + " per rank. Click Run 4 steps.");
    this.render();
  };

  Sim.prototype.makePopularity = function () {
    var perm = [];
    for (var e = 0; e < L; e++) perm.push(e);
    for (var i = L - 1; i > 0; i--) { var j = Math.floor(this.rng() * (i + 1)); var t = perm[i]; perm[i] = perm[j]; perm[j] = t; }
    this.pop = new Array(L);
    for (var r = 0; r < L; r++) this.pop[perm[r]] = 1 / Math.pow(r + 1, SKEW);
  };

  Sim.prototype.pick = function (w) {
    var tot = 0, i;
    for (i = 0; i < w.length; i++) tot += w[i];
    var x = this.rng() * tot;
    for (i = 0; i < w.length; i++) { x -= w[i]; if (x < 0) return i; }
    return w.length - 1;
  };

  Sim.prototype.runStep = function () {
    var tok = new Array(L).fill(0);
    var rows = new Array(R).fill(0);
    var copies = [];                                  // logical -> list of slots
    for (var e = 0; e < L; e++) copies.push([]);
    this.phy.forEach(function (ex, p) { copies[ex].push(p); });
    var turn = new Array(L).fill(0);
    var slotStep = new Array(this.P).fill(0);
    for (var t = 0; t < T; t++) {
      var w = this.pop.slice();
      for (var k = 0; k < K; k++) {
        var ex = this.pick(w);
        w[ex] = 0;                                    // k distinct experts
        tok[ex]++;
        var slot = copies[ex][turn[ex] % copies[ex].length];   // simplified copy choice
        turn[ex]++;
        slotStep[slot]++;
        rows[Math.floor(slot / this.cap)]++;
      }
    }
    this.window.push(tok);
    this.rankHist.push(rows);
    if (this.window.length > MAX_WINDOW) { this.window.shift(); this.rankHist.shift(); }
    this.slotRows = slotStep;
    this.steps++;
  };

  function lbOf(hist) {
    var mx = 0, mean = 0;
    hist.forEach(function (rows) {
      mx += Math.max.apply(null, rows);
      mean += rows.reduce(function (a, b) { return a + b; }, 0) / rows.length;
    });
    return mean > 0 ? mx / mean : 1;
  }

  // rank loads of a layout on the window, with tokens split evenly over copies (policy.py:31)
  Sim.prototype.predictLb = function (phy) {
    var cnt = copyCounts(phy), cap = this.cap;
    var hist = this.window.map(function (tok) {
      var rows = new Array(R).fill(0);
      phy.forEach(function (ex, p) { rows[Math.floor(p / cap)] += tok[ex] / cnt[ex]; });
      return rows;
    });
    return lbOf(hist);
  };

  Sim.prototype.run = function (n) {
    for (var i = 0; i < n; i++) this.runStep();
    this.lastLb = lbOf(this.rankHist);
    var last = this.rankHist[this.rankHist.length - 1];
    var busiest = last.indexOf(Math.max.apply(null, last));
    this.predicted = null;
    this.say("Ran " + n + " steps (step " + this.steps + "). moe_lb over the window: " + this.lastLb.toFixed(2) +
      ". Busiest rank in the last step: rank " + busiest + " with " + last[busiest] + " rows.");
    this.render();
  };

  Sim.prototype.rebalanceNow = function () {
    if (!this.window.length) { this.say("Run some steps first: the policy needs token counts."); this.render(); return; }
    var before = this.predictLb(this.phy);
    var next = rebalance(this.window, this.P, this.cap);
    var cap = this.cap, old = this.phy;
    // remote moves: (expert, rank) pairs where the rank did not hold the expert before (shuffle.py:28-44)
    var moves = 0;
    for (var r = 0; r < R; r++) {
      var had = {}, want = {};
      old.slice(r * cap, (r + 1) * cap).forEach(function (e) { had[e] = 1; });
      next.slice(r * cap, (r + 1) * cap).forEach(function (e) { want[e] = 1; });
      Object.keys(want).forEach(function (e) { if (!had[e]) moves++; });
    }
    this.phy = next;
    this.rebalances++;
    this.predicted = this.predictLb(next);
    var steps = this.window.length;
    this.window = []; this.rankHist = [];
    this.slotRows = new Array(this.P).fill(0);
    this.say("Rebalanced on " + steps + " steps. moe_lb on those steps: " + before.toFixed(2) + " before, " +
      this.predicted.toFixed(2) + " with the new layout. " + moves + " expert weights moved to other ranks. Run more steps to check.");
    this.render();
  };

  Sim.prototype.shift = function () {
    this.makePopularity();
    this.say("The hot experts changed. The layout stays the same until the next Rebalance.");
    this.render();
  };

  Sim.prototype.setLower = function (v) {
    this.lower = Math.max(0, Math.min(8, v));
    this.reset();
  };

  // ---- view ------------------------------------------------------------------
  var CSS = [
    ".mre-root{font-family:var(--sans);color:var(--ink)}",
    ".mre-controls{display:flex;flex-wrap:wrap;gap:8px;align-items:center}",
    ".mre-extra{display:flex;flex-wrap:wrap;align-items:center;gap:6px 10px;margin:12px 0 0;font-size:14.5px}",
    ".mre-extra .viz-btn{min-width:44px;padding:6px 10px;font:700 16px var(--mono)}",
    ".mre-extra b{font:700 15px var(--mono)}",
    ".mre-extra span{color:var(--mute)}",
    ".mre-stats{display:flex;flex-wrap:wrap;gap:6px;margin:12px 0 4px;padding:0;list-style:none}",
    ".mre-stats li{margin:0;border-radius:6px;padding:4px 10px;background:var(--panel-bg);font-size:13px;color:var(--mute);line-height:1.3}",
    ".mre-stats b{font:700 14px var(--mono);color:var(--ink);margin-left:4px}",
    ".mre-stats .mre-bad b{color:var(--amber-text)}",
    ".mre-stats .mre-good b{color:var(--emerald)}",
    ".mre-h{margin:14px 0 6px;font-size:13px;font-weight:700;color:var(--mute);text-transform:uppercase;letter-spacing:.03em}",
    ".mre-pop{display:grid;grid-template-columns:repeat(16,minmax(0,1fr));gap:3px;align-items:end;height:84px;margin:0;padding:0;list-style:none}",
    ".mre-pop li{margin:0;display:flex;flex-direction:column;justify-content:flex-end;align-items:center;height:100%;min-width:0}",
    ".mre-bar{width:100%;background:var(--blue);border-radius:2px 2px 0 0;min-height:2px}",
    ".mre-pop .mre-x2 .mre-bar{background:var(--emerald)}",
    ".mre-poplab{font:600 10.5px/1.3 var(--mono);color:var(--mute);white-space:nowrap}",
    ".mre-root:not(.mre-wide) .mre-poplab{font-size:8.5px;letter-spacing:-.03em}",
    ".mre-poplab b{color:var(--emerald)}",
    ".mre-ranks{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin:0;padding:0;list-style:none}",
    ".mre-wide .mre-ranks{grid-template-columns:repeat(4,minmax(0,1fr))}",
    ".mre-rank{margin:0;border:1px solid var(--border);border-radius:8px;padding:8px;background:var(--surface);min-width:0}",
    ".mre-rank.mre-hot{border-color:var(--amber);box-shadow:inset 0 0 0 1px var(--amber)}",
    ".mre-rtop{display:flex;justify-content:space-between;gap:6px;font-size:13.5px;font-weight:700}",
    ".mre-rtop span{font:600 13px var(--mono);color:var(--mute)}",
    ".mre-hot .mre-rtop span{color:var(--amber-text)}",
    ".mre-load{position:relative;height:10px;margin:6px 0 8px;border-radius:5px;background:var(--cell-empty);border:1px solid var(--line);overflow:hidden}",
    ".mre-load i{position:absolute;left:0;top:0;bottom:0;background:var(--blue)}",
    ".mre-hot .mre-load i{background:var(--amber)}",
    ".mre-slots{display:flex;flex-wrap:wrap;gap:4px}",
    ".mre-slot{font:600 12px/1 var(--mono);border:1.5px solid var(--line);border-radius:5px;padding:5px 5px;min-width:34px;text-align:center;background:var(--surface)}",
    ".mre-slot small{display:block;font-weight:400;font-size:10.5px;color:var(--mute);margin-top:2px}",
    ".mre-slot.mre-copy{border-color:var(--emerald);background:var(--emerald-tint)}",
    ".mre-note{margin:8px 0 0;font-size:13px;color:var(--mute)}",
    ".mre-log{margin:12px 0 0;border-top:1px solid var(--border);padding-top:8px}",
    ".mre-live{margin:0;font-size:14px;font-weight:600;min-height:1.5em}"
  ].join("\n");

  function injectStyle() {
    if (document.getElementById("mre-style")) return;
    var st = document.createElement("style");
    st.id = "mre-style";
    var P = ".viz-mount[data-viz='" + VIZ_ID + "'] ";
    st.textContent = CSS.split("\n").map(function (r) {
      return r.split("{")[0].split(",").map(function (s) {
        s = s.trim();
        return /^\.mre-(root|wide)\b/.test(s) ? P.trim() + s : P + s;
      }).join(",") + "{" + r.split("{").slice(1).join("{");
    }).join("\n");
    document.head.appendChild(st);
  }

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  function btn(label, cls, fn) {
    var b = el("button", "viz-btn" + (cls ? " " + cls : ""), label);
    b.type = "button";
    b.addEventListener("click", fn);
    return b;
  }

  Sim.prototype.build = function () {
    var self = this, m = this.mount;
    m.textContent = "";
    m.classList.add("mre-root");
    var c = el("div", "mre-controls");
    c.appendChild(btn("Run 4 steps", "viz-btn-primary", function () { self.run(4); }));
    c.appendChild(btn("Rebalance", "viz-btn-primary", function () { self.rebalanceNow(); }));
    c.appendChild(btn("Change hot experts", "", function () { self.shift(); }));
    c.appendChild(btn("Reset", "", function () { self.reset(); }));
    m.appendChild(c);

    var x = el("div", "mre-extra");
    x.appendChild(el("span", null, "DEEPINFER_OVERRIDE_NUM_EXTRA_EXPERTS:"));
    this.minus = btn("−", "", function () { self.setLower(self.lower - 1); });
    this.minus.setAttribute("aria-label", "Fewer extra experts");
    this.plus = btn("+", "", function () { self.setLower(self.lower + 1); });
    this.plus.setAttribute("aria-label", "More extra experts");
    this.lowerOut = el("b");
    this.resolvedOut = el("span");
    x.appendChild(this.minus); x.appendChild(this.lowerOut); x.appendChild(this.plus); x.appendChild(this.resolvedOut);
    m.appendChild(x);

    this.stats = el("ul", "mre-stats");
    m.appendChild(this.stats);

    m.appendChild(el("p", "mre-h", "Tokens per expert in the window (green: has an extra copy)"));
    this.popList = el("ul", "mre-pop");
    this.popList.setAttribute("aria-label", "Tokens per logical expert");
    m.appendChild(this.popList);

    m.appendChild(el("p", "mre-h", "EP ranks: rows received in the last step"));
    this.rankList = el("ul", "mre-ranks");
    m.appendChild(this.rankList);
    m.appendChild(el("p", "mre-note", "Each chip is one expert slot: the expert id, and the rows it got in the last step. Green chips hold an extra copy."));

    var log = el("div", "mre-log");
    this.live = el("p", "mre-live");
    this.live.setAttribute("aria-live", "polite");
    log.appendChild(this.live);
    m.appendChild(log);

    var check = function () { m.classList.toggle("mre-wide", m.clientWidth >= 640); };
    if (window.ResizeObserver) new ResizeObserver(check).observe(m); else window.addEventListener("resize", check);
    check();
  };

  Sim.prototype.say = function (msg) { this.msg = msg; };

  Sim.prototype.render = function () {
    var self = this, i;
    this.live.textContent = this.msg || "";
    this.lowerOut.textContent = String(this.lower);
    this.minus.disabled = this.lower <= 0;
    this.plus.disabled = this.lower >= 8;
    this.resolvedOut.textContent = "→ " + this.extra + " extra slots (16 + " + this.extra + " = " + this.P + " divides by " + R + ")";

    // stats
    this.stats.textContent = "";
    var add = function (label, val, cls) {
      var li = el("li", cls || null, label);
      li.appendChild(el("b", null, val));
      self.stats.appendChild(li);
    };
    add("steps", String(this.steps));
    add("window", this.window.length + " steps");
    add("slots per rank", String(this.cap));
    add("rebalances", String(this.rebalances));
    if (this.lastLb != null && this.window.length) add("moe_lb (window)", this.lastLb.toFixed(2), this.lastLb > 1.25 ? "mre-bad" : (this.lastLb < 1.15 ? "mre-good" : null));
    if (this.predicted != null) add("predicted after rebalance", this.predicted.toFixed(2), "mre-good");

    // popularity from the window
    var cnt = copyCounts(this.phy);
    var tot = new Array(L).fill(0);
    this.window.forEach(function (tok) { for (var e = 0; e < L; e++) tot[e] += tok[e]; });
    var mx = Math.max.apply(null, tot.concat([1]));
    this.popList.textContent = "";
    for (i = 0; i < L; i++) {
      var li = el("li", cnt[i] > 1 ? "mre-x2" : null);
      var bar = el("span", "mre-bar");
      bar.style.height = Math.round(60 * tot[i] / mx) + "px";
      li.appendChild(bar);
      var lab = el("span", "mre-poplab", "e" + i);
      if (cnt[i] > 1) { lab.appendChild(document.createElement("br")); lab.appendChild(el("b", null, "×" + cnt[i])); }
      li.appendChild(lab);
      li.setAttribute("aria-label", "expert " + i + ": " + tot[i] + " tokens, " + cnt[i] + " cop" + (cnt[i] > 1 ? "ies" : "y"));
      this.popList.appendChild(li);
    }

    // ranks
    var last = this.rankHist.length ? this.rankHist[this.rankHist.length - 1] : new Array(R).fill(0);
    var maxRows = Math.max.apply(null, last);
    var scale = Math.max(maxRows, (T * K / R) * 2);
    this.rankList.textContent = "";
    for (var r = 0; r < R; r++) {
      var hot = this.steps > 0 && last[r] === maxRows && maxRows > 0;
      var card = el("li", "mre-rank" + (hot ? " mre-hot" : ""));
      var top = el("div", "mre-rtop", "rank " + r);
      top.appendChild(el("span", null, last[r] + " rows" + (hot ? " (busiest)" : "")));
      card.appendChild(top);
      var load = el("div", "mre-load");
      var fill = el("i");
      fill.style.width = Math.round(100 * last[r] / scale) + "%";
      load.appendChild(fill);
      card.appendChild(load);
      var slots = el("div", "mre-slots");
      for (var k = 0; k < this.cap; k++) {
        var p = r * this.cap + k, ex = this.phy[p];
        var chip = el("span", "mre-slot" + (cnt[ex] > 1 ? " mre-copy" : ""), "e" + ex);
        chip.appendChild(el("small", null, String(this.slotRows[p] || 0)));
        chip.title = "slot " + p + ": expert " + ex;
        slots.appendChild(chip);
      }
      card.appendChild(slots);
      card.setAttribute("aria-label", "rank " + r + ": " + last[r] + " rows in the last step");
      this.rankList.appendChild(card);
    }
  };

  function init() {
    injectStyle();
    var mounts = document.querySelectorAll('[data-viz="' + VIZ_ID + '"]');
    for (var i = 0; i < mounts.length; i++) new Sim(mounts[i]);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
