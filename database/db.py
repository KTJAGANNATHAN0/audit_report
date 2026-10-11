"""
Database Engine for Regis Audit Automation.
Provides SQLite models, migrations, and CRUD operations.
Fulfills FR-10, FR-12, and PRD Section 9.
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
from core.config import DATABASE_PATH

def get_db_connection() -> sqlite3.Connection:
    """Creates a database connection with dict-like row access."""
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes SQLite schema and tables if they do not exist."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Audits table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        audit_id TEXT UNIQUE NOT NULL,
        site_name TEXT NOT NULL,
        proprietor_name TEXT,
        business_address TEXT,
        phone_number TEXT,
        business_contact TEXT,
        contact_email TEXT,
        person_in_charge TEXT,
        pic_email TEXT,
        nominated_fss TEXT,
        premise_type TEXT DEFAULT 'Aged Care',
        premise_class TEXT DEFAULT '1',
        council_name TEXT,
        council_reg_no TEXT,
        council_email TEXT,
        auditor_name TEXT,
        auditor_reg TEXT,
        auditor_phone TEXT,
        auditor_email TEXT,
        prev_audit_date TEXT,
        audit_date TEXT NOT NULL,
        audit_time TEXT DEFAULT '9:30am',
        scope_objective TEXT,
        audit_type TEXT DEFAULT 'Adequacy and Compliance Audit',
        audit_conclusion TEXT,
        review_status TEXT DEFAULT 'draft',
        approved_by TEXT,
        approved_at TEXT,
        docx_path TEXT,
        pdf_path TEXT,
        template_version TEXT DEFAULT '1.0',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)

    # 2. Findings table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS findings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        audit_id TEXT NOT NULL,
        fig_number INTEGER NOT NULL,
        fig_label TEXT NOT NULL,
        photo_path TEXT NOT NULL,
        user_notes TEXT,
        standard_row_index INTEGER,
        standard_name TEXT,
        sub_activity TEXT,
        fsp_ref TEXT,
        location TEXT,
        observation TEXT NOT NULL,
        risk TEXT,
        corrective_action TEXT,
        compliance_rating TEXT NOT NULL,
        due_date TEXT,
        review_status TEXT DEFAULT 'pending',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (audit_id) REFERENCES audits (audit_id) ON DELETE CASCADE
    )
    """)

    # 3. Audit History / Revisions table (FR-12)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        audit_id TEXT NOT NULL,
        action TEXT NOT NULL,
        actor TEXT NOT NULL,
        details TEXT,
        timestamp TEXT NOT NULL,
        FOREIGN KEY (audit_id) REFERENCES audits (audit_id) ON DELETE CASCADE
    )
    """)

    conn.commit()
    conn.close()

# --- Audit CRUD ---

def create_audit(audit_data: Dict[str, Any]) -> str:
    """Inserts a new audit record and logs history."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    
    # Auto-generate audit_id if not present
    audit_id = audit_data.get("audit_id")
    if not audit_id:
        today_str = datetime.now().strftime("%Y%m%d")
        cursor.execute("SELECT COUNT(*) FROM audits WHERE audit_id LIKE ?", (f"AUD-{today_str}-%",))
        count = cursor.fetchone()[0] + 1
        audit_id = f"AUD-{today_str}-{count:03d}"
        audit_data["audit_id"] = audit_id

    fields = [
        "audit_id", "site_name", "proprietor_name", "business_address", "phone_number",
        "business_contact", "contact_email", "person_in_charge", "pic_email", "nominated_fss",
        "premise_type", "premise_class", "council_name", "council_reg_no", "council_email",
        "auditor_name", "auditor_reg", "auditor_phone", "auditor_email", "prev_audit_date",
        "audit_date", "audit_time", "scope_objective", "audit_type", "audit_conclusion",
        "review_status", "approved_by", "approved_at", "docx_path", "pdf_path",
        "template_version", "created_at", "updated_at"
    ]

    values = [
        audit_data.get("audit_id"),
        audit_data.get("site_name"),
        audit_data.get("proprietor_name", "Regis Aged Care"),
        audit_data.get("business_address"),
        audit_data.get("phone_number"),
        audit_data.get("business_contact"),
        audit_data.get("contact_email"),
        audit_data.get("person_in_charge"),
        audit_data.get("pic_email"),
        audit_data.get("nominated_fss"),
        audit_data.get("premise_type", "Aged Care"),
        audit_data.get("premise_class", "1"),
        audit_data.get("council_name"),
        audit_data.get("council_reg_no"),
        audit_data.get("council_email"),
        audit_data.get("auditor_name"),
        audit_data.get("auditor_reg"),
        audit_data.get("auditor_phone"),
        audit_data.get("auditor_email"),
        audit_data.get("prev_audit_date"),
        audit_data.get("audit_date"),
        audit_data.get("audit_time", "9:30am"),
        audit_data.get("scope_objective"),
        audit_data.get("audit_type", "Adequacy and Compliance Audit"),
        audit_data.get("audit_conclusion"),
        audit_data.get("review_status", "draft"),
        audit_data.get("approved_by"),
        audit_data.get("approved_at"),
        audit_data.get("docx_path"),
        audit_data.get("pdf_path"),
        audit_data.get("template_version", "1.0"),
        now,
        now
    ]

    placeholders = ", ".join(["?"] * len(fields))
    col_names = ", ".join(fields)
    sql = f"INSERT INTO audits ({col_names}) VALUES ({placeholders})"
    
    cursor.execute(sql, values)
    conn.commit()

    # Log history
    log_audit_history(audit_id, "AUDIT_CREATED", audit_data.get("auditor_name", "System"), "New audit session created.")
    conn.close()
    return audit_id

