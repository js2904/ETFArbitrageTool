import re
import json
import base64
import requests
from bs4 import BeautifulSoup

SESSION_ID_RE = re.compile(r"WSDOM\.Page\.sessionID\s*=\s*WSOD_DATA\.sessionID\s*\|\|\s*'([^']+)'")
WSOD_ISSUE_RE = re.compile(r"var gSymbolWSODIssue = '(\d+)'")

def parse_num(val):
    val = val.strip().upper().replace(",", "").replace("$", "")
    try:
        if val.endswith("%"):
            return float(val[:-1]) / 100
        if val[-1] in {'B', 'M', 'K'}:
            return float(val[:-1]) * {'B': 1e9, 'M': 1e6, 'K': 1e3}[val[-1]]
        return float(val) if val else 0.0
    except:
        return 0.0  # fallback to 0 if bad format

def parse_holdings(raw):
    txt = raw.strip()
    if txt.startswith("this.apiReturn ="):
        txt = txt[len("this.apiReturn = "):]
    if txt.endswith(";"):
        txt = txt[:-1]

    data = json.loads(txt)
    rows = data["module"]["c"][0]["c"][1]["c"]
    out = []

    for row in rows:
        c = row["c"]
        try:
            weight = parse_num(c[2]["c"][0])
            if weight == 0:
                continue
            out.append({
                "symbol": c[0]["c"][0] if "c" in c[0] else "",
                "name": c[1]["c"][0] if "c" in c[1] else "",
                "weight_pct": weight,
                "shares": parse_num(c[3]["c"][0]),
                "market_value_usd": parse_num(c[4]["c"][0])
            })
        except:
            pass  # skip bad rows

    return out

def scrape_etf(symbol, nrows):
    url = f"https://www.schwab.wallst.com/schwab/Prospect/research/etfs/schwabETF/index.asp?type=holdings&symbol={symbol}"
    sess = requests.Session()
    resp = sess.get(url, headers={"User-Agent": "Mozilla/5.0", "Referer": url})
    resp.raise_for_status()

    sessionid_match = SESSION_ID_RE.search(resp.text)
    wsodid_match = WSOD_ISSUE_RE.search(resp.text)
    sessionid = sessionid_match.group(1) if sessionid_match else None
    wsodid = wsodid_match.group(1) if wsodid_match else None
    if not sessionid or not wsodid:
        print("[x] Could not extract sessionid or wsodid")
        return {"error": "sessionid/wsodid not found"}, []

    soup = BeautifulSoup(resp.text, "lxml")
    summary = {}

    def safe_select_one(element, selector):
        if element:
            found = element.select_one(selector)
            return found
        return None
    def safe_text(element):
        if element:
            return element.text.strip()
        return None

    try:
        tbl_row = soup.select_one("div.popupVersion.realtime table tr:nth-of-type(2)")
        if tbl_row:
            tbl = tbl_row.find_all("td")
            as_of_text = safe_text(soup.select_one("#firstGlanceFooter"))
            summary = {
                "last_price": safe_text(tbl[0]) if len(tbl) > 0 else None,
                "change": safe_text(tbl[2]) if len(tbl) > 2 else None,
                "bid": safe_text(safe_select_one(tbl[4], ".value")) if len(tbl) > 4 else None,
                "bid_size": safe_text(safe_select_one(tbl[4], ".sublabel")) if len(tbl) > 4 else None,
                "ask": safe_text(safe_select_one(tbl[6], ".value")) if len(tbl) > 6 else None,
                "ask_size": safe_text(safe_select_one(tbl[6], ".sublabel")) if len(tbl) > 6 else None,
                "volume": safe_text(safe_select_one(tbl[8], ".value")) if len(tbl) > 8 else None,
                "volume_label": safe_text(safe_select_one(tbl[8], ".sublabel")) if len(tbl) > 8 else None,
                "as_of": as_of_text.replace("As of", "").strip() if as_of_text else None
            }
        else:
            print("[x] summary parse fail (no table row)")
    except Exception as e:
        print(f"[x] summary parse fail: {e}")

    try:
        title_elem = soup.select_one("#content > div > h2")
        summary["title"] = title_elem.text.strip() if title_elem else None
    except Exception as e:
        print(f"[x] title parse fail: {e}")

    api = f"https://www.schwab.wallst.com/schwab/Prospect/research/resources/server/Module/SchwabETF.ModuleAPI.asp?{sessionid}"
    mod_args = {
        "ModuleID": "holdingsTableContainer",
        "symbol": symbol,
        "wsodissue": wsodid,
        "sortDir": "desc",
        "sortBy": "PctNetAssets",
        "page": "1",
        "numRows": str(nrows),
        "isThirdPartyETF": "true"
    }

    payload = {
        "module": "schwabETFHoldingsTable",
        "moduleArgs": mod_args
    }

    enc = base64.b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode()
    body = f"inputs=B64ENC{enc}&..contenttype..=text/javascript&..requester..=ContentBuffer"

    post_headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": url,
        "User-Agent": "Mozilla/5.0",
        "Accept": "*/*"
    }

    r2 = sess.post(api, headers=post_headers, data=body)
    r2.raise_for_status()
    holdings = parse_holdings(r2.text)

    return summary, holdings
