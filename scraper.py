# InvoiceScraper: A Playwright-based scraper for querying electronic invoices on the Vietnamese tax portal
from playwright.sync_api import sync_playwright
import json
import urllib3
import os
from pathlib import Path
from datetime import datetime, timedelta
import requests
from typing import List, Dict
import math
import argparse

class NetworkTrafficObserver:
    def __init__(self):
        self.auth_response = None
        self.target_url = "https://hoadondientu.gdt.gov.vn:30000/security-taxpayer/authenticate"
    
    def handle_response(self, response):
        if self.target_url in response.url:
            try:
                body = response.json()
                self.auth_response = body
            except:
                pass
    
    def get_auth_token(self):
        if self.auth_response and 'token' in self.auth_response:
            return self.auth_response['token']
        return None

class InvoiceScraper:
    def __init__(self):
        self.network_observer = NetworkTrafficObserver()
        self.base_url = "https://hoadondientu.gdt.gov.vn:30000"
        self.endpoints = [
            "/query/invoices/purchase",
            "/sco-query/invoices/purchase"
        ]
        self.ttxly_values = [5, 6]
        self.session = requests.Session()

    def __enter__(self):
        self.playwright = sync_playwright().start()
        browser_context = self.playwright.chromium.launch_persistent_context(
            user_data_dir="/Users/tranduat/Library/Application Support/Microsoft Edge/Default",
            channel="msedge",
            headless=False
        )
        
        # Setup response monitoring
        browser_context.on('response', self.network_observer.handle_response)
        
        self.browser = browser_context
        self.page = self.browser.new_page()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if hasattr(self, 'browser'):
                self.browser.close()
            if hasattr(self, 'playwright'):
                self.playwright.stop()
        except Exception as e:
            print(f"Error during cleanup: {e}")

    # Main scraping routine to navigate and extract invoice data
    def scrape_gorverment(self):
        """Navigate and authenticate, return token and cookies"""
        try:
            # Navigate to the electronic invoice lookup homepage
            self.page.goto("https://hoadondientu.gdt.gov.vn/")
            
            # Wait for and close any initial modal popup
            self.page.wait_for_selector('button.ant-modal-close', timeout=5000)
            self.page.click('button.ant-modal-close')
            
            # Click login and fill credentials
            self.page.click('div.ant-col.home-header-menu-item >> text=Đăng nhập')
            self.page.fill('input#username', '0316060982')
            self.page.fill('input#password', '1Q68nmL$')
            self.page.focus('div.ant-modal input#cvalue')
            
            # Wait for manual captcha entry and successful authentication
            max_wait_time = 60  # Maximum seconds to wait for authentication
            check_interval = 2   # Check every 2 seconds
            
            for _ in range(max_wait_time // check_interval):
                if self.get_auth_token():
                    print("🔒 Authentication successful!")
                    # Get cookies from browser
                    cookies = []
                    for cookie in self.browser.cookies():
                        self.session.cookies.set(cookie['name'], cookie['value'])
                        cookies.append(cookie)
                    print(f"🍪 Captured {len(cookies)} cookies")
                    return self.get_auth_token()
                    
                self.page.wait_for_timeout(check_interval * 1000)  # Convert to milliseconds
            
            raise Exception("Authentication timeout - no token received")
            
        except Exception as e:
            print(f"Error during authentication: {e}")
            raise

    def get_auth_token(self):
        return self.network_observer.get_auth_token()

    def fetch_all_invoices(self, start_date: str, end_date: str):
        """
        Fetch all invoices across all endpoints and ttxly values
        """
        token = self.get_auth_token()
        if not token:
            raise Exception("No authentication token available")

        all_results = []
        for endpoint in self.endpoints:
            for ttxly in self.ttxly_values:
                print("\n==============================")
                print(f"📡 Starting API call: endpoint={endpoint}, ttxly={ttxly}")
                print("==============================")
                results = self.fetch_paginated_data(endpoint, ttxly, start_date, end_date, token)
                all_results.extend(results)
                print(f"🔔 Completed API call: endpoint={endpoint}, ttxly={ttxly} - fetched {len(results)} records")
        
        return all_results

    def fetch_paginated_data(self, endpoint: str, ttxly: int, start_date: str, end_date: str, token: str):
        """
        Fetch all pages of data for a specific endpoint and ttxly value
        """
        page = 0
        size = 50
        all_data = []
        
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'vi',
            'Authorization': f'Bearer {token}',
            'Connection': 'keep-alive',
            'Origin': 'https://hoadondientu.gdt.gov.vn',
            'Referer': 'https://hoadondientu.gdt.gov.vn/',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }

        total = None
        state = None

        while True:
            try:
                url = f"{self.base_url}{endpoint}"
                # Build raw query string for exact formatting
                query_string = (
                    f"sort=tdlap:desc,khmshdon:asc,shdon:desc"
                    f"&size={size}"
                    f"&page={page}"
                )
                if state:
                    query_string += f"&state={state}"
                query_string += (
                    f"&search=tdlap=ge={start_date}T00:00:00;"
                    f"tdlap=le={end_date}T23:59:59;ttxly=={ttxly}"
                )
                full_url = f"{url}?{query_string}"

                print(f"🔄 Fetching page {page} from {endpoint} (ttxly={ttxly})")
                print(f"🌐 URL: {full_url}")
                response = self.session.get(
                    full_url,
                    headers=headers,
                    verify=False
                )
                response.raise_for_status()
                
                data = response.json()
                if total is None:
                    total = data.get('total')
                    total_pages = math.ceil(total / size)
                    print(f"📊 Total invoices to fetch: {total} across {total_pages} pages")
                
                state = data.get('state')
                records = data.get('datas', [])
                all_data.extend(records)
                
                if len(all_data) >= total:
                    break

                page += 1

            except requests.exceptions.RequestException as e:
                print(f"❌ Error fetching data: {e}")
                break

        return all_data

