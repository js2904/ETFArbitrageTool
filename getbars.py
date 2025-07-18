import requests
from urllib.parse import quote
import json
import time
import os
from dotenv import load_dotenv

load_dotenv()

def fetch_bars_for_symbols(symbols, etf_symbol=None):
    start_time = time.time()
    all_symbols = list(symbols)
    if etf_symbol and etf_symbol not in all_symbols:
        all_symbols = [etf_symbol] + all_symbols
    symbols_str = ",".join(all_symbols)
    symbols_encoded = quote(symbols_str, safe=".")


    url = f"https://data.alpaca.markets/v2/stocks/bars/latest?symbols={symbols_encoded}"

    headers = {
        "accept": "application/json",
        "APCA-API-KEY-ID": os.environ.get("ALPACA_API_KEY", ""),
        "APCA-API-SECRET-KEY": os.environ.get("ALPACA_SECRET_KEY", "")
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"[getbars] ERROR: {e}")
        return None

    bars = data.get("bars", {})
    etf_bar = None
    if etf_symbol and etf_symbol in bars:
        etf_bar = {etf_symbol: bars.pop(etf_symbol)}
    present = [s for s in symbols if s in bars]
    missing = [s for s in symbols if s not in bars]
    elapsed = time.time() - start_time
    #print(f"[getbars] Completed in {elapsed:.2f} seconds.{etf_bar}")
    return {"etf_bar": etf_bar, "bars": bars}
