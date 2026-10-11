"""
PDF Conversion Engine.
Primary method: LibreOffice headless conversion (as requested in PRD).
Fallback method: Microsoft Word automation via docx2pdf / win32com.
"""

import os
import subprocess
import shutil
from pathlib import Path
from typing import Tuple
from core.config import SOFFICE_PATHS

def find_libreoffice_executable() -> str:
    """Finds the path to soffice executable if installed."""
    # Check PATH first
    for cmd in ["soffice", "libreoffice"]:
        path = shutil.which(cmd)
        if path:
            return path
            
    # Check well-known installation paths
    for p in SOFFICE_PATHS:
        if os.path.exists(p):
            return p
            
    return ""

def convert_docx_to_pdf(docx_path: str, output_pdf_path: str = None) -> Tuple[bool, str, str]:
    """
    Converts a .docx document to .pdf.
    Returns (success, output_pdf_path, error_message).
    """
    docx_file = Path(docx_path).resolve()
    if not docx_file.exists():
        return False, "", f"Source DOCX file not found: {docx_path}"
        
    if not output_pdf_path:
        output_pdf_file = docx_file.with_suffix(".pdf")
    else:
        output_pdf_file = Path(output_pdf_path).resolve()
        
    output_dir = output_pdf_file.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Try LibreOffice (PRD Primary)
    soffice_exe = find_libreoffice_executable()
    if soffice_exe:
        try:
            cmd = [
                soffice_exe,
                "--headless",
                "--convert-to", "pdf",
                "--outdir", str(output_dir),
                str(docx_file)
            ]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=45)
            # LibreOffice writes file with same stem as docx in outdir
            expected_lo_pdf = output_dir / f"{docx_file.stem}.pdf"
            if expected_lo_pdf.exists() and expected_lo_pdf.stat().st_size > 0:
                if expected_lo_pdf != output_pdf_file:
                    shutil.move(str(expected_lo_pdf), str(output_pdf_file))
                return True, str(output_pdf_file), ""
        except Exception as e:
            # Fall through to docx2pdf
            pass

    # 2. Try docx2pdf (MS Word automation fallback)
    try:
        import docx2pdf
        docx2pdf.convert(str(docx_file), str(output_pdf_file))
        if output_pdf_file.exists() and output_pdf_file.stat().st_size > 0:
            return True, str(output_pdf_file), ""
    except Exception as e:
        pass

    # 3. Direct pywin32 COM fallback
    try:
        import win32com.client
        import pythoncom
        pythoncom.CoInitialize()
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        doc = word.Documents.Open(str(docx_file))
        # 17 = wdFormatPDF
        doc.SaveAs(str(output_pdf_file), FileFormat=17)
        doc.Close()
        word.Quit()
        pythoncom.CoUninitialize()
        if output_pdf_file.exists() and output_pdf_file.stat().st_size > 0:
            return True, str(output_pdf_file), ""
    except Exception as e:
        return False, "", f"PDF conversion failed: {str(e)}"

    return False, "", "Could not generate PDF. Please ensure LibreOffice or Microsoft Word is installed."
