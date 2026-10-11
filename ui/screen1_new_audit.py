"""
Screen 1 — New Audit
Select audit date and site, upload photos, enter short notes/keywords, and submit for AI analysis.
Fulfills FR-01, FR-02, FR-03, and PRD Section 8.
"""

import os
import shutil
from pathlib import Path
from datetime import datetime, date
import streamlit as st
from PIL import Image
from core.config import REGIS_SITES, DEFAULT_AUDITOR, UPLOADS_DIR, SUPPORTED_VISION_MODELS, DEFAULT_VISION_MODEL, OPENROUTER_API_KEY
from core.ai_service import analyze_photo_evidence
from database.db import create_audit, save_findings_for_audit

SAMPLE_NOTE_TEMPLATES = [
    "Dirty microwave, food residue on top interior, clean immediately.",
    "Canopy filters greasy, oil residue buildup above cooking range.",
    "Exposed unsealed timber below servery bench, potential bacterial harbourage.",
    "Hand wash basin obstructed by dishes and cleaning bottles.",
    "Visible mould growth on silicone seals around wash sink.",
    "Uncovered food trays stored in coolroom without date labels.",
    "Dented food can found in dry storage shelving."
]

def render_screen1():
    st.markdown("""
    <div class="hero-banner">
        <h1>📸 New Daily Food Safety Audit</h1>
        <p>Upload inspection photos, enter short keywords, and let OpenRouter AI generate structured findings mapped directly to the Regis Audit Standard.</p>
    </div>
    """, unsafe_allow_html=True)

    # 1. Site and Audit Details
    with st.expander("🏢 Audit Header & Facility Details", expanded=True):
        col_site, col_date = st.columns([2, 1])
        
        site_names = [s["site_name"] for s in REGIS_SITES] + ["Other / Custom Site..."]
        
        # Check session defaults
        current_site_name = st.session_state.get("audit_site_name", site_names[0])
        site_idx = site_names.index(current_site_name) if current_site_name in site_names else 0
        
        with col_site:
            selected_site = st.selectbox("Select Regis Facility", site_names, index=site_idx)
            
        with col_date:
            audit_date = st.date_input("Audit Date", value=st.session_state.get("audit_date_val", date.today()))
            audit_time = st.text_input("Audit Time", value=st.session_state.get("audit_time_val", "9:30am"))

        # Look up preset site details
        site_preset = next((s for s in REGIS_SITES if s["site_name"] == selected_site), None)
        
        c1, c2, c3 = st.columns(3)
        with c1:
            proprietor = st.text_input("Proprietor Name", value=site_preset["proprietor_name"] if site_preset else "Regis Aged Care")
            trading_name = st.text_input("Trading Name", value=selected_site if selected_site != "Other / Custom Site..." else "")
            business_address = st.text_input("Business Address", value=site_preset["business_address"] if site_preset else "")
            phone_number = st.text_input("Phone Number", value=site_preset["phone_number"] if site_preset else "")

        with c2:
            business_contact = st.text_input("Business Contact", value=site_preset["business_contact"] if site_preset else "Bryan Seeborun")
            contact_email = st.text_input("Contact Email", value=site_preset["contact_email"] if site_preset else "bseeborun@regis.com.au")
            person_in_charge = st.text_input("Person in Charge", value=site_preset["person_in_charge"] if site_preset else "Site Manager")
            pic_email = st.text_input("PIC Email", value=site_preset["pic_email"] if site_preset else "")

        with c3:
            nominated_fss = st.text_input("Nominated FSS", value=site_preset["nominated_fss"] if site_preset else "Sunil Kumar / Damith Yagamuni")
            council_name = st.text_input("Council / Shire", value=site_preset["council_name"] if site_preset else "City of Greater Dandenong")
            council_reg_no = st.text_input("Registration No.", value=site_preset["council_reg_no"] if site_preset else "F-2247 Expiry Date 31/12/2026")
            council_email = st.text_input("Council Email", value=site_preset["council_email"] if site_preset else "council@cgd.vic.gov.au")

        st.markdown("---")
        st.subheader("Auditor Credentials")
        ac1, ac2, ac3, ac4 = st.columns(4)
        with ac1:
            auditor_name = st.text_input("Auditor Name", value=DEFAULT_AUDITOR["name"])
        with ac2:
            auditor_reg = st.text_input("DHHS Reg.", value=DEFAULT_AUDITOR["dhhs_reg"])
        with ac3:
            auditor_phone = st.text_input("Auditor Phone", value=DEFAULT_AUDITOR["phone"])
        with ac4:
            auditor_email = st.text_input("Auditor Email", value=DEFAULT_AUDITOR["email"])

    # 2. Photo Upload & Short Notes Section
    st.markdown("### 📷 2. Audit Evidence: Photos & Observations")
    st.write("Take pictures on mobile or upload audit evidence photos. Enter a quick keyword note for each.")

    uploaded_files = st.file_uploader(
        "Upload one or multiple photos (JPG, PNG, WebP)",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        key="audit_photos_uploader"
    )

    if "photo_notes" not in st.session_state:
        st.session_state.photo_notes = {}

    photo_entries = []
    
    if uploaded_files:
        st.info(f"📁 {len(uploaded_files)} photo(s) selected for this audit. Provide a short note for each below.")
        
        # Display photos in 2-column grid for clean mobile and desktop layout
        cols = st.columns(2)
        for idx, file in enumerate(uploaded_files):
            col = cols[idx % 2]
            with col:
                with st.container(border=True):
                    st.markdown(f"**Evidence Photo #{idx + 1}** — `{file.name}`")
                    img = Image.open(file)
                    st.image(img, use_container_width=True)
                    
                    note_key = f"note_{file.name}_{idx}"
                    default_note = st.session_state.photo_notes.get(note_key, "")
                    
                    # Quick template chips
                    sample_choice = st.selectbox(
                        f"Quick insert template for Photo #{idx + 1}:",
                        ["(Select keyword snippet..."] + SAMPLE_NOTE_TEMPLATES,
                        key=f"sample_{idx}"
                    )
                    if sample_choice and not sample_choice.startswith("("):
                        default_note = sample_choice

                    note_input = st.text_area(
                        f"Short observation / keywords (Photo #{idx + 1})",
                        value=default_note,
                        placeholder="e.g. Dirty microwave, food residue on top interior, clean immediately.",
                        key=note_key,
                        height=80
                    )
                    st.session_state.photo_notes[note_key] = note_input

                    photo_entries.append({
                        "index": idx + 1,
                        "file": file,
                        "notes": note_input
                    })

    # 3. Model & AI Settings
    with st.expander("⚙️ AI Model & API Configuration", expanded=False):
        mc1, mc2 = st.columns([1, 1])
        with mc1:
            api_key_input = st.text_input(
                "OpenRouter API Key",
                value=st.session_state.get("openrouter_api_key", os.getenv("OPENROUTER_API_KEY", "")),
                type="password",
                help="Enter your OpenRouter API key. If omitted, the system will use intelligent offline audit heuristics."
            )
            if api_key_input:
                st.session_state.openrouter_api_key = api_key_input
        with mc2:
            model_options = [
                "google/gemini-2.0-flash-001",
                "meta-llama/llama-3.2-11b-vision-instruct",
                "anthropic/claude-3.5-sonnet",
                "openai/gpt-4o-mini",
                "openai/gpt-4o"
            ]
            selected_model = st.selectbox("Vision AI Model", model_options, index=0)

    # 4. Action Button
    st.markdown("<br>", unsafe_allow_html=True)
    start_btn = st.button("🚀 Analyze Evidence with AI & Generate Findings", type="primary", use_container_width=True)

    if start_btn:
        if not photo_entries:
            st.warning("⚠️ Please upload at least one audit photo to proceed.")
            return

        # Prepare audit record in DB
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

        # Save photos to disk and run AI analysis
        audit_upload_dir = UPLOADS_DIR / audit_id
        audit_upload_dir.mkdir(parents=True, exist_ok=True)

        analyzed_findings = []
        total = len(photo_entries)

        for i, entry in enumerate(photo_entries):
            progress_bar.progress(
                int((i / total) * 90),
                text=f"AI analyzing Photo {i + 1} of {total} ({entry['file'].name})..."
            )
            
            # Save image
            safe_filename = f"fig_{i + 1}_{Path(entry['file'].name).suffix.lower()}"
            img_dest = audit_upload_dir / safe_filename
            with open(img_dest, "wb") as f_out:
                f_out.write(entry["file"].getbuffer())

            # Call AI Vision
            user_notes = entry["notes"]
            ai_result = analyze_photo_evidence(
                photo_path=str(img_dest),
                user_notes=user_notes,
                api_key=st.session_state.get("openrouter_api_key"),
                model=selected_model
            )

            deadline_days = ai_result.get("suggested_deadline_days", 14)
            due_date_str = (datetime.now() + datetime.timedelta(days=deadline_days) if hasattr(datetime, "timedelta") else datetime.now()).strftime("%d/%m/%Y")
            # Calculate due date safely
            from datetime import timedelta
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

        # Transition to Screen 2
        st.session_state.current_screen = "Screen 2 — AI Findings"
        st.success(f"✅ Processed {len(analyzed_findings)} findings successfully! Redirecting to review screen...")
        st.rerun()
