# AI-Powered Daily Food Safety Audit Automation

Automated daily food safety audit reporting system for aged care facilities using **Photo + Short Notes → OpenRouter Vision AI → Regis DOCX Template Population → Downloadable PDF**.

Built with **Python 3.12+, Streamlit, OpenRouter API, python-docx, LibreOffice, and SQLite**.

---

## 🌟 Features

* **Multi-Photo Mobile / Desktop Upload:** Capture or upload audit photos on phone or desktop and attach quick keywords or observations.
* **OpenRouter Vision AI Integration:** Extracts visible physical evidence and translates observations into structured JSON conforming to food safety audit standards.
* **Regis Baseline Template Preservation:** Populates the exact Victorian aged care audit report layout (`Regis Audit Report for Automation.docx`), preserving all 6 tables, 45 standard checklist rows, and original styling.
* **4-Column Evidence Grid:** Automatically arranges photos into a clean 4-column table with figure captions (`Fig. 1`, `Fig. 2`, etc.) matching in-text non-conformance citations.
* **Human-in-the-Loop Review:** Allows auditors to verify and modify observations, compliance ratings (`OBS`, `N`, `C`, `Y`), corrective actions, and completion deadlines.
* **Validation & Missing Data Flags:** Checks required fields, rating validity, and missing deadlines prior to report generation.
* **Automated PDF Export:** Converts populated DOCX documents into official PDFs using LibreOffice headless conversion (with MS Word automation fallback).
* **Audit History & Archives:** SQLite database maintains report archives, download access, and an audit trail with timestamps.

---

## 🏗️ Architecture

```
audit maker/
├── Regis Audit Report for Automation.docx   # Baseline Regis template
├── app.py                                   # Streamlit application entry point
├── requirements.txt                         # Python dependencies
├── .env.example                             # Environment variable template
├── core/
│   ├── config.py                            # Settings, paths, Regis site profiles
│   ├── audit_rules.py                       # 45 Regis standards catalogue & keyword matcher
│   ├── validator.py                         # Report validation engine (FR-09)
│   ├── ai_service.py                        # OpenRouter Vision API & structured JSON parser
│   ├── docx_engine.py                       # Word document template population engine (FR-07)
│   └── pdf_converter.py                     # Headless LibreOffice & MS Word PDF converter (FR-08)
├── database/
│   └── db.py                                # SQLite schema, audits, findings, history (FR-10, FR-12)
├── ui/
│   ├── screen1_new_audit.py                 # Screen 1: Date/Site, Multi-photo upload & notes
│   ├── screen2_findings.py                  # Screen 2: Review AI findings, ratings & actions
│   ├── screen3_preview.py                   # Screen 3: Validation, report preview & approval
│   └── screen4_history.py                   # Screen 4: Search audits, downloads & revision log
└── static/
    └── styles.css                           # Modern UI theme and component styling
```

---

## 🚀 Quick Start

### 1. Clone & Install Dependencies

```bash
git clone https://github.com/KTJAGANNATHAN0/audit_report.git
cd audit_report
python -m pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and add your OpenRouter API Key:

```bash
cp .env.example .env
```

```env
OPENROUTER_API_KEY=your_openrouter_api_key_here
DEFAULT_VISION_MODEL=google/gemini-2.0-flash-001
```

*(Note: If no API key is provided, the application runs in offline heuristic mode).*

### 3. Launch the Application

```bash
python -m streamlit run app.py
```

Open your browser at `http://localhost:8501`.

---

## 📱 User Workflow (4 Screens)

1. **Screen 1 — New Audit:** Select facility (presets available for Regis sites), enter audit date/auditor credentials, upload photos, and attach quick keyword notes.
2. **Screen 2 — AI Findings:** Inspect AI-extracted findings, adjust ratings (`OBS`, `N`, `C`, `Y`), modify corrective actions, and set completion deadlines.
3. **Screen 3 — Report Preview:** Verify checklist, review generated executive conclusion, sign the declaration, and export both `.pdf` and `.docx`.
4. **Screen 4 — Report History:** Search historical audits, view approval timestamps, and re-download reports anytime.
