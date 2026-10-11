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

# Session state initialization
if "current_screen" not in st.session_state:
    st.session_state.current_screen = "Screen 1 — New Audit"

# --- Sidebar Navigation ---
with st.sidebar:
    st.markdown("""
    <div style="text-align: center; padding: 10px 0;">
        <h2 style="margin: 0; color: #0d9488; font-weight: 800;">REGIS AGED CARE</h2>
        <p style="margin: 4px 0 16px 0; font-size: 0.85rem; color: #94a3b8; font-weight: 600;">AI Food Safety Audit Suite</p>
    </div>
    """, unsafe_allow_html=True)

    screens = [
        "Screen 1 — New Audit",
        "Screen 2 — AI Findings",
        "Screen 3 — Report Preview",
        "Screen 4 — Report History"
    ]

    selected_screen = st.radio(
        "Navigation",
        screens,
        index=screens.index(st.session_state.current_screen) if st.session_state.current_screen in screens else 0,
        key="nav_radio"
    )
    st.session_state.current_screen = selected_screen

    st.markdown("---")
    
    # Active Audit Badge in Sidebar
    active_audit_id = st.session_state.get("current_audit_id")
    if active_audit_id:
        st.markdown(f"**Active Audit:** `{active_audit_id}`")
        if st.button("➕ Start Another Audit", use_container_width=True):
            st.session_state.current_audit_id = None
            st.session_state.current_findings = None
            st.session_state.photo_notes = {}
            st.session_state.current_screen = "Screen 1 — New Audit"
            st.rerun()



# --- Route Screen ---
if st.session_state.current_screen == "Screen 1 — New Audit":
    render_screen1()
elif st.session_state.current_screen == "Screen 2 — AI Findings":
    render_screen2()
elif st.session_state.current_screen == "Screen 3 — Report Preview":
    render_screen3()
elif st.session_state.current_screen == "Screen 4 — Report History":
    render_screen4()
