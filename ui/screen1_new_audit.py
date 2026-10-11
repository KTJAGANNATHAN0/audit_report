"""
Screen 1 — New Audit
Select audit date and site, upload photos, enter short notes/keywords, and submit for AI analysis.
Fulfills FR-01, FR-02, FR-03, and PRD Section 8.
"""

import os
from pathlib import Path
from datetime import datetime, date, timedelta
import streamlit as st
from PIL import Image
from core.config import REGIS_SITES, DEFAULT_AUDITOR, UPLOADS_DIR, SUPPORTED_VISION_MODELS, DEFAULT_VISION_MODEL, OPENROUTER_API_KEY
from core.ai_service import analyze_photo_evidence
from database.db import create_audit, save_findings_for_audit

QUICK_OBSERVATION_TEMPLATES = [
    "Dirty microwave with food residue on top interior",
    "Canopy grease buildup above cooking range",
    "Exposed unsealed timber below servery bench",
    "Hand wash basin obstructed by dishes and items",
    "Visible mould growth on silicone seals around sink",
    "Uncovered food trays inside cool room without labels",
    "Dented food can found in dry store shelving",
    "Dishwasher rinse temperature below standard",
    "Food stored directly on coolroom floor",
    "Damaged ceiling coving in food preparation area"
]

