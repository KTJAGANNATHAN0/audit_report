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

def render_screen3():
    st.markdown("""
    <div class="hero-banner">
        <div class="hero-badge">Step 3 • Report Verification & Final Export</div>
        <h1>Report Preview & Compliance Sign-off</h1>
        <p>Review the populated Regis template tables, execute quality assurance checks, and generate the official PDF & Word audit report.</p>
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

    # 1. Validation Engine Checklist (FR-09)
    val_result = validate_audit_report(audit, findings)
    
    if val_result["is_valid"]:
        st.markdown("""
        <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 12px; padding: 14px 20px; margin-bottom: 24px; display: flex; align-items: center; gap: 12px;">
            <div style="font-size: 1.4rem;">✅</div>
            <div>
                <strong style="color: #15803d; font-size: 1.02rem;">Validation Passed: Report Ready for Issuance</strong>
                <p style="margin: 2px 0 0 0; color: #475569; font-size: 0.88rem;">All required Regis report metadata, ratings, corrective actions, and evidence photos are fully verified.</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="background: #fef2f2; border: 1px solid #fecaca; border-radius: 12px; padding: 14px 20px; margin-bottom: 24px;">
            <strong style="color: #b91c1c; font-size: 1.02rem;">❌ {val_result['error_count']} Required Field Error(s) Found</strong>
            <p style="margin: 4px 0 0 0; color: #475569; font-size: 0.88rem;">Please correct the highlighted items before formal approval.</p>
        </div>
        """, unsafe_allow_html=True)
        for err in val_result["errors"]:
            st.markdown(f"• **{err['field']}**: {err['message']}")

    if val_result["warnings"]:
        with st.expander(f"⚠️ {len(val_result['warnings'])} Advisory Notices", expanded=False):
            for w in val_result["warnings"]:
                st.write(f"• {w['message']}")

    # 2. Executive KPI Metrics
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

    # 3. Interactive Document Sections Preview
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

    # 4. Formal Sign-off and Report Generation
    st.markdown("---")
    st.markdown("### ✍️ Auditor Legal Sign-off & Generation")
    
    decl_check = st.checkbox(
        "I declare that the information stated by me in this report is true and correct to the best of my knowledge and does not contain anything false or misleading.",
        value=audit.get("review_status") == "approved"
    )

    col_btn1, col_btn2 = st.columns([1, 1])
    
    with col_btn1:
        approve_and_generate = st.button(
            "🚀 Approve & Generate Final Regis Report",
            type="primary",
            use_container_width=True,
            disabled=not (val_result["is_valid"] and decl_check)
        )

    if approve_and_generate:
        with st.spinner("Populating Regis Word template and converting to PDF..."):
            today_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            clean_site_name = "".join(c for c in audit.get("site_name", "Report") if c.isalnum() or c in (" ", "_")).strip().replace(" ", "_")
            
            docx_filename = f"Regis_Audit_Report_{clean_site_name}_{today_str}.docx"
            pdf_filename = f"Regis_Audit_Report_{clean_site_name}_{today_str}.pdf"
            
            docx_path = str(OUTPUTS_DIR / docx_filename)
            pdf_path = str(OUTPUTS_DIR / pdf_filename)

            # 1. Generate DOCX
            generate_audit_docx(audit, findings, docx_path)
            
            # 2. Convert to PDF
            success, final_pdf_path, err_msg = convert_docx_to_pdf(docx_path, pdf_path)

            now_iso = datetime.now().isoformat()
            updates = {
                "review_status": "approved",
                "approved_by": audit.get("auditor_name"),
                "approved_at": now_iso,
                "docx_path": docx_path
            }
            if success:
                updates["pdf_path"] = final_pdf_path
                log_audit_history(audit_id, "PDF_GENERATED", audit.get("auditor_name"), f"Generated {pdf_filename}")
            else:
                log_audit_history(audit_id, "PDF_GENERATION_FAILED", audit.get("auditor_name"), err_msg)
                
            update_audit(audit_id, updates, actor=audit.get("auditor_name"))
            st.session_state.current_audit_data = get_audit(audit_id)
            
            st.success("🎉 Official Regis Audit Report generated and certified!")
            st.rerun()

    # Download section
    updated_audit = get_audit(audit_id)
    doc_path = updated_audit.get("docx_path")
    pdf_p = updated_audit.get("pdf_path")

    if doc_path and Path(doc_path).exists():
        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        st.markdown("### 📥 Download Official Audit Deliverables")
        d_col1, d_col2 = st.columns(2)
        
        with d_col1:
            if pdf_p and Path(pdf_p).exists():
                with open(pdf_p, "rb") as f_pdf:
                    st.download_button(
                        label="📄 Download Official PDF Report",
                        data=f_pdf.read(),
                        file_name=Path(pdf_p).name,
                        mime="application/pdf",
                        use_container_width=True,
                        type="primary"
                    )
            else:
                st.warning("PDF version is processing or unavailable.")

        with d_col2:
            with open(doc_path, "rb") as f_doc:
                st.download_button(
                    label="📝 Download Word Document (.docx)",
                    data=f_doc.read(),
                    file_name=Path(doc_path).name,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True
                )
