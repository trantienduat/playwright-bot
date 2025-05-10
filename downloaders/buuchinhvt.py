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
        download_dir = output_path.parent

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
                # Extract the href attribute of the download button
                # logger.info("🔄 Downloading file...")
                print("🔄 Downloading file...")
                with page.expect_download() as download_info:
                    page.click(download_button)
                download = download_info.value
                
                temp_file_path = download_dir / "temp_invoice.pdf"
                download.save_as(str(temp_file_path))
                logger.info(f"✅ Downloaded temporary file: {temp_file_path}")

                month_abbr = invoice.invoice_timestamp.strftime("%b") if invoice.invoice_timestamp else "Unknown"
                new_filename = f"{month_abbr}_{invoice.invoice_series}_{invoice.invoice_number}.pdf"
                new_file_path = download_dir / new_filename
                os.rename(temp_file_path, new_file_path)
                logger.info(f"📁 Renamed to: {new_file_path}")

                return True
            except Exception as e:
                logger.error(f"❌ Download failed: {str(e)}")
                return False
            finally:
                browser.close()