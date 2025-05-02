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

class InvoiceDownloader:
    """Base class for invoice downloaders"""
    def download(self, invoice: Invoice, output_path: Path) -> bool:
        raise NotImplementedException("Subclass must implement download()")

class ViettelDownloader(InvoiceDownloader):
    def download(self, invoice: Invoice, output_path: Path) -> bool:
        """
        Download invoice using Viettel's invoice search page with Playwright.
        
        Args:
            invoice (Invoice): Invoice object containing details.
            output_path (Path): Path to save the downloaded invoice.
        
        Returns:
            bool: True if download is successful, False otherwise.
        """
        url = "https://vinvoice.viettel.vn/utilities/invoice-search"
        download_dir = output_path.parent

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()
            try:
                # Open the invoice search page
                page.goto(url)
                print(f"🌐 Opened URL: {url}")

                # Fill in the form fields
                print(f"🔍 Filling form for invoice: {invoice.tracking_code}")
                if not invoice.seller.tax_code or not invoice.tracking_code:
                    raise ValueError("Missing required fields: seller.tax_code or tracking_code")

                page.fill("[formcontrolname='supplierTaxCode']", invoice.seller.tax_code)
                page.fill("[formcontrolname='reservationCode']", invoice.tracking_code)

                # Wait for user to complete CAPTCHA
                print(f"⚠️ Please complete the CAPTCHA manually in the browser...")
                time.sleep(10)  # Allow time for CAPTCHA completion

                # Submit the form
                print(f"🔍 Submitting form...")
                page.click("button[type='submit']")
                time.sleep(3)  # Wait for the results to load

                # Click the download button
                print(f"📥 Downloading invoice...")
                with page.expect_download() as download_info:
                    page.click("[class='btn btn-link mr-2']")
                download = download_info.value

                # Save the downloaded file
                temp_file_path = download_dir / "temp_invoice.pdf"
                download.save_as(str(temp_file_path))
                print(f"✅ Downloaded temporary file: {temp_file_path}")

                # Rename the downloaded file
                new_filename = f"{invoice.invoice_series}_{invoice.invoice_number}.pdf"
                new_file_path = download_dir / new_filename
                os.rename(temp_file_path, new_file_path)
                print(f"📁 Renamed to: {new_file_path}")

                return True
            except Exception as e:
                print(f"❌ Error downloading invoice: {e}")
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
        print(f"🔗 MISA Downloader: {url}")
        return download_by_url(url, output_path.parent, output_path.name)

class SoftDreamsDownloader(InvoiceDownloader):
    def download(self, invoice: Invoice, output_path: Path) -> bool:
        return False

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
        print(f"❌ Invalid provider_name type: {type(provider_name)}")
        return None

def download_invoices(start_date=None, end_date=None, output_dir='downloads'):
    """Download invoices matching the given filters"""
    
    # Initialize DB connection
    engine = create_engine('sqlite:///vantoi.db')
    
    with Session(engine) as session:
        # Query invoices
        invoices = get_invoices(session, start_date, end_date)
        print(f"\n📊 Found {len(invoices)} invoices")
        
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Generate index file with metadata
        index = {
            'downloaded_at': datetime.now().isoformat(),
            'filters': {
                'start_date': start_date.isoformat() if start_date else None,
                'end_date': end_date.isoformat() if end_date else None,
            },
            'invoices': []
        }
        
        # Process each invoice
        for invoice in invoices:
            filename = f"{invoice.invoice_series}_{invoice.invoice_number}.pdf"
            filepath = output_path / filename
            
            # Check if already downloaded
            if filepath.exists():
                if not invoice.is_downloaded:
                    invoice.is_downloaded = 1
                    session.commit()
                print(f"⏭ Skipping existing {filename}")
                continue
            
            # Fetch tax_provider using tax_provider_id
            tax_provider_id = invoice.tax_provider_id
            if not tax_provider_id:
                print(f"❌ No tax_provider_id found for {filename}")
                continue
            
            # Query the tax_provider from the database
            tax_provider = session.query(TaxProvider).filter_by(id=tax_provider_id).first()
            if not tax_provider:
                print(f"❌ No tax provider found for tax_provider_id: {tax_provider_id}")
                continue
            
            tax_provider_name = tax_provider.name
            if not tax_provider_name:
                print(f"❌ Tax provider name is missing for tax_provider_id: {tax_provider_id}")
                continue
            
            # Get appropriate downloader
            downloader = get_downloader(tax_provider_name)
            if not downloader:
                print(f"❌ No downloader available for {tax_provider_name}")
                continue
            
            try:
                success = downloader.download(invoice, filepath)
                if success:
                    print(f"✅ Downloaded {filename}")
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
                    print(f"❌ Failed to download {filename}")
            except Exception as e:
                print(f"❌ Error downloading {filename}: {e}")
                
            # Rate limit
            time.sleep(1)
        
        # Write index file
        index_file = output_path / 'index.json'
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Created index at {index_file}")
        print(f"📁 Downloads folder: {output_path.absolute()}")

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
    
    # Download invoices
    download_invoices(
        start_date=args.start_date,
        end_date=args.end_date,
        output_dir=args.output
    )
