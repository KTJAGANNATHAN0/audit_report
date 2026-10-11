import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Paths
TEMPLATE_PATH = BASE_DIR / "Regis Audit Report for Automation.docx"
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = BASE_DIR / "uploads"
OUTPUTS_DIR = BASE_DIR / "outputs"
DATABASE_PATH = DATA_DIR / "audit_automation.db"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

# OpenRouter Settings
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
DEFAULT_VISION_MODEL = os.getenv("DEFAULT_VISION_MODEL", "google/gemini-2.0-flash-001")

SUPPORTED_VISION_MODELS = [
    "google/gemini-2.0-flash-001",
    "meta-llama/llama-3.2-11b-vision-instruct",
    "anthropic/claude-3.5-sonnet",
    "openai/gpt-4o-mini",
    "openai/gpt-4o"
]

# LibreOffice executable paths to check on Windows and Linux
SOFFICE_PATHS = [
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    "/usr/bin/soffice",
    "/usr/bin/libreoffice"
]

# Regis Default Site Profiles
REGIS_SITES = [
    {
        "site_name": "Regis Dandenong North",
        "proprietor_name": "Regis Aged Care",
        "business_address": "5 Bakers Road Dandenong VIC 3175",
        "phone_number": "03 9701 1244",
        "business_contact": "Bryan Seeborun / Aurelie Flack",
        "contact_email": "bseeborun@regis.com.au, aflack@regis.com.au",
        "person_in_charge": "Helen Santoreneus",
        "pic_email": "dandenong@regis.com.au",
        "nominated_fss": "Sunil Kumar / Damith Yagamuni",
        "premise_type": "Aged Care",
        "premise_class": "1",
        "council_name": "City of Greater Dandenong",
        "council_reg_no": "F-2247 Expiry Date 31/12/2026",
        "council_email": "council@cgd.vic.gov.au"
    },
    {
        "site_name": "Regis Rosebud",
        "proprietor_name": "Regis Aged Care",
        "business_address": "125 Waterfall Gully Rd Rosebud VIC 3939",
        "phone_number": "03 5986 8200",
        "business_contact": "Bryan Seeborun",
        "contact_email": "bseeborun@regis.com.au",
        "person_in_charge": "Site Manager",
        "pic_email": "rosebud@regis.com.au",
        "nominated_fss": "Food Safety Supervisor",
        "premise_type": "Aged Care",
        "premise_class": "1",
        "council_name": "Mornington Peninsula Shire",
        "council_reg_no": "F-3100 Expiry Date 31/12/2026",
        "council_email": "info@mornpen.vic.gov.au"
    },
    {
        "site_name": "Regis Cranbourne",
        "proprietor_name": "Regis Aged Care",
        "business_address": "183-195 Cranbourne-Frankston Rd Cranbourne VIC 3977",
        "phone_number": "03 5995 5611",
        "business_contact": "Bryan Seeborun",
        "contact_email": "bseeborun@regis.com.au",
        "person_in_charge": "Facility Manager",
        "pic_email": "cranbourne@regis.com.au",
        "nominated_fss": "Food Safety Supervisor",
        "premise_type": "Aged Care",
        "premise_class": "1",
        "council_name": "City of Casey",
        "council_reg_no": "F-1892 Expiry Date 31/12/2026",
        "council_email": "caseycc@casey.vic.gov.au"
    }
]

# Default Auditor Details
DEFAULT_AUDITOR = {
    "name": "Narmada Oogathoo",
    "dhhs_reg": "00224045",
    "phone": "+61402701166",
    "email": "stryve@outlook.com.au"
}
