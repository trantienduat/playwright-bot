import requests
import sys
from pathlib import Path

def download_by_url(url, download_folder, filename="downloaded_invoice.pdf"):
    """
    Download a PDF file from meinvoice.vn
    
    Args:
        url (str): URL of the PDF to download
        download_folder (str): Folder where to save the PDF file
        filename (str): Name of the file to save as
    """
    print(f"Downloading PDF from: {url}")
    
    try:
        # Set up headers to mimic a browser request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Make the request
        response = requests.get(url, headers=headers, stream=True, timeout=30)
        
        # Check if the request was successful
        response.raise_for_status()
        
        # Verify content type is PDF
        content_type = response.headers.get('Content-Type', '').lower()
        if 'application/pdf' not in content_type and 'application/octet-stream' not in content_type:
            print(f"Warning: The response might not be a PDF (Content-Type: {content_type})")
        
        # Create directory if needed
        output_dir = Path(download_folder)
        if not output_dir.exists():
            output_dir.mkdir(parents=True, exist_ok=True)
        
        # Construct the output path
        output_path = output_dir / filename
        
        # Download the file with progress indicator
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(output_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:  # Filter out keep-alive chunks
                    file.write(chunk)
                    downloaded += len(chunk)
                    
                    # Update progress bar
                    if total_size > 0:
                        progress = int(50 * downloaded / total_size)
                        sys.stdout.write(f"\r[{'=' * progress}{' ' * (50-progress)}] {downloaded/1024/1024:.2f}MB/{total_size/1024/1024:.2f}MB")
                        sys.stdout.flush()

        print(f"File saved to: {output_path}")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"Error downloading PDF: {e}")
        return False