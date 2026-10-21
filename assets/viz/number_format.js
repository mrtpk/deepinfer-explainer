/* number_format.js - number-format converter for DeepInfer Explained (concepts/low-precision-formats).
 *
 * Mounts into <x-viz id="number-format">. Vanilla JS, no network, seeded and deterministic.
 *
 * Part 1: one number -> BF16, FP8 E4M3 ("fn": no infinity, NaN = S.1111.111) and FP4 E2M1
 *   (no infinity, no NaN). Rounding: round to nearest, ties to even, directly from the exact
 *   double value. Overflow: BF16 -> infinity (IEEE); E4M3 -> saturate to +-448 or NaN (the two
 *   OCP FP8 conversion modes, the reader picks one); E2M1 -> saturate to +-6 (no other code).
 * Part 2: a block of up to 32 values with one shared UE8M0 scale (MXFP4 or MXFP8).
 *   Scale rule copied from DeepInfer at commit 9bd9cf2:
 *     amax = max(amax, AMAX_MARGIN)                      (cuda/fused_transform.py:514)
 *     exp  = ceil(log2(amax * (1 / max_elem))) in FP32   (cuda/fused_transform.py:516, cuda/quant.py:4-9)
 *     UE8M0 byte = exp + 127, scale = 2^exp               (cuda/fused_transform.py:518-520)
 *     FP4_AMAX_MARGIN = 6 * 2^-126, FP8_AMAX_MARGIN = 1e-4 (tilelang_ops/common.py:23-27)
 *   Each value x is stored as code(x / 2^exp); the decoded value is code * 2^exp.
 * Left out: BF16 rounding of the inputs before the cast (the model's inputs are already BF16),
 *   the byte order of packed codes, and the E4M3-scaled FP4 format of the main KV cache.
 * The encoder core is also exported for node tests (module.exports) when there is no DOM.
 */
