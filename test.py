
from playwright.sync_api import sync_playwright
from pathlib import Path
import zipfile
import os
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('test')

# tax_code = "0302881072"
# url = f"https://{tax_code}-tt78.vnpt-invoice.com.vn/HomeNoLogin/SearchByFkey"  # Changed to https://
# tracking_code = "008DDB0C0CB3784312B0BBB77F63EF7201"
# download_dir = Path("./downloads")  # Ensure this directory exists

# with sync_playwright() as p:
#     browser = p.chromium.launch(headless=False)
#     context = browser.new_context(accept_downloads=True)
#     page = context.new_page()
#     try:
#         page.goto(url)
#         page.wait_for_selector("#strFkey")
#         page.fill("#strFkey", tracking_code)
        
#         download_button = "[class='icon-download-alt']"
#         page.wait_for_selector(download_button)
#         # Extract the href attribute of the download button
#         # logger.info("🔄 Downloading file...")
#         print("🔄 Downloading file...")
#         with page.expect_download() as download_info:
#             page.click(download_button)
#         download = download_info.value
        
#         temp_file_path = download_dir / "temp_invoice.pdf"
#         download.save_as(str(temp_file_path))
#         # logger.info(f"✅ Downloaded temporary file: {temp_file_path}")
#         print(f"✅ Downloaded temporary file: {temp_file_path}")
                
#         new_filename = f"test_file.pdf"
#         new_file_path = download_dir / new_filename
#         os.rename(temp_file_path, new_file_path)
#         logger.info(f"📁 Renamed to: {new_file_path}")
#         # Wait for the page to load
#         page.wait_for_timeout(10000)
#     except Exception as e:
#         print(f"❌ Error: {e}")
#     finally:
#         print("🔒 Closing browser...")
#         browser.close()














def parse_invoice_list(data_string):
    # Remove brackets and split by comma
    items = data_string.strip('[]').split(', ')
    
    parsed_data = []
    for item in items:
        # Split by underscore
        parts = item.split('_')
        if len(parts) == 4:
            parsed_data.append({
                'series': parts[0],
                'number': parts[1],
                'date': parts[2],
                'tracking_code': parts[3]
            })
    
    return parsed_data

# Example usage:
file_path = Path('data/fpt_list.txt')
download_dir = Path("./downloads_test")  # Ensure this directory exists

try:
    with open(file_path, 'r') as f:
        data = f.read()
        
    parsed_invoices = parse_invoice_list(data)

    # Print first few results as sample

    for invoice in parsed_invoices[:5]:
        print(invoice)
        # Extract month from the date and format it as a three-letter abbreviation
        try:
            month_name = datetime.strptime(invoice['date'], '%Y-%m-%d').strftime('%b')  # Convert to three-letter month abbreviation
        except ValueError:
            print(f"❌ Invalid date format for invoice: {invoice}")
            continue

        # Construct the URL
        url = f"https://hoadondientu.kimtingroup.com/api/invoice-mailpdf?sec={invoice['tracking_code']}"
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()
            try:
                with page.expect_download() as download_info:
                    page.evaluate(f"window.location.href = '{url}'")  # Trigger download by setting window location
                download = download_info.value
                
                # Format the file name with the month abbreviation
                file_name = f"{month_name}_{invoice['series']}_{invoice['number']}.pdf"
                file_path = download_dir / file_name
                download.save_as(str(file_path))
                print(f"✅ Downloaded and saved as: {file_path}")
            except Exception as e:
                print(f"❌ Error downloading {url}: {e}")
            finally:
                browser.close()

except FileNotFoundError:
    print(f"❌ Error: File not found at {file_path}")
    print("Please ensure the file exists in the data directory")