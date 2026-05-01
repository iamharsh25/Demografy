"""Chat FAB + popup widget assets.

Renders inside the body iframe (returned via `get_chatbox_assets`) so its
fixed-position CSS and JS stay isolated from native Streamlit DOM.

Owns:
  - FAB visibility (gated by `show` flag)
  - widget open/close + expand/split behavior (handled in iframe JS)
  - message thread render (driven by `messages` from session state)
  - "Thinking" pending state and disabled input on RBAC limit
  - Forwarding new user input to Python via window.postMessage
"""

from html import escape
from typing import Iterable, Optional


_CHAT_CSS = """
    @keyframes cwIn {
        0% { opacity: 0; transform: translateY(14px) scale(0.98); }
        100% { opacity: 1; transform: translateY(0) scale(1); }
    }
    @keyframes cwDot {
        0%, 80%, 100% { opacity: 0.25; transform: translateY(0); }
        40% { opacity: 1; transform: translateY(-2px); }
    }
    .chat-fab {
        position: fixed;
        right: 24px;
        bottom: 22px;
        width: 60px;
        height: 60px;
        border-radius: 999px;
        background: linear-gradient(135deg, #9a66ee, #5e17eb);
        color: #fff;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.45rem;
        cursor: pointer;
        box-shadow: 0 14px 30px rgba(94, 23, 235, 0.34), 0 4px 12px rgba(94, 23, 235, 0.24);
        z-index: 2200;
        transition: transform 0.15s ease, box-shadow 0.15s ease, opacity 0.15s ease;
    }
    .chat-fab.hidden {
        opacity: 0;
        pointer-events: none;
        transform: scale(0.92);
    }
    .chat-fab:hover {
        transform: translateY(-1px) scale(1.03);
        box-shadow: 0 18px 34px rgba(94, 23, 235, 0.4), 0 6px 16px rgba(94, 23, 235, 0.28);
    }
    .chat-widget {
        display: none;
        position: fixed;
        right: 16px;
        bottom: 16px;
        width: min(92vw, 560px);
        height: min(82vh, 700px);
        max-width: calc(100vw - 24px);
        background: #fff;
        border: 1px solid #dccbff;
        border-radius: 16px;
        overflow: hidden;
        box-shadow: 0 24px 48px rgba(94, 23, 235, 0.2), 0 6px 14px rgba(94, 23, 235, 0.12);
        z-index: 2195;
    }
    .chat-widget.open {
        display: flex;
        flex-direction: column;
        animation: cwIn 0.2s ease-out;
    }
    .chat-widget.split {
        right: 0;
        bottom: 0;
        width: 50vw;
        min-width: 360px;
        max-width: 920px;
        height: 100vh;
        border-radius: 0;
        border-right: none;
        box-shadow: -12px 0 32px rgba(94, 23, 235, 0.14);
    }
    .cw-header {
        height: 56px;
        padding: 0 14px;
        background: linear-gradient(135deg, #9a66ee 0%, #5e17eb 100%);
        color: #fff;
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-shrink: 0;
    }
    .cw-actions {
        display: inline-flex;
        gap: 6px;
        align-items: center;
    }
    .cw-title { display: inline-flex; align-items: center; gap: 8px; font-weight: 700; font-size: 1rem; }
    .cw-avatar {
        width: 26px; height: 26px; border-radius: 50%;
        background: rgba(255,255,255,0.22);
        display: inline-flex; align-items: center; justify-content: center;
        font-size: 0.92rem;
    }
    .cw-close, .cw-expand {
        border: none; background: transparent; color: #fff; font-size: 1rem; cursor: pointer;
        width: 28px; height: 28px; border-radius: 8px;
    }
    .cw-close:hover, .cw-expand:hover { background: rgba(255,255,255,0.15); }
    .cw-body {
        padding: 14px 14px 8px;
        flex: 1;
        overflow: auto;
        display: flex;
        flex-direction: column;
        gap: 10px;
    }
    .cw-bubble {
        background: #f3eeff;
        color: #5e17eb;
        border-radius: 10px;
        padding: 9px 11px;
        font-size: 0.9rem;
        font-weight: 600;
    }
    .cw-thread {
        display: flex;
        flex-direction: column;
        gap: 8px;
    }
    .cw-msg {
        padding: 9px 11px;
        border-radius: 12px;
        font-size: 0.92rem;
        line-height: 1.45;
        max-width: 88%;
        word-wrap: break-word;
        white-space: pre-wrap;
    }
    .cw-msg.user {
        align-self: flex-end;
        background: linear-gradient(135deg, #9a66ee, #5e17eb);
        color: #fff;
        border-bottom-right-radius: 4px;
    }
    .cw-msg.assistant {
        align-self: flex-start;
        background: #f3eeff;
        color: #272d2d;
        border-bottom-left-radius: 4px;
    }
    .cw-msg.thinking {
        align-self: flex-start;
        background: #ede2ff;
        color: #5e17eb;
        font-style: italic;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    .cw-msg.thinking .cw-dot {
        width: 6px; height: 6px; border-radius: 50%; background: currentColor;
        animation: cwDot 1.1s infinite ease-in-out;
    }
    .cw-msg.thinking .cw-dot:nth-child(2) { animation-delay: 0.15s; }
    .cw-msg.thinking .cw-dot:nth-child(3) { animation-delay: 0.3s; }
    .cw-input-wrap {
        border-top: 1px solid #eadfff;
        padding: 10px 12px;
        display: flex;
        gap: 8px;
        align-items: center;
        background: #fdfbff;
        flex-shrink: 0;
    }
    .cw-input {
        flex: 1;
        border: 1px solid #e3d2ff;
        background: #ffffff;
        border-radius: 8px;
        height: 38px;
        padding: 0 10px;
        font-size: 0.9rem;
        outline: none;
    }
    .cw-input:focus { border-color: #9a66ee; }
    .cw-input:disabled {
        background: #f5f1ff;
        color: #9087a8;
        cursor: not-allowed;
    }
    .cw-send {
        border: none;
        background: transparent;
        color: #a7b1bf;
        font-size: 1rem;
        cursor: pointer;
        width: 30px;
        height: 30px;
        border-radius: 8px;
    }
    .cw-send:hover { background: #f3f5f8; color: #5e17eb; }
    .cw-send:disabled { opacity: 0.4; cursor: not-allowed; }
    .cw-limit-note {
        padding: 8px 12px;
        background: #fff5f5;
        color: #b91c1c;
        font-size: 0.78rem;
        font-weight: 600;
        text-align: center;
        border-top: 1px solid #fecaca;
        flex-shrink: 0;
    }

    @media (max-width: 1200px) {
        .chat-widget.split {
            right: 16px;
            bottom: 16px;
            width: min(92vw, 560px);
            height: min(82vh, 700px);
            min-width: 0;
            max-width: calc(100vw - 24px);
            border-radius: 16px;
            border-right: 1px solid #dccbff;
            box-shadow: 0 24px 48px rgba(94, 23, 235, 0.2), 0 6px 14px rgba(94, 23, 235, 0.12);
        }
    }
"""


