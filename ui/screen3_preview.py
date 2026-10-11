"""
Screen 3 — Report Preview, Validation & Export
Performs required fields validation, document preview, formal approval, and exports DOCX & PDF.
Fulfills FR-07, FR-08, FR-09, and PRD Section 8.
"""

from pathlib import Path
from datetime import datetime
import streamlit as st
from PIL import Image
from core.config import OUTPUTS_DIR
from core.validator import validate_audit_report
from core.docx_engine import generate_audit_docx
from core.pdf_converter import convert_docx_to_pdf
from core.audit_rules import AUDIT_STANDARDS
from database.db import get_audit, get_findings_for_audit, update_audit, log_audit_history

def ensure_report_files(audit, findings):
    """Ensures that both DOCX and PDF deliverables exist for this audit session."""
    doc_path = audit.get("docx_path")
    pdf_path = audit.get("pdf_path")
    
    needs_gen = False
    if not doc_path or not Path(doc_path).exists():
        needs_gen = True
    if not pdf_path or not Path(pdf_path).exists():
        needs_gen = True
        
    if needs_gen and findings:
        clean_site_name = "".join(c for c in audit.get("site_name", "Report") if c.isalnum() or c in (" ", "_")).strip().replace(" ", "_")
        audit_id_clean = audit.get("audit_id", "AUDIT").replace("-", "_")
        docx_filename = f"Regis_Audit_Report_{clean_site_name}_{audit_id_clean}.docx"
        pdf_filename = f"Regis_Audit_Report_{clean_site_name}_{audit_id_clean}.pdf"
        
        doc_path = str(OUTPUTS_DIR / docx_filename)
        pdf_path = str(OUTPUTS_DIR / pdf_filename)
        
        try:
            generate_audit_docx(audit, findings, doc_path)
            success, final_pdf, err = convert_docx_to_pdf(doc_path, pdf_path)
            
            updates = {"docx_path": doc_path}
            if success and Path(final_pdf).exists():
                updates["pdf_path"] = final_pdf
            update_audit(audit["audit_id"], updates, actor="System")
            audit["docx_path"] = doc_path
            if success:
                audit["pdf_path"] = final_pdf
        except Exception as e:
            st.error(f"Error generating baseline report files: {e}")
            
    return audit

