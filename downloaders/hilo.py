from .invoice_downloader import IInvoiceDownloader
from models import Invoice
from pathlib import Path
import logging
from helpers import download_by_url
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('hilo_downloader')

class HiloDownloader(IInvoiceDownloader):
    def download(self, invoice: Invoice, output_path: Path) -> bool:
        """Download invoice using HILO's URL"""
        url = f"https://vn.einvoice.grab.com/Invoice/DowloadPdf?Fkey={invoice.tracking_code}"
        logger.info(f"🔗 HILO Downloader: {url}")
        return download_by_url(url, output_path.parent, output_path.name)
    
    def download_invoice(self, invoice: Invoice, output_path: Path) -> bool:
        """
        Download invoice with validation and retry logic
        """
        return self.download_with_validation(invoice, output_path)