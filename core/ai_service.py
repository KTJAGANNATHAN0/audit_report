"""
OpenRouter Vision AI Service for Audit Evidence Analysis.
Processes photo evidence and auditor short notes into structured audit findings.
Fulfills FR-03, FR-04, FR-05, and PRD Section 5.
"""

import os
import base64
import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
import requests
from core.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, DEFAULT_VISION_MODEL
from core.audit_rules import match_standard_by_keywords, get_standard_by_row_index, AUDIT_STANDARDS

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert Food Safety Auditor assistant specializing in aged care food safety audits under Food Standards Australia New Zealand (FSANZ) Standards (3.2.1, 3.2.2, 3.2.2A, 3.2.3) and the Victorian Food Act 1984.

Your task is to analyze photo evidence and auditor short notes, and generate a precise, factual audit finding in structured JSON format.

IMPORTANT AUDIT RULES:
1. NEVER invent evidence, temperatures, readings, dates, signatures, or completion of actions.
2. Only describe visible physical evidence shown in the photo, supplemented by the auditor's note.
3. Distinguish clearly between:
   - OBS (Observation): Opportunities for improvement or minor deviations.
   - N (Non-Critical Deficiency): Low-to-moderate risk deviation requiring corrective action (e.g., food residue on equipment, damaged non-food surfaces, uncovered food, grime buildup).
   - C (Critical Deficiency): Immediate or severe contamination risk.
   - Y (Compliant): Satisfactory condition.
4. Do NOT assume an issue is resolved merely because cleaning or repair is recommended.
5. Provide a realistic suggested corrective action following approved food hygiene practices.
6. Provide an appropriate suggested deadline: 14 days for general cleaning/signage, 28-30 days for maintenance/repairs, immediate/7 days for critical hygiene issues.

OUTPUT FORMAT:
You MUST respond with valid JSON adhering to this exact schema:
{
  "observation": "Clear, professional factual description of the visible evidence in the photo",
  "risk": "Food safety risk / contamination hazard associated with this issue",
  "suggested_action": "Professional corrective action required to rectify the finding",
  "suggested_rating": "OBS" | "N" | "C" | "Y",
  "location": "Serveries" | "Main Kitchen" | "Cool room" | "Dry store" | "Dishwash Area" | "Dining Area",
  "standard_row_index": <int row index in Table 4, between 2 and 56>,
  "standard_name": "Standard name matching the row",
  "suggested_deadline_days": 14 | 28
}

STANDARD ROW INDEX REFERENCE:
- Row 8: Standard 3.2.2 - Food handling skills and knowledge (hand basin misuse, uncovered food, scoops in food, floor contact)
- Row 13: Standard 3.2.2 - Dry Storage
- Row 14: Standard 3.2.2 - Cold Storage / Cool room / Freezer (temperature, storage)
- Row 32: Standard 3.2.2 - 19 Cleanliness / Cleaning (dust, grime, grease, food residue, microwave, oven, canopy, surfaces)
- Row 33: Standard 3.2.2 - 20 Sanitising (sanitiser, chemical storage)
- Row 34: Standard 3.2.2 - Dishwasher (rinse temperature, dishwasher condition)
- Row 35: Standard 3.2.2 - 21 Maintenance (general maintenance)
- Row 37: Standard 3.2.2 - 22 Temperature measuring devices (calibrations)
- Row 38: Standard 3.2.2 - 24 Animals and Pests (pest evidence, exclusion)
- Row 50: Standard 3.2.3 - 10 Floors (floor surface, damaged tiles, drainage)
- Row 51: Standard 3.2.3 - 11 Walls and ceilings (cracks, peeling paint, mould on ceiling)
- Row 53: Standard 3.2.3 - 12(1) Fixtures, fittings and equipment (exposed timber, damaged seals, silicone mould, broken doors, racks)
"""

def encode_image_to_base64(image_path: str) -> str:
    """Encodes an image file to base64 string."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def analyze_photo_evidence(
    photo_path: str,
    user_notes: str,
    api_key: Optional[str] = None,
    model: Optional[str] = None
) -> Dict[str, Any]:
    """
    Sends photo evidence and auditor notes to OpenRouter Vision API.
    Returns structured audit finding dictionary.
    """
    key = api_key or os.getenv("OPENROUTER_API_KEY") or OPENROUTER_API_KEY
    selected_model = model or DEFAULT_VISION_MODEL
    
    if not key:
        logger.warning("No OpenRouter API key provided. Using intelligent offline audit rule heuristic.")
        return generate_heuristic_finding(photo_path, user_notes)
        
    try:
        # Prepare image payload
        image_b64 = encode_image_to_base64(photo_path)
        mime_type = "image/jpeg"
        if photo_path.lower().endswith(".png"):
            mime_type = "image/png"
        elif photo_path.lower().endswith(".webp"):
            mime_type = "image/webp"

        user_content = [
            {
                "type": "text",
                "text": f"Auditor Short Observation / Keywords:\n\"{user_notes}\"\n\nPlease analyze this photo evidence and auditor note according to the Regis Food Safety Audit standard."
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime_type};base64,{image_b64}"
                }
            }
        ]

        headers = {
            "Authorization": f"Bearer {key}",
            "HTTP-Referer": "https://regis.com.au/audit-automation",
            "X-Title": "Regis AI Audit Maker",
            "Content-Type": "application/json"
        }

        payload = {
            "model": selected_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
            "max_tokens": 1000
        }

        response = requests.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=40
        )

        if response.status_code != 200:
            logger.error(f"OpenRouter API error {response.status_code}: {response.text}")
            # Fall back to heuristic with note about API error
            res = generate_heuristic_finding(photo_path, user_notes)
            res["api_warning"] = f"OpenRouter API returned HTTP {response.status_code}. Heuristic finding generated."
            return res

        data = response.json()
        content = data["choices"][0]["message"]["content"]
        
        # Parse JSON
        result = json.loads(content)
        
        # Validate and normalize parsed result
        std_row = result.get("standard_row_index")
        if std_row is None or not isinstance(std_row, int) or std_row < 2:
            std_row = match_standard_by_keywords(f"{user_notes} {result.get('observation', '')}")
            result["standard_row_index"] = std_row
            
        std_info = get_standard_by_row_index(std_row)
        if std_info:
            result["standard_name"] = f"{std_info['activity']} - {std_info['sub_activity']}".strip(" -")
            result["fsp_ref"] = std_info["fsp_ref"]
            
        return result

    except Exception as e:
        logger.exception(f"Error in OpenRouter vision analysis: {e}")
        res = generate_heuristic_finding(photo_path, user_notes)
        res["api_warning"] = f"AI analysis error: {str(e)}. Heuristic finding generated."
        return res

