import os
import base64
from io import BytesIO
from typing import Optional
from dataclasses import dataclass
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Resolution for PDF page rasterization. ~200 is the sweet spot for table extraction quality.
# Higher values improve OCR accuracy but increase image size and LLM costs.
# Lower values reduce costs but may degrade table recognition.
PDF_RASTERIZE_RESOLUTION = 150

# GPT-4o API parameters for financial statement extraction
GPT4O_MODEL = "gpt-4o"
GPT4O_MAX_TOKENS = 4096  # Maximum tokens for response (needs to accommodate full financial tables)
GPT4O_TEMPERATURE = 0    # Temperature 0 for deterministic, consistent extraction


def rasterize(page) -> str:
    """
    Rasterize PDF page to base64 encoded PNG image for GPT-4o vision.
    
    Args:
        page: pdfplumber page object
    
    Returns:
        Base64 encoded PNG image string
    """
    img = page.to_image(resolution=PDF_RASTERIZE_RESOLUTION)
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return base64.b64encode(img_bytes.read()).decode('utf-8')


@dataclass
class FinancialStatementContext:
    """Context object containing extracted financial statement information."""
    classification: Optional[str]  # 'income_statement', 'balance_sheet', 'cash_flow', or None
    markdown_content: str  # Extracted markdown table
    report_year: Optional[str]  # Year of the report (e.g., '2024')
    company_name: Optional[str]  # Name of the company


def classify_and_extract_financial_statement(page, page_num: int) -> FinancialStatementContext:
    """
    Use GPT-4o to classify a page and extract financial statement in one call.
    
    Args:
        page: pdfplumber page object
        page_num: Page number for logging
    
    Returns:
        FinancialStatementContext object containing:
        - classification: One of 'income_statement', 'balance_sheet', 'cash_flow', or None
        - markdown_content: Extracted markdown table (empty string if not a financial statement)
        - report_year: Year of the report (e.g., '2024') or None if not found
        - company_name: Name of the company or None if not found
    """
    client = OpenAI(api_key=os.getenv('BRADENS_OPENAI_API_KEY'))
    
    base64_image = rasterize(page)
    
    prompt = """Analyze this page from an annual report and perform FOUR tasks:

1. CLASSIFY the page into ONE of these categories:
   - income_statement: Contains Income Statement, Statement of Profit or Loss, Statement of Operations, or P&L
   - balance_sheet: Contains Balance Sheet or Statement of Financial Position
   - cash_flow: Contains Cash Flow Statement or Statement of Cash Flows
   - none: Does not contain any of the above financial statements

2. EXTRACT the company name:
   - Look for the company name on the page (usually at the top or in headers)
   - Return the full company name as it appears (e.g., 'Eaton Corporation')
   - If no company name is found, return 'unknown'

3. EXTRACT the report year/date:
   - Look for the most recent year mentioned in the financial statement (usually in column headers or title)
   - Return only the 4-digit year (e.g., '2024')
   - If multiple years are present, and you are unsure which is the most recent, return 'unknown'
   - If no year is found, return 'unknown'

4. If the page contains a financial statement (not 'none'), EXTRACT it to markdown format:
   - Extract all line items, values, and columns exactly as they appear
   - Preserve the table structure using markdown tables
   - Include all headers, subtotals, and totals
   - Maintain proper indentation for sub-items
   - Include the period/year information if visible
   - Keep all numerical values exactly as shown (with currency symbols (like % and $)  if present)

Respond in this exact format:
CLASSIFICATION: [income_statement|balance_sheet|cash_flow|none]
COMPANY_NAME: [company name|unknown]
REPORT_YEAR: [YYYY|unknown]

[If not 'none', include the markdown table here. If 'none', leave this section empty.]"""
    
    try:
        response = client.chat.completions.create(
            model=GPT4O_MODEL,
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
            max_tokens=GPT4O_MAX_TOKENS,
            temperature=GPT4O_TEMPERATURE
        )
        
        content = response.choices[0].message.content.strip()
        
        classification = None
        markdown_content = ""
        report_year = None
        company_name = None
        
        if content.startswith("CLASSIFICATION:"):
            lines = content.split("\n")
            classification_line = lines[0].replace("CLASSIFICATION:", "").strip().lower()
            
            if classification_line in ['income_statement', 'balance_sheet', 'cash_flow']:
                classification = classification_line
                
                if len(lines) > 1 and lines[1].startswith("COMPANY_NAME:"):
                    company_line = lines[1].replace("COMPANY_NAME:", "").strip()
                    if company_line and company_line != 'unknown':
                        company_name = company_line
                
                if len(lines) > 2 and lines[2].startswith("REPORT_YEAR:"):
                    year_line = lines[2].replace("REPORT_YEAR:", "").strip()
                    if year_line and year_line != 'unknown':
                        report_year = year_line
                    
                    if len(lines) > 3:
                        markdown_content = "\n".join(lines[3:]).strip()
        
        return FinancialStatementContext(
            classification=classification,
            markdown_content=markdown_content,
            report_year=report_year,
            company_name=company_name
        )
        
    except Exception as e:
        print(f"    Error processing page {page_num}: {e}")
        return FinancialStatementContext(
            classification=None,
            markdown_content="",
            report_year=None,
            company_name=None
        )
