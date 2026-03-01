import re
import yaml
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urljoin
import time
from utils import sanitize_filename


ANNUAL_REPORT_KEYWORDS = [
    'annual report',
    'annual-report',
    'annualreport',
]

REQUEST_TIMEOUT = 60        # Increased timeout for slow servers
DOWNLOAD_TIMEOUT = 90
DOWNLOAD_DELAY = 2          # Extend this to not hammer their download API
MAX_RETRIES = 3             
RETRY_DELAY = 5             
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36'

BASIC_HEADERS = {
    'User-Agent': USER_AGENT
}

BROWSER_HEADERS = {
    'User-Agent': USER_AGENT,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'en-CA,en-US;q=0.9,en-GB;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'Cache-Control': 'max-age=0',
    'Sec-Ch-Ua': '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
    'Sec-Ch-Ua-Mobile': '?0',
    'Sec-Ch-Ua-Platform': '"macOS"',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1',
    'Priority': 'u=0, i'
}


def load_companies(yaml_file):
    """Load company data from YAML file."""
    with open(yaml_file, 'r') as f:
        companies = yaml.safe_load(f)
    return companies


def get_target_years(years_to_scrape):
    """Calculate target years for annual reports."""
    current_year = datetime.now().year
    latest_report_year = current_year - 1
    target_years = list(range(latest_report_year - years_to_scrape + 1, latest_report_year + 1))
    return target_years


def is_pdf_link(url):
    """Check if URL is a PDF link."""
    return url.lower().endswith('.pdf')


def is_annual_report(text, url):
    """Check if link text or URL suggests it's an annual report."""
    if not text:
        text = ""
    combined = f"{text.lower()} {url.lower()}"
    
    return any(keyword in combined for keyword in ANNUAL_REPORT_KEYWORDS)


def extract_year_from_text(text, url, target_years):
    """Extract year from text or URL."""
    combined = f"{text} {url}"
    
    year_pattern = r'\b(20\d{2})\b'
    matches = re.findall(year_pattern, combined)
    
    for match in matches:
        year = int(match)
        if year in target_years:
            return year
    
    return None


def scrape_annual_reports(company, target_years):
    """Scrape annual report PDFs from company's investor relations page."""
    company_name = company['name']
    ir_url = company['investor_relations_url']
    use_modern_headers = company.get('use_modern_headers', True)
    
    headers = BROWSER_HEADERS if use_modern_headers else BASIC_HEADERS
    
    print(f"\n{'='*60}")
    print(f"Scraping: {company_name}")
    print(f"URL: {ir_url}")
    print(f"{'='*60}")
    
    for attempt in range(MAX_RETRIES):
        try:
            if attempt > 0:
                print(f"  Retry attempt {attempt + 1}/{MAX_RETRIES}...")
                time.sleep(RETRY_DELAY)
            
            response = requests.get(ir_url, headers=headers, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'lxml')
            
            links = soup.find_all('a', href=True)
            
            annual_report_pdf_links = []
            pdf_count = 0
            
            for link in links:
                href = link['href']
                link_text = link.get_text(strip=True)
                
                absolute_url = urljoin(ir_url, href)
                
                if is_pdf_link(absolute_url):
                    pdf_count += 1
                    if is_annual_report(link_text, absolute_url):
                        year = extract_year_from_text(link_text, absolute_url, target_years)
                        
                        if year:
                            annual_report_pdf_links.append({
                                'url': absolute_url,
                                'year': year,
                                'text': link_text
                            })
                            print(f"  Found: {year} - {link_text[:80]}")
            
            if pdf_count > 0 and not annual_report_pdf_links:
                print(f"  Found {pdf_count} PDF links but none matched annual report criteria")
            
            return annual_report_pdf_links
        
        except requests.exceptions.Timeout as e:
            if attempt < MAX_RETRIES - 1:
                print(f"  Timeout error, retrying... ({str(e)})")
            else:
                print(f"  Error scraping {company_name} after {MAX_RETRIES} attempts: {str(e)}")
                return []
        
        except Exception as e:
            print(f"  Error scraping {company_name}: {str(e)}")
            return []
    
    return []


def download_pdf(url, save_path):
    """Download PDF from URL to save_path."""
    try:
        response = requests.get(url, headers=BROWSER_HEADERS, timeout=DOWNLOAD_TIMEOUT, stream=True)
        response.raise_for_status()
        
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        file_size = save_path.stat().st_size / (1024 * 1024)
        print(f"    Downloaded: {save_path.name} ({file_size:.2f} MB)")
        return True
    
    except Exception as e:
        print(f"    Error downloading {url}: {str(e)}")
        return False


def run_scraper(yaml_file, output_dir, years_to_scrape):
    """Main scraper execution function."""
    print("Starting Annual Report Scraper")
    print("="*60)
    
    companies = load_companies(yaml_file)
    print(f"Loaded {len(companies)} companies from {yaml_file}")
    
    target_years = get_target_years(years_to_scrape)
    print(f"Target years: {target_years[0]} - {target_years[-1]}")
    
    total_downloaded = 0
    
    for company in companies:
        company_name = company['name']
        safe_name = sanitize_filename(company_name)
        
        pdf_links = scrape_annual_reports(company, target_years)
        
        if not pdf_links:
            print(f"  No annual reports found for {company_name}")
            continue
        
        print(f"\n  Downloading {len(pdf_links)} reports for {company_name}...")
        
        for pdf_info in pdf_links:
            year = pdf_info['year']
            url = pdf_info['url']
            
            filename = f"{safe_name}_{year}_Annual_Report.pdf"
            save_path = output_dir / safe_name / filename
            
            if save_path.exists():
                print(f"    Skipped: {filename} (already exists)")
                continue
            
            if download_pdf(url, save_path):
                total_downloaded += 1
            
            time.sleep(DOWNLOAD_DELAY)
    
    print("\n" + "="*60)
    print(f"Scraping complete! Downloaded {total_downloaded} annual reports.")
    print(f"Reports saved to: {output_dir.absolute()}")
    print("="*60)
    
    return total_downloaded
