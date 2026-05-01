"""Hero + mockup body, rendered as an isolated iframe via components.html.

The chat FAB + popup widget is composed in alongside the body so it shares
the same iframe (its JS toggles the widget locally). The actual chat assets
live in `components/chatbox.py` to keep ownership clear.
"""

import streamlit.components.v1 as components

from components.chatbox import get_chatbox_assets


_BODY_CSS = """
    @import url("https://fonts.googleapis.com/css2?family=Open+Sauce+One:wght@400;500;600;700;800&display=swap");

    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }

    .page {
        min-height: 100vh;
        width: 100%;
        background: #ffffff;
        display: flex;
        flex-direction: column;
    }

    .canvas {
        flex: 1;
        width: 100%;
        background: linear-gradient(180deg, #f6f6fa 0%, #f3efff 100%);
        display: flex;
        justify-content: center;
        padding: 56px 40px 80px;
        box-sizing: border-box;
    }

    .hero {
        width: 100%;
        max-width: 1180px;
        display: grid;
        grid-template-columns: minmax(0, 1fr) minmax(0, 1.08fr);
        gap: 44px;
        align-items: center;
    }

    .hero-left { max-width: 540px; }

    .badge {
        display: inline-flex;
        align-items: center;
        padding: 5px 14px;
        border-radius: 999px;
        border: 1px solid #d8c9f7;
        background: #f2eafe;
        color: #9a66ee;
        font-family: "Open Sauce One", "Inter", "Segoe UI", sans-serif;
        font-size: 0.62rem;
        font-weight: 700;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        margin-bottom: 20px;
    }

    .hero-title {
        margin: 0;
        font-family: "Open Sauce One", "Inter", "Segoe UI", sans-serif;
        font-size: 3.9rem;
        line-height: 0.98;
        letter-spacing: -0.05em;
        color: #272d2d;
        font-weight: 700;
    }
    .hero-title .accent { color: #5e17eb; }

    .hero-desc {
        margin: 22px 0 0;
        font-family: "Open Sauce One", "Inter", "Segoe UI", sans-serif;
        font-size: 1.05rem;
        line-height: 1.75;
        color: #444a4a;
        max-width: 490px;
    }

    .hero-cta-row {
        margin-top: 30px;
        display: flex;
        gap: 12px;
        align-items: center;
    }

    .hero-btn {
        height: 44px;
        padding: 0 22px;
        border-radius: 10px;
        font-family: "Open Sauce One", "Inter", "Segoe UI", sans-serif;
        font-size: 0.84rem;
        font-weight: 600;
        text-decoration: none;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border: 1px solid transparent;
    }

    .hero-btn-secondary {
        background: #ffffff;
        color: #272d2d;
        border-color: #dbdddc;
    }

    .hero-btn-primary {
        color: #ffffff;
        background: linear-gradient(135deg, #9a66ee, #5e17eb);
        box-shadow: 0 8px 24px rgba(94, 23, 235, 0.28);
    }

    .hero-right {
        display: flex;
        justify-content: center;
    }

    .mockup-card {
        width: 100%;
        max-width: 650px;
        background: #ffffff;
        border: 1px solid #e8e8ec;
        border-radius: 18px;
        box-shadow: 0 20px 55px rgba(50, 41, 102, 0.14);
        overflow: hidden;
    }

    .mockup-head {
        height: 56px;
        display: flex;
        align-items: center;
        padding: 0 18px;
        border-bottom: 1px solid #f0f0f3;
        font-family: "Open Sauce One", "Inter", "Segoe UI", sans-serif;
        font-size: 2rem;
        font-weight: 800;
        color: #272d2d;
    }
    .mockup-head .accent { color: #9a66ee; }

    .mockup-content { padding: 14px 16px 18px; }

    .mockup-top {
        display: grid;
        grid-template-columns: 1.2fr 1fr 1fr;
        gap: 10px;
        margin-bottom: 12px;
    }

    .panel {
        border: 1px solid #ececf0;
        border-radius: 10px;
        padding: 10px;
        background: #fcfcfe;
    }

    .panel-title {
        font-family: "Open Sauce One", "Inter", "Segoe UI", sans-serif;
        font-size: 0.58rem;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: #9b9fa7;
        margin-bottom: 7px;
        font-weight: 700;
    }

    .panel-value {
        font-family: "Open Sauce One", "Inter", "Segoe UI", sans-serif;
        font-size: 2rem;
        color: #272d2d;
        font-weight: 700;
        line-height: 1.1;
    }

    .filters-label {
        font-family: "Open Sauce One", "Inter", "Segoe UI", sans-serif;
        font-size: 0.58rem;
        color: #9b9fa7;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        margin-bottom: 9px;
        font-weight: 700;
    }

    .fake-select {
        border: 1px solid #e6e6ea;
        background: #ffffff;
        border-radius: 8px;
        height: 30px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0 9px;
        box-sizing: border-box;
        font-family: "Open Sauce One", "Inter", "Segoe UI", sans-serif;
        font-size: 0.68rem;
        color: #3f4444;
        margin-bottom: 6px;
    }

    .table {
        border: 1px solid #ececf0;
        border-radius: 10px;
        overflow: hidden;
    }

    .table-head, .table-row {
        display: grid;
        grid-template-columns: 66px 1fr 100px;
        align-items: center;
        gap: 8px;
        padding: 9px 12px;
    }

    .table-head {
        background: #fafafe;
        border-bottom: 1px solid #eeeeF3;
        font-family: "Open Sauce One", "Inter", "Segoe UI", sans-serif;
        font-size: 0.62rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #9b9fa7;
        font-weight: 700;
    }

    .table-row { border-bottom: 1px solid #f3f3f6; }

    .rank-pill {
        width: 34px;
        height: 22px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: "Open Sauce One", "Inter", "Segoe UI", sans-serif;
        font-size: 0.62rem;
        font-weight: 700;
        color: #ffffff;
        background: #f6b70e;
    }

    .area-name {
        font-family: "Open Sauce One", "Inter", "Segoe UI", sans-serif;
        font-size: 0.76rem;
        color: #272d2d;
        font-weight: 600;
    }

    .area-sub {
        font-family: "Open Sauce One", "Inter", "Segoe UI", sans-serif;
        font-size: 0.62rem;
        color: #9b9fa7;
        margin-top: 2px;
    }

    .population {
        font-family: "Open Sauce One", "Inter", "Segoe UI", sans-serif;
        font-size: 0.74rem;
        font-weight: 600;
        color: #3f4444;
        text-align: right;
    }

    @media (max-width: 1100px) {
        .hero { grid-template-columns: 1fr; gap: 30px; }
        .hero-left { max-width: 100%; }
        .hero-title { font-size: 3rem; }
    }
    @media (max-width: 760px) {
        .canvas { padding: 28px 16px 40px; }
        .hero-title { font-size: 2.4rem; }
        .hero-desc { font-size: 0.95rem; }
        .hero-cta-row { flex-wrap: wrap; }
        .mockup-top { grid-template-columns: 1fr; }
    }
"""


