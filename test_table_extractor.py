from pathlib import Path
from table_extractor import convert_pdfs_to_markdown_tables

if __name__ == "__main__":
    yaml_file = 'euro-stonks.yaml'
    annual_reports_dir = Path('golden_test_files/annual_reports')
    result_tables_dir = Path('golden_test_files/result_tables')
    
    convert_pdfs_to_markdown_tables(annual_reports_dir, result_tables_dir, yaml_file)
