/* zos_timeline.js - "ZOS timeline": CPU lane and device lane for 6 decode steps (DeepInfer Explained).
 *
 * Mounts into <x-viz id="zos-timeline">. Vanilla JS, no network, no randomness (deterministic).
 * A simplified model of Worker.execute_model_step at commit 9bd9cf2 (deepinfer/worker/worker.py:113-189):
 *   ZOS off: S(N) -> device F(N), s(N) -> CPU waits for s(N) -> P(N) -> S(N+1) ...
 *            (post-process now: worker.py:183-185; the wait is sample_end_evt.synchronize(), worker.py:262-263)
 *   ZOS on:  S(N) -> device F(N) queued -> CPU waits for s(N-1) -> P(N-1) -> device s(N) queued -> S(N+1) ...
 *            (forward N, then post-process N-1, then sample N: worker.py:122, 144, 154; keep N: worker.py:187)
 *            The sample of N cannot start before the CPU launches it, so a long P(N-1) can delay s(N).
 *            The last kept step is post-processed by the flush (worker.py:274-283).
 * S = schedule + prepare inputs + launch forward; P = wait + post-process; F = forward; s = sample.
 * Left out: launch costs of the sampler, DP all-reduces, CUDA graph details, prefill steps.
 */
(function () {
  "use strict";

  var VIZ_ID = "zos-timeline";
  var STEPS = 6;
  var DEF = { s: 2, p: 1.5, d: 5, zos: true };
  var SAMPLE_SHARE = 0.2;          // sample = 20 % of the device time of a step (toy value)
  var UID = 0;

  var CSS = [
    ".zt-root{font-family:var(--sans);color:var(--ink)}",
    ".zt-ctrl{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px 18px;margin:0 0 12px}",
    ".zt-sl{display:flex;flex-direction:column;gap:2px;font-size:14px}",
    ".zt-sl label{font-weight:600}",
    ".zt-sl small{color:var(--mute);font-size:12.5px}",
    ".zt-sl output{font:700 14px var(--mono);color:var(--ink)}",
    ".zt-sl input{width:100%;min-height:32px;margin:0;accent-color:var(--blue)}",
    ".zt-row{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:0 0 12px}",
    ".zt-seg{display:inline-flex;border:1px solid var(--line);border-radius:8px;overflow:hidden}",
    ".zt-seg button{min-height:40px;padding:6px 14px;border:0;background:var(--surface);color:var(--ink);font:600 14px var(--sans);cursor:pointer;touch-action:manipulation}",
    ".zt-seg button+button{border-left:1px solid var(--line)}",
    ".zt-seg button[aria-pressed='true']{background:var(--blue-tint);color:var(--blue)}",
    ".zt-chart{margin:4px 0 0}",
    ".zt-lane{display:grid;grid-template-columns:58px minmax(0,1fr);align-items:center;gap:8px;margin:0 0 8px}",
    ".zt-lname{font-size:13px;font-weight:700;color:var(--mute);text-align:right}",
    ".zt-track{position:relative;height:38px;border-radius:6px;background:var(--panel-bg);border:1px solid var(--border)}",
    ".zt-b{position:absolute;top:3px;bottom:3px;border:1.5px solid;border-radius:4px;display:flex;align-items:center;justify-content:center;overflow:hidden;font:700 12px/1 var(--mono);white-space:nowrap;box-sizing:border-box}",
    ".zt-b.zt-S{border-color:var(--blue);background:var(--blue-tint);color:var(--blue)}",
    ".zt-b.zt-P{border-color:var(--violet);background:var(--violet-tint);color:var(--violet)}",
    ".zt-b.zt-F{border-color:var(--emerald);background:var(--emerald-tint);color:var(--emerald)}",
    ".zt-b.zt-s{border-color:var(--amber);background:var(--amber-tint);color:var(--amber-text)}",
    ".zt-b.zt-I{border:1.5px dashed var(--gray-mid);background:transparent;color:var(--mute);font:italic 500 11.5px/1 var(--sans)}",
    ".zt-axis{position:relative;height:22px;margin-left:66px}",
    ".zt-tick{position:absolute;top:0;font:11px var(--mono);color:var(--mute);transform:translateX(-50%)}",
    ".zt-tick::before{content:'';position:absolute;left:50%;top:-4px;height:4px;border-left:1px solid var(--gray-mid)}",
    ".zt-legend{display:flex;flex-wrap:wrap;gap:4px 14px;margin:6px 0 0;padding:0;list-style:none;font-size:13px;color:var(--ink)}",
    ".zt-legend li{display:inline-flex;align-items:center;gap:6px;margin:0}",
    ".zt-sw{display:inline-block;width:14px;height:14px;border-radius:3px;border:1.5px solid}",
    ".zt-stats{display:flex;flex-wrap:wrap;gap:6px;margin:12px 0 4px;padding:0;list-style:none}",
    ".zt-stats li{margin:0;border-radius:6px;padding:4px 10px;background:var(--panel-bg);font-size:13px;color:var(--mute);line-height:1.3}",
    ".zt-stats b{font:700 14px var(--mono);color:var(--ink);margin-left:4px}",
    ".zt-stats .zt-hi b{color:var(--blue)}",
    ".zt-live{margin:8px 0 0;font-size:14px;font-weight:600;min-height:1.5em}",
    ".zt-note{margin:6px 0 0;font-size:13px;color:var(--mute)}"
  ].join("\n");

  function injectStyle() {
    if (document.getElementById("zt-style")) return;
    var st = document.createElement("style");
    st.id = "zt-style";
    var P = ".viz-mount[data-viz='" + VIZ_ID + "'] ";
    st.textContent = CSS.split("\n").map(function (r) {
      var sel = r.split("{")[0];
      var body = r.slice(sel.length);
      return sel.split(",").map(function (s) { return P + s.trim(); }).join(",") + body;
    }).join("\n");
    document.head.appendChild(st);
  }

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  function fmt(x) { return (Math.round(x * 10) / 10).toFixed(1); }

  /* ---- the model ---------------------------------------------------------- */
  // returns {cpu:[{t0,t1,kind,label}], dev:[...], total, devBusy, cpuWait}
  function simulate(S, P, D, zos) {
    var F = D * (1 - SAMPLE_SHARE), Sm = D * SAMPLE_SHARE;
    var cpu = [], dev = [], t = 0, devT = 0, k, wait = 0;
    function add(list, t0, t1, kind, label) { if (t1 - t0 > 1e-9) list.push({ t0: t0, t1: t1, kind: kind, label: label }); }
    if (!zos) {
      for (k = 1; k <= STEPS; k++) {
        add(cpu, t, t + S, "S", "S" + k); t += S;
        var f0 = Math.max(devT, t);
        add(dev, f0, f0 + F, "F", "F" + k);
        add(dev, f0 + F, f0 + F + Sm, "s", "s" + k); devT = f0 + F + Sm;
        if (devT > t) { add(cpu, t, devT, "I", "wait"); wait += devT - t; t = devT; }
        add(cpu, t, t + P, "P", "P" + k); t += P;
      }
    } else {
      var prevEnd = null;
      for (k = 1; k <= STEPS; k++) {
        add(cpu, t, t + S, "S", "S" + k); t += S;
        var fs = Math.max(devT, t);
        add(dev, fs, fs + F, "F", "F" + k); devT = fs + F;
        if (prevEnd !== null) {
          if (prevEnd > t) { add(cpu, t, prevEnd, "I", "wait"); wait += prevEnd - t; t = prevEnd; }
          add(cpu, t, t + P, "P", "P" + (k - 1)); t += P;
        }
        var ss = Math.max(devT, t);
        add(dev, ss, ss + Sm, "s", "s" + k); devT = ss + Sm; prevEnd = devT;
      }
      if (prevEnd > t) { add(cpu, t, prevEnd, "I", "wait"); wait += prevEnd - t; t = prevEnd; }
      add(cpu, t, t + P, "P", "P" + STEPS); t += P;   // flush_inflight_reqs
    }
    var busy = 0;
    dev.forEach(function (b) { busy += b.t1 - b.t0; });
    // idle gaps on the device lane, from 0 to the end
    var gaps = [], cur = 0;
    dev.forEach(function (b) { if (b.t0 - cur > 1e-9) gaps.push({ t0: cur, t1: b.t0, kind: "I", label: "idle" }); cur = Math.max(cur, b.t1); });
    if (t - cur > 1e-9) gaps.push({ t0: cur, t1: t, kind: "I", label: "idle" });
    return { cpu: cpu, dev: dev.concat(gaps), total: t, devBusy: busy, cpuWait: wait };
  }

  /* ---- the widget --------------------------------------------------------- */
  function Viz(mount) {
    this.mount = mount;
    this.build();
    this.reset(true);
  }

  Viz.prototype.slider = function (parent, id, label, hint, min, max, step) {
    var box = el("div", "zt-sl");
    var lab = el("label");
    var inp = el("input");
    var out = el("output");
    var uid = "zt-" + id + "-" + (++UID);
    inp.type = "range"; inp.min = min; inp.max = max; inp.step = step; inp.id = uid;
    lab.htmlFor = uid;
    lab.appendChild(document.createTextNode(label + ": "));
    lab.appendChild(out);
    box.appendChild(lab);
    box.appendChild(inp);
    box.appendChild(el("small", null, hint));
    parent.appendChild(box);
    var self = this;
    inp.addEventListener("input", function () { self.render(false); });
    inp.addEventListener("change", function () { self.render(true); });
    return { inp: inp, out: out };
  };

  Viz.prototype.build = function () {
    injectStyle();
    var m = this.mount, self = this;
    m.textContent = "";
    var root = el("div", "zt-root");
    var ctrl = el("div", "zt-ctrl");
    this.sS = this.slider(ctrl, "s", "CPU: schedule + prepare", "per step, in time units", 0.5, 8, 0.5);
    this.sP = this.slider(ctrl, "p", "CPU: post-process", "per step, in time units", 0.5, 8, 0.5);
    this.sD = this.slider(ctrl, "d", "Device: forward + sample", "per step (sample = 20 %)", 1, 10, 0.5);
    root.appendChild(ctrl);

    var row = el("div", "zt-row");
    var seg = el("div", "zt-seg");
    seg.setAttribute("role", "group");
    seg.setAttribute("aria-label", "Zero-overhead scheduling");
    this.bOff = el("button", null, "ZOS off");
    this.bOn = el("button", null, "ZOS on");
    [this.bOff, this.bOn].forEach(function (b) { b.type = "button"; seg.appendChild(b); });
    this.bOff.addEventListener("click", function () { self.zos = false; self.render(true); });
    this.bOn.addEventListener("click", function () { self.zos = true; self.render(true); });
    row.appendChild(seg);
    var pre1 = el("button", "viz-btn", "CPU-heavy example");
    pre1.type = "button";
    pre1.addEventListener("click", function () { self.set(3, 4, 5); });
    var pre2 = el("button", "viz-btn", "Long post-process");
    pre2.type = "button";
    pre2.addEventListener("click", function () { self.set(1, 5, 5); });
    var rst = el("button", "viz-btn viz-btn-primary", "Reset");
    rst.type = "button";
    rst.addEventListener("click", function () { self.reset(false); });
    row.appendChild(pre1); row.appendChild(pre2); row.appendChild(rst);
    root.appendChild(row);

    var chart = el("div", "zt-chart");
    chart.setAttribute("role", "img");
    this.chart = chart;
    this.cpuTrack = this.lane(chart, "CPU");
    this.devTrack = this.lane(chart, "device");
    this.axis = el("div", "zt-axis");
    chart.appendChild(this.axis);
    root.appendChild(chart);

    var leg = el("ul", "zt-legend");
    [["S", "schedule + prepare (CPU)", "--blue"], ["P", "post-process (CPU)", "--violet"],
     ["F", "forward (device)", "--emerald"], ["s", "sample (device)", "--amber"]].forEach(function (x) {
      var li = el("li");
      var sw = el("span", "zt-sw");
      sw.style.borderColor = "var(" + x[2] + ")";
      sw.style.background = "var(" + x[2] + "-tint)";
      li.appendChild(sw);
      li.appendChild(document.createTextNode(x[0] + ": " + x[1]));
      leg.appendChild(li);
    });
    var liI = el("li");
    var swI = el("span", "zt-sw");
    swI.style.borderStyle = "dashed"; swI.style.borderColor = "var(--gray-mid)";
    liI.appendChild(swI); liI.appendChild(document.createTextNode("idle / wait"));
    leg.appendChild(liI);
    root.appendChild(leg);

    this.stats = el("ul", "zt-stats");
    root.appendChild(this.stats);
    this.live = el("p", "zt-live");
    this.live.setAttribute("aria-live", "polite");
    root.appendChild(this.live);
    root.appendChild(el("p", "zt-note",
      "Simplified model: 6 decode steps, times in toy units. Numbers in a block are step numbers. " +
      "With ZOS, P2 means: the CPU post-processes step 2 during the call for step 3."));
    m.appendChild(root);

    var t = null;
    window.addEventListener("resize", function () { clearTimeout(t); t = setTimeout(function () { self.render(false); }, 120); });
  };

  Viz.prototype.lane = function (parent, name) {
    var row = el("div", "zt-lane");
    row.appendChild(el("div", "zt-lname", name));
    var tr = el("div", "zt-track");
    row.appendChild(tr);
    parent.appendChild(row);
    return tr;
  };

  Viz.prototype.set = function (s, p, d) {
    this.sS.inp.value = s; this.sP.inp.value = p; this.sD.inp.value = d;
    this.render(true);
  };

  Viz.prototype.reset = function (quiet) {
    this.zos = DEF.zos;
    this.sS.inp.value = DEF.s; this.sP.inp.value = DEF.p; this.sD.inp.value = DEF.d;
    this.render(!quiet);
    if (quiet) this.live.textContent = "";
  };

  Viz.prototype.drawTrack = function (track, blocks, scale) {
    track.textContent = "";
    var px = track.clientWidth || 600;
    blocks.forEach(function (b) {
      var d = el("div", "zt-b zt-" + b.kind);
      d.style.left = (b.t0 / scale * 100) + "%";
      d.style.width = ((b.t1 - b.t0) / scale * 100) + "%";
      var w = (b.t1 - b.t0) / scale * px;
      var minW = b.kind === "I" ? 34 : 22;
      if (w >= minW) d.textContent = b.label;
      d.title = b.label + ": " + fmt(b.t0) + " to " + fmt(b.t1);
      track.appendChild(d);
    });
  };

  Viz.prototype.render = function (announce) {
    var S = +this.sS.inp.value, P = +this.sP.inp.value, D = +this.sD.inp.value;
    this.sS.out.textContent = fmt(S);
    this.sP.out.textContent = fmt(P);
    this.sD.out.textContent = fmt(D);
    this.bOff.setAttribute("aria-pressed", String(!this.zos));
    this.bOn.setAttribute("aria-pressed", String(this.zos));

    var off = simulate(S, P, D, false), on = simulate(S, P, D, true);
    var cur = this.zos ? on : off;
    var scale = Math.max(off.total, on.total);
    this.drawTrack(this.cpuTrack, cur.cpu, scale);
    this.drawTrack(this.devTrack, cur.dev, scale);

    // axis: about 6 ticks
    this.axis.textContent = "";
    var stepT = Math.max(1, Math.ceil(scale / 6 / 5) * 5);
    if (scale < 30) stepT = Math.max(1, Math.ceil(scale / 6));
    for (var t = 0; t <= scale + 1e-9; t += stepT) {
      var tk = el("span", "zt-tick", String(t));
      tk.style.left = (t / scale * 100) + "%";
      this.axis.appendChild(tk);
    }

    var idle = cur.total - cur.devBusy;
    var speed = off.total / on.total;
    this.stats.textContent = "";
    var items = [
      ["Total, ZOS off", fmt(off.total), !this.zos],
      ["Total, ZOS on", fmt(on.total), this.zos],
      ["Speed-up", speed.toFixed(2) + "x", false],
      ["Device idle (shown)", fmt(idle) + " (" + Math.round(idle / cur.total * 100) + " %)", false],
      ["CPU waits (shown)", fmt(cur.cpuWait), false]
    ];
    var self = this;
    items.forEach(function (x) {
      var li = el("li", x[2] ? "zt-hi" : null);
      li.appendChild(document.createTextNode(x[0]));
      li.appendChild(el("b", null, x[1]));
      self.stats.appendChild(li);
    });
    var desc = (this.zos ? "ZOS on" : "ZOS off") + ": 6 steps take " + fmt(cur.total) + " units. The device is idle for " +
      fmt(idle) + " units. ZOS on is " + speed.toFixed(2) + " times faster than ZOS off with these times.";
    this.chart.setAttribute("aria-label", desc);
    if (announce) this.live.textContent = desc;
  };

  function init() {
    var mounts = document.querySelectorAll('[data-viz="' + VIZ_ID + '"]');
    for (var i = 0; i < mounts.length; i++) new Viz(mounts[i]);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
