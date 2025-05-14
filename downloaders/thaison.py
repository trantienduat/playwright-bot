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
logger = logging.getLogger('thaison')

class ThaiSonDownloader(IInvoiceDownloader):
    def download(self, invoice: Invoice, output_path: Path) -> bool:
        logger.info(f"🤖 Starting Thaison downloader for invoice {invoice.invoice_series}-{invoice.invoice_number}")
        url = "https://einvoice.vn/tra-cuu"

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()
            try:
                logger.info(f"🌐 Connecting to thaison portal: {url}")
                page.goto(url)
                logger.debug("Page loaded successfully")

                field_selector = "[class='col-md-7 form-control h36 fix-with-content opacity-placeholder MaNhanHoaDon']"
                page.wait_for_selector(field_selector, state="visible", timeout=10000)
                page.fill(field_selector, invoice.tracking_code)
                
                page.focus("#CaptchaInputText")
                
                download_button_selector = "a.btn-icon-fix[href*='/tra-cuu/tai-hoa-don-dien-tu?format=pdf']"
                page.wait_for_selector(download_button_selector, state="visible", timeout=10000)
                
                # Handle download
                with page.expect_download() as download_info:
                    page.click(download_button_selector)
                download = download_info.value

                download.save_as(str(output_path))
                logger.info(f"✅ Invoice downloaded successfully to: {output_path}")

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