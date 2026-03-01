import pdfplumber
from pathlib import Path
from typing import Set, Dict
from llm_client import classify_and_extract_financial_statement, FinancialStatementContext

SURROUNDING_CONTEXT_PAGES = 0


def isTableInPage(page) -> bool:
    """
    Check if a page contains tables.
    
    Args:
        page: pdfplumber page object
    
    Returns:
        True if page contains tables, False otherwise
    """
    tables = page.extract_tables()
    # extract_tables can return a list of empty tables, so we need to check if any of them are non-empty
    if tables and any(len(table) > 0 for table in tables):
        return True
    
    # Fallback: use text-based table detection if no tables found with default settings
    table_settings = {
        "vertical_strategy": "text", 
        "horizontal_strategy": "text" 
    }
    tables = page.extract_tables(table_settings)
    return tables and any(len(table) > 0 for table in tables)


def identify_table_pages_with_context(pdf_path: Path) -> Set[int]:
    """
    Identify pages with tables and include surrounding pages before and after.
    
    Args:
        pdf_path: Path to the PDF file
    
    Returns:
        Set of page numbers (0-indexed) that contain tables or are within SURROUNDING_CONTEXT_PAGES of a table
    """
    pages_with_context = set()
    
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        
        for page_num, page in enumerate(pdf.pages):
            if isTableInPage(page):
                start = max(0, page_num - SURROUNDING_CONTEXT_PAGES)
                end = min(total_pages - 1, page_num + SURROUNDING_CONTEXT_PAGES)
                pages_with_context.update(range(start, end + 1))
    
    return pages_with_context


def save_financial_statement_as_markdown(classification: str, markdown_content: str, output_path: Path, page_num: int, report_year: str = None):
    """
    Save extracted financial statement as markdown file.
    
    Args:
        classification: The financial statement type
        markdown_content: The extracted markdown content
        output_path: Path to save the markdown file
        page_num: Page number for the filename
        report_year: Year of the report (optional) - fallback to unknown_year
    """
    if markdown_content:
        statement_title = classification.replace('_', ' ').title()
        full_content = f"# {statement_title}\n\n"
        full_content += f"**Page:** {page_num + 1}\n\n"
        if report_year:
            full_content += f"**Report Year:** {report_year}\n\n"
        full_content += "---\n\n"
        full_content += markdown_content
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(full_content, encoding='utf-8')


def convert_pdfs_to_markdown_tables(input_dir: Path, output_dir: Path):
    """
    Process PDFs to extract tables and convert to markdown.
    
    Args:
        input_dir: Directory containing PDF files
        output_dir: Directory to save extracted tables
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    pdf_files = list(input_dir.glob("**/*.pdf"))
    
    if not pdf_files:
        print(f"No PDF files found in {input_dir}")
        return
    
    print(f"Found {len(pdf_files)} PDF files to process")
    
    for pdf_path in pdf_files:
        print(f"\nProcessing: {pdf_path.name}")
        
        try:
            pages_to_extract = identify_table_pages_with_context(pdf_path)
            
            if not pages_to_extract:
                print(f"  No tables found in {pdf_path.name}")
                continue
            
            print(f"  Found tables on {len(pages_to_extract)} pages (including {SURROUNDING_CONTEXT_PAGES}-page context)")
            print(f"  Pages: {sorted(pages_to_extract)}")
            
            classifications: Dict[str, int] = {
                'income_statement': 0,
                'balance_sheet': 0,
                'cash_flow': 0
            }
            
            report_years = {}
            extracted_company_name = None
            
            with pdfplumber.open(pdf_path) as pdf:
                for page_num in sorted(pages_to_extract):
                    page = pdf.pages[page_num]
                    
                    print(f"    Processing page {page_num + 1}...", end=" ")
                    context: FinancialStatementContext = classify_and_extract_financial_statement(page, page_num)
                    
                    if context.classification:
                        print(f"{context.classification} (Company: {context.company_name or 'unknown'}, Year: {context.report_year or 'unknown'})")
                        classifications[context.classification] += 1
                        
                        if context.report_year:
                            report_years[context.classification] = context.report_year
                        
                        if context.company_name and not extracted_company_name:
                            extracted_company_name = context.company_name
                        
                        year_dir = context.report_year if context.report_year else 'unknown_year'
                        company_name = extracted_company_name if extracted_company_name else pdf_path.stem
                        
                        company_dir = output_dir / company_name / year_dir / context.classification
                        output_file = company_dir / f"{context.classification}_page_{page_num + 1}.md"
                        save_financial_statement_as_markdown(context.classification, context.markdown_content, output_file, page_num, context.report_year)
                        print(f"      Saved: {output_file.relative_to(output_dir)}")
                    else:
                        print("not a financial statement")
            
            print(f"\n  Summary for {pdf_path.name}:")
            print(f"    Income Statements: {classifications['income_statement']}")
            print(f"    Balance Sheets: {classifications['balance_sheet']}")
            print(f"    Cash Flow Statements: {classifications['cash_flow']}")
                
        except Exception as e:
            print(f"  Error processing {pdf_path.name}: {e}")


