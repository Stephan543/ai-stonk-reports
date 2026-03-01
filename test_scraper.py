from pathlib import Path
from scraper import run_scraper

if __name__ == "__main__":
    LOOKBACK_WINDOW_YEARS = 10
    yaml_file = 'euro-stonks.yaml'
    annual_reports_dir = Path('annual_reports')
    
    run_scraper(yaml_file, annual_reports_dir, LOOKBACK_WINDOW_YEARS)
