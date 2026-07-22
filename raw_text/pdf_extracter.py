import sys
import os
import pdfplumber

def save_pdf_extract(pdf_path, output_txt_path="/Users/ada/myprojects/my-first-app/raw_text/benefits.txt"):
    """Extracts digital text from a PDF page-by-page."""
    if not os.path.exists(pdf_path):
        print(f"[ERROR] The file '{pdf_path}' could not be found.")
        return

    full_text = []
    print(f"[PROCESSING] Digital PDF: {pdf_path}...")
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            page_text = page.extract_text()
            if page_text:
                full_text.append(f"--- Page {page_num} ---\n{page_text}")
            else:
                full_text.append(f"--- Page {page_num} ---\n[No extractable text found]")

    with open(output_txt_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(full_text))
    print(f"[SUCCESS] Extraction saved to: {output_txt_path}")

if __name__ == "__main__":
    target_file = sys.argv[1] if len(sys.argv) > 1 else "/Users/ada/myprojects/my-first-app/raw_text/SBC-Template.pdf"
    save_pdf_extract(target_file)