_BODY_HTML = """
    <div class="page">
        <div class="canvas">
            <section class="hero">
                <div class="hero-left">
                    <div class="badge">Coming in Beta</div>
                    <h1 class="hero-title">
                        <span class="accent">Australian</span><br>
                        <span class="accent">property insights,</span><br>
                        propelled by data.
                    </h1>
                    <p class="hero-desc">
                        Ditch the guesswork. Our platform gives investors, homebuyers,
                        and pros the hard numbers on suburb growth, so you can make
                        your move with confidence, not just a hunch.
                    </p>
                    <div class="hero-cta-row">
                        <a class="hero-btn hero-btn-secondary" href="#">Discover more</a>
                        <a class="hero-btn hero-btn-primary" href="#">Get early access -></a>
                    </div>
                </div>

                <div class="hero-right">
                    <div class="mockup-card">
                        <div class="mockup-head"><span class="accent">D</span>emografy</div>
                        <div class="mockup-content">
                            <div class="mockup-top">
                                <div class="panel">
                                    <div class="filters-label">Filters</div>
                                    <div class="fake-select"><span>State</span><span>NSW</span></div>
                                    <div class="fake-select"><span>Local Govt Area</span><span>All LGAs</span></div>
                                    <div class="fake-select"><span>Region Type</span><span>All regions</span></div>
                                </div>
                                <div class="panel">
                                    <div class="panel-title">Total Areas</div>
                                    <div class="panel-value">644</div>
                                </div>
                                <div class="panel">
                                    <div class="panel-title">Active KPIs</div>
                                    <div class="panel-value">3</div>
                                </div>
                            </div>

                            <div class="table">
                                <div class="table-head">
                                    <div>Rank</div>
                                    <div>SA2</div>
                                    <div style="text-align:right;">Population</div>
                                </div>
                                <div class="table-row">
                                    <div><div class="rank-pill">#1</div></div>
                                    <div>
                                        <div class="area-name">Corowa</div>
                                        <div class="area-sub">NSW · Major Cities</div>
                                    </div>
                                    <div class="population">7,005</div>
                                </div>
                                <div class="table-row">
                                    <div><div class="rank-pill">#2</div></div>
                                    <div>
                                        <div class="area-name">Rosemeadow - Glen Alpine</div>
                                        <div class="area-sub">NSW · Major Cities</div>
                                    </div>
                                    <div class="population">25,636</div>
                                </div>
                                <div class="table-row">
                                    <div><div class="rank-pill">#3</div></div>
                                    <div>
                                        <div class="area-name">Leppington - Catherine Field</div>
                                        <div class="area-sub">NSW · Major Cities</div>
                                    </div>
                                    <div class="population">3,231</div>
                                </div>
                                <div class="table-row">
                                    <div><div class="rank-pill">#4</div></div>
                                    <div>
                                        <div class="area-name">Randwick - North</div>
                                        <div class="area-sub">NSW · Major Cities</div>
                                    </div>
                                    <div class="population">63,875</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </section>
        </div>
    </div>
"""


def render_body(show_chat_widget: bool) -> None:
    chat = get_chatbox_assets(show_chat_widget)

    page_html = f"""
        <style>
{_BODY_CSS}
{chat["css"]}
        </style>

{_BODY_HTML}
{chat["html"]}
        <script>
{chat["script"]}
        </script>
    """

    components.html(
        page_html,
        height=860,
        scrolling=False,
    )
