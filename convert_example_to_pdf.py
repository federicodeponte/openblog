#!/usr/bin/env python3
"""
Convert the final HTML example to PDF using federicodeponte/html-to-pdf service.

This script demonstrates the complete openblog pipeline output by converting
the generated HTML article to a publication-ready PDF format.
"""

import requests
import base64
import json
from pathlib import Path

# Service URL from Modal deployment
PDF_SERVICE_URL = "https://clients--pdf-generation-fastapi-app.modal.run"

def convert_html_to_pdf(html_content: str, output_path: str) -> dict:
    """
    Convert HTML content to PDF using the Modal-deployed service.
    
    Args:
        html_content: The HTML content to convert
        output_path: Where to save the PDF file
        
    Returns:
        Response data with conversion metrics
    """
    
    # Prepare the request payload
    payload = {
        "html": html_content,
        "format": "A4",
        "landscape": False,
        "print_background": True,
        "prefer_css_page_size": True,
        "viewport_width": 1200,
        "device_scale_factor": 2,  # High DPI for crisp text
        "color_scheme": "light"
    }
    
    print(f"Converting HTML to PDF using {PDF_SERVICE_URL}/convert...")
    
    try:
        response = requests.post(
            f"{PDF_SERVICE_URL}/convert",
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=120
        )
        response.raise_for_status()
        
        result = response.json()
        
        # Decode the base64 PDF and save it
        pdf_data = base64.b64decode(result["pdf_base64"])
        
        with open(output_path, "wb") as f:
            f.write(pdf_data)
        
        print(f"✅ PDF saved to: {output_path}")
        print(f"   File size: {result['size_bytes']:,} bytes ({result['size_bytes']/1024:.1f} KB)")
        print(f"   Render time: {result['render_time_ms']} ms")
        
        return result
        
    except requests.RequestException as e:
        print(f"❌ Error calling PDF service: {e}")
        raise
    except Exception as e:
        print(f"❌ Error converting PDF: {e}")
        raise

def main():
    """Main conversion function."""
    
    # Paths
    html_file = Path("/Users/federicodeponte/openblog-isaac-security/final_example_complete.html")
    pdf_file = Path("/Users/federicodeponte/openblog-isaac-security/examples/zero-trust-security-architecture-guide.pdf")
    
    # Create examples directory if it doesn't exist
    pdf_file.parent.mkdir(exist_ok=True)
    
    # Read the HTML content
    if not html_file.exists():
        raise FileNotFoundError(f"HTML file not found: {html_file}")
    
    print(f"Reading HTML from: {html_file}")
    html_content = html_file.read_text(encoding="utf-8")
    
    print(f"HTML content length: {len(html_content):,} characters")
    
    # Convert to PDF
    result = convert_html_to_pdf(html_content, str(pdf_file))
    
    print(f"\n🎉 Conversion complete!")
    print(f"📄 Generated PDF: {pdf_file}")
    print(f"📊 Quality: High DPI (scale factor: 2)")
    print(f"📐 Format: A4 portrait with proper margins")
    
    # Also generate a debug comparison (screenshot + PDF)
    try:
        print(f"\nGenerating debug comparison...")
        debug_payload = {
            "html": html_content,
            "format": "A4",
            "print_background": True,
            "viewport_width": 1200,
            "device_scale_factor": 2
        }
        
        debug_response = requests.post(
            f"{PDF_SERVICE_URL}/convert/debug",
            headers={"Content-Type": "application/json"},
            json=debug_payload,
            timeout=120
        )
        
        if debug_response.status_code == 200:
            debug_result = debug_response.json()
            
            # Save screenshot
            screenshot_data = base64.b64decode(debug_result["screenshot_base64"])
            screenshot_path = pdf_file.with_suffix(".screenshot.png")
            with open(screenshot_path, "wb") as f:
                f.write(screenshot_data)
            print(f"📸 Debug screenshot: {screenshot_path}")
        
    except Exception as e:
        print(f"⚠️  Debug generation failed (not critical): {e}")

if __name__ == "__main__":
    main()