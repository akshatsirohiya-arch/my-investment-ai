import yfinance as yf
import pandas as pd
import requests
from concurrent.futures import ThreadPoolExecutor

def get_total_market():
    url = "https://raw.githubusercontent.com/rreichel3/US-Stock-Symbols/main/all/all_tickers.txt"
    r = requests.get(url, timeout=15)
    return [t.strip().upper() for t in r.text.splitlines() if 1 <= len(t.strip()) <= 5]

def process_ticker(ticker):
    try:
        # High speed download
        data = yf.download(ticker, period="60d", interval="1d", progress=False, threads=False, auto_adjust=True)
        if data.empty or len(data) < 30: return None
        
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        curr_p = data['Close'].iloc[-1]
        if isinstance(curr_p, pd.Series): curr_p = curr_p.iloc[0]
        if curr_p < 5.0: return None

        # Staircase Math
        w1, w2 = data.iloc[-20:-10], data.iloc[-10:]
        if (w2['High'].max() > w1['High'].max()) and (w2['Low'].min() > w1['Low'].min()):
            p_start = data['Close'].iloc[-20]
            if isinstance(p_start, pd.Series): p_start = p_start.iloc[0]
            
            slope = (curr_p - p_start) / 20
            vol_recent = data['Volume'].tail(10).mean()
            vol_avg = data['Volume'].iloc[-30:-10].mean()
            rvol = vol_recent / vol_avg if vol_avg > 0 else 0

            if rvol > 1.0:
                return {"Ticker": ticker, "Price": round(float(curr_p), 2), "Slope": round(float(slope), 4), "RVOL": round(float(rvol), 2)}
    except: pass
    return None

def scan():
    universe = get_total_market()
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(process_ticker, universe))
    
    winners = [r for r in results if r is not None]
    pd.DataFrame(winners).to_csv("daily_watchlist.csv", index=False)
    print(f"✅ Saved {len(winners)} stocks.")

if __name__ == "__main__":
    scan()
