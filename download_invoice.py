from pathlib import Path
from datetime import datetime
import argparse
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from db import get_invoices
from models import TaxProvider
from downloaders.viettel import ViettelDownloader
from downloaders.fpt import FPTDownloader
from downloaders.invoice_downloader import IInvoiceDownloader
from downloaders.softdream import SoftDreamsDownloader
from downloaders.misa import MISADownloader
from downloaders.buuchinhvt import BuuChinhVTDownloader
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('invoice_downloader')

# class VNPTDownloader(InvoiceDownloader):
#     def download(self, invoice: Invoice, output_path: Path) -> bool:
#         return False

# class DNADownloader(InvoiceDownloader):
#     def download(self, invoice: Invoice, output_path: Path) -> bool:
#         return False

# class InvoiceDownloader(InvoiceDownloader):
#     def download(self, invoice: Invoice, output_path: Path) -> bool:
#         return False

# class BKAVDownloader(InvoiceDownloader):
#     def download(self, invoice: Invoice, output_path: Path) -> bool:
#         return False

# class WintechDownloader(InvoiceDownloader):
#     def download(self, invoice: Invoice, output_path: Path) -> bool:
#         return False

# class ThaiSonDownloader(InvoiceDownloader):
#     def download(self, invoice: Invoice, output_path: Path) -> bool:
#         return False

# class VisnamDownloader(InvoiceDownloader):
#     def download(self, invoice: Invoice, output_path: Path) -> bool:
#         return False



def get_downloader(provider_name: str) -> IInvoiceDownloader:
    """Factory method to get the appropriate downloader"""
    downloaders = {
        'softdreams': SoftDreamsDownloader(),
        # 'dna': DNADownloader(),
        'misa': MISADownloader(),
        'viettel': ViettelDownloader(),
        # 'bkav': BKAVDownloader(),
        # 'wintech': WintechDownloader(), 
        # 'thaison': ThaiSonDownloader(),
        'buuchinhvt': BuuChinhVTDownloader(),
        # 'visnam': VisnamDownloader(),
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
