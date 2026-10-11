"""
Word Document Generation Engine for Regis Audit Reports.
Preserves existing Regis audit report layout, tables, styles, headers, and FSP references.
Fulfills FR-07, FR-11, and PRD Section 7.
"""

import shutil
from pathlib import Path
from typing import Dict, List, Any
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from core.config import TEMPLATE_PATH
from core.audit_rules import AUDIT_STANDARDS, get_standard_by_row_index

def set_cell_text(cell, text: str, font_size_pt: float = 9.5, bold: bool = False, italic: bool = False):
    """Safely updates text in a table cell while keeping clean formatting."""
    # Clear existing paragraphs except first
    p = cell.paragraphs[0]
    p.text = ""
    # remove any extra paragraphs
    for extra_p in cell.paragraphs[1:]:
        p_elem = extra_p._p
        p_elem.getparent().remove(p_elem)
        
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.15
    run = p.add_run(text)
    run.font.size = Pt(font_size_pt)
    run.font.name = "Arial"
    run.bold = bold
    run.italic = italic

def generate_audit_docx(
    audit_data: Dict[str, Any],
    findings: List[Dict[str, Any]],
    output_path: str,
    template_path: str = None
) -> str:
    """
    Populates a copy of the Regis audit report template with audit_data and findings.
    Preserves all fixed sections, tables, styles, and page layouts.
    """
    src_template = Path(template_path) if template_path else TEMPLATE_PATH
    dest_file = Path(output_path).resolve()
    dest_file.parent.mkdir(parents=True, exist_ok=True)
    
    # 1. Create a working copy of the template
    shutil.copyfile(str(src_template), str(dest_file))
    
    # 2. Open document
    doc = docx.Document(str(dest_file))
    
    # 3. Populate Table 1: Food Business Details
    t1 = doc.tables[0]
    date_time_str = audit_data.get("audit_date_time") or f"{audit_data.get('audit_date', '')} at {audit_data.get('audit_time', '9:30am')}"
    
    set_cell_text(t1.cell(1, 1), audit_data.get("proprietor_name", "Regis Aged Care"))
    set_cell_text(t1.cell(1, 3), date_time_str)
    set_cell_text(t1.cell(2, 1), audit_data.get("site_name", "Regis Dandenong North"))
    set_cell_text(t1.cell(2, 3), audit_data.get("phone_number", "03 9701 1244"))
    set_cell_text(t1.cell(3, 1), audit_data.get("business_address", ""))
    set_cell_text(t1.cell(4, 1), audit_data.get("business_contact", ""))
    set_cell_text(t1.cell(4, 3), audit_data.get("contact_email", ""))
    set_cell_text(t1.cell(5, 1), audit_data.get("person_in_charge", ""))
    set_cell_text(t1.cell(5, 3), audit_data.get("pic_email", ""))
    set_cell_text(t1.cell(6, 1), audit_data.get("nominated_fss", ""))
    set_cell_text(t1.cell(7, 1), audit_data.get("premise_type", "Aged Care"))
    set_cell_text(t1.cell(7, 3), audit_data.get("premise_class", "1"))
    set_cell_text(t1.cell(9, 1), audit_data.get("council_name", "City of Greater Dandenong"))
    set_cell_text(t1.cell(9, 3), audit_data.get("council_reg_no", "F-2247 Expiry Date 31/12/2026"))
    set_cell_text(t1.cell(10, 1), audit_data.get("council_email", "council@cgd.vic.gov.au"))

    # 4. Populate Table 2: Auditor Details
    t2 = doc.tables[1]
    set_cell_text(t2.cell(1, 1), audit_data.get("auditor_name", "Narmada Oogathoo"))
    set_cell_text(t2.cell(1, 3), audit_data.get("auditor_reg", "00224045"))
    set_cell_text(t2.cell(2, 1), audit_data.get("auditor_phone", "+61402701166"))
    set_cell_text(t2.cell(2, 3), audit_data.get("auditor_email", "stryve@outlook.com.au"))

    # 5. Populate Table 3: Audit Details
    t3 = doc.tables[2]
    set_cell_text(t3.cell(1, 1), audit_data.get("prev_audit_date", "15/05/2025"))
    set_cell_text(t3.cell(1, 3), audit_data.get("audit_date", "20/05/2026"))
    if audit_data.get("scope_objective"):
        set_cell_text(t3.cell(2, 1), audit_data.get("scope_objective"))
    if audit_data.get("audit_type"):
        set_cell_text(t3.cell(4, 1), audit_data.get("audit_type"))

    # 6. Group findings by Table 4 row index
    findings_by_row: Dict[int, List[Dict[str, Any]]] = {}
    for f in findings:
        r_idx = f.get("standard_row_index")
        if r_idx is not None:
            r_idx = int(r_idx)
            findings_by_row.setdefault(r_idx, []).append(f)

    # 7. Populate Table 4: Standards Checklist Matrix (57 rows total)
    t4 = doc.tables[3]
    
    # Pre-build lookup of standard items
    standards_map = {s["row_index"]: s for s in AUDIT_STANDARDS}

    for row_idx, std in standards_map.items():
        if row_idx >= len(t4.rows):
            continue
            
        row = t4.rows[row_idx]
        if len(row.cells) < 7:
            continue
            
        row_findings = findings_by_row.get(row_idx, [])
        
        if not row_findings:
            # Compliant standard row
            set_cell_text(row.cells[3], "Y", font_size_pt=9.5, bold=True)
            set_cell_text(row.cells[4], std["default_compliant_text"], font_size_pt=9)
            set_cell_text(row.cells[5], "", font_size_pt=9)
            set_cell_text(row.cells[6], "", font_size_pt=9)
        else:
            # Row has audit findings
            # Determine overall compliance rating: C > N > OBS > Y
            ratings = [f.get("compliance_rating", "OBS") for f in row_findings]
            if "C" in ratings:
                overall_rating = "C"
            elif "N" in ratings:
                overall_rating = "N"
            elif "OBS" in ratings:
                overall_rating = "OBS"
            else:
                overall_rating = "Y"
                
            # Build consolidated evidence text
            evidence_parts = []
            # Start with general baseline compliance intro if applicable
            base_intro = std["default_compliant_text"]
            if base_intro:
                # Keep first sentence of base compliance
                first_sent = base_intro.split(".")[0] + "."
                evidence_parts.append(first_sent)
                
            evidence_parts.append("However, the following were observed during the audit:")
            
            # Group observations by location if available
            location_groups: Dict[str, List[str]] = {}
            for f in row_findings:
                loc = f.get("location") or "Premises"
                fig_label = f.get("fig_label") or f"Fig. {f.get('fig_number')}"
                obs_text = f.get("observation", "").strip()
                if not obs_text.endswith("."):
                    obs_text += "."
                line = f"{obs_text} ({fig_label})"
                location_groups.setdefault(loc, []).append(line)
                
            for loc, lines in location_groups.items():
                if loc and loc != "Premises":
                    evidence_parts.append(f"\n{loc}:")
                for l in lines:
                    evidence_parts.append(f"• {l}")
                    
            full_evidence = "\n".join(evidence_parts)
            
            # Build consolidated action text
            action_parts = []
            for f in row_findings:
                act = f.get("corrective_action", "").strip()
                if act and act not in action_parts:
                    action_parts.append(f"• {act}")
            full_action = "\n".join(action_parts) if action_parts else ""
            
            # Get earliest due date
            due_dates = [f.get("due_date", "") for f in row_findings if f.get("due_date")]
            overall_due_date = due_dates[0] if due_dates else ""
            
            set_cell_text(row.cells[3], overall_rating, font_size_pt=10, bold=True)
            set_cell_text(row.cells[4], full_evidence, font_size_pt=9)
            set_cell_text(row.cells[5], full_action, font_size_pt=9)
            set_cell_text(row.cells[6], overall_due_date, font_size_pt=9)

    # 8. Populate Table 5: Photo Evidence Grid (4 columns)
    t5 = doc.tables[4]
    
    # Clear all existing rows from Table 5
    for _ in range(len(t5.rows)):
        p = t5.rows[0]._tr
        p.getparent().remove(p)
        
    # Sort findings by figure number
    findings_with_photos = [f for f in findings if f.get("photo_path") and Path(f["photo_path"]).exists()]
    findings_with_photos.sort(key=lambda x: int(x.get("fig_number", 999)))
    
    # Insert photos in 4-column rows
    chunk_size = 4
    for i in range(0, len(findings_with_photos), chunk_size):
        chunk = findings_with_photos[i:i + chunk_size]
        new_row = t5.add_row()
        for c in new_row.cells:
            c.text = ""
            
        for c_idx, finding in enumerate(chunk):
            cell = new_row.cells[c_idx]
            fig_label = finding.get("fig_label") or f"Fig. {finding.get('fig_number')}"
            
            # Paragraph 1: Caption label
            p_label = cell.paragraphs[0]
            p_label.text = ""
            p_label.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_label.paragraph_format.space_before = Pt(4)
            p_label.paragraph_format.space_after = Pt(2)
            run_lbl = p_label.add_run(fig_label)
            run_lbl.bold = True
            run_lbl.font.size = Pt(9.5)
            run_lbl.font.name = "Arial"
            
            # Paragraph 2: Image
            p_img = cell.add_paragraph()
            p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_img.paragraph_format.space_before = Pt(0)
            p_img.paragraph_format.space_after = Pt(4)
            run_img = p_img.add_run()
            try:
                run_img.add_picture(finding["photo_path"], width=Inches(2.2))
            except Exception as e:
                run_img.add_text(f"[Image could not be rendered: {e}]")

    # 9. Populate Table 6: Audit Conclusion
    t6 = doc.tables[5]
    if audit_data.get("audit_conclusion"):
        conclusion_text = audit_data["audit_conclusion"]
    else:
        # Generate conclusion based on findings counts
        total_findings = len(findings)
        n_count = sum(1 for f in findings if f.get("compliance_rating") == "N")
        c_count = sum(1 for f in findings if f.get("compliance_rating") == "C")
        obs_count = sum(1 for f in findings if f.get("compliance_rating") == "OBS")
        
        site_name = audit_data.get("site_name", "Regis Aged Care")
        site_contact = audit_data.get("business_contact", "the team")
        
        conclusion_text = (
            f"The facility demonstrated several positive food safety practices, including the implementation of "
            f"regular food safety monitoring records and dedicated storage arrangements for resident meals. Staff "
            f"were observed to have access to hand washing facilities, food storage equipment, and cleaning resources "
            f"necessary to support food safety operations. "
        )
        
        if n_count > 0 or c_count > 0 or obs_count > 0:
            defects = []
            if c_count > 0:
                defects.append(f"{c_count} critical deficiency(ies)")
            if n_count > 0:
                defects.append(f"{n_count} non-conformance(s)")
            if obs_count > 0:
                defects.append(f"{obs_count} observation(s)")
            defect_summary = " and ".join(defects)
            
            conclusion_text += (
                f"However, the audit identified {defect_summary} relating to cleanliness, maintenance of equipment, "
                f"and operational controls. The identified items require prompt corrective action to ensure ongoing "
                f"compliance with the Food Standards Australia New Zealand (FSANZ) Food Safety Standards. Continued focus "
                f"on cleaning effectiveness, preventive maintenance, and environmental hygiene will further strengthen "
                f"the site's food safety management system. Items raised must be addressed and followed up at the next internal audit. "
            )
        else:
            conclusion_text += (
                "No non-conformances were identified during this audit. The site continues to demonstrate a high standard "
                "of compliance with FSANZ Food Safety Standards and Victorian Food Act requirements. "
            )
            
        conclusion_text += f"Thanking {site_contact} and the team at {site_name} for their cooperation and engagement throughout the audit process."

    set_cell_text(t6.cell(2, 0), conclusion_text, font_size_pt=9.5)

    # 10. Update closing Signature Date
    audit_date = audit_data.get("audit_date", "")
    for p in doc.paragraphs[-10:]:
        if "Signature" in p.text and "Date" in p.text:
            p.text = f"Signature   \tDate    {audit_date}"
            p.runs[0].font.name = "Arial"
            p.runs[0].font.size = Pt(10)
            break

    # 11. Save final document
    doc.save(str(dest_file))
    return str(dest_file)
