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

def validate_pdfs_in_downloads(downloads_folder: Path):
    """
    Iterate through all PDF files in the downloads folder and validate them.
    """
    for pdf_file in downloads_folder.glob("*.pdf"):
        if is_valid_pdf(pdf_file):
            logger.info(f"Valid PDF: {pdf_file}")
        else:
            logger.warning(f"Invalid PDF: {pdf_file}")

    # Example usage
def delete_invalid_pdfs(downloads_folder: Path):
    """
    Delete all invalid PDF files in the downloads folder.
    """
    for pdf_file in downloads_folder.glob("*.pdf"):
        if not is_valid_pdf(pdf_file):
            try:
                pdf_file.unlink()
                logger.info(f"Deleted invalid PDF: {pdf_file}")
            except Exception as e:
                logger.error(f"Failed to delete {pdf_file}: {str(e)}")


downloads_folder = Path("/Users/tranduat/workspace/Personal/python/playwright_bot/downloads")
# validate_pdfs_in_downloads(downloads_folder)
# Call the function to delete invalid PDFs
delete_invalid_pdfs(downloads_folder)