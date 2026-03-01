# Stephan's Stonk Scraper

## To run

Set the environment variable:

```bash
BRADENS_OPENAI_API_KEY=?
```

To test just the pdf classification/extractor:
```ssh
> uv run test_table_extractor.py
```

To run the full web scraper and classification of the project:
```ssh
> uv run main.py
```

Run the table extractor:
```ssh
> uv run test_table_extractor.py
```

## To scrape a new company

1. Add the company to the `euro-stonks.yaml` file.
2. Run the scraper.
3. Run the table extractor.

## Key assumptions
Assume the only relavant web page to scrape is the investor relations page nearest to annual reports of the company. Out of scope to scrape and store the entire investor relations website for the entire history of each company. 

Assume the income statement, balance sheet, and cash flow statement are the only financial statements of interest and are always in the form of a table. Out of scope to scrape and store other financial statements or verbage. 

Assume all PDFs are digital and not scanned images.

Assume 10 years of history implies complete history. For example, 2026 does not have an annual report, so 2026 is not included in the 10 years of history.

## Design Decisions
### Two pass strategy
Use pdfplumber to detect pages that contain tables. Send the detected pages to a low cost LLM to extract the financial statements. GPT-4o is used for document classification. The purpose of this is to leverage heuristics to pre process and reduce the number of pages sent to the LLM for extraction. This will greatly improve time and cost efficiency.

### Convert pdf pages to images (rasterize)
Table extraction and preservation of formatting is funky business and not always reliable. In my testing using pure heuristics did not make the cut for the variety of financial docs. 

Using pdfplumber to rasterize pages into images for the LLM to use OCR on, was the most reliable method I could find.

### "Rolling Master" aggregation
The most common determinisc strategy is to use map reduce to strict target schema defined by an LLM. The issue with this is line items are not always consistent across years. 

The most reasonable method found was to use the LLM to handle the merging logic using an iterative approach to avoid massive context windows.

## Known Issues
### The scraper has a tendency to miss the most recent annual report since they are not usually dated.

## Future Improvements

### Implement hybrid web scraper for investor relations websites using heuristics and llms to detect annual reports.
At the moment investor relations pages for EU companies are not consistent. Annual reports are not named consistently, and are not always in the same location. 

For example: 
 - some companies use "Annual report" to identify the latest (2025 when this was written) annual report.
 - Some companies used dated annual reports, such as "Annual Report 2025".
 - Some companies store all annual reports in the same location.
 - Some companies require filter and search to find the annual report.

### Implement OCR for scanned PDFs.

### Test alternative Markdown structures.
According to some benchmakrs Markdown-KV is more machine friendly than traditional markdown tables.

### Implement vector store for efficient retrieval of annual reports for future analysis.
A vector store would allow for efficient retrieval of annual reports for future analysis. And allow end user to create custom queries and dashboards.

### Concurrent scraping and extraction.

### Batch upload to save costs
If data does not need to be processed in real-time, batch upload to save costs.
https://developers.openai.com/api/docs/guides/batch/


