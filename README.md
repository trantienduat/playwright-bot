# Playwright Bot

A comprehensive invoice automation system for Vietnamese electronic invoices with web scraping, database management, and automated downloading capabilities.

## Feature Status

| Feature               | Code | Test | Docs |
| --------------------- | ---- | ---- | ---- |
| Database Operations   | ✅    | 🚧    | ✅    |
| Invoice Scraper       | ✅    | 🚧    | ✅    |
| SoftDreams Downloader | ✅    | 🚧    | ✅    |
| Viettel Downloader    | ✅    | 🚧    | ✅    |
| MISA Downloader       | ✅    | 🚧    | ✅    |
| FPT Downloader        | ✅    | 🚧    | 🚧    |
| ThaiSon Downloader    | ✅    | 🚧    | 🚧    |
| BuuChinhVT Downloader | ✅    | 🚧    | ✅    |
| Vina Downloader       | ✅    | 🚧    | 🚧    |
| Hilo Downloader       | ✅    | 🚧    | 🚧    |
| CLI Interface         | ✅    | 🚧    | ✅    |

**Legend**: ✅ Implemented | 🚧 Work in Progress | ❌ Not Started

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

### BuuChinhVT Downloader
Uses VNPT invoice portal. The process:
1. Constructs URL as `https://{tax_code}-tt78.vnpt-invoice.com.vn/HomeNoLogin/SearchByFkey`
2. Fills tracking_code and searches to retrieve checkCode
3. Extracts checkCode from response and downloads from `https://{tax_code}-tt78.vnpt-invoice.com.vn/HomeNoLogin/downloadPDF?checkCode={checkCode}`

### Other Downloaders
- **FPT Downloader**: Handles FPT invoice system
- **ThaiSon Downloader**: Supports ThaiSon invoice platform
- **Vina Downloader**: Works with Vina invoice services
- **Hilo Downloader**: Integrates with Hilo invoice system

## System Architecture

### Invoice Scraper (`scraper.py`)
Web scraper for the Vietnamese government electronic invoice portal:
- Uses Playwright to automate browser interactions
- Handles authentication with manual CAPTCHA completion
- Fetches invoices from multiple API endpoints
- Supports pagination for large datasets
- Exports data to JSON format organized by profile and date

### Database Management (`db.py`)
Comprehensive CLI for invoice database operations:
- SQLite/PostgreSQL database support via SQLAlchemy
- Profile-based configuration management
- Data import/export functionality
- Advanced querying and filtering
- Statistics and reporting capabilities

### Invoice Downloader (`download_invoice.py`)
Automated invoice downloading system:
- Supports multiple tax provider platforms
- Handles different authentication methods
- Implements rate limiting and error handling
- Organizes files with intelligent naming conventions
- Tracks download status in database

## Usage

### 1. Invoice Scraping

First, scrape invoices from the government portal for a specific date range:

```bash
python3 scraper.py --start-date 01/06/2025 --end-date 30/06/2025
```

**Parameters:**
- `--start-date`: Start date in `DD/MM/YYYY` format (required)
- `--end-date`: End date in `DD/MM/YYYY` format (required)

**Features:**
- Automated browser navigation with Playwright
- Manual CAPTCHA completion support
- Multi-endpoint data fetching
- Profile-based output organization
- JSON export to `data/{profile}/{year}_{month}_invoices.json`

### 2. Database Management

The `db.py` script provides comprehensive database operations:

#### Load Data into Database
```bash
python3 db.py fetch --input data/profile_name/2025_Jun_invoices.json
```

**Parameters:**
- `--input` / `-i`: Path to input JSON file containing invoice data

**Process:**
- Loads tax providers, sellers, and invoices
- Handles duplicate detection and merging
- Updates tracking codes for special cases (e.g., KIM TÍN)
- Maintains data integrity with constraints

#### View Database Statistics
```bash
python3 db.py stats --start-date 01/06/2025 --end-date 30/06/2025
```

**Parameters:**
- `--start-date` / `-s`: Start date in `DD/MM/YYYY` format (optional)
- `--end-date` / `-e`: End date in `DD/MM/YYYY` format (optional)

**Output:**
- Total invoices and download statistics
- Tax provider breakdown with download rates
- Date range analysis
- Visual tables with rich formatting

#### Query Invoices
```bash
python3 db.py query --start-date 01/02/2025 --end-date 28/02/2025 --output Feb_invoices.csv
```

**Parameters:**
- `--tax-code` / `-t`: Filter by seller tax code
- `--start-date` / `-s`: Start date in `DD/MM/YYYY` format
- `--end-date` / `-e`: End date in `DD/MM/YYYY` format
- `--is-downloaded` / `-id`: Filter by download status (true/false)
- `--seller-id` / `-sid`: Filter by seller ID
- `--tax-provider-id` / `-tpid`: Filter by tax provider ID
- `--output` / `-o`: Export results to CSV file

### 3. Invoice Downloading

Download invoices automatically using various provider platforms:

```bash
python3 download_invoice.py --start-date 01/05/2025 --end-date 31/05/2025
```

**Parameters:**
- `--start-date`: Start date in `DD/MM/YYYY` format (required)
- `--end-date`: End date in `DD/MM/YYYY` format (required)

**Features:**
- Multi-platform support (9 different providers)
- Intelligent file naming with month prefix
- Download status tracking in database
- Rate limiting and error handling
- Profile-based output directory configuration
- Automatic skip for existing files

**Supported Platforms:**
- SoftDreams (easyinvoice)
- Viettel (vinvoice)
- MISA (meinvoice)
- FPT
- ThaiSon
- BuuChinhVT (VNPT)
- Vina
- Hilo

## Configuration

The system uses profile-based configuration managed by `profile_manager`:

- **Database settings**: Connection strings and credentials
- **Download paths**: Output directories for different file types
- **Seller mappings**: Short name mappings for file naming
- **Provider credentials**: Authentication details for various platforms
- **KIMTIN list path**: Special tracking code file location

## File Organization

```
data/
├── profile_name/
│   └── 2025_Jun_invoices.json
downloads/
├── profile_name/
│   ├── Jun_CompanyShort_12345.pdf
│   └── Jun_AnotherCompany_67890.pdf
```

## Error Handling

- **Graceful degradation**: Missing providers don't stop the process
- **Rate limiting**: Prevents overwhelming target servers
- **Retry mechanisms**: Handles temporary network issues
- **Comprehensive logging**: Detailed progress and error reporting
- **Data validation**: Ensures data integrity throughout the pipeline



