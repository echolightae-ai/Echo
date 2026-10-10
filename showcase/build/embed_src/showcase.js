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
      waClient: "Hello EchoLight, I saw \"{t}\" in the selection you sent me{n}. I'd like to discuss it. Date / venue / guests: ", askLook: "Ask about this look", copied: "Link copied", sel_: "selected", copyLink: "Copy link to this page", copy: "Copy link", clip: "clip", clips: "clips", selected: "selected", selFor: "Selected for {n}", selForYou: "Selected for you", emptyClient: "This selection is empty or the link is incomplete. Ask EchoLight for a fresh one.", fullShow: "Watch the full show", selAll: "Select all", clientWa: "Talk to EchoLight on WhatsApp", more: "More like this", video: "video", videos: "videos", cm: { sel: "selected", hint: "Tap ＋ on any clip to add it to a private client page", name: "Client name (optional)", note: "Short note for the client (optional)", copy: "Copy client link", preview: "Preview", clear: "Clear", exit: "Exit", film: "Full film", addfilm: "Add the full film" } },
    ar: { types: { corporate: "الشركات والمؤتمرات", gala: "الحفلات والجوائز", wedding: "الأعراس", launch: "الإطلاقات والافتتاحات", government: "الوطنية والحكومية", private: "المناسبات الخاصة", exhibition: "المعارض", show: "عروض الضوء" },
      sv: { lighting: "إضاءة المسارح", led: "شاشات LED", sound: "الصوتيات", mapping: "الإسقاط ثلاثي الأبعاد", laser: "عروض الليزر والضوء" },
      why: { led: "محتوى كبير وواضح مقروء من الصف الأخير.", sound: "تغطية واضحة للكلام والموسيقى في كل مقعد.", lighting: "إضاءة مسرح وقاعة مصممة مشهداً بمشهد.", laser: "أشعة وليزر يصورها الناس ويتذكرونها.", mapping: "إسقاط مضبوط على مبنى أو منتج أو ديكور." },
      all: "كل الفعاليات", allSvc: "كل الخدمات", events: "فعالية", event: "فعالية", subAll: "اختر نوع الفعالية أو اكتب فعاليتك بالأعلى.", subQ: "الأقرب لـ «{q}» أولاً.", subF: "مُصفّاة حسب اختيارك.",
      recoFor: "لـ {t}، هذا ما كنّا سنبنيه", recoGen: "هذا ما كنّا سنبنيه لك", recoCta: "اطلب عرض سعر لهذا التجهيز", look: "فعاليات للاطلاع", ask: "اطلب مراجع",
      ph: ["مؤتمر شركة", "حفل زفاف في قاعة", "إطلاق سيارة", "اليوم الوطني في الهواء الطلق", "حفل جوائز مع ليزر", "إسقاط على واجهة فندق"],
      waBase: "مرحباً إيكو لايت، أخطط لفعالية.", waType: " النوع: {t}.", waSvc: " مهتم بـ {s}.", waEv: "مرحباً إيكو لايت، شاهدت \"{t}\" في معرض أعمالكم وأريد شيئاً مثله لفعاليتي. التاريخ / الموقع / الضيوف: ", waTail: " التاريخ / الموقع / الضيوف: ",
      waClient: "مرحباً إيكو لايت، شاهدت \"{t}\" في الاختيار الذي أرسلتموه{n}. أودّ مناقشته. التاريخ / الموقع / الضيوف: ", askLook: "اسأل عن هذا الشكل", copied: "تم نسخ الرابط", sel_: "محدد", copyLink: "انسخ رابط هذه الصفحة", copy: "انسخ الرابط", clip: "مقطع", clips: "مقاطع", selected: "محدد", selFor: "اختيار خاص بـ {n}", selForYou: "اختيار خاص بك", emptyClient: "هذا الاختيار فارغ أو الرابط غير مكتمل. اطلب رابطاً جديداً من إيكو لايت.", fullShow: "شاهد العرض كاملاً", selAll: "تحديد الكل", clientWa: "تحدّث مع إيكو لايت عبر واتساب", more: "المزيد مثل هذا", video: "فيديو", videos: "فيديوهات", cm: { sel: "محدد", hint: "اضغط ＋ على أي مقطع لإضافته إلى صفحة خاصة بالعميل", name: "اسم العميل (اختياري)", note: "ملاحظة قصيرة للعميل (اختياري)", copy: "انسخ رابط العميل", preview: "معاينة", clear: "مسح", exit: "خروج", film: "الفيلم الكامل", addfilm: "أضف الفيلم الكامل" } }
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
  function watch(tiles) { if (!window.IntersectionObserver || reduced) return; io = io || new IntersectionObserver(function (en) { en.forEach(function (e) { if (e.isIntersecting && e.intersectionRatio >= 0.4) mount(e.target); else unmount(e.target); }); }, { threshold: [0, 0.4] }); tiles.forEach(function (t) { io.observe(t); }); }
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
    filmWire(art); watch(tiles.filter(function (t) { return t.classList.contains("is-v"); })); return true;
  }
  function route() { route0(); decorateAll(); trayUpdate(); }
  function route0() {
    closeLb(); var h = location.hash.replace(/^#/, ""), p = new URLSearchParams(h);
    if (h === "curator") { curSet(true); try { history.replaceState(null, "", location.pathname + location.search); } catch (e) {} h = ""; p = new URLSearchParams(""); }
    if (mode === "event") { var a = $(".elev"); a.hidden = false; setView("ev"); evOpen = a; wireStatic(a); return; }
    if (p.get("c")) return clientView(p);
    if (h === "picker") { setView("cur"); buildCurator(); top(); return; }
    if (p.get("e") && openEvent(p.get("e"))) return;
    setView("hub"); if (!hubReady) initHub(); applyHash(p); window.scrollTo(0, hubY || window.pageYOffset);
  }
  function wireStatic(art) { filmWire(art); var title = art.getAttribute("data-title"), tiles = evTiles(art), list = tiles.map(function (t) { return tileData(t, title); }); tiles.forEach(function (t, i) { t.addEventListener("click", function (e) { e.preventDefault(); openLb(list, i, t); }); }); var f = $("[data-full]", art); if (f) f.addEventListener("click", function (e) { e.preventDefault(); openLb([{ t: "v", src: f.href, poster: f.getAttribute("data-poster"), alt: title, title: title }], 0, f); }); var cp = $("[data-copy]", art); if (cp) cp.addEventListener("click", function () { var u = location.href.split("#")[0]; (navigator.clipboard ? navigator.clipboard.writeText(u) : Promise.reject()).then(function () { cp.textContent = T.copied; }, function () { cp.textContent = u; }); }); watch(tiles.filter(function (t) { return t.classList.contains("is-v"); })); }

  /* ---- client view ---- */
  function allTiles() { var m = {}; $$(".elev").forEach(function (a) { var title = a.getAttribute("data-title"); $$(".tile", a).forEach(function (t) { m[t.getAttribute("data-k")] = { t: t, title: title }; }); var f = $("[data-film]", a); if (f) { var img = $("img", f), t = el("a", { class: "tile is-v", href: f.getAttribute("data-src"), "data-k": "film:" + a.id.replace("el-ev-", ""), "data-t": "v", "data-src": f.getAttribute("data-src"), "data-poster": img.src, style: "aspect-ratio:1.6" }, [el("img", { src: img.src, alt: title + " (" + T.cm.film + ")" }), el("span", { class: "vbadge", text: "▶ " + T.cm.film }), el("span", { class: "cap", text: title })]); m["film:" + a.id.replace("el-ev-", "")] = { t: t, title: title + " (" + T.cm.film + ")" }; } }); return m; }
  function clientView(p) {
    setView("client"); var ids = (p.get("c") || "").split("~").filter(Boolean), n = p.get("n"), note = p.get("m"), map = allTiles();
    $(".cl-h", views.client).textContent = n ? fmt(T.selFor, { n: n }) : T.selForYou; $(".cl-n", views.client).textContent = note || ""; var g = $(".cl-g", views.client); g.textContent = "";
    var items = ids.map(function (k) { return map[k]; }).filter(Boolean); if (!items.length) { g.appendChild(el("p", { class: "empty", text: T.emptyClient })); top(); return; }
    var list = items.map(function (o) { return tileData(o.t, o.title); }), tiles = [];
    items.forEach(function (o, i) { var c = o.t.cloneNode(true); c.removeAttribute("id"); var vid = c.querySelector("video"); if (vid) vid.remove(); c._v = null; c.addEventListener("click", function (e) { e.preventDefault(); openLb(list, i, c); }); g.appendChild(c); tiles.push(c); });
    watch(tiles.filter(function (t) { return t.classList.contains("is-v"); }));
    $(".cl-wa", views.client).href = waURL(T.waBase + (n ? " (" + n + ")" : "") + T.waTail); top();
  }

  /* ---- curator mode: pick clips while browsing the real page ---- */
  var cur = { on: false, picked: [], name: "", note: "" }, tray;
  try { var sv = JSON.parse(localStorage.getItem("elsc_cur") || "null"); if (sv && typeof sv === "object") cur = { on: !!sv.on, picked: sv.picked || [], name: sv.name || "", note: sv.note || "" }; } catch (e) {}
  function curSave() { try { localStorage.setItem("elsc_cur", JSON.stringify(cur)); } catch (e) {} }
  function curSet(on) { cur.on = on; curSave(); decorateAll(); trayUpdate(); }
  function keyOf(t) { return t.getAttribute("data-k"); }
  function decorate(t) { var old = $(".pick", t); if (!cur.on) { if (old) old.remove(); t.classList.remove("picked"); return; } if (old) { return; } var b = el("button", { class: "pick", type: "button", "aria-label": "Select", text: "＋" }); b.addEventListener("click", function (e) { e.preventDefault(); e.stopPropagation(); togglePick(keyOf(t)); }); t.appendChild(b); }
  function decorateAll() { $$(".tile[data-k]").forEach(decorate); $$(".film").forEach(function (f) { var a = f.closest(".elev"), old = $(".pick", f); if (!cur.on || !a) { if (old) old.remove(); return; } if (old) return; var k = "film:" + a.id.replace("el-ev-", ""), b = el("button", { class: "pick", type: "button", "aria-label": "Select film", text: "＋ " + T.cm.addfilm }); b.setAttribute("data-fk", k); b.addEventListener("click", function (e) { e.preventDefault(); e.stopPropagation(); togglePick(k); }); f.appendChild(b); }); marks(); }
  function togglePick(k) { var i = cur.picked.indexOf(k); if (i > -1) cur.picked.splice(i, 1); else cur.picked.push(k); curSave(); marks(); trayUpdate(); }
  function marks() { $$(".tile[data-k]").forEach(function (t) { var on = cur.picked.indexOf(keyOf(t)) > -1; t.classList.toggle("picked", on); var b = $(".pick", t); if (b) b.textContent = on ? "✓" : "＋"; }); $$(".pick[data-fk]").forEach(function (b) { var on = cur.picked.indexOf(b.getAttribute("data-fk")) > -1; b.classList.toggle("on", on); b.textContent = (on ? "✓ " : "＋ ") + T.cm.addfilm; }); }
  function curLinkURL() { var u = location.origin + location.pathname + "#c=" + cur.picked.join("~"); if (cur.name) u += "&n=" + encodeURIComponent(cur.name); if (cur.note) u += "&m=" + encodeURIComponent(cur.note); return u; }
  function trayUpdate() {
    if (!cur.on) { if (tray) tray.hidden = true; R.classList.remove("cm"); return; } R.classList.add("cm");
    if (!tray) {
      var n = el("input", { type: "text", "aria-label": T.cm.name, placeholder: T.cm.name, maxlength: "60" }), m = el("input", { type: "text", "aria-label": T.cm.note, placeholder: T.cm.note, maxlength: "160" }), cnt = el("strong", { class: "cm-n" }), hint = el("span", { class: "cm-h", text: T.cm.hint }), cp = el("button", { class: "btn btn-go small", type: "button", text: T.cm.copy }), pv = el("a", { class: "btn btn-ghost small", target: "_blank", rel: "noopener", text: T.cm.preview }), cl = el("button", { class: "btn btn-ghost small", type: "button", text: T.cm.clear }), ex = el("button", { class: "btn btn-ghost small", type: "button", text: T.cm.exit });
      n.value = cur.name; m.value = cur.note; n.addEventListener("input", function () { cur.name = n.value; curSave(); trayUpdate(); }); m.addEventListener("input", function () { cur.note = m.value; curSave(); trayUpdate(); });
      cp.addEventListener("click", function () { var u = curLinkURL(); (navigator.clipboard ? navigator.clipboard.writeText(u) : Promise.reject()).then(function () { cp.textContent = T.copied; setTimeout(function () { cp.textContent = T.cm.copy; }, 1600); }, function () { window.prompt && 0; cp.textContent = u; }); });
      cl.addEventListener("click", function () { cur.picked = []; curSave(); marks(); trayUpdate(); }); ex.addEventListener("click", function () { curSet(false); });
      tray = el("div", { class: "cmtray", role: "region", "aria-label": "Client selection" }, [cnt, hint, n, m, cp, pv, cl, ex]); tray._p = { cnt: cnt, hint: hint, cp: cp, pv: pv, cl: cl }; R.appendChild(tray);
    }
    tray.hidden = false; var p = tray._p, k = cur.picked.length; p.cnt.textContent = k + " " + (k === 1 ? T.clip : T.clips) + " " + T.sel_; p.hint.hidden = k > 0; p.cp.disabled = !k; p.pv.hidden = !k; p.cl.hidden = !k; if (k) p.pv.href = curLinkURL();
  }
  /* ---- the older list picker (#picker) ---- */
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
    $$(".ecard").forEach(function (c) { var o = { slug: c.getAttribute("data-slug"), types: c.getAttribute("data-ty").split(" "), svc: c.getAttribute("data-sv").split(" "), hero: c.hasAttribute("data-hero"), old: c.hasAttribute("data-old"), clips: +c.getAttribute("data-clips"), rank: +c.getAttribute("data-rank"), q: c.getAttribute("data-q") || "" }; cards[o.slug] = c; H.push(o); });
    $("#el-finder").addEventListener("submit", function (e) { e.preventDefault(); var q = $("#el-q").value.trim(); if (!q) return; var p = parse(q), tx = textHits(q); state = { ty: p.ty, sv: p.sv, q: q, tx: tx }; apply(); jump(); });
    $$("[data-pick]").forEach(function (b) { b.addEventListener("click", function () { state = { ty: b.getAttribute("data-pick"), sv: [], q: "" }; $("#el-q").value = ""; apply(); jump(); }); });
    $$("[data-svc]").forEach(function (b) { b.addEventListener("click", function (e) { e.preventDefault(); state = { ty: null, sv: [b.getAttribute("data-svc")], q: "" }; apply(); jump(); }); });
    $$(".ecard > a").forEach(function (a) { a.addEventListener("click", function () { hubY = window.pageYOffset; }); });
    cardVideos(); reelPlay();
    if (window.Beams) hero = new Beams($("#el-hero-canvas"), { count: window.innerWidth < 700 ? 6 : 9, colors: PAL.default.concat(PAL.default), host: $(".el-hero") });
    placeholder(); if (window.FX) { FX.lang = lang; FX.wa = waURL; if (FX.init) FX.init(R); }
  }
  function cardMount(c) { if (c._v || reduced || c.hidden || !c.getAttribute("data-v")) return; var v = el("video", { muted: "", loop: "", playsinline: "", preload: "metadata", "aria-hidden": "true" }); v.muted = true; v.src = c.getAttribute("data-v"); v.addEventListener("playing", function () { v.classList.add("on"); }); var cov = $(".cov", c); cov.insertBefore(v, $("img", cov).nextSibling); c._v = v; if (playing.length >= 5) { var o = playing[0]; if (o._v && o.classList.contains("ecard")) cardUnmount(o); else unmount(o); } playing.push(c); var p = v.play(); if (p && p.catch) p.catch(function () {}); }
  function cardUnmount(c) { if (!c._v) return; c._v.pause(); c._v.removeAttribute("src"); c._v.load(); c._v.remove(); c._v = null; playing = playing.filter(function (x) { return x !== c; }); }
  function cardVideos() { if (reduced) return; var cs = $$(".ecard[data-v]"); if (window.IntersectionObserver) { var o = new IntersectionObserver(function (en) { en.forEach(function (e) { if (e.isIntersecting && e.intersectionRatio >= 0.4) cardMount(e.target); else cardUnmount(e.target); }); }, { threshold: [0, 0.4] }); cs.forEach(function (c) { o.observe(c); }); } cs.forEach(function (c) { c.addEventListener("pointerenter", function (ev) { if (ev.pointerType !== "touch") cardMount(c); }); }); }
  function reelPlay() { if (reduced || !window.IntersectionObserver) return; var o = new IntersectionObserver(function (en) { en.forEach(function (e) { var v = e.target; if (e.isIntersecting) { if (!v.getAttribute("src")) v.src = v.getAttribute("data-src"); v.addEventListener("playing", function () { v.classList.add("on"); }, { once: true }); var p = v.play(); if (p && p.catch) p.catch(function () {}); } else v.pause(); }); }, { rootMargin: "120px" }); $$(".rv video").forEach(function (v) { o.observe(v); }); }
  function filmWire(art) { var b = $("[data-film]", art); if (!b || b._w) return; b._w = 1; b.addEventListener("click", function () { var v = el("video", { controls: "", autoplay: "", playsinline: "", poster: $("img", b).src }); v.src = b.getAttribute("data-src"); b.parentNode.replaceChild(v, b); var p = v.play(); if (p && p.catch) p.catch(function () {}); }); }
  function placeholder() { var ph = T.ph, i = 0, j = 0, del = false, q = $("#el-q"); (function tick() { if (reduced) { q.placeholder = ph[0]; return; } var s = ph[i]; q.placeholder = s.slice(0, j); if (!del && j < s.length) { j++; setTimeout(tick, 55); } else if (!del) { del = true; setTimeout(tick, 1300); } else if (j > 0) { j--; setTimeout(tick, 22); } else { del = false; i = (i + 1) % ph.length; setTimeout(tick, 250); } })(); }
  function textHits(q) { var toks = q.toLowerCase().split(/[^\p{L}\p{N}]+/u).filter(function (t) { return t.length >= 3; }); if (!toks.length) return null; var r = H.filter(function (e) { return toks.every(function (t) { return e.q.indexOf(t) > -1; }); }).map(function (e) { return e.slug; }); return r.length ? r : null; }
  function parse(q) { var s = q.toLowerCase(), ty = null, best = 0, sv = []; Object.keys(KW).forEach(function (k) { var n = 0; KW[k].forEach(function (w) { if (s.indexOf(w) > -1) n += w.length > 3 ? 2 : 1; }); if (n > best) { best = n; ty = k; } }); Object.keys(SKW).forEach(function (k) { if (SKW[k].some(function (w) { return s.indexOf(w) > -1; })) sv.push(k); }); return { ty: ty, sv: sv }; }
  function score(e) { var s = 0; if (state.tx && state.tx.indexOf(e.slug) > -1) s += 8; if (state.ty) { var i = e.types.indexOf(state.ty); s += i === 0 ? 6 : i > 0 ? 4 : -2; } if (state.sv.length) { var hit = state.sv.filter(function (x) { return e.svc.indexOf(x) > -1; }).length; s += hit ? 3 * hit : -3; } if (state.ty) (RECO[state.ty] || []).forEach(function (x, r) { if (e.svc.indexOf(x) > -1) s += (4 - r) * 0.3; }); if (e.hero) s += 1.5; if (e.old) s -= 3; s += Math.min(e.clips, 12) * 0.05 + e.rank * 0.001; return s; }
  function render() {
    var strict = state.ty || state.sv.length || state.tx, shown = 0;
    function match(e) { if (state.tx && !state.ty && !state.sv.length) return state.tx.indexOf(e.slug) > -1; return (!state.ty || e.types.indexOf(state.ty) > -1) && (!state.sv.length || state.sv.some(function (s) { return e.svc.indexOf(s) > -1; })); }
    H.map(function (e) { return { e: e, s: score(e) }; }).sort(function (a, b) { return b.s - a.s; }).forEach(function (x) { var c = cards[x.e.slug], ok = !strict || match(x.e); c.hidden = !ok; if (ok) { shown++; grid.appendChild(c); } });
    $("#el-count").textContent = shown + " " + (shown === 1 ? T.event : T.events); $("#el-empty").hidden = shown > 0;
    $("#el-gsub").textContent = state.q ? fmt(T.subQ, { q: state.q }) : (strict ? T.subF : T.subAll); pills(); reco(); clipView();
  }
  var clipLimit = 36;
  function clipView() {
    var box = $("#el-clips"); if (!state.sv.length) { box.hidden = true; $("#el-clips-g").textContent = ""; return; }
    var all = $$(".elev .tile").filter(function (t) { return state.sv.some(function (s) { return (" " + t.getAttribute("data-sv") + " ").indexOf(" " + s + " ") > -1; }) && (!state.ty || (" " + t.getAttribute("data-ty") + " ").indexOf(" " + state.ty + " ") > -1); });
    all.sort(function (a, b) { return (b.classList.contains("is-v") ? 1 : 0) - (a.classList.contains("is-v") ? 1 : 0); });
    var g = $("#el-clips-g"); g.textContent = ""; box.hidden = false; $("#el-clips-h").textContent = state.sv.map(function (s) { return T.sv[s]; }).join(" + ") + " · " + all.length + " " + (all.length === 1 ? T.clip : T.clips);
    var shown = all.slice(0, clipLimit), list = shown.map(function (t) { return tileData(t, t.querySelector(".cap").textContent); }), tiles = [];
    shown.forEach(function (t, i) { var c = t.cloneNode(true); var v = c.querySelector("video"); if (v) v.remove(); c._v = null; c.addEventListener("click", function (e) { e.preventDefault(); openLb(list, i, c); }); g.appendChild(c); tiles.push(c); });
    tiles.forEach(function (c) { var o = $(".pick", c); if (o) o.remove(); }); decorateAll(); watch(tiles.filter(function (t) { return t.classList.contains("is-v"); })); var mb = $("#el-clips-more"); mb.hidden = all.length <= clipLimit; mb.onclick = function () { clipLimit += 36; clipView(); };
  }
  function pills() {
    var ft = $("#el-ftypes"), fs = $("#el-fsvc"); ft.textContent = ""; fs.textContent = "";
    function pill(label, on, fn, col) { var b = el("button", { class: "pill" + (on ? " on" : ""), type: "button", "aria-pressed": on ? "true" : "false" }, [col ? el("i", { style: "background:" + col }) : null, el("span", { text: label })]); b.onclick = fn; return b; }
    ft.appendChild(pill(T.all, !state.ty, function () { state.ty = null; state.q = ""; state.tx = null; apply(); }));
    Object.keys(T.types).forEach(function (k) { ft.appendChild(pill(T.types[k], state.ty === k, function () { state.ty = state.ty === k ? null : k; state.q = ""; state.tx = null; apply(); }, PAL[k][0])); });
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
  function apply() { clipLimit = 36; var p = PAL[state.ty || "default"]; if (hero) hero.setColors(p.concat(p)); R.style.setProperty("--accent", p[0]); R.style.setProperty("--accent2", p[1]); render(); }
  function jump() { $("#el-work").scrollIntoView({ behavior: reduced ? "auto" : "smooth", block: "start" }); }
  function applyHash(p) { var t = p.get("t"), s = p.get("s"); if (t && T.types[t]) state = { ty: t, sv: [], q: "" }; else if (s) state = { ty: null, sv: s.split(",").filter(function (x) { return T.sv[x]; }), q: "" }; apply(); }

  window.addEventListener("hashchange", route);
  var back = $$("[data-back]"); back.forEach(function (a) { if (mode === "hub") a.addEventListener("click", function (e) { e.preventDefault(); if (location.hash) history.pushState(null, "", location.pathname + location.search); route(); }); });
  if (mode === "hub") { var q0 = new URLSearchParams(location.search).get("q"); initHub(); route(); if (q0) { $("#el-q").value = q0; var p0 = parse(q0); state = { ty: p0.ty, sv: p0.sv, q: q0, tx: textHits(q0) }; apply(); } }
  else { initHubLite(); route(); }
  function initHubLite() { if (window.FX && FX.init) FX.init(R); }
  if (window.parent !== window) { var send = function () { try { parent.postMessage({ echolightHeight: document.documentElement.scrollHeight }, "*"); } catch (e) {} }; setInterval(send, 1500); }
})();
