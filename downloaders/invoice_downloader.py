from abc import ABC, abstractmethod
from models import Invoice
from pathlib import Path

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