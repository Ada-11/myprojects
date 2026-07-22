import sys
import os
import requests
from bs4 import BeautifulSoup

def scrape_provider_faq(url, output_txt_path="faq_scraped_text.txt"):
    """
    Scrapes a public FAQ webpage using requests and beautifulsoup4.
    Targets granular content nodes to bypass JavaScript/Salesforce layout component traps.
    """
    print(f"[PROCESSING] Sending request to target URL: {url}...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"[ERROR] Failed to reach page. HTTP Status Code: {response.status_code}")
            return

        soup = BeautifulSoup(response.text, "html.parser")

        # Directly capture structural text nodes that contain content text strings
        # This grabs tables, list elements, headings, and data blocks
        target_tags = ['p', 'h1', 'h2', 'h3', 'h4', 'li', 'td', 'th', 'span']
        text_elements = soup.find_all(target_tags)
        
        clean_lines = []
        seen_text = set()  # To prevent duplicates from nested child nodes (e.g. <td><span>text</span></td>)

        for element in text_elements:
            # Drop boilerplate navigation layout structures
            parent_classes = "".join(str(element.find_parents(class_=True))).lower()
            parent_tags = [parent.name for parent in element.parents]
            
            if any(nav_tag in parent_tags for nav_tag in ['nav', 'header', 'footer', 'aside', 'script', 'style']):
                continue
            if any(nav_class in parent_classes for nav_class in ['nav', 'footer', 'menu', 'sidebar', 'banner', 'utility']):
                continue

            text = element.get_text().strip()
            
            # Filter short system artifacts, empty elements, or repeated elements
            if text and len(text) > 3 and text not in seen_text:
                seen_text.add(text)
                clean_lines.append(text)

        # Join the unique content lines with space layout breaks
        final_article_text = "\n\n".join(clean_lines)

        # Export raw text layout
        with open(output_txt_path, "w", encoding="utf-8") as f:
            f.write(f"Source URL: {url}\n")
            f.write("=" * 60 + "\n\n")
            if final_article_text.strip():
                f.write(final_article_text)
            else:
                f.write("[EMPTY CONTENT] Webpage content is protected or fully locked inside JavaScript arrays.\n")
                f.write("Raw HTML length was: " + str(len(response.text)) + " characters.")
            
        print(f"[SUCCESS] Scraped content successfully written to: {output_txt_path}")

    except requests.exceptions.Timeout:
        print("[CRITICAL ERROR] The remote server took too long to respond.")
    except Exception as e:
        print(f"[CRITICAL ERROR] Web scraping engine failure: {str(e)}")

if __name__ == "__main__":
    target_faq_url = "https://www.qhpcertification.cms.gov/QHP/faqs/Network-Adequacy-FAQs"
    save_file = "faq_scraped_text.txt"
    
    if len(sys.argv) > 1:
        target_faq_url = sys.argv[1]
        
    scrape_provider_faq(target_faq_url, save_file)