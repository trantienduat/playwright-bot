from sqlalchemy import create_engine, select, text, func
from sqlalchemy.orm import Session
from pathlib import Path
import json
import yaml
from models import Provider, TaxProvider, Invoice, Base, init_db
from datetime import datetime, timedelta
import dateutil.parser
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

app = typer.Typer(help="Invoice Database CLI")
console = Console()

def load_providers_from_json():
    """Load provider data from invoices.json"""
    json_path = Path('data/invoices.json')
    if not json_path.exists():
        print("❌ invoices.json not found")
        return []
    
    with open(json_path, 'r', encoding='utf-8') as f:
        invoices = json.load(f)
    
    # Extract unique providers by tax_code
    providers = {}
    for invoice in invoices:
        tax_code = invoice.get('nbmst')
        name = invoice.get('nbten')
        if tax_code and name:
            if tax_code not in providers:
                providers[tax_code] = name
                print(f"Found provider: {tax_code} - {name}")
    
    provider_list = [Provider(tax_code=tc, name=name) for tc, name in providers.items()]
    print(f"\n📊 Total unique providers found: {len(provider_list)}")
    return provider_list

def load_tax_providers_from_json():
    """Load tax provider data from invoices.json"""
    json_path = Path('data/invoices.json')
    if not json_path.exists():
        print("❌ invoices.json not found")
        return []
    
    with open(json_path, 'r', encoding='utf-8') as f:
        invoices = json.load(f)
    
    # Extract unique tax providers
    tax_providers = {}
    for invoice in invoices:
        name = invoice.get('ngcnhat')
        if name and name.startswith('tvan_'):
            name = name.replace('tvan_', '')
            if name not in tax_providers:
                tax_providers[name] = TaxProvider(name=name)
                print(f"Found tax provider: {name}")
    
    return list(tax_providers.values())

def load_search_urls():
    """Load search URLs from config.yml"""
    config_path = Path('config') / 'config.yml'
    if not config_path.exists():
        print("❌ config.yml not found")
        return {}
    
    with open(config_path, 'r', encoding='utf-8') as f:
        urls = yaml.safe_load(f)
        return urls

def merge_tax_providers(session, new_tax_providers):
    """Merge tax providers while handling duplicates and update search URLs"""
    existing = {tp.name: tp for tp in get_existing_tax_providers(session)}
    print(f"\n💾 Existing tax providers in DB: {len(existing)}")

    # Load search URLs from config
    search_urls = load_search_urls()
    
    merged = []
    for tp in new_tax_providers:
        if tp.name not in existing:
            print(f"+ Adding new tax provider: {tp.name}")
            # Set search URL if available
            tp.search_url = search_urls.get(tp.name)
            merged.append(tp)
        else:
            print(f"~ Tax provider exists: {tp.name}")
            # Update search URL for existing provider
            existing[tp.name].search_url = search_urls.get(tp.name)
    
    # Add only new tax providers
    for tp in merged:
        session.add(tp)
    session.commit()
    return merged

def merge_providers(session, new_providers):
    """Merge providers while handling duplicates"""
    existing = {p.tax_code: p for p in get_existing_providers(session)}
    print(f"\n💾 Existing providers in DB: {len(existing)}")

    merged = []
    updated = []
    for provider in new_providers:
        if provider.tax_code not in existing:
            print(f"+ Adding new provider: {provider.tax_code} - {provider.name}")
            merged.append(provider)
        else:
            print(f"~ Updating provider: {provider.tax_code} - {provider.name}")
            existing[provider.tax_code].name = provider.name
            updated.append(existing[provider.tax_code])
    
    # Add new providers
    for provider in merged:
        session.add(provider)
    session.commit()
    
    return merged, updated

def get_existing_providers(session):
    """Get list of existing providers from DB"""
    return session.query(Provider).all()

def get_existing_tax_providers(session):
    """Get list of existing tax providers from DB"""
    return session.query(TaxProvider).all()

def load_invoices_from_json(session):
    """Load and parse invoice data from invoices.json"""
    json_path = Path('data/invoices.json')
    if not json_path.exists():
        print("❌ invoices.json not found")
        return []

    with open(json_path, 'r', encoding='utf-8') as f:
        raw_invoices = json.load(f)

    invoices = []
    tax_code_to_provider = {p.tax_code: p for p in get_existing_providers(session)}
    name_to_tax_provider = {tp.name: tp for tp in get_existing_tax_providers(session)}

    for raw in raw_invoices:
        tax_code = raw.get('nbmst')
        tax_provider_name = raw.get('ngcnhat', '').replace('tvan_', '') if raw.get('ngcnhat') else None
        
        if not tax_code:
            continue

        provider = tax_code_to_provider.get(tax_code)
        tax_provider = name_to_tax_provider.get(tax_provider_name) if tax_provider_name else None
        
        if not provider:
            continue

        invoice = Invoice(
            invoice_form=raw.get('khmshdon'),
            invoice_series=raw.get('khhdon'),
            invoice_timestamp=dateutil.parser.parse(raw.get('tdlap')) if raw.get('tdlap') else None,
            invoice_number=raw.get('shdon'),
            provider=provider,
            tax_provider=tax_provider
        )
        invoices.append(invoice)
        print(f"Found invoice: {invoice.invoice_series}-{invoice.invoice_number} from {provider.name} via {tax_provider_name if tax_provider else 'unknown'}")

    return invoices

