import os
import glob
from pypdf import PdfReader

# CONFIG
# Adjust path to match your structure
BASE_DIR = "agenticai/data"
OUTPUT_DIR = "agenticai/data/processed_rag"

def extract_pdf_text(filepath, max_pages=30):
    """Reads PDF, limited to max_pages to avoid processing 40MB of references"""
    print(f"   📄 Processing PDF: {os.path.basename(filepath)}...")
    text = ""
    try:
        reader = PdfReader(filepath)
        # Limit pages to get the "Executive Summary" and core guidelines
        limit = min(len(reader.pages), max_pages)
        for i in range(limit):
            page = reader.pages[i]
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
        print(f"      -> Extracted {len(text)} characters from {limit} pages.")
        return text
    except Exception as e:
        print(f"      ❌ Error reading PDF: {e}")
        return ""

def extract_txt_text(filepath):
    """Reads simple text files"""
    print(f"   📝 Processing Text: {os.path.basename(filepath)}...")
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()
        print(f"      -> Extracted {len(text)} characters.")
        return text
    except Exception as e:
        print(f"      ❌ Error reading text file: {e}")
        return ""

def process_domain(domain):
    print(f"\n🚀 Starting Processing for: {domain.upper()}")
    
    # 1. Gather all raw text from all regions
    combined_text = f"=== {domain.upper()} DIETARY GUIDELINES (GLOBAL) ===\n\n"
    
    # Define regions to look for
    regions = ["india", "us", "sg"]
    
    for region in regions:
        raw_path = os.path.join(BASE_DIR, domain, "raw", region)
        if not os.path.exists(raw_path):
            print(f"   ⚠️  Warning: Path not found {raw_path}")
            continue
            
        print(f"   🌍 Region: {region.upper()}")
        combined_text += f"\n--- REGION: {region.upper()} ---\n"
        
        # Process all files in that folder
        files = glob.glob(os.path.join(raw_path, "*"))
        for f in files:
            if f.lower().endswith(".pdf"):
                combined_text += extract_pdf_text(f)
            elif f.lower().endswith(".txt"):
                combined_text += extract_txt_text(f)
    
    # 2. Save to Processed Output
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_file = os.path.join(OUTPUT_DIR, f"{domain}_guidelines.txt")
    
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(combined_text)
    
    print(f"✅ Saved processed data to: {out_file}")
    print("-" * 40)

if __name__ == "__main__":
    # Ensure dependencies: pip install pypdf
    process_domain("diabetes")
    process_domain("hypertension")