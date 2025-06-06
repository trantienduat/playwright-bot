from datetime import datetime
import argparse
import json
import re
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from db import get_invoices
from models import TaxProvider, Seller
from downloaders.viettel import ViettelDownloader
from downloaders.fpt import FPTDownloader
from downloaders.invoice_downloader import IInvoiceDownloader
from downloaders.softdream import SoftDreamsDownloader
from downloaders.misa import MISADownloader
from downloaders.buuchinhvt import BuuChinhVTDownloader
from downloaders.thaison import ThaiSonDownloader
from downloaders.hilo import HiloDownloader
from downloaders.vina import VinaDownloader
import time
import logging
from unidecode import unidecode
from config.profile_manager import profile_manager

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

# class VisnamDownloader(InvoiceDownloader):
#     def download(self, invoice: Invoice, output_path: Path) -> bool:
#         return False

def construct_file_name(text: str, month_abbr: str) -> str:
    """Remove Vietnamese tone marks, normalize a given text and replace with short name."""
    if not isinstance(text, str):
        raise ValueError("Input must be a string")

    # Get seller_short_name mappings from active profile
    seller_mappings = profile_manager.get_active_profile().get('seller_short_name', {})
    
    # First try exact match in the mappings
    if text in seller_mappings:
        return f"{month_abbr}_{seller_mappings[text]}"
    
    # If not found, raise an error instead of returning None
    raise KeyError(f"Seller '{text}' not found in seller_short_name mapping. Please add it to your profile configuration.")



def get_downloader(provider_name: str) -> IInvoiceDownloader:
    """Factory method to get the appropriate downloader"""
    downloaders = {
        'softdreams': SoftDreamsDownloader(),
        # 'dna': DNADownloader(),
        'misa': MISADownloader(),
        'viettel': ViettelDownloader(),
        # 'bkav': BKAVDownloader(),
        # 'wintech': WintechDownloader(), 
        'thaison': ThaiSonDownloader(),
        'buuchinhvt': BuuChinhVTDownloader(),
        'vina': VinaDownloader(),
        # 'visnam': VisnamDownloader(),
        'fpt': FPTDownloader(),
        'hilo': HiloDownloader()
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

    
    with profile_manager.get_session() as session:
        invoices = get_invoices(session, start_date, end_date)
        logger.info(f"📊 Found {len(invoices)} invoices")
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        for invoice in invoices:
            logger.debug(f"Processing invoice: {invoice.invoice_series}-{invoice.invoice_number}")
            seller = session.query(Seller).filter_by(id=invoice.seller_id).first()
            seller_name = seller.name if seller else "Unknown"
            
            # Extract month abbreviation from invoice.invoice_timestamp
            invoice_month = None
            if hasattr(invoice, "invoice_timestamp") and invoice.invoice_timestamp:
                invoice_month = invoice.invoice_timestamp.strftime("%b")
            else:
                invoice_month = "Unknown"

            try:
                filename = construct_file_name(seller_name, invoice_month)
                filename = f"{filename}_{invoice.invoice_number}.pdf"
            except KeyError as e:
                logger.error(f"❌ {e}")
                continue
            
            filepath = output_path / filename
            
            if filepath.exists():
                if not invoice.is_downloaded:
                    invoice.is_downloaded = 1
                    session.commit()
                logger.info(f"⏭ Skipping existing {filename}")
                continue
            
            if not invoice.tracking_code:
                logger.info(f"⏭ Skipping {filename} (missing tracking code)")
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
                success = downloader.download_invoice(invoice, filepath)
                print()
                if success:
                    logger.info(f"✅ Successfully downloaded: {filename}")
                    invoice.is_downloaded = 1
                    session.commit()

                else:
                    logger.error(f"❌ Failed to download: {filename}")
            except Exception as e:
                logger.error(f"❌ Error processing {filename}: {e}")
            
            logger.debug("Applying rate limit...")
            time.sleep(1)
        
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
    
    args = parser.parse_args()
    

    
    download_path = profile_manager.get_active_profile()['download_path']
    
    download_invoices(
        start_date=args.start_date,
        end_date=args.end_date,
        output_dir=download_path
    )
