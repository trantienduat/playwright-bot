from playwright.sync_api import sync_playwright
from .invoice_downloader import IInvoiceDownloader
from models import Invoice
from pathlib import Path
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('buuchinhvt')

class BuuChinhVTDownloader(IInvoiceDownloader):
    def download(self, invoice: Invoice, output_path: Path) -> bool:
        logger.info(f"🤖 Starting Viettel downloader for invoice {invoice.invoice_series}-{invoice.invoice_number}")
        url = f"https://{invoice.seller.tax_code}-tt78.vnpt-invoice.com.vn/HomeNoLogin/SearchByFkey"

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()
            try:
                page.goto(url)
                page.wait_for_selector("#strFkey")
                page.fill("#strFkey", invoice.tracking_code)

                logger.info("⚠️ Waiting for manual CAPTCHA completion...")
                page.focus(".captcha_input.form-control")

                download_button = "[class='icon-download-alt']"
                page.wait_for_selector(download_button)
                print("🔄 Downloading file...")
                with page.expect_download() as download_info:
                    page.click(download_button)
                download = download_info.value

                temp_file_path = output_path.with_name("temp_invoice.pdf")
                download.save_as(str(temp_file_path))
                logger.info(f"✅ Downloaded temporary file: {temp_file_path}")

                os.rename(temp_file_path, output_path)
                logger.info(f"📁 Saved as: {output_path}")

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