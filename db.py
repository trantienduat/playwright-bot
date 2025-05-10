from sqlalchemy import create_engine, select, text, func, case
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pathlib import Path
import json
import yaml
from models import Seller, TaxProvider, Invoice, Base, init_db
from datetime import datetime, timedelta
import dateutil.parser
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint
import csv

app = typer.Typer(help="Invoice Database CLI")
console = Console()

def load_sellers_from_json(json_path):
    """Load seller data from JSON file"""
    if not Path(json_path).exists():
        print(f"❌ {json_path} not found")
        return []
    
    with open(json_path, 'r', encoding='utf-8') as f:
        invoices = json.load(f)
    
    # Extract unique sellers by tax_code
    sellers = {}
    for invoice in invoices:
        tax_code = invoice.get('nbmst')
        name = invoice.get('nbten')
        if tax_code and name:
            if tax_code not in sellers:
                sellers[tax_code] = name
                # print(f"Found seller: {tax_code} - {name}")
    
    seller_list = [Seller(tax_code=tc, name=name) for tc, name in sellers.items()]
    print(f"\n📊 Total unique sellers found: {len(seller_list)}")
    return seller_list

def load_tax_providers_from_json(json_path):
    """Load tax provider data from JSON file and merge with config settings"""
    if not Path(json_path).exists():
        print(f"❌ {json_path} not found")
        return []
    
    with open(json_path, 'r', encoding='utf-8') as f:
        invoices = json.load(f)
    
    tax_providers = {}
    provider_settings = load_search_urls()
    
    for invoice in invoices:
        name = invoice.get('ngcnhat')
        if name and name.startswith('tvan_'):
            name = name.replace('tvan_', '')
            if name not in tax_providers:
                settings = provider_settings.get(name, {})
                provider = TaxProvider(
                    name=name,
                    status=settings.get('status', 'TBD'),
                    note=settings.get('note'),
                    search_url=settings.get('search_url')  # Updated key
                )
                tax_providers[name] = provider
                # print(f"Found tax provider: {name} [Status: {provider.status}]")
    
    return list(tax_providers.values())

def load_search_urls():
    """Load tax provider settings from config.yml"""
    config_path = Path('config') / 'config.yml'
    if not config_path.exists():
        print("❌ config.yml not found")
        return {}
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
        return config.get('tax_providers', {})

def merge_tax_providers(session, new_tax_providers):
    """Merge tax providers while handling duplicates and update settings"""
    existing = {tp.name: tp for tp in get_existing_tax_providers(session)}
    print(f"\n💾 Existing tax providers in DB: {len(existing)}")
    
    provider_settings = load_search_urls()
    merged = []
    
    for tp in new_tax_providers:
        settings = provider_settings.get(tp.name, {})
        if tp.name not in existing:
            rprint(f"[green]+ Adding[/green] {tp.name} [Status: {tp.status}]")
            tp.search_url = settings.get('search_url')  # Updated key
            merged.append(tp)
        else:
            existing_tp = existing[tp.name]
            existing_tp.search_url = settings.get('search_url', existing_tp.search_url)  # Updated key
            existing_tp.status = settings.get('status', existing_tp.status)
            existing_tp.note = settings.get('note', existing_tp.note)
            rprint(f"[blue]~ Updated[/blue] {tp.name} [Status: {existing_tp.status}]")
    
    # Add only new tax providers
    for tp in merged:
        session.add(tp)
    session.commit()
    return merged

def merge_sellers(session, new_sellers):
    """Merge sellers while handling duplicates"""
    existing = {s.tax_code: s for s in get_existing_sellers(session)}
    print(f"\n💾 Existing sellers in DB: {len(existing)}")

    merged = []
    updated = []
    for seller in new_sellers:
        if seller.tax_code not in existing:
            print(f"+ Adding new seller: {seller.tax_code} - {seller.name}")
            merged.append(seller)
        else:
            # print(f"~ Updating seller: {seller.tax_code} - {seller.name}")
            existing[seller.tax_code].name = seller.name
            updated.append(existing[seller.tax_code])
    
    # Add new sellers
    for seller in merged:
        session.add(seller)
    session.commit()
    
    return merged, updated

