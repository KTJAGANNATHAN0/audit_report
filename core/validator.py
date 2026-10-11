"""
Validation Engine for Regis Audit Reports.
Implements FR-09 and PRD Section 10: Validates required fields, flags missing information.
"""

from typing import Dict, List, Any

def validate_audit_header(audit_data: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Validates general audit metadata.
    Returns a list of issue dicts with 'field', 'message', and 'severity'.
    """
    issues = []
    
    required_fields = [
        ("site_name", "Trading Name / Site Name"),
        ("audit_date", "Date of Current Audit"),
        ("auditor_name", "Auditor Name"),
        ("proprietor_name", "Proprietor Name"),
        ("business_address", "Business Address"),
    ]
    
    for field_key, field_name in required_fields:
        val = audit_data.get(field_key, "")
        if not val or not str(val).strip():
            issues.append({
                "field": field_key,
                "message": f"Required field missing: {field_name}",
                "severity": "error"
            })
            
    # Warning fields
    recommended_fields = [
        ("council_name", "Council / Shire"),
        ("council_reg_no", "Registration No. & Expiry"),
        ("auditor_reg", "Auditor DHHS Registration No."),
        ("auditor_phone", "Auditor Phone Number"),
    ]
    
    for field_key, field_name in recommended_fields:
        val = audit_data.get(field_key, "")
        if not val or not str(val).strip():
            issues.append({
                "field": field_key,
                "message": f"Recommended field empty: {field_name}",
                "severity": "warning"
            })
            
    return issues

def validate_finding(finding: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Validates an individual audit finding.
    """
    issues = []
    fig_label = finding.get("fig_label", f"Fig. {finding.get('fig_number', '?')}")
    
    # 1. Photo must exist
    if not finding.get("photo_path"):
        issues.append({
            "field": "photo_path",
            "message": f"{fig_label}: Missing photo evidence file.",
            "severity": "error"
        })
        
    # 2. Observation text
    obs = finding.get("observation", "")
    if not obs or not obs.strip():
        issues.append({
            "field": "observation",
            "message": f"{fig_label}: Observation statement cannot be blank.",
            "severity": "error"
        })
        
    # 3. Compliance rating
    rating = finding.get("compliance_rating", "")
    if rating not in ["Y", "OBS", "N", "C"]:
        issues.append({
            "field": "compliance_rating",
            "message": f"{fig_label}: Invalid or unassigned compliance rating '{rating}'. Must be Y, OBS, N, or C.",
            "severity": "error"
        })
        
    # 4. Corrective action required if not compliant
    if rating in ["OBS", "N", "C"]:
        action = finding.get("corrective_action", "")
        if not action or not action.strip():
            issues.append({
                "field": "corrective_action",
                "message": f"{fig_label}: Rating is '{rating}' but corrective action is missing.",
                "severity": "error"
            })
            
        due_date = finding.get("due_date", "")
        if not due_date or not due_date.strip() or "Click or tap" in due_date:
            issues.append({
                "field": "due_date",
                "message": f"{fig_label}: Agreed completion deadline is required for non-compliant items.",
                "severity": "warning"
            })
            
    # 5. Standard mapping
    if finding.get("standard_row_index") is None:
        issues.append({
            "field": "standard_row_index",
            "message": f"{fig_label}: Finding must be mapped to a Regis audit standard row.",
            "severity": "error"
        })
        
    return issues

def validate_audit_report(audit_data: Dict[str, Any], findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Full validation of the entire audit package before report approval.
    """
    header_issues = validate_audit_header(audit_data)
    findings_issues = []
    
    for f in findings:
        findings_issues.extend(validate_finding(f))
        
    all_issues = header_issues + findings_issues
    errors = [i for i in all_issues if i["severity"] == "error"]
    warnings = [i for i in all_issues if i["severity"] == "warning"]
    
    return {
        "is_valid": len(errors) == 0,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
        "all_issues": all_issues
    }
