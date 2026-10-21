/* attention_toy.js - interactive "attention toy" for learn/attention (DeepInfer Explained).
 *
 * Mounts into <x-viz id="attention-toy">. Vanilla JS, no network, deterministic (fixed example vectors).
 * The model: one attention head, 6 tokens, head size d_h = 2.
 *   scores  S[i][j] = m * (q_i . k_j) / sqrt(d_h)      (m = the "sharpness" slider; m = 1 is the real rule)
 *   mask    S[i][j] = -inf for j > i                    (causal mask; the checkbox can turn it off)
 *   weights W[i]    = softmax(S[i])                     (max subtracted first, as real kernels do)
 *   output  o_i     = sum_j W[i][j] * v_j
 * Rows 1-4 use the same keys and values as the worked example on learn/kv-cache and learn/attention.
 * DeepInfer differences (see the page): many heads, head_dim 512, one shared KV head (MLA), an index list
 * instead of a mask, and an attention sink value per head (v4_modules/attn.py, layers/attention_backend.py).
 */
(function () {
  "use strict";

  var VIZ_ID = "attention-toy";
  var TOKENS = ["The", "cat", "sat", "on", "the", "mat"];
  var Q0 = [[1, 0], [0, 1], [0, 2], [1, 2], [2, 0], [0, 1]];
  var K0 = [[1, 0], [0, 1], [1, 1], [2, 1], [1, 0], [0, 2]];
  var V0 = [[2, 0], [0, 2], [1, 1], [0, 3], [2, 0], [1, 3]];
  var DH = 2;
  var START_ROW = 3;      // "on", as in the worked example
  var START_EDIT = 1;     // edit the key of "cat"

  function clone(a) { return a.map(function (r) { return r.slice(); }); }
  function fmt(x, n) {
    if (x === -Infinity) return "−∞";
    var s = x.toFixed(n == null ? 2 : n);
    if (/^-0\.0+$/.test(s)) s = s.slice(1);
    return s.replace("-", "−");
  }
  function vec(v) { return "(" + fmt(v[0], v[0] % 1 ? 2 : 0) + ", " + fmt(v[1], v[1] % 1 ? 2 : 0) + ")"; }

  var CSS = [
    ".att-root{font-family:var(--sans);color:var(--ink)}",
    ".att-intro{margin:0 0 10px;font-size:14.5px;color:var(--mute)}",
    ".att-toks{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 6px;padding:0;list-style:none}",
    ".att-toks li{margin:0}",
    ".att-tok{min-width:58px;font-family:var(--mono);font-size:14px}",
    ".att-tok[aria-pressed='true']{border-color:var(--blue);color:var(--blue);background:var(--blue-tint);font-weight:700;box-shadow:inset 0 0 0 1px var(--blue)}",
    ".att-controls{display:grid;grid-template-columns:minmax(0,1fr);gap:10px 18px;margin:12px 0 4px;padding:10px 12px;border:1px solid var(--border);border-radius:8px;background:var(--panel-bg)}",
    ".att-wide .att-controls{grid-template-columns:repeat(2,minmax(0,1fr))}",
    ".att-ctl{display:flex;flex-direction:column;gap:4px;min-width:0;font-size:14px}",
    ".att-ctl label,.att-ctl .att-lab{font-weight:600;color:var(--ink)}",
    ".att-ctl small{color:var(--mute);font-size:12.5px;line-height:1.35}",
    ".att-row{display:flex;flex-wrap:wrap;align-items:center;gap:6px 10px}",
    ".att-root input[type=range]{flex:1 1 140px;min-width:120px;height:32px;accent-color:var(--blue)}",
    ".att-root input[type=checkbox]{width:20px;height:20px;margin:0;accent-color:var(--blue)}",
    ".att-root select{min-height:36px;font:14px var(--mono);color:var(--ink);background:var(--surface);border:1px solid var(--line);border-radius:6px;padding:2px 6px}",
    ".att-val{font:700 14px var(--mono);min-width:3.2em}",
    ".att-check{display:inline-flex;align-items:center;gap:8px;min-height:36px;cursor:pointer;font-weight:600}",
    ".att-body{display:grid;grid-template-columns:minmax(0,1fr);gap:18px;margin-top:12px}",
    ".att-wide .att-body{grid-template-columns:minmax(0,1fr) minmax(0,1fr)}",
    ".att-h{margin:0 0 6px;font-size:13px;font-weight:700;color:var(--mute);text-transform:uppercase;letter-spacing:.03em}",
    ".att-gridwrap{overflow-x:auto}",
    ".att-grid{border-collapse:separate;border-spacing:3px;margin:0;font-family:var(--mono);font-size:12.5px;table-layout:fixed}",
    ".att-grid th{font-weight:600;color:var(--mute);padding:0 2px;text-align:center;white-space:nowrap}",
    ".att-grid th.att-rowh{text-align:right;padding-right:6px}",
    ".att-grid thead th{font-size:12px}",
    ".att-grid td{width:44px;height:34px;padding:0;text-align:center;vertical-align:middle;border-radius:4px;border:1px solid var(--line);font-variant-numeric:tabular-nums}",
    ".att-grid td.att-masked{background:repeating-linear-gradient(135deg,var(--cell-empty),var(--cell-empty) 4px,var(--border) 4px,var(--border) 6px);color:var(--mute)}",
    ".att-grid tr.att-sel td{border-color:var(--blue);border-width:2px}",
    ".att-grid tr.att-sel th{color:var(--blue);font-weight:700}",
    ".att-grid th button{all:unset;cursor:pointer;padding:6px 2px;border-radius:4px}",
    ".att-grid th button:focus-visible{outline:2px solid var(--blue);outline-offset:1px}",
    ".att-key{font-size:12.5px;color:var(--mute);margin:6px 0 0}",
    ".att-tab{width:100%;border-collapse:collapse;font-size:13px;margin:0}",
    ".att-tab th,.att-tab td{padding:4px 6px;border-bottom:1px solid var(--border);text-align:right;white-space:nowrap;font-family:var(--mono)}",
    ".att-tab th:first-child,.att-tab td:first-child{text-align:left}",
    ".att-tab th{font-family:var(--sans);font-weight:600;color:var(--mute);font-size:12.5px}",
    ".att-tab tr.att-off td{color:var(--mute)}",
    ".att-tabwrap{overflow-x:auto}",
    ".att-mix{display:flex;height:30px;margin:10px 0 4px;border-radius:6px;overflow:hidden;border:1px solid var(--line)}",
    ".att-mix span{display:block;min-width:0;height:100%}",
    ".att-legend{display:flex;flex-wrap:wrap;gap:4px 12px;margin:0;padding:0;list-style:none;font-size:12.5px}",
    ".att-legend li{margin:0;display:inline-flex;align-items:center;gap:5px;font-family:var(--mono)}",
    ".att-sw{display:inline-block;width:12px;height:12px;border-radius:3px}",
    ".att-out{margin:10px 0 0;font-size:14.5px}",
    ".att-out b{font-family:var(--mono)}",
    ".att-live{margin:12px 0 0;padding-top:8px;border-top:1px solid var(--border);font-size:14px;font-weight:600;min-height:1.5em}",
    ".att-note{margin:6px 0 0;font-size:13px;color:var(--mute)}"
  ];

  function injectStyle() {
    if (document.getElementById("att-style")) return;
    var st = document.createElement("style");
    st.id = "att-style";
    var P = ".viz-mount[data-viz='" + VIZ_ID + "'] ";
    st.textContent = CSS.map(function (r) {
      var sel = r.split("{")[0], rest = r.slice(sel.length);
      return sel.split(",").map(function (s) {
        s = s.trim();
        return /^\.att-(root|wide)\b/.test(s) ? P.trim() + s : P + s;
      }).join(",") + rest;
    }).join("\n");
    document.head.appendChild(st);
  }

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  // colour helpers: blend var(--blue) into var(--surface) and pick a readable text colour
  function parseColor(s) {
    s = (s || "").trim();
    var m = /^#([0-9a-f]{6})$/i.exec(s);
    if (m) return [parseInt(m[1].slice(0, 2), 16), parseInt(m[1].slice(2, 4), 16), parseInt(m[1].slice(4, 6), 16)];
    m = /^#([0-9a-f]{3})$/i.exec(s);
    if (m) return [0, 1, 2].map(function (i) { return parseInt(m[1][i] + m[1][i], 16); });
    m = /rgba?\(([^)]+)\)/.exec(s);
    if (m) return m[1].split(",").slice(0, 3).map(function (x) { return parseFloat(x); });
    return null;
  }
  function lum(c) {
    var a = c.map(function (v) { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); });
    return 0.2126 * a[0] + 0.7152 * a[1] + 0.0722 * a[2];
  }

  function Toy(mount) {
    this.mount = mount;
    this.build();
    this.reset();
  }

  Toy.prototype.reset = function () {
    this.Q = clone(Q0); this.K = clone(K0); this.V = clone(V0);
    this.row = START_ROW;
    this.m = 1;
    this.causal = true;
    this.view = "weights";
    this.edit = START_EDIT;
    this.sharp.value = "1";
    this.causalBox.checked = true;
    this.viewSel.value = "weights";
    this.editSel.value = String(START_EDIT);
    this.syncEditSliders();
    this.render();
    this.say("Reset. Row \"on\" is selected: it is the worked example from the page.");
  };

  Toy.prototype.compute = function () {
    var T = TOKENS.length, S = [], Wt = [], O = [], raw = [];
    var scale = this.m / Math.sqrt(DH);
    for (var i = 0; i < T; i++) {
      var r = [], rr = [];
      for (var j = 0; j < T; j++) {
        var dot = this.Q[i][0] * this.K[j][0] + this.Q[i][1] * this.K[j][1];
        rr.push(dot);
        r.push(this.causal && j > i ? -Infinity : dot * scale);
      }
      var mx = Math.max.apply(null, r), sum = 0;
      var e = r.map(function (x) { var v = x === -Infinity ? 0 : Math.exp(x - mx); sum += v; return v; });
      var w = e.map(function (x) { return x / sum; });
      var o = [0, 0];
      for (var k = 0; k < T; k++) { o[0] += w[k] * this.V[k][0]; o[1] += w[k] * this.V[k][1]; }
      S.push(r); Wt.push(w); O.push(o); raw.push(rr);
    }
    return { S: S, W: Wt, O: O, raw: raw, scale: scale };
  };

  Toy.prototype.build = function () {
    var m = this.mount, self = this;
    m.textContent = "";
    m.classList.add("att-root");
    m.appendChild(el("p", "att-intro",
      "Click a token to see what it looks at. Each row of the grid is one query token; each column is one key token."));

    var toks = el("ul", "att-toks");
    toks.setAttribute("aria-label", "Query token");
    this.tokBtns = TOKENS.map(function (t, i) {
      var li = el("li"), b = el("button", "viz-btn att-tok", t);
      b.type = "button";
      b.setAttribute("aria-pressed", "false");
      b.setAttribute("aria-label", "Query token " + (i + 1) + ": " + t);
      b.addEventListener("click", function () { self.select(i); });
      li.appendChild(b); toks.appendChild(li);
      return b;
    });
    m.appendChild(toks);

    var ctr = el("div", "att-controls");
    // sharpness slider
    var c1 = el("div", "att-ctl");
    var id1 = "att-sharp-" + (Toy.n = (Toy.n || 0) + 1);
    var l1 = el("label", null, "Sharpness m (scores × m)"); l1.htmlFor = id1;
    var r1 = el("div", "att-row");
    this.sharp = el("input"); this.sharp.type = "range"; this.sharp.id = id1;
    this.sharp.min = "0"; this.sharp.max = "4"; this.sharp.step = "0.25";
    this.sharpVal = el("span", "att-val");
    this.sharp.addEventListener("input", function () { self.m = parseFloat(self.sharp.value); self.render(); self.announceRow(); });
    r1.appendChild(this.sharp); r1.appendChild(this.sharpVal);
    c1.appendChild(l1); c1.appendChild(r1);
    c1.appendChild(el("small", null, "m = 1 is the real rule (scale 1/√d_h). m = 0 gives equal weights; a large m gives almost all weight to the best key."));
    ctr.appendChild(c1);

    // edit one key
    var c2 = el("div", "att-ctl");
    var id2 = "att-edit-" + Toy.n;
    var l2 = el("label", null, "Edit the key of"); l2.htmlFor = id2;
    this.editSel = el("select"); this.editSel.id = id2;
    TOKENS.forEach(function (t, i) { var o = el("option", null, (i + 1) + " " + t); o.value = String(i); self.editSel.appendChild(o); });
    this.editSel.addEventListener("change", function () { self.edit = parseInt(self.editSel.value, 10); self.syncEditSliders(); self.render(); });
    var top = el("div", "att-row"); top.appendChild(l2); top.appendChild(this.editSel);
    c2.appendChild(top);
    this.kSl = [0, 1].map(function (c) {
      var row = el("div", "att-row");
      var lid = "att-k" + c + "-" + Toy.n;
      var lab = el("label", null, "k[" + c + "]"); lab.htmlFor = lid;
      lab.style.fontFamily = "var(--mono)";
      var s = el("input"); s.type = "range"; s.id = lid; s.min = "-2"; s.max = "3"; s.step = "0.5";
      var v = el("span", "att-val");
      s.addEventListener("input", function () {
        self.K[self.edit][c] = parseFloat(s.value);
        self.render();
        self.say("Key of \"" + TOKENS[self.edit] + "\" is now " + vec(self.K[self.edit]) + ". " + self.rowSummary());
      });
      row.appendChild(lab); row.appendChild(s); row.appendChild(v);
      c2.appendChild(row);
      return { s: s, v: v };
    });
    ctr.appendChild(c2);

    // causal mask + view
    var c3 = el("div", "att-ctl");
    var lab3 = el("label", "att-check");
    this.causalBox = el("input"); this.causalBox.type = "checkbox";
    this.causalBox.addEventListener("change", function () {
      self.causal = self.causalBox.checked; self.render();
      self.say(self.causal ? "Causal mask on: a token sees only itself and earlier tokens." :
        "Causal mask off: every token also sees later tokens. A decoder LLM never does this.");
    });
    lab3.appendChild(this.causalBox); lab3.appendChild(document.createTextNode("Causal mask (hide later tokens)"));
    c3.appendChild(lab3);
    ctr.appendChild(c3);

    var c4 = el("div", "att-ctl");
    var id4 = "att-view-" + Toy.n;
    var l4 = el("label", null, "Grid shows"); l4.htmlFor = id4;
    this.viewSel = el("select"); this.viewSel.id = id4;
    [["weights", "weights (after softmax)"], ["scores", "scaled scores (before softmax)"]].forEach(function (o) {
      var op = el("option", null, o[1]); op.value = o[0]; self.viewSel.appendChild(op);
    });
    this.viewSel.addEventListener("change", function () { self.view = self.viewSel.value; self.render(); });
    var r4 = el("div", "att-row"); r4.appendChild(l4); r4.appendChild(this.viewSel);
    c4.appendChild(r4);
    var rb = el("button", "viz-btn", "Reset"); rb.type = "button";
    rb.addEventListener("click", function () { self.reset(); });
    c4.appendChild(rb);
    ctr.appendChild(c4);
    m.appendChild(ctr);

    var body = el("div", "att-body");
    var left = el("div");
    this.gridTitle = el("p", "att-h");
    left.appendChild(this.gridTitle);
    var gw = el("div", "att-gridwrap");
    this.grid = el("table", "att-grid");
    gw.appendChild(this.grid);
    left.appendChild(gw);
    left.appendChild(el("p", "att-key", "Rows: query tokens (click a name). Columns: key tokens. Striped: masked (a later token)."));
    var right = el("div");
    this.rowTitle = el("p", "att-h");
    right.appendChild(this.rowTitle);
    var tw = el("div", "att-tabwrap");
    this.tab = el("table", "att-tab");
    tw.appendChild(this.tab);
    right.appendChild(tw);
    this.mix = el("div", "att-mix");
    this.mix.setAttribute("aria-hidden", "true");
    right.appendChild(this.mix);
    this.mixLegend = el("ul", "att-legend");
    right.appendChild(this.mixLegend);
    this.out = el("p", "att-out");
    right.appendChild(this.out);
    body.appendChild(left); body.appendChild(right);
    m.appendChild(body);

    this.live = el("p", "att-live");
    this.live.setAttribute("aria-live", "polite");
    this.live.setAttribute("role", "status");
    m.appendChild(this.live);
    m.appendChild(el("p", "att-note",
      "Simplified model: one head, d_h = 2, fixed made-up vectors. The page lists what DeepInfer does differently."));

    var fit = function () {
      m.classList.toggle("att-wide", m.clientWidth >= 700);
      var nar = m.clientWidth < 520;
      if (nar !== self.narrow) { self.narrow = nar; if (self.Q) self.render(); }
    };
    fit();
    if (window.ResizeObserver) new ResizeObserver(fit).observe(m); else window.addEventListener("resize", fit);
    if (window.MutationObserver) {
      new MutationObserver(function () { self.render(); })
        .observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme", "class"] });
    }
  };

  Toy.prototype.syncEditSliders = function () {
    var k = this.K[this.edit];
    this.kSl.forEach(function (o, c) { o.s.value = String(k[c]); });
  };

  Toy.prototype.select = function (i) {
    this.row = i;
    this.render();
    this.announceRow();
  };

  Toy.prototype.rowSummary = function () {
    var r = this.compute(), w = r.W[this.row], best = 0;
    for (var j = 1; j < w.length; j++) if (w[j] > w[best]) best = j;
    return "Row \"" + TOKENS[this.row] + "\": the largest weight is " + fmt(w[best], 3) + " on \"" + TOKENS[best] +
      "\". Output " + vec(r.O[this.row].map(function (x) { return Math.round(x * 1000) / 1000; })) + ".";
  };
  Toy.prototype.announceRow = function () { this.say(this.rowSummary()); };
  Toy.prototype.say = function (t) { this.live.textContent = t; };

  Toy.prototype.colors = function () {
    var cs = getComputedStyle(this.mount);
    return { blue: parseColor(cs.getPropertyValue("--blue")) || [26, 95, 180],
             surf: parseColor(cs.getPropertyValue("--surface")) || [255, 255, 255] };
  };

  Toy.prototype.render = function () {
    var self = this, r = this.compute(), T = TOKENS.length, col = this.colors();
    this.sharpVal.textContent = fmt(this.m, 2);
    this.kSl.forEach(function (o) { o.v.textContent = fmt(parseFloat(o.s.value), 1); });
    this.tokBtns.forEach(function (b, i) { b.setAttribute("aria-pressed", i === self.row ? "true" : "false"); });

    // ---- grid
    var isW = this.view === "weights";
    this.gridTitle.textContent = isW ? "Attention weights (each row sums to 1)" : "Scaled scores m · q·k / √2";
    var g = this.grid;
    g.textContent = "";
    var thead = el("thead"), hr = el("tr");
    var corner = el("th"); corner.setAttribute("scope", "col");
    corner.appendChild(el("span", null, "q \\ k"));
    hr.appendChild(corner);
    TOKENS.forEach(function (t) { var th = el("th", null, t); th.setAttribute("scope", "col"); hr.appendChild(th); });
    thead.appendChild(hr); g.appendChild(thead);
    var tb = el("tbody");
    var smax = 0;
    r.S.forEach(function (row) { row.forEach(function (x) { if (x !== -Infinity) smax = Math.max(smax, Math.abs(x)); }); });
    for (var i = 0; i < T; i++) {
      var tr = el("tr", i === this.row ? "att-sel" : null);
      var th = el("th", "att-rowh"); th.setAttribute("scope", "row");
      var hb = el("button", null, TOKENS[i]); hb.type = "button";
      hb.setAttribute("aria-label", "Select query row " + (i + 1) + ": " + TOKENS[i]);
      (function (ii) { hb.addEventListener("click", function () { self.select(ii); }); })(i);
      th.appendChild(hb); tr.appendChild(th);
      for (var j = 0; j < T; j++) {
        var masked = r.S[i][j] === -Infinity;
        var td = el("td", masked ? "att-masked" : null);
        if (masked) {
          td.textContent = isW ? "0" : "−∞";
          td.setAttribute("aria-label", TOKENS[i] + " to " + TOKENS[j] + ": masked");
        } else {
          var val = isW ? r.W[i][j] : r.S[i][j];
          var a = isW ? val : (smax ? Math.max(0, val) / smax : 0);
          a = Math.min(1, a) * 0.9;
          var c = [0, 1, 2].map(function (k) { return Math.round(col.surf[k] + (col.blue[k] - col.surf[k]) * a); });
          td.style.background = "rgb(" + c.join(",") + ")";
          var L = lum(c);
          td.style.color = L < 0.36 ? "#ffffff" : "#141414";
          td.textContent = fmt(val, 2);
          td.setAttribute("aria-label", TOKENS[i] + " to " + TOKENS[j] + ": " + (isW ? "weight " : "score ") + fmt(val, 3));
        }
        tr.appendChild(td);
      }
      tb.appendChild(tr);
    }
    g.appendChild(tb);

    // ---- selected row table
    var i0 = this.row, q = this.Q[i0];
    this.rowTitle.textContent = "Row \"" + TOKENS[i0] + "\": q = " + vec(q);
    var t = this.tab;
    t.textContent = "";
    var h = el("tr");
    var keep = this.narrow ? [0, 2, 3, 4, 5] : [0, 1, 2, 3, 4, 5];
    ["key", "k", "q·k", "score", "weight", "weight × v"].forEach(function (s, c) {
      if (keep.indexOf(c) < 0) return;
      var x = el("th", null, s); x.setAttribute("scope", "col"); h.appendChild(x);
    });
    var th2 = el("thead"); th2.appendChild(h); t.appendChild(th2);
    var b2 = el("tbody");
    for (var j2 = 0; j2 < T; j2++) {
      var off = r.S[i0][j2] === -Infinity;
      var trr = el("tr", off ? "att-off" : null);
      var w = r.W[i0][j2], v = this.V[j2];
      [TOKENS[j2], vec(this.K[j2]), fmt(r.raw[i0][j2], 2), off ? "masked" : fmt(r.S[i0][j2], 2), fmt(w, 3),
        off ? "—" : vec([Math.round(w * v[0] * 100) / 100, Math.round(w * v[1] * 100) / 100])]
        .forEach(function (s, c) { if (keep.indexOf(c) >= 0) trr.appendChild(el("td", null, s)); });
      b2.appendChild(trr);
    }
    t.appendChild(b2);

    // ---- mix bar + output
    this.mix.textContent = ""; this.mixLegend.textContent = "";
    for (var j3 = 0; j3 < T; j3++) {
      var w3 = r.W[i0][j3];
      var c3 = "var(--viz-c" + (j3 + 1) + ")";
      if (w3 > 0.0005) { var sp = el("span"); sp.style.width = (w3 * 100) + "%"; sp.style.background = c3; this.mix.appendChild(sp); }
      var li = el("li"); var sw = el("span", "att-sw"); sw.style.background = c3;
      li.appendChild(sw); li.appendChild(document.createTextNode(TOKENS[j3] + " " + fmt(w3, 2)));
      this.mixLegend.appendChild(li);
    }
    var o = r.O[i0];
    this.out.textContent = "";
    this.out.appendChild(document.createTextNode("Output for \"" + TOKENS[i0] + "\" = Σ weight × v = "));
    this.out.appendChild(el("b", null, "(" + fmt(o[0], 3) + ", " + fmt(o[1], 3) + ")"));
  };

  function init() {
    var mounts = document.querySelectorAll('[data-viz="' + VIZ_ID + '"]');
    if (!mounts.length) return;
    injectStyle();
    for (var i = 0; i < mounts.length; i++) {
      if (mounts[i].getAttribute("data-viz-ready")) continue;
      mounts[i].setAttribute("data-viz-ready", "1");
      new Toy(mounts[i]);
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
