import sys
import os
import io
from PIL import Image
import pytesseract
from pypdf import PdfReader

def convert_from_path(pdf_path, dpi=300):
    """
    Simulates pdf2image.convert_from_path using pure Python libraries.
    Extracts embedded page images so you do not need to install Poppler.
    """
    extracted_images = []
    reader = PdfReader(pdf_path)
    for page in reader.pages:
        for image_file_object in page.images:
            image_bytes = image_file_object.data
            img = Image.open(io.BytesIO(image_bytes))
            extracted_images.append(img)
    return extracted_images

def save_scanned_ocr_extract(file_path, output_txt_path="/Users/ada/myprojects/my-first-app/raw_text/enrollment.txt"):
    """Performs OCR on scanned text graphics or flat scanned photo PDFs."""
    if not os.path.exists(file_path):
        print(f"[ERROR] The file '{file_path}' could not be found.")
        return

    full_text = []
    _, ext = os.path.splitext(file_path.lower())
    print(f"[PROCESSING] OCR execution on: {file_path}...")

    try:
        # Handle scanned multipage PDFs
        if ext == '.pdf':
            pages = convert_from_path(file_path, dpi=300) 
            for page_num, page_img in enumerate(pages, start=1):
                text = pytesseract.image_to_string(page_img, lang="eng")
                full_text.append(f"--- Scanned Page {page_num} ---\n{text}")
                
                # Note any OCR accuracy issues with handwriting or checkboxes per page
                print(f"[NOTE] Page {page_num}: Checkboxes and handwriting may exhibit reduced OCR accuracy.")
        
        # Handle standalone image documents
        elif ext in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
            with Image.open(file_path) as img:
                text = pytesseract.image_to_string(img, lang="eng")
                full_text.append(text)
                
            # Note any OCR accuracy issues with handwriting or checkboxes for flat images
            print("[NOTE] Image file: Checkboxes and handwriting may exhibit reduced OCR accuracy.")
        else:
            print(f"[ERROR] Unsupported file extension format: {ext}")
            return

        with open(output_txt_path, "w", encoding="utf-8") as f:
            f.write("\n\n".join(full_text))
        print(f"[SUCCESS] OCR Extraction saved to: {output_txt_path}")

    except Exception as e:
        print(f"[CRITICAL ERROR] OCR Engine failure: {str(e)}")

if __name__ == "__main__":
    target_file = sys.argv if len(sys.argv) > 1 else "/Users/ada/myprojects/my-first-app/raw_text/scanned_form.pdf"
    save_scanned_ocr_extract(target_file)