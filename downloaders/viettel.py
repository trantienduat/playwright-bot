import logging
from playwright.sync_api import sync_playwright
from .invoice_downloader import IInvoiceDownloader
from models import Invoice
from pathlib import Path
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('viettel')

class ViettelDownloader(IInvoiceDownloader):
    def download(self, invoice: Invoice, output_path: Path) -> bool:
        logger.info(f"🤖 Starting Viettel downloader for invoice {invoice.invoice_series}-{invoice.invoice_number}")
        url = "https://vinvoice.viettel.vn/utilities/invoice-search"

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()
            try:
                logger.info(f"🌐 Connecting to Viettel portal: {url}")
                page.goto(url)
                logger.debug("Page loaded successfully")

                if not invoice.seller.tax_code or not invoice.tracking_code:
                    raise ValueError("Missing required fields: seller.tax_code or tracking_code")

                page.fill("[formcontrolname='supplierTaxCode']", invoice.seller.tax_code)
                page.fill("[formcontrolname='reservationCode']", invoice.tracking_code)
                
                # Wait for download button to appear after manual search
                download_button = "[class='btn btn-link mr-2']"
                page.wait_for_selector(download_button, state="visible", timeout=60000)
                
                # Handle download
                logger.info("📥 Starting download...")
                with page.expect_download() as download_info:
                    page.click(download_button)
                download = download_info.value

                temp_file_path = output_path.parent / "temp_invoice.pdf"
                download.save_as(str(temp_file_path))
                logger.info(f"✅ Downloaded temporary file: {temp_file_path}")

                os.rename(temp_file_path, output_path)
                logger.info(f"📁 Renamed to: {output_path}")

                return True
            except Exception as e:
                logger.error(f"❌ Download failed: {str(e)}")
                return False
            finally:
                browser.close()


    def download_invoice(self, invoice: Invoice, output_path: Path) -> bool:
        """
        Download invoice with validation and retry logic
        """
        return self.download_with_validation(invoice, output_path)