def get_existing_sellers(session):
    """Get list of existing sellers from DB"""
    return session.query(Seller).all()

def get_existing_tax_providers(session):
    """Get list of existing tax providers from DB"""
    return session.query(TaxProvider).all()

def load_invoices_from_json(session, json_path):
    """Load and parse invoice data from JSON file"""
    if not Path(json_path).exists():
        print(f"❌ {json_path} not found")
        return []

    with open(json_path, 'r', encoding='utf-8') as f:
        raw_invoices = json.load(f)

    invoices = []
    tax_code_to_seller = {s.tax_code: s for s in get_existing_sellers(session)}
    name_to_tax_provider = {tp.name: tp for tp in get_existing_tax_providers(session)}

    total_found = 0
    skipped = 0
    for raw in raw_invoices:
        tax_code = raw.get('nbmst')  # Seller's tax code
        tax_provider_name = raw.get('ngcnhat', '').replace('tvan_', '') if raw.get('ngcnhat') else None
        
        if not tax_code:
            continue

        seller = tax_code_to_seller.get(tax_code)
        tax_provider = name_to_tax_provider.get(tax_provider_name) if tax_provider_name else None
        
        if not seller:
            continue

        # Extract tracking_code from ttkhac
        tracking_code = None
        for field in raw.get('ttkhac', []):
            if field.get('ttruong') in ["Mã số bí mật", "Fkey"]:
                tracking_code = field.get('dlieu')
        if raw.get('mhdon'):
            tracking_code = raw.get('mhdon')

        # Check if invoice exists using SQL query
        existing_invoice = session.query(Invoice).filter(
            Invoice.invoice_form == raw.get('khmshdon'),
            Invoice.invoice_series == raw.get('khhdon'),
            Invoice.invoice_number == raw.get('shdon')
        ).first()

        if existing_invoice:
            # Update tracking_code if it is missing and a new tracking_code is available
            if not existing_invoice.tracking_code and tracking_code:
                existing_invoice.tracking_code = tracking_code
                session.commit()
                print(f"🔄 Updated tracking_code for invoice: {raw.get('khmshdon')}-{raw.get('khhdon')}-{raw.get('shdon')}")
            else:
                # print(f"⏭ Skipping existing invoice: {raw.get('khmshdon')}-{raw.get('khhdon')}-{raw.get('shdon')}")
                skipped += 1
            continue

        invoice = Invoice(
            invoice_form=raw.get('khmshdon'),
            invoice_series=raw.get('khhdon'),
            invoice_timestamp=dateutil.parser.parse(raw.get('tdlap')) if raw.get('tdlap') else None,
            invoice_number=raw.get('shdon'),
            tracking_code=tracking_code,  # Set the extracted tracking_code
            seller_id=seller.id if seller else None,  # Updated to seller_id
            tax_provider_id=tax_provider.id if tax_provider else None
        )
        invoices.append(invoice)
        total_found += 1
        if total_found % 100 == 0:  # Show progress every 100 invoices
            rprint(f"[cyan]⏳ Processing... Found {total_found:,} invoices[/cyan]")
    rprint(f"[green]✓[/green] Skipped: {skipped} invoices")
    rprint(f"\n[green]📋 Total invoices found: {total_found:,}[/green]")
    return invoices

def merge_invoices(session, new_invoices):
    """Merge invoices while handling duplicates using database constraints"""
    merged = []
    for invoice in new_invoices:
        try:
            session.add(invoice)
            session.flush()
            merged.append(invoice)
        except IntegrityError:
            session.rollback()
            print(f"⏭ Skipping duplicate invoice: {invoice.invoice_form}-{invoice.invoice_series}-{invoice.invoice_number}")
            continue
    
    session.commit()
    rprint(f"[green]✓ Successfully merged {len(merged):,} new invoices[/green]")
    return merged

