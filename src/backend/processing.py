from PIL import Image
import requests
from bs4 import BeautifulSoup
from io import BytesIO

def resize_image_for_storage(image_bytes):
    """
    Resizes image to max width 1920px while maintaining aspect ratio.
    Converts to RGB (removes Alpha) and saves as JPEG.
    """
    try:
        img = Image.open(image_bytes)
        
        # Convert to RGB if necessary (e.g. PNGs)
        if img.mode in ("RGBA", "P"): 
            img = img.convert("RGB")

        max_size = (1920, 1920)
        img.thumbnail(max_size, Image.Resampling.LANCZOS)

        output_io = BytesIO()
        img.save(output_io, format='JPEG', quality=85)
        output_io.seek(0)
        return output_io
    except Exception as e:
        print(f"Resize Error: {e}")
        raise e

def scrape_website(url):
    """
    Basic scraper using BeautifulSoup.
    """
    try:
        # User agent to avoid some 403s
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract title and paragraphs
        title = soup.title.string if soup.title else ""
        text_content = ""
        for p in soup.find_all('p'):
            text_content += p.get_text() + "\n"
            
        return {
            "title": title,
            "text": text_content[:10000] # Limit context window
        }
    except Exception as e:
        print(f"Scrape Error: {e}")
        raise e

def capture_pdf(url):
    """
    Stub for PDF capture. 
    Real implementation requires wkhtmltopdf binary installed on system.
    """
    # import pdfkit
    # pdf_bytes = pdfkit.from_url(url, False)
    # return BytesIO(pdf_bytes)
    return None