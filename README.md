# Stephan's Stonk Scraper

An automated pipeline for scraping, classifying, extracting, and aggregating financial statements from European company annual reports. The system downloads PDFs from investor relations pages, uses AI-powered OCR to extract financial tables, and aggregates multi-year data into master financial statements.

## Setup

**Install dependencies:**

This project uses `uv` for dependency management. Dependencies are defined in `pyproject.toml`.

```bash
uv sync
```

**Set the environment variable:**

```bash
OPENAI_API_KEY=your_api_key_here
```

## To test locally

**Recommended: Start with Step 2** using the pre-scraped `golden_test_files` to save time and API costs. The golden files contain already-downloaded and trimmed PDFs ready for extraction.

### Sequential Testing Steps

The pipeline consists of three sequential stages. Each can be tested independently:

**Step 1: Web Scraper** *(Optional - skip for testing)* - Downloads annual report PDFs from company investor relations pages
```bash
uv run test_scraper.py
```

**Step 2: Table Extractor** *(Start here)* - Classifies and extracts financial statements from PDFs using AI
```bash
uv run test_table_extractor.py
```

**Step 3: Statement Aggregator** - Merges multi-year statements into master views
```bash
uv run test_statement_aggregator.py
```

### Full Pipeline

To run all three stages sequentially in one command:
```bash
uv run main.py
```

> **⚠️ Disclaimer:** The full pipeline is not well tested. Running 1 company through 10yrs of history can take > 1hr. See Future Improvements for a potential solution.

## To scrape a new company

1. Add the company to the `euro-stonks.yaml` file.
2. Run the scraper independently or in via `main.py`

## Key assumptions
Assume the only relavant web page to scrape is the investor relations page nearest to annual reports of the company. Out of scope to scrape and store the entire investor relations website for the entire history of each company. 

Assume the income statement, balance sheet, and cash flow statement are the only financial statements of interest and are always present and in the form of a table. Out of scope to scrape and store other financial statements or verbage. 

Assume all PDFs contain native text and are not scanned images.

Assume all PDFs are in English.

Assume 10 years of history implies complete history. For example, 2026 does not have an annual report, so 2026 is not included in the 10 years of history.

## Design Decisions
### Two pass strategy
`pdfPlumber` is used to detect pages that contain tables. Detected pages are sent to a low cost LLM to classify and extract the financial statements. GPT-4o is used for document classification. The purpose of this is to leverage heuristics to pre process and reduce the number of pages sent to the LLM for extraction. This will greatly improve time and cost efficiency.

### Convert pdf pages to images (rasterize)
Table extraction and preservation of formatting is funky business and not always reliable. In my testing, using pure heuristics did not make the cut for the variety of financial docs. 

`pdfPlumber` is used to rasterize pages into images for the LLM to use OCR on. This is the most reliable method I found.

### "Rolling Master" aggregation
The most common aggregation strategy is to use map reduce to strict target schema defined by an LLM. The issue with this is line items are not always consistent across years. 

The most reasonable method found was to use the LLM to handle the merging logic using an iterative approach to avoid massive context windows and allow for more extensible and flexible merging logic.

## Known Issues
### The scraper has a tendency to miss the most recent annual report.
This happens because the scraper is entirely heuristic based. Meaning it depends on the naming convention of the annual report. If the original filename does not contain the year, the scraper will miss the most recent annual report.

See Future Improvements for a potential solution.

### Most testing was done with the golden_test_files.
To demonstrate long-term efficacy and resilience, comprehensive end-to-end (E2E) tests must be executed for a wider range of companies using `main.py`.

## Future Improvements

### Concurrent scraping, classification, and extraction.
Either batch or make concurrent requests to LLM for classification, and extraction. Note aggregation implies sequential requests. with the current "Rolling Master" strategy.

### Improve table identification and extraction.
When running extraction against 100+ page pdf the LLM can incorrectly identify tables. We can use prompt refinement to fix this or a better model with supervised learning. 

### Implement hybrid web scraper for investor relations websites using heuristics and LLMs to detect annual reports.
At the moment investor relations pages for EU companies are not consistent. Annual reports are not named consistently, and are not always in the same location. 

For example: 
 - some companies use "Annual report" to identify the latest (2025 when this was written) annual report.
 - Some companies used dated annual reports, such as "Annual Report 2025".
 - Some companies store all annual reports in the same location.
 - Some companies require filter and search to find the annual report.

### Implement vector store for efficient retrieval of annual reports for future analysis.
A vector store would allow for efficient retrieval of annual reports for future analysis. Furthermore it would allow end user to create custom queries and dashboards.

### Test alternative Markdown structures.
According to some benchmarks Markdown-KV is more machine friendly than traditional markdown tables. This could potentially improve the quality, cost, and speed of the extracted table aggregation.

### Batch upload to save costs
If data does not need to be processed in real-time, batch upload to save costs.
https://developers.openai.com/api/docs/guides/batch/


