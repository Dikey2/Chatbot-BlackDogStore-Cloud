/*!
 * Widget de chat de la plataforma de chatbots (Black Dog Store Cloud).
 *
 * Instalación en cualquier web autorizada por el negocio:
 *   <script src="https://PLATAFORMA/widget.js" data-chatbot-id="bd_xxx" defer></script>
 *
 * Opcionales: data-position="left" (por defecto, right), data-offset-bottom="96",
 * data-api-url="https://api.plataforma" (si la API no está en el mismo origen que el script),
 * data-launcher="none" (la página usa su propio botón y llama a window.BDChatbot.open()),
 * data-theme="light" | "dark" | "auto" (sistema operativo) | "host" (sigue el tema de la página).
 *
 * API para la página anfitriona: window.BDChatbot.open() / .close() / .toggle(), el
 * evento "bdchatbot:ready" cuando el widget está listo y "bdchatbot:unread"
 * ({ id, count }) cuando cambian los mensajes sin leer (para el botón propio de la página).
 *
 * Diseño:
 * - Shadow DOM: la página anfitriona no altera el widget y el widget no altera la página.
 * - Nunca lanza errores hacia la página: si algo falla, se registra en consola y se oculta.
 * - Sin claves: el negocio se identifica por su id público y el visitante por un token
 *   de sesión anónima (sessionStorage) que solo abre su propia conversación.
 */
