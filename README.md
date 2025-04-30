# Playwright Bot

...existing content...

## Usage

### Database CLI

The `db.py` script provides a CLI for managing the invoice database. Below are some common commands:

1. **Fetch Data**: Load data from JSON files into the database.
   ```bash
   python3 db.py fetch
   ```

2. **View Statistics**: Display summary statistics of the invoice database, including tax providers and their invoices in a date range.
   ```bash
   python3 db.py stats --start-date <START_DATE> --end-date <END_DATE>
   ```

   - `--start-date`: Start date in `DD/MM/YYYY` format (optional).
   - `--end-date`: End date in `DD/MM/YYYY` format (optional).

   Example:
   ```bash
   python3 db.py stats --start-date 01/01/2023 --end-date 31/01/2023
   ```

3. **Query Invoices**: Query invoices with optional filters.
   ```bash
   python3 db.py query --tax-code <TAX_CODE> --days <DAYS> --output <OUTPUT_FILE>
   ```

   - `--tax-code`: Filter by provider tax code.
   - `--days`: Number of days to look back (default: 30).
   - `--output`: Save the query results to a JSON file.

### Invoice Downloader

The `download_invoice.py` script allows downloading invoices based on date range and other filters.

1. **Download Invoices**: Download invoices for a specific date range.
   ```bash
   python3 download_invoice.py --start-date <START_DATE> --end-date <END_DATE> --output <OUTPUT_DIR>
   ```

   - `--start-date`: Start date in `DD/MM/YYYY` format.
   - `--end-date`: End date in `DD/MM/YYYY` format.
   - `--output`: Directory to save downloaded invoices (default: `downloads`).

   Example:
   ```bash
   python3 download_invoice.py --start-date 01/02/2025 --end-date 28/02/2025 --output invoices
   ```

...existing content...
