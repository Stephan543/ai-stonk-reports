from pathlib import Path
from datetime import datetime
from llm_client import aggregate_financial_statements, AggregationResult

STATEMENT_TYPES = ['income_statement', 'balance_sheet', 'cash_flow']


def combine_pages_for_year(year_dir: Path, statement_type: str) -> str:
    """
    Combine all pages for a given year and statement type into single markdown.
    
    Some statements types may have a structure like: 
    
    Args:
        year_dir: Path to the year directory (e.g., result_tables/Company/2024)
        statement_type: Type of statement ('income_statement', 'balance_sheet', 'cash_flow')
    
    Returns:
        Combined markdown content from all pages
    """
    statement_dir = year_dir / statement_type
    
    if not statement_dir.exists():
        return ""
    
    page_files = sorted(statement_dir.glob(f"{statement_type}_page_*.md"))
    
    if not page_files:
        return ""
    
    combined_content = []
    
    for page_file in page_files:
        content = page_file.read_text(encoding='utf-8')
        
        lines = content.split('\n')
        markdown_started = False
        page_content = []
        
        for line in lines:
            if line.startswith('---'):
                markdown_started = True
                continue
            
            if markdown_started and line.strip():
                page_content.append(line)
        
        if page_content:
            combined_content.extend(page_content)
    
    return '\n'.join(combined_content)


def aggregate_company_statements(result_tables_dir: Path, company_name: str):
    """
    Aggregate all financial statements for a single company.
    
    Args:
        result_tables_dir: Root directory containing result tables
        company_name: Name of the company to aggregate
    """
    company_dir = result_tables_dir / company_name
    
    if not company_dir.exists():
        print(f"  Company directory not found: {company_dir}")
        return
    
    year_dirs = [d for d in company_dir.iterdir() if d.is_dir() and d.name != 'master']
    
    if not year_dirs:
        print(f"  No year directories found for {company_name}")
        return
    
    years = []
    for year_dir in year_dirs:
        try:
            year = int(year_dir.name)
            years.append((year, year_dir))
        except ValueError:
            continue
    
    years.sort(key=lambda x: x[0])
    
    print(f"\n{'='*60}")
    print(f"Aggregating statements for: {company_name}")
    print(f"Years found: {[y[0] for y in years]}")
    print(f"{'='*60}")
    
    master_dir = company_dir / 'master'
    master_dir.mkdir(parents=True, exist_ok=True)
    
    for statement_type in STATEMENT_TYPES:
        print(f"\n  Processing {statement_type.replace('_', ' ').title()}...")
        
        master_file = master_dir / f"{statement_type}_master.md"
        
        if master_file.exists():
            master_file.unlink()
            print("Deleted existing master file for fresh regeneration")
        
        master_md = ""
        all_years_processed = []
        all_duplicates = []
        
        for year, year_dir in years:
            print(f"    Processing year {year}...", end=" ")
            
            year_content = combine_pages_for_year(year_dir, statement_type)
            
            if not year_content:
                print(f"No {statement_type} data found")
                continue
            
            try:
                result: AggregationResult = aggregate_financial_statements(
                    master_md=master_md,
                    current_year_md=year_content,
                    statement_type=statement_type
                )
                
                master_md = result.aggregated_markdown
                
                if result.years_processed:
                    all_years_processed.extend(result.years_processed)
                    print(f"Added years: {', '.join(result.years_processed)}", end="")
                
                if result.duplicate_years:
                    all_duplicates.extend(result.duplicate_years)
                    print(f" | Overwrote duplicates: {', '.join(result.duplicate_years)}", end="")
                
                print()
                
            except Exception as e:
                print(f"ERROR: {e}")
                continue
        
        if master_md:
            statement_title = statement_type.replace('_', ' ').title()
            oldest_year = years[0][0] if years else 'Unknown'
            newest_year = years[-1][0] if years else 'Unknown'
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            full_content = f"# {statement_title} - Master Aggregation\n\n"
            full_content += f"**Company:** {company_name}\n"
            full_content += f"**Years Covered:** {oldest_year} - {newest_year}\n"
            full_content += f"**Last Updated:** {timestamp}\n\n"
            full_content += "---\n\n"
            full_content += master_md
            
            master_file.write_text(full_content, encoding='utf-8')
            print(f"    ✓ Saved master file: {master_file.relative_to(result_tables_dir)}")
            print(f"    Summary: {len(set(all_years_processed))} unique years, {len(set(all_duplicates))} duplicates overwritten")
        else:
            print(f"    No data aggregated for {statement_type}")


def aggregate_statements_from_directory(result_tables_dir: Path):
    """
    Aggregate financial statements for all companies in the directory.
    
    Args:
        result_tables_dir: Root directory containing extracted tables organized by company
    """
    if not result_tables_dir.exists():
        print(f"Directory not found: {result_tables_dir}")
        return
    
    company_dirs = [d for d in result_tables_dir.iterdir() if d.is_dir()]
    
    if not company_dirs:
        print(f"No company directories found in {result_tables_dir}")
        return
    
    print(f"\n{'='*60}")
    print("FINANCIAL STATEMENT AGGREGATION")
    print(f"{'='*60}")
    print(f"Found {len(company_dirs)} companies to process")
    
    for company_dir in company_dirs:
        aggregate_company_statements(result_tables_dir, company_dir.name)
    
    print(f"\n{'='*60}")
    print("AGGREGATION COMPLETE")
    print(f"{'='*60}")
