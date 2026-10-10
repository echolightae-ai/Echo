/* Five interactive labs, one per discipline. Canvas 2D, no dependencies. Each lab only runs while on screen,
   respects prefers-reduced-motion, and ends with a WhatsApp button that describes exactly what the visitor built. */
(function () {
  var reduced = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches, TAU = Math.PI * 2;
  var LBL = {
    en: { cta: "I want this at my event", colour: "Colour", auto: "Auto", pattern: "Pattern",
      lighting: { gobo: "Gobo", spokes: "Spokes", rings: "Rings", dots: "Dots", stars: "Stars", move: "Movement", sweep: "Sweep", fan: "Fan", cross: "Cross", pulse: "Pulse", n: "Fixtures", follow: "Move your cursor over the stage to steer the spots." },
      led: { content: "Content", plasma: "Plasma", head: "Headline", bars: "Bars", ring: "Ring", text: "Your headline", dens: "Pixel density", c: "Coarse", f: "Fine", u: "Ultra", bright: "Brightness" },
      sound: { splay: "Splay angle", boxes: "Boxes per side", level: "Level", room: "Room", hall: "Ballroom", arena: "Arena", ideal: "Ideal splay for this room", even: "Even coverage" },
      mapping: { stage: "Stage", survey: "Survey", map: "Map", warp: "Warp", content: "Content", wave: "Wave", pulse: "Pulse", stripes: "Stripes", letters: "Letters", text: "3 letters" },
      laser: { fig: "Figure", lis: "Lissajous", ring: "Ring", star: "Star", off: "Off", beams: "Beams", speed: "Speed", fan: "Fan", cross: "Cross", sweep: "Sweep", tunnel: "Tunnel" } },
    ar: { cta: "أريد هذا في فعاليتي", colour: "اللون", auto: "تلقائي", pattern: "النمط",
      lighting: { gobo: "غوبو", spokes: "أشعة", rings: "حلقات", dots: "نقاط", stars: "نجوم", move: "الحركة", sweep: "مسح", fan: "مروحة", cross: "تقاطع", pulse: "نبض", n: "عدد الأجهزة", follow: "حرّك المؤشر فوق المسرح لتوجيه الأضواء." },
      led: { content: "المحتوى", plasma: "بلازما", head: "عنوان", bars: "أعمدة", ring: "حلقة", text: "عنوانك", dens: "كثافة البكسل", c: "خشنة", f: "دقيقة", u: "فائقة", bright: "السطوع" },
      sound: { splay: "زاوية الانفراج", boxes: "عدد الصناديق", level: "المستوى", room: "القاعة", hall: "قاعة", arena: "ساحة", ideal: "الانفراج المثالي لهذه القاعة", even: "تغطية متساوية" },
      mapping: { stage: "المرحلة", survey: "مسح", map: "إسقاط", warp: "ضبط", content: "المحتوى", wave: "موجة", pulse: "نبض", stripes: "خطوط", letters: "حروف", text: "٣ حروف" },
      laser: { fig: "الشكل", lis: "ليساجو", ring: "حلقة", star: "نجمة", off: "إيقاف", beams: "الأشعة", speed: "السرعة", fan: "مروحة", cross: "تقاطع", sweep: "مسح", tunnel: "نفق" } } };
  var PAL = [["Aqua", [70, 150, 255], [140, 220, 255]], ["Amber", [255, 170, 60], [255, 90, 140]], ["Violet", [190, 80, 255], [60, 220, 255]], ["Red", [255, 60, 70], [255, 255, 255]], ["Lime", [140, 255, 70], [43, 196, 224]], ["White", [255, 255, 255], [190, 215, 255]]];
  var PALN = { en: PAL.map(function (p) { return p[0]; }), ar: ["أزرق", "عنبري", "بنفسجي", "أحمر", "ليموني", "أبيض"] };
  function rgba(c, a) { return "rgba(" + (c[0] | 0) + "," + (c[1] | 0) + "," + (c[2] | 0) + "," + a + ")"; }
  function hsl(h, s, l, a) { return "hsla(" + (((h % 360) + 360) % 360) + "," + s + "%," + l + "%," + (a == null ? 1 : a) + ")"; }
  function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }
  function el(tag, cls, text) { var n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; }

  function scene(canvas, S, draw) {
    var ctx = canvas.getContext("2d"), st = { t: 0, w: 0, h: 0, px: null, py: null }, run = false, vis = true;
    function size() { var r = canvas.getBoundingClientRect(), dpr = Math.min(window.devicePixelRatio || 1, 1.5); st.w = Math.max(2, Math.round(r.width * dpr)); st.h = Math.max(2, Math.round(r.height * dpr)); canvas.width = st.w; canvas.height = st.h; S._dirty = true; draw(ctx, st, S, 0); }
    function kick() { if (run || !vis || document.hidden || reduced) return; run = true; var last = performance.now(); (function loop(now) { if (!vis || document.hidden) { run = false; return; } var dt = Math.max(0, Math.min(0.05, (now - last) / 1000)); last = now; st.t += dt; draw(ctx, st, S, dt); requestAnimationFrame(loop); })(last); }
    canvas.addEventListener("pointermove", function (e) { var r = canvas.getBoundingClientRect(); st.px = (e.clientX - r.left) / r.width; st.py = (e.clientY - r.top) / r.height; }, { passive: true });
    canvas.addEventListener("pointerleave", function () { st.px = null; }, { passive: true });
    if (window.ResizeObserver) new ResizeObserver(size).observe(canvas); else addEventListener("resize", size);
    if (window.IntersectionObserver) new IntersectionObserver(function (e) { vis = e[0].isIntersecting; kick(); }, { threshold: 0.05 }).observe(canvas);
    document.addEventListener("visibilitychange", kick); size(); kick(); S._redraw = function () { if (reduced || !run) draw(ctx, st, S, 0); };
  }

  /* ---------- control builders ---------- */
  function seg(box, label, opts, S, key, after) { var g = el("div", "ctl"), row = el("div", "seg"); g.appendChild(el("span", "", label)); opts.forEach(function (o) { var b = el("button", "seg-b" + (S[key] === o[0] ? " on" : ""), o[1]); b.type = "button"; b.onclick = function () { S[key] = o[0]; [].forEach.call(row.children, function (x) { x.classList.remove("on"); }); b.classList.add("on"); if (after) after(); S._redraw && S._redraw(); }; row.appendChild(b); }); g.appendChild(row); box.appendChild(g); }
  function swatches(box, label, S, key, lang, allowAuto) { var g = el("div", "ctl"), row = el("div", "sw"); g.appendChild(el("span", "", label)); var bs = [];
    function mark() { bs.forEach(function (b, i) { b.classList.toggle("on", S[key] === i - (allowAuto ? 1 : 0)); }); }
    if (allowAuto) { var a = el("button", "swatch auto", ""); a.type = "button"; a.title = LBL[lang].auto; a.setAttribute("aria-label", LBL[lang].auto); a.onclick = function () { S[key] = -1; mark(); S._redraw && S._redraw(); }; bs.push(a); row.appendChild(a); }
    PAL.forEach(function (p, i) { var b = el("button", "swatch"); b.type = "button"; b.style.background = "linear-gradient(135deg," + rgba(p[1], 1) + "," + rgba(p[2], 1) + ")"; b.setAttribute("aria-label", PALN[lang][i]); b.onclick = function () { S[key] = i; mark(); S._redraw && S._redraw(); }; bs.push(b); row.appendChild(b); }); g.appendChild(row); box.appendChild(g); mark(); }
  function range(box, label, min, max, step, S, key, fmt) { var g = el("div", "ctl"), r = el("input"), o = el("em", "", ""); r.type = "range"; r.min = min; r.max = max; r.step = step || 1; r.value = S[key]; r.setAttribute("aria-label", label); var u = function () { S[key] = +r.value; o.textContent = fmt ? fmt(S[key]) : ""; S._redraw && S._redraw(); }; r.addEventListener("input", u); o.textContent = fmt ? fmt(S[key]) : ""; g.appendChild(el("span", "", label)); g.appendChild(r); g.appendChild(o); box.appendChild(g); }
  function text(box, label, S, key, max, ph) { var g = el("div", "ctl"), i = el("input"); i.type = "text"; i.maxLength = max; i.value = S[key]; i.placeholder = ph || ""; i.setAttribute("aria-label", label); i.addEventListener("input", function () { S[key] = i.value; S._redraw && S._redraw(); }); g.appendChild(el("span", "", label)); g.appendChild(i); box.appendChild(g); }
  function cta(box, lang, msg) { var a = el("a", "btn btn-wa small", LBL[lang].cta); a.target = "_blank"; a.rel = "noopener"; a.href = "#"; a.addEventListener("click", function () { a.href = FX.wa ? FX.wa(msg()) : "#"; }); a.addEventListener("focus", function () { a.href = FX.wa ? FX.wa(msg()) : "#"; }); box.appendChild(a); }

  /* ---------- 1. STAGE LIGHTING ---------- */
  var CUES = [["CUE 12 · VERSE", 0], ["CUE 13 · CHORUS", 1], ["CUE 14 · BREAK", 2], ["CUE 15 · FINALE", 3]];
  function gobo(ctx, kind, r, t, col) {
    ctx.strokeStyle = rgba(col, 0.8); ctx.fillStyle = rgba(col, 0.8); ctx.lineWidth = Math.max(1, r * 0.09);
    if (kind === "spokes") { ctx.rotate(t * 1.2); for (var s = 0; s < 6; s++) { ctx.rotate(TAU / 6); ctx.beginPath(); ctx.moveTo(r * 0.25, 0); ctx.lineTo(r * 1.1, 0); ctx.stroke(); } }
    else if (kind === "rings") { for (var q = 1; q <= 3; q++) { ctx.beginPath(); ctx.arc(0, 0, r * q * 0.36 + Math.sin(t * 2 + q) * r * 0.05, 0, TAU); ctx.stroke(); } }
    else if (kind === "dots") { ctx.rotate(t * 0.6); for (var d = 0; d < 9; d++) { var a = d / 9 * TAU; ctx.beginPath(); ctx.arc(Math.cos(a) * r * 0.75, Math.sin(a) * r * 0.75, r * 0.12, 0, TAU); ctx.fill(); } ctx.beginPath(); ctx.arc(0, 0, r * 0.14, 0, TAU); ctx.fill(); }
    else if (kind === "stars") { ctx.rotate(t * 0.9); ctx.beginPath(); for (var p = 0; p < 8; p++) { var rr = p % 2 ? r * 0.35 : r * 1.05, aa = p / 8 * TAU; p ? ctx.lineTo(Math.cos(aa) * rr, Math.sin(aa) * rr) : ctx.moveTo(Math.cos(aa) * rr, Math.sin(aa) * rr); } ctx.closePath(); ctx.stroke(); }
  }
  function lighting(c, box, lang) {
    var S = { pal: -1, gobo: "spokes", move: "sweep", n: 7, cueT: 0, cue: 0, cur: [PAL[0][1].slice(), PAL[0][2].slice()] }, L = LBL[lang], X = L.lighting;
    swatches(box, L.colour, S, "pal", lang, true); seg(box, X.gobo, [["spokes", X.spokes], ["rings", X.rings], ["dots", X.dots], ["stars", X.stars]], S, "gobo"); seg(box, X.move, [["sweep", X.sweep], ["fan", X.fan], ["cross", X.cross], ["pulse", X.pulse]], S, "move"); range(box, X.n, 3, 10, 1, S, "n", function (v) { return v; });
    cta(box, lang, function () { return FX.msg("lighting", [S.pal < 0 ? L.auto : PALN[lang][S.pal], X[S.gobo], X[S.move], S.n + " " + X.n]); });
    scene(c, S, function (ctx, st, S, dt) {
      var w = st.w, h = st.h, t = st.t; S.cueT += dt; if (S.cueT > 4.2) { S.cueT = 0; S.cue = (S.cue + 1) % 4; }
      var ti = S.pal < 0 ? S.cue : S.pal, tg = [PAL[ti][1], PAL[ti][2]]; for (var i = 0; i < 2; i++) for (var k = 0; k < 3; k++) S.cur[i][k] += (tg[i][k] - S.cur[i][k]) * Math.min(1, dt * 3 + (dt ? 0 : 1));
      ctx.globalCompositeOperation = "source-over"; var g = ctx.createLinearGradient(0, 0, 0, h); g.addColorStop(0, "#04050a"); g.addColorStop(1, "#0b0d16"); ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
      var floorY = h * 0.78; ctx.fillStyle = "rgba(255,255,255,0.03)"; ctx.fillRect(0, floorY, w, h - floorY); ctx.globalCompositeOperation = "lighter"; var n = S.n, trussY = h * 0.1;
      for (var f = 0; f < n; f++) {
        var u = n > 1 ? f / (n - 1) : 0.5, fx = w * (0.1 + 0.8 * u), col = S.cur[f % 2], tx, ty;
        if (st.px != null) { tx = st.px * w + (f - (n - 1) / 2) * w * 0.012; ty = Math.max(floorY * 0.9, st.py * h); }
        else if (S.move === "fan") { tx = w * (0.15 + 0.7 * u) + Math.sin(t * 0.6) * w * 0.05; ty = floorY + h * 0.06; }
        else if (S.move === "cross") { tx = w * (1 - u) * 0.8 + w * 0.1 + Math.sin(t * 0.9 + f) * w * 0.05; ty = floorY + h * 0.05 + Math.cos(t * 0.8 + f) * h * 0.03; }
        else if (S.move === "pulse") { tx = fx + Math.sin(t * 0.4 + f) * w * 0.03; ty = floorY + h * 0.07 + Math.sin(t * 3 + f) * h * 0.03; }
        else { tx = w * 0.5 + Math.sin(t * 0.7 + f * 0.9) * w * 0.34 + (f - (n - 1) / 2) * w * 0.04; ty = floorY + Math.cos(t * 0.9 + f * 1.3) * h * 0.05 + h * 0.05; }
        var dx = tx - fx, dy = ty - trussY, Ln = Math.hypot(dx, dy), nx = -dy / Ln, ny = dx / Ln, sp = w * 0.026 * (n > 8 ? 0.8 : 1);
        var gr = ctx.createLinearGradient(fx, trussY, tx, ty); gr.addColorStop(0, rgba(col, 0.6)); gr.addColorStop(1, rgba(col, 0.08)); ctx.fillStyle = gr; ctx.beginPath(); ctx.moveTo(fx - nx * 3, trussY - ny * 3); ctx.lineTo(tx + nx * sp, ty + ny * sp * 0.4); ctx.lineTo(tx - nx * sp, ty - ny * sp * 0.4); ctx.lineTo(fx + nx * 3, trussY + ny * 3); ctx.fill();
        var ell = ctx.createRadialGradient(tx, ty, 0, tx, ty, sp * 1.8); ell.addColorStop(0, rgba(col, 0.8)); ell.addColorStop(1, rgba(col, 0)); ctx.save(); ctx.translate(tx, ty); ctx.scale(1, 0.32); ctx.fillStyle = ell; ctx.beginPath(); ctx.arc(0, 0, sp * 1.8, 0, TAU); ctx.fill(); gobo(ctx, S.gobo, sp * (S.gobo === "rings" ? 1.1 : 1), t * (f % 2 ? 1 : -1), col); ctx.restore();
      }
      ctx.globalCompositeOperation = "source-over"; ctx.fillStyle = "#1b1f2c"; ctx.fillRect(w * 0.04, trussY - 4, w * 0.92, 5);
      for (var q = 0; q < n; q++) { var x = w * (0.1 + 0.8 * (n > 1 ? q / (n - 1) : 0.5)); ctx.fillStyle = "#2a3042"; ctx.fillRect(x - w * 0.012, trussY, w * 0.024, w * 0.018); }
      ctx.fillStyle = "rgba(255,255,255,.7)"; ctx.font = (w * 0.022) + "px ui-monospace,monospace"; ctx.fillText(st.px != null ? "FOLLOW SPOT" : CUES[S.cue][0], w * 0.04, h * 0.94);
    });
  }

  /* ---------- 2. LED SCREENS ---------- */
  function hslToRgb(h, s, l) { var r, g, b; if (s === 0) r = g = b = l; else { var q = l < 0.5 ? l * (1 + s) : l + s - l * s, p = 2 * l - q, f = function (t) { if (t < 0) t += 1; if (t > 1) t -= 1; if (t < 1 / 6) return p + (q - p) * 6 * t; if (t < 1 / 2) return q; if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6; return p; }; r = f(h + 1 / 3); g = f(h); b = f(h - 1 / 3); } return [Math.round(r * 255), Math.round(g * 255), Math.round(b * 255)]; }
  function led(c, box, lang) {
    var S = { content: "auto", text: lang === "ar" ? "أهلاً" : "WELCOME", dens: 96, bright: 100 }, L = LBL[lang], X = L.led, off = document.createElement("canvas"), o = off.getContext("2d", { willReadFrequently: true });
    seg(box, X.content, [["auto", L.auto], ["plasma", X.plasma], ["head", X.head], ["bars", X.bars], ["ring", X.ring]], S, "content"); text(box, X.text, S, "text", 18, "WELCOME"); seg(box, X.dens, [[48, X.c], [96, X.f], [160, X.u]], S, "dens"); range(box, X.bright, 30, 100, 5, S, "bright", function (v) { return v + "%"; });
    cta(box, lang, function () { return FX.msg("led", [S.content === "auto" ? L.auto : X[S.content], "“" + S.text + "”", S.dens + " px"]); });
    scene(c, S, function (ctx, st, S) {
      var w = st.w, h = st.h, t = st.t, W = S.dens, H = Math.round(W * 9 / 16), ph = S.content === "auto" ? ["plasma", "head", "bars", "ring"][Math.floor(t / 5) % 4] : S.content, lt = t % 5;
      if (off.width !== W || off.height !== H) { off.width = W; off.height = H; }
      o.fillStyle = "#000"; o.fillRect(0, 0, W, H);
      if (ph === "plasma") { var im = o.createImageData(W, H), k = 96 / W; for (var y = 0; y < H; y++) for (var x = 0; x < W; x++) { var v = Math.sin(x * 0.12 * k + t * 1.4) + Math.sin(y * 0.2 * k - t) + Math.sin((x + y) * 0.1 * k + t * 0.7), rgb = hslToRgb(((v * 40 + 200 + t * 20) % 360) / 360, 0.9, 0.5), i = (y * W + x) * 4; im.data[i] = rgb[0]; im.data[i + 1] = rgb[1]; im.data[i + 2] = rgb[2]; im.data[i + 3] = 255; } o.putImageData(im, 0, 0); }
      else if (ph === "head") { o.fillStyle = "#07122b"; o.fillRect(0, 0, W, H); var tx = (S.text || " ").slice(0, 18); o.font = "bold 100px Arial"; o.textAlign = "center"; o.textBaseline = "middle"; var tw = o.measureText(tx).width || 1, fs = Math.min(H * 0.6, 100 * W * 0.9 / tw); o.font = "bold " + fs + "px Arial"; o.fillStyle = "#fff"; o.fillText(tx, W / 2 + Math.sin(t) * W * 0.02, H * 0.46); o.fillStyle = "#35c3dc"; o.fillRect(W * 0.2, H * 0.78, W * 0.6 * Math.min(1, ((t % 4) + 0.1) / 2), Math.max(1, H * 0.03)); }
      else if (ph === "bars") { var nb = Math.round(W / 4); for (var b = 0; b < nb; b++) { var bh = (0.25 + 0.7 * Math.abs(Math.sin(t * 2 + b * 0.6) * Math.cos(t * 0.7 + b))) * H; o.fillStyle = hsl(180 + b * 7 * (24 / nb), 85, 55); o.fillRect(b * (W / nb) + 0.5, H - bh, W / nb - 1, bh); } }
      else { var g2 = o.createRadialGradient(W / 2, H / 2, 0, W / 2, H / 2, H); g2.addColorStop(0, "#ff4d6d"); g2.addColorStop(1, "#1a0a2e"); o.fillStyle = g2; o.fillRect(0, 0, W, H); o.strokeStyle = "#fff"; o.lineWidth = Math.max(1, H * 0.06); o.beginPath(); o.arc(W / 2, H / 2, Math.max(1, H * 0.18 + Math.sin(t * 3) * H * 0.07 + lt * H * 0.05), 0, TAU); o.stroke(); }
      var px = o.getImageData(0, 0, W, H).data, br = S.bright / 100;
      ctx.fillStyle = "#05060a"; ctx.fillRect(0, 0, w, h); var pad = w * 0.05, ww = w - pad * 2, hh = ww * H / W; if (hh > h - pad * 2.2) { hh = h - pad * 2.2; ww = hh * W / H; } var ox = (w - ww) / 2, oy = (h - hh) / 2 - h * 0.02, cs = ww / W;
      ctx.fillStyle = "#0b0d14"; ctx.fillRect(ox - 6, oy - 6, ww + 12, hh + 12); var gap = cs > 5 ? 0.86 : 0.92;
      for (var yy = 0; yy < H; yy++) for (var xx = 0; xx < W; xx++) { var q = (yy * W + xx) * 4; ctx.fillStyle = "rgb(" + (px[q] * br | 0) + "," + (px[q + 1] * br | 0) + "," + (px[q + 2] * br | 0) + ")"; ctx.fillRect(ox + xx * cs, oy + yy * cs, cs * gap, cs * gap); }
      ctx.fillStyle = "rgba(255,255,255,.7)"; ctx.font = (w * 0.022) + "px ui-monospace,monospace"; ctx.fillText("LED WALL · " + W + "×" + H + " PIXELS", ox, oy + hh + w * 0.04);
    });
  }

  /* ---------- 3. SOUND ---------- */
  function sound(c, box, lang) {
    var S = { splay: 6, boxes: 8, level: 70, room: "hall" }, L = LBL[lang], X = L.sound;
    range(box, X.splay, 1, 16, 0.5, S, "splay", function (v) { return v + "°"; }); range(box, X.boxes, 4, 12, 1, S, "boxes", function (v) { return v; }); range(box, X.level, 20, 100, 5, S, "level", function (v) { return v + "%"; }); seg(box, X.room, [["hall", X.hall], ["arena", X.arena]], S, "room");
    var out = { even: 0 }; cta(box, lang, function () { return FX.msg("sound", [S.boxes + " boxes", S.splay + "° splay", S.room === "hall" ? X.hall : X.arena, X.even + " " + out.even + "%"]); });
    scene(c, S, function (ctx, st, S) {
      var w = st.w, h = st.h, t = st.t, ax = w * 0.1, ay = h * 0.1, n = S.boxes, sp = S.splay * Math.PI / 180, beat = Math.sin(t * 6.3) > 0.7 ? 1 : 0.6, lv = S.level / 100;
      var x0 = w * 0.28, x1 = S.room === "hall" ? w * 0.94 : w * 0.97, y0 = h * (S.room === "hall" ? 0.46 : 0.42), y1 = h * (S.room === "hall" ? 0.76 : 0.8), cols = 18, rows = 6;
      var tmin = 9, tmax = -9; [[x0, y0], [x1, y1], [x0, y1], [x1, y0]].forEach(function (p) { var a = Math.atan2(p[1] - ay, p[0] - ax); tmin = Math.min(tmin, a); tmax = Math.max(tmax, a); }); var span = tmax - tmin, ideal = span / Math.max(1, n - 1), cen = (tmin + tmax) / 2;
      ctx.fillStyle = "#05060a"; ctx.fillRect(0, 0, w, h); ctx.globalCompositeOperation = "lighter";
      for (var r = 0; r < 6; r++) { var rad = ((t * 0.5 + r / 6) % 1) * w * 0.85; ctx.strokeStyle = "rgba(53,195,220," + (0.45 * (1 - rad / (w * 0.85)) * beat * lv) + ")"; ctx.lineWidth = Math.max(1.5, w / 380); ctx.beginPath(); ctx.arc(ax, ay + h * 0.12, rad, tmin - 0.1, tmax + 0.1); ctx.stroke(); }
      var vals = [], i, j, tot = 0;
      for (i = 0; i < cols; i++) for (j = 0; j < rows; j++) { var x = x0 + (x1 - x0) * i / (cols - 1), y = y0 + (y1 - y0) * j / (rows - 1), dist = Math.hypot(x - ax, y - ay), a = Math.atan2(y - ay, x - ax), g = 0; for (var b = 0; b < n; b++) { var d = (a - (cen + (b - (n - 1) / 2) * sp)) / (Math.max(sp, 0.04) * 0.75); g += Math.exp(-d * d); } vals.push({ x: x, y: y, g: Math.min(1.6, g) }); tot += Math.min(1.6, g); }
      var mean = tot / vals.length, varr = 0; vals.forEach(function (v) { varr += (v.g - mean) * (v.g - mean); }); out.even = Math.max(0, Math.round(100 - Math.sqrt(varr / vals.length) / Math.max(mean, 0.05) * 100));
      vals.forEach(function (v) { var l = Math.min(1, v.g * lv * (0.78 + 0.22 * Math.sin(t * 6.3 - v.x / w * 9)) * beat * 1.1); ctx.fillStyle = hsl(190 - l * 160, 90, 28 + l * 38, 0.25 + l * 0.75); ctx.beginPath(); ctx.arc(v.x, v.y, w * 0.011 * (0.8 + l * 0.5), 0, TAU); ctx.fill(); });
      ctx.globalCompositeOperation = "source-over"; var bw = w * 0.05, bh = Math.min(h * 0.04, (h * 0.34) / n);
      for (var q = 0; q < n; q++) { var by = ay + q * bh * 1.1; ctx.save(); ctx.translate(ax, by); ctx.rotate((q - (n - 1) / 2) * sp * 0.6); ctx.fillStyle = "#1b2030"; ctx.strokeStyle = "#35c3dc"; ctx.lineWidth = 1; ctx.fillRect(-bw / 2, 0, bw, bh); ctx.strokeRect(-bw / 2, 0, bw, bh); ctx.restore(); }
      ctx.strokeStyle = "#2a3042"; ctx.beginPath(); ctx.moveTo(ax, 0); ctx.lineTo(ax, ay); ctx.stroke();
      var ns = 32; for (var s = 0; s < ns; s++) { var v2 = (0.2 + 0.8 * Math.abs(Math.sin(t * 3 + s * 0.45) * Math.cos(t * 1.3 + s * 0.2))) * (1 - s / ns * 0.5) * (0.4 + lv * 0.6), bh2 = v2 * h * 0.18; ctx.fillStyle = hsl(190 - s * 4, 85, 55); ctx.fillRect(w * 0.06 + s * w * 0.0275, h * 0.97 - bh2, w * 0.02, bh2); }
      ctx.fillStyle = "rgba(255,255,255,.75)"; ctx.font = (w * 0.021) + "px ui-monospace,monospace"; ctx.fillText(X.even.toUpperCase() + " " + out.even + "% · " + X.ideal.toUpperCase() + " " + (ideal * 180 / Math.PI).toFixed(1) + "°", w * 0.2, h * 0.37);
    });
  }

  /* ---------- 4. 3D MAPPING ---------- */
  function mapping(c, box, lang) {
    var S = { stage: "auto", content: "wave", pal: 2, text: lang === "ar" ? "أبو" : "UAE" }, L = LBL[lang], X = L.mapping, off = document.createElement("canvas"), COLS = 10, ROWS = 14; off.width = COLS; off.height = ROWS; var o = off.getContext("2d", { willReadFrequently: true });
    seg(box, X.stage, [["auto", L.auto], ["survey", X.survey], ["map", X.map], ["warp", X.warp]], S, "stage"); seg(box, X.content, [["wave", X.wave], ["pulse", X.pulse], ["stripes", X.stripes], ["letters", X.letters]], S, "content"); text(box, X.letters + " (" + X.text + ")", S, "text", 3, "UAE"); swatches(box, L.colour, S, "pal", lang, false);
    cta(box, lang, function () { return FX.msg("mapping", [S.stage === "auto" ? L.auto : X[S.stage], X[S.content], S.content === "letters" ? "“" + S.text + "”" : "", PALN[lang][S.pal]]); });
    scene(c, S, function (ctx, st, S) {
      var w = st.w, h = st.h, t = st.t, ph = S.stage === "auto" ? ["survey", "map", "map", "warp"][Math.floor(t / 4.5) % 4] : S.stage, p = PAL[S.pal], hue = (function () { var m = p[1]; return rgbHue(m); })();
      ctx.fillStyle = "#05060a"; ctx.fillRect(0, 0, w, h); var bw = Math.min(w * 0.46, h * 0.62), bh = bw * 1.5, bx = w * 0.5 - bw * 0.1, by = h * 0.06; if (bh > h * 0.86) { bh = h * 0.86; bw = bh / 1.5; }
      ctx.fillStyle = "#0d1019"; ctx.fillRect(bx, by, bw, bh); ctx.strokeStyle = "#2f3650"; ctx.lineWidth = 1.5; ctx.strokeRect(bx, by, bw, bh);
      if (S.content === "letters") { o.fillStyle = "#000"; o.fillRect(0, 0, COLS, ROWS); o.fillStyle = "#fff"; o.textAlign = "center"; o.textBaseline = "middle"; var tx = (S.text || " ").slice(0, 3); var f = 100; o.font = "bold " + f + "px Arial"; var wd = o.measureText(tx).width || 1; var fs = Math.min(ROWS * 0.45, f * COLS * 0.96 / wd); o.font = "bold " + fs + "px Arial"; o.fillText(tx, COLS / 2, ROWS / 2 + 0.3); } var px = S.content === "letters" ? o.getImageData(0, 0, COLS, ROWS).data : null;
      ctx.globalCompositeOperation = "lighter"; var mapped = ph !== "survey", pr = mapped ? 1 : 0;
      if (mapped) { var prx = w * 0.06, pry = h * 0.98, gr = ctx.createLinearGradient(prx, pry, bx + bw / 2, by + bh / 2); gr.addColorStop(0, "rgba(255,255,255,.2)"); gr.addColorStop(1, "rgba(255,255,255,0)"); ctx.fillStyle = gr; ctx.beginPath(); ctx.moveTo(prx, pry); ctx.lineTo(bx, by + bh * 0.1); ctx.lineTo(bx, by + bh); ctx.fill(); }
      for (var i = 0; i < COLS; i++) for (var j = 0; j < ROWS; j++) {
        var wx = bx + bw * (0.06 + i * (0.88 / COLS)), wy = by + bh * (0.04 + j * (0.92 / ROWS)), ww = bw * 0.88 / COLS * 0.68, wh = bh * 0.92 / ROWS * 0.62, v = 0;
        ctx.strokeStyle = mapped ? "rgba(255,255,255,.1)" : "#3a4260"; ctx.lineWidth = 1; ctx.strokeRect(wx, wy, ww, wh);
        if (!mapped) continue;
        if (S.content === "wave") v = (Math.sin(t * 1.6 - i * 0.7 + j * 0.35) + 1) / 2; else if (S.content === "pulse") v = (Math.sin(t * 3 - Math.hypot(i - COLS / 2, (j - ROWS / 2) * 0.7) * 1.1) + 1) / 2; else if (S.content === "stripes") v = (Math.floor(j + t * 3) % 3 === 0) ? 1 : 0.12; else v = px ? px[(j * COLS + i) * 4] / 255 : 0;
        ctx.fillStyle = hsl(hue + (S.content === "wave" ? i * 14 + j * 6 : 0), 90, 55, 0.12 + 0.8 * v * pr); ctx.fillRect(wx, wy, ww, wh);
      }
      if (ph === "survey") { var sy = by + ((t * 0.3) % 1) * bh; ctx.strokeStyle = "rgba(53,195,220,.85)"; ctx.beginPath(); ctx.moveTo(bx - 10, sy); ctx.lineTo(bx + bw + 10, sy); ctx.stroke(); }
      if (ph === "warp") { ctx.strokeStyle = "rgba(255,255,255,.4)"; for (var m = 0; m <= COLS; m += 2) { ctx.beginPath(); for (var q = 0; q <= 14; q++) { var xx = bx + bw * m / COLS + Math.sin(t * 2 + q * 0.5) * 3, yy = by + bh * q / 14; q ? ctx.lineTo(xx, yy) : ctx.moveTo(xx, yy); } ctx.stroke(); } ctx.fillStyle = "rgba(255,255,255,.8)"; [[0, 0], [1, 0], [1, 1], [0, 1]].forEach(function (cn) { ctx.fillRect(bx + bw * cn[0] - 4, by + bh * cn[1] - 4, 8, 8); }); }
      ctx.globalCompositeOperation = "source-over"; ctx.fillStyle = "rgba(255,255,255,.75)"; ctx.font = (w * 0.021) + "px ui-monospace,monospace"; ctx.fillText(ph === "survey" ? "SCAN · FACADE SURVEY" : ph === "map" ? "PROJECTION · CONTENT FITTED TO WINDOWS" : "WARP MESH · EDGE BLEND", w * 0.04, h * 0.95);
    });
  }
  function rgbHue(c) { var r = c[0] / 255, g = c[1] / 255, b = c[2] / 255, mx = Math.max(r, g, b), mn = Math.min(r, g, b), d = mx - mn, h = 0; if (d) { if (mx === r) h = ((g - b) / d) % 6; else if (mx === g) h = (b - r) / d + 2; else h = (r - g) / d + 4; } return h * 60; }

  /* ---------- 5. LASER & LIGHT SHOWS ---------- */
  function laser(c, box, lang) {
    var S = { pal: 0, pattern: "fan", n: 9, speed: 5, fig: "lis" }, L = LBL[lang], X = L.laser;
    swatches(box, L.colour, S, "pal", lang, false); seg(box, L.pattern, [["fan", X.fan], ["cross", X.cross], ["sweep", X.sweep], ["tunnel", X.tunnel]], S, "pattern"); seg(box, X.fig, [["lis", X.lis], ["ring", X.ring], ["star", X.star], ["off", X.off]], S, "fig"); range(box, X.beams, 3, 24, 1, S, "n", function (v) { return v; }); range(box, X.speed, 1, 10, 1, S, "speed", function (v) { return v; });
    cta(box, lang, function () { return FX.msg("laser", [PALN[lang][S.pal], X[S.pattern], S.n + " " + X.beams, X.fig + ": " + X[S.fig]]); });
    var cle = true;
    scene(c, S, function (ctx, st, S, dt) {
      var w = st.w, h = st.h; S.tt = (S.tt || 0) + dt * (S.speed / 5); var t = S.tt, p = PAL[S.pal], hue = rgbHue(p[1]); if (S._dirty) { ctx.fillStyle = "#04050a"; ctx.fillRect(0, 0, w, h); S._dirty = false; }
      ctx.globalCompositeOperation = "source-over"; ctx.fillStyle = "rgba(4,5,10," + (dt ? 0.22 : 0.9) + ")"; ctx.fillRect(0, 0, w, h); ctx.globalCompositeOperation = "lighter"; var n = S.n, L2 = Math.hypot(w, h) * 1.1;
      for (var i = 0; i < n; i++) {
        var f = n > 1 ? i / (n - 1) : 0.5, ox, oy, a, c1 = i % 2 ? p[1] : p[2];
        if (S.pattern === "cross") { var left = i % 2 === 0, k = Math.floor(i / 2) / Math.max(1, Math.ceil(n / 2) - 1); ox = left ? w * (0.08 + k * 0.28) : w * (0.92 - k * 0.28); oy = h; a = (left ? -1.05 : -2.09) + Math.sin(t * 0.7 + k * 3) * 0.42 * (left ? 1 : -1); }
        else if (S.pattern === "sweep") { ox = w * (0.04 + f * 0.92); oy = h; a = -Math.PI / 2 + Math.sin(t * 0.8 + f * 1.4) * 0.62; }
        else if (S.pattern === "tunnel") { var side = i % 3, kk = Math.floor(i / 3) / Math.max(1, Math.ceil(n / 3) - 1), cx = w * 0.5 + Math.sin(t * 0.5) * w * 0.1, cy = h * 0.4; ox = side === 0 ? 0 : side === 1 ? w : w * (0.1 + kk * 0.8); oy = side === 2 ? h : h * (0.2 + kk * 0.8); a = Math.atan2(cy - oy, cx - ox); }
        else { ox = w * (0.1 + f * 0.8); oy = h; a = -Math.PI / 2 + (f - 0.5) * 1.6 * (0.8 + 0.2 * Math.sin(t * 0.6)) + Math.sin(t * 1.3 + i) * 0.1; }
        var ex = ox + Math.cos(a) * L2, ey = oy + Math.sin(a) * L2, g = ctx.createLinearGradient(ox, oy, ex, ey); g.addColorStop(0, rgba(c1, 0.8)); g.addColorStop(1, rgba(c1, 0)); ctx.strokeStyle = g; ctx.lineWidth = Math.max(1.5, w / 500); ctx.beginPath(); ctx.moveTo(ox, oy); ctx.lineTo(ex, ey); ctx.stroke();
      }
      if (S.fig !== "off") {
        var cx2 = w / 2, cy2 = h * 0.4, R = Math.min(w, h) * 0.26, col = p[2]; ctx.strokeStyle = rgba(col, 0.95); ctx.lineWidth = Math.max(2, w / 330); ctx.shadowColor = rgba(col, 1); ctx.shadowBlur = 14; ctx.beginPath();
        for (var s = 0; s <= 240; s++) { var u = s / 240 * TAU, x2, y2; if (S.fig === "ring") { var rr = R * (0.8 + 0.12 * Math.sin(u * 6 + t * 2)); x2 = cx2 + Math.cos(u) * rr; y2 = cy2 + Math.sin(u) * rr * 0.8; } else if (S.fig === "star") { var r5 = R * (0.55 + 0.45 * ((Math.floor(u / TAU * 10) % 2) ? 0.45 : 1)); x2 = cx2 + Math.cos(u + t * 0.4) * r5; y2 = cy2 + Math.sin(u + t * 0.4) * r5 * 0.8; } else { x2 = cx2 + Math.sin(3 * u + t) * R; y2 = cy2 + Math.sin((2 + Math.sin(t * 0.3) * 0.5) * u) * R * 0.8; } s ? ctx.lineTo(x2, y2) : ctx.moveTo(x2, y2); } ctx.stroke(); ctx.shadowBlur = 0;
      }
      ctx.globalCompositeOperation = "source-over"; ctx.fillStyle = "rgba(255,255,255,.75)"; ctx.font = (w * 0.021) + "px ui-monospace,monospace"; ctx.fillText("LASER · " + S.pattern.toUpperCase() + " · " + S.n + " BEAMS", w * 0.04, h * 0.95);
    });
  }

  var FX = window.FX = { lighting: lighting, led: led, sound: sound, mapping: mapping, laser: laser, lang: "en", wa: null,
    msg: function (kind, parts) { var ar = FX.lang === "ar", names = ar ? { lighting: "إضاءة المسارح", led: "شاشات LED", sound: "الصوتيات", mapping: "الإسقاط ثلاثي الأبعاد", laser: "الليزر والعروض الضوئية" } : { lighting: "Stage Lighting", led: "LED Screens", sound: "Sound", mapping: "3D Mapping", laser: "Laser & Light Shows" }; return (ar ? "مرحباً إيكو لايت، جرّبت مختبر " : "Hello EchoLight, I tried your ") + names[kind] + (ar ? " وأريد شيئاً مثل هذا: " : " lab and want something like this: ") + parts.filter(Boolean).join(" · ") + (ar ? ". التاريخ / الموقع / الضيوف: " : ". Date / venue / guests: "); } };
  FX.init = function (root) { var lang = FX.lang || "en"; (root || document).querySelectorAll("canvas[data-fx]").forEach(function (c) { if (c._fx) return; c._fx = 1; var f = FX[c.getAttribute("data-fx")], wrap = c.closest(".fxwrap"); if (!f) return; var box = wrap ? wrap.querySelector(".labctl") : null; if (!box && wrap) { box = el("div", "labctl"); wrap.appendChild(box); } f(c, box || el("div"), lang); }); };
})();
