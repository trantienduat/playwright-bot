# Playwright Bot

## Feature Status

| Feature               | Code | Test | Docs |
| --------------------- | ---- | ---- | ---- |
| Database Operations   | 🚧    | 🚧    | 🚧    |
| SoftDreams Downloader | ✅    | 🚧    | 🚧    |
| Viettel Downloader    | ✅    | 🚧    | 🚧    |
| MISA Downloader       | ✅    | 🚧    | 🚧    |
| VNPT Downloader       | 🚧    | 🚧    | 🚧    |
| FPT Downloader        | 🚧    | 🚧    | 🚧    |
| BKAV Downloader       | 🚧    | 🚧    | 🚧    |
| DNA Downloader        | 🚧    | 🚧    | 🚧    |
| ThaiSon Downloader    | 🚧    | 🚧    | 🚧    |
| BuuChinhVT Downloader | 🚧    | 🚧    | 🚧    |
| Wintech Downloader    | 🚧    | 🚧    | 🚧    |
| Visnam Downloader     | 🚧    | 🚧    | 🚧    |
| CLI Interface         | 🚧    | 🚧    | 🚧    |

## How downloaders work

### SoftDreams Downloader
Downloads invoices from easyinvoice portal. The process:
1. Attempts to connect to `https://{tax_code}hd.easyinvoice.com.vn`
2. If domain unreachable, retries with `https://{tax_code}hd.easyinvoice.vn`
3. Fills in tracking code and requires manual CAPTCHA completion
4. Downloads a ZIP file containing the invoice
5. Extracts the PDF from the ZIP file and cleans up temporary files

### Viettel Downloader
Uses Viettel's public invoice search page. The process:
1. Navigates to `https://vinvoice.viettel.vn/utilities/invoice-search`
2. Fills in tax code and tracking code
3. Requires manual CAPTCHA completion and search button click
4. Downloads PDF directly
5. Renames file with month prefix and invoice details (e.g., Feb_C25TKM_2652.pdf)

### MISA Downloader
Uses direct download URL approach. The process:
1. Constructs URL with tracking code: `https://www.meinvoice.vn/tra-cuu/DownloadHandler.ashx?Type=pdf&Viewer=1&Code={tracking_code}`
2. Downloads PDF directly using requests library with browser-like headers
3. Shows download progress with a progress bar
4. No CAPTCHA required

### buuchinhvt (WIP)
1. construct url as `https://{tax_code}-tt78.vnpt-invoice.com.vn/HomeNoLogin/SearchByFkey`
2. fill tracking_code & search -> retrieving checkCode
3. consider to extract checkCode from then download from `https://{tax_code}-tt78.vnpt-invoice.com.vn/HomeNoLogin/downloadPDF?checkCode=8+0arNQParpTotMzLDdWVGzoBP6SJRtbzgwduEsVNdY=`
```html
<a style="color: #1068bf;" title="Tải file pdf" href="/HomeNoLogin/downloadPDF?checkCode=8+0arNQParpTotMzLDdWVGzoBP6SJRtbzgwduEsVNdY="><i class="icon-download-alt"></i></a>
```

## Usage

### Database CLI

The `db.py` script provides a CLI for managing the invoice database. Below are some common commands:

1. **Fetch Data**: Load data from JSON files into the database.
   ```bash
   python3 db.py fetch --input <JSON_FILE>
   ```

   - `--input`: Path to the input JSON file containing invoice data.

   Example:
   ```bash
   python3 db.py fetch --input data/invoices.json
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



