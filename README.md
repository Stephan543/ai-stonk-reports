# Stephan's Stonk Scraper

## To run

Set your env variables:

```bash
BRADENS_OPENAI_API_KEY=?
LLAMA_CLOUD_API_KEY=?
```

Run the project:
```ssh
> uv run main.py
```

## Key assumptions
Assume the only relavant page to scrape is the investor relations page nearest to annual reports of the company. Given the nature of this project, it is not reasonable to scrape and store the entire investor relations website for the entire history of each company. 

Assume all PDFs are digital and not scanned images.
Assume 10 years of history implies complete history. For example, 2026 does not have an annual report, so 2026 is not included in the 10 years of history.

## Design Decisions
### Why use Llama extraction?
Two-pass strategy — Its a cheap full-scan first (fast mode) to detect which pages contain financial statements, then fires a focused deep extraction only on those pages. This keeps API costs down on a 100-page PDF by avoiding LLM processing on every page.