def merge_invoices(session, new_invoices):
    """Merge invoices while handling duplicates"""
    # Get existing keys without triggering autoflush
    with session.no_autoflush:
        existing = session.query(Invoice).all()
        existing_keys = {(i.invoice_form, i.invoice_series, i.invoice_timestamp, i.invoice_number) for i in existing}

    merged = []
    
    # Process invoices in batches
    batch_size = 100
    for i in range(0, len(new_invoices), batch_size):
        batch = new_invoices[i:i + batch_size]
        
        for invoice in batch:
            key = (invoice.invoice_form, invoice.invoice_series, invoice.invoice_timestamp, invoice.invoice_number)
            if key not in existing_keys:
                # Create a fresh invoice object
                new_invoice = Invoice(
                    invoice_form=invoice.invoice_form,
                    invoice_series=invoice.invoice_series,
                    invoice_number=invoice.invoice_number,
                    invoice_timestamp=invoice.invoice_timestamp
                )

                # Set relationships using existing session objects
                if invoice.provider:
                    provider = session.query(Provider).get(invoice.provider.id)
                    new_invoice.provider = provider
                
                if invoice.tax_provider:
                    tax_provider = session.query(TaxProvider).get(invoice.tax_provider.id)
                    new_invoice.tax_provider = tax_provider
                
                merged.append(new_invoice)
                session.add(new_invoice)
        
        # Commit each batch
        session.commit()
        session.flush()
        
    return merged

def get_invoices(session, start_date=None, end_date=None, tax_code=None):
    """Get invoices with optional date range and tax code filters"""
    query = session.query(Invoice).join(Invoice.provider)
    
    if start_date:
        query = query.filter(Invoice.invoice_timestamp >= start_date)
    if end_date:
        query = query.filter(Invoice.invoice_timestamp <= end_date)
    if tax_code:
        query = query.filter(Provider.tax_code == tax_code)
        
    return query.order_by(Invoice.invoice_timestamp.desc()).all()

def get_invoice_stats(session):
    """Get summary stats of invoices"""
    total = session.query(Invoice).count()
    
    # Get date range
    date_range = session.query(
        func.min(Invoice.invoice_timestamp),
        func.max(Invoice.invoice_timestamp)
    ).first()
    
    # Get tax providers and their occurrence
    tax_provider_stats = session.query(
        TaxProvider.name,
        func.count(Invoice.id)
    ).join(Invoice, TaxProvider.id == Invoice.tax_provider_id).group_by(TaxProvider.name).all()
    
    return {
        'total_invoices': total,
        'date_from': date_range[0] if date_range[0] else None,
        'date_to': date_range[1] if date_range[1] else None,
        'tax_provider_stats': tax_provider_stats
    }

@app.command()
def fetch():
    """Fetch and load all invoice data from JSON files into database"""
    engine = create_engine('sqlite:///vantoi.db')
    init_db()
    
    with Session(engine) as session:
        # Process tax providers
        new_tax_providers = load_tax_providers_from_json()
        merged_tax_providers = merge_tax_providers(session, new_tax_providers)
        rprint(f"[green]✓[/green] Added {len(merged_tax_providers)} tax providers")
        
        # Process providers
        new_providers = load_providers_from_json()
        merged, updated = merge_providers(session, new_providers)
        rprint(f"[green]✓[/green] Added {len(merged)} new providers")
        rprint(f"[blue]↻[/blue] Updated {len(updated)} providers")
        
        # Process invoices
        new_invoices = load_invoices_from_json(session)
        merged_invoices = merge_invoices(session, new_invoices)
        rprint(f"[green]✓[/green] Added {len(merged_invoices)} invoices")

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
Date Range: {stats['date_from']} to {stats['date_to']}
            """,
            title="📊 Statistics"
        ))
        
        # Display tax providers and their invoice counts
        table = Table(title="Tax Providers and Invoice Counts")
        table.add_column("Tax Provider")
        table.add_column("Invoice Count")
        
        for tax_provider, count in tax_provider_invoices:
            table.add_row(tax_provider, str(count))
        
        console.print(table)

@app.command()
def query(
    tax_code: str = typer.Option(None, "--tax-code", "-t", help="Filter by provider tax code"),
    days: int = typer.Option(30, "--days", "-d", help="Number of days to look back"),
    output: str = typer.Option(None, "--output", "-o", help="Output to JSON file")
):
    """Query invoices with filters"""
    engine = create_engine('sqlite:///vantoi.db')
    
    with Session(engine) as session:
        end = datetime.now()
        start = end - timedelta(days=days)
        
        invoices = get_invoices(session, start_date=start, tax_code=tax_code)
        
        table = Table(title=f"Invoices (last {days} days)")
        table.add_column("Date")
        table.add_column("Series")
        table.add_column("Number")
        table.add_column("Provider")
        table.add_column("Tax Provider")
        
        for inv in invoices:
            table.add_row(
                inv.invoice_timestamp.strftime("%Y-%m-%d"),
                inv.invoice_series,
                str(inv.invoice_number),
                inv.provider.name,
                inv.tax_provider.name if inv.tax_provider else "-"
            )
        
        console.print(table)
        
        if output:
            data = [{
                'date': inv.invoice_timestamp.isoformat(),
                'series': inv.invoice_series,
                'number': inv.invoice_number,
                'provider': inv.provider.name,
                'tax_provider': inv.tax_provider.name if inv.tax_provider else None
            } for inv in invoices]
            
            with open(output, 'w') as f:
                json.dump(data, f, indent=2)
            rprint(f"[green]✓[/green] Saved to {output}")

if __name__ == "__main__":
    app()