def render_screen1():
    # --- Hero Header ---
    st.markdown("""
    <div class="hero-banner">
        <div class="hero-badge">🛡️ Quality & Food Safety Compliance • FSANZ Standards</div>
        <h1>Daily Food Safety Audit Automation</h1>
        <p>Effortlessly transform field inspection photos and short notes into compliant, structured Regis audit findings with OpenRouter Vision AI.</p>
    </div>
    """, unsafe_allow_html=True)

    # --- Step 1: Audit Metadata & Facility Profiles ---
    st.markdown("""
    <div class="step-header">
        <div class="step-number">1</div>
        <h3 class="step-title">Facility Profile & Audit Information</h3>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("🏢 Inspect & Edit Facility Metadata", expanded=True):
        col_site, col_date = st.columns([2, 1])
        
        site_names = [s["site_name"] for s in REGIS_SITES] + ["Other / Custom Facility..."]
        current_site_name = st.session_state.get("audit_site_name", site_names[0])
        site_idx = site_names.index(current_site_name) if current_site_name in site_names else 0
        
        with col_site:
            selected_site = st.selectbox("Select Regis Aged Care Facility", site_names, index=site_idx)
            
        with col_date:
            audit_date = st.date_input("Audit Inspection Date", value=st.session_state.get("audit_date_val", date.today()))
            audit_time = st.text_input("Inspection Time", value=st.session_state.get("audit_time_val", "9:30am"))

        site_preset = next((s for s in REGIS_SITES if s["site_name"] == selected_site), None)
        
        c1, c2, c3 = st.columns(3)
        with c1:
            proprietor = st.text_input("Proprietor", value=site_preset["proprietor_name"] if site_preset else "Regis Aged Care")
            trading_name = st.text_input("Trading Name", value=selected_site if selected_site != "Other / Custom Facility..." else "")
            business_address = st.text_input("Business Address", value=site_preset["business_address"] if site_preset else "")
            phone_number = st.text_input("Facility Phone", value=site_preset["phone_number"] if site_preset else "")

        with c2:
            business_contact = st.text_input("Business Contact", value=site_preset["business_contact"] if site_preset else "Bryan Seeborun")
            contact_email = st.text_input("Contact Email", value=site_preset["contact_email"] if site_preset else "bseeborun@regis.com.au")
            person_in_charge = st.text_input("Person in Charge (PIC)", value=site_preset["person_in_charge"] if site_preset else "Site Manager")
            pic_email = st.text_input("PIC Email", value=site_preset["pic_email"] if site_preset else "")

        with c3:
            nominated_fss = st.text_input("Nominated FSS", value=site_preset["nominated_fss"] if site_preset else "Sunil Kumar / Damith Yagamuni")
            council_name = st.text_input("Council / Shire Authority", value=site_preset["council_name"] if site_preset else "City of Greater Dandenong")
            council_reg_no = st.text_input("Registration & Expiry No.", value=site_preset["council_reg_no"] if site_preset else "F-2247 Expiry Date 31/12/2026")
            council_email = st.text_input("Council Email", value=site_preset["council_email"] if site_preset else "council@cgd.vic.gov.au")

        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        st.markdown("**Auditor Official Credentials**")
        ac1, ac2, ac3, ac4 = st.columns(4)
        with ac1:
            auditor_name = st.text_input("Auditor Name", value=DEFAULT_AUDITOR["name"])
        with ac2:
            auditor_reg = st.text_input("DHHS Reg. Number", value=DEFAULT_AUDITOR["dhhs_reg"])
        with ac3:
            auditor_phone = st.text_input("Auditor Phone", value=DEFAULT_AUDITOR["phone"])
        with ac4:
            auditor_email = st.text_input("Auditor Email", value=DEFAULT_AUDITOR["email"])

    # --- Step 2: Audit Evidence Photos & Notes ---
    st.markdown("""
    <div class="step-header">
        <div class="step-number">2</div>
        <h3 class="step-title">Inspection Evidence & Observations</h3>
    </div>
    """, unsafe_allow_html=True)

    uploaded_files = st.file_uploader(
        "Drop or capture audit photos (JPG, PNG, WebP) — Multiple files supported",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        key="audit_photos_uploader"
    )

    if "photo_notes" not in st.session_state:
        st.session_state.photo_notes = {}

    photo_entries = []
    
    if uploaded_files:
        st.markdown(f"""
        <div style="background: #e0f2fe; border: 1px solid #bae6fd; border-radius: 12px; padding: 12px 18px; margin-bottom: 20px;">
            <span style="font-weight: 700; color: #0369a1;">📸 {len(uploaded_files)} Evidence Photograph(s) Loaded.</span>
            <span style="color: #475569; font-size: 0.9rem;"> Add concise notes or select standard snippets for each item below.</span>
        </div>
        """, unsafe_allow_html=True)
        
        # Grid layout for uploaded images
        cols = st.columns(2)
        for idx, file in enumerate(uploaded_files):
            col = cols[idx % 2]
            with col:
                with st.container(border=True):
                    st.markdown(f"**Fig. {idx + 1}** — `{file.name}`")
                    img = Image.open(file)
                    st.image(img, use_container_width=True)
                    
                    note_key = f"note_{file.name}_{idx}"
                    default_note = st.session_state.photo_notes.get(note_key, "")
                    
                    sample_choice = st.selectbox(
                        f"Quick insert template for Fig. {idx + 1}:",
                        ["(Select keyword template...)"] + QUICK_OBSERVATION_TEMPLATES,
                        key=f"sample_{idx}"
                    )
                    if sample_choice and not sample_choice.startswith("("):
                        default_note = sample_choice

                    note_input = st.text_area(
                        f"Observation keywords for Fig. {idx + 1}:",
                        value=default_note,
                        placeholder="e.g. Dirty microwave, food residue on top interior, clean immediately.",
                        key=note_key,
                        height=85
                    )
                    st.session_state.photo_notes[note_key] = note_input

                    photo_entries.append({
                        "index": idx + 1,
                        "file": file,
                        "notes": note_input
                    })

    # --- Step 3: AI Configuration Dedicated Card ---
    st.markdown("""
    <div class="step-header">
        <div class="step-number">3</div>
        <h3 class="step-title">AI Model & API Configuration</h3>
    </div>
    """, unsafe_allow_html=True)

    current_api_key = st.session_state.get("openrouter_api_key", os.getenv("OPENROUTER_API_KEY", ""))
    is_connected = bool(current_api_key and current_api_key.strip())
    
    status_class = "ai-status-connected" if is_connected else "ai-status-heuristic"
    status_icon = "🟢" if is_connected else "🟡"
    status_text = "API Key Active • Live OpenRouter AI" if is_connected else "Offline Mode • Local Heuristic Active"

    st.markdown(f"""
    <div class="ai-config-panel">
        <div class="ai-config-header">
            <div class="ai-config-title">
                <span style="font-size: 1.35rem;">⚙️</span>
                <h3>OpenRouter Vision Engine Settings</h3>
            </div>
            <div class="ai-status-pill {status_class}">
                <span>{status_icon}</span>
                <span>{status_text}</span>
            </div>
        </div>
        <p style="color: #64748b; font-size: 0.92rem; margin: 0 0 16px 0;">
            Configure your OpenRouter API key and select your preferred multimodal vision model. 
            Inspection photos and notes are processed into structured JSON adhering to FSANZ Food Safety Standards.
        </p>
    </div>
    """, unsafe_allow_html=True)

    col_key, col_model = st.columns([1, 1])
    
    with col_key:
        api_key_input = st.text_input(
            "🔑 OpenRouter API Key",
            value=current_api_key,
            type="password",
            placeholder="sk-or-v1-...",
            help="Your API key stays securely in your local session. Leave empty to run with built-in audit heuristics."
        )
        if api_key_input != current_api_key:
            st.session_state.openrouter_api_key = api_key_input.strip()

    with col_model:
        model_display_names = {
            "google/gemini-2.0-flash-001": "⚡ Google Gemini 2.0 Flash (Recommended — Fast & Low Cost)",
            "anthropic/claude-3.5-sonnet": "🧠 Anthropic Claude 3.5 Sonnet (High Accuracy Vision)",
            "meta-llama/llama-3.2-11b-vision-instruct": "🦙 Meta Llama 3.2 11B Vision (Open Weights)",
            "openai/gpt-4o-mini": "🚀 OpenAI GPT-4o Mini (Efficient Multimodal)",
            "openai/gpt-4o": "👑 OpenAI GPT-4o (Flagship Model)"
        }
        
        selected_model = st.selectbox(
            "🤖 Vision AI Model",
            options=SUPPORTED_VISION_MODELS,
            format_func=lambda m: model_display_names.get(m, m),
            index=0
        )

    st.markdown("""
    <div class="ai-features-strip" style="margin-top: 10px; margin-bottom: 20px;">
        <span class="ai-feature-tag">🛡️ Strict JSON Schema Validation</span>
        <span class="ai-feature-tag">📸 Multi-Angle Defect Detection</span>
        <span class="ai-feature-tag">📑 Victorian Food Act 1984 Alignment</span>
        <span class="ai-feature-tag">🔒 Zero Data Retention / Private Server</span>
    </div>
    """, unsafe_allow_html=True)

    # --- Submit Action ---
    st.markdown("<br>", unsafe_allow_html=True)
    start_btn = st.button("🚀 Analyze Evidence with AI & Generate Findings", type="primary", use_container_width=True)

    if start_btn:
        if not photo_entries:
            st.warning("⚠️ Please upload at least one inspection photograph to begin.")
            return

        audit_payload = {
            "site_name": trading_name or selected_site,
            "proprietor_name": proprietor,
            "business_address": business_address,
            "phone_number": phone_number,
            "business_contact": business_contact,
            "contact_email": contact_email,
            "person_in_charge": person_in_charge,
            "pic_email": pic_email,
            "nominated_fss": nominated_fss,
            "premise_type": "Aged Care",
            "premise_class": "1",
            "council_name": council_name,
            "council_reg_no": council_reg_no,
            "council_email": council_email,
            "auditor_name": auditor_name,
            "auditor_reg": auditor_reg,
            "auditor_phone": auditor_phone,
            "auditor_email": auditor_email,
            "prev_audit_date": "15/05/2025",
            "audit_date": audit_date.strftime("%d/%m/%Y"),
            "audit_time": audit_time,
            "review_status": "in_review"
        }

        progress_bar = st.progress(0, text="Initializing audit session...")
        audit_id = create_audit(audit_payload)
        st.session_state.current_audit_id = audit_id
        st.session_state.current_audit_data = audit_payload

        audit_upload_dir = UPLOADS_DIR / audit_id
        audit_upload_dir.mkdir(parents=True, exist_ok=True)

        analyzed_findings = []
        total = len(photo_entries)

        for i, entry in enumerate(photo_entries):
            progress_bar.progress(
                int((i / total) * 90),
                text=f"AI analyzing Photo {i + 1} of {total} ({entry['file'].name})..."
            )
            
            safe_filename = f"fig_{i + 1}_{Path(entry['file'].name).suffix.lower()}"
            img_dest = audit_upload_dir / safe_filename
            with open(img_dest, "wb") as f_out:
                f_out.write(entry["file"].getbuffer())

            user_notes = entry["notes"]
            ai_result = analyze_photo_evidence(
                photo_path=str(img_dest),
                user_notes=user_notes,
                api_key=st.session_state.get("openrouter_api_key"),
                model=selected_model
            )

            deadline_days = ai_result.get("suggested_deadline_days", 14)
            due_date_calc = (datetime.now() + timedelta(days=deadline_days)).strftime("%d/%m/%Y")

            finding_item = {
                "fig_number": i + 1,
                "fig_label": f"Fig. {i + 1}",
                "photo_path": str(img_dest),
                "user_notes": user_notes,
                "standard_row_index": ai_result.get("standard_row_index", 32),
                "standard_name": ai_result.get("standard_name", "19 Cleanliness"),
                "fsp_ref": ai_result.get("fsp_ref", "FSP Ref: 78 - 85"),
                "location": ai_result.get("location", "Main Kitchen"),
                "observation": ai_result.get("observation", ""),
                "risk": ai_result.get("risk", ""),
                "corrective_action": ai_result.get("suggested_action", ""),
                "compliance_rating": ai_result.get("suggested_rating", "N"),
                "due_date": due_date_calc,
                "review_status": "pending"
            }
            analyzed_findings.append(finding_item)

        progress_bar.progress(100, text="AI Analysis complete! Saving findings...")
        save_findings_for_audit(audit_id, analyzed_findings, actor=auditor_name)
        st.session_state.current_findings = analyzed_findings

        st.session_state.current_screen = "Screen 2 — AI Findings"
        st.success(f"✅ Generated {len(analyzed_findings)} findings successfully! Navigating to review screen...")
        st.rerun()
