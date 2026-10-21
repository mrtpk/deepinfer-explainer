/* spec_decode.js - speculative decoding: accept / reject / residual (DeepInfer Explained).
 *
 * Mounts into <x-viz id="spec-decode">. Vanilla JS, no network, seeded and deterministic.
 * Rules copied from DeepInfer at commit 9bd9cf2 (simplified, toy vocabulary of 6 tokens):
 *   - row j checks draft j+1; the last row of a request is a fresh sample
 *     (csrc/engine/prepare_sample.cpp:220-225, tilelang_ops/sampler.py:13-25)
 *   - accept if min(1, q/p) > U, else sample from max(q - p, 0) normalized
 *     (tilelang_ops/fused_sample.py:227-246; DeepInfer uses max(q - alpha*p, 0), alpha = exp(-5e-5))
 *   - only the prefix before the first rejected row counts (tilelang_ops/sampler.py:243-247)
 *   - DSpark toggle: running product of confidences, then keep the drafts with the best
 *     expected tokens per unit of time (csrc/engine/mtp_varlen.hpp:150-267). Toy: one request,
 *     linear cost 4 + 1 * rows. The real code sorts all requests of the batch and uses a measured curve.
 * Left out: Markov dependence between drafts, temperature/top-p/top-k, the hash-based U.
 */
