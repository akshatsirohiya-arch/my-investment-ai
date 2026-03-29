import yfinance as yf
import pandas as pd
import time
import requests
from concurrent.futures import ThreadPoolExecutor

def get_total_market():
    url = "https://raw.githubusercontent.com/rreichel3/US-Stock-Symbols/main/all/all_tickers.txt"
    try:
        r = requests.get(url, timeout=15)
        return [t.strip().upper() for t in r.text.splitlines() if 1 <= len(t.strip()) <= 5]
    except:
        return []

def process_ticker(ticker):
    try:
        # auto_adjust=True handles splits/dividends automatically
        data = yf.download(ticker, period="60d", interval="1d", progress=False, threads=False, auto_adjust=True)
        
        if data.empty or len(data) < 30:
            return None

        # Fix for Multi-Index columns (handles tuple headers)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        # FIX: Use .item() or .iloc[0] to avoid the FutureWarning
        # This converts a single-element Series to a scalar safely
        curr_p = data['Close'].iloc[-1]
        if isinstance(curr_p, pd.Series): curr_p = curr_p.iloc[0]
        
        if curr_p < 5.0: return None

        # Pattern Logic: 10-day windows
        w1 = data.iloc[-20:-10]
        w2 = data.iloc[-10:]
        
        # Extract max/min as scalars
        w1_high = w1['High'].max()
        w2_high = w2['High'].max()
        w1_low = w1['Low'].min()
        w2_low = w2['Low'].min()
        
        # Higher High and Higher Low detection
        if (w2_high > w1_high) and (w2_low > w1_low):
            price_20d_ago = data['Close'].iloc[-20]
            if isinstance(price_20d_ago, pd.Series): price_20d_ago = price_20d_ago.iloc[0]
            
            slope = (curr_p - price_20d_ago) / 20
            
            vol_recent = data['Volume'].tail(10).mean()
            vol_avg = data['Volume'].iloc[-30:-10].mean()
            
            # Ensure we are comparing scalars
            if isinstance(vol_recent, pd.Series): vol_recent = vol_recent.iloc[0]
            if isinstance(vol_avg, pd.Series): vol_avg = vol_avg.iloc[0]
            
            rvol = vol_recent / vol_avg if vol_avg > 0 else 0

            if rvol > 1.0:
                return {
                    "Ticker": ticker,
                    "Price": round(float(curr_p), 2),
                    "Slope": round(float(slope), 4),
                    "RVOL": round(float(rvol), 2)
                }
    except Exception:
        pass
    return None

def scan():
    universe = get_total_market()
    print(f"🕵️ Scanning {len(universe)} tickers...")
    
    # Process in parallel
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(process_ticker, universe))
    
    winners = [r for r in results if r is not None]
    
    # Always save something to prevent EmptyDataError in App
    if not winners:
        winners = [{"Ticker": "MARKET_FLAT", "Price": 0, "Slope": 0, "RVOL": 0}]
    
    df = pd.DataFrame(winners)
    df = df.sort_values(by="Slope", ascending=False)
    df.to_csv("daily_watchlist.csv", index=False)
    print(f"✅ Saved {len(winners)} stocks.")

if __name__ == "__main__":
    scan()
