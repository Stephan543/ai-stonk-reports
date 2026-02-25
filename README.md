# Stephan's Stonk Scraper

## To run
`uv run main.py`

## Key assumptions
Assume the only relavant page to scrape is the investor relations page nearest to annual reports of the company. Given the nature of this project, it is not reasonable to scrape and store the entire investor relations website for the entire history of each company. 

Assume 10 years of history implies complete history. For example, 2026 does not have an annual report, so 2026 is not included in the 10 years of history.


## Classification Keywords

| Target Statement |                                                                              |
|------------------|------------------------------------------------------------------------------|
| Income Statement | Statement of Profit or Loss ,   Income Statement ,   Statement of Operations |
| Balance Sheet    | Statement of Financial Position ,   Balance Sheet                            |
| Cash Flow        | Statement of Cash Flows ,   Cash Flow Statement                              |