def generate_heuristic_finding(photo_path: str, user_notes: str) -> Dict[str, Any]:
    """
    Intelligent offline rule-based heuristic when API key is unavailable or fails.
    Fulfills PRD FR-04 and FR-05 requirements without breaking the audit flow.
    """
    row_idx = match_standard_by_keywords(user_notes)
    std_info = get_standard_by_row_index(row_idx)
    notes_clean = user_notes.strip() if user_notes else "Visual defect observed during inspection."
    
    # Cleanliness finding
    if row_idx == 32:
        return {
            "observation": f"Visible food residue, grease or dust accumulation was observed on equipment surfaces ({notes_clean}).",
            "risk": "Potential microbial contamination and pest harbourage if equipment and surfaces are not adequately cleaned and sanitised.",
            "suggested_action": "A food business must maintain food premises to a standard of cleanliness where there is no accumulation of food waste, dirt, grease or other visible matter. Clean and sanitise the equipment according to the approved cleaning schedule.",
            "suggested_rating": "N",
            "location": "Serveries" if "servery" in notes_clean.lower() else "Main Kitchen",
            "standard_row_index": 32,
            "standard_name": "19 Cleanliness - Cleaning",
            "fsp_ref": "FSP Ref: 78 - 85",
            "suggested_deadline_days": 14
        }
    # Fixtures & fittings finding
    elif row_idx == 53:
        return {
            "observation": f"Deteriorated, damaged or absorbent surface identified ({notes_clean}), which prevents effective cleaning and sanitising.",
            "risk": "Exposed or cracked surfaces may harbour pathogenic bacteria and compromise hygiene standards.",
            "suggested_action": "Repair, reseal or replace damaged fixture or equipment to ensure all surfaces are smooth, impervious, and capable of being easily cleaned and sanitised.",
            "suggested_rating": "N",
            "location": "Main Kitchen",
            "standard_row_index": 53,
            "standard_name": "12(1) Fixtures, fittings and equipment",
            "fsp_ref": "FSP Ref: 74",
            "suggested_deadline_days": 28
        }
    # Food handling / storage
    elif row_idx in [8, 13, 14]:
        return {
            "observation": f"Food handling or storage practice deviation observed ({notes_clean}).",
            "risk": "Risk of cross-contamination or degradation of food safety controls for vulnerable residents.",
            "suggested_action": "Implement approved food handling controls, ensure proper covering, date labelling, and segregation off the floor.",
            "suggested_rating": "N",
            "location": "Cool room" if row_idx == 14 else "Main Kitchen",
            "standard_row_index": row_idx,
            "standard_name": f"{std_info['activity']} - {std_info['sub_activity']}" if std_info else "Food Handling",
            "fsp_ref": std_info["fsp_ref"] if std_info else "FSP Ref: 95",
            "suggested_deadline_days": 14
        }
    else:
        return {
            "observation": f"Audit inspection observation noted: {notes_clean}.",
            "risk": "Deviation from food safety management system guidelines.",
            "suggested_action": "Review procedure and implement corrective action in accordance with site food safety program.",
            "suggested_rating": "OBS",
            "location": "Main Kitchen",
            "standard_row_index": row_idx,
            "standard_name": f"{std_info['activity']} - {std_info['sub_activity']}" if std_info else "General Standard",
            "fsp_ref": std_info["fsp_ref"] if std_info else "FSP Ref: 91",
            "suggested_deadline_days": 28
        }
