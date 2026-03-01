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
GPT4O_MAX_TOKENS = 4500  # Maximum tokens for response (needs to accommodate full financial tables [(15 tokens per row) * (60 rows) * (5 documents)) 
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


@dataclass
class AggregationResult:
    """Result of aggregating financial statements."""
    aggregated_markdown: str  # The aggregated markdown content
    years_processed: list[str]  # List of years that were added/updated
    duplicate_years: list[str]  # List of years that were duplicates and overwritten


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
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    base64_image = rasterize(page)
    
    prompt = """Analyze this page from an annual report and perform THREE tasks:

1. CLASSIFY the page into ONE of these categories:
   - income_statement: Contains Income Statement, Statement of Profit or Loss, Statement of Operations, or P&L
   - balance_sheet: Contains Balance Sheet or Statement of Financial Position
   - cash_flow: Contains Cash Flow Statement or Statement of Cash Flows
   - none: Does not contain any of the above financial statements

2. EXTRACT the report year/date:
   - Look for the most recent year mentioned in the financial statement (usually in column headers or title)
   - Return only the 4-digit year (e.g., '2024')
   - If multiple years are present, and you are unsure which is the most recent, return 'unknown'
   - If no year is found, return 'unknown'

3. If the page contains a financial statement (not 'none'), EXTRACT it to markdown format:
   - Extract all line items, values, and columns exactly as they appear
   - Preserve the table structure using markdown tables
   - Include all headers, subtotals, and totals
   - Maintain proper indentation for sub-items
   - Include the period/year information if visible
   - Keep all numerical values exactly as shown (with currency symbols (like % and $)  if present)

Respond in this exact format:
CLASSIFICATION: [income_statement|balance_sheet|cash_flow|none]
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
                
                if len(lines) > 1 and lines[1].startswith("REPORT_YEAR:"):
                    year_line = lines[1].replace("REPORT_YEAR:", "").strip()
                    if year_line and year_line != 'unknown':
                        report_year = year_line
                    
                    if len(lines) > 2:
                        markdown_content = "\n".join(lines[2:]).strip()
        
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


def aggregate_financial_statements(master_md: str, current_year_md: str, statement_type: str) -> AggregationResult:
    """
    Aggregate financial statements by merging current year data into master.
    
    Args:
        master_md: Existing master aggregation markdown (empty string if first year)
        current_year_md: Current year's statement markdown to merge in
        statement_type: Type of statement ('income_statement', 'balance_sheet', 'cash_flow')
    
    Returns:
        AggregationResult containing:
        - aggregated_markdown: Updated master markdown
        - years_processed: List of years added/updated
        - duplicate_years: List of duplicate years that were overwritten
    """
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    statement_title = statement_type.replace('_', ' ').title()
    
    if not master_md:
        prompt = f"""You are aggregating financial statements. This is the FIRST year being processed.

STATEMENT TYPE: {statement_title}

CURRENT YEAR DATA:
{current_year_md}

TASK:
1. Extract the markdown table from the current year data
2. Identify all year columns present in the table
3. Create a clean aggregated table with proper formatting

RESPONSE FORMAT:
YEARS_ADDED: [comma-separated list of years, e.g., "2024,2023,2022"]
DUPLICATE_YEARS: [empty for first year]

[Clean markdown table here]"""
    else:
        prompt = f"""You are aggregating financial statements. Merge the current year data into the existing master.

STATEMENT TYPE: {statement_title}

EXISTING MASTER:
{master_md}

CURRENT YEAR DATA TO MERGE:
{current_year_md}

TASK:
1. Identify all year columns in the current year data
2. For each year column in current year data:
   - If the year already exists in master, REPLACE it with the new data (most recent report takes precedence)
   - If the year is new, ADD it to the master
3. Align all line items across years
4. Handle missing line items gracefully (use "—" or empty cells)
5. Preserve currency symbols and formatting
6. Keep subtotals and totals properly aligned
7. Maintain chronological column order (oldest to newest, left to right)

RESPONSE FORMAT:
YEARS_ADDED: [comma-separated list of NEW years added, e.g., "2024"]
DUPLICATE_YEARS: [comma-separated list of years that were REPLACED, e.g., "2023,2022"]

[Complete aggregated markdown table with all years]"""
    
    try:
        response = client.chat.completions.create(
            model=GPT4O_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=GPT4O_MAX_TOKENS, 
            temperature=GPT4O_TEMPERATURE
        )
        
        content = response.choices[0].message.content.strip()
        
        years_processed = []
        duplicate_years = []
        aggregated_markdown = ""
        
        if content.startswith("YEARS_ADDED:"):
            lines = content.split("\n")
            
            years_added_line = lines[0].replace("YEARS_ADDED:", "").strip()
            if years_added_line and years_added_line != "[]":
                years_processed = [y.strip() for y in years_added_line.split(",") if y.strip()]
            
            if len(lines) > 1 and lines[1].startswith("DUPLICATE_YEARS:"):
                duplicate_line = lines[1].replace("DUPLICATE_YEARS:", "").strip()
                if duplicate_line and duplicate_line != "[]":
                    duplicate_years = [y.strip() for y in duplicate_line.split(",") if y.strip()]
                
                if len(lines) > 2:
                    aggregated_markdown = "\n".join(lines[2:]).strip()
        else:
            aggregated_markdown = content
        
        return AggregationResult(
            aggregated_markdown=aggregated_markdown,
            years_processed=years_processed,
            duplicate_years=duplicate_years
        )
        
    except Exception as e:
        print(f"    Error aggregating statements: {e}")
        return AggregationResult(
            aggregated_markdown=master_md if master_md else current_year_md,
            years_processed=[],
            duplicate_years=[]
        )