def validate_date_format(date_string):
    """Validate date string format (DD/MM/YYYY)"""
    try:
        datetime.strptime(date_string, "%d/%m/%Y")
        return date_string
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date format. Use DD/MM/YYYY")

if __name__ == "__main__":
    """
    Invoice Scraper CLI
    
    This script fetches electronic invoices from the Vietnamese tax portal for a specified date range.
    
    Usage:
        python scraper.py --start-date DD/MM/YYYY --end-date DD/MM/YYYY
    
    Examples:
        python scraper.py --start-date 01/01/2025 --end-date 31/01/2025
        python scraper.py --start-date 01/12/2024 --end-date 31/12/2024
    
    Notes:
        - Dates must be in DD/MM/YYYY format
        - Start date must be before or equal to end date
        - Requires manual CAPTCHA entry during authentication
        - Results are saved to ./data/<Month>_invoices.json
    """
    parser = argparse.ArgumentParser(
        description='Fetch electronic invoices from the Vietnamese tax portal',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--start-date', type=validate_date_format, required=True,
                      help='Start date (DD/MM/YYYY)')
    parser.add_argument('--end-date', type=validate_date_format, required=True,
                      help='End date (DD/MM/YYYY)')
    args = parser.parse_args()

    # Disable SSL verification warnings
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    try:
        with InvoiceScraper() as scraper:
            token = scraper.scrape_gorverment()
            if token:
                print(f"Using auth token: {token[:30]}...")
                print(f"Fetching invoices from {args.start_date} to {args.end_date}")
                invoices = scraper.fetch_all_invoices(args.start_date, args.end_date)
                print(f"Total invoices fetched: {len(invoices)}")
                if len(invoices) > 0:
                    output_dir = Path('data')
                    output_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Extract month name and year from start date
                    start_date_obj = datetime.strptime(args.start_date, "%d/%m/%Y")
                    month_name = start_date_obj.strftime("%b")  # Short month name (e.g., Jan, Feb)
                    year_number = start_date_obj.strftime("%Y")  # Year (e.g., 2025)
                    output_file = output_dir / f'{year_number}_{month_name}_invoices.json'
                    
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(invoices, f, ensure_ascii=False, indent=2)
                    print(f"✅ Invoices written to {output_file}")
                else:
                    print("No invoices found for the specified date range")
    except Exception as e:
        print(f"Error during execution: {e}")