def update_audit(audit_id: str, updates: Dict[str, Any], actor: str = "Auditor"):
    """Updates audit metadata."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    updates["updated_at"] = now
    
    set_clauses = []
    values = []
    for k, v in updates.items():
        set_clauses.append(f"{k} = ?")
        values.append(v)
        
    values.append(audit_id)
    sql = f"UPDATE audits SET {', '.join(set_clauses)} WHERE audit_id = ?"
    cursor.execute(sql, values)
    conn.commit()
    conn.close()

    log_audit_history(audit_id, "AUDIT_UPDATED", actor, f"Updated fields: {list(updates.keys())}")

def get_audit(audit_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves an audit by its audit_id."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM audits WHERE audit_id = ?", (audit_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_audits(search_query: str = None) -> List[Dict[str, Any]]:
    """Retrieves all audits, sorted by most recent first."""
    conn = get_db_connection()
    cursor = conn.cursor()
    if search_query:
        q = f"%{search_query}%"
        cursor.execute("""
            SELECT * FROM audits 
            WHERE audit_id LIKE ? OR site_name LIKE ? OR auditor_name LIKE ?
            ORDER BY created_at DESC
        """, (q, q, q))
    else:
        cursor.execute("SELECT * FROM audits ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# --- Findings CRUD ---

def save_findings_for_audit(audit_id: str, findings: List[Dict[str, Any]], actor: str = "Auditor"):
    """Overwrites or inserts findings for an audit."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    
    # Remove existing findings for this audit to maintain clean state
    cursor.execute("DELETE FROM findings WHERE audit_id = ?", (audit_id,))
    
    for idx, f in enumerate(findings):
        fig_num = f.get("fig_number") or (idx + 1)
        fig_label = f.get("fig_label") or f"Fig. {fig_num}"
        
        cursor.execute("""
        INSERT INTO findings (
            audit_id, fig_number, fig_label, photo_path, user_notes,
            standard_row_index, standard_name, sub_activity, fsp_ref,
            location, observation, risk, corrective_action, compliance_rating,
            due_date, review_status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            audit_id,
            fig_num,
            fig_label,
            f.get("photo_path", ""),
            f.get("user_notes", ""),
            f.get("standard_row_index"),
            f.get("standard_name", ""),
            f.get("sub_activity", ""),
            f.get("fsp_ref", ""),
            f.get("location", ""),
            f.get("observation", ""),
            f.get("risk", ""),
            f.get("corrective_action", ""),
            f.get("compliance_rating", "OBS"),
            f.get("due_date", ""),
            f.get("review_status", "approved"),
            now,
            now
        ))
        
    conn.commit()
    conn.close()
    log_audit_history(audit_id, "FINDINGS_SAVED", actor, f"Saved {len(findings)} findings.")

def get_findings_for_audit(audit_id: str) -> List[Dict[str, Any]]:
    """Retrieves all findings for an audit in figure order."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM findings WHERE audit_id = ? ORDER BY fig_number ASC", (audit_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# --- History / Audit Trail (FR-12) ---

def log_audit_history(audit_id: str, action: str, actor: str, details: str = ""):
    """Logs an immutable revision entry."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute("""
    INSERT INTO audit_history (audit_id, action, actor, details, timestamp)
    VALUES (?, ?, ?, ?, ?)
    """, (audit_id, action, actor, details, now))
    conn.commit()
    conn.close()

def get_audit_history(audit_id: str) -> List[Dict[str, Any]]:
    """Retrieves chronological history entries for an audit."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM audit_history WHERE audit_id = ? ORDER BY id DESC", (audit_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]
