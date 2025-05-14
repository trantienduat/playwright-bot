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
logger = logging.getLogger('vina')

class VinaDownloader(IInvoiceDownloader):
    def download(self, invoice: Invoice, output_path: Path) -> bool:
        logger.info(f"🤖 Starting Vina downloader for invoice {invoice.invoice_series}-{invoice.invoice_number}")
        
        # Retrieve the URL from the tax provider
        url = "https://tracuuhd.smartsign.com.vn/"
        if not url:
            logger.error("❌ No search URL provided by the tax provider.")
            return False

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()
            try:
                logger.info(f"🌐 Connecting to thaison portal: {url}")
                page.goto(url)
                logger.debug("Page loaded successfully")

                logger.info("📝 Filling form fields...")
                field_selector = "#ContentPlaceHolder1_txtCode"
                logger.info("⏳ Waiting for the input field to be available...")
                page.wait_for_selector(field_selector, state="visible", timeout=10000)
                page.fill(field_selector, invoice.tracking_code)
                
                logger.info("⚠️ CAPTCHA field detected. Focusing cursor on the CAPTCHA input field...")
                page.focus("#ContentPlaceHolder1_txtCapcha")
                
                logger.info("⏳ Waiting for the dropdown button to be available...")
                page.wait_for_selector("button.btn.dropdown-toggle", state="visible", timeout=10000)
                drop_down_buttons = page.query_selector_all("button.btn.dropdown-toggle")
                for button in drop_down_buttons:
                    if button.text_content().strip() == "Tải File":
                        button.click()
                        break
                else:
                    raise Exception("❌ Dropdown button with text 'Tải File' not found.")
                
                logger.info("🔽 Selecting the dropdown item...")
                dropdown_item_selector = "a.dropdown-item"
                logger.info("⏳ Waiting for the dropdown items to be available...")
                # page.wait_for_selector(dropdown_item_selector, state="visible", timeout=10000)
                dropdown_items = page.query_selector_all(dropdown_item_selector)
                for item in dropdown_items:
                    if "PDF" in item.text_content().strip():
                        item.click()
                        logger.info("✅ Dropdown item 'Tải file PDF' selected successfully.")
                        break
                else:
                    raise Exception("❌ Dropdown item with text 'Tải file PDF' not found.")
                # Handle download
                logger.info("📥 Starting download...")
                with page.expect_download() as download_info:
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