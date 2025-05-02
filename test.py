from playwright.sync_api import sync_playwright
from pathlib import Path
import zipfile

tax_code = "0306013246"
url = f"http://{tax_code}hd.easyinvoice.vn"
tracking_code = "4d4e1f0c-1de0-4b96-a4c2-871bf4aef010"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(accept_downloads=True)
    page = context.new_page()
    try:
        page.goto(url)
        print(f"🔍 Filling form for invoice: {tracking_code}")
        page.fill("#iFkey", tracking_code)
        
        # Focus on CAPTCHA field right after filling tracking code
        page.focus("#Capcha")
        print(f"⚠️ Please complete the CAPTCHA and click submit manually...")
        
        # Wait for download button to appear
        button_selector = "button[name='downloadPdfAndFileAttach']"
        print("⏳ Waiting for download button to appear...")
        page.wait_for_selector(button_selector, state="visible", timeout=60000)
        
        # Handle download
        print("📥 Starting download...")
        with page.expect_download() as download_info:
            page.click(button_selector)
        
        # Process downloaded file
        script_dir = Path(__file__).parent
        temp_zip = script_dir / "temp_invoice.zip"
        download_info.value.save_as(temp_zip)
        
        if not temp_zip.exists() or temp_zip.stat().st_size == 0:
            raise Exception("Download failed: Invalid or empty zip file")
            
        # Extract PDF
        final_path = script_dir / "invoice.pdf"
        try:
            with zipfile.ZipFile(temp_zip) as zip_ref:
                pdf_files = [f for f in zip_ref.namelist() if f.lower().endswith('.pdf')]
                if not pdf_files:
                    raise Exception("No PDF file found in zip")
                with zip_ref.open(pdf_files[0]) as pdf_file:
                    final_path.write_bytes(pdf_file.read())
            print(f"✅ PDF extracted: {final_path} ({final_path.stat().st_size} bytes)")
        finally:
            if temp_zip.exists():
                temp_zip.unlink()
                print("🧹 Cleaned up temporary zip file")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        print("🔒 Closing browser...")
        browser.close()
