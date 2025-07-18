import json
import os
from collections import OrderedDict

def load_json(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)

def clean_name(name_field):
    # Handles HTML-like dict or string
    if isinstance(name_field, dict) and 'c' in name_field and isinstance(name_field['c'], list):
        return ' '.join(str(x) for x in name_field['c'])
    return str(name_field)

def expand_bar_keys(bar):
    # Map short keys to full descriptive names
    key_map = {
        'c': 'close',
        'h': 'high',
        'l': 'low',
        'n': 'num_trades',
        'o': 'open',
        't': 'timestamp',
        'v': 'volume',
        'vw': 'vwap',
    }
    return {key_map.get(k, k): v for k, v in bar.items()}

def merge_etf_and_alpaca(summary, holdings, alpaca_response):
    alpaca_bars = alpaca_response.get('bars', {})
    symbols_dict = OrderedDict()
    for h in holdings:
        symbol = h.get('alpaca_symbol') or h.get('symbol')
        bar = alpaca_bars.get(symbol, {})
        bar_expanded = expand_bar_keys(bar)
        # Clean name
        name = clean_name(h.get('name', ''))
        # Organize: symbol, name, ETF data, Alpaca bar data
        etf_fields = {k: v for k, v in h.items() if k not in ['symbol', 'alpaca_symbol', 'name']}
        entry = OrderedDict()
        entry['symbol'] = symbol
        entry['name'] = name
        entry.update(etf_fields)
        entry.update(bar_expanded)
        symbols_dict[symbol] = entry
    output = {
        'summary': summary,
        'symbols': symbols_dict
    }
    return output

def main():
    summary = load_json('etf_summary.json')
    holdings = load_json('etf_holdings.json')
    alpaca_response = load_json('alpaca_responses.json')
    merged = merge_etf_and_alpaca(summary, holdings, alpaca_response)
    with open('merged_etf_data.json', 'w', encoding='utf-8') as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

if __name__ == '__main__':
    main() 