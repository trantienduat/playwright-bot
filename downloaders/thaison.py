import logging
from playwright.sync_api import sync_playwright
from .invoice_downloader import IInvoiceDownloader
from models import Invoice
from pathlib import Path
import os
import zipfile
import tempfile
import shutil

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
                logger.info("🔐 Please complete the CAPTCHA and press Enter to continue...")
                
                # Wait for user to complete CAPTCHA
                page.wait_for_function(
                    "() => document.querySelector('#CaptchaInputText').value.length > 0",
                    timeout=60000  # 1 minute timeout
                )
                
                # Wait for the dropdown toggle button to be visible
                dropdown_selector = "a.dropdown-toggle.btn-download-custom"
                page.wait_for_selector(dropdown_selector, state="visible", timeout=15000)
                logger.info("🔽 Clicking dropdown menu...")
                page.click(dropdown_selector)
                
                # Wait for dropdown menu to open and PDF download link to be visible
                pdf_download_selector = "a[download][href='/tra-cuu/tai-hoa-don-dien-tu?format=pdf']"
                page.wait_for_selector(pdf_download_selector, state="visible", timeout=10000)
                logger.info("📄 Clicking PDF download link...")
                
                # Handle download
                with page.expect_download() as download_info:
                    page.click(pdf_download_selector)
                download = download_info.value

                # Create a temporary file to save the downloaded zip
                with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_zip:
                    temp_zip_path = temp_zip.name
                
                try:
                    download.save_as(temp_zip_path)
                    logger.info(f"📦 Downloaded zip file to temporary location")
                    
                    # Extract PDF from zip file
                    self._extract_pdf_from_zip(temp_zip_path, output_path)
                    logger.info(f"✅ Invoice PDF extracted successfully to: {output_path}")
                    
                finally:
                    # Clean up temporary zip file
                    if os.path.exists(temp_zip_path):
                        os.unlink(temp_zip_path)
                        logger.debug("🗑️ Cleaned up temporary zip file")

                return True
            except Exception as e:
                logger.error(f"❌ Download failed: {str(e)}")
                return False
            finally:
                browser.close()
    
    def _extract_pdf_from_zip(self, zip_path: str, output_path: Path) -> None:
        """
        Extract PDF file from the downloaded zip archive
        """
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # List all files in the zip
                file_list = zip_ref.namelist()
                logger.debug(f"📋 Files in zip: {file_list}")
                
                # Find PDF files in the zip
                pdf_files = [f for f in file_list if f.lower().endswith('.pdf')]
                
                if not pdf_files:
                    raise Exception("No PDF files found in the downloaded zip archive")
                
                if len(pdf_files) > 1:
                    logger.warning(f"⚠️ Multiple PDF files found: {pdf_files}. Using the first one.")
                
                # Extract the first PDF file
                pdf_file = pdf_files[0]
                logger.info(f"📄 Extracting PDF: {pdf_file}")
                
                # Extract to a temporary location first
                with tempfile.TemporaryDirectory() as temp_dir:
                    extracted_path = zip_ref.extract(pdf_file, temp_dir)
                    
                    # Move the extracted PDF to the final output location
                    shutil.move(extracted_path, str(output_path))
                    logger.info(f"✅ PDF extracted and moved to: {output_path}")
                    
        except zipfile.BadZipFile:
            raise Exception("Downloaded file is not a valid zip archive")
        except Exception as e:
            raise Exception(f"Failed to extract PDF from zip: {str(e)}")
                
    def download_invoice(self, invoice: Invoice, output_path: Path) -> bool:
        """
        Download invoice with validation and retry logic
        """
        return self.download_with_validation(invoice, output_path)