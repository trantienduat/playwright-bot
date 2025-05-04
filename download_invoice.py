from pathlib import Path
from datetime import datetime
import argparse
import os
import json
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from db import get_invoices
from models import Invoice, init_db, TaxProvider
from typing import Dict
import requests
from playwright.sync_api import sync_playwright
import time
from helpers import download_by_url  # Import the working function from helpers.py
import zipfile
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('invoice_downloader')

class InvoiceDownloader:
    """Base class for invoice downloaders"""
    def download(self, invoice: Invoice, output_path: Path) -> bool:
        raise NotImplementedException("Subclass must implement download()")

class ViettelDownloader(InvoiceDownloader):
    def download(self, invoice: Invoice, output_path: Path) -> bool:
        logger.info(f"🤖 Starting Viettel downloader for invoice {invoice.invoice_series}-{invoice.invoice_number}")
        url = "https://vinvoice.viettel.vn/utilities/invoice-search"
        download_dir = output_path.parent

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

                logger.info("📝 Filling form fields...")
                page.fill("[formcontrolname='supplierTaxCode']", invoice.seller.tax_code)
                page.fill("[formcontrolname='reservationCode']", invoice.tracking_code)
                logger.debug(f"Form filled with tax_code: {invoice.seller.tax_code}")

                logger.info("⚠️ Please complete CAPTCHA and click Search button manually...")
                
                # Wait for download button to appear after manual search
                download_button = "[class='btn btn-link mr-2']"
                logger.info("⏳ Waiting for download button to appear...")
                page.wait_for_selector(download_button, state="visible", timeout=60000)
                
                # Handle download
                logger.info("📥 Starting download...")
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

class VNPTDownloader(InvoiceDownloader):
    def download(self, invoice: Invoice, output_path: Path) -> bool:
        return False

class MISADownloader(InvoiceDownloader):
    def download(self, invoice: Invoice, output_path: Path) -> bool:
        """Download invoice using MISA's URL"""
        url = f"https://www.meinvoice.vn/tra-cuu/DownloadHandler.ashx?Type=pdf&Viewer=1&Code={invoice.tracking_code}"
        logger.info(f"🔗 MISA Downloader: {url}")
        return download_by_url(url, output_path.parent, output_path.name)

class SoftDreamsDownloader(InvoiceDownloader):
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

class DNADownloader(InvoiceDownloader):
    def download(self, invoice: Invoice, output_path: Path) -> bool:
        return False

class InvoiceDownloader(InvoiceDownloader):
    def download(self, invoice: Invoice, output_path: Path) -> bool:
        return False

class BKAVDownloader(InvoiceDownloader):
    def download(self, invoice: Invoice, output_path: Path) -> bool:
        return False

class WintechDownloader(InvoiceDownloader):
    def download(self, invoice: Invoice, output_path: Path) -> bool:
        return False

class ThaiSonDownloader(InvoiceDownloader):
    def download(self, invoice: Invoice, output_path: Path) -> bool:
        return False

class BuuChinhVTDownloader(InvoiceDownloader):
    def download(self, invoice: Invoice, output_path: Path) -> bool:
        return False

class VisnamDownloader(InvoiceDownloader):
    def download(self, invoice: Invoice, output_path: Path) -> bool:
        return False

class FPTDownloader(InvoiceDownloader):
    def download(self, invoice: Invoice, output_path: Path) -> bool:
        return False

def get_downloader(provider_name: str) -> InvoiceDownloader:
    """Factory method to get the appropriate downloader"""
    downloaders = {
        'softdreams': SoftDreamsDownloader(),
        'dna': DNADownloader(),
        'misa': MISADownloader(),
        'invoice': InvoiceDownloader(),
        'viettel': ViettelDownloader(),
        'bkav': BKAVDownloader(),
        'wintech': WintechDownloader(), 
        'thaison': ThaiSonDownloader(),
        'buuchinhvt': BuuChinhVTDownloader(),
        'visnam': VisnamDownloader(),
        'fpt': FPTDownloader()
    }
    if isinstance(provider_name, str):
        return downloaders.get(provider_name.lower())
    else:
        logger.error(f"❌ Invalid provider_name type: {type(provider_name)}")
        return None

