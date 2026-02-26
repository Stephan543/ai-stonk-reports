import os
import re
from pathlib import Path
from llama_parse import LlamaParse
from dotenv import load_dotenv
import time

load_dotenv()

TARGET_TABLES = {
    "income_statement":  ["income statement", "profit or loss", "statement of operations"],
    "balance_sheet":     ["balance sheet", "financial position"],
    "cash_flow":         ["cash flow", "statement of cash flows"],
}

TABLE_NAMES = list(TARGET_TABLES.keys())

SCAN_INSTRUCTION = (
    "This is a financial annual report. "
    "Return only the page numbers that contain an Income Statement, "
    "Balance Sheet, or Cash Flow Statement."
)

EXTRACT_INSTRUCTION = (
    "This document contains financial statements. "
    "Extract ONLY the following tables in full, preserving all rows, columns, "
    "and numeric values exactly as they appear:\n"
    "1. Income Statement (or Statement of Profit or Loss / Operations)\n"
    "2. Balance Sheet (or Statement of Financial Position)\n"
    "3. Cash Flow Statement (or Statement of Cash Flows)\n"
    "Output each table as a clean Markdown table with a ## heading above it. "
    "Do not include any other content."
)

PAGE_SEPARATOR = "--- PAGE {pageNumber} ---"
PARSE_DELAY = 1


def find_table_pages(text: str, aliases: list[str]) -> list[int]:
    """Return page numbers (0-indexed) where any alias heading is found."""
    pages = []
    sections = re.split(r"--- PAGE (\d+) ---", text)
    for i in range(1, len(sections) - 1, 2):
        page_num = int(sections[i])
        content  = sections[i + 1].lower()
        if any(alias in content for alias in aliases):
            pages.append(page_num)
    return pages


def extract_section(md: str, aliases: list[str]) -> str:
    """Pull the markdown block starting at a matching ## heading."""
    lines   = md.splitlines()
    capture = False
    buf     = []
    for line in lines:
        lower = line.lower()
        if line.startswith("##") and any(alias in lower for alias in aliases):
            capture = True
        elif line.startswith("##") and capture:
            break
        if capture:
            buf.append(line)
    return "\n".join(buf).strip()


def extract_tables_from_pdf(pdf_path, api_key):
    """Extract financial tables from a single PDF using two-pass strategy."""
    try:
        scanner = LlamaParse(
            api_key=api_key,
            result_type="markdown",
            parsing_instruction=SCAN_INSTRUCTION,
            page_separator=PAGE_SEPARATOR,
            hide_headers=False,
            hide_footers=True,
        )
        
        print(f"    Scanning: {pdf_path.name} for financial statement pages...")
        scan_docs = scanner.load_data(str(pdf_path))
        full_text = "\n".join(doc.text for doc in scan_docs)
        
        discovered_pages: dict[str, list[int]] = {}
        for table_key, aliases in TARGET_TABLES.items():
            found = find_table_pages(full_text, aliases)
            discovered_pages[table_key] = found
            if found:
                print(f"      {table_key}: found on pages {found}")
        
        all_pages = sorted(set(p for pages in discovered_pages.values() for p in pages))
        
        if not all_pages:
            print(f"    Warning: No financial statement pages found in {pdf_path.name}")
            return None
        
        # Add next page to each page assuming some tables span multiple pages
        expanded_pages = sorted(set(all_pages + [p + 1 for p in all_pages])) 
        target_pages_str = ",".join(str(p) for p in expanded_pages)
        print(f"    Targeting pages for deep extraction: {target_pages_str}")
        
        extractor = LlamaParse(
            api_key=api_key,
            result_type="markdown",
            target_pages=target_pages_str,
            parsing_instruction=EXTRACT_INSTRUCTION,
            output_tables_as_HTML=False,
            merge_tables_across_pages=True,
            auto_mode=True,
            auto_mode_trigger_on_table_in_page=True,
            hide_headers=True,
            hide_footers=True,
        )
        
        print(f"    Running deep extraction on targeted pages...")
        docs = extractor.load_data(str(pdf_path))
        extracted_md = "\n\n".join(doc.text for doc in docs)
        
        income_statement_md = extract_section(extracted_md, TARGET_TABLES["income_statement"])
        balance_sheet_md    = extract_section(extracted_md, TARGET_TABLES["balance_sheet"])
        cash_flow_md        = extract_section(extracted_md, TARGET_TABLES["cash_flow"])
        
        return {
            "full": extracted_md,
            "income_statement": income_statement_md,
            "balance_sheet": balance_sheet_md,
            "cash_flow": cash_flow_md,
        }
            
    except Exception as e:
        print(f"    Error parsing {pdf_path.name}: {str(e)}")
        return None


def convert_pdfs_to_markdown_tables(annual_reports_dir, output_dir, api_key=None):
    """Convert all annual report PDFs to markdown tables."""
    if api_key is None:
        api_key = os.getenv('LLAMA_CLOUD_API_KEY')
    
    if not api_key:
        raise ValueError("LLAMA_CLOUD_API_KEY not found in environment variables or .env file")
    
    annual_reports_path = Path(annual_reports_dir)
    output_path = Path(output_dir)
    
    if not annual_reports_path.exists():
        print(f"Error: Annual reports directory not found: {annual_reports_path}")
        return 0
    
    print("\n" + "="*60)
    print("Starting Table Extraction from Annual Reports")
    print("="*60)
    
    total_processed = 0
    total_extracted = 0
    
    company_dirs = [d for d in annual_reports_path.iterdir() if d.is_dir()]
    
    for company_dir in sorted(company_dirs):
        company_name = company_dir.name
        print(f"\nProcessing: {company_name}")
        
        pdf_files = list(company_dir.glob("*.pdf"))
        
        if not pdf_files:
            print(f"  No PDF files found for {company_name}")
            continue
        
        company_output_dir = output_path / company_name
        company_output_dir.mkdir(parents=True, exist_ok=True)
        
        for pdf_file in sorted(pdf_files):
            total_processed += 1
            
            output_filename = pdf_file.stem + "_tables.md"
            output_file = company_output_dir / output_filename
            
            if output_file.exists():
                print(f"    Skipped: {output_filename} (already exists)")
                continue
            
            result = extract_tables_from_pdf(pdf_file, api_key)
            
            if result:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(f"# Financial Tables Extracted from {pdf_file.name}\n\n")
                    f.write(f"**Extraction Date:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    f.write("---\n\n")
                    f.write(result["full"])
                
                for table_name in TABLE_NAMES:
                    content = result.get(table_name, "")
                    if content:
                        table_file = company_output_dir / (pdf_file.stem + f"_{table_name}.md")
                        with open(table_file, 'w', encoding='utf-8') as f:
                            f.write(content)
                        print(f"    ✓ Saved {table_file.name} ({len(content)} chars)")
                    else:
                        print(f"    ⚠  Could not isolate {table_name}")
                
                file_size = output_file.stat().st_size / 1024
                print(f"    Saved: {output_filename} ({file_size:.2f} KB)")
                total_extracted += 1
            
            time.sleep(PARSE_DELAY)
    
    print("\n" + "="*60)
    print(f"Table Extraction Complete!")
    print(f"Processed: {total_processed} PDFs")
    print(f"Extracted: {total_extracted} table files")
    print(f"Output directory: {output_path.absolute()}")
    print("="*60)
    
    return total_extracted
