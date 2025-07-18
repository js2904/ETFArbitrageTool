"""
ETF NAV and Holdings Analyzer
----------------------------
Given an ETF symbol, this script scrapes ETF holdings and summary data, fetches latest prices from Alpaca, merges all data, and prints a NAV discrepancy report with per-holding details. The output JSON includes both ETF site and Alpaca data for transparency.

Usage:
    python etf.py <ETF_SYMBOL> [NROWS] [OUTPUT_FILE]

- <ETF_SYMBOL>: The ticker symbol of the ETF (e.g., SPY)
- [NROWS]:      (Optional) Number of holdings to fetch (default: 100)
- [OUTPUT_FILE]: (Optional) Path to save the merged JSON output

Environment:
    Set ALPACA_API_KEY and ALPACA_SECRET_KEY in your environment (or use a .env file with python-dotenv).
"""
import sys
import os
import json
import re
import time
from etf_scraper import scrape_etf
from getbars import fetch_bars_for_symbols
from merge import merge_etf_and_alpaca
from collections import OrderedDict
# If you want to use environment variables from a .env file, install python-dotenv and uncomment:
# from dotenv import load_dotenv
# load_dotenv()


def normalize_symbol(symbol):
    """Normalize holding symbols for Alpaca compatibility."""
    if not symbol or symbol.strip() == '' or symbol == '--':
        return None
    symbol = symbol.replace('/', '.')
    symbol = re.sub(r'[^A-Za-z0-9\.]+', '', symbol)
    return symbol if symbol else None


def calculate_nav_and_report(merged):
    """Print NAV summary, volume info, and per-holding discrepancy table."""
    symbols = merged.get('symbols', {})
    summary = merged.get('summary', {})
    results = []
    total_holdings_value = 0.0
    total_reported_market_value = 0.0
    for symbol, info in symbols.items():
        name = info.get('name', '')
        shares = info.get('shares', 0)
        close = info.get('close', 0)
        market_value = info.get('market_value_usd', 0)
        try:
            shares = float(shares)
            close = float(close)
            market_value = float(market_value)
        except Exception:
            continue
        true_value = shares * close
        total_holdings_value += true_value
        total_reported_market_value += market_value
        discrepancy = true_value - market_value
        discrepancy_pct = (discrepancy / market_value * 100) if market_value else 0
        results.append({
            'symbol': symbol,
            'name': name,
            'market_value_usd': market_value,
            'true_value': true_value,
            'discrepancy': discrepancy,
            'discrepancy_pct': discrepancy_pct
        })
    results.sort(key=lambda x: abs(x['discrepancy']), reverse=True)
    last_price_str = summary.get('last_price', '')
    # If last_price is a dict (from Alpaca), use the 'c' (close) value
    if isinstance(last_price_str, dict) and 'c' in last_price_str:
        last_price_val = last_price_str['c']
    else:
        last_price_val = str(last_price_str).replace('$', '').replace(',', '')
        try:
            last_price_val = float(last_price_val)
        except Exception:
            last_price_val = None
    last_price = last_price_val
    etf_shares_outstanding = (total_reported_market_value / last_price) if last_price else None
    actual_nav_per_share = (total_holdings_value / etf_shares_outstanding) if etf_shares_outstanding else None
    print("ETF NAV SUMMARY")
    print("==============")
    if last_price is not None and actual_nav_per_share is not None:
        nav_diff = actual_nav_per_share - last_price
        nav_diff_pct = (nav_diff / last_price * 100) if last_price else 0
        print(f"ETF reported last price:   ${last_price:,.4f}")
        print(f"Calculated NAV per share:  ${actual_nav_per_share:,.4f}")
        print(f"Difference:               ${nav_diff:,.4f}  ({nav_diff_pct:.4f}%)")
    else:
        print("Insufficient data to calculate NAV discrepancy.")
    # Print volume, volume_label, and as_of after NAV summary
    volume = summary.get('volume', 'N/A')
    volume_label = summary.get('volume_label', 'N/A')
    as_of = summary.get('as_of', 'N/A')
    print(f"Volume: {volume}")
    print(f"Volume label: {volume_label}")
    print(f"As of: {as_of}")
    print()
    print(f"{'Symbol':<8} {'Name':<30} {'Market Value':>15} {'True Value':>15} {'Discrepancy':>15} {'% Diff':>10}")
    print('-' * 95)
    for r in results:
        print(f"{r['symbol']:<8} {r['name'][:28]:<30} {r['market_value_usd']:15,.2f} {r['true_value']:15,.2f} {r['discrepancy']:15,.2f} {r['discrepancy_pct']:10.2f}")
    return merged


