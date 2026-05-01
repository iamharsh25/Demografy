"""Chat FAB + popup widget assets.

Renders inside the body iframe (returned via `get_chatbox_assets`) so its
fixed-position CSS and JS stay isolated from native Streamlit DOM.

Owns:
  - FAB visibility (gated by `show` flag)
  - widget open/close behavior (handled in iframe JS)
"""


_CHAT_CSS = """
    @keyframes cwIn {
        0% { opacity: 0; transform: translateY(14px) scale(0.98); }
        100% { opacity: 1; transform: translateY(0) scale(1); }
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
        transition: transform 0.15s ease, box-shadow 0.15s ease;
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
    .cw-body { padding: 12px 14px 10px; }
    .chat-widget .cw-body { flex: 1; overflow: auto; }
    .cw-bubble {
        background: #f3eeff;
        color: #5e17eb;
        border-radius: 10px;
        padding: 9px 11px;
        font-size: 0.9rem;
        font-weight: 600;
        margin-bottom: 10px;
    }
    .cw-prompt {
        background: #ede2ff;
        color: #4f1ab8;
        border-radius: 10px;
        padding: 8px 11px;
        font-size: 0.92rem;
        font-weight: 700;
        margin-bottom: 10px;
    }
    .cw-quick {
        display: block;
        width: fit-content;
        min-width: 165px;
        margin-bottom: 8px;
        border: 1px solid #ceb4ff;
        background: #fff;
        color: #5e17eb;
        border-radius: 6px;
        padding: 8px 12px;
        font-size: 0.88rem;
        font-weight: 600;
        cursor: pointer;
        text-align: left;
    }
    .cw-quick:hover { border-color: #9a66ee; color: #4f1ab8; background: #f8f6ff; }
    .cw-input-wrap {
        border-top: 1px solid #eadfff;
        padding: 10px 12px;
        display: flex;
        gap: 8px;
        align-items: center;
        background: #fdfbff;
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


_CHAT_HTML = """
    <div id="chat-fab" class="chat-fab">💬</div>
    <div id="chat-widget" class="chat-widget">
        <div class="cw-header">
            <div class="cw-title"><span class="cw-avatar">🤖</span>HubBot</div>
            <div class="cw-actions">
                <button id="cw-expand" class="cw-expand" aria-label="Expand chat">⤢</button>
                <button id="cw-close" class="cw-close" aria-label="Close chat">✕</button>
            </div>
        </div>
        <div class="cw-body">
            <div class="cw-bubble">here to help you find your way.</div>
            <div class="cw-prompt">What would you like to do?</div>
            <button class="cw-quick">Learn about products</button>
            <button class="cw-quick">Learn about pricing</button>
            <button class="cw-quick">Get educational content</button>
        </div>
        <div class="cw-input-wrap">
            <input class="cw-input" placeholder="Choose an option" />
            <button class="cw-send">➤</button>
        </div>
    </div>
"""


_CHAT_JS = """
    (function () {
        const fab = document.getElementById("chat-fab");
        const widget = document.getElementById("chat-widget");
        const page = document.querySelector(".page");
        const closeBtn = document.getElementById("cw-close");
        const expandBtn = document.getElementById("cw-expand");
        if (!fab || !widget) return;

        const openWidget = () => {
            widget.classList.add("open");
            widget.classList.remove("split");
            if (page) page.classList.remove("chat-split");
            fab.classList.add("hidden");
        };
        const closeWidget = () => {
            widget.classList.remove("open");
            widget.classList.remove("split");
            if (page) page.classList.remove("chat-split");
            fab.classList.remove("hidden");
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
                widget.classList.toggle("split");
                if (page) page.classList.toggle("chat-split");
            });
        }
    })();
"""


def get_chatbox_assets(show: bool) -> dict:
    """Return the css/html/script fragments to embed in the body iframe.

    The CSS and JS are always included (cheap, harmless) so the iframe
    structure is consistent. The HTML (FAB + widget DOM) is only injected
    when `show` is True, so anonymous users never see the FAB.
    """
    return {
        "css": _CHAT_CSS,
        "html": _CHAT_HTML if show else "",
        "script": _CHAT_JS,
    }


def render_chatbox() -> None:
    """No-op: chatbox is rendered as part of the body iframe.

    Kept for orchestrator parity with the plan's `app_v4.py` shape so the
    main entrypoint can still call `render_chatbox()` if a future change
    moves the FAB out of the body iframe.
    """
    return None
