"""
Regis AI Daily Food Safety Audit Automation
Main Application Entry Point (Streamlit).
Fulfills PRD: Photo + short text -> AI-generated audit report -> downloadable PDF.
"""

import os
from pathlib import Path
import streamlit as st

# Configure page settings
st.set_page_config(
    page_title="Regis AI Daily Audit Maker",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database
from database.db import init_db
init_db()

# Load custom CSS
css_path = Path(__file__).parent / "static" / "styles.css"
if css_path.exists():
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Imports for screens
from ui.screen1_new_audit import render_screen1
from ui.screen2_findings import render_screen2
from ui.screen3_preview import render_screen3
from ui.screen4_history import render_screen4
from core.config import SUPPORTED_VISION_MODELS, DEFAULT_VISION_MODEL

# Session state initialization
if "current_screen" not in st.session_state:
    st.session_state.current_screen = "Screen 1 — New Audit"

# --- Executive Sidebar ---
with st.sidebar:
    st.markdown("""
    <div style="padding: 12px 6px 18px 6px;">
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
            <div style="background: linear-gradient(135deg, #0284c7, #0f766e); width: 38px; height: 38px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 1.25rem; box-shadow: 0 2px 8px rgba(2, 132, 199, 0.25);">🛡️</div>
            <div>
                <h3 style="margin: 0; font-size: 1.15rem; font-weight: 800; color: #0f172a; letter-spacing: -0.01em;">REGIS AGED CARE</h3>
                <span style="font-size: 0.75rem; color: #0284c7; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em;">AI Audit Suite</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    screens = [
        "Screen 1 — New Audit",
        "Screen 2 — AI Findings",
        "Screen 3 — Report Preview",
        "Screen 4 — Report History"
    ]

    selected_screen = st.radio(
        "Navigation Menu",
        screens,
        index=screens.index(st.session_state.current_screen) if st.session_state.current_screen in screens else 0,
        key="nav_radio"
    )
    st.session_state.current_screen = selected_screen

    # Active Audit Badge in Sidebar
    active_audit_id = st.session_state.get("current_audit_id")
    if active_audit_id:
        st.markdown("---")
        st.markdown(f"""
        <div style="background: #e0f2fe; border: 1px solid #bae6fd; border-radius: 10px; padding: 12px; margin-bottom: 12px;">
            <span style="font-size: 0.72rem; color: #475569; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;">Active Audit Session</span>
            <div style="font-weight: 800; color: #0369a1; font-size: 0.95rem; margin-top: 2px;">{active_audit_id}</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("➕ Start New Audit", use_container_width=True):
            st.session_state.current_audit_id = None
            st.session_state.current_findings = None
            st.session_state.photo_notes = {}
            st.session_state.current_screen = "Screen 1 — New Audit"
            st.rerun()

    st.markdown("---")
    st.markdown("##### ⚙️ AI Engine Configuration")
    
    sidebar_api_key = st.text_input(
        "OpenRouter API Key",
        value=st.session_state.get("openrouter_api_key", os.getenv("OPENROUTER_API_KEY", "")),
        type="password",
        placeholder="sk-or-v1-...",
        help="Enter OpenRouter key. Stored securely in your session."
    )
    if sidebar_api_key:
        st.session_state.openrouter_api_key = sidebar_api_key.strip()
        
    model_labels = {
        "google/gemini-2.0-flash-001": "⚡ Gemini 2.0 Flash (Fast)",
        "anthropic/claude-3.5-sonnet": "🧠 Claude 3.5 Sonnet",
        "meta-llama/llama-3.2-11b-vision-instruct": "🦙 Llama 3.2 Vision",
        "openai/gpt-4o-mini": "🚀 GPT-4o Mini",
        "openai/gpt-4o": "👑 GPT-4o"
    }
    
    cur_model = st.session_state.get("selected_vision_model", DEFAULT_VISION_MODEL)
    cur_idx = SUPPORTED_VISION_MODELS.index(cur_model) if cur_model in SUPPORTED_VISION_MODELS else 0
    
    sidebar_model = st.selectbox(
        "Vision AI Model",
        SUPPORTED_VISION_MODELS,
        format_func=lambda m: model_labels.get(m, m),
        index=cur_idx,
        key="sidebar_ai_model_selector"
    )
    st.session_state.selected_vision_model = sidebar_model
    
    if bool(st.session_state.get("openrouter_api_key")):
        st.markdown('<div class="ai-status-pill ai-status-connected" style="margin-top: 6px;">🟢 Live OpenRouter Active</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="ai-status-pill ai-status-heuristic" style="margin-top: 6px;">🟡 Offline Heuristic Active</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.caption("🔒 Verified Food Safety Standard FSANZ 3.2.1 • 3.2.2 • 3.2.3")

# --- Route Screen ---
if st.session_state.current_screen == "Screen 1 — New Audit":
    render_screen1()
elif st.session_state.current_screen == "Screen 2 — AI Findings":
    render_screen2()
elif st.session_state.current_screen == "Screen 3 — Report Preview":
    render_screen3()
elif st.session_state.current_screen == "Screen 4 — Report History":
    render_screen4()
