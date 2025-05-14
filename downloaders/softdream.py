from playwright.sync_api import sync_playwright
from .invoice_downloader import IInvoiceDownloader
from models import Invoice
from pathlib import Path
import logging
import zipfile
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('softdreams')

class SoftDreamsDownloader(IInvoiceDownloader):
    def download(self, invoice: Invoice, output_path: Path) -> bool:
        logger.info(f"🤖 Starting SoftDreams downloader for invoice {invoice.invoice_series}-{invoice.invoice_number}")
        
        domains = [
            f"https://{invoice.seller.tax_code}hd.easyinvoice.com.vn",
            f"https://{invoice.seller.tax_code}hd.easyinvoice.vn"
        ]
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            success = False
            
            try:
                for url in domains:
                    try:
                        context = browser.new_context(accept_downloads=True)
                        page = context.new_page()
                        
                        logger.info(f"🌐 Connecting to portal: {url}")
                        try:
                            page.goto(url, wait_until="load", timeout=3000)
                        except Exception as e:
                            logger.error(f"❌ Page navigation failed: {e}")
                            logger.warning(f"⚠️ Domain {url} failed, trying alternative domain...")
                            continue  # Switch to the next domain_page()
                        
                        logger.info(f"🌐 Connecting to portal: {url}")
                        page.goto(url, wait_until="networkidle")

                        logger.info("📝 Filling tracking code...")
                        page.fill("#iFkey", invoice.tracking_code)

                        logger.info("⚠️ Waiting for manual CAPTCHA completion...")
                        page.focus("#Capcha")

                        button_selector = "button[name='downloadPdfAndFileAttach']"
                        logger.info("⏳ Waiting for download button to appear...")
                        page.wait_for_selector(button_selector, state="visible", timeout=60000)

                        logger.info("📥 Starting download...")
                        with page.expect_download() as download_info:
                            page.click(button_selector)

                        temp_zip = output_path.parent / "temp_invoice.zip"
                        download_info.value.save_as(temp_zip)

                        if not temp_zip.exists() or temp_zip.stat().st_size == 0:
                            raise Exception("Download failed: Invalid or empty zip file")

                        try:
                            with zipfile.ZipFile(temp_zip) as zip_ref:
                                pdf_files = [f for f in zip_ref.namelist() if f.lower().endswith('.pdf')]
                                if not pdf_files:
                                    raise Exception("No PDF file found in zip")
                                with zip_ref.open(pdf_files[0]) as pdf_file:
                                    output_path.write_bytes(pdf_file.read())
                            logger.info(f"✅ PDF extracted: {output_path} ({output_path.stat().st_size} bytes)")
                            success = True
                            break  # Exit the domain loop on success
                            
                        finally:
                            if temp_zip.exists():
                                temp_zip.unlink()
                                logger.info("🧹 Cleaned up temporary zip file")
                            context.close()
                            
                    except Exception as e:
                        error_msg = str(e)
                        context.close()
                        
                        # If this is not a name resolution error, or we're on the last domain, log and break
                        if "ERR_NAME_NOT_RESOLVED" not in error_msg or url == domains[-1]:
                            logger.error(f"❌ Download failed: {error_msg}")
                            break
                            
                        # Otherwise, log retry attempt and continue to next domain
                        logger.warning(f"⚠️ Domain {url} not resolved, trying alternative domain...")
                        continue
                        
            finally:
                browser.close()
                
            return success
        
    def download_invoice(self, invoice: Invoice, output_path: Path) -> bool:
        """
        Download invoice with validation and retry logic
        """
        return self.download_with_validation(invoice, output_path)