(function () {
  "use strict";

  var VIZ_ID = "spec-decode";
  var SEED = 20261022;
  var TOKENS = ["the", "cat", "sat", "on", "a", "mat"];
  var V = TOKENS.length;
  var NEXTN = 5;
  var COST_BASE = 4, COST_ROW = 1;   // toy cost: time = 4 + 1 * rows

  function mulberry32(a) {
    return function () {
      a |= 0; a = (a + 0x6d2b79f5) | 0;
      var t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function gauss(rng) {
    var u = 1 - rng(), v = rng();
    return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
  }
  function softmax(z) {
    var m = Math.max.apply(null, z), s = 0, out = [];
    for (var i = 0; i < z.length; i++) { out.push(Math.exp(z[i] - m)); s += out[i]; }
    return out.map(function (x) { return x / s; });
  }
  function draw(probs, u) {             // inverse CDF, like random_sampling_ref
    var s = 0, tot = 0, i;
    for (i = 0; i < probs.length; i++) tot += probs[i];
    for (i = 0; i < probs.length; i++) { s += probs[i]; if (s > u * tot) return i; }
    return probs.length - 1;
  }
  function f3(x) { return x.toFixed(3); }
  function f2(x) { return x.toFixed(2); }

  var CSS = [
    ".sd-root{font-family:var(--sans);color:var(--ink)}",
    ".sd-controls{display:flex;flex-wrap:wrap;gap:8px;align-items:center}",
    ".sd-toggle{display:flex;align-items:center;gap:8px;margin:10px 0 0;font-size:14px;min-height:40px;cursor:pointer}",
    ".sd-toggle input{width:20px;height:20px;margin:0;accent-color:var(--blue)}",
    ".sd-h{margin:14px 0 6px;font-size:13px;font-weight:700;color:var(--mute);text-transform:uppercase;letter-spacing:.03em}",
    ".sd-strip{display:flex;flex-wrap:wrap;gap:6px;margin:0;padding:0;list-style:none}",
    ".sd-chip{margin:0;min-width:72px;border:1.5px solid var(--line);border-radius:8px;padding:5px 8px;background:var(--surface);font-size:12.5px;line-height:1.35}",
    ".sd-chip b{display:block;font:700 14px var(--mono);color:var(--ink)}",
    ".sd-chip .sd-st{font-weight:600}",
    ".sd-chip.sd-real{border-color:var(--viz-c1)}",
    ".sd-chip.sd-acc{border-color:var(--emerald);background:var(--emerald-tint)}",
    ".sd-chip.sd-acc .sd-st{color:var(--emerald)}",
    ".sd-chip.sd-rej{border-color:var(--amber);background:var(--amber-tint)}",
    ".sd-chip.sd-rej .sd-st{color:var(--amber-text)}",
    ".sd-chip.sd-cur{outline:2px solid var(--ink);outline-offset:1px}",
    ".sd-chip.sd-off{border-style:dashed;opacity:.6}",
    ".sd-chip.sd-new{border-color:var(--viz-c4);background:var(--panel-bg)}",
    ".sd-conf{font:12px var(--mono);color:var(--mute)}",
    ".sd-charts{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:14px;margin-top:4px}",
    ".sd-chart{margin:0;border:1px solid var(--border);border-radius:8px;padding:8px 8px 6px;background:var(--surface);min-width:0}",
    ".sd-chart figcaption{font-size:13px;font-weight:700;margin-bottom:4px}",
    ".sd-bars{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:4px;align-items:end;height:118px}",
    ".sd-col{display:flex;flex-direction:column;justify-content:flex-end;align-items:stretch;height:100%;min-width:0}",
    ".sd-val{font:600 10.5px var(--mono);color:var(--mute);text-align:center;white-space:nowrap;margin-bottom:4px}",
    ".sd-bar{border-radius:3px 3px 0 0;min-height:1px}",
    ".sd-bar.sd-hl{outline:2px solid var(--ink);outline-offset:1px}",
    ".sd-lab{font:600 11.5px var(--mono);text-align:center;margin-top:3px;color:var(--ink);overflow:hidden;text-overflow:ellipsis}",
    ".sd-lab.sd-hl{text-decoration:underline;text-decoration-thickness:2px}",
    ".sd-calc{margin:10px 0 0;padding:8px 10px;border-radius:8px;background:var(--panel-bg);font:13px/1.6 var(--mono);overflow-wrap:anywhere;white-space:pre-wrap}",
    ".sd-calc .sd-ok{color:var(--emerald);font-weight:700}",
    ".sd-calc .sd-no{color:var(--amber-text);font-weight:700}",
    ".sd-sum{display:flex;flex-wrap:wrap;gap:6px;margin:12px 0 0;padding:0;list-style:none}",
    ".sd-sum li{margin:0;border-radius:6px;padding:4px 10px;background:var(--panel-bg);font-size:13px;color:var(--mute)}",
    ".sd-sum b{font:700 14px var(--mono);color:var(--ink);margin-left:4px}",
    ".sd-table{border-collapse:collapse;font:12.5px var(--mono);margin-top:4px;width:100%}",
    ".sd-table th,.sd-table td{border:1px solid var(--border);padding:3px 6px;text-align:right}",
    ".sd-table th{font-family:var(--sans);font-weight:600;color:var(--mute);text-align:left}",
    ".sd-table tr.sd-best td{background:var(--emerald-tint);font-weight:700}",
    ".sd-tablewrap{overflow-x:auto}",
    ".sd-live{margin:12px 0 0;font-size:14px;font-weight:600;min-height:1.5em}",
    ".sd-note{margin:6px 0 0;font-size:13px;color:var(--mute)}"
  ].join("\n");

  function injectStyle() {
    if (document.getElementById("sd-style")) return;
    var st = document.createElement("style");
    st.id = "sd-style";
    var P = ".viz-mount[data-viz='" + VIZ_ID + "'] ";
    st.textContent = CSS.split("\n").map(function (r) {
      return r.split("{")[0].split(",").map(function (s) { return P + s.trim(); }).join(",") + "{" + r.split("{").slice(1).join("{");
    }).join("\n");
    document.head.appendChild(st);
  }

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }
  function btn(label, primary) {
    var b = el("button", "viz-btn" + (primary ? " viz-btn-primary" : ""), label);
    b.type = "button";
    return b;
  }

  // ---- one round of drafts ---------------------------------------------------
  function makeRound(n) {
    var rng = mulberry32(SEED + n * 7919);
    var rows = [];
    for (var j = 0; j <= NEXTN; j++) {           // rows 0..4 check drafts; row 5 is the bonus row
      var z = [], zd = [];
      for (var i = 0; i < V; i++) z.push(gauss(rng) * 1.7);
      var sigma = 0.45 + 0.4 * j;                // later drafts are worse guesses
      for (i = 0; i < V; i++) zd.push(z[i] + gauss(rng) * sigma);
      var q = softmax(z), p = softmax(zd);
      var alpha = 0;
      for (i = 0; i < V; i++) alpha += Math.min(p[i], q[i]);
      rows.push({
        q: q, p: p, alpha: alpha,
        d: draw(p, rng()),                         // the draft token (draft model sample)
        u: rng(),                                  // U for the accept test
        v: rng(),                                  // number for the residual / bonus draw
        conf: Math.max(0.02, Math.min(0.98, alpha + (rng() - 0.5) * 0.24))
      });
    }
    var cum = [], r = 1;
    for (j = 0; j < NEXTN; j++) { r *= rows[j].conf; cum.push(r); }
    var best = 0, bestScore = -1, table = [];
    for (var k = 0; k <= NEXTN; k++) {
      var e = 1;
      for (j = 0; j < k; j++) e += cum[j];
      var t = COST_BASE + COST_ROW * (1 + k);
      table.push({ k: k, e: e, t: t, s: e / t });
      if (e / t > bestScore) { bestScore = e / t; best = k; }
    }
    return { n: n, rows: rows, cum: cum, table: table, bestK: best, last: TOKENS[Math.floor(rng() * V)] };
  }

  function Sim(mount) {
    this.mount = mount;
    this.dspark = false;
    this.build();
    this.reset();
  }

  Sim.prototype.build = function () {
    var m = this.mount, self = this;
    m.innerHTML = "";
    var root = el("div", "sd-root");
    var c = el("div", "sd-controls");
    this.bStep = btn("Check next draft", true);
    this.bRun = btn("Run to end");
    this.bNew = btn("New round");
    this.bReset = btn("Reset");
    [this.bStep, this.bRun, this.bNew, this.bReset].forEach(function (b) { c.appendChild(b); });
    root.appendChild(c);

    var lab = el("label", "sd-toggle");
    this.cb = document.createElement("input");
    this.cb.type = "checkbox";
    lab.appendChild(this.cb);
    lab.appendChild(el("span", null, "DSpark: confidence-scheduled length (simplified)"));
    root.appendChild(lab);

    root.appendChild(el("p", "sd-h", "Inputs of this step (last real token + drafts)"));
    this.strip = el("ul", "sd-strip");
    root.appendChild(this.strip);

    this.dsBox = el("div");
    root.appendChild(this.dsBox);

    this.chartHead = el("p", "sd-h", "");
    root.appendChild(this.chartHead);
    this.charts = el("div", "sd-charts");
    root.appendChild(this.charts);
    this.calc = el("div", "sd-calc");
    root.appendChild(this.calc);

    this.sum = el("ul", "sd-sum");
    root.appendChild(this.sum);
    this.live = el("p", "sd-live");
    this.live.setAttribute("aria-live", "polite");
    root.appendChild(this.live);
    root.appendChild(el("p", "sd-note", "Simplified model: 6-token vocabulary, independent toy distributions per row, seeded U. Pink = draft model p, blue = target model q, orange = residual."));
    m.appendChild(root);

    this.bStep.addEventListener("click", function () { self.step(); });
    this.bRun.addEventListener("click", function () {
      while (!self.done) self.step(true);
      self.render();
      var acc = self.status.filter(function (x) { return x === "acc"; }).length;
      self.say("Result: " + acc + " of " + self.L + " drafts accepted, then the " + (self.out.kind === "bonus" ? "bonus token" : "residual sample") +
        " “" + TOKENS[self.out.token] + "”. " + (acc + 1) + " tokens this step.");
    });
    this.bNew.addEventListener("click", function () { self.load(self.round.n + 1); self.say("New round " + (self.round.n + 1) + ": new drafts. Click Check next draft."); });
    this.bReset.addEventListener("click", function () { self.reset(); });
    this.cb.addEventListener("change", function () { self.dspark = self.cb.checked; self.load(self.round.n); self.say(self.dspark ? "DSpark on: the request sends only " + self.L + " of 5 drafts." : "DSpark off: the request sends all 5 drafts."); });
  };

  Sim.prototype.load = function (n) {
    this.round = makeRound(n);
    this.L = this.dspark ? this.round.bestK : NEXTN;   // number of drafts sent
    this.k = 0;              // next row to check
    this.status = [];        // per draft: "acc" | "rej" | null
    this.done = false;
    this.out = null;         // {kind, token}
    this.lastRow = -1;
    this.render();
  };

  Sim.prototype.reset = function () {
    this.load(0);
    this.say("Round 1. The draft model proposed 5 drafts" + (this.dspark ? "; DSpark sends " + this.L : "") + ". Click Check next draft.");
  };

  Sim.prototype.say = function (s) { this.live.textContent = s; };

  Sim.prototype.step = function (quiet) {
    if (this.done) return;
    var R = this.round, j = this.k;
    if (j >= this.L) {                                   // all sent drafts accepted: bonus row
      var row = R.rows[j];
      var tok = draw(row.q, row.v);
      this.out = { kind: "bonus", token: tok, row: j };
      this.done = true; this.lastRow = j;
      if (!quiet) { this.render(); this.say("All " + this.L + " drafts accepted. Row " + j + " samples the bonus token “" + TOKENS[tok] + "” from q. " + (this.L + 1) + " tokens this step."); }
      return;
    }
    var r = R.rows[j];
    var ratio = Math.min(1, r.q[r.d] / r.p[r.d]);
    this.lastRow = j;
    if (r.u < ratio) {
      this.status[j] = "acc"; this.k++;
      if (!quiet) { this.render(); this.say("Row " + j + ": draft " + (j + 1) + " “" + TOKENS[r.d] + "” accepted (U " + f3(r.u) + " < " + f3(ratio) + ")."); }
    } else {
      this.status[j] = "rej";
      var res = r.q.map(function (x, i) { return Math.max(x - r.p[i], 0); });
      var t2 = draw(res, r.v);
      this.out = { kind: "residual", token: t2, row: j, res: res };
      this.done = true;
      if (!quiet) { this.render(); this.say("Row " + j + ": draft " + (j + 1) + " rejected (U " + f3(r.u) + " ≥ " + f3(ratio) + "). The residual gives “" + TOKENS[t2] + "”. " + (j + 1) + " tokens this step."); }
    }
  };

  Sim.prototype.chart = function (title, probs, color, hl) {
    var fig = el("figure", "sd-chart");
    var cap = el("figcaption", null, title);
    cap.style.color = color;
    fig.appendChild(cap);
    var bars = el("div", "sd-bars");
    var mx = Math.max.apply(null, probs.concat([0.0001]));
    var sum = probs.reduce(function (a, b) { return a + b; }, 0) || 1;
    for (var i = 0; i < V; i++) {
      var col = el("div", "sd-col");
      var pv = probs[i] / sum;
      col.appendChild(el("span", "sd-val", f2(pv)));
      var b = el("div", "sd-bar" + (i === hl ? " sd-hl" : ""));
      b.style.height = Math.round(82 * probs[i] / mx) + "px";
      b.style.background = color;
      col.appendChild(b);
      bars.appendChild(col);
    }
    fig.appendChild(bars);
    var labs = el("div", "sd-bars");
    labs.style.height = "auto";
    for (i = 0; i < V; i++) labs.appendChild(el("span", "sd-lab" + (i === hl ? " sd-hl" : ""), TOKENS[i]));
    fig.appendChild(labs);
    fig.setAttribute("aria-label", title + ": " + TOKENS.map(function (t, i) { return t + " " + f2(probs[i] / sum); }).join(", "));
    return fig;
  };

  Sim.prototype.render = function () {
    var R = this.round, self = this;
    // strip
    this.strip.innerHTML = "";
    var li0 = el("li", "sd-chip sd-real");
    li0.appendChild(el("b", null, R.last));
    li0.appendChild(el("span", "sd-st", "last real token"));
    this.strip.appendChild(li0);
    for (var j = 0; j < NEXTN; j++) {
      var st = this.status[j];
      var sent = j < this.L;
      var cls = "sd-chip" + (st === "acc" ? " sd-acc" : st === "rej" ? " sd-rej" : "") + (!sent ? " sd-off" : "") +
        (!this.done && sent && j === this.k ? " sd-cur" : "");
      var li = el("li", cls);
      li.appendChild(el("b", null, TOKENS[R.rows[j].d]));
      var txt = !sent ? "not sent" : st === "acc" ? "accepted" : st === "rej" ? "rejected" : (this.done ? "dropped" : "draft " + (j + 1));
      li.appendChild(el("span", "sd-st", txt));
      if (this.dspark) li.appendChild(el("div", "sd-conf", "c " + f2(R.rows[j].conf)));
      this.strip.appendChild(li);
    }
    if (this.out) {
      var lo = el("li", "sd-chip sd-new");
      lo.appendChild(el("b", null, TOKENS[this.out.token]));
      lo.appendChild(el("span", "sd-st", this.out.kind === "bonus" ? "bonus token" : "residual sample"));
      this.strip.appendChild(lo);
    }

    // DSpark table
    this.dsBox.innerHTML = "";
    if (this.dspark) {
      this.dsBox.appendChild(el("p", "sd-h", "DSpark (toy): pick the number of drafts k with the best E / time"));
      var wrap = el("div", "sd-tablewrap");
      var tb = el("table", "sd-table");
      var hr = el("tr");
      ["k drafts", "running product of draft k", "E = expected tokens", "time = 4 + rows", "E / time"].forEach(function (h) { hr.appendChild(el("th", null, h)); });
      tb.appendChild(hr);
      R.table.forEach(function (t) {
        var tr = el("tr", t.k === R.bestK ? "sd-best" : null);
        [String(t.k), t.k ? f3(R.cum[t.k - 1]) : "-", f3(t.e), String(t.t), f3(t.s)].forEach(function (v) { tr.appendChild(el("td", null, v)); });
        tb.appendChild(tr);
      });
      wrap.appendChild(tb);
      this.dsBox.appendChild(wrap);
    }

    // charts for the current / last row
    var row = this.lastRow >= 0 ? this.lastRow : this.k;
    if (row > this.L) row = this.L;
    var r = R.rows[row];
    this.charts.innerHTML = "";
    var isBonusRow = row >= this.L;
    this.chartHead.textContent = isBonusRow ? "Row " + row + ": fresh sample (no draft to check)" : "Row " + row + ": checks draft " + (row + 1) + " “" + TOKENS[r.d] + "”";
    if (!isBonusRow) this.charts.appendChild(this.chart("draft model p", r.p, "var(--viz-c2)", r.d));
    this.charts.appendChild(this.chart("target model q", r.q, "var(--viz-c1)", isBonusRow ? (this.out ? this.out.token : -1) : r.d));
    if (this.out && this.out.kind === "residual" && this.out.row === row) {
      this.charts.appendChild(this.chart("residual max(q − p, 0), normalized", this.out.res, "var(--viz-c4)", this.out.token));
    }

    // calculation
    this.calc.innerHTML = "";
    if (isBonusRow) {
      this.calc.appendChild(el("div", null, this.out ? "All sent drafts passed. bonus = sample(q, v = " + f3(r.v) + ") → “" + TOKENS[this.out.token] + "”" :
        "All sent drafts passed. Click again to sample the bonus token from q."));
    } else {
      var ratio = Math.min(1, r.q[r.d] / r.p[r.d]);
      this.calc.appendChild(el("div", null, "p(" + TOKENS[r.d] + ") = " + f3(r.p[r.d]) + "   q(" + TOKENS[r.d] + ") = " + f3(r.q[r.d]) + "   min(1, q/p) = " + f3(ratio)));
      var line = el("div");
      if (this.status[row]) {
        line.appendChild(document.createTextNode("U = " + f3(r.u) + "  →  "));
        var s = el("span", this.status[row] === "acc" ? "sd-ok" : "sd-no", this.status[row] === "acc" ? "accept (U < min(1, q/p))" : "reject (U ≥ min(1, q/p))");
        line.appendChild(s);
      } else {
        line.textContent = "U = ?  (click Check next draft)";
      }
      this.calc.appendChild(line);
      if (this.out && this.out.kind === "residual" && this.out.row === row) {
        var Z = this.out.res.reduce(function (a, b) { return a + b; }, 0);
        this.calc.appendChild(el("div", null, "P(reject) = Σ max(q − p, 0) = " + f3(Z) + "   residual sample (v = " + f3(r.v) + ") → “" + TOKENS[this.out.token] + "”"));
      }
      this.calc.appendChild(el("div", null, "true accept chance of this row Σ min(p, q) = " + f3(r.alpha)));
    }

    // summary
    var acc = this.status.filter(function (x) { return x === "acc"; }).length;
    this.sum.innerHTML = "";
    [["rows sent", String(this.L + 1)], ["accepted drafts", String(acc)], ["tokens this step", this.done ? String(acc + 1) : "…"], ["round", String(R.n + 1)]]
      .forEach(function (kv) { var li = el("li", null, kv[0]); li.appendChild(el("b", null, kv[1])); self.sum.appendChild(li); });

    this.bStep.disabled = this.done;
    this.bRun.disabled = this.done;
    this.bStep.textContent = (!this.done && this.k >= this.L) ? "Sample bonus token" : "Check next draft";
  };

  function init() {
    var mounts = document.querySelectorAll('[data-viz="' + VIZ_ID + '"]');
    if (!mounts.length) return;
    injectStyle();
    for (var i = 0; i < mounts.length; i++) {
      if (mounts[i].getAttribute("data-viz-ready")) continue;
      mounts[i].setAttribute("data-viz-ready", "1");
      new Sim(mounts[i]);
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
