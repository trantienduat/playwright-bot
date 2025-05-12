
from PyPDF2 import PdfReader
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def is_valid_pdf(file_path: Path) -> bool:
    """
    Validate if a file is a valid PDF
    Returns True if valid, False otherwise
    """
    try:
        with open(file_path, 'rb') as file:
            # Try to read the PDF
            PdfReader(file)
            return True
    except Exception as e:
        logger.error(f"Invalid PDF file {file_path}: {str(e)}")
        return False