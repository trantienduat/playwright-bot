from pathlib import Path
from datetime import datetime
import argparse
import os
import json
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from db import get_invoices
from models import Invoice, init_db
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
        return False

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
            
            # Skip if already downloaded
            if filepath.exists():
                print(f"⏭ Skipping existing {filename}")
                continue
                
            # Get tax_provider name from tax_provider_id
            tax_provider_id = getattr(invoice, 'tax_provider_id', None)
            if not tax_provider_id:
                print(f"❌ No tax_provider_id found for {filename}")
                continue
            
            # Fetch tax_provider name (assuming a method or mapping exists)
            tax_provider_name = invoice.tax_provider.name if invoice.tax_provider else None
            if not tax_provider_name:
                print(f"❌ No tax provider name found for tax_provider_id: {tax_provider_id}")
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
    
    # Initialize database if needed
    init_db()
    
    # Download invoices
    download_invoices(
        start_date=args.start_date,
        end_date=args.end_date,
        output_dir=args.output
    )