_WELCOME_BUBBLE_HTML = (
    '<div class="cw-bubble">Hi! I\'m HubBot. Ask me anything about Australian '
    "suburb data and I'll dig into the numbers for you.</div>"
)


def _render_messages_html(messages: Iterable[dict], pending: bool) -> str:
    items = list(messages or [])

    if not items and not pending:
        return _WELCOME_BUBBLE_HTML

    parts = ['<div class="cw-thread">']
    for msg in items:
        role = msg.get("role", "assistant")
        css_class = "user" if role == "user" else "assistant"
        content = escape(str(msg.get("content", "")))
        parts.append(f'<div class="cw-msg {css_class}">{content}</div>')

    if pending:
        parts.append(
            '<div class="cw-msg thinking">'
            '<span class="cw-dot"></span>'
            '<span class="cw-dot"></span>'
            '<span class="cw-dot"></span>'
            "Thinking..."
            "</div>"
        )

    parts.append("</div>")
    return "".join(parts)


def _render_input_html(pending: bool, limit_reached: bool) -> str:
    if limit_reached:
        return (
            '<div class="cw-limit-note">'
            "You\u2019ve reached your question limit for this session."
            "</div>"
        )

    disabled_attr = " disabled" if pending else ""
    placeholder = "Thinking..." if pending else "Ask about Australian suburb data..."
    return (
        '<div class="cw-input-wrap">'
        f'<input id="cw-input" class="cw-input" placeholder="{placeholder}" autocomplete="off"{disabled_attr} />'
        f'<button id="cw-send" class="cw-send" aria-label="Send"{disabled_attr}>\u279C</button>'
        "</div>"
    )


