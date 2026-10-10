/* EchoLight showcase for Squarespace: one self-contained block. Views: hub, event, client selection, curator.
   Routes (hash): (none)=hub, #e=<slug> event, #c=<ids>&n=<name>&m=<note> client page, #curator private picker. */
(function () {
  "use strict";
  var R = document.getElementById("elsc"); if (!R || R.getAttribute("data-ready")) return; R.setAttribute("data-ready", "1");
  var $ = function (s, r) { return (r || R).querySelector(s); }, $$ = function (s, r) { return [].slice.call((r || R).querySelectorAll(s)); };
  var lang = R.getAttribute("data-lang") || "en", mode = R.getAttribute("data-mode") || "hub", hubUrl = R.getAttribute("data-hub-url") || "";
  var reduced = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches, WA = "971567220533";
  var T = {
    en: { types: { corporate: "Corporate & Conferences", gala: "Galas & Awards", wedding: "Weddings", launch: "Launches & Openings", government: "National & Government", private: "Private Celebrations", exhibition: "Exhibitions", show: "Light Shows & Showreels" },
      sv: { lighting: "Stage Lighting", led: "LED Screens", sound: "Sound", mapping: "3D Mapping", laser: "Laser & Light Shows" },
      why: { led: "Big, sharp content readable from the last row.", sound: "Clear coverage for speech and music in every seat.", lighting: "Stage and room lighting designed cue by cue.", laser: "Beams and laser moments people film and remember.", mapping: "Projection fitted to a building, product or stage set." },
      all: "All events", allSvc: "All services", events: "events", event: "event", subAll: "Pick an event type or describe yours above.", subQ: "Closest matches for “{q}” first.", subF: "Filtered to what you picked.",
      recoFor: "For {t}, this is what we'd build", recoGen: "Here's what we'd build for you", recoCta: "Get a quote for this setup", look: "events to look at", ask: "Ask us for references",
      ph: ["a corporate summit", "a wedding in a ballroom", "a car launch", "National Day outdoors", "an awards night with lasers", "a hotel facade mapping"],
      waBase: "Hello EchoLight, I'm planning an event.", waType: " It's {t}.", waSvc: " I'm interested in {s}.", waEv: "Hello EchoLight, I saw \"{t}\" on your showcase and I'd like something like it for my event. Date / venue / guests: ", waTail: " Date / venue / guests: ",
      waClient: "Hello EchoLight, I saw \"{t}\" in the selection you sent me{n}. I'd like to discuss it. Date / venue / guests: ", askLook: "Ask about this look", copied: "Link copied", copyLink: "Copy link to this page", copy: "Copy link", clip: "clip", clips: "clips", selected: "selected", selFor: "Selected for {n}", selForYou: "Selected for you", emptyClient: "This selection is empty or the link is incomplete. Ask EchoLight for a fresh one.", fullShow: "Watch the full show", selAll: "Select all", clientWa: "Talk to EchoLight on WhatsApp", more: "More like this", video: "video", videos: "videos" },
    ar: { types: { corporate: "الشركات والمؤتمرات", gala: "الحفلات والجوائز", wedding: "الأعراس", launch: "الإطلاقات والافتتاحات", government: "الوطنية والحكومية", private: "المناسبات الخاصة", exhibition: "المعارض", show: "عروض الضوء" },
      sv: { lighting: "إضاءة المسارح", led: "شاشات LED", sound: "الصوتيات", mapping: "الإسقاط ثلاثي الأبعاد", laser: "عروض الليزر والضوء" },
      why: { led: "محتوى كبير وواضح مقروء من الصف الأخير.", sound: "تغطية واضحة للكلام والموسيقى في كل مقعد.", lighting: "إضاءة مسرح وقاعة مصممة مشهداً بمشهد.", laser: "أشعة وليزر يصورها الناس ويتذكرونها.", mapping: "إسقاط مضبوط على مبنى أو منتج أو ديكور." },
      all: "كل الفعاليات", allSvc: "كل الخدمات", events: "فعالية", event: "فعالية", subAll: "اختر نوع الفعالية أو اكتب فعاليتك بالأعلى.", subQ: "الأقرب لـ «{q}» أولاً.", subF: "مُصفّاة حسب اختيارك.",
      recoFor: "لـ {t}، هذا ما كنّا سنبنيه", recoGen: "هذا ما كنّا سنبنيه لك", recoCta: "اطلب عرض سعر لهذا التجهيز", look: "فعاليات للاطلاع", ask: "اطلب مراجع",
      ph: ["مؤتمر شركة", "حفل زفاف في قاعة", "إطلاق سيارة", "اليوم الوطني في الهواء الطلق", "حفل جوائز مع ليزر", "إسقاط على واجهة فندق"],
      waBase: "مرحباً إيكو لايت، أخطط لفعالية.", waType: " النوع: {t}.", waSvc: " مهتم بـ {s}.", waEv: "مرحباً إيكو لايت، شاهدت \"{t}\" في معرض أعمالكم وأريد شيئاً مثله لفعاليتي. التاريخ / الموقع / الضيوف: ", waTail: " التاريخ / الموقع / الضيوف: ",
      waClient: "مرحباً إيكو لايت، شاهدت \"{t}\" في الاختيار الذي أرسلتموه{n}. أودّ مناقشته. التاريخ / الموقع / الضيوف: ", askLook: "اسأل عن هذا الشكل", copied: "تم نسخ الرابط", copyLink: "انسخ رابط هذه الصفحة", copy: "انسخ الرابط", clip: "مقطع", clips: "مقاطع", selected: "محدد", selFor: "اختيار خاص بـ {n}", selForYou: "اختيار خاص بك", emptyClient: "هذا الاختيار فارغ أو الرابط غير مكتمل. اطلب رابطاً جديداً من إيكو لايت.", fullShow: "شاهد العرض كاملاً", selAll: "تحديد الكل", clientWa: "تحدّث مع إيكو لايت عبر واتساب", more: "المزيد مثل هذا", video: "فيديو", videos: "فيديوهات" }
  }[lang];
  var KW = {
    corporate: ["corporate", "conference", "summit", "seminar", "meeting", "agm", "company", "business", "forum", "keynote", "congress", "شركة", "مؤتمر", "قمة", "ملتقى", "اجتماع", "ندوة", "منتدى"],
    gala: ["gala", "awards", "award", "dinner", "anniversary", "ceremony", "fashion", "حفل جوائز", "جوائز", "تكريم", "عشاء", "ذكرى", "أزياء"],
    wedding: ["wedding", "bride", "bridal", "groom", "engagement", "henna", "reception", "عرس", "زفاف", "خطوبة", "حنة", "عروس", "فرح", "كوشة"],
    launch: ["launch", "opening", "inauguration", "showroom", "product", "car", "brand", "activation", "reveal", "store", "إطلاق", "افتتاح", "تدشين", "سيارة", "منتج", "علامة"],
    government: ["national day", "government", "ministry", "heritage", "national", "royal", "اليوم الوطني", "وطني", "حكومي", "تراث"],
    private: ["birthday", "party", "new year", "nye", "private", "celebration", "ramadan", "iftar", "eid", "عيد ميلاد", "حفلة", "رأس السنة", "رمضان", "إفطار", "عيد", "احتفال"],
    exhibition: ["exhibition", "expo", "booth", "stand", "trade show", "معرض"],
    show: ["show", "concert", "performance", "showreel", "music", "festival", "عرض", "حفل غنائي", "مهرجان"]
  };
  var SKW = { laser: ["laser", "beam", "sky", "fireworks", "light show", "ليزر", "أشعة"], mapping: ["mapping", "projection", "projector", "facade", "3d", "hologram", "إسقاط", "ماب", "ثلاثي", "واجهة"], led: ["led", "screen", "video wall", "wall", "شاشة", "شاشات", "ليد"], sound: ["sound", "audio", "speaker", "mic", "dj", "صوت", "سماعات", "ساوند"], lighting: ["light", "lighting", "stage", "spot", "truss", "إضاءة", "اضاءة", "مسرح"] };
  var RECO = { corporate: ["led", "sound", "lighting", "laser"], gala: ["lighting", "laser", "led", "sound"], wedding: ["lighting", "laser", "led", "sound"], launch: ["mapping", "led", "laser", "lighting"], government: ["laser", "mapping", "lighting", "led"], private: ["lighting", "laser", "led", "sound"], exhibition: ["led", "lighting", "sound", "mapping"], show: ["laser", "lighting", "mapping", "led"] };
  var PAL = { default: ["#2bc4e0", "#5b7cff", "#b46bff", "#ffffff"], corporate: ["#3da9ff", "#7fd8ff", "#ffffff", "#5b7cff"], gala: ["#ffd27a", "#ff7aa8", "#ffffff", "#7fd8ff"], wedding: ["#ffb86b", "#ff7aa8", "#fff1d6", "#ffd27a"], launch: ["#c04dff", "#ff3df0", "#3dd6ff", "#ffffff"], government: ["#2ee59d", "#ff4d5e", "#ffffff", "#2ee59d"], private: ["#ff9f43", "#ee5a9b", "#ffffff", "#7a8cff"], exhibition: ["#3dd6ff", "#ffffff", "#5b7cff", "#2bc4e0"], show: ["#ff3df0", "#3dd6ff", "#c04dff", "#ffffff"] };
  function el(tag, a, kids) { var n = document.createElement(tag), k; for (k in a || {}) { if (k === "class") n.className = a[k]; else if (k === "text") n.textContent = a[k]; else n.setAttribute(k, a[k]); } (kids || []).forEach(function (c) { if (c) n.appendChild(c); }); return n; }
  function fmt(s, v) { return s.replace(/\{(\w+)\}/g, function (m, k) { return v[k] != null ? v[k] : m; }); }
  function waURL(msg) { return "https://wa.me/" + WA + "?text=" + encodeURIComponent(msg); }
  $$("[data-wa]").forEach(function (a) { a.href = waURL(a.getAttribute("data-wa")); });

  /* ---- autoplay manager (max 4 videos) ---- */
  var playing = [], io;
  function mount(t) { if (t._v || reduced) return; var v = el("video", { muted: "", loop: "", playsinline: "", preload: "metadata", "aria-hidden": "true" }); v.muted = true; v.src = t.getAttribute("data-src"); v.addEventListener("playing", function () { v.classList.add("on"); }); t.insertBefore(v, t.firstChild.nextSibling); t._v = v; if (playing.length >= 4) unmount(playing[0]); playing.push(t); var p = v.play(); if (p && p.catch) p.catch(function () {}); }
  function unmount(t) { if (!t._v) return; t._v.pause(); t._v.removeAttribute("src"); t._v.load(); t._v.remove(); t._v = null; playing = playing.filter(function (x) { return x !== t; }); }
  function watch(tiles) { if (!window.IntersectionObserver || reduced) return; io = io || new IntersectionObserver(function (en) { en.forEach(function (e) { if (e.isIntersecting && e.intersectionRatio >= 0.6) mount(e.target); else unmount(e.target); }); }, { threshold: [0, 0.6] }); tiles.forEach(function (t) { io.observe(t); }); }
  function stopAll() { playing.slice().forEach(unmount); }

  /* ---- lightbox ---- */
  var lb, cur = { list: [], i: 0, from: null };
  function buildLb() {
    lb = el("div", { class: "lb", role: "dialog", "aria-modal": "true", hidden: "" }, [el("button", { class: "lb-x", type: "button", "aria-label": "Close", text: "×" }), el("button", { class: "lb-nav prev", type: "button", "aria-label": "Previous", text: "‹" }), el("button", { class: "lb-nav next", type: "button", "aria-label": "Next", text: "›" }),
      el("figure", { class: "lb-fig" }, [el("div", { class: "lb-media" }), el("figcaption", {}, [el("div", {}, [el("strong", { class: "lb-t" }), el("span", { class: "lb-m" })]), el("a", { class: "btn btn-wa small", target: "_blank", rel: "noopener", text: T.askLook })])])]);
    R.appendChild(lb); $(".lb-x", lb).onclick = closeLb; $(".prev", lb).onclick = function () { step(-1); }; $(".next", lb).onclick = function () { step(1); };
    lb.addEventListener("click", function (e) { if (e.target === lb || e.target.classList.contains("lb-fig")) closeLb(); });
    document.addEventListener("keydown", function (e) { if (lb.hidden) return; if (e.key === "Escape") closeLb(); else if (e.key === "ArrowRight") step(lang === "ar" ? -1 : 1); else if (e.key === "ArrowLeft") step(lang === "ar" ? 1 : -1); });
    var x0 = null; lb.addEventListener("pointerdown", function (e) { x0 = e.clientX; }); lb.addEventListener("pointerup", function (e) { if (x0 == null) return; var d = e.clientX - x0; x0 = null; if (Math.abs(d) > 70) step(d < 0 ? 1 : -1); });
  }
  function showLb() { var it = cur.list[cur.i]; if (!it) return; var m = $(".lb-media", lb); m.textContent = ""; var n; if (it.t === "p") n = el("img", { src: it.src, alt: it.alt }); else { n = el("video", { controls: "", autoplay: "", loop: "", playsinline: "", poster: it.poster }); n.muted = true; n.src = it.src; } m.appendChild(n); $(".lb-t", lb).textContent = it.title; $(".lb-m", lb).textContent = (cur.i + 1) + " / " + cur.list.length; $(".btn-wa", lb).href = waURL(fmt(T.waClient, { t: it.title, n: "" }).replace(" .", ".")); }
  function step(d) { var L = cur.list.length; cur.i = (cur.i + d + L) % L; showLb(); }
  function openLb(list, i, from) { if (!lb) buildLb(); cur = { list: list, i: i, from: from }; lb.hidden = false; document.documentElement.style.overflow = "hidden"; showLb(); $(".lb-x", lb).focus(); }
  function closeLb() { if (!lb || lb.hidden) return; lb.hidden = true; $(".lb-media", lb).textContent = ""; document.documentElement.style.overflow = ""; if (cur.from) try { cur.from.focus(); } catch (e) {} }
  function tileData(t, title) { return { t: t.getAttribute("data-t") === "p" ? "p" : "v", src: t.getAttribute("data-src"), poster: t.getAttribute("data-poster"), alt: t.querySelector("img").alt, title: title }; }

  /* ---- views ---- */
  var views = { hub: $(".el-hub"), ev: $(".el-evs"), client: $(".el-client"), cur: $(".el-cur") }, hubY = 0, evOpen = null;
  function setView(v) { Object.keys(views).forEach(function (k) { if (views[k]) views[k].hidden = k !== v; }); if (v !== "hub") stopAll(); }
  function top() { var y = R.getBoundingClientRect().top + window.pageYOffset; window.scrollTo(0, Math.max(0, y - 90)); }
  function evTiles(art) { return $$(".tile", art); }
  function openEvent(slug) {
    var art = $("#el-ev-" + slug); if (!art) return false; if (!views.hub.hidden) hubY = window.pageYOffset;
    $$(".elev").forEach(function (a) { a.hidden = a !== art; }); setView("ev"); evOpen = art; top();
    var title = art.getAttribute("data-title"), tiles = evTiles(art), list = tiles.map(function (t) { return tileData(t, title); });
    if (!art._wired) { art._wired = 1; tiles.forEach(function (t, i) { t.addEventListener("click", function (e) { e.preventDefault(); openLb(list, i, t); }); }); var f = $("[data-full]", art); if (f) f.addEventListener("click", function (e) { e.preventDefault(); openLb([{ t: "v", src: f.href, poster: f.getAttribute("data-poster"), alt: title, title: title }], 0, f); }); var cp = $("[data-copy]", art); if (cp) cp.addEventListener("click", function () { var u = location.origin + location.pathname + "#e=" + slug; (navigator.clipboard ? navigator.clipboard.writeText(u) : Promise.reject()).then(function () { cp.textContent = T.copied; }, function () { cp.textContent = u; }); }); }
    watch(tiles.filter(function (t) { return t.classList.contains("is-v"); })); return true;
  }
  function route() {
    closeLb(); var h = location.hash.replace(/^#/, ""), p = new URLSearchParams(h);
    if (mode === "event") { var a = $(".elev"); a.hidden = false; setView("ev"); evOpen = a; wireStatic(a); return; }
    if (p.get("c")) return clientView(p);
    if (h === "curator" || p.has("curator")) { setView("cur"); buildCurator(); top(); return; }
    if (p.get("e") && openEvent(p.get("e"))) return;
    setView("hub"); if (!hubReady) initHub(); applyHash(p); window.scrollTo(0, hubY || window.pageYOffset);
  }
  function wireStatic(art) { var title = art.getAttribute("data-title"), tiles = evTiles(art), list = tiles.map(function (t) { return tileData(t, title); }); tiles.forEach(function (t, i) { t.addEventListener("click", function (e) { e.preventDefault(); openLb(list, i, t); }); }); var f = $("[data-full]", art); if (f) f.addEventListener("click", function (e) { e.preventDefault(); openLb([{ t: "v", src: f.href, poster: f.getAttribute("data-poster"), alt: title, title: title }], 0, f); }); var cp = $("[data-copy]", art); if (cp) cp.addEventListener("click", function () { var u = location.href.split("#")[0]; (navigator.clipboard ? navigator.clipboard.writeText(u) : Promise.reject()).then(function () { cp.textContent = T.copied; }, function () { cp.textContent = u; }); }); watch(tiles.filter(function (t) { return t.classList.contains("is-v"); })); }

  /* ---- client view ---- */
  function allTiles() { var m = {}; $$(".elev").forEach(function (a) { var title = a.getAttribute("data-title"); $$(".tile", a).forEach(function (t) { m[t.getAttribute("data-k")] = { t: t, title: title }; }); }); return m; }
  function clientView(p) {
    setView("client"); var ids = (p.get("c") || "").split("~").filter(Boolean), n = p.get("n"), note = p.get("m"), map = allTiles();
    $(".cl-h", views.client).textContent = n ? fmt(T.selFor, { n: n }) : T.selForYou; $(".cl-n", views.client).textContent = note || ""; var g = $(".cl-g", views.client); g.textContent = "";
    var items = ids.map(function (k) { return map[k]; }).filter(Boolean); if (!items.length) { g.appendChild(el("p", { class: "empty", text: T.emptyClient })); top(); return; }
    var list = items.map(function (o) { return tileData(o.t, o.title); }), tiles = [];
    items.forEach(function (o, i) { var c = o.t.cloneNode(true); c.removeAttribute("id"); var vid = c.querySelector("video"); if (vid) vid.remove(); c._v = null; c.addEventListener("click", function (e) { e.preventDefault(); openLb(list, i, c); }); g.appendChild(c); tiles.push(c); });
    watch(tiles.filter(function (t) { return t.classList.contains("is-v"); }));
    $(".cl-wa", views.client).href = waURL(T.waBase + (n ? " (" + n + ")" : "") + T.waTail); top();
  }

  /* ---- curator (private) ---- */
  var picked = [], curBuilt = false;
  function buildCurator() {
    if (!curBuilt) { curBuilt = true; ["#cu-client", "#cu-note"].forEach(function (s) { $(s).addEventListener("input", curLink); }); $("#cu-copy").addEventListener("click", function () { var o = $("#cu-out"); o.select(); (navigator.clipboard ? navigator.clipboard.writeText(o.value) : Promise.reject()).then(function () { $("#cu-copy").textContent = T.copied; setTimeout(function () { $("#cu-copy").textContent = T.copy; }, 1500); }, function () { try { document.execCommand("copy"); } catch (e) {} }); }); $("#cu-clear").addEventListener("click", function () { picked = []; curRender(); }); }
    curRender();
  }
  function curRender() {
    var list = $("#cu-list"); list.textContent = "";
    $$(".elev").forEach(function (a) {
      var tiles = evTiles(a), d = el("details", { class: "cev" }, [el("summary", {}, [el("span", { class: "ct", text: a.getAttribute("data-title") }), el("span", { class: "cm", text: tiles.length + " " + (tiles.length === 1 ? T.clip : T.clips) })])]), g = el("div", { class: "cg" });
      tiles.forEach(function (t) { var k = t.getAttribute("data-k"), on = picked.indexOf(k) > -1, b = el("button", { type: "button", class: "ct-clip" + (on ? " on" : ""), "aria-pressed": on ? "true" : "false", "aria-label": a.getAttribute("data-title") }, [el("img", { src: t.getAttribute("data-poster"), alt: "", loading: "lazy" }), t.classList.contains("is-v") ? el("span", { class: "vb", text: "▶" }) : null, el("span", { class: "ck", text: on ? "✓" : "" })]); b.onclick = function () { var i = picked.indexOf(k); if (i > -1) picked.splice(i, 1); else picked.push(k); curRender(); }; g.appendChild(b); });
      var all = el("button", { type: "button", class: "btn small", text: T.selAll }); all.onclick = function () { tiles.forEach(function (t) { var k = t.getAttribute("data-k"); if (picked.indexOf(k) < 0) picked.push(k); }); curRender(); };
      d.appendChild(g); d.appendChild(all); list.appendChild(d); if (tiles.some(function (t) { return picked.indexOf(t.getAttribute("data-k")) > -1; })) d.open = true;
    });
    $("#cu-cnt").textContent = picked.length + " " + (picked.length === 1 ? T.clip : T.clips) + " " + T.selected;
    var s = $("#cu-sel"); s.textContent = ""; var map = allTiles(); picked.forEach(function (k, i) { var o = map[k]; if (!o) return; var x = el("button", { type: "button", class: "sel-i" }, [el("img", { src: o.t.getAttribute("data-poster"), alt: "" }), el("span", { text: "×" })]); x.onclick = function () { picked.splice(i, 1); curRender(); }; s.appendChild(x); }); curLink();
  }
  function curLink() { var n = $("#cu-client").value.trim(), note = $("#cu-note").value.trim(), out = $("#cu-out"); if (!picked.length) { out.value = ""; $("#cu-open").removeAttribute("href"); return; } var u = location.origin + location.pathname + "#c=" + picked.join("~") + (n ? "&n=" + encodeURIComponent(n) : "") + (note ? "&m=" + encodeURIComponent(note) : ""); out.value = u; $("#cu-open").href = u; }

  /* ---- hub ---- */
  var hubReady = false, hero, state = { ty: null, sv: [], q: "" }, cards = {}, grid, H = [];
  function initHub() {
    hubReady = true; grid = $(".el-cards");
    $$(".ecard").forEach(function (c) { var o = { slug: c.getAttribute("data-slug"), types: c.getAttribute("data-types").split(" "), svc: c.getAttribute("data-svc").split(" "), hero: c.hasAttribute("data-hero"), old: c.hasAttribute("data-old"), clips: +c.getAttribute("data-clips"), rank: +c.getAttribute("data-rank") }; cards[o.slug] = c; H.push(o); });
    $("#el-finder").addEventListener("submit", function (e) { e.preventDefault(); var q = $("#el-q").value.trim(); if (!q) return; var p = parse(q); state = { ty: p.ty, sv: p.sv, q: q }; apply(); jump(); });
    $$("[data-pick]").forEach(function (b) { b.addEventListener("click", function () { state = { ty: b.getAttribute("data-pick"), sv: [], q: "" }; $("#el-q").value = ""; apply(); jump(); }); });
    $$("[data-svc]").forEach(function (b) { b.addEventListener("click", function (e) { e.preventDefault(); state = { ty: null, sv: [b.getAttribute("data-svc")], q: "" }; apply(); jump(); }); });
    $$(".ecard > a").forEach(function (a) { a.addEventListener("click", function () { hubY = window.pageYOffset; }); });
    if (window.Beams) hero = new Beams($("#el-hero-canvas"), { count: window.innerWidth < 700 ? 6 : 9, colors: PAL.default.concat(PAL.default), host: $(".el-hero") });
    placeholder(); if (window.FX) { FX.lang = lang; FX.wa = waURL; if (FX.init) FX.init(R); }
  }
  function placeholder() { var ph = T.ph, i = 0, j = 0, del = false, q = $("#el-q"); (function tick() { if (reduced) { q.placeholder = ph[0]; return; } var s = ph[i]; q.placeholder = s.slice(0, j); if (!del && j < s.length) { j++; setTimeout(tick, 55); } else if (!del) { del = true; setTimeout(tick, 1300); } else if (j > 0) { j--; setTimeout(tick, 22); } else { del = false; i = (i + 1) % ph.length; setTimeout(tick, 250); } })(); }
  function parse(q) { var s = q.toLowerCase(), ty = null, best = 0, sv = []; Object.keys(KW).forEach(function (k) { var n = 0; KW[k].forEach(function (w) { if (s.indexOf(w) > -1) n += w.length > 3 ? 2 : 1; }); if (n > best) { best = n; ty = k; } }); Object.keys(SKW).forEach(function (k) { if (SKW[k].some(function (w) { return s.indexOf(w) > -1; })) sv.push(k); }); return { ty: ty, sv: sv }; }
  function score(e) { var s = 0; if (state.ty) { var i = e.types.indexOf(state.ty); s += i === 0 ? 6 : i > 0 ? 4 : -2; } if (state.sv.length) { var hit = state.sv.filter(function (x) { return e.svc.indexOf(x) > -1; }).length; s += hit ? 3 * hit : -3; } if (state.ty) (RECO[state.ty] || []).forEach(function (x, r) { if (e.svc.indexOf(x) > -1) s += (4 - r) * 0.3; }); if (e.hero) s += 1.5; if (e.old) s -= 3; s += Math.min(e.clips, 12) * 0.05 + e.rank * 0.001; return s; }
  function render() {
    var strict = state.ty || state.sv.length, shown = 0;
    function match(e) { return (!state.ty || e.types.indexOf(state.ty) > -1) && (!state.sv.length || state.sv.some(function (s) { return e.svc.indexOf(s) > -1; })); }
    H.map(function (e) { return { e: e, s: score(e) }; }).sort(function (a, b) { return b.s - a.s; }).forEach(function (x) { var c = cards[x.e.slug], ok = !strict || match(x.e); c.hidden = !ok; if (ok) { shown++; grid.appendChild(c); } });
    $("#el-count").textContent = shown + " " + (shown === 1 ? T.event : T.events); $("#el-empty").hidden = shown > 0;
    $("#el-gsub").textContent = state.q ? fmt(T.subQ, { q: state.q }) : (strict ? T.subF : T.subAll); pills(); reco();
  }
  function pills() {
    var ft = $("#el-ftypes"), fs = $("#el-fsvc"); ft.textContent = ""; fs.textContent = "";
    function pill(label, on, fn, col) { var b = el("button", { class: "pill" + (on ? " on" : ""), type: "button", "aria-pressed": on ? "true" : "false" }, [col ? el("i", { style: "background:" + col }) : null, el("span", { text: label })]); b.onclick = fn; return b; }
    ft.appendChild(pill(T.all, !state.ty, function () { state.ty = null; state.q = ""; apply(); }));
    Object.keys(T.types).forEach(function (k) { ft.appendChild(pill(T.types[k], state.ty === k, function () { state.ty = state.ty === k ? null : k; state.q = ""; apply(); }, PAL[k][0])); });
    fs.appendChild(pill(T.allSvc, !state.sv.length, function () { state.sv = []; apply(); }));
    Object.keys(T.sv).forEach(function (k) { fs.appendChild(pill(T.sv[k], state.sv.indexOf(k) > -1, function () { var i = state.sv.indexOf(k); if (i > -1) state.sv.splice(i, 1); else state.sv.push(k); apply(); })); });
  }
  function reco() {
    var box = $("#el-reco"); if (!state.ty && !state.sv.length) { box.hidden = true; box.textContent = ""; return; }
    var base = state.ty ? RECO[state.ty].slice() : ["lighting", "led", "laser", "mapping"], l = state.sv.slice(); base.forEach(function (s) { if (l.indexOf(s) < 0) l.push(s); }); l = l.slice(0, 4);
    box.hidden = false; box.textContent = ""; box.appendChild(el("h3", { text: state.ty ? fmt(T.recoFor, { t: T.types[state.ty] }) : T.recoGen })); var row = el("div", { class: "reco-row" });
    l.forEach(function (s) { var n = H.filter(function (e) { return e.svc.indexOf(s) > -1 && (!state.ty || e.types.indexOf(state.ty) > -1); }).length, b = el("button", { class: "rcard", type: "button" }, [el("strong", { text: T.sv[s] }), el("p", { text: T.why[s] }), el("em", { text: n ? n + " " + T.look : T.ask })]); b.onclick = function () { state.sv = [s]; apply(); jump(); }; row.appendChild(b); });
    box.appendChild(row); box.appendChild(el("a", { class: "btn btn-wa small", href: waURL(T.waBase + (state.ty ? fmt(T.waType, { t: T.types[state.ty] }) : "") + (state.sv.length ? fmt(T.waSvc, { s: state.sv.map(function (s) { return T.sv[s]; }).join(", ") }) : "") + T.waTail), target: "_blank", rel: "noopener", text: T.recoCta }));
  }
  function apply() { var p = PAL[state.ty || "default"]; if (hero) hero.setColors(p.concat(p)); R.style.setProperty("--accent", p[0]); R.style.setProperty("--accent2", p[1]); render(); }
  function jump() { $("#el-work").scrollIntoView({ behavior: reduced ? "auto" : "smooth", block: "start" }); }
  function applyHash(p) { var t = p.get("t"), s = p.get("s"); if (t && T.types[t]) state = { ty: t, sv: [], q: "" }; else if (s) state = { ty: null, sv: s.split(",").filter(function (x) { return T.sv[x]; }), q: "" }; apply(); }

  window.addEventListener("hashchange", route);
  var back = $$("[data-back]"); back.forEach(function (a) { if (mode === "hub") a.addEventListener("click", function (e) { e.preventDefault(); if (location.hash) history.pushState(null, "", location.pathname + location.search); route(); }); });
  if (mode === "hub") { var q0 = new URLSearchParams(location.search).get("q"); initHub(); route(); if (q0) { $("#el-q").value = q0; var p0 = parse(q0); state = { ty: p0.ty, sv: p0.sv, q: q0 }; apply(); } }
  else { initHubLite(); route(); }
  function initHubLite() { if (window.FX && FX.init) FX.init(R); }
  if (window.parent !== window) { var send = function () { try { parent.postMessage({ echolightHeight: document.documentElement.scrollHeight }, "*"); } catch (e) {} }; setInterval(send, 1500); }
})();
