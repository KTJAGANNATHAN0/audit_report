"""
Screen 2 — AI Findings Review & Auditor Approval
Allows auditor to inspect, edit, rate, and approve every finding before generating the report.
Fulfills FR-05, FR-06, and PRD Section 8.
"""

from pathlib import Path
from datetime import datetime, date
import streamlit as st
from PIL import Image
from core.audit_rules import AUDIT_STANDARDS, COMPLIANCE_RATINGS, get_standard_options
from database.db import get_audit, get_findings_for_audit, save_findings_for_audit, update_audit

def render_screen2():
    st.markdown("""
    <div class="hero-banner">
        <div class="hero-badge">Step 2 • Human-in-the-Loop Review</div>
        <h1>Review & Approve AI Audit Findings</h1>
        <p>Inspect AI-extracted evidence, adjust compliance ratings (OBS, N, C, Y), refine corrective actions, and set agreed remediation deadlines.</p>
    </div>
    """, unsafe_allow_html=True)

    audit_id = st.session_state.get("current_audit_id")
    if not audit_id:
        st.warning("⚠️ No active audit session found. Please start a new audit on Screen 1 or select one from History.")
        if st.button("⬅️ Go to Screen 1 (New Audit)"):
            st.session_state.current_screen = "Screen 1 — New Audit"
            st.rerun()
        return

    audit = get_audit(audit_id)
    findings = st.session_state.get("current_findings") or get_findings_for_audit(audit_id)

    if not findings:
        st.info("No findings found for this audit session. Please return to Screen 1 to upload photos.")
        return

    # Header pill
    st.markdown(f"""
    <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 12px 20px; margin-bottom: 24px; display: flex; flex-wrap: wrap; gap: 16px; align-items: center;">
        <div><span style="color: #64748b; font-size: 0.8rem; font-weight: 700; text-transform: uppercase;">Audit Session:</span> <code style="color: #0284c7; font-weight: 700;">{audit_id}</code></div>
        <div><span style="color: #64748b; font-size: 0.8rem; font-weight: 700; text-transform: uppercase;">Facility:</span> <b style="color: #0f172a;">{audit.get('site_name')}</b></div>
        <div><span style="color: #64748b; font-size: 0.8rem; font-weight: 700; text-transform: uppercase;">Inspection Date:</span> <b style="color: #0f172a;">{audit.get('audit_date')}</b></div>
        <div><span style="color: #64748b; font-size: 0.8rem; font-weight: 700; text-transform: uppercase;">Auditor:</span> <b style="color: #0f172a;">{audit.get('auditor_name')}</b></div>
    </div>
    """, unsafe_allow_html=True)
    
    # Quick Summary Metrics
    c_count = sum(1 for f in findings if f.get("compliance_rating") == "C")
    n_count = sum(1 for f in findings if f.get("compliance_rating") == "N")
    obs_count = sum(1 for f in findings if f.get("compliance_rating") == "OBS")
    y_count = sum(1 for f in findings if f.get("compliance_rating") == "Y")
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Critical Deficiencies (C)", c_count)
    m2.metric("Non-Critical (N)", n_count)
    m3.metric("Observations (OBS)", obs_count)
    m4.metric("Compliant Items (Y)", y_count)

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    standard_options = get_standard_options()
    std_row_indices = [opt[0] for opt in standard_options]

    updated_findings = []
    
    for idx, f in enumerate(findings):
        fig_label = f.get("fig_label") or f"Fig. {idx + 1}"
        current_rating = f.get("compliance_rating", "N")
        badge_class = f"badge-{current_rating.lower()}"
        
        with st.container(border=True):
            st.markdown(f"""
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <h3 style="margin: 0; font-size: 1.2rem; color: #0f172a;">{fig_label} — Evidence Finding</h3>
                <span class="badge {badge_class}">{current_rating}</span>
            </div>
            """, unsafe_allow_html=True)
            
            col_img, col_details = st.columns([1, 2])
            
            with col_img:
                photo_path = f.get("photo_path")
                if photo_path and Path(photo_path).exists():
                    img = Image.open(photo_path)
                    st.image(img, caption=f"{fig_label}", use_container_width=True)
                else:
                    st.warning("Photo unavailable")
                    
                st.markdown(f"""
                <div style="background: #f8fafc; border-radius: 8px; padding: 10px; margin-top: 8px; font-size: 0.85rem; border: 1px solid #e2e8f0;">
                    <span style="color: #64748b; font-weight: 600;">Auditor Notes:</span><br>
                    <span style="color: #1e293b;">{f.get('user_notes', 'N/A')}</span>
                </div>
                """, unsafe_allow_html=True)
                
            with col_details:
                # 1. Mapped Standard
                current_row_idx = f.get("standard_row_index", 32)
                try:
                    default_opt_index = std_row_indices.index(current_row_idx)
                except ValueError:
                    default_opt_index = 0

                selected_opt = st.selectbox(
                    f"Mapped Standard for {fig_label}:",
                    range(len(standard_options)),
                    format_func=lambda i: standard_options[i][1],
                    index=default_opt_index,
                    key=f"std_select_{idx}"
                )
                chosen_row_idx = std_row_indices[selected_opt]
                
                c_loc, c_rate = st.columns([1, 1])
                with c_loc:
                    loc_val = st.text_input(
                        "Location / Department Area:",
                        value=f.get("location", "Main Kitchen"),
                        key=f"loc_{idx}"
                    )
                with c_rate:
                    rating_val = st.selectbox(
                        "Compliance Rating Classification:",
                        options=["OBS", "N", "C", "Y"],
                        index=["OBS", "N", "C", "Y"].index(f.get("compliance_rating", "N")),
                        key=f"rating_{idx}",
                        help="OBS: Observation | N: Non-Critical Deficiency | C: Critical Deficiency | Y: Compliant"
                    )

                # 2. Observation
                obs_val = st.text_area(
                    "Factual Evidence Statement (Inserted into Regis Report):",
                    value=f.get("observation", ""),
                    key=f"obs_{idx}",
                    height=85
                )
                
                # 3. Risk Statement
                risk_val = st.text_input(
                    "Food Safety Hazard & Contamination Risk:",
                    value=f.get("risk", ""),
                    key=f"risk_{idx}"
                )

                # 4. Corrective Action & Deadline
                c_act, c_due = st.columns([2, 1])
                with c_act:
                    action_val = st.text_area(
                        "Mandated Corrective Action:",
                        value=f.get("corrective_action", ""),
                        key=f"action_{idx}",
                        height=75
                    )
                with c_due:
                    due_val = st.text_input(
                        "Agreed Deadline:",
                        value=f.get("due_date", "28/08/2026"),
                        key=f"due_{idx}"
                    )

                is_approved = st.checkbox(
                    "✓ Verified & Approved by Auditor",
                    value=f.get("review_status") == "approved",
                    key=f"approved_{idx}"
                )

            updated_finding_item = {
                "fig_number": idx + 1,
                "fig_label": fig_label,
                "photo_path": f.get("photo_path"),
                "user_notes": f.get("user_notes"),
                "standard_row_index": chosen_row_idx,
                "standard_name": standard_options[selected_opt][1],
                "location": loc_val,
                "observation": obs_val,
                "risk": risk_val,
                "corrective_action": action_val,
                "compliance_rating": rating_val,
                "due_date": due_val,
                "review_status": "approved" if is_approved else "pending"
            }
            updated_findings.append(updated_finding_item)

    st.markdown("<br>", unsafe_allow_html=True)
    
    col_save, col_approve_all, col_next = st.columns([1, 1, 1])
    
    with col_save:
        if st.button("💾 Save Findings Draft", use_container_width=True):
            save_findings_for_audit(audit_id, updated_findings, actor=audit.get("auditor_name", "Auditor"))
            st.session_state.current_findings = updated_findings
            st.success("Findings saved successfully!")

    with col_approve_all:
        if st.button("✓ Approve All Findings", use_container_width=True):
            for uf in updated_findings:
                uf["review_status"] = "approved"
            save_findings_for_audit(audit_id, updated_findings, actor=audit.get("auditor_name", "Auditor"))
            st.session_state.current_findings = updated_findings
            st.success("All findings marked as approved!")
            st.rerun()

    with col_next:
        if st.button("➡️ Proceed to Report Preview & Sign-off", type="primary", use_container_width=True):
            save_findings_for_audit(audit_id, updated_findings, actor=audit.get("auditor_name", "Auditor"))
            st.session_state.current_findings = updated_findings
            st.session_state.current_screen = "Screen 3 — Report Preview"
            st.rerun()