def render_screen3():
    st.markdown("""
    <div class="hero-banner">
        <div class="hero-badge">Step 3 • Report Verification & Direct Downloads</div>
        <h1>Report Preview & Instant Deliverables</h1>
        <p>Review the populated Regis template tables, execute quality assurance checks, and download your official PDF and Word audit reports.</p>
    </div>
    """, unsafe_allow_html=True)

    audit_id = st.session_state.get("current_audit_id")
    if not audit_id:
        st.warning("⚠️ No active audit selected. Please start a new audit or select one from History.")
        if st.button("⬅️ Go to Screen 1"):
            st.session_state.current_screen = "Screen 1 — New Audit"
            st.rerun()
        return

    audit = get_audit(audit_id)
    findings = st.session_state.get("current_findings") or get_findings_for_audit(audit_id)

    # Automatically ensure files are ready for instant download
    audit = ensure_report_files(audit, findings)

    # 1. Prominent Instant Download Card at Top
    st.markdown("""
    <div style="background: #ffffff; border: 2px solid #0284c7; border-radius: 14px; padding: 20px 24px; margin-bottom: 24px; box-shadow: 0 4px 14px rgba(2, 132, 199, 0.1);">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; margin-bottom: 14px;">
            <div>
                <h3 style="margin: 0; font-size: 1.25rem; font-weight: 800; color: #0f172a;">📥 Download Official Deliverables</h3>
                <span style="color: #64748b; font-size: 0.88rem;">Preserves exact Regis template layout, fonts, compliance tables, and 4-column photo grid.</span>
            </div>
            <span class="badge badge-y">Ready for Download</span>
        </div>
    """, unsafe_allow_html=True)

    col_dl1, col_dl2, col_regen = st.columns([2, 2, 1.5])
    
    doc_path = audit.get("docx_path")
    pdf_path = audit.get("pdf_path")

    with col_dl1:
        if pdf_path and Path(pdf_path).exists():
            with open(pdf_path, "rb") as f_pdf:
                st.download_button(
                    label="📄 Download Official PDF Report",
                    data=f_pdf.read(),
                    file_name=Path(pdf_path).name,
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary",
                    key="top_dl_pdf_btn"
                )
        else:
            if st.button("📄 Generate & Download PDF", type="primary", use_container_width=True, key="gen_pdf_btn"):
                with st.spinner("Converting report to PDF via LibreOffice..."):
                    clean_site_name = "".join(c for c in audit.get("site_name", "Report") if c.isalnum() or c in (" ", "_")).strip().replace(" ", "_")
                    docx_fn = str(OUTPUTS_DIR / f"Regis_Audit_Report_{clean_site_name}_{audit_id}.docx")
                    pdf_fn = str(OUTPUTS_DIR / f"Regis_Audit_Report_{clean_site_name}_{audit_id}.pdf")
                    generate_audit_docx(audit, findings, docx_fn)
                    success, final_pdf, err = convert_docx_to_pdf(docx_fn, pdf_fn)
                    update_audit(audit_id, {"docx_path": docx_fn, "pdf_path": pdf_fn}, actor="Auditor")
                    st.success("PDF generated! Click again to download.")
                    st.rerun()

    with col_dl2:
        if doc_path and Path(doc_path).exists():
            with open(doc_path, "rb") as f_doc:
                st.download_button(
                    label="📝 Download Word Document (.docx)",
                    data=f_doc.read(),
                    file_name=Path(doc_path).name,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                    key="top_dl_doc_btn"
                )
        else:
            if st.button("📝 Generate Word Document (.docx)", use_container_width=True, key="gen_doc_btn"):
                with st.spinner("Building Word document from Regis template..."):
                    clean_site_name = "".join(c for c in audit.get("site_name", "Report") if c.isalnum() or c in (" ", "_")).strip().replace(" ", "_")
                    docx_fn = str(OUTPUTS_DIR / f"Regis_Audit_Report_{clean_site_name}_{audit_id}.docx")
                    generate_audit_docx(audit, findings, docx_fn)
                    update_audit(audit_id, {"docx_path": docx_fn}, actor="Auditor")
                    st.success("Word report generated! Click again to download.")
                    st.rerun()

    with col_regen:
        if st.button("🔄 Refresh Files", use_container_width=True, help="Regenerates Word and PDF with your latest edits"):
            with st.spinner("Refreshing deliverables..."):
                clean_site_name = "".join(c for c in audit.get("site_name", "Report") if c.isalnum() or c in (" ", "_")).strip().replace(" ", "_")
                docx_fn = str(OUTPUTS_DIR / f"Regis_Audit_Report_{clean_site_name}_{audit_id}.docx")
                pdf_fn = str(OUTPUTS_DIR / f"Regis_Audit_Report_{clean_site_name}_{audit_id}.pdf")
                generate_audit_docx(audit, findings, docx_fn)
                convert_docx_to_pdf(docx_fn, pdf_fn)
                update_audit(audit_id, {"docx_path": docx_fn, "pdf_path": pdf_fn}, actor="Auditor")
                st.success("Deliverables updated!")
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

    # 2. Validation Engine Checklist (FR-09)
    val_result = validate_audit_report(audit, findings)
    
    if val_result["is_valid"]:
        st.markdown("""
        <div style="background: #f0fdf4; border: 1.5px solid #86efac; border-radius: 12px; padding: 14px 20px; margin-bottom: 24px; display: flex; align-items: center; gap: 12px;">
            <div style="font-size: 1.4rem;">✅</div>
            <div>
                <strong style="color: #15803d; font-size: 1.02rem;">Validation Passed: Report Meets All Regis Audit Criteria</strong>
                <p style="margin: 2px 0 0 0; color: #475569; font-size: 0.88rem;">All required facility metadata, ratings, corrective actions, and evidence photos are fully verified.</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="background: #fef2f2; border: 1.5px solid #fca5a5; border-radius: 12px; padding: 14px 20px; margin-bottom: 24px;">
            <strong style="color: #b91c1c; font-size: 1.02rem;">❌ {val_result['error_count']} Required Field Warning(s)</strong>
            <p style="margin: 4px 0 0 0; color: #475569; font-size: 0.88rem;">Review the items below. Reports can still be generated and reviewed.</p>
        </div>
        """, unsafe_allow_html=True)
        for err in val_result["errors"]:
            st.markdown(f"• **{err['field']}**: {err['message']}")

    # 3. Executive KPI Metrics
    total_findings = len(findings)
    c_count = sum(1 for f in findings if f.get("compliance_rating") == "C")
    n_count = sum(1 for f in findings if f.get("compliance_rating") == "N")
    obs_count = sum(1 for f in findings if f.get("compliance_rating") == "OBS")
    compliant_count = 45 - (c_count + n_count + obs_count)
    
    col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
    col_m1.metric("Evidence Photos", total_findings)
    col_m2.metric("Critical (C)", c_count)
    col_m3.metric("Non-Critical (N)", n_count)
    col_m4.metric("Observations (OBS)", obs_count)
    col_m5.metric("Compliant Clauses", compliant_count)

    st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

    # 4. Interactive Document Sections Preview
    st.markdown("### 📋 Document Sections Live Preview")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🏢 1. Facility Details",
        "👨‍⚖️ 2. Auditor & Scope",
        "📊 3. Checklist Matrix (Table 4)",
        "🖼️ 4. Evidence Gallery (Table 5)",
        "📝 5. Conclusion (Table 6)"
    ])

    with tab1:
        st.markdown(f"""
        | Field | Official Value |
        | :--- | :--- |
        | **Proprietor Name** | {audit.get('proprietor_name')} |
        | **Trading Name / Facility** | {audit.get('site_name')} |
        | **Business Address** | {audit.get('business_address')} |
        | **Phone Number** | {audit.get('phone_number')} |
        | **Business Contact** | {audit.get('business_contact')} ({audit.get('contact_email')}) |
        | **Person in Charge** | {audit.get('person_in_charge')} ({audit.get('pic_email')}) |
        | **Nominated FSS** | {audit.get('nominated_fss')} |
        | **Council Authority** | {audit.get('council_name')} (Registration: {audit.get('council_reg_no')}) |
        """)

    with tab2:
        st.markdown(f"""
        | Field | Official Value |
        | :--- | :--- |
        | **Auditor Name** | {audit.get('auditor_name')} |
        | **DHHS Registration No.** | {audit.get('auditor_reg')} |
        | **Auditor Contact** | {audit.get('auditor_phone')} • {audit.get('auditor_email')} |
        | **Audit Inspection Date** | {audit.get('audit_date')} at {audit.get('audit_time')} |
        | **Previous Audit Date** | {audit.get('prev_audit_date')} |
        | **Scope & Objective** | {audit.get('scope_objective', 'Third Party Food Safety Audit under FSANZ Standards & Vic Food Act 1984.')} |
        | **Type of Audit** | {audit.get('audit_type')} |
        """)

    with tab3:
        st.write("Summary of items with identified findings & actions:")
        findings_by_row = {}
        for f in findings:
            r_idx = f.get("standard_row_index")
            if r_idx is not None:
                findings_by_row.setdefault(r_idx, []).append(f)

        standards_map = {s["row_index"]: s for s in AUDIT_STANDARDS}

        for r_idx, row_findings in findings_by_row.items():
            std = standards_map.get(r_idx, {})
            title = f"Row {r_idx}: {std.get('activity', 'Standard')} - {std.get('sub_activity', '')}"
            with st.container(border=True):
                st.markdown(f"**{title}** `({std.get('fsp_ref', '')})`")
                for f in row_findings:
                    badge_class = f"badge-{f.get('compliance_rating', 'n').lower()}"
                    st.markdown(
                        f"<span class='badge {badge_class}'>{f.get('compliance_rating')}</span> "
                        f"**{f.get('fig_label')}:** {f.get('observation')}",
                        unsafe_allow_html=True
                    )
                    st.write(f"👉 **Action Required:** {f.get('corrective_action')}")
                    st.caption(f"📅 Remediation Deadline: {f.get('due_date')} | Area: {f.get('location')}")

        st.caption("All remaining 40+ standard rows default to Compliant (Y) with certified food safety practices.")

    with tab4:
        st.write("Evidence Photo Grid (matches the 4-column layout of the Regis template):")
        cols = st.columns(4)
        for idx, f in enumerate(findings):
            col = cols[idx % 4]
            with col:
                photo_path = f.get("photo_path")
                if photo_path and Path(photo_path).exists():
                    img = Image.open(photo_path)
                    st.image(img, caption=f.get("fig_label", f"Fig. {idx + 1}"), use_container_width=True)

    with tab5:
        conclusion_val = st.text_area(
            "Executive Audit Conclusion (Table 6 in Document):",
            value=audit.get("audit_conclusion") or (
                f"The facility demonstrated several positive food safety practices, including regular food safety records "
                f"and dedicated storage arrangements. Staff were observed to have access to necessary equipment. "
                f"However, the audit identified {n_count} non-conformance(s) and {obs_count} observation(s) requiring prompt "
                f"rectification to ensure ongoing compliance with Food Standards Australia New Zealand (FSANZ) Food Safety Standards. "
                f"Thanking {audit.get('business_contact', 'the team')} and the team at {audit.get('site_name')} for their cooperation."
            ),
            height=125
        )
        if conclusion_val != audit.get("audit_conclusion"):
            update_audit(audit_id, {"audit_conclusion": conclusion_val}, actor=audit.get("auditor_name", "Auditor"))

    # 5. Formal Certification & Status Update
    st.markdown("---")
    st.markdown("### ✍️ Formal Audit Sign-off")
    
    decl_check = st.checkbox(
        "I declare that the information stated by me in this report is true and correct to the best of my knowledge and does not contain anything false or misleading.",
        value=audit.get("review_status") == "approved"
    )

    if st.button("✅ Certify & Mark Report as Approved", type="secondary", use_container_width=True):
        update_audit(audit_id, {
            "review_status": "approved",
            "approved_by": audit.get("auditor_name"),
            "approved_at": datetime.now().isoformat()
        }, actor=audit.get("auditor_name"))
        st.success("🎉 Audit marked as Approved! Re-download or refresh your files above.")
        st.rerun()
