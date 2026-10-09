// EchoLight website chat. Add to the site with:
// <script src="https://YOUR-SALESBOT-HOST/widget.js" defer></script>
(function () {
  var script = document.currentScript;
  var base = script ? new URL(script.src).origin : "";
  var arabic = (document.documentElement.lang || "").toLowerCase().indexOf("ar") === 0 ||
    location.pathname.indexOf("/ar") === 0;
  var t = arabic
    ? { open: "تحدث معنا", title: "إيكو لايت", placeholder: "اكتب رسالتك...", send: "إرسال",
        hello: "أهلاً! حدثنا عن فعاليتك: النوع، التاريخ والمكان، وبنساعدك فوراً.", wait: "..." }
    : { open: "Chat with us", title: "EchoLight", placeholder: "Type your message...", send: "Send",
        hello: "Hi! Tell us about your event (type, date and venue) and we'll help right away.", wait: "..." };

  function sessionId() {
    var id = null;
    try { id = localStorage.getItem("echolight_chat_session"); } catch (e) {}
    if (!id) {
      id = (crypto.randomUUID ? crypto.randomUUID() : String(Date.now()) + Math.random().toString(16).slice(2));
      try { localStorage.setItem("echolight_chat_session", id); } catch (e) {}
    }
    return id;
  }

  var css = document.createElement("style");
  css.textContent =
    "#el-chat-btn{position:fixed;bottom:20px;inset-inline-end:20px;z-index:99999;background:#111;color:#fff;" +
    "border:0;border-radius:24px;padding:12px 18px;font:600 15px system-ui;box-shadow:0 4px 16px rgba(0,0,0,.3);cursor:pointer}" +
    "#el-chat{position:fixed;bottom:80px;inset-inline-end:20px;z-index:99999;width:min(360px,calc(100vw - 32px));" +
    "height:min(520px,calc(100vh - 120px));background:#fff;color:#111;border-radius:14px;display:none;flex-direction:column;" +
    "box-shadow:0 8px 32px rgba(0,0,0,.35);font:14px/1.45 system-ui;overflow:hidden}" +
    "#el-chat header{background:#111;color:#fff;padding:12px 14px;font-weight:600;display:flex;justify-content:space-between}" +
    "#el-chat header button{background:none;border:0;color:#fff;font-size:18px;cursor:pointer}" +
    "#el-log{flex:1;overflow-y:auto;padding:12px;display:flex;flex-direction:column;gap:8px}" +
    ".el-msg{max-width:85%;padding:8px 11px;border-radius:12px;white-space:pre-wrap;word-wrap:break-word}" +
    ".el-bot{background:#f1f1f1;align-self:flex-start}.el-me{background:#111;color:#fff;align-self:flex-end}" +
    "#el-form{display:flex;border-top:1px solid #eee}#el-input{flex:1;border:0;padding:12px;font:inherit;outline:none}" +
    "#el-form button{border:0;background:#111;color:#fff;padding:0 16px;font:600 14px system-ui;cursor:pointer}";
  document.head.appendChild(css);

  var btn = document.createElement("button");
  btn.id = "el-chat-btn";
  btn.textContent = t.open;
  var panel = document.createElement("div");
  panel.id = "el-chat";
  panel.dir = arabic ? "rtl" : "ltr";
  panel.innerHTML = '<header><span></span><button aria-label="Close">×</button></header><div id="el-log"></div>' +
    '<form id="el-form"><input id="el-input" autocomplete="off"><button type="submit"></button></form>';
  panel.querySelector("header span").textContent = t.title;
  panel.querySelector("#el-input").placeholder = t.placeholder;
  panel.querySelector("#el-form button").textContent = t.send;
  document.body.appendChild(btn);
  document.body.appendChild(panel);

  var log = panel.querySelector("#el-log");
  function add(text, who) {
    var div = document.createElement("div");
    div.className = "el-msg " + (who === "me" ? "el-me" : "el-bot");
    div.textContent = text;
    log.appendChild(div);
    log.scrollTop = log.scrollHeight;
    return div;
  }

  var greeted = false;
  btn.onclick = function () {
    panel.style.display = panel.style.display === "flex" ? "none" : "flex";
    if (!greeted) { add(t.hello, "bot"); greeted = true; }
    panel.querySelector("#el-input").focus();
  };
  panel.querySelector("header button").onclick = function () { panel.style.display = "none"; };

  panel.querySelector("#el-form").onsubmit = function (e) {
    e.preventDefault();
    var input = panel.querySelector("#el-input");
    var text = input.value.trim();
    if (!text) return;
    input.value = "";
    add(text, "me");
    var pending = add(t.wait, "bot");
    fetch(base + "/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId(), text: text })
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.reply) { pending.textContent = data.reply; } else { pending.remove(); }
        if (data.detail) { pending.textContent = data.detail; }
      })
      .catch(function () { pending.textContent = "WhatsApp: +971 56 722 0533"; });
  };
})();
