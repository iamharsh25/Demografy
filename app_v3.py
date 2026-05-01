"""
Demografy — app_v3.py
Full Streamlit reimplementation matching demografy.com.au UI.
Run via: streamlit run app.py  (app.py delegates here)
"""

import os
import uuid
import streamlit as st
from dotenv import load_dotenv
from datetime import date, timedelta

load_dotenv()

# ── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Demografy",
    page_icon="🏘️",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ══════════════════════════════════════════════════════════════════════════════
# CSS — Design system matching demografy.com.au
# ══════════════════════════════════════════════════════════════════════════════
def load_css():
    st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

    html, body, .stApp, [class*="css"] {
        font-family: 'Inter', sans-serif !important;
    }

    #MainMenu { visibility: hidden; }
    footer     { visibility: hidden; }
    header     { visibility: hidden; }

    /* ═══ LAYOUT — centered, 1280px max, 48px side padding ═══ */
    .block-container {
        padding-top: 0 !important;
        padding-bottom: 0 !important;
        padding-left: 48px !important;
        padding-right: 48px !important;
        max-width: 1280px !important;
        margin-left: auto !important;
        margin-right: auto !important;
    }

    section[data-testid="stMain"] {
        background: #ffffff !important;
    }
    section[data-testid="stMain"] > div:first-child {
        background: transparent !important;
    }

    /* Centered content wrapper used inside HTML sections */
    .cw {
        max-width: 1200px;
        margin: 0 auto;
        padding: 0 32px;
    }

    /* ═══ NAVBAR ═══ */
    div[data-testid="stHorizontalBlock"]:first-of-type {
        position: sticky !important;
        top: 0 !important;
        z-index: 200 !important;
        background: rgba(255,255,255,0.96) !important;
        border-bottom: 1px solid #f3f4f6 !important;
        backdrop-filter: blur(8px) !important;
        -webkit-backdrop-filter: blur(8px) !important;
        padding: 0 48px !important;
        gap: 0 !important;
        align-items: center !important;
        min-height: 64px !important;
        /* span full viewport width despite block-container padding */
        margin-left: -48px !important;
        margin-right: -48px !important;
        width: calc(100% + 96px) !important;
    }

    .nav-logo {
        font-size: 1.25rem;
        font-weight: 800;
        color: #1f2937;
        letter-spacing: -0.5px;
        white-space: nowrap;
        line-height: 64px;
    }
    .nav-logo .acc { color: #8b5cf6; }

    .nav-links-bar {
        display: flex;
        gap: 32px;
        align-items: center;
        justify-content: center;
        height: 64px;
    }
    .nav-links-bar a {
        font-size: 0.875rem;
        font-weight: 500;
        color: #6b7280;
        text-decoration: none;
        white-space: nowrap;
        cursor: default;
        transition: color 0.15s;
    }
    .nav-links-bar a:hover { color: #1f2937; }

    /* Navbar logged-out: Login + Signup buttons */
    [data-testid="stVerticalBlock"]:has(.nav-login-area) {
        display: flex !important;
        flex-direction: row !important;
        align-items: center !important;
        justify-content: flex-end !important;
        gap: 8px !important;
        height: 64px !important;
    }
    [data-testid="stVerticalBlock"]:has(.nav-login-area) [data-testid="stButton"] button[kind="secondary"] {
        background: transparent !important;
        color: #374151 !important;
        border: 1.5px solid #e5e7eb !important;
        border-radius: 999px !important;
        font-size: 0.875rem !important;
        font-weight: 500 !important;
        height: 38px !important;
        padding: 0 20px !important;
        white-space: nowrap !important;
        transition: all 0.15s !important;
    }
    [data-testid="stVerticalBlock"]:has(.nav-login-area) [data-testid="stButton"] button[kind="secondary"]:hover {
        background: #f9fafb !important;
        border-color: #d1d5db !important;
    }
    [data-testid="stVerticalBlock"]:has(.nav-login-area) [data-testid="stButton"] button[kind="primary"] {
        background: #5e17eb !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-size: 0.875rem !important;
        font-weight: 600 !important;
        height: 38px !important;
        padding: 0 20px !important;
        white-space: nowrap !important;
        transition: opacity 0.15s !important;
    }
    [data-testid="stVerticalBlock"]:has(.nav-login-area) [data-testid="stButton"] button[kind="primary"]:hover {
        opacity: 0.88 !important;
    }

    /* Navbar logged-in: Hi, [Name] pill */
    [data-testid="stVerticalBlock"]:has(.nav-hi-area) {
        display: flex !important;
        flex-direction: column !important;
        align-items: flex-end !important;
        justify-content: center !important;
        height: 64px !important;
    }
    [data-testid="stVerticalBlock"]:has(.nav-hi-area) [data-testid="stButton"] > button {
        background: transparent !important;
        color: #374151 !important;
        border: 1.5px solid #e5e7eb !important;
        border-radius: 999px !important;
        font-size: 0.875rem !important;
        font-weight: 500 !important;
        height: 38px !important;
        padding: 0 18px !important;
        white-space: nowrap !important;
        width: auto !important;
        min-width: unset !important;
    }
    [data-testid="stVerticalBlock"]:has(.nav-hi-area) [data-testid="stButton"] > button:hover {
        background: #f9fafb !important;
    }

    /* User dropdown items */
    [data-testid="stMarkdownContainer"]:has(.user-dropdown) ~ [data-testid="stButton"] > button {
        background: #fafafa !important;
        color: #374151 !important;
        border: 1px solid #f3f4f6 !important;
        border-radius: 8px !important;
        font-size: 0.875rem !important;
        font-weight: 500 !important;
        text-align: left !important;
        justify-content: flex-start !important;
        padding: 8px 14px !important;
        width: 100% !important;
        margin-top: 4px !important;
    }
    [data-testid="stMarkdownContainer"]:has(.user-dropdown) ~ [data-testid="stButton"] > button:hover {
        background: #f3f4f6 !important;
        color: #1f2937 !important;
    }

    /* ═══ PAGE BACKGROUND (landing only) ═══ */
    section[data-testid="stMain"] {
        background: linear-gradient(135deg, #ffffff 0%, #f5f0ff 55%, #ede8ff 100%) !important;
        min-height: 100vh;
    }
    section[data-testid="stMain"] > div:first-child {
        background: transparent !important;
    }

    /* ═══ HERO ═══ */
    .hero-wrap {
        padding: 80px 0 60px;
        min-height: calc(100vh - 64px);
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .hero-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: transparent;
        color: #5e17eb;
        border: 1.5px solid #c9a5ff;
        border-radius: 999px;
        padding: 4px 14px;
        font-size: 0.68rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin-bottom: 22px;
        background: rgba(94,23,235,0.04);
    }
    .hero-h1 {
        font-size: 3.2rem;
        font-weight: 700;
        color: #1a1a2e;
        line-height: 1.15;
        letter-spacing: -1px;
        margin: 0 0 0;
    }
    .hero-h2 {
        font-size: 3.2rem;
        font-weight: 800;
        color: #5e17eb;
        line-height: 1.15;
        letter-spacing: -1px;
        margin: 0 0 22px;
    }
    .hero-sub {
        font-size: 0.95rem;
        color: #555;
        line-height: 1.75;
        max-width: 480px;
        margin-bottom: 36px;
        font-weight: 400;
    }

    /* Hero CTA primary */
    [data-testid="stVerticalBlock"]:has(.hero-cta-primary) [data-testid="stButton"] > button {
        background: linear-gradient(135deg, #5e17eb, #9a66ee) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        font-size: 0.88rem !important;
        font-weight: 600 !important;
        height: 46px !important;
        padding: 0 24px !important;
        white-space: nowrap !important;
        transition: opacity 0.15s !important;
    }
    [data-testid="stVerticalBlock"]:has(.hero-cta-primary) [data-testid="stButton"] > button:hover {
        opacity: 0.9 !important;
    }
    /* Hero CTA secondary */
    [data-testid="stVerticalBlock"]:has(.hero-cta-secondary) [data-testid="stButton"] > button {
        background: white !important;
        color: #1a1a2e !important;
        border: 1.5px solid #ddd !important;
        border-radius: 10px !important;
        font-size: 0.88rem !important;
        font-weight: 600 !important;
        height: 46px !important;
        padding: 0 24px !important;
        white-space: nowrap !important;
    }
    [data-testid="stVerticalBlock"]:has(.hero-cta-secondary) [data-testid="stButton"] > button:hover {
        border-color: #9a66ee !important;
        color: #5e17eb !important;
    }

    /* ═══ PRODUCT MOCKUP ═══ */
    .mockup-outer {
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 40px 0;
        min-height: calc(100vh - 64px);
    }
    .mockup-card {
        background: white;
        border-radius: 20px;
        box-shadow: 0 20px 60px rgba(21,12,81,0.13), 0 4px 16px rgba(0,0,0,0.05);
        padding: 24px 22px;
        font-family: 'Inter', sans-serif;
        font-size: 0.73rem;
        width: 100%;
        max-width: 430px;
        border: 1px solid #e5e7eb;
        overflow: hidden;
    }
    .mk-header { font-weight: 900; font-size: 1rem; color: #1f2937; margin-bottom: 14px; letter-spacing: -0.3px; }
    .mk-header .acc { color: #8b5cf6; }
    .mk-filters { display: flex; gap: 8px; margin-bottom: 14px; flex-wrap: wrap; align-items: center; }
    .mk-fl { color: #9ca3af; font-size: 0.62rem; text-transform: uppercase; letter-spacing: 0.5px; }
    .mk-fp { background: #ede9fe; color: #8b5cf6; border: 1px solid #ddd6fe; border-radius: 6px; padding: 3px 10px; font-size: 0.68rem; font-weight: 600; }
    .mk-stats { display: flex; gap: 20px; margin-bottom: 14px; padding-bottom: 12px; border-bottom: 1px solid #f3f4f6; }
    .mk-sl { color: #9ca3af; font-size: 0.58rem; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 2px; }
    .mk-sv { font-size: 1.5rem; font-weight: 800; color: #1f2937; }
    .mk-th { display: grid; grid-template-columns: 30px 1fr 76px; gap: 6px; color: #9ca3af; font-size: 0.6rem; text-transform: uppercase; letter-spacing: 0.6px; padding: 4px 0; border-bottom: 1px solid #f3f4f6; margin-bottom: 6px; }
    .mk-row { display: grid; grid-template-columns: 30px 1fr 76px; gap: 6px; align-items: center; padding: 6px 0; border-bottom: 1px solid #fafafa; }
    .mk-rank { width: 22px; height: 22px; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 0.62rem; color: white; }
    .r1 { background: #8b5cf6; } .r2 { background: #a78bfa; } .r3 { background: #60a5fa; }
    .rn { background: #e5e7eb; color: #6b7280; }
    .mk-name { font-weight: 600; color: #1f2937; font-size: 0.72rem; }
    .mk-loc  { color: #9ca3af; font-size: 0.6rem; }
    .mk-pop  { font-weight: 600; color: #374151; font-size: 0.72rem; text-align: right; }

    /* ═══ SECTION SHARED ═══ */
    .sec-badge {
        display: inline-flex; align-items: center; gap: 6px;
        background: #ede9fe; color: #8b5cf6; border-radius: 4px;
        padding: 4px 12px; font-size: 0.7rem; font-weight: 700;
        letter-spacing: 0.18em; text-transform: uppercase; margin-bottom: 18px;
    }
    .sec-badge .dot { width: 6px; height: 6px; background: #8b5cf6; border-radius: 50%; display: inline-block; }
    .sec-h2 { font-size: 2.6rem; font-weight: 700; color: #1f2937; letter-spacing: -0.5px; line-height: 1.2; margin: 0 0 16px; }
    .sec-sub { font-size: 1rem; color: #6b7280; line-height: 1.7; max-width: 560px; margin: 0 0 52px; }
    .sec-sub-center { max-width: 700px; margin: 0 auto 52px; text-align: center; }

    /* ═══ FEATURES SECTION ═══ */
    .section-feat { background: #f9fafb; padding: 96px 32px; }
    .feat-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 16px;
    }
    .feat-card {
        background: #f9fafb;
        border: 1px solid #e5e7eb;
        border-radius: 26px;
        padding: 26px 22px;
        transition: box-shadow 0.2s, transform 0.2s;
    }
    .feat-card:hover { box-shadow: 0 8px 32px rgba(139,92,246,0.1); transform: translateY(-2px); }
    .feat-icon {
        width: 48px; height: 48px; background: white; border-radius: 12px;
        display: flex; align-items: center; justify-content: center;
        font-size: 1.4rem; margin-bottom: 16px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.07);
    }
    .feat-title { font-size: 1rem; font-weight: 600; color: #1f2937; margin-bottom: 8px; }
    .feat-desc  { font-size: 0.875rem; color: #4b5563; line-height: 1.65; font-weight: 400; }

    /* ═══ FEATURES DETAILED ═══ */
    .section-fd { background: white; padding: 96px 32px; }
    .fd-pair {
        max-width: 1200px; margin: 0 auto;
        display: grid; grid-template-columns: 1fr 1fr;
        gap: 72px; align-items: center;
        padding: 40px 0;
    }
    .fd-pair + .fd-pair { border-top: 1px solid #f3f4f6; }
    .fd-pair.rev { direction: rtl; }
    .fd-pair.rev > * { direction: ltr; }
    .fd-badge { display: inline-flex; align-items: center; gap: 6px; background: #ede9fe; color: #8b5cf6; border-radius: 4px; padding: 3px 10px; font-size: 0.68rem; font-weight: 700; letter-spacing: 0.15em; text-transform: uppercase; margin-bottom: 14px; }
    .fd-h3 { font-size: 2rem; font-weight: 700; color: #1f2937; letter-spacing: -0.5px; line-height: 1.25; margin: 0 0 16px; }
    .fd-h3 .acc { color: #8b5cf6; }
    .fd-p { font-size: 0.95rem; color: #6b7280; line-height: 1.75; margin-bottom: 24px; }
    .fd-link { color: #8b5cf6; font-weight: 600; font-size: 0.9rem; text-decoration: none; }
    .fd-link:hover { text-decoration: underline; }
    .fd-visual {
        background: white; border: 1px solid #e5e7eb; border-radius: 20px;
        padding: 24px 20px; box-shadow: 0 12px 40px rgba(21,12,81,0.09);
        font-size: 0.75rem; font-family: 'Inter', sans-serif;
    }
    .fd-vis-head { font-weight: 700; font-size: 0.85rem; color: #1f2937; margin-bottom: 14px; display: flex; justify-content: space-between; align-items: center; }
    .fd-vis-tag { background: #ede9fe; color: #8b5cf6; border-radius: 4px; padding: 2px 8px; font-size: 0.65rem; font-weight: 600; }
    .fd-bar-row { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
    .fd-bar-label { width: 100px; font-size: 0.7rem; color: #6b7280; text-align: right; flex-shrink: 0; }
    .fd-bar-track { flex: 1; height: 8px; background: #f3f4f6; border-radius: 999px; overflow: hidden; }
    .fd-bar-fill { height: 100%; border-radius: 999px; background: linear-gradient(90deg, #8b5cf6, #a78bfa); }
    .fd-bar-val { font-size: 0.7rem; font-weight: 600; color: #1f2937; width: 36px; text-align: right; flex-shrink: 0; }
    .fd-compare-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 12px; }
    .fd-compare-card { background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 12px; padding: 12px; }
    .fd-cc-name { font-weight: 700; font-size: 0.78rem; color: #1f2937; margin-bottom: 8px; }
    .fd-cc-kpi { display: flex; justify-content: space-between; font-size: 0.68rem; color: #6b7280; margin-bottom: 4px; }
    .fd-cc-kpi span { font-weight: 600; color: #1f2937; }
    .fd-heatmap { display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; }
    .fd-hm-cell { height: 28px; border-radius: 4px; }

    /* ═══ USE CASES ═══ */
    .section-uc { background: white; padding: 96px 32px; border-top: 1px solid #f3f4f6; }
    .uc-layout { max-width: 1200px; margin: 0 auto; display: grid; grid-template-columns: minmax(0,1fr) minmax(0,1.1fr); gap: 64px; }
    .uc-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
    .uc-card {
        background: white; border: 1px solid #e5e7eb; border-radius: 26px;
        padding: 20px 18px; transition: box-shadow 0.2s;
    }
    .uc-card:hover { box-shadow: 0 4px 20px rgba(139,92,246,0.12); }
    .uc-icon { font-size: 1.5rem; margin-bottom: 10px; }
    .uc-title { font-size: 0.88rem; font-weight: 700; color: #1f2937; margin-bottom: 4px; }
    .uc-sub   { font-size: 0.78rem; color: #8b5cf6; font-weight: 500; }

    /* ═══ TESTIMONIALS ═══ */
    .section-testi { background: #F3F4F6; padding: 96px 32px; }
    .testi-grid { max-width: 1200px; margin: 0 auto; display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; }
    .testi-card {
        background: white; border-radius: 26px; padding: 32px 28px;
        box-shadow: 0 4px 24px rgba(0,0,0,0.06); border: 1px solid #e5e7eb;
    }
    .testi-stars { color: #8b5cf6; font-size: 1rem; letter-spacing: 2px; margin-bottom: 16px; }
    .testi-quote { font-size: 0.95rem; color: #374151; line-height: 1.75; font-style: italic; margin-bottom: 24px; }
    .testi-author { display: flex; align-items: center; gap: 12px; }
    .testi-av { width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1.1rem; flex-shrink: 0; }
    .av-1 { background: #ede9fe; } .av-2 { background: #dbeafe; } .av-3 { background: #d1fae5; }
    .testi-name { font-size: 0.88rem; font-weight: 700; color: #1f2937; }
    .testi-role { font-size: 0.78rem; color: #8b5cf6; font-weight: 500; }

    /* ═══ PRICING CTA ═══ */
    .section-cta { background: white; padding: 96px 32px; text-align: center; border-top: 1px solid #f3f4f6; }
    .cta-glow {
        display: inline-block;
        background: linear-gradient(135deg, rgba(139,92,246,0.08) 0%, rgba(167,139,250,0.04) 100%);
        border: 1px solid #e9d5ff;
        border-radius: 32px;
        padding: 64px 80px;
        max-width: 680px;
        width: 100%;
    }
    .cta-h2 { font-size: 2.6rem; font-weight: 800; color: #1f2937; letter-spacing: -1px; margin-bottom: 14px; line-height: 1.15; }
    .cta-sub { font-size: 1rem; color: #6b7280; line-height: 1.7; margin-bottom: 0; }

    /* Pricing CTA button via :has() */
    [data-testid="stHorizontalBlock"]:has(.pricing-cta-area) {
        background: white !important;
        padding: 28px 0 0 !important;
        display: flex !important;
        justify-content: center !important;
    }
    [data-testid="stVerticalBlock"]:has(.pricing-cta-area) [data-testid="stButton"] > button {
        background: #8b5cf6 !important;
        color: white !important;
        border: none !important;
        border-radius: 999px !important;
        font-size: 1rem !important;
        font-weight: 600 !important;
        height: 54px !important;
        padding: 0 40px !important;
        white-space: nowrap !important;
        transition: background 0.15s !important;
    }
    [data-testid="stVerticalBlock"]:has(.pricing-cta-area) [data-testid="stButton"] > button:hover {
        background: #7c3aed !important;
    }

    /* ═══ FOOTER ═══ */
    .footer-wrap { background: #111827; padding: 64px 32px 40px; color: #9ca3af; }
    .footer-inner { max-width: 1200px; margin: 0 auto; }
    .footer-top { display: grid; grid-template-columns: 1.5fr repeat(4,1fr); gap: 48px; margin-bottom: 48px; }
    .footer-logo { font-size: 1.2rem; font-weight: 800; color: white; letter-spacing: -0.5px; margin-bottom: 8px; }
    .footer-logo .acc { color: #8b5cf6; }
    .footer-tagline { font-size: 0.85rem; color: #6b7280; line-height: 1.6; max-width: 220px; }
    .footer-col-title { font-size: 0.75rem; font-weight: 700; color: #f3f4f6; text-transform: uppercase; letter-spacing: 0.12em; margin-bottom: 16px; }
    .footer-col a { display: block; font-size: 0.875rem; color: #6b7280; text-decoration: none; margin-bottom: 10px; cursor: default; transition: color 0.15s; }
    .footer-col a:hover { color: #9ca3af; }
    .footer-bottom { border-top: 1px solid #1f2937; padding-top: 24px; font-size: 0.8rem; color: #4b5563; display: flex; justify-content: space-between; align-items: center; }

    /* ═══ CHAT FAB ═══ */
    [data-testid="stMarkdownContainer"]:has(.chat-fab-anchor) ~ [data-testid="stButton"] > button {
        position: fixed !important;
        bottom: 28px !important;
        right: 28px !important;
        width: 64px !important;
        height: 64px !important;
        border-radius: 50% !important;
        background: linear-gradient(135deg, #8b5cf6, #7c3aed) !important;
        color: white !important;
        font-size: 1.6rem !important;
        border: none !important;
        padding: 0 !important;
        z-index: 9999 !important;
        box-shadow: 0 8px 32px rgba(139,92,246,0.5) !important;
        transition: transform 0.18s, box-shadow 0.18s !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    [data-testid="stMarkdownContainer"]:has(.chat-fab-anchor) ~ [data-testid="stButton"] > button:hover {
        transform: scale(1.1) !important;
        box-shadow: 0 12px 40px rgba(139,92,246,0.65) !important;
    }
    [data-testid="stMarkdownContainer"]:has(.chat-fab-anchor) ~ [data-testid="stButton"] > button p {
        font-size: 1.6rem !important;
        margin: 0 !important;
        line-height: 1 !important;
    }

    /* ═══ CHAT SCREEN ═══ */
    .back-btn button {
        background: transparent !important;
        color: #8b5cf6 !important;
        border: none !important;
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        padding: 4px 8px !important;
    }
    .back-btn button:hover { text-decoration: underline !important; }

    /* Sidebar gradient — scoped by .chat-layout-marker */
    [data-testid="stVerticalBlock"]:has(.chat-layout-marker)
      [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"]:nth-child(2):last-child)
      > [data-testid="stColumn"]:first-child {
        background: linear-gradient(160deg, #8b5cf6 0%, #7c3aed 100%);
        border-radius: 16px;
    }
    [data-testid="stVerticalBlock"]:has(.chat-layout-marker)
      [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"]:nth-child(2):last-child)
      > [data-testid="stColumn"]:first-child
      > [data-testid="stVerticalBlockBorderWrapper"] > div > [data-testid="stVerticalBlock"] {
        padding: 20px 14px;
        min-height: 88vh;
        display: flex;
        flex-direction: column;
    }
    [data-testid="stVerticalBlock"]:has(.chat-layout-marker)
      [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"]:nth-child(2):last-child)
      > [data-testid="stColumn"]:first-child button {
        background: transparent !important;
        color: rgba(255,255,255,0.85) !important;
        border: none !important;
        border-radius: 10px !important;
        font-size: 0.88rem !important;
        font-weight: 500 !important;
        padding: 10px 14px !important;
        width: 100% !important;
        text-align: left !important;
        justify-content: flex-start !important;
        transition: background 0.15s, color 0.15s !important;
    }
    [data-testid="stVerticalBlock"]:has(.chat-layout-marker)
      [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"]:nth-child(2):last-child)
      > [data-testid="stColumn"]:first-child button:hover {
        background: rgba(255,255,255,0.15) !important;
        color: white !important;
    }

    .sb-logo { color: white; font-size: 1.2rem; font-weight: 900; letter-spacing: -0.5px; padding: 4px 14px 20px; }
    .sb-logo .acc { font-weight: 400; opacity: 0.85; }
    .sb-divider { border: none; border-top: 1px solid rgba(255,255,255,0.18); margin: 8px 0; width: 100%; }
    .sb-user { color: rgba(255,255,255,0.9); font-size: 0.8rem; padding: 10px 14px 4px; }
    .sb-user-name { font-weight: 700; font-size: 0.88rem; color: white; }
    .sb-user-tier { opacity: 0.7; font-size: 0.75rem; }

    .empty-wrap { display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 65vh; text-align: center; padding: 20px; }
    .empty-heading { font-size: 2.2rem; font-weight: 700; color: #1f2937; margin-bottom: 0; line-height: 1.3; }

    .chip-wrap button {
        background: white !important; color: #374151 !important;
        border: 1px solid #e5e7eb !important; border-radius: 999px !important;
        font-size: 0.82rem !important; font-weight: 500 !important; padding: 10px 18px !important;
    }
    .chip-wrap button:hover { background: #ede9fe !important; border-color: #c4b5fd !important; color: #8b5cf6 !important; }

    .counter-fixed {
        position: fixed; bottom: 72px; right: 24px; z-index: 999;
        background: rgba(255,255,255,0.92); border: 1px solid #e5e7eb;
        border-radius: 20px; padding: 4px 14px; font-size: 0.72rem; font-weight: 600;
        backdrop-filter: blur(8px); box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    .c-green  { color: #8b5cf6; }
    .c-yellow { color: #d97706; }
    .c-red    { color: #dc2626; }

    .badge-pro   { background: linear-gradient(90deg,#f7971e,#ffd200); color:#333; padding:2px 9px; border-radius:10px; font-size:0.68rem; font-weight:700; }
    .badge-basic { background: linear-gradient(90deg,#8b5cf6,#7c3aed); color:white; padding:2px 9px; border-radius:10px; font-size:0.68rem; font-weight:700; }
    .badge-free  { background:#f3f4f6; color:#6b7280; padding:2px 9px; border-radius:10px; font-size:0.68rem; font-weight:700; }

    /* ═══ RESPONSIVE ═══ */
    @media (max-width: 1024px) {
        .hero-inner { grid-template-columns: 1fr; gap: 40px; }
        .fd-pair     { grid-template-columns: 1fr; gap: 32px; }
        .fd-pair.rev { direction: ltr; }
        .uc-layout   { grid-template-columns: 1fr; }
        .footer-top  { grid-template-columns: 1fr 1fr; }
        .hero-h1, .hero-h2 { font-size: 2.8rem; }
        .testi-grid  { grid-template-columns: 1fr; gap: 16px; }
    }
    @media (max-width: 767px) {
        .hero-wrap   { padding: 48px 0; min-height: unset; }
        .hero-h1, .hero-h2 { font-size: 2.1rem; letter-spacing: -1px; }
        .hero-sub    { font-size: 0.9rem; }
        .section-feat, .section-fd, .section-uc, .section-testi, .section-cta { padding: 60px 16px; }
        .feat-grid   { grid-template-columns: 1fr; }
        .uc-grid     { grid-template-columns: repeat(2, 1fr); }
        .sec-h2      { font-size: 1.9rem; }
        .cta-h2      { font-size: 1.9rem; }
        .cta-glow    { padding: 40px 24px; }
        .footer-top  { grid-template-columns: 1fr 1fr; }
        .nav-links-bar { display: none; }
        div[data-testid="stHorizontalBlock"]:first-of-type {
            padding: 0 16px !important;
            margin-left: -16px !important;
            margin-right: -16px !important;
            width: calc(100% + 32px) !important;
        }
        .block-container { padding-left: 16px !important; padding-right: 16px !important; }
    }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def _save_current(user_id: str):
    from utils.chat_history import save_session
    msgs = st.session_state.get("messages", [])
    if msgs:
        title = msgs[0]["content"][:60]
        save_session(user_id, st.session_state.session_id, title, msgs)


# ══════════════════════════════════════════════════════════════════════════════
# MODALS
# ══════════════════════════════════════════════════════════════════════════════
@st.dialog("Sign In")
def show_login_modal():
    st.markdown("""
    <div style="text-align:center; margin-bottom:20px;">
        <div style="font-size:1.8rem; font-weight:900; letter-spacing:-1px; color:#1f2937;">
            <span style="color:#8b5cf6;">D</span>emografy
        </div>
        <div style="color:#9ca3af; font-size:0.85rem; margin-top:6px;">
            Enter your User ID to continue
        </div>
    </div>
    """, unsafe_allow_html=True)

    user_id_input = st.text_input("User ID", placeholder="e.g. user_001", label_visibility="collapsed")
    login_clicked = st.button("Sign In", use_container_width=True, type="primary")

    if login_clicked:
        if not user_id_input.strip():
            st.error("Please enter a User ID.")
        else:
            with st.spinner("Checking credentials..."):
                try:
                    from auth.rbac import get_user
                    user = get_user(user_id_input.strip())
                    if user is None:
                        st.error("User not found or account is inactive.")
                    else:
                        new_sid = str(uuid.uuid4())
                        st.session_state.user           = user
                        st.session_state.question_count = 0
                        st.session_state.messages       = []
                        st.session_state.session_id     = new_sid
                        st.session_state.chat_open      = False
                        st.session_state.show_user_menu = False
                        st.query_params["u"] = user["user_id"]
                        st.query_params["s"] = new_sid
                        st.rerun()
                except Exception as e:
                    st.error(f"Could not connect. Error: {str(e)}")


@st.dialog("My Account")
def show_user_modal(user: dict, question_count: int, limit: int, tier: str):
    remaining = limit - question_count
    pct = min(question_count / max(limit, 1), 1.0)
    tier_emoji = {"pro": "🥇", "basic": "🥈", "free": "🥉"}.get(tier, "")

    st.markdown(
        f"**{user['user_id']}** &nbsp; <span class='badge-{tier}'>{tier.upper()} {tier_emoji}</span>",
        unsafe_allow_html=True,
    )
    st.caption(user.get("email", ""))
    st.divider()

    c1, c2 = st.columns(2)
    c1.metric("Questions Used", question_count)
    c2.metric("Remaining", remaining)
    st.progress(pct, text=f"{question_count} / {limit} questions this session")

    if remaining <= 0:
        st.error("Question limit reached for this session.")
    elif remaining <= 5:
        st.warning(f"⚠️ Only {remaining} question{'s' if remaining != 1 else ''} left.")
    else:
        st.success(f"✅ {remaining} questions remaining.")

    st.divider()
    if st.button("🚪  Sign Out", type="primary", use_container_width=True):
        for key in ["user", "question_count", "messages", "session_id",
                    "pending_question", "chat_open", "show_user_menu"]:
            st.session_state.pop(key, None)
        st.query_params.clear()
        st.rerun()


@st.dialog("Chat History")
def show_history_modal(user: dict):
    from utils.chat_history import load_history
    sessions = load_history(user["user_id"])

    if not sessions:
        st.info("No previous chats yet. Start a conversation!")
        return

    today_str     = date.today().isoformat()
    yesterday_str = (date.today() - timedelta(days=1)).isoformat()

    grouped = {}
    for s in sessions:
        d = s.get("date", "")
        label = "Today" if d == today_str else "Yesterday" if d == yesterday_str else d
        grouped.setdefault(label, []).append(s)

    for group_label, group_sessions in list(grouped.items())[:7]:
        st.markdown(f"**{group_label}**")
        for s in group_sessions[:5]:
            title = s.get("title", "Untitled")
            short = (title[:55] + "…") if len(title) > 55 else title
            if st.button(f"· {short}", key=f"hm_{s['session_id']}", use_container_width=True):
                _save_current(user["user_id"])
                st.session_state.messages   = s["messages"]
                st.session_state.session_id = s["session_id"]
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# COMPONENT — Navbar
# ══════════════════════════════════════════════════════════════════════════════
def render_navbar():
    col_logo, col_nav, col_actions = st.columns([1.2, 5, 2])

    with col_logo:
        st.markdown(
            '<span class="nav-logo"><span class="acc">D</span>emografy</span>',
            unsafe_allow_html=True,
        )

    with col_nav:
        st.markdown(
            """<div class="nav-links-bar">
                <a href="#">Home</a>
                <a href="#">Features</a>
                <a href="#">Testimonials</a>
                <a href="#">Use Case</a>
                <a href="#">Pricing</a>
                <a href="#">Career</a>
                <a href="#">Property Calculator</a>
            </div>""",
            unsafe_allow_html=True,
        )

    with col_actions:
        user = st.session_state.get("user")

        if user is None:
            st.markdown('<div class="nav-login-area"></div>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                login_clicked = st.button("Log in", key="nav_login", type="secondary", use_container_width=True)
            with c2:
                signup_clicked = st.button("Sign up", key="nav_signup", type="primary", use_container_width=True)
            if login_clicked or signup_clicked:
                show_login_modal()
        else:
            from auth.rbac import get_question_limit
            st.markdown('<div class="nav-hi-area"></div>', unsafe_allow_html=True)
            display_name = user.get("email", user["user_id"]).split("@")[0].title()
            hi_clicked = st.button(f"Hi, {display_name} ▾", key="hi_user")
            if hi_clicked:
                st.session_state.show_user_menu = not st.session_state.get("show_user_menu", False)

            if st.session_state.get("show_user_menu"):
                st.markdown('<div class="user-dropdown"></div>', unsafe_allow_html=True)
                if st.button("👤  Profile", key="menu_profile", use_container_width=True):
                    st.session_state.show_user_menu = False
                    tier  = user["tier"]
                    limit = get_question_limit(tier)
                    show_user_modal(user, st.session_state.question_count, limit, tier)
                if st.button("🚪  Logout", key="menu_logout", use_container_width=True):
                    for key in ["user", "question_count", "messages", "session_id",
                                "pending_question", "chat_open", "show_user_menu"]:
                        st.session_state.pop(key, None)
                    st.query_params.clear()
                    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# COMPONENT — Hero
# ══════════════════════════════════════════════════════════════════════════════
def render_hero():
    col_text, col_mock = st.columns([1, 1], gap="large")

    with col_text:
        st.markdown("""
        <div class="hero-wrap" style="padding-right:0;">
            <div class="hero-badge">▸ EXPLORE IN BETA</div>
            <div class="hero-h1">Australian<br>property insights,</div>
            <div class="hero-h2">propelled by data.</div>
            <div class="hero-sub">
                Ditch the guesswork. Our platform gives investors, homebuyers,
                and pros the hard numbers on suburb growth, so you can make
                your move with confidence, not just a hunch.
            </div>
        </div>
        """, unsafe_allow_html=True)

        user = st.session_state.get("user")
        if user is None:
            cta1, cta2 = st.columns([1.2, 1.3], gap="small")
            with cta1:
                st.markdown('<div class="hero-cta-secondary"></div>', unsafe_allow_html=True)
                if st.button("Discover more", key="hero_discover"):
                    show_login_modal()
            with cta2:
                st.markdown('<div class="hero-cta-primary"></div>', unsafe_allow_html=True)
                if st.button("Get early access →", key="hero_primary"):
                    show_login_modal()
        else:
            cta1, cta2 = st.columns([1.2, 1.3], gap="small")
            with cta1:
                st.markdown('<div class="hero-cta-secondary"></div>', unsafe_allow_html=True)
                if st.button("Discover more", key="hero_discover"):
                    pass
            with cta2:
                st.markdown('<div class="hero-cta-primary"></div>', unsafe_allow_html=True)
                if st.button("Open Chat 💬", key="hero_open_chat"):
                    _save_current(user["user_id"])
                    st.session_state.messages       = []
                    st.session_state.session_id     = str(uuid.uuid4())
                    st.session_state.question_count = 0
                    st.session_state.chat_open      = True
                    st.rerun()

    with col_mock:
        st.markdown("""
        <div class="hero-wrap mockup-outer" style="padding-left:20px;">
        <div class="mockup-card">
            <div class="mk-header"><span class="acc">D</span>emografy</div>
            <div class="mk-filters">
                <span class="mk-fl">State</span>
                <span class="mk-fp">NSW ▾</span>
                <span class="mk-fl" style="margin-left:6px;">Land Size</span>
                <span class="mk-fp">All sizes ▾</span>
                <span class="mk-fl" style="margin-left:6px;">Region</span>
                <span class="mk-fp">All regions ▾</span>
            </div>
            <div class="mk-stats">
                <div><div class="mk-sl">Total Areas</div><div class="mk-sv">644</div></div>
                <div><div class="mk-sl">Active KPIs</div><div class="mk-sv">3</div></div>
            </div>
            <div class="mk-th"><div>Rank</div><div>SA2 Area</div><div style="text-align:right;">Population</div></div>
            <div class="mk-row">
                <div><span class="mk-rank r1">1</span></div>
                <div><div class="mk-name">Corowa</div><div class="mk-loc">NSW · Riverina</div></div>
                <div class="mk-pop">1,026</div>
            </div>
            <div class="mk-row">
                <div><span class="mk-rank r2">2</span></div>
                <div><div class="mk-name">Bowraville – Glen Alpina</div><div class="mk-loc">NSW · Mid North Coast</div></div>
                <div class="mk-pop">23,830</div>
            </div>
            <div class="mk-row">
                <div><span class="mk-rank r3">3</span></div>
                <div><div class="mk-name">Leppington – Catherine Field</div><div class="mk-loc">NSW · South West Sydney</div></div>
                <div class="mk-pop">2,217</div>
            </div>
            <div class="mk-row">
                <div><span class="mk-rank rn">4</span></div>
                <div><div class="mk-name">Randwick – North</div><div class="mk-loc">NSW · Eastern Suburbs</div></div>
                <div class="mk-pop">63,873</div>
            </div>
            <div class="mk-row">
                <div><span class="mk-rank rn">5</span></div>
                <div><div class="mk-name">Maryland – Fletcher – Minmi</div><div class="mk-loc">NSW · Newcastle</div></div>
                <div class="mk-pop">6,217</div>
            </div>
            <div class="mk-row">
                <div><span class="mk-rank rn">6</span></div>
                <div><div class="mk-name">Broulee – Tomakin</div><div class="mk-loc">NSW · South East</div></div>
                <div class="mk-pop">23,082</div>
            </div>
        </div>
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# COMPONENT — Features section (static HTML)
# ══════════════════════════════════════════════════════════════════════════════
def render_features():
    st.markdown("""
<div class="section-feat" id="features">
  <div class="cw">
    <div style="text-align:center;">
        <span class="sec-badge"><span class="dot"></span> Features</span>
        <div class="sec-h2" style="margin:0 auto 16px;">Everything you need to make an<br>informed decision</div>
        <div class="sec-sub sec-sub-center">
            From suburb growth rates to livability scores — all the data you need,
            presented simply so you can act with confidence.
        </div>
    </div>
    <div class="feat-grid">
        <div class="feat-card">
            <div class="feat-icon">🔍</div>
            <div class="feat-title">Suburb Profiles</div>
            <div class="feat-desc">Deep dive on growth rates, prices, demographics, and local stats for every Australian suburb.</div>
        </div>
        <div class="feat-card">
            <div class="feat-icon">⚖️</div>
            <div class="feat-title">Compare Mode</div>
            <div class="feat-desc">Line up suburbs side-by-side and spot future growth zones instantly across 50+ metrics.</div>
        </div>
        <div class="feat-card">
            <div class="feat-icon">🗺️</div>
            <div class="feat-title">Growth Heatmaps</div>
            <div class="feat-desc">Visual analytics backed by ABS census data and real property listing trends.</div>
        </div>
        <div class="feat-card">
            <div class="feat-icon">📍</div>
            <div class="feat-title">Proximity Index</div>
            <div class="feat-desc">Schools, jobs, and transport all scored for convenience and lifestyle — before you visit.</div>
        </div>
        <div class="feat-card">
            <div class="feat-icon">📈</div>
            <div class="feat-title">Investment Insights</div>
            <div class="feat-desc">Yield, vacancy rates, and capital growth trajectories simplified into clear, actionable data.</div>
        </div>
        <div class="feat-card">
            <div class="feat-icon">🏡</div>
            <div class="feat-title">Livability Scores</div>
            <div class="feat-desc">See what everyday life feels like across suburbs before you commit — backed by real data.</div>
        </div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# COMPONENT — Features Detailed (alternating layout)
# ══════════════════════════════════════════════════════════════════════════════
def render_features_detailed():
    st.markdown("""
<div class="section-fd">
  <div style="max-width:1200px; margin:0 auto; text-align:center; margin-bottom:16px;">
      <span class="sec-badge"><span class="dot"></span> How It Works</span>
      <div class="sec-h2">The smartest suburb<br><span style="color:#8b5cf6;">intelligence platform</span></div>
  </div>

  <!-- Row 1: visual left, text right -->
  <div class="fd-pair">
    <div class="fd-visual">
        <div class="fd-vis-head">
            <span>AI Query Results</span>
            <span class="fd-vis-tag">Live</span>
        </div>
        <div style="background:#f9fafb; border-radius:10px; padding:12px; margin-bottom:12px; font-size:0.78rem; color:#6b7280; font-style:italic;">
            "What are the top 3 suburbs in Victoria with the highest diversity index?"
        </div>
        <div class="fd-bar-row">
            <div class="fd-bar-label">Footscray</div>
            <div class="fd-bar-track"><div class="fd-bar-fill" style="width:92%;"></div></div>
            <div class="fd-bar-val">9.2</div>
        </div>
        <div class="fd-bar-row">
            <div class="fd-bar-label">Springvale</div>
            <div class="fd-bar-track"><div class="fd-bar-fill" style="width:88%;"></div></div>
            <div class="fd-bar-val">8.8</div>
        </div>
        <div class="fd-bar-row">
            <div class="fd-bar-label">Richmond</div>
            <div class="fd-bar-track"><div class="fd-bar-fill" style="width:84%;"></div></div>
            <div class="fd-bar-val">8.4</div>
        </div>
    </div>
    <div class="fd-text">
        <div class="fd-badge">✦ AI-Powered</div>
        <div class="fd-h3">Ask in plain English.<br><span class="acc">Get instant answers.</span></div>
        <div class="fd-p">
            No SQL knowledge required. Just ask your question in plain English
            and our AI queries 50+ suburb metrics to give you a precise, data-backed answer
            in seconds — powered by Google Gemini and live BigQuery data.
        </div>
        <a class="fd-link" href="#">Learn more →</a>
    </div>
  </div>

  <!-- Row 2: text left, visual right -->
  <div class="fd-pair rev">
    <div class="fd-visual">
        <div class="fd-vis-head">
            <span>Suburb Comparison</span>
            <span class="fd-vis-tag">2 Suburbs</span>
        </div>
        <div class="fd-compare-row">
            <div class="fd-compare-card">
                <div class="fd-cc-name">Bondi Beach</div>
                <div class="fd-cc-kpi">Diversity <span>7.8</span></div>
                <div class="fd-cc-kpi">Prosperity <span>8.4</span></div>
                <div class="fd-cc-kpi">Population <span>12,430</span></div>
                <div class="fd-cc-kpi">Growth % <span style="color:#10b981;">+6.2%</span></div>
            </div>
            <div class="fd-compare-card">
                <div class="fd-cc-name">Manly</div>
                <div class="fd-cc-kpi">Diversity <span>6.9</span></div>
                <div class="fd-cc-kpi">Prosperity <span>8.7</span></div>
                <div class="fd-cc-kpi">Population <span>16,020</span></div>
                <div class="fd-cc-kpi">Growth % <span style="color:#10b981;">+4.8%</span></div>
            </div>
        </div>
        <div style="font-size:0.68rem; color:#9ca3af; margin-top:8px;">★ Bondi edges ahead on diversity &amp; growth trajectory</div>
    </div>
    <div class="fd-text">
        <div class="fd-badge">✦ Compare Mode</div>
        <div class="fd-h3">Side-by-side suburb<br><span class="acc">comparison.</span></div>
        <div class="fd-p">
            Stack any two suburbs against each other across 50+ KPIs.
            Diversity index, prosperity score, rental yields, population density —
            all the data you need to pick the better option, not just the popular one.
        </div>
        <a class="fd-link" href="#">Learn more →</a>
    </div>
  </div>

  <!-- Row 3: visual left, text right -->
  <div class="fd-pair">
    <div class="fd-visual">
        <div class="fd-vis-head">
            <span>Growth Heatmap — NSW</span>
            <span class="fd-vis-tag">ABS 2024</span>
        </div>
        <div class="fd-heatmap" style="margin-bottom:8px;">
            <div class="fd-hm-cell" style="background:#c4b5fd;"></div>
            <div class="fd-hm-cell" style="background:#8b5cf6;"></div>
            <div class="fd-hm-cell" style="background:#6d28d9;"></div>
            <div class="fd-hm-cell" style="background:#a78bfa;"></div>
            <div class="fd-hm-cell" style="background:#7c3aed;"></div>
            <div class="fd-hm-cell" style="background:#ddd6fe;"></div>
            <div class="fd-hm-cell" style="background:#8b5cf6;"></div>
            <div class="fd-hm-cell" style="background:#5b21b6;"></div>
            <div class="fd-hm-cell" style="background:#8b5cf6;"></div>
            <div class="fd-hm-cell" style="background:#ede9fe;"></div>
            <div class="fd-hm-cell" style="background:#7c3aed;"></div>
            <div class="fd-hm-cell" style="background:#6d28d9;"></div>
            <div class="fd-hm-cell" style="background:#a78bfa;"></div>
            <div class="fd-hm-cell" style="background:#c4b5fd;"></div>
            <div class="fd-hm-cell" style="background:#8b5cf6;"></div>
            <div class="fd-hm-cell" style="background:#7c3aed;"></div>
            <div class="fd-hm-cell" style="background:#ddd6fe;"></div>
            <div class="fd-hm-cell" style="background:#5b21b6;"></div>
            <div class="fd-hm-cell" style="background:#a78bfa;"></div>
            <div class="fd-hm-cell" style="background:#6d28d9;"></div>
            <div class="fd-hm-cell" style="background:#ede9fe;"></div>
        </div>
        <div style="display:flex; gap:8px; align-items:center; font-size:0.62rem; color:#9ca3af;">
            <div style="width:10px; height:10px; background:#ede9fe; border-radius:2px;"></div> Low
            <div style="width:10px; height:10px; background:#8b5cf6; border-radius:2px;"></div> Medium
            <div style="width:10px; height:10px; background:#5b21b6; border-radius:2px;"></div> High growth
        </div>
    </div>
    <div class="fd-text">
        <div class="fd-badge">✦ Visual Analytics</div>
        <div class="fd-h3">Growth mapped,<br><span class="acc">visually.</span></div>
        <div class="fd-p">
            Heatmaps powered by ABS census data and property listing trends reveal
            high-growth zones at a glance. Stop guessing which suburbs are up-and-coming —
            see the data patterns yourself.
        </div>
        <a class="fd-link" href="#">Learn more →</a>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# COMPONENT — Use Cases section (static HTML)
# ══════════════════════════════════════════════════════════════════════════════
def render_use_cases():
    st.markdown("""
<div class="section-uc" id="use-cases">
  <div class="uc-layout">
    <div>
        <span class="sec-badge"><span class="dot"></span> Use Cases</span>
        <div class="sec-h2">Who this<br>is for</div>
        <div class="sec-sub" style="margin-bottom:0;">
            Whether you're buying your first studio, flipping your tenth investment property,
            or helping clients navigate the market — our platform speaks your language.
        </div>
    </div>
    <div class="uc-grid">
        <div class="uc-card">
            <div class="uc-icon">🏠</div>
            <div class="uc-title">First-Home Buyers</div>
            <div class="uc-sub">Decide best suburb</div>
        </div>
        <div class="uc-card">
            <div class="uc-icon">💼</div>
            <div class="uc-title">Investors</div>
            <div class="uc-sub">Growth versus risk</div>
        </div>
        <div class="uc-card">
            <div class="uc-icon">🤝</div>
            <div class="uc-title">Real Estate Agents</div>
            <div class="uc-sub">Business building</div>
        </div>
        <div class="uc-card">
            <div class="uc-icon">🏗️</div>
            <div class="uc-title">Property Developers</div>
            <div class="uc-sub">Best regions to focus</div>
        </div>
        <div class="uc-card">
            <div class="uc-icon">📋</div>
            <div class="uc-title">Mortgage Brokers</div>
            <div class="uc-sub">Add-on services</div>
        </div>
        <div class="uc-card">
            <div class="uc-icon">👨‍👩‍👧</div>
            <div class="uc-title">Families Relocating</div>
            <div class="uc-sub">Choose the best area</div>
        </div>
        <div class="uc-card">
            <div class="uc-icon">🎯</div>
            <div class="uc-title">Buyer's Agents</div>
            <div class="uc-sub">Analytics within reach</div>
        </div>
        <div class="uc-card">
            <div class="uc-icon">📊</div>
            <div class="uc-title">Home Upgraders</div>
            <div class="uc-sub">Decide when to sell</div>
        </div>
        <div class="uc-card">
            <div class="uc-icon">🔬</div>
            <div class="uc-title">Data Geeks</div>
            <div class="uc-sub">Play around with data</div>
        </div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# COMPONENT — Testimonials (static HTML)
# ══════════════════════════════════════════════════════════════════════════════
def render_testimonials():
    st.markdown("""
<div class="section-testi" id="testimonials">
  <div class="cw">
    <div style="text-align:center; margin-bottom:52px;">
        <span class="sec-badge"><span class="dot"></span> Testimonials</span>
        <div class="sec-h2">Trusted by property professionals</div>
        <div class="sec-sub sec-sub-center">
            Real people making smarter property decisions with Demografy.
        </div>
    </div>
    <div class="testi-grid">
        <div class="testi-card">
            <div class="testi-stars">★★★★★</div>
            <div class="testi-quote">
                "In just weeks, I went from property beginner to informed buyer.
                The suburb comparison tool showed me exactly why I should look at
                Footscray instead of Richmond — and the numbers proved it."
            </div>
            <div class="testi-author">
                <div class="testi-av av-1">👤</div>
                <div>
                    <div class="testi-name">Michael Chen</div>
                    <div class="testi-role">First-home buyer, Melbourne</div>
                </div>
            </div>
        </div>
        <div class="testi-card">
            <div class="testi-stars">★★★★★</div>
            <div class="testi-quote">
                "I used the platform to find my perfect suburb. Later, the exact same tools
                helped me identify a high-growth unit for my first investment. It made the leap
                from emotional home-buying to strategic investing feel completely natural."
            </div>
            <div class="testi-author">
                <div class="testi-av av-2">👤</div>
                <div>
                    <div class="testi-name">Sarah Thompson</div>
                    <div class="testi-role">Home-owner &amp; investor, Sydney</div>
                </div>
            </div>
        </div>
        <div class="testi-card">
            <div class="testi-stars">★★★★★</div>
            <div class="testi-quote">
                "The data depth is unlike anything else I've used. My clients trust my
                suburb recommendations 100% more now that I can back every suggestion
                with hard ABS numbers and live growth trends."
            </div>
            <div class="testi-author">
                <div class="testi-av av-3">👤</div>
                <div>
                    <div class="testi-name">James Nguyen</div>
                    <div class="testi-role">Buyer's Agent, Brisbane</div>
                </div>
            </div>
        </div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# COMPONENT — Pricing / CTA
# ══════════════════════════════════════════════════════════════════════════════
def render_pricing_cta():
    st.markdown("""
<div class="section-cta" id="pricing">
  <div class="cw" style="display:flex; flex-direction:column; align-items:center;">
    <div class="cta-glow">
        <span class="sec-badge" style="margin-bottom:20px;"><span class="dot"></span> Get Started</span>
        <div class="cta-h2">Start exploring Australian<br>suburbs today</div>
        <div class="cta-sub">
            Free access available. Upgrade for unlimited queries<br>and advanced analytics across all 644 SA2 areas.
        </div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

    # Streamlit button — centered, styled via :has()
    _, center, _ = st.columns([2.5, 1.5, 2.5])
    with center:
        st.markdown('<div class="pricing-cta-area"></div>', unsafe_allow_html=True)
        if st.button("Get early access →", key="pricing_cta", use_container_width=True):
            show_login_modal()

    # White spacer so footer connects cleanly
    st.markdown('<div style="background:white; padding:24px 0;"></div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# COMPONENT — Footer (static HTML)
# ══════════════════════════════════════════════════════════════════════════════
def render_footer():
    st.markdown("""
<div class="footer-wrap">
  <div class="footer-inner">
    <div class="footer-top">
        <div>
            <div class="footer-logo"><span class="acc">D</span>emografy</div>
            <div class="footer-tagline">
                Data-driven insights on every Australian suburb.
                Make smarter property decisions.
            </div>
        </div>
        <div class="footer-col">
            <div class="footer-col-title">Product</div>
            <a href="#">Features</a>
            <a href="#">Pricing</a>
            <a href="#">Changelog</a>
            <a href="#">Roadmap</a>
        </div>
        <div class="footer-col">
            <div class="footer-col-title">Company</div>
            <a href="#">About</a>
            <a href="#">Career</a>
            <a href="#">Blog</a>
            <a href="#">Press</a>
        </div>
        <div class="footer-col">
            <div class="footer-col-title">Legal</div>
            <a href="#">Privacy Policy</a>
            <a href="#">Terms of Service</a>
            <a href="#">Cookie Policy</a>
        </div>
        <div class="footer-col">
            <div class="footer-col-title">Connect</div>
            <a href="#">LinkedIn</a>
            <a href="#">GitHub</a>
            <a href="#">Twitter / X</a>
            <a href="#">Contact Us</a>
        </div>
    </div>
    <div class="footer-bottom">
        <span>© 2025 Demografy Pty Ltd. All rights reserved.</span>
        <span>Built in Australia 🇦🇺</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# COMPONENT — Chat FAB (logged-in, fixed bottom-right)
# ══════════════════════════════════════════════════════════════════════════════
def render_chat_fab():
    st.markdown('<div class="chat-fab-anchor"></div>', unsafe_allow_html=True)
    if st.button("💬", key="chat_fab"):
        user = st.session_state.user
        if user:
            _save_current(user["user_id"])
        st.session_state.messages       = []
        st.session_state.session_id     = str(uuid.uuid4())
        st.session_state.question_count = 0
        st.session_state.chat_open      = True
        st.query_params["s"] = st.session_state.session_id
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# COMPONENT — Full landing page
# ══════════════════════════════════════════════════════════════════════════════
def render_landing_page():
    render_navbar()
    render_hero()
    if st.session_state.get("user"):
        render_chat_fab()


# ══════════════════════════════════════════════════════════════════════════════
# COMPONENT — Sidebar (chat screen)
# ══════════════════════════════════════════════════════════════════════════════
def render_sidebar(user: dict, question_count: int, limit: int, tier: str):
    st.markdown('<div class="sb-logo"><span class="acc">D</span>emografy</div>', unsafe_allow_html=True)

    if st.button("✏️  New Chat", key="new_chat", use_container_width=True):
        _save_current(user["user_id"])
        new_sid = str(uuid.uuid4())
        st.session_state.messages       = []
        st.session_state.session_id     = new_sid
        st.session_state.question_count = 0
        st.query_params["s"] = new_sid
        st.rerun()

    if st.button("🕐  Chat History", key="history", use_container_width=True):
        show_history_modal(user)

    st.markdown("<div style='flex:1'></div>", unsafe_allow_html=True)
    st.markdown('<hr class="sb-divider">', unsafe_allow_html=True)

    tier_label = {"pro": "Pro ✦", "basic": "Basic", "free": "Free"}.get(tier, tier.title())
    st.markdown(
        f'<div class="sb-user"><div class="sb-user-name">👤 {user["user_id"]}</div>'
        f'<div class="sb-user-tier">{tier_label} · {user.get("email", "")}</div></div>',
        unsafe_allow_html=True,
    )
    if st.button("⚙️  Account", key="user_footer", use_container_width=True):
        show_user_modal(user, question_count, limit, tier)


# ══════════════════════════════════════════════════════════════════════════════
# COMPONENT — Empty state
# ══════════════════════════════════════════════════════════════════════════════
def render_empty_state() -> str | None:
    st.markdown("""
    <div class="empty-wrap">
        <div class="empty-heading">What suburb are you exploring?</div>
    </div>
    """, unsafe_allow_html=True)

    suggestions = [
        ("🏘️", "Top 3 diverse suburbs in Victoria?"),
        ("📊", "Average prosperity score in NSW?"),
        ("🏡", "Cheapest rentals in Queensland?"),
    ]

    cols = st.columns(3)
    for i, (icon_label, chip_text) in enumerate(suggestions):
        with cols[i]:
            st.markdown('<div class="chip-wrap">', unsafe_allow_html=True)
            if st.button(f"{icon_label}  {chip_text}", key=f"sug_{i}", use_container_width=True):
                return chip_text
            st.markdown('</div>', unsafe_allow_html=True)

    return None


# ══════════════════════════════════════════════════════════════════════════════
# COMPONENT — Chat messages
# ══════════════════════════════════════════════════════════════════════════════
def render_chat_messages(messages: list):
    for msg in messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("sql"):
                with st.expander("🔍 View SQL Query"):
                    st.code(msg["sql"], language="sql")


# ══════════════════════════════════════════════════════════════════════════════
# COMPONENT — Counter pill
# ══════════════════════════════════════════════════════════════════════════════
def render_counter(question_count: int, limit: int, tier: str):
    remaining = limit - question_count
    if remaining <= 0:
        cls, label = "c-red", "❌ limit reached"
    elif remaining <= 3:
        cls, label = "c-red", f"🔴 {remaining} left"
    elif remaining <= int(limit * 0.25):
        cls, label = "c-yellow", f"🟡 {remaining} left"
    else:
        cls, label = "c-green", f"🟢 {remaining} left"

    st.markdown(
        f'<div class="counter-fixed"><span class="{cls}">{label} · {tier.upper()}</span></div>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# HANDLER — Process a question
# ══════════════════════════════════════════════════════════════════════════════
def handle_question(question: str, user: dict, tier: str, limit: int):
    from utils.chat_history import save_session

    st.session_state.question_count += 1

    st.session_state.messages.append({"role": "user", "content": question, "sql": None})

    with st.chat_message("user"):
        st.markdown(question)

    sql_query = None
    answer    = None

    with st.chat_message("assistant"):
        try:
            from agent.sql_agent import ask
            from langchain_community.callbacks.streamlit import StreamlitCallbackHandler
            steps_container = st.container()
            st_callback = StreamlitCallbackHandler(
                steps_container,
                expand_new_thoughts=True,
                collapse_completed_thoughts=True,
            )
            answer, sql_query = ask(question, callbacks=[st_callback])
        except Exception as agent_err:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                from langchain_core.messages import SystemMessage, HumanMessage
                with st.spinner("Thinking..."):
                    llm = ChatGoogleGenerativeAI(
                        model="gemini-2.5-flash",
                        google_api_key=os.getenv("GEMINI_API_KEY"),
                        temperature=0,
                    )
                    response = llm.invoke([
                        SystemMessage(content=(
                            "You are Demografy, an AI assistant specialising in Australian suburb demographics. "
                            "You have knowledge of ABS census data, suburb statistics, KPIs like diversity index, "
                            "prosperity score, rental costs, population density, and more. "
                            "Answer questions helpfully and concisely. "
                            "Note: live BigQuery data is not yet connected, so answers are based on general knowledge."
                        )),
                        HumanMessage(content=question),
                    ])
                answer = response.content + "\n\n> ⚠️ *Live data not connected — answer from general AI knowledge.*"
            except Exception as e2:
                answer = f"⚠️ Could not get a response.\n\n**Error:** {str(e2)}"

        if answer:
            st.markdown(answer)
            if sql_query:
                with st.expander("🔍 View SQL Query"):
                    st.code(sql_query, language="sql")

    st.session_state.messages.append({"role": "assistant", "content": answer or "", "sql": sql_query})

    save_session(
        user_id=user["user_id"],
        session_id=st.session_state.session_id,
        title=st.session_state.messages[0]["content"][:60],
        messages=st.session_state.messages,
    )

    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# COMPONENT — Full chat screen
# ══════════════════════════════════════════════════════════════════════════════
def render_chat_screen():
    from auth.rbac import get_question_limit, is_limit_reached

    user           = st.session_state.user
    tier           = user["tier"]
    question_count = st.session_state.question_count
    limit          = get_question_limit(tier)
    messages       = st.session_state.messages

    st.markdown('<div class="back-btn">', unsafe_allow_html=True)
    if st.button("← Home", key="back_home"):
        st.session_state.chat_open = False
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # Marker scopes sidebar CSS to chat screen only
    st.markdown('<div class="chat-layout-marker"></div>', unsafe_allow_html=True)

    left, right = st.columns([1, 4])

    with left:
        render_sidebar(user, question_count, limit, tier)

    with right:
        pending = st.session_state.pop("pending_question", None)

        if not messages:
            suggestion = render_empty_state()
            if suggestion:
                st.session_state.pending_question = suggestion
                st.rerun()
        else:
            render_chat_messages(messages)

        limit_reached = is_limit_reached(tier, question_count)
        render_counter(question_count, limit, tier)

        question = st.chat_input(
            "Question limit reached — upgrade to continue" if limit_reached
            else "e.g. What are the top 3 suburbs in Victoria by diversity index?",
            disabled=limit_reached,
        ) or pending

        if question and not limit_reached:
            handle_question(question, user, tier, limit)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
load_css()

for _key, _default in [
    ("user",             None),
    ("question_count",   0),
    ("messages",         []),
    ("session_id",       str(uuid.uuid4())),
    ("pending_question", None),
    ("chat_open",        False),
    ("show_user_menu",   False),
]:
    if _key not in st.session_state:
        st.session_state[_key] = _default

# ── Auto-restore session from URL params ──────────────────────────────────────
if st.session_state.user is None:
    _uid = st.query_params.get("u")
    _sid = st.query_params.get("s")
    if _uid:
        try:
            from auth.rbac import get_user
            from utils.chat_history import load_history
            _user = get_user(_uid)
            if _user:
                _sessions = load_history(_uid)
                _session  = next((s for s in _sessions if s["session_id"] == _sid), None)
                _msgs     = _session["messages"] if _session else []
                st.session_state.user           = _user
                st.session_state.messages       = _msgs
                st.session_state.session_id     = _sid if _sid else str(uuid.uuid4())
                st.session_state.question_count = len([m for m in _msgs if m["role"] == "user"])
                if _msgs:
                    st.session_state.chat_open = True
            else:
                st.query_params.clear()
        except Exception:
            st.query_params.clear()

# ── Main routing ──────────────────────────────────────────────────────────────
if st.session_state.get("chat_open") and st.session_state.user:
    render_chat_screen()
else:
    render_landing_page()