(function () {
  "use strict";

  var script = document.currentScript;
  if (!script) return;
  var publicId = script.getAttribute("data-chatbot-id") || "";
  if (!/^[A-Za-z0-9_-]{4,40}$/.test(publicId)) {
    if (window.console) console.warn("[chatbot] data-chatbot-id inválido o ausente.");
    return;
  }
  // Una sola instancia por chatbot aunque el script se cargue dos veces.
  var flag = "__bdChatbotLoaded_" + publicId;
  if (window[flag]) return;
  window[flag] = true;

  var apiBase;
  try {
    apiBase = (script.getAttribute("data-api-url") || new URL(script.src, location.href).origin).replace(/\/+$/, "");
  } catch (e) {
    return;
  }
  var base = apiBase + "/api/widget/" + encodeURIComponent(publicId);
  var position = script.getAttribute("data-position") === "left" ? "left" : "right";
  var ownLauncher = script.getAttribute("data-launcher") !== "none";
  var offsetBottom = parseInt(script.getAttribute("data-offset-bottom") || "20", 10);
  if (!(offsetBottom >= 0 && offsetBottom <= 400)) offsetBottom = 20;

  var STORE_KEY = "bdchat:" + publicId;
  var REQUEST_TIMEOUT_MS = 12000;
  var POLL_OPEN_MS = 5000;
  var POLL_CLOSED_MS = 20000;
  // Si a la sesión le queda menos que esto, se rota el token al cargar la página.
  var ROTATE_BEFORE_MS = 12 * 60 * 60 * 1000;

  var MESSAGES = {
    network: "Sin conexión con el chat. Revisa tu internet e inténtalo de nuevo.",
    timeout: "El chat tardó demasiado en responder. Inténtalo de nuevo.",
    rate: "Estás enviando mensajes muy rápido. Espera unos segundos.",
    limit: "Se alcanzó el límite de mensajes de esta sesión. Recarga la página más tarde.",
    unavailable: "El chat no está disponible en este momento. Inténtalo en unos minutos.",
    invalid: "Revisa tu mensaje (máximo 500 caracteres).",
    generic: "No se pudo enviar el mensaje. Inténtalo de nuevo."
  };

  // ------------------------------------------------------------------ estado
  var state = {
    config: null,
    token: null,
    conversation: null,
    lastId: 0,
    seen: {},
    open: false,
    sending: false,
    online: navigator.onLine !== false,
    unread: 0,
    pollTimer: null
  };

  function load() {
    try {
      var raw = sessionStorage.getItem(STORE_KEY);
      if (!raw) return;
      var data = JSON.parse(raw);
      if (data && data.token && Date.parse(data.expires_at) > Date.now()) {
        state.token = data.token;
        state.expiresAt = Date.parse(data.expires_at);
      }
    } catch (e) { /* almacenamiento bloqueado: la sesión vive solo en memoria */ }
  }

  function save(token, expiresAt) {
    state.token = token;
    state.expiresAt = expiresAt ? Date.parse(expiresAt) : 0;
    try {
      if (token) sessionStorage.setItem(STORE_KEY, JSON.stringify({ token: token, expires_at: expiresAt }));
      else sessionStorage.removeItem(STORE_KEY);
    } catch (e) { /* ignorado */ }
  }

  // ------------------------------------------------------------------ red
  function ApiError(status, code, message, retryAfter) {
    this.status = status;
    this.code = code;
    this.message = message;
    this.retryAfter = retryAfter;
  }

  function request(method, path, body, attempt) {
    attempt = attempt || 1;
    var controller = typeof AbortController === "function" ? new AbortController() : null;
    var timer = controller ? setTimeout(function () { controller.abort(); }, REQUEST_TIMEOUT_MS) : null;
    var headers = { "Accept": "application/json" };
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (state.token) headers["X-Visitor-Token"] = state.token;
    return fetch(base + path, {
      method: method,
      headers: headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      credentials: "omit",
      mode: "cors",
      signal: controller ? controller.signal : undefined
    }).then(function (response) {
      if (timer) clearTimeout(timer);
      setOnline(true);
      return response.json().catch(function () { return null; }).then(function (data) {
        if (response.ok) return data;
        var err = (data && data.error) || {};
        throw new ApiError(response.status, err.code || "error", err.message || "", response.headers.get("Retry-After"));
      });
    }, function (error) {
      if (timer) clearTimeout(timer);
      var timedOut = error && error.name === "AbortError";
      // Solo las lecturas se reintentan solas: reenviar un mensaje podría duplicarlo.
      if (method === "GET" && attempt < 2 && !timedOut) {
        return wait(800).then(function () { return request(method, path, body, attempt + 1); });
      }
      setOnline(false);
      throw new ApiError(0, timedOut ? "timeout" : "network", "");
    }).catch(function (error) {
      // Sesión vencida o rotada: se crea otra y se repite UNA vez (el servidor no procesó nada).
      if (error instanceof ApiError && error.status === 401 && attempt < 3 && path !== "/session/") {
        save(null);
        return ensureSession().then(function () { return request(method, path, body, 3); });
      }
      throw error;
    });
  }

  function wait(ms) { return new Promise(function (resolve) { setTimeout(resolve, ms); }); }

  /** Token nuevo para la misma conversación; el anterior deja de servir en el servidor. */
  function rotateIfOld() {
    if (!state.token || !(state.expiresAt - Date.now() < ROTATE_BEFORE_MS)) return Promise.resolve();
    return request("POST", "/session/rotate/", {})
      .then(function (data) { save(data.token, data.expires_at); })
      .catch(function () { /* si falla, se sigue con el token actual hasta que venza */ });
  }

  function ensureSession() {
    if (state.token) return Promise.resolve();
    return request("POST", "/session/", {}).then(function (data) { save(data.token, data.expires_at); });
  }

  function errorText(error) {
    if (!(error instanceof ApiError)) return MESSAGES.generic;
    if (error.code === "timeout" || error.status === 504) return MESSAGES.timeout;
    if (error.code === "network") return MESSAGES.network;
    if (error.code === "session_message_limit") return MESSAGES.limit;
    if (error.status === 429) {
      var seconds = parseInt(error.retryAfter || "", 10);
      return seconds > 0 ? MESSAGES.rate.replace("unos segundos", seconds + " s") : MESSAGES.rate;
    }
    if (error.status === 400) return MESSAGES.invalid;
    if (error.status >= 500) return MESSAGES.unavailable;
    return MESSAGES.generic;
  }

  // ------------------------------------------------------------------ interfaz
  var host, root, ui = {};

  function el(tag, attrs, text) {
    var node = document.createElement(tag);
    if (attrs) for (var k in attrs) if (Object.prototype.hasOwnProperty.call(attrs, k)) node.setAttribute(k, attrs[k]);
    if (text) node.textContent = text; // nunca innerHTML con datos: sin inyección de HTML
    return node;
  }

  function safeColor(value) {
    return /^#[0-9A-Fa-f]{6}$/.test(value || "") ? value : "#111111";
  }

  function luma(hex) {
    var r = parseInt(hex.substr(1, 2), 16), g = parseInt(hex.substr(3, 2), 16), b = parseInt(hex.substr(5, 2), 16);
    return (r * 299 + g * 587 + b * 114) / 1000;
  }

  function contrast(hex) {
    return luma(hex) > 150 ? "#111111" : "#ffffff";
  }

  /** Color de acento legible en cada tema: un color casi negro no se ve sobre fondo
   *  oscuro (se usa blanco) y uno casi blanco no se ve sobre fondo claro (se usa negro). */
  function accents(primary) {
    var light = luma(primary) > 225 ? "#111111" : primary;
    var dark = luma(primary) < 60 ? "#fafafa" : primary;
    return { light: light, lightFg: contrast(light), dark: dark, darkFg: contrast(dark) };
  }

  var ICON_CHAT = '<svg viewBox="0 0 24 24" width="26" height="26" aria-hidden="true" focusable="false"><path fill="currentColor" d="M4 4h16a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H8l-4 4V6a2 2 0 0 1 2-2z"/></svg>';
  var ICON_CLOSE = '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false"><path fill="currentColor" d="M18.3 5.7 12 12l6.3 6.3-1.4 1.4L10.6 13.4 4.3 19.7 2.9 18.3 9.2 12 2.9 5.7 4.3 4.3l6.3 6.3 6.3-6.3z"/></svg>';
  var ICON_SEND = '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" focusable="false"><path fill="currentColor" d="M3 20.5 21 12 3 3.5 3 10l12 2-12 2z"/></svg>';

  function css(primary) {
    var a = accents(primary);
    var side = position + ":20px;";
    return [
      // Tema claro (por defecto) y oscuro con los mismos nombres de variables.
      ":host{all:initial;",
      "--accent:" + a.light + ";--accent-fg:" + a.lightFg + ";",
      "--panel:#ffffff;--text:#111111;--muted:#555555;--log:#f6f6f7;--line:#e5e5e5;",
      "--bubble:#ffffff;--bubble-line:#e5e5e5;--advisor:#eff6ff;--advisor-line:#bfdbfe;",
      "--field:#ffffff;--field-line:#d4d4d4;--link:#2563eb;--dot:#999999;",
      "--error:#991b1b;--error-bg:#fef2f2;--error-line:#fecaca;",
      "--head:" + a.light + ";--head-fg:" + a.lightFg + ";--head-line:transparent;",
      "--shadow:0 18px 50px rgba(0,0,0,.3);}",
      ":host([data-mode=dark]){",
      "--accent:" + a.dark + ";--accent-fg:" + a.darkFg + ";",
      "--panel:#141414;--text:#fafafa;--muted:#a3a3a3;--log:#0a0a0a;--line:#262626;",
      "--bubble:#1c1c1c;--bubble-line:#2a2a2a;--advisor:#172554;--advisor-line:#1e3a8a;",
      "--field:#0f0f0f;--field-line:#333333;--link:#93c5fd;--dot:#737373;",
      "--error:#fca5a5;--error-bg:#2a1212;--error-line:#7f1d1d;",
      "--head:#141414;--head-fg:#fafafa;--head-line:#262626;",
      "--shadow:0 18px 50px rgba(0,0,0,.7),0 0 0 1px #262626;}",
      "*{box-sizing:border-box;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;}",
      ".launcher{position:fixed;" + side + "bottom:" + offsetBottom + "px;width:58px;height:58px;border-radius:50%;border:0;cursor:pointer;",
      "background:var(--accent);color:var(--accent-fg);box-shadow:0 8px 24px rgba(0,0,0,.25);display:flex;align-items:center;justify-content:center;z-index:2147483000;transition:transform .2s;}",
      ".launcher:hover{transform:scale(1.05);}",
      "[hidden]{display:none!important;}",
      ".launcher:focus-visible,button:focus-visible,textarea:focus-visible{outline:3px solid #2563eb;outline-offset:2px;}",
      ".badge{position:absolute;top:-2px;right:-2px;min-width:20px;height:20px;border-radius:10px;background:#dc2626;color:#fff;font-size:12px;font-weight:700;display:flex;align-items:center;justify-content:center;padding:0 5px;}",
      ".panel{position:fixed;" + side + "bottom:" + (offsetBottom + (ownLauncher ? 70 : 0)) + "px;width:370px;max-width:calc(100vw - 24px);height:560px;max-height:calc(100vh - " + (offsetBottom + 90) + "px);",
      "background:var(--panel);color:var(--text);border-radius:16px;box-shadow:var(--shadow);display:flex;flex-direction:column;overflow:hidden;z-index:2147483001;",
      "opacity:0;transform:translateY(12px);pointer-events:none;transition:opacity .18s,transform .18s;}",
      ".panel.open{opacity:1;transform:none;pointer-events:auto;}",
      "@media (max-width:480px){.panel{left:0;right:0;bottom:0;width:100vw;max-width:100vw;height:88vh;max-height:88vh;border-radius:16px 16px 0 0;}.panel.open~.launcher{display:none;}}",
      "@media (prefers-reduced-motion:reduce){.panel,.launcher{transition:none;}}",
      ".head{background:var(--head);color:var(--head-fg);border-bottom:1px solid var(--head-line);padding:14px 14px;display:flex;align-items:center;gap:10px;}",
      ".logo{width:34px;height:34px;border-radius:50%;object-fit:cover;background:rgba(255,255,255,.2);}",
      ".title{flex:1;min-width:0;}",
      ".name{font-size:15px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}",
      ".status{font-size:12px;opacity:.85;display:flex;align-items:center;gap:6px;}",
      ".dot{width:8px;height:8px;border-radius:50%;background:#22c55e;}.dot.off{background:#f59e0b;}",
      ".close{background:transparent;border:0;color:inherit;cursor:pointer;padding:6px;border-radius:8px;display:flex;}",
      ".log{flex:1;overflow-y:auto;padding:14px;background:var(--log);display:flex;flex-direction:column;gap:8px;}",
      ".msg{max-width:82%;padding:9px 12px;border-radius:14px;font-size:14px;line-height:1.4;white-space:pre-wrap;word-wrap:break-word;}",
      ".msg.cliente{align-self:flex-end;background:var(--accent);color:var(--accent-fg);border-bottom-right-radius:4px;}",
      ".msg.bot,.msg.asesor{align-self:flex-start;background:var(--bubble);color:var(--text);border:1px solid var(--bubble-line);border-bottom-left-radius:4px;}",
      ".msg.asesor{border-color:var(--advisor-line);background:var(--advisor);}",
      ".who{display:block;font-size:11px;font-weight:700;opacity:.7;margin-bottom:2px;}",
      ".notice{align-self:center;font-size:12px;color:var(--muted);text-align:center;padding:4px 8px;}",
      ".error{align-self:stretch;font-size:13px;color:var(--error);background:var(--error-bg);border:1px solid var(--error-line);border-radius:10px;padding:8px 10px;display:flex;gap:8px;align-items:center;justify-content:space-between;}",
      ".error button{background:var(--panel);color:var(--text);border:1px solid var(--error-line);border-radius:8px;padding:4px 8px;cursor:pointer;font-size:12px;}",
      ".typing{align-self:flex-start;background:var(--bubble);border:1px solid var(--bubble-line);border-radius:14px;padding:10px 12px;display:flex;gap:4px;}",
      ".typing span{width:6px;height:6px;border-radius:50%;background:var(--dot);animation:b 1s infinite;}",
      ".typing span:nth-child(2){animation-delay:.15s}.typing span:nth-child(3){animation-delay:.3s}",
      "@keyframes b{0%,80%,100%{opacity:.3}40%{opacity:1}}",
      "@media (prefers-reduced-motion:reduce){.typing span{animation:none;}}",
      ".foot{border-top:1px solid var(--line);padding:10px;background:var(--panel);}",
      ".row{display:flex;gap:8px;align-items:flex-end;}",
      "textarea{flex:1;resize:none;border:1px solid var(--field-line);border-radius:12px;padding:9px 10px;font-size:14px;max-height:96px;min-height:40px;color:var(--text);background:var(--field);}",
      "textarea::placeholder{color:var(--muted);}",
      ".send{width:40px;height:40px;border-radius:12px;border:0;background:var(--accent);color:var(--accent-fg);cursor:pointer;display:flex;align-items:center;justify-content:center;}",
      ".send:disabled{opacity:.5;cursor:not-allowed;}",
      ".human{margin-top:8px;background:none;border:0;color:var(--link);font-size:12px;cursor:pointer;padding:2px;}",
      ".human:disabled{color:var(--muted);cursor:default;}",
      ".sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap;}"
    ].join("");
  }

  // ------------------------------------------------------------------ tema
  // data-theme: light (por defecto) | dark | auto (sistema operativo) | host (la página).
  var themeAttr = (script.getAttribute("data-theme") || "light").toLowerCase();
  var themeMode = /^(light|dark|auto|host)$/.test(themeAttr) ? themeAttr : "light";

  /** Tema de la página anfitriona: data-theme / clase "dark" en <html> o <body>, o su color-scheme. */
  function hostTheme() {
    var nodes = [document.documentElement, document.body];
    for (var i = 0; i < nodes.length; i++) {
      var n = nodes[i];
      if (!n) continue;
      var attr = (n.getAttribute("data-theme") || n.getAttribute("data-mode") || "").toLowerCase();
      if (attr === "dark" || attr === "light") return attr;
      if (n.classList && n.classList.contains("dark")) return "dark";
      if (n.classList && n.classList.contains("light")) return "light";
    }
    try {
      var scheme = getComputedStyle(document.documentElement).colorScheme || "";
      if (scheme.trim() === "dark") return "dark";
    } catch (e) { /* ignorado */ }
    return systemTheme();
  }

  function systemTheme() {
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function resolvedTheme() {
    if (themeMode === "dark" || themeMode === "light") return themeMode;
    return themeMode === "host" ? hostTheme() : systemTheme();
  }

  function applyTheme() {
    if (host) host.setAttribute("data-mode", resolvedTheme());
  }

  function watchTheme() {
    applyTheme();
    if (themeMode === "host" && typeof MutationObserver === "function") {
      var observer = new MutationObserver(applyTheme);
      var opts = { attributes: true, attributeFilter: ["data-theme", "data-mode", "class", "style"] };
      observer.observe(document.documentElement, opts);
      if (document.body) observer.observe(document.body, opts);
    }
    if ((themeMode === "host" || themeMode === "auto") && window.matchMedia) {
      var mq = window.matchMedia("(prefers-color-scheme: dark)");
      if (mq.addEventListener) mq.addEventListener("change", applyTheme);
      else if (mq.addListener) mq.addListener(applyTheme);
    }
  }

  function build(config) {
    var primary = safeColor(config.primary_color);
    host = el("div", { "data-bd-chatbot": publicId });
    root = host.attachShadow ? host.attachShadow({ mode: "open" }) : host;
    var style = el("style");
    style.textContent = css(primary);
    root.appendChild(style);
    watchTheme();

    var panelId = "bd-chat-panel";
    ui.panel = el("section", { "class": "panel", id: panelId, role: "dialog", "aria-modal": "false", "aria-label": config.assistant_name, "aria-hidden": "true" });

    var head = el("div", { "class": "head" });
    if (config.business && /^https:\/\//.test(config.business.logo_url || "")) {
      head.appendChild(el("img", { "class": "logo", src: config.business.logo_url, alt: "" }));
    }
    var title = el("div", { "class": "title" });
    title.appendChild(el("div", { "class": "name" }, config.assistant_name));
    ui.status = el("div", { "class": "status", "aria-live": "polite" });
    ui.dot = el("span", { "class": "dot", "aria-hidden": "true" });
    ui.statusText = el("span", null, "En línea");
    ui.status.appendChild(ui.dot);
    ui.status.appendChild(ui.statusText);
    title.appendChild(ui.status);
    head.appendChild(title);
    ui.close = el("button", { "class": "close", type: "button", "aria-label": "Cerrar chat" });
    ui.close.innerHTML = ICON_CLOSE;
    head.appendChild(ui.close);
    ui.panel.appendChild(head);

    ui.log = el("div", { "class": "log", role: "log", "aria-live": "polite", "aria-relevant": "additions" });
    ui.panel.appendChild(ui.log);

    var foot = el("form", { "class": "foot", novalidate: "novalidate" });
    var row = el("div", { "class": "row" });
    var label = el("label", { "class": "sr", "for": "bd-chat-input" }, "Escribe tu mensaje");
    ui.input = el("textarea", { id: "bd-chat-input", rows: "1", maxlength: "500", placeholder: "Escribe tu mensaje…", autocomplete: "off" });
    ui.send = el("button", { "class": "send", type: "submit", "aria-label": "Enviar mensaje" });
    ui.send.innerHTML = ICON_SEND;
    row.appendChild(label);
    row.appendChild(ui.input);
    row.appendChild(ui.send);
    foot.appendChild(row);
    ui.human = el("button", { "class": "human", type: "button" }, "Hablar con un asesor");
    foot.appendChild(ui.human);
    ui.form = foot;
    ui.panel.appendChild(foot);

    ui.launcher = el("button", { "class": "launcher", type: "button", "aria-label": "Abrir chat con " + config.assistant_name, "aria-expanded": "false", "aria-controls": panelId });
    ui.launcher.innerHTML = ICON_CHAT;
    ui.badge = el("span", { "class": "badge", hidden: "hidden", "aria-hidden": "true" });
    ui.launcher.appendChild(ui.badge);

    root.appendChild(ui.panel);
    if (ownLauncher) root.appendChild(ui.launcher);
    document.body.appendChild(host);

    ui.launcher.addEventListener("click", function () { toggle(!state.open); });
    ui.close.addEventListener("click", function () { toggle(false); });
    ui.panel.addEventListener("keydown", function (event) {
      if (event.key === "Escape") { event.stopPropagation(); toggle(false); }
    });
    ui.input.addEventListener("keydown", function (event) {
      if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); submit(); }
    });
    ui.form.addEventListener("submit", function (event) { event.preventDefault(); submit(); });
    ui.human.addEventListener("click", askHuman);
    window.addEventListener("online", function () { setOnline(true); schedulePoll(0); });
    window.addEventListener("offline", function () { setOnline(false); });
    document.addEventListener("visibilitychange", function () { if (!document.hidden) schedulePoll(0); });

    addNotice(config.welcome_message, "bot");
  }

  function setOnline(value) {
    state.online = value;
    if (!ui.dot) return;
    ui.dot.className = value ? "dot" : "dot off";
    ui.statusText.textContent = value ? "En línea" : "Sin conexión";
  }

  function notifyUnread() {
    try {
      window.dispatchEvent(new CustomEvent("bdchatbot:unread", { detail: { id: publicId, count: state.unread } }));
    } catch (e) { /* navegadores antiguos */ }
  }

  function scroll() { ui.log.scrollTop = ui.log.scrollHeight; }

  function addNotice(text, kind) {
    var node = el("div", { "class": "msg " + (kind || "bot") }, text);
    ui.log.appendChild(node);
    scroll();
    return node;
  }

  function addMessage(message) {
    if (!message || state.seen[message.id]) return;
    state.seen[message.id] = true;
    if (message.id > state.lastId) state.lastId = message.id;
    var node = el("div", { "class": "msg " + message.sender });
    if (message.sender === "asesor") node.appendChild(el("span", { "class": "who" }, "Asesor"));
    node.appendChild(document.createTextNode(message.content));
    ui.log.appendChild(node);
    if (!state.open && message.sender !== "cliente") {
      state.unread += 1;
      ui.badge.textContent = String(state.unread);
      ui.badge.removeAttribute("hidden");
      notifyUnread();
    }
    scroll();
  }

  function showError(text, retry) {
    clearError();
    ui.error = el("div", { "class": "error", role: "alert" });
    ui.error.appendChild(el("span", null, text));
    if (retry) {
      var button = el("button", { type: "button" }, "Reintentar");
      button.addEventListener("click", function () { clearError(); retry(); });
      ui.error.appendChild(button);
    }
    ui.log.appendChild(ui.error);
    scroll();
  }

  function clearError() {
    if (ui.error && ui.error.parentNode) ui.error.parentNode.removeChild(ui.error);
    ui.error = null;
  }

  function typing(on) {
    if (on && !ui.typing) {
      ui.typing = el("div", { "class": "typing", "aria-label": "El asistente está escribiendo" });
      for (var i = 0; i < 3; i++) ui.typing.appendChild(el("span"));
      ui.log.appendChild(ui.typing);
      scroll();
    } else if (!on && ui.typing) {
      ui.typing.parentNode.removeChild(ui.typing);
      ui.typing = null;
    }
  }

  function setConversation(conversation) {
    state.conversation = conversation;
    var derived = conversation && (conversation.status === "derivada" || conversation.status === "atendiendo");
    ui.human.disabled = !!derived;
    ui.human.textContent = derived ? "Un asesor revisará tu consulta" : "Hablar con un asesor";
    if (conversation && conversation.status === "cerrada" && !state.closedNotice) {
      state.closedNotice = conversation.id;
      var notice = el("div", { "class": "notice" }, "Esta consulta fue cerrada. Si escribes de nuevo, se abrirá otra.");
      ui.log.appendChild(notice);
      scroll();
    }
  }

  function toggle(open) {
    state.open = open;
    ui.panel.className = open ? "panel open" : "panel";
    ui.panel.setAttribute("aria-hidden", open ? "false" : "true");
    ui.launcher.setAttribute("aria-expanded", open ? "true" : "false");
    if (open) {
      state.unread = 0;
      ui.badge.setAttribute("hidden", "hidden");
      notifyUnread();
      setTimeout(function () { try { ui.input.focus(); } catch (e) { /* ignorado */ } }, 50);
      refresh();
    } else if (ownLauncher) {
      ui.launcher.focus();
    } else if (state.opener && state.opener.focus) {
      state.opener.focus();
    }
    schedulePoll(open ? POLL_OPEN_MS : POLL_CLOSED_MS);
  }

  // ------------------------------------------------------------------ acciones
  function refresh() {
    if (!state.token) return Promise.resolve();
    return request("GET", "/conversation/?after=" + state.lastId).then(function (data) {
      if (data.conversation && state.conversation && data.conversation.id !== state.conversation.id) {
        state.closedNotice = null;
      }
      (data.messages || []).forEach(addMessage);
      setConversation(data.conversation);
    }).catch(function (error) {
      if (error instanceof ApiError && error.status === 401) { save(null); return; }
      // El sondeo falla en silencio; el estado de conexión ya lo indica.
    });
  }

  function schedulePoll(delay) {
    if (state.pollTimer) clearTimeout(state.pollTimer);
    var waiting = state.conversation && (state.conversation.status === "derivada" || state.conversation.status === "atendiendo");
    if (!state.token || (!state.open && !waiting)) return;
    state.pollTimer = setTimeout(function () {
      if (document.hidden) return schedulePoll(state.open ? POLL_OPEN_MS : POLL_CLOSED_MS);
      refresh().then(function () { schedulePoll(state.open ? POLL_OPEN_MS : POLL_CLOSED_MS); });
    }, delay);
  }

  function submit() {
    var text = (ui.input.value || "").trim();
    if (!text || state.sending) return;
    if (text.length > 500) { showError(MESSAGES.invalid); return; }
    send(text);
  }

  function send(text) {
    state.sending = true;
    ui.send.disabled = true;
    clearError();
    ui.input.value = "";
    var pending = el("div", { "class": "msg cliente" }, text);
    ui.log.appendChild(pending);
    scroll();
    typing(true);
    ensureSession()
      .then(function () { return request("POST", "/messages/", { message: text }); })
      .then(function (data) {
        typing(false);
        pending.parentNode.removeChild(pending);
        addMessage(data.user_message);
        addMessage(data.bot_message);
        setConversation(data.conversation);
        if (data.degraded) setOnline(true);
        schedulePoll(POLL_OPEN_MS);
      })
      .catch(function (error) {
        typing(false);
        pending.style.opacity = "0.55";
        var retryable = !(error instanceof ApiError) || error.status === 0 || error.status >= 500 || error.status === 429;
        showError(errorText(error), retryable ? function () {
          if (pending.parentNode) pending.parentNode.removeChild(pending);
          send(text);
        } : null);
      })
      .then(function () {
        state.sending = false;
        ui.send.disabled = false;
      });
  }

  function askHuman() {
    if (!state.conversation) {
      showError("Escribe tu consulta y luego podrás pedir un asesor.");
      return;
    }
    ui.human.disabled = true;
    request("POST", "/handoff/", {})
      .then(function (data) {
        if (data.bot_message) addMessage(data.bot_message);
        setConversation(data.conversation);
        schedulePoll(POLL_OPEN_MS);
      })
      .catch(function (error) {
        ui.human.disabled = false;
        showError(errorText(error));
      });
  }

  // ------------------------------------------------------------------ API pública
  function expose() {
    var api = window.BDChatbot || {};
    var instances = api._instances || {};
    instances[publicId] = { toggle: toggle, isOpen: function () { return state.open; } };
    var pick = function (id) { return instances[id || Object.keys(instances)[0]]; };
    window.BDChatbot = {
      _instances: instances,
      open: function (id) {
        var it = pick(id);
        if (it) { state.opener = document.activeElement; it.toggle(true); }
      },
      close: function (id) { var it = pick(id); if (it) it.toggle(false); },
      toggle: function (id) { var it = pick(id); if (it) it.toggle(!it.isOpen()); },
      isOpen: function (id) { var it = pick(id); return !!(it && it.isOpen()); },
      // Tema: "light", "dark", "auto" o "host". La página lo puede cambiar en cualquier momento.
      setTheme: function (mode) {
        if (/^(light|dark|auto|host)$/.test(String(mode))) { themeMode = mode; applyTheme(); }
      }
    };
    try {
      window.dispatchEvent(new CustomEvent("bdchatbot:ready", { detail: { id: publicId } }));
    } catch (e) { /* navegadores antiguos */ }
  }

  // ------------------------------------------------------------------ arranque
  function start() {
    load();
    request("GET", "/config/")
      .then(function (config) {
        state.config = config;
        build(config);
        expose();
        if (state.token) {
          rotateIfOld()
            .then(refresh)
            .then(function () { schedulePoll(POLL_CLOSED_MS); });
        }
      })
      .catch(function (error) {
        // Chatbot inexistente, suspendido u origen no autorizado: la página sigue igual.
        if (window.console) console.warn("[chatbot] no se cargó el widget:", error && (error.code || error.message));
      });
  }

  try {
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
    else start();
  } catch (e) {
    if (window.console) console.warn("[chatbot] error al iniciar el widget", e);
  }
})();
