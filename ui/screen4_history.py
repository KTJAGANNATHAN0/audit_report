"""
Screen 4 — Report History & Archives
Search previous audits, check approval status, download reports, and inspect revision history.
Fulfills FR-10, FR-12, and PRD Section 8.
"""

from pathlib import Path
import streamlit as st
from database.db import get_all_audits, get_audit, get_findings_for_audit, get_audit_history

def render_screen4():
    st.markdown("""
    <div class="hero-banner">
        <h1>📚 Audit Report History & Archives</h1>
        <p>Search previous audits, review historical findings, inspect revision timestamps, and re-download generated PDF and Word documents.</p>
    </div>
    """, unsafe_allow_html=True)

    # 1. Search and Filter Bar
    c_search, c_filter = st.columns([3, 1])
    with c_search:
        search_query = st.text_input("🔍 Search Audits by Facility, Audit ID, or Auditor", "")
    with c_filter:
        status_filter = st.selectbox("Status Filter", ["All", "approved", "in_review", "draft"])

    # 2. Retrieve Audits
    all_audits = get_all_audits(search_query=search_query.strip() if search_query else None)
    if status_filter != "All":
        all_audits = [a for a in all_audits if a.get("review_status") == status_filter]

    if not all_audits:
        st.info("No audit reports found matching the criteria. Click 'Screen 1' to create your first audit.")
        return

    st.write(f"Showing **{len(all_audits)}** audit report(s):")

    for audit in all_audits:
        audit_id = audit["audit_id"]
        findings = get_findings_for_audit(audit_id)
        
        status = audit.get("review_status", "draft")
        badge_color = "#16a34a" if status == "approved" else "#d97706" if status == "in_review" else "#64748b"

        with st.container(border=True):
            col_info, col_stats, col_actions = st.columns([3, 2, 2])
            
            with col_info:
                st.markdown(f"### {audit.get('site_name', 'Audit')} — `{audit_id}`")
                st.write(f"📅 **Audit Date:** {audit.get('audit_date')} | 👤 **Auditor:** {audit.get('auditor_name')}")
                st.markdown(
                    f"**Status:** <span style='background-color:{badge_color}22; color:{badge_color}; padding:2px 8px; border-radius:12px; font-weight:700; border:1px solid {badge_color};'>{status.upper()}</span>",
                    unsafe_allow_html=True
                )
                if audit.get("approved_at"):
                    st.caption(f"Approved on: {audit.get('approved_at')[:19]}")

            with col_stats:
                st.markdown("**Findings Breakdown:**")
                c_cnt = sum(1 for f in findings if f.get("compliance_rating") == "C")
                n_cnt = sum(1 for f in findings if f.get("compliance_rating") == "N")
                obs_cnt = sum(1 for f in findings if f.get("compliance_rating") == "OBS")
                
                st.write(f"• Evidence Photos: **{len(findings)}**")
                st.write(f"• Non-Critical (N): **{n_cnt}** | Critical (C): **{c_cnt}**")
                st.write(f"• Observations (OBS): **{obs_cnt}**")

            with col_actions:
                st.markdown("**Downloads & Actions:**")
                pdf_p = audit.get("pdf_path")
                doc_p = audit.get("docx_path")

                if pdf_p and Path(pdf_p).exists():
                    with open(pdf_p, "rb") as f_pdf:
                        st.download_button(
                            "📄 Download PDF",
                            data=f_pdf.read(),
                            file_name=Path(pdf_p).name,
                            mime="application/pdf",
                            key=f"dl_pdf_{audit_id}",
                            use_container_width=True
                        )
                else:
                    st.caption("PDF not generated yet")

                if doc_p and Path(doc_p).exists():
                    with open(doc_p, "rb") as f_doc:
                        st.download_button(
                            "📝 Download DOCX",
                            data=f_doc.read(),
                            file_name=Path(doc_p).name,
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key=f"dl_doc_{audit_id}",
                            use_container_width=True
                        )

                if st.button("✏️ Load in Reviewer", key=f"load_{audit_id}", use_container_width=True):
                    st.session_state.current_audit_id = audit_id
                    st.session_state.current_audit_data = audit
                    st.session_state.current_findings = findings
                    st.session_state.current_screen = "Screen 2 — AI Findings"
                    st.success(f"Loaded audit {audit_id} into reviewer!")
                    st.rerun()

            # Revision history expander (FR-12)
            with st.expander("🕒 View Audit Revision History Trail", expanded=False):
                history = get_audit_history(audit_id)
                if history:
                    for h in history:
                        st.markdown(f"• **{h['timestamp'][:19]}** — `{h['action']}` by *{h['actor']}*: {h['details']}")
                else:
                    st.write("No revision logs recorded yet.")