def get_invoices(session, start_date=None, end_date=None, tax_code=None):
    """Get invoices with optional date range and tax code filters, including all matches for day, month, and year"""
    query = session.query(Invoice).join(Invoice.seller)  # Use the relationship

    if start_date:
        start_date = datetime(start_date.year, start_date.month, start_date.day)  # Normalize to start of the day
        query = query.filter(Invoice.invoice_timestamp >= start_date)
    if end_date:
        end_date = datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59)  # Normalize to end of the day
        query = query.filter(Invoice.invoice_timestamp <= end_date)
    if tax_code:
        query = query.filter(Seller.tax_code == tax_code)

    return query.order_by(Invoice.invoice_timestamp.desc()).all()

def get_invoice_stats(session):
    """Get summary stats of invoices"""
    total = session.query(Invoice).count()
    
    # Get date range
    date_range = session.query(
        func.min(Invoice.invoice_timestamp),
        func.max(Invoice.invoice_timestamp)
    ).first()
    
    # Get tax providers and their occurrence with download stats
    tax_provider_stats = session.query(
        TaxProvider.name,
        func.count(Invoice.id),
        func.sum(case((Invoice.is_downloaded == 1, 1), else_=0)).label('downloaded_count')
    ).join(Invoice, TaxProvider.id == Invoice.tax_provider_id)\
     .group_by(TaxProvider.name).all()
    
    # Get overall download stats
    download_stats = session.query(
        func.count(Invoice.id),
        func.sum(case((Invoice.is_downloaded == 1, 1), else_=0))
    ).first()
    
    return {
        'total_invoices': total,
        'total_downloaded': download_stats[1] or 0,
        'download_percentage': round((download_stats[1] or 0) / total * 100, 2) if total > 0 else 0,
        'date_from': date_range[0] if date_range[0] else None,
        'date_to': date_range[1] if date_range[1] else None,
        'tax_provider_stats': [
            {
                'name': name,
                'total': count,
                'downloaded': downloaded or 0,
                'percentage': round((downloaded or 0) / count * 100, 2) if count > 0 else 0
            }
            for name, count, downloaded in tax_provider_stats
        ]
    }
    
