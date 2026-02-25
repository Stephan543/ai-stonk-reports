from pathlib import Path
from scraper import run_scraper

LOOKBACK_WINDOW_YEARS = 10
DOCUMENT_TYPE = "annual report"
DOCUMENT_TYPE_KEYWORDS = {
    "income_statement": ["income statement", "statement of profit or loss", "statement of operations"],
    "balance_sheet": ["balance sheet", "statement of financial position"],
    "cash_flow": ["cash flow", "statement of cash flows", "cash flow statement"],
}

def main():
    yaml_file = 'euro-stonks.yaml'
    output_dir = Path('annual_reports')
    
    run_scraper(yaml_file, output_dir, LOOKBACK_WINDOW_YEARS)

if __name__ == "__main__":
    main()