(function () {
  "use strict";

  /* ------------------------------------------------------------------ core */

  function pow2(n) { return Math.pow(2, n); }           // exact for integer n

  function floorLog2(a) {                                 // exact for finite a > 0
    var e = Math.floor(Math.log2(a));
    while (pow2(e) > a) e--;
    while (pow2(e + 1) <= a) e++;
    return e;
  }

  var FORMATS = {
    bf16: { id: "bf16", name: "BF16", ebits: 8, mbits: 7, bias: 127, ieee: true },
    e4m3: { id: "e4m3", name: "FP8 E4M3", ebits: 4, mbits: 3, bias: 7, ieee: false, nan: true },
    e2m1: { id: "e2m1", name: "FP4 E2M1", ebits: 2, mbits: 1, bias: 1, ieee: false, nan: false }
  };
  (function () {
    for (var k in FORMATS) {
      var f = FORMATS[k];
      f.bits = 1 + f.ebits + f.mbits;
      f.emin = 1 - f.bias;
      if (f.ieee) {
        f.emax = pow2(f.ebits) - 2 - f.bias;               // all-ones exponent = inf / NaN
        f.max = (2 - pow2(-f.mbits)) * pow2(f.emax);
      } else if (f.nan) {
        f.emax = pow2(f.ebits) - 1 - f.bias;               // all-ones exponent is used ...
        f.max = (2 - pow2(1 - f.mbits)) * pow2(f.emax);    // ... except mantissa all ones (NaN)
      } else {
        f.emax = pow2(f.ebits) - 1 - f.bias;
        f.max = (2 - pow2(-f.mbits)) * pow2(f.emax);
      }
    }
  })();

  function fields(bits, f) {
    return {
      sign: (bits >> (f.ebits + f.mbits)) & 1,
      exp: (bits >> f.mbits) & (pow2(f.ebits) - 1),
      mant: bits & (pow2(f.mbits) - 1)
    };
  }

  function decode(bits, f) {
    var fl = fields(bits, f);
    var s = fl.sign ? -1 : 1;
    var eAll = pow2(f.ebits) - 1, mAll = pow2(f.mbits) - 1;
    if (f.ieee && fl.exp === eAll) return fl.mant ? NaN : s * Infinity;
    if (f.nan && fl.exp === eAll && fl.mant === mAll) return NaN;
    if (fl.exp === 0) return s * fl.mant * pow2(f.emin - f.mbits);
    return s * (pow2(f.mbits) + fl.mant) * pow2(fl.exp - f.bias - f.mbits);
  }

  function pack(sign, exp, mant, f) {
    return (sign << (f.ebits + f.mbits)) | (exp << f.mbits) | mant;
  }

  function fromValue(v, sign, f) {                        // v >= 0 exactly representable
    if (v === 0) return pack(sign, 0, 0, f);
    var ev = floorLog2(v);
    if (ev < f.emin) return pack(sign, 0, v / pow2(f.emin - f.mbits), f);
    return pack(sign, ev + f.bias, v / pow2(ev - f.mbits) - pow2(f.mbits), f);
  }

  /* encode(x, f, overflow) -> {bits, value, kind, tie, dir, err}
     kind: zero | subnormal | normal | inf | nan | saturated | overflow-nan | no-nan
     overflow: "saturate" or "nan" (E4M3 only). */
  function encode(x, f, overflow) {
    var r = { bits: null, value: NaN, kind: "", tie: false, dir: 0, input: x };
    var sign = (x < 0 || Object.is(x, -0)) ? 1 : 0;
    var eAll = pow2(f.ebits) - 1, mAll = pow2(f.mbits) - 1;
    function nanCode() {
      if (f.ieee) return pack(0, eAll, 1 << (f.mbits - 1), f);
      return pack(0, eAll, mAll, f);
    }
    function over() {
      if (f.ieee) { r.bits = pack(sign, eAll, 0, f); r.kind = "inf"; }
      else if (f.nan && overflow === "nan") { r.bits = nanCode(); r.kind = "overflow-nan"; }
      else { r.bits = fromValue(f.max, sign, f); r.kind = "saturated"; }
      r.value = decode(r.bits, f);
      return r;
    }
    if (isNaN(x)) {
      if (f.ieee || f.nan) { r.bits = nanCode(); r.kind = "nan"; r.value = NaN; }
      else { r.kind = "no-nan"; }
      return r;
    }
    var a = Math.abs(x);
    if (a === Infinity) return over();
    if (a === 0) { r.bits = pack(sign, 0, 0, f); r.value = sign ? -0 : 0; r.kind = "zero"; return r; }
    var e = floorLog2(a);
    var eq = e < f.emin ? f.emin : e;
    var q = pow2(eq - f.mbits);
    var t = a / q;                                         // exact: q is a power of two
    var n = Math.floor(t);
    var frac = t - n;                                      // exact: t < 2^(mbits+1) or huge
    if (frac > 0.5) { n += 1; r.dir = 1; }
    else if (frac < 0.5) { r.dir = frac > 0 ? -1 : 0; }
    else { r.tie = true; if (n % 2 !== 0) { n += 1; r.dir = 1; } else { r.dir = -1; } }
    var v = n * q;
    if (v > f.max) return over();
    r.bits = fromValue(v, sign, f);
    r.value = sign ? -v : v;
    r.kind = v === 0 ? "zero" : (floorLog2(v) < f.emin ? "subnormal" : "normal");
    return r;
  }

  /* UE8M0 block scale, as in DeepInfer's quantize kernels (see header). */
  var MARGIN = { e2m1: 6 * pow2(-126), e4m3: 1e-4 };
  function blockScale(values, elemId) {
    var f = FORMATS[elemId];
    var amax = 0;
    for (var i = 0; i < values.length; i++) amax = Math.max(amax, Math.abs(values[i]));
    var fr = Math.fround;
    var amaxC = Math.max(fr(amax), fr(MARGIN[elemId]));
    var ratio = fr(amaxC * fr(1 / f.max));
    var e = floorLog2(ratio);
    var exp = pow2(e) === ratio ? e : e + 1;               // ceil(log2(ratio))
    var codes = values.map(function (x) {
      var c = encode(x / pow2(exp), f, "saturate");
      c.decoded = c.value * pow2(exp);
      c.err = c.decoded - x;
      return c;
    });
    return { amax: amax, amaxClamped: amaxC, ratio: ratio, exp: exp, scale: pow2(exp), byte: exp + 127, codes: codes, f: f };
  }

  var core = { FORMATS: FORMATS, encode: encode, decode: decode, fields: fields, blockScale: blockScale, floorLog2: floorLog2 };

  if (typeof document === "undefined") {
    if (typeof module !== "undefined" && module.exports) module.exports = core;
    return;
  }

  /* ------------------------------------------------------------------ UI */

  var VIZ_ID = "number-format";
  var SEED = 20261021;
  var PRESETS = ["0.3", "1/3", "2.5", "448", "470", "0.001", "-6.5", "100000"];

  function mulberry32(a) {
    return function () {
      a |= 0; a = (a + 0x6d2b79f5) | 0;
      var t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  var CSS = [
    ".nfv-root{font-family:var(--sans);color:var(--ink)}",
    ".viz-mount .nfv-root h4.nfv-h{margin:0 0 10px;padding:0;font:700 13px/1.4 var(--sans);color:var(--mute);text-transform:uppercase;letter-spacing:.03em;border:0}",
    ".nfv-sec+.nfv-sec{margin-top:22px;padding-top:16px;border-top:1px solid var(--border)}",
    ".nfv-row{display:flex;flex-wrap:wrap;gap:8px;align-items:center}",
    ".nfv-in{min-height:40px;box-sizing:border-box;width:13em;max-width:100%;padding:6px 10px;border:1px solid var(--line);border-radius:8px;background:var(--surface);color:var(--ink);font:500 16px var(--mono)}",
    ".nfv-in:focus,.nfv-ta:focus{outline:2px solid var(--blue);outline-offset:1px}",
    ".nfv-label{font-weight:600;font-size:14.5px}",
    ".nfv-presets{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}",
    ".nfv-presets .viz-btn{font-family:var(--mono);font-size:13.5px;padding:6px 10px}",
    ".nfv-opt{display:flex;flex-wrap:wrap;gap:4px 14px;align-items:center;margin:10px 0 0;padding:0;border:0;font-size:14px}",
    ".nfv-opt legend{float:left;padding:0;margin-right:6px;font-weight:600;color:var(--mute)}",
    ".nfv-opt label{display:inline-flex;align-items:center;gap:6px;min-height:32px;cursor:pointer}",
    ".nfv-opt input{width:18px;height:18px;margin:0;accent-color:var(--blue)}",
    ".nfv-parsed{margin:10px 0 0;font:13.5px var(--mono);color:var(--mute);overflow-wrap:anywhere}",
    ".nfv-cards{display:grid;grid-template-columns:minmax(0,1fr);gap:10px;margin-top:12px}",
    ".nfv-card-wide{grid-column:1/-1}",
    ".nfv-card{border:1px solid var(--border);border-radius:8px;padding:10px 12px;background:var(--surface);min-width:0}",
    ".nfv-card-top{display:flex;flex-wrap:wrap;justify-content:space-between;gap:4px 12px;align-items:baseline}",
    ".nfv-fname{font-weight:700;font-size:15px}",
    ".nfv-hex{font:600 13px var(--mono);color:var(--mute)}",
    ".nfv-bits{display:flex;flex-wrap:wrap;gap:3px;margin:8px 0 6px}",
    ".nfv-bit{display:inline-flex;align-items:center;justify-content:center;min-width:20px;height:26px;padding:0 2px;border:1.5px solid;border-radius:4px;font:700 14px var(--mono);box-sizing:border-box}",
    ".nfv-gap{width:6px}",
    ".nfv-s{border-color:var(--pink);background:var(--pink-tint);color:var(--pink)}",
    ".nfv-e{border-color:var(--blue);background:var(--blue-tint);color:var(--blue)}",
    ".nfv-m{border-color:var(--amber);background:var(--amber-tint);color:var(--amber-text)}",
    ".nfv-kv{display:grid;grid-template-columns:max-content minmax(0,1fr);gap:2px 12px;margin:0;font-size:14px}",
    ".nfv-kv dt{color:var(--mute);margin:0}",
    ".nfv-kv dd{margin:0;font-family:var(--mono);overflow-wrap:anywhere}",
    ".nfv-note{margin:6px 0 0;font-size:13.5px;color:var(--mute)}",
    ".nfv-warn{color:var(--amber-text);font-weight:600}",
    ".nfv-legend{display:flex;flex-wrap:wrap;gap:4px 14px;margin:10px 0 0;font-size:13px;color:var(--mute)}",
    ".nfv-legend span{display:inline-flex;align-items:center;gap:5px}",
    ".nfv-sw{display:inline-block;width:12px;height:12px;border:1.5px solid;border-radius:3px}",
    ".nfv-ta{display:block;width:100%;box-sizing:border-box;min-height:84px;margin-top:8px;padding:8px 10px;border:1px solid var(--line);border-radius:8px;background:var(--surface);color:var(--ink);font:13.5px/1.5 var(--mono);resize:vertical}",
    ".nfv-steps{margin:12px 0 0;padding-left:1.4em;font-size:14.5px}",
    ".nfv-steps li{margin:2px 0}",
    ".nfv-steps code{font-family:var(--mono)}",
    ".nfv-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(112px,1fr));gap:6px;margin:12px 0 0;padding:0;list-style:none}",
    ".nfv-grid.nfv-grid8{grid-template-columns:repeat(auto-fill,minmax(172px,1fr))}",
    ".nfv-cell{margin:0;border:1px solid var(--border);border-radius:6px;padding:5px 6px;background:var(--surface);font:12.5px/1.45 var(--mono);min-width:0}",
    ".nfv-cell.nfv-max{border:2px solid var(--ink)}",
    ".nfv-cell.nfv-zero{border-style:dashed}",
    ".nfv-ci{color:var(--mute);font-size:11.5px}",
    ".nfv-cell .nfv-bits{margin:3px 0;gap:2px}",
    ".nfv-cell .nfv-bit{min-width:15px;height:20px;font-size:12px;border-width:1px}",
    ".nfv-cell .nfv-gap{width:3px}",
    ".nfv-errv{color:var(--mute)}",
    ".nfv-sum{display:flex;flex-wrap:wrap;gap:6px;margin:12px 0 0;padding:0;list-style:none}",
    ".nfv-sum li{margin:0;border-radius:6px;padding:4px 10px;background:var(--panel-bg);font-size:13px;color:var(--mute);line-height:1.3}",
    ".nfv-sum b{font:700 14px var(--mono);color:var(--ink);margin-left:4px}",
    ".nfv-live{margin:14px 0 0;font-size:14px;font-weight:600;min-height:1.5em}",
    ".nfv-err{color:var(--amber-text);font-size:14px;margin:8px 0 0}",
    "@media (min-width:700px){.nfv-cards{grid-template-columns:repeat(2,minmax(0,1fr))}}",
    "@media (max-width:560px){.nfv-bit{min-width:17px;height:24px;font-size:13px}.nfv-bits{gap:2px}}"
  ].join("\n");

  function injectCss() {
    if (document.getElementById("nfv-style")) return;
    var st = document.createElement("style");
    st.id = "nfv-style";
    st.textContent = CSS;
    document.head.appendChild(st);
  }

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }

  function button(label, cls, onClick) {
    var b = el("button", "viz-btn" + (cls ? " " + cls : ""), label);
    b.type = "button";
    b.addEventListener("click", onClick);
    return b;
  }

  // compact number text: up to 7 significant digits, no trailing zeros
  function fmt(v) {
    if (typeof v !== "number") return String(v);
    if (isNaN(v)) return "NaN";
    if (v === Infinity) return "+inf";
    if (v === -Infinity) return "-inf";
    if (v === 0) return Object.is(v, -0) ? "-0" : "0";
    var a = Math.abs(v);
    var s = (a >= 1e7 || a < 1e-4) ? v.toExponential(8) : v.toPrecision(10);
    if (s.indexOf("e") >= 0) {
      var p = s.split("e");
      return p[0].replace(/\.?0+$/, "") + "e" + p[1];
    }
    return s.indexOf(".") >= 0 ? s.replace(/\.?0+$/, "") : s;
  }

  function short(v) { return v === 0 ? "0" : fmt(Number(v.toPrecision(4))); }

  function pow2Text(e) { return "2^" + e; }

  function bitString(bits, f) {
    var s = "";
    for (var i = f.bits - 1; i >= 0; i--) s += (bits >> i) & 1;
    return s;
  }

  function hex(bits, f) {
    var digits = Math.ceil(f.bits / 4);
    var h = bits.toString(16).toUpperCase();
    while (h.length < digits) h = "0" + h;
    return "0x" + h;
  }

  function bitBoxes(bits, f, small) {
    var wrap = el("div", "nfv-bits");
    wrap.setAttribute("aria-hidden", "true");
    var s = bitString(bits, f);
    for (var i = 0; i < s.length; i++) {
      var cls = i === 0 ? "nfv-s" : (i <= f.ebits ? "nfv-e" : "nfv-m");
      if (i === 1 || i === 1 + f.ebits) wrap.appendChild(el("span", "nfv-gap"));
      wrap.appendChild(el("span", "nfv-bit " + cls, s[i]));
    }
    return wrap;
  }

  function fieldsText(bits, f) {
    var s = bitString(bits, f);
    return "sign " + s[0] + ", exponent " + s.slice(1, 1 + f.ebits) + ", mantissa " + s.slice(1 + f.ebits);
  }

  // parse "0.3", "1/3", "-2e-3", "inf", "nan", "2^-9"
  function parseNumber(txt) {
    var t = String(txt).trim().toLowerCase().replace(/\s+/g, "").replace(/−/g, "-");
    if (!t) return null;
    if (/^[+-]?(inf|infinity)$/.test(t)) return t[0] === "-" ? -Infinity : Infinity;
    if (t === "nan") return NaN;
    var m = /^([+-]?)2\^([+-]?\d+)$/.exec(t);
    if (m) return (m[1] === "-" ? -1 : 1) * Math.pow(2, +m[2]);
    m = /^([+-]?[0-9.]+(?:e[+-]?\d+)?)\/([0-9.]+(?:e[+-]?\d+)?)$/.exec(t);
    if (m) { var d = Number(m[2]); return d === 0 ? null : Number(m[1]) / d; }
    if (!/^[+-]?(\d+\.?\d*|\.\d+)(e[+-]?\d+)?$/.test(t)) return null;
    return Number(t);
  }

  function describe(r, f) {
    var parts = [];
    if (r.kind === "no-nan") return "E2M1 has no NaN code. The value cannot be stored.";
    if (r.kind === "nan") return "NaN input gives the NaN code.";
    if (r.kind === "inf") return "Overflow: the value is above the largest BF16 value after rounding, so it becomes infinity.";
    if (r.kind === "saturated") return "Overflow: the rounded value is above " + fmt(f.max) + ". The code saturates to the largest value, " + (r.value < 0 ? "-" : "") + fmt(f.max) + ".";
    if (r.kind === "overflow-nan") return "Overflow: the rounded value is above 448. A non-saturating conversion gives NaN.";
    if (r.kind === "zero" && r.input !== 0) parts.push("Underflow: the value is at or below half of the smallest step, so it rounds to 0.");
    if (r.kind === "subnormal") parts.push("Subnormal: the exponent field is 0, so the value is 0.mantissa × " + pow2Text(f.emin) + ".");
    if (r.tie) parts.push("Tie: the value is exactly between two codes. Round to even picks the code whose last mantissa bit is 0.");
    else if (r.dir > 0) parts.push("Rounded up to the nearest code.");
    else if (r.dir < 0) parts.push("Rounded down to the nearest code.");
    else if (r.kind !== "zero") parts.push("Exact: this value has a code.");
    return parts.join(" ");
  }

  function mount(root) {
    injectCss();
    root.innerHTML = "";
    var box = el("div", "nfv-root");
    root.appendChild(box);

    var state = { text: "0.3", overflow: "saturate", elem: "e2m1", seedStep: 0, values: null, custom: false };

    /* ---- part 1: one number ---- */
    var s1 = el("section", "nfv-sec");
    s1.appendChild(el("h4", "nfv-h", "1 · One number in three formats"));
    var row = el("div", "nfv-row");
    var inId = "nfv-in-" + Math.floor(Math.random() * 1e9);
    var lab = el("label", "nfv-label", "Number");
    lab.htmlFor = inId;
    var input = el("input", "nfv-in");
    input.id = inId;
    input.type = "text";
    input.setAttribute("inputmode", "decimal");
    input.setAttribute("autocomplete", "off");
    input.setAttribute("spellcheck", "false");
    input.setAttribute("aria-describedby", inId + "-help");
    input.value = state.text;
    row.appendChild(lab);
    row.appendChild(input);
    row.appendChild(button("Convert", "viz-btn-primary", function () { state.text = input.value; renderOne(true); }));
    s1.appendChild(row);
    var help = el("p", "nfv-note", "Type a decimal number, a fraction such as 1/3, a power such as 2^-9, inf or nan. Press Enter or Convert.");
    help.id = inId + "-help";
    s1.appendChild(help);
    input.addEventListener("keydown", function (ev) { if (ev.key === "Enter") { state.text = input.value; renderOne(true); } });

    var presets = el("div", "nfv-presets");
    presets.setAttribute("role", "group");
    presets.setAttribute("aria-label", "Example numbers");
    PRESETS.forEach(function (p) {
      presets.appendChild(button(p, "", function () { input.value = p; state.text = p; renderOne(true); }));
    });
    s1.appendChild(presets);

    var ovf = el("fieldset", "nfv-opt");
    ovf.appendChild(el("legend", null, "E4M3 overflow:"));
    [["saturate", "saturate to ±448"], ["nan", "give NaN"]].forEach(function (o) {
      var l = el("label");
      var r = el("input");
      r.type = "radio"; r.name = inId + "-ovf"; r.value = o[0]; r.checked = state.overflow === o[0];
      r.addEventListener("change", function () { state.overflow = o[0]; renderOne(true); });
      l.appendChild(r); l.appendChild(document.createTextNode(o[1]));
      ovf.appendChild(l);
    });
    s1.appendChild(ovf);

    var parsed = el("p", "nfv-parsed");
    s1.appendChild(parsed);
    var cards = el("div", "nfv-cards");
    s1.appendChild(cards);
    var legend = el("div", "nfv-legend");
    [["nfv-s", "sign bit"], ["nfv-e", "exponent bits"], ["nfv-m", "mantissa bits"]].forEach(function (k) {
      var sp = el("span");
      sp.appendChild(el("span", "nfv-sw " + k[0]));
      sp.appendChild(document.createTextNode(k[1]));
      legend.appendChild(sp);
    });
    s1.appendChild(legend);
    box.appendChild(s1);

    /* ---- part 2: a block with one UE8M0 scale ---- */
    var s2 = el("section", "nfv-sec");
    s2.appendChild(el("h4", "nfv-h", "2 · A block of 32 values with one UE8M0 scale"));
    var fmtSel = el("fieldset", "nfv-opt");
    fmtSel.appendChild(el("legend", null, "Element format:"));
    [["e2m1", "MXFP4 (E2M1, max 6)"], ["e4m3", "MXFP8 (E4M3, max 448)"]].forEach(function (o) {
      var l = el("label");
      var r = el("input");
      r.type = "radio"; r.name = inId + "-elem"; r.value = o[0]; r.checked = state.elem === o[0];
      r.addEventListener("change", function () { state.elem = o[0]; renderBlock(true); });
      l.appendChild(r); l.appendChild(document.createTextNode(o[1]));
      fmtSel.appendChild(l);
    });
    s2.appendChild(fmtSel);
    var brow = el("div", "nfv-row");
    brow.style.marginTop = "10px";
    brow.appendChild(button("New block", "viz-btn-primary", function () { state.seedStep += 1; state.custom = false; state.values = genBlock(state.seedStep); renderBlock(true); }));
    brow.appendChild(button("Add an outlier", "", function () { addOutlier(); renderBlock(true); }));
    brow.appendChild(button("Reset", "", function () { resetAll(); }));
    s2.appendChild(brow);

    var taId = inId + "-ta";
    var taLab = el("label", "nfv-label", "Values (1 to 32 numbers, separated by commas or spaces)");
    taLab.htmlFor = taId;
    taLab.style.display = "block";
    taLab.style.marginTop = "12px";
    s2.appendChild(taLab);
    var ta = el("textarea", "nfv-ta");
    ta.id = taId;
    ta.setAttribute("spellcheck", "false");
    s2.appendChild(ta);
    var trow = el("div", "nfv-row");
    trow.style.marginTop = "8px";
    trow.appendChild(button("Use these values", "", function () { useText(); }));
    s2.appendChild(trow);
    var taErr = el("p", "nfv-err");
    taErr.hidden = true;
    s2.appendChild(taErr);

    var steps = el("ol", "nfv-steps");
    s2.appendChild(steps);
    var sum = el("ul", "nfv-sum");
    s2.appendChild(sum);
    var grid = el("ul", "nfv-grid");
    grid.setAttribute("aria-label", "Encoded values of the block");
    s2.appendChild(grid);
    box.appendChild(s2);

    var live = el("p", "nfv-live");
    live.setAttribute("aria-live", "polite");
    box.appendChild(live);

    /* ---- logic ---- */
    function genBlock(step) {
      var rnd = mulberry32(SEED + step * 7919);
      var out = [];
      for (var i = 0; i < 32; i++) {
        var u1 = Math.max(rnd(), 1e-12), u2 = rnd();
        var z = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
        out.push(Number((z * 0.8).toFixed(3)));
      }
      return out;
    }

    function addOutlier() {
      var vals = state.values.slice();
      var rnd = mulberry32(SEED + 104729 + state.seedStep * 31 + vals.length);
      var idx = Math.floor(rnd() * vals.length);
      var amax = 0;
      vals.forEach(function (v) { amax = Math.max(amax, Math.abs(v)); });
      vals[idx] = Number(((rnd() < 0.5 ? -1 : 1) * Math.max(amax, 0.1) * 12).toFixed(3));
      state.values = vals;
      state.custom = true;
    }

    function useText() {
      var parts = ta.value.split(/[\s,;]+/).filter(function (p) { return p.length > 0; });
      var vals = [];
      for (var i = 0; i < parts.length; i++) {
        var v = parseNumber(parts[i]);
        if (v === null || !isFinite(v)) {
          taErr.textContent = "“" + parts[i] + "” is not a finite number. Fix it and try again.";
          taErr.hidden = false;
          live.textContent = taErr.textContent;
          return;
        }
        vals.push(v);
      }
      if (vals.length < 1 || vals.length > 32) {
        taErr.textContent = "Type between 1 and 32 numbers. You typed " + vals.length + ".";
        taErr.hidden = false;
        live.textContent = taErr.textContent;
        return;
      }
      taErr.hidden = true;
      state.values = vals;
      state.custom = true;
      renderBlock(true);
    }

    function resetAll() {
      state.text = "0.3"; state.overflow = "saturate"; state.elem = "e2m1"; state.seedStep = 0; state.custom = false;
      state.values = genBlock(0);
      input.value = state.text;
      box.querySelectorAll('input[type="radio"]').forEach(function (r) {
        r.checked = (r.value === state.overflow || r.value === state.elem);
      });
      taErr.hidden = true;
      renderOne(false);
      renderBlock(false);
      live.textContent = "Reset: the number is 0.3 and the block is the first example block.";
    }

    function renderOne(announce) {
      var x = parseNumber(state.text);
      cards.innerHTML = "";
      if (x === null) {
        parsed.textContent = "Not a number: “" + state.text + "”.";
        if (announce) live.textContent = parsed.textContent;
        return;
      }
      parsed.textContent = "Input value: " + (isFinite(x) && x !== 0 ? String(x) : fmt(x));
      var said = [];
      ["bf16", "e4m3", "e2m1"].forEach(function (id) {
        var f = FORMATS[id];
        var r = encode(x, f, state.overflow);
        var c = el("div", "nfv-card" + (id === "bf16" ? " nfv-card-wide" : ""));
        var top = el("div", "nfv-card-top");
        top.appendChild(el("span", "nfv-fname", f.name));
        top.appendChild(el("span", "nfv-hex", r.bits === null ? "no code" : hex(r.bits, f)));
        c.appendChild(top);
        if (r.bits !== null) c.appendChild(bitBoxes(r.bits, f));
        var dl = el("dl", "nfv-kv");
        function kv(k, v) { dl.appendChild(el("dt", null, k)); dl.appendChild(el("dd", null, v)); }
        if (r.bits !== null) {
          var fl = fields(r.bits, f);
          kv("fields", fl.sign + " · " + bitString(r.bits, f).slice(1, 1 + f.ebits) + " · " + bitString(r.bits, f).slice(1 + f.ebits));
          var expTxt = fl.exp === 0 ? "0 (subnormal: " + pow2Text(f.emin) + ")" : fl.exp + " − " + f.bias + " = " + (fl.exp - f.bias);
          kv("exponent", expTxt);
          kv("stored value", fmt(r.value));
          if (isFinite(x) && isFinite(r.value)) {
            var err = r.value - x;
            kv("error", (err > 0 ? "+" : "") + fmt(err) + (x !== 0 ? "  (" + fmt(Math.abs(err) / Math.abs(x) * 100) + " %)" : ""));
          }
          c.setAttribute("aria-label", f.name + ": " + fieldsText(r.bits, f) + ", stored value " + fmt(r.value));
        }
        c.appendChild(dl);
        var note = el("p", "nfv-note" + (/saturated|overflow|inf|no-nan/.test(r.kind) ? " nfv-warn" : ""), describe(r, f));
        c.appendChild(note);
        cards.appendChild(c);
        said.push(f.name + " " + (r.bits === null ? "no code" : hex(r.bits, f) + " = " + fmt(r.value)));
      });
      if (announce) live.textContent = "Converted " + state.text + ": " + said.join("; ") + ".";
    }

    function renderBlock(announce) {
      if (!state.custom || document.activeElement !== ta) ta.value = state.values.map(fmt).join(", ");
      var res = blockScale(state.values, state.elem);
      var f = res.f;
      steps.innerHTML = "";
      function li(html) { var l = el("li"); l.innerHTML = html; steps.appendChild(l); }
      var marg = state.elem === "e2m1" ? "6 × 2^-126" : "1e-4";
      li("Largest magnitude: <code>amax = " + fmt(res.amax) + "</code>" + (res.amaxClamped > Math.fround(res.amax) ? " (below the floor " + marg + ", so the floor is used)" : "") + ".");
      li("Divide by the largest " + (state.elem === "e2m1" ? "E2M1" : "E4M3") + " value: <code>amax / " + fmt(f.max) + " = " + fmt(res.ratio) + "</code>.");
      li("Round the exponent up: <code>ceil(log2(" + fmt(res.ratio) + ")) = " + res.exp + "</code>, so <code>scale = 2^" + res.exp + " = " + fmt(res.scale) + "</code>.");
      var byteBits = res.byte.toString(2);
      while (byteBits.length < 8) byteBits = "0" + byteBits;
      li("UE8M0 byte: <code>" + res.exp + " + 127 = " + res.byte + " = " + byteBits + "</code> (exponent bits only).");
      li("Each value: <code>code = round(x / " + fmt(res.scale) + ")</code>, stored value <code>= code × " + fmt(res.scale) + "</code>.");

      var n = state.values.length;
      var bytes = state.elem === "e2m1" ? Math.ceil(n / 2) : n;
      var sumAbs = 0, maxAbs = 0, zeros = 0, sat = 0;
      res.codes.forEach(function (c, i) {
        sumAbs += Math.abs(c.err); maxAbs = Math.max(maxAbs, Math.abs(c.err));
        if (c.value === 0 && state.values[i] !== 0) zeros++;
        if (c.kind === "saturated") sat++;
      });
      sum.innerHTML = "";
      function chip(k, v) { var l = el("li"); l.appendChild(document.createTextNode(k)); l.appendChild(el("b", null, v)); sum.appendChild(l); }
      chip("values", String(n));
      chip("bytes", bytes + " + 1 scale = " + (bytes + 1));
      chip("bits per value", fmt((bytes + 1) * 8 / n));
      chip("BF16 bytes", String(2 * n));
      chip("mean |error|", short(sumAbs / n));
      chip("max |error|", short(maxAbs));
      chip("rounded to 0", String(zeros));

      grid.innerHTML = "";
      grid.className = "nfv-grid" + (state.elem === "e4m3" ? " nfv-grid8" : "");
      var amaxIdx = -1, amax = -1;
      state.values.forEach(function (v, i) { if (Math.abs(v) > amax) { amax = Math.abs(v); amaxIdx = i; } });
      res.codes.forEach(function (c, i) {
        var x = state.values[i];
        var cell = el("li", "nfv-cell" + (i === amaxIdx ? " nfv-max" : "") + (c.value === 0 && x !== 0 ? " nfv-zero" : ""));
        cell.appendChild(el("div", "nfv-ci", "#" + i + (i === amaxIdx ? " (amax)" : "")));
        cell.appendChild(el("div", null, "x " + fmt(x)));
        cell.appendChild(el("div", "nfv-errv", "x/s " + fmt(x / res.scale)));
        cell.appendChild(bitBoxes(c.bits, f, true));
        cell.appendChild(el("div", null, "= " + fmt(c.decoded)));
        cell.appendChild(el("div", "nfv-errv", "err " + (c.err > 0 ? "+" : "") + fmt(c.err)));
        cell.setAttribute("aria-label", "Value " + i + ": " + fmt(x) + ", code " + bitString(c.bits, f) + ", stored " + fmt(c.decoded) + ", error " + fmt(c.err));
        grid.appendChild(cell);
      });
      if (announce) {
        live.textContent = (state.elem === "e2m1" ? "MXFP4" : "MXFP8") + " block of " + n + " values: amax " + fmt(res.amax) +
          ", scale 2^" + res.exp + " (UE8M0 byte " + res.byte + "), mean absolute error " + short(sumAbs / n) +
          ", " + zeros + " values rounded to 0.";
      }
    }

    state.values = genBlock(0);
    renderOne(false);
    renderBlock(false);
  }

  function init() {
    var mounts = document.querySelectorAll('[data-viz="' + VIZ_ID + '"]');
    for (var i = 0; i < mounts.length; i++) mount(mounts[i]);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
