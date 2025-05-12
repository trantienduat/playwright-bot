from pathlib import Path
from datetime import datetime
import argparse
import json
import re
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

def construct_file_name(text: str) -> str:
    """Remove Vietnamese tone marks, normalize a given text, remove specific substrings, and remove all spaces."""
    if not isinstance(text, str):
        raise ValueError("Input must be a string")
    
    normalized_text = re.sub("và", '', text, flags=re.IGNORECASE)
    
    # Use unidecode to remove diacritical marks and normalize text
    normalized_text = unidecode(text)
    
    normalized_text = normalized_text.replace(' ', '')
    
    # Replace specific substrings with desired replacements
    substrings_to_replace = {
        'CONGTYTNHHTHUONGMAIVANTAINGUYENPHUOC': 'NGUYENPHUOC',
        'CONGTYTNHHTHUONGMAIMAYVY': 'MAYVY',
        'CONGTYCPDUOCPHAMPHUCTHIEN': 'PHUCTHIEN',
        'CONGTYTNHHTHUONGMAIDICHVUTRANGTHIETBIYTEMINHTRI': 'MINHTRI',
        'CONGTYTNHHFULLERTONHEALTHVIETNAM': 'FULLERTONHEALTHVIETNAM',
        'CONGTYTNHHGRAB': 'GRAB',
        'CONGTYTNHHNEMVANTHANH': 'NEMVANTHANH',
        'CONGTYCOPHANMORINAGANUTRITIONALFOODSVIETNAM': 'MORINAGANUTRITIONALFOODSVIETNAM',
        'CongTyTNHHThuongMaiDauTuDinhVang': 'DinhVang',
        'CONGTYCOPHANTHUONGMAIDICHVUDOANKHOAHOC': 'DOANKHOAHOC',
        'CONGTYTRACHNHIEMHUUHANTHUONGMAIDICHVUTHIETBIYTENGUYENKHOA': 'NGUYENKHOA',
        'CONGTYTNHHTUVANVBP': 'VBP',
        'CONGTYTNHHTHIENANNAM': 'THIENANNAM',
        'CONGTYCOPHANTOPCVVIETNAM': 'TOPCVVIETNAM',
        'CONGTYTNHHDAUTUVAKINHDOANHBATDONGSANMYCANH': 'MYCANH',
        'CONGTYTNHHSANXUATTHUONGMAIVADICHVUALOBUYVIETNAM': 'ALOBUYVIETNAM',
        'CONGTYTNHHSAIGONBOULEVARDCOMPLEX': 'SAIGONBOULEVARDCOMPLEX',
        'CONGTYTNHHTHIETBIYTETHIENTRI': 'THIENTRI',
        'CONGTYTNHHMOTTHANHVIENNHATCHIMAI': 'NHATCHIMAI',
        'CONGTYTNHHKINGSMENVIETNAM': 'KINGSMENVIETNAM',
        'CONGTYCPDUOCLIEUTRUNGUONG2\\(PHYTOPHARMA\\)': 'DUOCLIEUTRUNGUONG2',
        'CONGTYTNHHDKSHVIETNAM': 'DKSHVIETNAM',
        'CONGTYTNHHTHIETBIDUYMINH': 'DUYMINH',
        'CONGTYTNHHTRANGTHIETBIYTETRANVATRUNG': 'TRANVATRUNG',
        'CONGTYCOPHANNIPPONPAPERVIETHOAMY': 'NIPPONPAPERVIETHOAMY',
        'CONGTYTNHHTHUONGMAIVADICHVUCAFAM': 'CAFAM',
        'CONGTYCOPHANCONGNGHEC+': 'CONGNGHEC',
        'CONGTYTNHHCOWAYVINA': 'COWAYVINA',
        'CONGTYTNHHSAIGONBOULEVARDCOMPLEX': 'SAIGONBOULEVARDCOMPLEX',
        'CONGTYCOPHANDAUTUTHIETBIYTETHIENAN': 'THIENAN',
        'CONGTYTNHHINSONGTHINH': 'SONGTHINH',
        'CONGTYTNHHSGSAGAWAVIETNAM': 'SGSAGAWAVIETNAM',
        'CONGTYCOPHANANHDUONGVIETNAM': 'ANHDUONGVIETNAM',
        'CONGTYTNHHTHIETBIYTENDENT': 'NDENT',
        'TrungtamKinhdoanhVNPTthanhphoHoChiMinh-ChinhanhTongcongtyDichvuVienthong': 'VNPT_HCM',
        'TRUNGTAMKINHDOANHVNPT-HANOI-CHINHANHTONGCONGTYDICHVUVIENTHONG': 'VNPT_HaNoi',
    }
    
    for old, new in substrings_to_replace.items():
        normalized_text = re.sub(old, new, normalized_text, flags=re.IGNORECASE)
        
    # Remove all spaces
    normalized_text = normalized_text.replace('.', '')
    
    # Return the cleaned text
    return normalized_text.strip()

def get_downloader(provider_name: str) -> IInvoiceDownloader:
    """Factory method to get the appropriate downloader"""
    downloaders = {
        'softdreams': SoftDreamsDownloader(),
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
    
    engine = create_engine('sqlite:///dym_q1.db')
    
    with Session(engine) as session:
        invoices = get_invoices(session, start_date, end_date)
        logger.info(f"📊 Found {len(invoices)} invoices")
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        for invoice in invoices:
            logger.debug(f"Processing invoice: {invoice.invoice_series}-{invoice.invoice_number}")
            seller = session.query(Seller).filter_by(id=invoice.seller_id).first()
            seller_name = seller.name if seller else "Unknown"
            filename = f"{construct_file_name(seller_name)}_{invoice.invoice_number}.pdf"
            # filename = f"{month_abbr}_{invoice.invoice_form}_{invoice.invoice_series}_{invoice.invoice_number}.pdf"
            filepath = output_path / filename
            print(filename)
            
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
    parser.add_argument('--output', default='downloads',
                      help='Output directory (default: downloads)')
    
    args = parser.parse_args()
    
    download_invoices(
        start_date=args.start_date,
        end_date=args.end_date,
        output_dir=args.output
    )
