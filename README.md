# ETF NAV and Holdings Analyzer

A Python tool to fetch, merge, and analyze ETF holdings and price data, providing a detailed NAV discrepancy report and per-holding breakdown. Designed for transparency and reproducibility, suitable for research, reporting, and open-source collaboration.

## Features
- Scrapes ETF holdings and summary data from Schwab
- Fetches latest prices for all holdings and the ETF itself from Alpaca
- Merges and normalizes all data for analysis
- Prints a professional NAV summary and per-holding discrepancy table
- Outputs a comprehensive JSON file for further use

## Installation
1. Clone this repository:
   ```bash
   git clone <your-repo-url>
   cd <your-repo-directory>
   ```
2. Install dependencies (ideally in a virtual environment):
   ```bash
   pip install -r requirements.txt
   ```
   - Required: `requests`, `beautifulsoup4`, `lxml`
   - Optional: `python-dotenv` (for .env support)

## Environment Variables
Set your Alpaca API credentials as environment variables:
```bash
export ALPACA_API_KEY=your_key_here
export ALPACA_SECRET_KEY=your_secret_here
```
Or create a `.env` file in the project root:
```
ALPACA_API_KEY=your_key_here
ALPACA_SECRET_KEY=your_secret_here
```

## Usage
Run the script from the command line:
```bash
python main.py <ETF_SYMBOL> [NROWS] [OUTPUT_FILE]
```
- `<ETF_SYMBOL>`: The ticker symbol of the ETF (e.g., `SPY`)
- `[NROWS]`: (Optional) Number of holdings to fetch (default: 100)
- `[OUTPUT_FILE]`: (Optional) Path to save the merged JSON output

### Example
```bash
python main.py SPY 100 spy_output.json
```

## Example Output 
```
ETF NAV SUMMARY
==============
ETF reported last price:   $628.4900
Calculated NAV per share:  $634.1626
Difference:               $5.6726  (0.9026%)
Volume: 14,053
Volume label: Below Avg.
As of: close 07/18/2025

Symbol   Name                              Market Value      True Value     Discrepancy     % Diff
-----------------------------------------------------------------------------------------------
NVDA     NVIDIA Corp                    50,100,000,000.00 51,053,871,000.00  953,871,000.00       1.90
MSFT     Microsoft Corp                 45,300,000,000.00 45,886,650,000.00  586,650,000.00       1.30
...
```

