/* Live motion-graphic scenes, one per service. Canvas 2D, no dependencies.
   Each scene only runs while on screen and respects prefers-reduced-motion. */
(function () {
  var reduced = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  var TAU = Math.PI * 2;
  function rgba(c, a) { return "rgba(" + c[0] + "," + c[1] + "," + c[2] + "," + a + ")"; }
  function hsl(h, s, l, a) { return "hsla(" + (h % 360) + "," + s + "%," + l + "%," + (a == null ? 1 : a) + ")"; }

  function scene(canvas, init, draw) {
    var ctx = canvas.getContext("2d"), st = { t: 0, w: 0, h: 0, dpr: 1 }, run = false, vis = true, S = null;
    function size() {
      var r = canvas.getBoundingClientRect(); st.dpr = Math.min(window.devicePixelRatio || 1, 1.5);
      st.w = Math.max(2, Math.round(r.width * st.dpr)); st.h = Math.max(2, Math.round(r.height * st.dpr)); canvas.width = st.w; canvas.height = st.h;
      S = init(st, ctx); draw(ctx, st, S, 0);
    }
    function kick() {
      if (run || !vis || document.hidden || reduced) return; run = true; var last = performance.now();
      (function loop(now) { if (!vis || document.hidden) { run = false; return; } var dt = Math.max(0, Math.min(0.05, (now - last) / 1000)); last = now; st.t += dt; draw(ctx, st, S, dt); requestAnimationFrame(loop); })(last);
    }
    if (window.ResizeObserver) new ResizeObserver(size).observe(canvas); else addEventListener("resize", size);
    if (window.IntersectionObserver) new IntersectionObserver(function (e) { vis = e[0].isIntersecting; kick(); }, { threshold: 0.05 }).observe(canvas);
    document.addEventListener("visibilitychange", kick); size(); kick();
  }

  /* 1. STAGE LIGHTING: truss, moving heads with gobo patterns, cue changes */
  var CUES = [["CUE 12 · VERSE", [[70, 150, 255], [140, 220, 255]]], ["CUE 13 · CHORUS", [[255, 170, 60], [255, 90, 140]]], ["CUE 14 · BREAK", [[190, 80, 255], [60, 220, 255]]], ["CUE 15 · FINALE", [[255, 60, 70], [255, 255, 255]]]];
  function lighting(c) {
    scene(c, function (st) { return { cue: 0, cueT: 0, cur: [[70, 150, 255], [140, 220, 255]] }; }, function (ctx, st, S, dt) {
      var w = st.w, h = st.h, t = st.t; S.cueT += dt; if (S.cueT > 4.2) { S.cueT = 0; S.cue = (S.cue + 1) % CUES.length; }
      var tgt = CUES[S.cue][1]; for (var i = 0; i < 2; i++) for (var k = 0; k < 3; k++) S.cur[i][k] += (tgt[i][k] - S.cur[i][k]) * Math.min(1, dt * 2.5);
      ctx.globalCompositeOperation = "source-over"; var g = ctx.createLinearGradient(0, 0, 0, h); g.addColorStop(0, "#04050a"); g.addColorStop(1, "#0b0d16"); ctx.fillStyle = g; ctx.fillRect(0, 0, w, h);
      var floorY = h * 0.78; ctx.fillStyle = "rgba(255,255,255,0.03)"; ctx.fillRect(0, floorY, w, h - floorY);
      ctx.globalCompositeOperation = "lighter"; var n = 7, trussY = h * 0.1;
      for (var f = 0; f < n; f++) {
        var fx = w * (0.1 + 0.8 * f / (n - 1)), col = S.cur[f % 2].map(Math.round);
        var tx = w * 0.5 + Math.sin(t * 0.7 + f * 0.9) * w * 0.34 + (f - 3) * w * 0.04, ty = floorY + Math.cos(t * 0.9 + f * 1.3) * h * 0.05 + h * 0.05;
        var dx = tx - fx, dy = ty - trussY, L = Math.hypot(dx, dy), nx = -dy / L, ny = dx / L, sp = w * 0.026;
        var gr = ctx.createLinearGradient(fx, trussY, tx, ty); gr.addColorStop(0, rgba(col, 0.55)); gr.addColorStop(1, rgba(col, 0.06));
        ctx.fillStyle = gr; ctx.beginPath(); ctx.moveTo(fx - nx * 3, trussY - ny * 3); ctx.lineTo(tx + nx * sp, ty + ny * sp * 0.4); ctx.lineTo(tx - nx * sp, ty - ny * sp * 0.4); ctx.lineTo(fx + nx * 3, trussY + ny * 3); ctx.fill();
        var ell = ctx.createRadialGradient(tx, ty, 0, tx, ty, sp * 1.7); ell.addColorStop(0, rgba(col, 0.55)); ell.addColorStop(1, rgba(col, 0));
        ctx.save(); ctx.translate(tx, ty); ctx.scale(1, 0.32); ctx.fillStyle = ell; ctx.beginPath(); ctx.arc(0, 0, sp * 1.7, 0, TAU); ctx.fill();
        ctx.strokeStyle = rgba(col, 0.75); ctx.lineWidth = Math.max(1, w / 900); ctx.rotate(t * (f % 2 ? 1.2 : -1.2));   // gobo: spinning spokes
        for (var s = 0; s < 6; s++) { ctx.rotate(TAU / 6); ctx.beginPath(); ctx.moveTo(sp * 0.25, 0); ctx.lineTo(sp * 1.1, 0); ctx.stroke(); }
        ctx.restore();
      }
      ctx.globalCompositeOperation = "source-over"; ctx.fillStyle = "#1b1f2c"; ctx.fillRect(w * 0.04, trussY - 4, w * 0.92, 5);
      for (var q = 0; q < n; q++) { var x = w * (0.1 + 0.8 * q / (n - 1)); ctx.fillStyle = "#2a3042"; ctx.fillRect(x - w * 0.012, trussY, w * 0.024, w * 0.018); }
      ctx.fillStyle = "rgba(255,255,255,.7)"; ctx.font = (w * 0.022) + "px ui-monospace,monospace"; ctx.fillText(CUES[S.cue][0], w * 0.04, h * 0.94);
    });
  }

  /* 2. LED SCREENS: real pixel grid sampled from a low-res content canvas */
  function led(c) {
    var off = document.createElement("canvas"), W = 96, H = 54; off.width = W; off.height = H; var o = off.getContext("2d", { willReadFrequently: true });
    scene(c, function () { return {}; }, function (ctx, st, S) {
      var w = st.w, h = st.h, t = st.t, ph = Math.floor(t / 5) % 4, lt = t % 5;
      o.fillStyle = "#000"; o.fillRect(0, 0, W, H);
      if (ph === 0) { var im = o.createImageData(W, H); for (var y = 0; y < H; y++) for (var x = 0; x < W; x++) { var v = Math.sin(x * 0.12 + t * 1.4) + Math.sin(y * 0.2 - t) + Math.sin((x + y) * 0.1 + t * 0.7); var hh = (v * 40 + 200 + t * 20) % 360; var rgb = hslToRgb(hh / 360, 0.9, 0.5); var i = (y * W + x) * 4; im.data[i] = rgb[0]; im.data[i + 1] = rgb[1]; im.data[i + 2] = rgb[2]; im.data[i + 3] = 255; } o.putImageData(im, 0, 0); }
      else if (ph === 1) { o.fillStyle = "#07122b"; o.fillRect(0, 0, W, H); o.fillStyle = "#fff"; o.font = "bold 22px Arial"; o.textAlign = "center"; o.fillText("WELCOME", W / 2 + Math.sin(t) * 3, H / 2 + 2); o.fillStyle = "#35c3dc"; o.fillRect(W * 0.2, H * 0.68, W * 0.6 * Math.min(1, lt / 2), 2); }
      else if (ph === 2) { for (var b = 0; b < 24; b++) { var bh = (0.25 + 0.7 * Math.abs(Math.sin(t * 2 + b * 0.6) * Math.cos(t * 0.7 + b))) * H; o.fillStyle = hsl(180 + b * 7, 85, 55); o.fillRect(b * 4 + 0.5, H - bh, 3, bh); } }
      else { var g2 = o.createRadialGradient(W / 2, H / 2, 0, W / 2, H / 2, H); g2.addColorStop(0, "#ff4d6d"); g2.addColorStop(1, "#1a0a2e"); o.fillStyle = g2; o.fillRect(0, 0, W, H); o.strokeStyle = "#fff"; o.lineWidth = 3; o.beginPath(); o.arc(W / 2, H / 2, 10 + Math.sin(t * 3) * 4 + lt * 3, 0, TAU); o.stroke(); }
      var px = o.getImageData(0, 0, W, H).data;
      ctx.fillStyle = "#05060a"; ctx.fillRect(0, 0, w, h);
      var pad = w * 0.05, ww = w - pad * 2, hh2 = ww * H / W; if (hh2 > h - pad * 2.2) { hh2 = h - pad * 2.2; ww = hh2 * W / H; } var ox = (w - ww) / 2, oy = (h - hh2) / 2 - h * 0.02, cs = ww / W;
      ctx.fillStyle = "#0b0d14"; ctx.fillRect(ox - 6, oy - 6, ww + 12, hh2 + 12);
      for (var yy = 0; yy < H; yy++) for (var xx = 0; xx < W; xx++) { var k = (yy * W + xx) * 4; ctx.fillStyle = "rgb(" + px[k] + "," + px[k + 1] + "," + px[k + 2] + ")"; ctx.fillRect(ox + xx * cs, oy + yy * cs, cs * 0.86, cs * 0.86); }
      ctx.fillStyle = "rgba(255,255,255,.7)"; ctx.font = (w * 0.022) + "px ui-monospace,monospace"; ctx.fillText("LED WALL · FINE-PITCH · 1920×1080 MAPPED", ox, oy + hh2 + w * 0.04);
    });
  }
  function hslToRgb(h, s, l) { var r, g, b; if (s === 0) r = g = b = l; else { var q = l < 0.5 ? l * (1 + s) : l + s - l * s, p = 2 * l - q; var f = function (t) { if (t < 0) t += 1; if (t > 1) t -= 1; if (t < 1 / 6) return p + (q - p) * 6 * t; if (t < 1 / 2) return q; if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6; return p; }; r = f(h + 1 / 3); g = f(h); b = f(h - 1 / 3); } return [Math.round(r * 255), Math.round(g * 255), Math.round(b * 255)]; }

  /* 3. SOUND: line-array coverage over an audience, with a live spectrum */
  function sound(c) {
    scene(c, function () { return {}; }, function (ctx, st) {
      var w = st.w, h = st.h, t = st.t; ctx.fillStyle = "#05060a"; ctx.fillRect(0, 0, w, h);
      var ax = w * 0.1, ay = h * 0.1, boxes = 8, beat = (Math.sin(t * 6.3) > 0.7 ? 1 : 0.6);
      ctx.globalCompositeOperation = "lighter";
      for (var r = 0; r < 7; r++) { var rad = ((t * 0.5 + r / 7) % 1) * w * 0.85; var a0 = -0.15, a1 = 1.05; ctx.strokeStyle = "rgba(53,195,220," + (0.5 * (1 - rad / (w * 0.85)) * beat) + ")"; ctx.lineWidth = Math.max(1.5, w / 380); ctx.beginPath(); ctx.arc(ax, ay + h * 0.12, rad, a0, a1); ctx.stroke(); }
      var cols = 18, rows = 6;
      for (var i = 0; i < cols; i++) for (var j = 0; j < rows; j++) {
        var x = w * (0.28 + 0.66 * i / (cols - 1)), y = h * (0.46 + 0.28 * j / (rows - 1)), d = Math.hypot(x - ax, y - ay) / w, lvl = Math.max(0, 1 - d * 0.9) * (0.75 + 0.25 * Math.sin(t * 6.3 - d * 9)) * beat;
        ctx.fillStyle = hsl(190 - lvl * 160, 90, 30 + lvl * 35, 0.35 + lvl * 0.65); ctx.beginPath(); ctx.arc(x, y, w * 0.011 * (0.8 + lvl * 0.5), 0, TAU); ctx.fill();
      }
      ctx.globalCompositeOperation = "source-over";
      for (var b = 0; b < boxes; b++) { var by = ay + b * h * 0.045, bw = w * 0.05, ang = b * 0.06; ctx.save(); ctx.translate(ax, by); ctx.rotate(ang); ctx.fillStyle = "#1b2030"; ctx.strokeStyle = "#35c3dc"; ctx.lineWidth = 1; ctx.fillRect(-bw / 2, 0, bw, h * 0.038); ctx.strokeRect(-bw / 2, 0, bw, h * 0.038); ctx.restore(); }
      ctx.strokeStyle = "#2a3042"; ctx.beginPath(); ctx.moveTo(ax, 0); ctx.lineTo(ax, ay); ctx.stroke();
      var n = 32; for (var s = 0; s < n; s++) { var v = (0.2 + 0.8 * Math.abs(Math.sin(t * 3 + s * 0.45) * Math.cos(t * 1.3 + s * 0.2))) * (1 - s / n * 0.5); var bh2 = v * h * 0.18; ctx.fillStyle = hsl(190 - s * 4, 85, 55); ctx.fillRect(w * 0.06 + s * w * 0.0275, h * 0.97 - bh2, w * 0.02, bh2); }
      ctx.fillStyle = "rgba(255,255,255,.7)"; ctx.font = (w * 0.022) + "px ui-monospace,monospace"; ctx.fillText("LINE ARRAY · EVEN COVERAGE", w * 0.28, h * 0.4);
    });
  }

  /* 4. 3D MAPPING: a facade goes from wireframe to warped projection */
  function mapping(c) {
    scene(c, function () { return {}; }, function (ctx, st) {
      var w = st.w, h = st.h, t = st.t, ph = (t % 15) / 15; ctx.fillStyle = "#05060a"; ctx.fillRect(0, 0, w, h);
      var bx = w * 0.3, by = h * 0.08, bw = w * 0.5, bh = h * 0.78, cols = 6, rows = 7;
      ctx.fillStyle = "#0d1019"; ctx.fillRect(bx, by, bw, bh); ctx.strokeStyle = "#2f3650"; ctx.lineWidth = 1.5; ctx.strokeRect(bx, by, bw, bh);
      var mapped = ph > 0.3; var proj = Math.max(0, Math.min(1, (ph - 0.3) / 0.15));
      ctx.globalCompositeOperation = "lighter";
      if (mapped) { var px = w * 0.08, py = h * 0.98, gr = ctx.createLinearGradient(px, py, bx + bw / 2, by + bh / 2); gr.addColorStop(0, "rgba(255,255,255," + 0.18 * proj + ")"); gr.addColorStop(1, "rgba(255,255,255,0)"); ctx.fillStyle = gr; ctx.beginPath(); ctx.moveTo(px, py); ctx.lineTo(bx, by); ctx.lineTo(bx, by + bh); ctx.fill(); }
      for (var i = 0; i < cols; i++) for (var j = 0; j < rows; j++) {
        var wx = bx + bw * (0.07 + i * (0.86 / cols)), wy = by + bh * (0.05 + j * (0.9 / rows)), ww = bw * 0.86 / cols * 0.7, wh = bh * 0.9 / rows * 0.62;
        ctx.strokeStyle = mapped ? "rgba(255,255,255,.12)" : "#3a4260"; ctx.lineWidth = 1; ctx.strokeRect(wx, wy, ww, wh);
        if (mapped) { var hue = (t * 40 + i * 28 + j * 18 + Math.sin(t + j) * 30) % 360, sweep = (Math.sin(t * 1.4 - i * 0.7 + j * 0.3) + 1) / 2; ctx.fillStyle = hsl(hue, 90, 55, (0.25 + 0.6 * sweep) * proj); ctx.fillRect(wx, wy, ww, wh); }
      }
      if (ph < 0.3) { var sy = by + ((ph / 0.3) * 2 % 1) * bh; ctx.strokeStyle = "rgba(53,195,220,.8)"; ctx.beginPath(); ctx.moveTo(bx - 10, sy); ctx.lineTo(bx + bw + 10, sy); ctx.stroke(); }
      if (ph > 0.75) { ctx.strokeStyle = "rgba(255,255,255,.35)"; for (var m = 0; m <= cols; m++) { ctx.beginPath(); for (var q = 0; q <= 12; q++) { var xx = bx + bw * m / cols + Math.sin(t * 2 + q * 0.5) * 3, yy = by + bh * q / 12; q ? ctx.lineTo(xx, yy) : ctx.moveTo(xx, yy); } ctx.stroke(); } }
      ctx.globalCompositeOperation = "source-over"; ctx.fillStyle = "rgba(255,255,255,.7)"; ctx.font = (w * 0.022) + "px ui-monospace,monospace";
      ctx.fillText(ph < 0.3 ? "SCAN · FACADE SURVEY" : ph < 0.75 ? "PROJECTION · CONTENT FITTED TO WINDOWS" : "WARP MESH · EDGE BLEND", w * 0.04, h * 0.95);
    });
  }

  /* 5. LASER & LIGHT SHOWS: beam fan plus a drifting lissajous figure on haze */
  function laser(c) {
    scene(c, function (st, ctx) { ctx.fillStyle = "#04050a"; ctx.fillRect(0, 0, st.w, st.h); return {}; }, function (ctx, st) {
      var w = st.w, h = st.h, t = st.t; ctx.globalCompositeOperation = "source-over"; ctx.fillStyle = "rgba(4,5,10,0.22)"; ctx.fillRect(0, 0, w, h);
      ctx.globalCompositeOperation = "lighter"; var hue = (t * 30) % 360, n = 9;
      for (var i = 0; i < n; i++) { var f = i / (n - 1), a = -Math.PI / 2 + (f - 0.5) * 1.6 * (0.8 + 0.2 * Math.sin(t * 0.6)) + Math.sin(t * 1.3 + i) * 0.1, x = w * (0.12 + 0.76 * f), L = h * 1.2; var g = ctx.createLinearGradient(x, h, x + Math.cos(a) * L, h + Math.sin(a) * L); g.addColorStop(0, hsl(hue + i * 12, 100, 60, 0.75)); g.addColorStop(1, hsl(hue + i * 12, 100, 60, 0)); ctx.strokeStyle = g; ctx.lineWidth = Math.max(1.5, w / 500); ctx.beginPath(); ctx.moveTo(x, h); ctx.lineTo(x + Math.cos(a) * L, h + Math.sin(a) * L); ctx.stroke(); }
      var cx = w / 2, cy = h * 0.4, R = Math.min(w, h) * 0.26, A = 3, B = 2 + Math.sin(t * 0.3) * 0.5; ctx.strokeStyle = hsl(hue + 160, 100, 65, 0.95); ctx.lineWidth = Math.max(2, w / 330); ctx.shadowColor = hsl(hue + 160, 100, 60, 1); ctx.shadowBlur = 14; ctx.beginPath();
      for (var s = 0; s <= 240; s++) { var u = s / 240 * TAU, x2 = cx + Math.sin(A * u + t) * R, y2 = cy + Math.sin(B * u) * R * 0.8; s ? ctx.lineTo(x2, y2) : ctx.moveTo(x2, y2); } ctx.stroke(); ctx.shadowBlur = 0;
      ctx.globalCompositeOperation = "source-over"; ctx.fillStyle = "rgba(255,255,255,.7)"; ctx.font = (w * 0.022) + "px ui-monospace,monospace"; ctx.fillText("LASER · ILDA SCAN PATTERN", w * 0.04, h * 0.95);
    });
  }

  window.FX = { lighting: lighting, led: led, sound: sound, mapping: mapping, laser: laser };
  document.addEventListener("DOMContentLoaded", function () { document.querySelectorAll("canvas[data-fx]").forEach(function (c) { var f = window.FX[c.getAttribute("data-fx")]; if (f) f(c); }); });
})();
