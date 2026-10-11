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
        <h1>🔍 Review & Approve AI Findings</h1>
        <p>Human oversight is required. Verify each observation, corrective action, compliance rating (OBS, N, C, Y), and completion deadline.</p>
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
        st.info("No findings found for this audit. You can add one or return to Screen 1.")
        return

    st.markdown(f"**Audit ID:** `{audit_id}` | **Facility:** `{audit.get('site_name')}` | **Date:** `{audit.get('audit_date')}`")
    
    # Quick Summary Bar
    c_count = sum(1 for f in findings if f.get("compliance_rating") == "C")
    n_count = sum(1 for f in findings if f.get("compliance_rating") == "N")
    obs_count = sum(1 for f in findings if f.get("compliance_rating") == "OBS")
    y_count = sum(1 for f in findings if f.get("compliance_rating") == "Y")
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Critical (C)", c_count)
    m2.metric("Non-Critical (N)", n_count)
    m3.metric("Observations (OBS)", obs_count)
    m4.metric("Compliant (Y)", y_count)

    st.markdown("---")

    standard_options = get_standard_options()
    # Lookup map for options
    std_row_indices = [opt[0] for opt in standard_options]

    updated_findings = []
    
    for idx, f in enumerate(findings):
        fig_label = f.get("fig_label") or f"Fig. {idx + 1}"
        
        with st.container(border=True):
            st.markdown(f"### {fig_label} — Evidence & Finding Details")
            
            col_img, col_details = st.columns([1, 2])
            
            with col_img:
                photo_path = f.get("photo_path")
                if photo_path and Path(photo_path).exists():
                    img = Image.open(photo_path)
                    st.image(img, caption=f"{fig_label}", use_container_width=True)
                else:
                    st.warning("Photo not found")
                    
                st.caption(f"**Auditor Note:** {f.get('user_notes', 'N/A')}")
                
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
                        "Location / Department",
                        value=f.get("location", "Main Kitchen"),
                        key=f"loc_{idx}"
                    )
                with c_rate:
                    rating_val = st.selectbox(
                        "Compliance Rating",
                        options=["OBS", "N", "C", "Y"],
                        index=["OBS", "N", "C", "Y"].index(f.get("compliance_rating", "N")),
                        key=f"rating_{idx}",
                        help="OBS: Observation | N: Non-Critical Deficiency | C: Critical Deficiency | Y: Compliant"
                    )

                # 2. Observation
                obs_val = st.text_area(
                    "Visible Evidence / Observation (Factual description):",
                    value=f.get("observation", ""),
                    key=f"obs_{idx}",
                    height=90
                )
                
                # 3. Risk Statement
                risk_val = st.text_input(
                    "Food Safety Hazard / Risk Statement:",
                    value=f.get("risk", ""),
                    key=f"risk_{idx}"
                )

                # 4. Corrective Action & Deadline
                c_act, c_due = st.columns([2, 1])
                with c_act:
                    action_val = st.text_area(
                        "Corrective Action Required:",
                        value=f.get("corrective_action", ""),
                        key=f"action_{idx}",
                        height=80
                    )
                with c_due:
                    due_val = st.text_input(
                        "Agreed Deadline (DD/MM/YYYY):",
                        value=f.get("due_date", "28/08/2026"),
                        key=f"due_{idx}"
                    )

                # Auditor approval toggle for this finding
                is_approved = st.checkbox(
                    "✓ Verified and Approved by Auditor",
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
