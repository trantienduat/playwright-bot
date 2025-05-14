from playwright.sync_api import sync_playwright
from .invoice_downloader import IInvoiceDownloader
from models import Invoice
from pathlib import Path
import logging
import os
from datetime import datetime
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('kimtin')

class FPTDownloader(IInvoiceDownloader):

    def download(self, invoice: Invoice, output_path: Path) -> bool:
        logger.info(f"🤖 Starting FPT downloader for invoice {invoice.invoice_series}-{invoice.invoice_number}")
        try:
            # Construct the URL
            url = f"https://hoadondientu.kimtingroup.com/api/invoice-mailpdf?sec={invoice.tracking_code}"
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(accept_downloads=True)
                page = context.new_page()
                try:
                    with page.expect_download() as download_info:
                        page.evaluate(f"window.location.href = '{url}'")  # Trigger download by setting window location
                    download = download_info.value
                    
                    # Save the file directly to the specified output path
                    download.save_as(str(output_path))
                    print(f"✅ Downloaded and saved as: {output_path}")
                except Exception as e:
                    print(f"❌ Error downloading {url}: {e}")
                finally:
                    browser.close()

        except FileNotFoundError:
            print(f"❌ Error: File not found at {output_path}")
            print("Please ensure the file exists in the data directory")
        return True

    def download_invoice(self, invoice: Invoice, output_path: Path) -> bool:
        """
        Download invoice with validation and retry logic
        """
        return self.download_with_validation(invoice, output_path)
