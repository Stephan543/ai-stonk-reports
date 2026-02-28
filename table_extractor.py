import pdfplumber
from pathlib import Path
from typing import Set, Dict
from llm_client import classify_and_extract_financial_statement


def isTableInPage(page) -> bool:
    """
    Check if a page contains tables.
    
    Args:
        page: pdfplumber page object
    
    Returns:
        True if page contains tables, False otherwise
    """
    tables = page.extract_tables()
    return tables and any(len(table) > 0 for table in tables)


def identify_table_pages_with_context(pdf_path: Path) -> Set[int]:
    """
    Identify pages with tables and include 1 surrounding page before and after.
    
    Args:
        pdf_path: Path to the PDF file
    
    Returns:
        Set of page numbers (0-indexed) that contain tables or are within 1 page of a table
    """
    pages_with_context = set()
    
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        
        for page_num, page in enumerate(pdf.pages):
            if isTableInPage(page):
                start = max(0, page_num - 1)
                end = min(total_pages - 1, page_num + 1)
                pages_with_context.update(range(start, end + 1))
    
    return pages_with_context


def save_financial_statement_as_markdown(classification: str, markdown_content: str, output_path: Path, page_num: int):
    """
    Save extracted financial statement as markdown file.
    
    Args:
        classification: The financial statement type
        markdown_content: The extracted markdown content
        output_path: Path to save the markdown file
        page_num: Page number for the filename
    """
    if markdown_content:
        statement_title = classification.replace('_', ' ').title()
        full_content = f"# {statement_title}\n\n"
        full_content += f"**Page:** {page_num + 1}\n\n"
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
            
            print(f"  Found tables on {len(pages_to_extract)} pages (including 1-page context)")
            print(f"  Pages: {sorted(pages_to_extract)}")
            
            classifications: Dict[str, int] = {
                'income_statement': 0,
                'balance_sheet': 0,
                'cash_flow': 0
            }
            
            with pdfplumber.open(pdf_path) as pdf:
                for page_num in sorted(pages_to_extract):
                    page = pdf.pages[page_num]
                    
                    print(f"    Processing page {page_num + 1}...", end=" ")
                    classification, markdown_content = classify_and_extract_financial_statement(page, page_num)
                    
                    if classification:
                        print(f"{classification}")
                        classifications[classification] += 1
                        
                        company_dir = output_dir / pdf_path.stem
                        output_file = company_dir / f"{classification}_page_{page_num + 1}.md"
                        save_financial_statement_as_markdown(classification, markdown_content, output_file, page_num)
                        print(f"      Saved: {output_file.relative_to(output_dir)}")
                    else:
                        print("not a financial statement")
            
            print(f"\n  Summary for {pdf_path.name}:")
            print(f"    Income Statements: {classifications['income_statement']}")
            print(f"    Balance Sheets: {classifications['balance_sheet']}")
            print(f"    Cash Flow Statements: {classifications['cash_flow']}")
                
        except Exception as e:
            print(f"  Error processing {pdf_path.name}: {e}")