def check_invoice_in_KIMTIN_list(series, number, KINTIM_list_path):
    """
    Check if invoice exists in KIMTIN list and extract tracking code
    Args:
        series: invoice series (e.g., K25TKT)
        number: invoice number
        KINTIM_list_path: path to the KIMTIN_list.txt file containing line by line entries
    Returns:
        tracking_code or None if not found
    """
    try:
        with open(KINTIM_list_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:  # Skip empty lines
                    continue
                    
                # Format example: K25TKT-0000012345-20231010-TRACKING123
                parts = line.split('_')
                if len(parts) == 4:
                    KIMTIN_series = parts[0]
                    KIMTIN_number = parts[1].lstrip('0')  # Remove leading zeros
                    tracking_code = parts[3]
                    
                    if KIMTIN_series == series and KIMTIN_number == number:
                        return tracking_code
                        
        return None
    except FileNotFoundError:
        rprint(f"[red]Error: File not found at {KINTIM_list_path}[/red]")
        return None
    except Exception as e:
        rprint(f"[red]Error reading file: {str(e)}[/red]")
        return None

def fetch_and_update_invoices(session):
    """
    Fetch invoices for seller 52 and update tracking codes - KIM TÍN
    """
    KINTIM_list_path = "data/KIMTIN_list.txt"
    
    # Fetch seller ID by name containing "KIM TÍN"
    seller = session.query(Seller).filter(Seller.name.contains("KIM TÍN")).first()
    if not seller:
        rprint("[red]❌ No seller found with name containing 'KIM TÍN'[/red]")
        return

    # Fetch invoices for the found seller
    invoices = session.query(Invoice).filter(
        Invoice.seller_id == seller.id,
        Invoice.tracking_code.is_(None)
    ).all()

    rprint(f"[cyan]Found {len(invoices)} invoices with no tracking_code[/cyan]")
    updated_count = 0
    skipped_count = 0
    for invoice in invoices:
        tracking_code = check_invoice_in_KIMTIN_list(
            invoice.invoice_series,
            invoice.invoice_number,
            KINTIM_list_path
        )
        
        if tracking_code:
            invoice.tracking_code = tracking_code
            updated_count += 1
        else:
            skipped_count += 1
            rprint(f"[yellow]⏭ Skipping invoice: {invoice.invoice_form}-{invoice.invoice_series}-{invoice.invoice_number}[/yellow]")
    
    session.commit()
    rprint(f"[blue]↻[/blue] Updated {updated_count} invoices with tracking codes")

@app.command()
def fetch(
    input_file: str = typer.Option(..., "--input", "-i", help="Path to input JSON file")
):
    """Fetch and load all invoice data from JSON file into database"""
    engine = create_engine('sqlite:///vantoi.db')
    init_db()
    
    with Session(engine) as session:
        # Process tax providers
        new_tax_providers = load_tax_providers_from_json(input_file)
        merged_tax_providers = merge_tax_providers(session, new_tax_providers)
        rprint(f"[green]✓[/green] Added {len(merged_tax_providers)} tax providers")
        
        # Process sellers
        new_sellers = load_sellers_from_json(input_file)
        merged, updated = merge_sellers(session, new_sellers)
        rprint(f"[green]✓[/green] Added {len(merged)} new sellers")
        rprint(f"[blue]↻[/blue] Updated {len(updated)} sellers")
        
        # Process invoices
        new_invoices = load_invoices_from_json(session, input_file)
        merged_invoices = merge_invoices(session, new_invoices)
        rprint(f"[green]✓[/green] Added {len(merged_invoices)} invoices")
        
        # Fetch and update invoices for seller 52
        rprint("[cyan]Processing KIM TÍN invoices...[/cyan]")
        fetch_and_update_invoices(session)

@app.command()
def stats(
    start_date: str = typer.Option(None, "--start-date", "-s", help="Start date (DD/MM/YYYY)"),
    end_date: str = typer.Option(None, "--end-date", "-e", help="End date (DD/MM/YYYY)")
):
    
    """Show invoice database statistics, including tax providers and their invoices in the date range"""
    engine = create_engine('sqlite:///vantoi.db')
    
    with Session(engine) as session:
        # Parse date range
        start = datetime.strptime(start_date, "%d/%m/%Y") if start_date else None
        end = datetime.strptime(end_date, "%d/%m/%Y") if end_date else None
        
        # Get stats
        stats = get_invoice_stats(session)
        
        # Get invoices grouped by tax provider in the date range
        query = session.query(
            TaxProvider.name,
            func.count(Invoice.id)
        ).join(Invoice, TaxProvider.id == Invoice.tax_provider_id)
        
        if start:
            query = query.filter(Invoice.invoice_timestamp >= start)
        if end:
            query = query.filter(Invoice.invoice_timestamp <= end)
        
        tax_provider_invoices = query.group_by(TaxProvider.name).all()
        
        # Display stats
        console.print(Panel.fit(
            f"""[bold blue]Invoice Database Statistics[/bold blue]
            
Total Invoices: {stats['total_invoices']}
Downloaded: {stats['total_downloaded']} ({stats['download_percentage']}%)
Date Range: {stats['date_from']} to {stats['date_to']}
            """,
            title="📊 Statistics"
        ))
        
        # Display tax providers and their invoice counts
        table = Table(title="Tax Providers and Invoice Counts")
        table.add_column("Tax Provider")
        table.add_column("Status")
        table.add_column("Total")
        table.add_column("Downloaded")
        table.add_column("Note")
        
        for provider_stat in stats['tax_provider_stats']:
            provider = session.query(TaxProvider).filter_by(name=provider_stat['name']).first()
            table.add_row(
                provider_stat['name'],
                f"[{'green' if provider.status == 'RESOLVED' else 'yellow'}]{provider.status}[/]",
                str(provider_stat['total']),
                f"{provider_stat['downloaded']} ({provider_stat['percentage']}%)",
                provider.note or "-"
            )
        
        console.print(table)
        

@app.command()
def query(
    tax_code: str = typer.Option(None, "--tax-code", "-t", help="Filter by seller tax code"),
    start_date: str = typer.Option(None, "--start-date", "-s", help="Start date (DD/MM/YYYY)"),
    end_date: str = typer.Option(None, "--end-date", "-e", help="End date (DD/MM/YYYY)"),
    is_downloaded: bool = typer.Option(False, "--is-downloaded", "-id", help="Filter by download status (True or False)"),
    seller_id: int = typer.Option(None, "--seller-id", "-sid", help="Filter by seller ID"),
    tax_provider_id: int = typer.Option(None, "--tax-provider-id", "-tpid", help="Filter by tax provider ID"),
    output: str = typer.Option(None, "--output", "-o", help="Output to CSV file")
):
    """
    Query invoices with various filters and display the results in a table or save them to a CSV file.
    Args:
        tax_code (str, optional): Filter by seller tax code. Defaults to None.
        start_date (str, optional): Start date in the format DD/MM/YYYY. Defaults to None.
        end_date (str, optional): End date in the format DD/MM/YYYY. Defaults to None.
        is_downloaded (bool, optional): Filter by download status (True or False). Defaults to False.
        seller_id (int, optional): Filter by seller ID. Defaults to None.
        tax_provider_id (int, optional): Filter by tax provider ID. Defaults to None.
        output (str, optional): File path to save the output as a CSV file. Defaults to None.
    Returns:
        None: Displays the filtered invoices in a table format in the console. If the `output` parameter is provided, saves the filtered invoices to a CSV file.
    Raises:
        ValueError: If the `start_date` or `end_date` is not in the correct format (DD/MM/YYYY).
    Sample:
        python3 db.py query --start-date "01/02/2025" --end-date "28/02/2025" --output "Feb_invoices.csv"
    """

    engine = create_engine('sqlite:///vantoi.db')
    
    with Session(engine) as session:
        # Parse date range
        start = datetime.strptime(start_date, "%d/%m/%Y") if start_date else None
        end = datetime.strptime(end_date, "%d/%m/%Y") if end_date else None
        
        invoices = get_invoices(session, start_date=start, end_date=end, tax_code=tax_code)
        
        # Apply additional filters
        if is_downloaded is not None:
            invoices = [inv for inv in invoices if inv.is_downloaded == is_downloaded]
        if seller_id is not None:
            invoices = [inv for inv in invoices if inv.seller_id == seller_id]
        if tax_provider_id is not None:
            invoices = [inv for inv in invoices if inv.tax_provider_id == tax_provider_id]
        
        table = Table(title="Invoices")
        table.add_column("Date")
        table.add_column("Series")
        table.add_column("Number")
        table.add_column("Seller")
        table.add_column("Tax Provider")
        table.add_column("Downloaded")
        
        for inv in invoices:
            table.add_row(
                inv.invoice_timestamp.strftime("%Y-%m-%d"),
                inv.invoice_series,
                str(inv.invoice_number),
                inv.seller.name,
                session.query(TaxProvider).filter_by(id=inv.tax_provider_id).first().name if inv.tax_provider_id else "-",
                "Yes" if inv.is_downloaded else "No"
            )
        
        console.print(table)
        
        if output:
            with open(output, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Date", "Series", "Number", "Seller", "Tax Provider", "Downloaded"])
                for inv in invoices:
                    writer.writerow([
                        inv.invoice_timestamp.strftime("%Y-%m-%d"),
                        inv.invoice_series,
                        inv.invoice_number,
                        inv.seller.name,
                        session.query(TaxProvider).filter_by(id=inv.tax_provider_id).first().name if inv.tax_provider_id else "-",
                        "Yes" if inv.is_downloaded else "No"
                    ])
            rprint(f"[green]✓[/green] Saved to {output}")

if __name__ == "__main__":
    app()