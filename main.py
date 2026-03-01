from pathlib import Path
from scraper import run_scraper
from table_extractor import convert_pdfs_to_markdown_tables
from statement_aggregator import aggregate_statements_from_directory

LOOKBACK_WINDOW_YEARS = 10
DOCUMENT_TYPE = "annual report"
DOCUMENT_TYPE_KEYWORDS = {
    "income_statement": ["income statement", "statement of profit or loss", "statement of operations"],
    "balance_sheet": ["balance sheet", "statement of financial position"],
    "cash_flow": ["cash flow", "statement of cash flows", "cash flow statement"],
}

def main():
    yaml_file = 'euro-stonks.yaml'
    annual_reports_dir = Path('annual_reports')
    result_tables_dir = Path('result_tables')
    
    run_scraper(yaml_file, annual_reports_dir, LOOKBACK_WINDOW_YEARS)
    
    print("\n" + "="*60)
    print("Starting table extraction from downloaded reports...")
    print("="*60)
    
    convert_pdfs_to_markdown_tables(annual_reports_dir, result_tables_dir, yaml_file)
    
    print("\n" + "="*60)
    print("Starting statement aggregation...")
    print("="*60)
    
    aggregate_statements_from_directory(result_tables_dir)

if __name__ == "__main__":
    main()
