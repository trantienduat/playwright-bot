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
logger = logging.getLogger('misa')

class MISADownloader(IInvoiceDownloader):
    def download(self, invoice: Invoice, output_path: Path) -> bool:
        """Download invoice using MISA's URL"""
        url = f"https://www.meinvoice.vn/tra-cuu/DownloadHandler.ashx?Type=pdf&Viewer=1&Code={invoice.tracking_code}"
        logger.info(f"🔗 MISA Downloader: {url}")
        return download_by_url(url, output_path.parent, output_path.name)