def download_invoices(start_date=None, end_date=None, output_dir='downloads'):
    logger.info("🚀 Starting invoice download process")
    logger.info(f"Date range: {start_date} to {end_date}")
    logger.info(f"Output directory: {output_dir}")
    
    engine = create_engine('sqlite:///vantoi.db')
    
    with Session(engine) as session:
        invoices = get_invoices(session, start_date, end_date)
        logger.info(f"📊 Found {len(invoices)} invoices")
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        index = {
            'downloaded_at': datetime.now().isoformat(),
            'filters': {
                'start_date': start_date.isoformat() if start_date else None,
                'end_date': end_date.isoformat() if end_date else None,
            },
            'invoices': []
        }
        
        for invoice in invoices:
            logger.debug(f"Processing invoice: {invoice.invoice_series}-{invoice.invoice_number}")
            month_abbr = invoice.invoice_timestamp.strftime("%b") if invoice.invoice_timestamp else "Unknown"
            filename = f"{month_abbr}_{invoice.invoice_series}_{invoice.invoice_number}.pdf"
            filepath = output_path / filename
            
            if filepath.exists():
                if not invoice.is_downloaded:
                    invoice.is_downloaded = 1
                    session.commit()
                logger.info(f"⏭ Skipping existing {filename}")
                continue
            
            tax_provider_id = invoice.tax_provider_id
            if not tax_provider_id:
                logger.error(f"❌ No tax_provider_id found for {filename}")
                continue
            
            tax_provider = session.query(TaxProvider).filter_by(id=tax_provider_id).first()
            if not tax_provider:
                logger.error(f"❌ No tax provider found for tax_provider_id: {tax_provider_id}")
                continue
            
            tax_provider_name = tax_provider.name
            if not tax_provider_name:
                logger.error(f"❌ Tax provider name is missing for tax_provider_id: {tax_provider_id}")
                continue
            
            downloader = get_downloader(tax_provider_name)
            if not downloader:
                logger.error(f"❌ No downloader available for {tax_provider_name}")
                continue
            
            try:
                success = downloader.download(invoice, filepath)
                print()
                if success:
                    logger.info(f"✅ Successfully downloaded: {filename}")
                    invoice.is_downloaded = 1
                    session.commit()
                    index['invoices'].append({
                        'filename': filename,
                        'series': invoice.invoice_series,
                        'number': invoice.invoice_number,
                        'timestamp': invoice.invoice_timestamp.isoformat(),
                        'provider': {
                            'tax_provider_id': tax_provider_id,
                            'tax_provider_name': tax_provider_name
                        }
                    })
                else:
                    logger.error(f"❌ Failed to download: {filename}")
            except Exception as e:
                logger.error(f"❌ Error processing {filename}: {e}")
            
            logger.debug("Applying rate limit...")
            time.sleep(1)
        
        index_file = output_path / 'index.json'
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Created index at {index_file}")
        logger.info(f"📁 Downloads folder: {output_path.absolute()}")

def parse_date(date_string):
    """Parse date string in DD/MM/YYYY format"""
    try:
        return datetime.strptime(date_string, "%d/%m/%Y")
    except ValueError:
        raise argparse.ArgumentTypeError("Invalid date format. Use DD/MM/YYYY")
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Download invoices for a date range')
    parser.add_argument('--start-date', type=parse_date,
                      help='Start date (DD/MM/YYYY)')
    parser.add_argument('--end-date', type=parse_date,
                      help='End date (DD/MM/YYYY)')
    parser.add_argument('--output', default='downloads',
                      help='Output directory (default: downloads)')
    
    args = parser.parse_args()
    
    download_invoices(
        start_date=args.start_date,
        end_date=args.end_date,
        output_dir=args.output
    )
