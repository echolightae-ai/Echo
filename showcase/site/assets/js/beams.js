/* Live laser / moving-head beam renderer (2D canvas, additive light). No dependencies. */
(function () {
  function hex(h) { h = h.replace("#", ""); return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)]; }
  function mix(a, b, t) { return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t]; }

  function Beams(canvas, opts) {
    this.c = canvas; this.ctx = canvas.getContext("2d");
    this.o = Object.assign({ count: 9, pattern: "fan", speed: 1, pointer: true, haze: true, dprCap: 1.5 }, opts || {});
    this.cols = (opts && opts.colors || ["#2bc4e0", "#5b7cff", "#b46bff", "#ffffff"]).map(hex);
    this.target = this.cols.map(function (c) { return c.slice(); });
    this.px = null; this.py = null; this.pw = 0; this.pwT = 0; this.t = Math.random() * 100; this.run = false; this.vis = true;
    this.motes = []; var i; for (i = 0; i < 38; i++) this.motes.push({ x: Math.random(), y: Math.random(), r: Math.random() * 1.6 + 0.4, s: Math.random() * 0.02 + 0.004, p: Math.random() * 6 });
    this.reduced = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
    var self = this;
    this.resize = function () {
      var dpr = Math.min(window.devicePixelRatio || 1, self.o.dprCap), r = self.c.getBoundingClientRect();
      var small = r.width < 700 ? 0.75 : 1;
      self.c.width = Math.max(2, Math.round(r.width * dpr * small)); self.c.height = Math.max(2, Math.round(r.height * dpr * small));
      self.w = self.c.width; self.h = self.c.height; self.draw(0);
    };
    if (window.ResizeObserver) new ResizeObserver(this.resize).observe(canvas); else addEventListener("resize", this.resize);
    if (this.o.pointer) {
      var host = this.o.host || canvas.parentElement;
      host.addEventListener("pointermove", function (e) { var r = canvas.getBoundingClientRect(); self.px = (e.clientX - r.left) / r.width; self.py = (e.clientY - r.top) / r.height; self.pwT = 1; }, { passive: true });
      host.addEventListener("pointerleave", function () { self.pwT = 0; }, { passive: true });
    }
    if (window.IntersectionObserver) new IntersectionObserver(function (en) { self.vis = en[0].isIntersecting; self.kick(); }, { threshold: 0.01 }).observe(canvas);
    document.addEventListener("visibilitychange", function () { self.kick(); });
    this.resize(); this.kick();
  }

  Beams.prototype.set = function (k, v) { this.o[k] = v; };
  Beams.prototype.setColors = function (c) { this.target = c.map(hex); };
  Beams.prototype.kick = function () {
    if (this.run || !this.vis || document.hidden || this.reduced) return;
    this.run = true; var self = this, last = performance.now();
    (function loop(now) {
      if (!self.vis || document.hidden) { self.run = false; return; }
      var dt = Math.max(0, Math.min(0.05, (now - last) / 1000)); last = now; self.draw(dt); requestAnimationFrame(loop);
    })(last);
  };

  /* where beam i starts and which way it points at time t */
  Beams.prototype.geom = function (i, n, t) {
    var f = n > 1 ? i / (n - 1) : 0.5, W = this.w, H = this.h, p = this.o.pattern, ox, oy, a;
    if (p === "cross") {                    // two banks that cross over the middle
      var left = i % 2 === 0, k = Math.floor(i / 2) / Math.max(1, Math.ceil(n / 2) - 1);
      ox = left ? W * (0.08 + k * 0.28) : W * (0.92 - k * 0.28); oy = H * 1.02;
      a = (left ? -1.05 : -2.09) + Math.sin(t * 0.9 + i) * 0.5 * (left ? 1 : -1) * 0 + Math.sin(t * 0.7 + k * 3) * 0.42 * (left ? 1 : -1);
    } else if (p === "sweep") {             // parallel curtain sweeping together
      ox = W * (0.04 + f * 0.92); oy = H * 1.02; a = -Math.PI / 2 + Math.sin(t * 0.8 + f * 1.4) * 0.62;
    } else if (p === "tunnel") {            // beams from the edges converge to a point
      var side = i % 3; var kk = Math.floor(i / 3) / Math.max(1, Math.ceil(n / 3) - 1);
      var cx = W * 0.5 + Math.sin(t * 0.5) * W * 0.12, cy = H * 0.38 + Math.cos(t * 0.4) * H * 0.06;
      ox = side === 0 ? 0 : side === 1 ? W : W * (0.1 + kk * 0.8); oy = side === 2 ? H * 1.02 : H * (0.2 + kk * 0.8);
      a = Math.atan2(cy - oy, cx - ox) + Math.sin(t * 1.3 + i) * 0.05;
    } else {                                // fan
      ox = W * (0.1 + f * 0.8); oy = H * 1.02;
      a = -Math.PI / 2 + (f - 0.5) * 1.5 * (0.75 + 0.25 * Math.sin(t * 0.35)) + Math.sin(t * 1.1 + i * 0.9) * 0.18;
    }
    if (this.o.pointer && this.pw > 0.01 && this.px != null) {   // follow-spot: beams lean toward the pointer
      var tx = this.px * W, ty = this.py * H, ta = Math.atan2(ty - oy, tx - ox);
      var d = Math.atan2(Math.sin(ta - a), Math.cos(ta - a)); a += d * 0.55 * this.pw;
    }
    return { x: ox, y: oy, a: a };
  };

  Beams.prototype.draw = function (dt) {
    var ctx = this.ctx, W = this.w, H = this.h, i, n = this.o.count;
    this.t += dt * this.o.speed;
    for (i = 0; i < this.cols.length; i++) this.cols[i] = mix(this.cols[i], this.target[i % this.target.length], Math.min(1, dt * 2.2));
    this.pw += (this.pwT - this.pw) * Math.min(1, dt * 4);
    ctx.globalCompositeOperation = "source-over"; ctx.fillStyle = "#04050a"; ctx.fillRect(0, 0, W, H);
    ctx.globalCompositeOperation = "lighter";
    if (this.o.haze) {                       // drifting haze pools
      for (i = 0; i < 3; i++) {
        var hx = W * (0.2 + 0.3 * i + Math.sin(this.t * 0.07 + i * 2) * 0.12), hy = H * (0.62 + Math.cos(this.t * 0.05 + i) * 0.08), c = this.cols[i % this.cols.length];
        var g = ctx.createRadialGradient(hx, hy, 0, hx, hy, Math.max(W, H) * 0.5);
        g.addColorStop(0, "rgba(" + (c[0] | 0) + "," + (c[1] | 0) + "," + (c[2] | 0) + ",0.16)"); g.addColorStop(1, "rgba(0,0,0,0)");
        ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
      }
    }
    var len = Math.hypot(W, H) * 1.15;
    for (i = 0; i < n; i++) {
      var b = this.geom(i, n, this.t), c = this.cols[i % this.cols.length], ex = b.x + Math.cos(b.a) * len, ey = b.y + Math.sin(b.a) * len;
      var spread = (0.016 + 0.007 * Math.sin(this.t * 0.9 + i)) * (this.o.pattern === "tunnel" ? 0.8 : 1);
      var px = -Math.sin(b.a), py = Math.cos(b.a), wEnd = len * spread * 3.2, rgb = (c[0] | 0) + "," + (c[1] | 0) + "," + (c[2] | 0);
      var g2 = ctx.createLinearGradient(b.x, b.y, ex, ey);
      g2.addColorStop(0, "rgba(" + rgb + ",0.85)"); g2.addColorStop(0.55, "rgba(" + rgb + ",0.26)"); g2.addColorStop(1, "rgba(" + rgb + ",0)");
      ctx.fillStyle = g2; ctx.beginPath(); ctx.moveTo(b.x + px * 2, b.y + py * 2); ctx.lineTo(ex + px * wEnd, ey + py * wEnd); ctx.lineTo(ex - px * wEnd, ey - py * wEnd); ctx.lineTo(b.x - px * 2, b.y - py * 2); ctx.closePath(); ctx.fill();
      ctx.strokeStyle = "rgba(255,255,255,0.35)"; ctx.lineWidth = Math.max(1, W / 1600); ctx.beginPath(); ctx.moveTo(b.x, b.y); ctx.lineTo(b.x + Math.cos(b.a) * len * 0.7, b.y + Math.sin(b.a) * len * 0.7); ctx.stroke();
      var gg = ctx.createRadialGradient(b.x, b.y, 0, b.x, b.y, W * 0.045); gg.addColorStop(0, "rgba(" + rgb + ",0.75)"); gg.addColorStop(1, "rgba(" + rgb + ",0)");
      ctx.fillStyle = gg; ctx.fillRect(b.x - W * 0.05, b.y - W * 0.05, W * 0.1, W * 0.1);
    }
    ctx.fillStyle = "rgba(255,255,255,0.55)";   // dust in the beams
    for (i = 0; i < this.motes.length; i++) {
      var m = this.motes[i]; m.y -= m.s * dt * 6; if (m.y < -0.02) { m.y = 1.02; m.x = Math.random(); }
      var mx = (m.x + Math.sin(this.t * 0.3 + m.p) * 0.01) * W, a = 0.25 + 0.25 * Math.sin(this.t * 1.5 + m.p);
      ctx.globalAlpha = a; ctx.beginPath(); ctx.arc(mx, m.y * H, m.r * (W / 1200), 0, 6.283); ctx.fill();
    }
    ctx.globalAlpha = 1; ctx.globalCompositeOperation = "source-over";
  };

  window.Beams = Beams;
})();