def main(symbol, nrows=100, save_file=None):
    """Main pipeline: scrape, normalize, fetch prices, merge, report, and save."""
    # Scrape ETF summary and holdings
    summary, holdings = scrape_etf(symbol, nrows)
    # Ensure summary always includes volume, volume_label, and as_of from the ETF scraper
    summary_fields = ['volume', 'volume_label', 'as_of']
    scraped_summary, _ = scrape_etf(symbol, nrows)
    for field in summary_fields:
        if field in scraped_summary:
            summary[field] = scraped_summary[field]
    if not holdings:
        print("No holdings found.")
        return
    # Normalize and deduplicate symbols
    for h in holdings:
        h["alpaca_symbol"] = normalize_symbol(h["symbol"])
    valid_holdings = [h for h in holdings if h["alpaca_symbol"]]
    symbols = [h["alpaca_symbol"] for h in valid_holdings]
    seen = set()
    unique_symbols = []
    for s in symbols:
        if s and s not in seen:
            unique_symbols.append(s)
            seen.add(s)
    # Fetch latest prices from Alpaca
    bars_data = fetch_bars_for_symbols(unique_symbols, etf_symbol=symbol) or {}
    etf_bar = bars_data.get("etf_bar") if isinstance(bars_data, dict) else None
    # If Alpaca ETF bar is available, store the full bar dict in summary['last_price']
    if etf_bar and symbol in etf_bar:
        summary["last_price"] = etf_bar[symbol]  # This is now a dict, not a string
    # Do NOT overwrite summary['volume'] (keep ETF scraper's value)
    bars = bars_data.get("bars", {}) if isinstance(bars_data, dict) else {}
    # Merge all data
    merged = merge_etf_and_alpaca(summary, valid_holdings, {"bars": bars})
    # Ensure merged['summary'] always includes volume, volume_label, and as_of
    for field in ['volume', 'volume_label', 'as_of']:
        if field in summary:
            merged['summary'][field] = summary[field]
    # Print NAV summary and per-holding table
    merged = calculate_nav_and_report(merged)
    # Optionally save output
    if save_file:
        with open(save_file, "w", encoding="utf-8") as f:
            json.dump(merged, f, indent=2, ensure_ascii=False)
    return merged


def print_usage():
    print("Usage: python etf.py <ETF_SYMBOL> [NROWS] [OUTPUT_FILE]")
    print("  <ETF_SYMBOL>: The ticker symbol of the ETF (e.g., SPY)")
    print("  [NROWS]:      (Optional) Number of holdings to fetch (default: 100)")
    print("  [OUTPUT_FILE]: (Optional) Path to save the merged JSON output")

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in {"-h", "--help"}:
        print_usage()
        sys.exit(1)
    symbol = sys.argv[1].strip().upper()
    if not symbol.isalnum() and "." not in symbol:
        print(f"Invalid ETF symbol: {symbol}")
        print_usage()
        sys.exit(1)
    try:
        nrows = int(sys.argv[2]) if len(sys.argv) > 2 else 100
        if nrows <= 0:
            raise ValueError
    except (ValueError, IndexError):
        print("NROWS must be a positive integer.")
        print_usage()
        sys.exit(1)
    save_file = sys.argv[3] if len(sys.argv) > 3 else None
    main(symbol, nrows, save_file) 