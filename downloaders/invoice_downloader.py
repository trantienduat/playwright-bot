from abc import ABC, abstractmethod
from models import Invoice
from pathlib import Path
from PyPDF2 import PdfReader
import logging

logger = logging.getLogger(__name__)

class IInvoiceDownloader(ABC):
    """Interface for invoice downloaders"""
    
    @abstractmethod
    def download(self, invoice: Invoice, output_path: Path) -> bool:
        """
        Download an invoice and save it to the specified path
        
        Args:
            invoice: Invoice object containing all necessary invoice details
            output_path: Path where the downloaded invoice should be saved
            
        Returns:
            bool: True if download was successful, False otherwise
        """
        pass

    def validate_pdf(self, file_path: Path) -> bool:
        """
        Validate if the downloaded file is a valid PDF
        
        Args:
            file_path: Path to the PDF file to validate
            
        Returns:
            bool: True if PDF is valid, False otherwise
        """
        try:
            with open(file_path, 'rb') as file:
                PdfReader(file)
                return True
        except Exception as e:
            logger.error(f"Invalid PDF file {file_path}: {str(e)}")
            return False

    def download_with_validation(self, invoice: Invoice, output_path: Path, max_retries: int = 1) -> bool:
        """
        Download invoice with PDF validation and retry logic
        
        Args:
            invoice: Invoice object containing all necessary invoice details
            output_path: Path where the downloaded invoice should be saved
            max_retries: Maximum number of download attempts
            
        Returns:
            bool: True if download and validation was successful, False otherwise
        """
        for attempt in range(max_retries):
            if self.download(invoice, output_path):
                if self.validate_pdf(output_path):
                    logger.info(f"✅ Successfully downloaded and validated: {output_path}")
                    return True
                else:
                    logger.warning(f"⚠️ Attempt {attempt + 1}: PDF validation failed, retrying...")
                    output_path.unlink(missing_ok=True)  # Delete invalid file

            if attempt < max_retries - 1:
                logger.info(f"Retrying download... Attempt {attempt + 2}/{max_retries}")

        logger.error(f"❌ Failed to download valid PDF after {max_retries} attempts")
        return False