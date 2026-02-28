import os
import base64
from io import BytesIO
from typing import Optional
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


def extract_page_as_image(page) -> str:
    """
    Extract page as base64 encoded image for GPT-4o vision.
    
    Args:
        page: pdfplumber page object
    
    Returns:
        Base64 encoded PNG image string
    """
    img = page.to_image(resolution=150)
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return base64.b64encode(img_bytes.read()).decode('utf-8')


def classify_and_extract_financial_statement(page, page_num: int) -> tuple[Optional[str], str]:
    """
    Use GPT-4o to classify a page and extract financial statement in one call.
    
    Args:
        page: pdfplumber page object
        page_num: Page number for logging
    
    Returns:
        Tuple of (classification, markdown_content)
        - classification: One of 'income_statement', 'balance_sheet', 'cash_flow', or None
        - markdown_content: Extracted markdown table (empty string if not a financial statement)
    """
    client = OpenAI(api_key=os.getenv('BRADENS_OPENAI_API_KEY'))
    
    base64_image = extract_page_as_image(page)
    
    prompt = """Analyze this page from an annual report and perform TWO tasks:

1. CLASSIFY the page into ONE of these categories:
   - income_statement: Contains Income Statement, Statement of Profit or Loss, Statement of Operations, or P&L
   - balance_sheet: Contains Balance Sheet or Statement of Financial Position
   - cash_flow: Contains Cash Flow Statement or Statement of Cash Flows
   - none: Does not contain any of the above financial statements

2. If the page contains a financial statement (not 'none'), EXTRACT it to markdown format:
   - Extract all line items, values, and columns exactly as they appear
   - Preserve the table structure using markdown tables
   - Include all headers, subtotals, and totals
   - Maintain proper indentation for sub-items
   - Include the period/year information if visible
   - Keep all numerical values exactly as shown (with currency symbols (like % and $)  if present)

Respond in this exact format:
CLASSIFICATION: [income_statement|balance_sheet|cash_flow|none]

[If not 'none', include the markdown table here. If 'none', leave this section empty.]"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=4096,
            temperature=0
        )
        
        content = response.choices[0].message.content.strip()
        
        classification = None
        markdown_content = ""
        
        if content.startswith("CLASSIFICATION:"):
            lines = content.split("\n", 1)
            classification_line = lines[0].replace("CLASSIFICATION:", "").strip().lower()
            
            if classification_line in ['income_statement', 'balance_sheet', 'cash_flow']:
                classification = classification_line
                if len(lines) > 1:
                    markdown_content = lines[1].strip()
        
        return classification, markdown_content
        
    except Exception as e:
        print(f"    Error processing page {page_num}: {e}")
        return None, ""
