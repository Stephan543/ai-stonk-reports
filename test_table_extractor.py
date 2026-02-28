from pathlib import Path
from table_extractor import convert_pdfs_to_markdown_tables

if __name__ == "__main__":
    annual_reports_dir = Path('golden_test_files/test_company_annual_reports')
    extracted_tables_dir = Path('golden_test_files/test_company_markdown_result')
    
    convert_pdfs_to_markdown_tables(annual_reports_dir, extracted_tables_dir)
