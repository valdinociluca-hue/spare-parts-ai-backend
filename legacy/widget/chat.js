/**
 * Spare Parts AI Chat Widget
 * Embed on lvtrade.ru with:
 *   <script src="https://api.lvtrade.ru/widget/chat.js" defer></script>
 *
 * Or self-host this file and point to your own API:
 *   <script src="/static/chat.js" data-api="https://api.lvtrade.ru" defer></script>
 */
(function () {
  "use strict";

  // ── Config ─────────────────────────────────────────────────────────────
  var currentScript = document.currentScript || (function () {
    var scripts = document.getElementsByTagName("script");
    return scripts[scripts.length - 1];
  })();

  var API_BASE = (currentScript && currentScript.getAttribute("data-api"))
    || "https://api.lvtrade.ru";

  var CHAT_ENDPOINT = API_BASE + "/api/v1/chat";

  var STRINGS = {
    title:       "Консультант по запчастям",
    subtitle:    "Онлайн — отвечу за секунды",
    placeholder: "Опишите технику или номер детали...",
    send:        "Отправить",
    welcome:     "Здравствуйте! Я помогу подобрать запчасти для вашего оборудования. Укажите марку, модель или артикул детали.",
    error:       "Произошла ошибка. Попробуйте ещё раз.",
    thinking:    "Подбираю...",
  };

  // ── State ──────────────────────────────────────────────────────────────
  var sessionId = null;
  var isOpen    = false;
  var isLoading = false;

  // ── Styles ────────────────────────────────────────────────────────────
  var CSS = `
    #sp-chat-widget * { box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
    #sp-chat-widget { position: fixed; bottom: 24px; right: 24px; z-index: 9999; }

    #sp-chat-btn {
      width: 56px; height: 56px; border-radius: 50%;
      background: #1a56db; color: #fff; border: none; cursor: pointer;
      box-shadow: 0 4px 12px rgba(0,0,0,0.25);
      display: flex; align-items: center; justify-content: center;
      transition: transform 0.2s, box-shadow 0.2s;
    }
    #sp-chat-btn:hover { transform: scale(1.08); box-shadow: 0 6px 16px rgba(0,0,0,0.3); }
    #sp-chat-btn svg { width: 26px; height: 26px; }

    #sp-chat-window {
      display: none; flex-direction: column;
      position: absolute; bottom: 68px; right: 0;
      width: 360px; height: 520px;
      background: #fff; border-radius: 16px;
      box-shadow: 0 8px 32px rgba(0,0,0,0.18);
      overflow: hidden;
    }
    #sp-chat-window.open { display: flex; }

    #sp-chat-header {
      background: #1a56db; color: #fff;
      padding: 14px 16px; display: flex; align-items: center; gap: 12px;
    }
    #sp-chat-header-avatar {
      width: 38px; height: 38px; border-radius: 50%;
      background: rgba(255,255,255,0.2);
      display: flex; align-items: center; justify-content: center; flex-shrink: 0;
    }
    #sp-chat-header-avatar svg { width: 22px; height: 22px; }
    #sp-chat-header-text { flex: 1; min-width: 0; }
    #sp-chat-header-title { font-size: 14px; font-weight: 600; line-height: 1.3; }
    #sp-chat-header-subtitle { font-size: 11px; opacity: 0.82; margin-top: 1px; }
    #sp-chat-close {
      background: none; border: none; color: rgba(255,255,255,0.8);
      cursor: pointer; padding: 4px; border-radius: 4px; line-height: 0;
    }
    #sp-chat-close:hover { color: #fff; background: rgba(255,255,255,0.15); }

    #sp-chat-messages {
      flex: 1; overflow-y: auto; padding: 16px;
      display: flex; flex-direction: column; gap: 10px;
      scroll-behavior: smooth;
    }
    #sp-chat-messages::-webkit-scrollbar { width: 4px; }
    #sp-chat-messages::-webkit-scrollbar-thumb { background: #d1d5db; border-radius: 2px; }

    .sp-msg { max-width: 82%; word-wrap: break-word; }
    .sp-msg-bot {
      align-self: flex-start;
      background: #f3f4f6; color: #111827;
      padding: 10px 14px; border-radius: 0 14px 14px 14px;
      font-size: 13.5px; line-height: 1.5;
    }
    .sp-msg-user {
      align-self: flex-end;
      background: #1a56db; color: #fff;
      padding: 10px 14px; border-radius: 14px 14px 0 14px;
      font-size: 13.5px; line-height: 1.5;
    }
    .sp-msg-typing {
      align-self: flex-start;
      background: #f3f4f6;
      padding: 10px 14px; border-radius: 0 14px 14px 14px;
      display: flex; gap: 4px; align-items: center;
    }
    .sp-dot {
      width: 7px; height: 7px; border-radius: 50%; background: #9ca3af;
      animation: sp-bounce 1.2s infinite ease-in-out;
    }
    .sp-dot:nth-child(2) { animation-delay: 0.2s; }
    .sp-dot:nth-child(3) { animation-delay: 0.4s; }
    @keyframes sp-bounce { 0%,80%,100%{transform:scale(0.6)} 40%{transform:scale(1)} }

    #sp-chat-footer {
      border-top: 1px solid #e5e7eb;
      padding: 10px 12px;
      display: flex; gap: 8px; align-items: flex-end;
      background: #fff;
    }
    #sp-chat-input {
      flex: 1; resize: none; border: 1px solid #d1d5db; border-radius: 10px;
      padding: 9px 12px; font-size: 13.5px; line-height: 1.5; outline: none;
      max-height: 96px; min-height: 38px;
      transition: border-color 0.15s;
    }
    #sp-chat-input:focus { border-color: #1a56db; }
    #sp-chat-send {
      background: #1a56db; color: #fff; border: none; cursor: pointer;
      border-radius: 10px; padding: 9px 14px; font-size: 13px; font-weight: 500;
      white-space: nowrap; transition: background 0.15s;
      align-self: flex-end;
    }
    #sp-chat-send:hover { background: #1648c0; }
    #sp-chat-send:disabled { background: #93c5fd; cursor: not-allowed; }

    @media (max-width: 420px) {
      #sp-chat-window { width: calc(100vw - 32px); right: -8px; }
    }
  `;

  // ── DOM ────────────────────────────────────────────────────────────────
  function buildWidget() {
    // Inject styles
    var style = document.createElement("style");
    style.textContent = CSS;
    document.head.appendChild(style);

    var container = document.createElement("div");
    container.id = "sp-chat-widget";
    container.innerHTML = `
      <div id="sp-chat-window">
        <div id="sp-chat-header">
          <div id="sp-chat-header-avatar">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 3H5a2 2 0 00-2 2v4m6-6h10a2 2 0 012 2v4M9 3v18m0 0h10a2 2 0 002-2V9M9 21H5a2 2 0 01-2-2V9m0 0h18"/>
            </svg>
          </div>
          <div id="sp-chat-header-text">
            <div id="sp-chat-header-title">${STRINGS.title}</div>
            <div id="sp-chat-header-subtitle">${STRINGS.subtitle}</div>
          </div>
          <button id="sp-chat-close" aria-label="Закрыть">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
        <div id="sp-chat-messages"></div>
        <div id="sp-chat-footer">
          <textarea id="sp-chat-input" rows="1" placeholder="${STRINGS.placeholder}"></textarea>
          <button id="sp-chat-send">${STRINGS.send}</button>
        </div>
      </div>
      <button id="sp-chat-btn" aria-label="Открыть чат">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
        </svg>
      </button>
    `;
    document.body.appendChild(container);

    // Events
    document.getElementById("sp-chat-btn").addEventListener("click", toggleChat);
    document.getElementById("sp-chat-close").addEventListener("click", toggleChat);
    document.getElementById("sp-chat-send").addEventListener("click", sendMessage);
    document.getElementById("sp-chat-input").addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
    });
    document.getElementById("sp-chat-input").addEventListener("input", autoResizeTextarea);

    // Show welcome on first open
    appendBotMessage(STRINGS.welcome);
  }

  // ── Helpers ────────────────────────────────────────────────────────────
  function toggleChat() {
    isOpen = !isOpen;
    var win = document.getElementById("sp-chat-window");
    win.classList.toggle("open", isOpen);
    if (isOpen) {
      setTimeout(function () {
        document.getElementById("sp-chat-input").focus();
      }, 60);
    }
  }

  function appendBotMessage(text) {
    var msgs = document.getElementById("sp-chat-messages");
    var el = document.createElement("div");
    el.className = "sp-msg sp-msg-bot";
    el.textContent = text;
    msgs.appendChild(el);
    msgs.scrollTop = msgs.scrollHeight;
    return el;
  }

  function appendUserMessage(text) {
    var msgs = document.getElementById("sp-chat-messages");
    var el = document.createElement("div");
    el.className = "sp-msg sp-msg-user";
    el.textContent = text;
    msgs.appendChild(el);
    msgs.scrollTop = msgs.scrollHeight;
  }

  function showTyping() {
    var msgs = document.getElementById("sp-chat-messages");
    var el = document.createElement("div");
    el.className = "sp-msg-typing";
    el.id = "sp-typing";
    el.innerHTML = '<div class="sp-dot"></div><div class="sp-dot"></div><div class="sp-dot"></div>';
    msgs.appendChild(el);
    msgs.scrollTop = msgs.scrollHeight;
  }

  function hideTyping() {
    var el = document.getElementById("sp-typing");
    if (el) el.remove();
  }

  function autoResizeTextarea() {
    var ta = document.getElementById("sp-chat-input");
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 96) + "px";
  }

  function setLoading(v) {
    isLoading = v;
    document.getElementById("sp-chat-send").disabled = v;
  }

  // ── API call ───────────────────────────────────────────────────────────
  function sendMessage() {
    if (isLoading) return;
    var input = document.getElementById("sp-chat-input");
    var text = input.value.trim();
    if (!text) return;

    input.value = "";
    input.style.height = "auto";
    appendUserMessage(text);
    setLoading(true);
    showTyping();

    var body = { message: text };
    if (sessionId) body.session_id = sessionId;

    fetch(CHAT_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",   // send/receive sparechat_session cookie
      body: JSON.stringify(body),
    })
      .then(function (res) {
        if (!res.ok) throw new Error("HTTP " + res.status);
        return res.json();
      })
      .then(function (data) {
        hideTyping();
        sessionId = data.session_id || sessionId;
        appendBotMessage(data.response || STRINGS.error);
      })
      .catch(function () {
        hideTyping();
        appendBotMessage(STRINGS.error);
      })
      .finally(function () {
        setLoading(false);
      });
  }

  // ── Init ───────────────────────────────────────────────────────────────
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", buildWidget);
  } else {
    buildWidget();
  }
})();
