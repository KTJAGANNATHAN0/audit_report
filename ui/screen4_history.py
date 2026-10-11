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
        <div class="hero-badge">Step 4 • Historical Archives & Audit Trail</div>
        <h1>Audit Report Archives & Governance</h1>
        <p>Search previous audits, review compliance status, verify immutable revision logs, and re-download certified PDF and Word reports.</p>
    </div>
    """, unsafe_allow_html=True)

    # 1. Search and Filter Bar
    c_search, c_filter = st.columns([3, 1])
    with c_search:
        search_query = st.text_input("🔍 Search Audits by Facility Name, Audit ID, or Auditor", "")
    with c_filter:
        status_filter = st.selectbox("Filter by Status", ["All", "approved", "in_review", "draft"])

    # 2. Retrieve Audits
    all_audits = get_all_audits(search_query=search_query.strip() if search_query else None)
    if status_filter != "All":
        all_audits = [a for a in all_audits if a.get("review_status") == status_filter]

    if not all_audits:
        st.info("No audit reports found matching your search. Return to Screen 1 to conduct a new audit.")
        return

    st.markdown(f"**Found {len(all_audits)} Historical Audit Report(s)**")

    for audit in all_audits:
        audit_id = audit["audit_id"]
        findings = get_findings_for_audit(audit_id)
        
        status = audit.get("review_status", "draft")
        badge_class = "badge-y" if status == "approved" else "badge-obs" if status == "in_review" else "badge-n"

        with st.container(border=True):
            col_info, col_stats, col_actions = st.columns([3, 2, 2])
            
            with col_info:
                st.markdown(f"### {audit.get('site_name', 'Audit')} — `{audit_id}`")
                st.write(f"📅 **Date:** {audit.get('audit_date')} | 👤 **Auditor:** {audit.get('auditor_name')}")
                st.markdown(
                    f"**Status:** <span class='badge {badge_class}'>{status.upper()}</span>",
                    unsafe_allow_html=True
                )
                if audit.get("approved_at"):
                    st.caption(f"Certified: {audit.get('approved_at')[:19]}")

            with col_stats:
                st.markdown("**Evidence Breakdown:**")
                c_cnt = sum(1 for f in findings if f.get("compliance_rating") == "C")
                n_cnt = sum(1 for f in findings if f.get("compliance_rating") == "N")
                obs_cnt = sum(1 for f in findings if f.get("compliance_rating") == "OBS")
                
                st.write(f"• Total Photos: **{len(findings)}**")
                st.write(f"• Deficiencies: **{n_cnt} N** • **{c_cnt} C**")
                st.write(f"• Opportunities: **{obs_cnt} OBS**")

            with col_actions:
                st.markdown("**Deliverables:**")
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
                    st.success(f"Audit {audit_id} loaded into reviewer!")
                    st.rerun()

            # Revision history trail (FR-12)
            with st.expander("🕒 View Revision Governance Log", expanded=False):
                history = get_audit_history(audit_id)
                if history:
                    for h in history:
                        st.markdown(f"• **{h['timestamp'][:19]}** — `{h['action']}` by *{h['actor']}*: {h['details']}")
                else:
                    st.write("No audit revisions logged.")