_CHAT_JS = """
    (function () {
        const fab = document.getElementById("chat-fab");
        const widget = document.getElementById("chat-widget");
        const page = document.querySelector(".page");
        const closeBtn = document.getElementById("cw-close");
        const expandBtn = document.getElementById("cw-expand");
        const sendBtn = document.getElementById("cw-send");
        const input = document.getElementById("cw-input");
        const body = document.querySelector(".cw-body");
        if (!fab || !widget) return;

        const wasOpen = widget.dataset.persistOpen === "true";
        if (wasOpen) {
            widget.classList.add("open");
            fab.classList.add("hidden");
            if (widget.dataset.persistSplit === "true") {
                widget.classList.add("split");
                if (page) page.classList.add("chat-split");
            }
        }

        if (body) body.scrollTop = body.scrollHeight;

        const openWidget = () => {
            widget.classList.add("open");
            widget.classList.remove("split");
            if (page) page.classList.remove("chat-split");
            fab.classList.add("hidden");
            widget.dataset.persistOpen = "true";
            widget.dataset.persistSplit = "false";
            if (input && !input.disabled) input.focus();
        };
        const closeWidget = () => {
            widget.classList.remove("open");
            widget.classList.remove("split");
            if (page) page.classList.remove("chat-split");
            fab.classList.remove("hidden");
            widget.dataset.persistOpen = "false";
            widget.dataset.persistSplit = "false";
        };

        fab.addEventListener("click", () => {
            if (widget.classList.contains("open")) {
                closeWidget();
            } else {
                openWidget();
            }
        });
        if (closeBtn) closeBtn.addEventListener("click", closeWidget);
        if (expandBtn) {
            expandBtn.addEventListener("click", () => {
                const splitOn = widget.classList.toggle("split");
                if (page) page.classList.toggle("chat-split", splitOn);
                widget.dataset.persistSplit = splitOn ? "true" : "false";
            });
        }

        function sendQuestion() {
            if (!input || input.disabled) return;
            const value = (input.value || "").trim();
            if (!value) return;
            input.value = "";
            const payload = {
                demografy_chat: "ask",
                question: value,
                ts: Date.now(),
            };
            // Broadcast to every sibling iframe of the main page so the
            // invisible bridge component reliably receives the payload.
            // Cross-origin postMessage is allowed; only DOM access isn't.
            try {
                const frames = window.parent.frames;
                for (let i = 0; i < frames.length; i++) {
                    try { frames[i].postMessage(payload, "*"); } catch (_) {}
                }
            } catch (_) {}
            // Belt-and-suspenders: also notify the parent window directly.
            window.parent.postMessage(payload, "*");
        }

        if (sendBtn) sendBtn.addEventListener("click", sendQuestion);
        if (input) {
            input.addEventListener("keydown", (event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    sendQuestion();
                }
            });
        }
    })();
"""


def _build_chat_html(
    messages: Iterable[dict],
    pending: bool,
    limit_reached: bool,
) -> str:
    message_list = list(messages or [])
    has_messages = bool(message_list)
    persist_open = "true" if (pending or has_messages) else "false"
    return (
        '<div id="chat-fab" class="chat-fab">\U0001F4AC</div>'
        f'<div id="chat-widget" class="chat-widget" data-persist-open="{persist_open}" data-persist-split="false">'
        '<div class="cw-header">'
        '<div class="cw-title"><span class="cw-avatar">\U0001F916</span>HubBot</div>'
        '<div class="cw-actions">'
        '<button id="cw-expand" class="cw-expand" aria-label="Expand chat">\u2922</button>'
        '<button id="cw-close" class="cw-close" aria-label="Close chat">\u2715</button>'
        "</div>"
        "</div>"
        f'<div class="cw-body">{_render_messages_html(message_list, pending)}</div>'
        f"{_render_input_html(pending, limit_reached)}"
        "</div>"
    )


def get_chatbox_assets(
    show: bool,
    messages: Optional[Iterable[dict]] = None,
    pending: bool = False,
    limit_reached: bool = False,
) -> dict:
    """Return css/html/script fragments to embed in the body iframe.

    The CSS and JS are always included (cheap, harmless) so the iframe
    structure is consistent. The HTML (FAB + widget DOM) is only injected
    when ``show`` is True, so anonymous users never see the FAB.
    """
    html = _build_chat_html(messages or [], pending, limit_reached) if show else ""
    return {
        "css": _CHAT_CSS,
        "html": html,
        "script": _CHAT_JS,
    }


def render_chatbox() -> None:
    """No-op: chatbox is rendered as part of the body iframe.

    Kept for orchestrator parity with the plan's `app_v4.py` shape so the
    main entrypoint can still call `render_chatbox()` if a future change
    moves the FAB out of the body iframe.
    """
    return None
