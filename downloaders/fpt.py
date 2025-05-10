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
        if not invoice.tracking_code:
            logger.error("❌ Missing tracking code")
            return False
        logger.info(f"🤖 Starting FPT downloader for invoice {invoice.invoice_series}-{invoice.invoice_number}")
        try:
            download_dir = output_path.parent
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
                    
                    # Format the file name with the month abbreviation
                    month_name = invoice.invoice_timestamp.strftime("%b") if invoice.invoice_timestamp else "Unknown"
                    file_name = f"{month_name}_{invoice.invoice_series}_{invoice.invoice_number}.pdf"
                    file_path = download_dir / file_name
                    download.save_as(str(file_path))
                    print(f"✅ Downloaded and saved as: {file_path}")
                except Exception as e:
                    print(f"❌ Error downloading {url}: {e}")
                finally:
                    browser.close()

        except FileNotFoundError:
            print(f"❌ Error: File not found at {file_path}")
            print("Please ensure the file exists in the data directory")
        return True