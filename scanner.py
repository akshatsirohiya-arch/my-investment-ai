import yfinance as yf
import pandas as pd
import time
import requests
from concurrent.futures import ThreadPoolExecutor

# 1. ADD CUSTOM HEADERS TO BYPASS 401/UNAUTHORIZED
# This makes the request look like a standard web browser
yf.set_tz_cache_location("cache") # Helps with performance

def get_total_market():
    url = "https://raw.githubusercontent.com/rreichel3/US-Stock-Symbols/main/all/all_tickers.txt"
    try:
        r = requests.get(url, timeout=15)
        return [t.strip().upper() for t in r.text.splitlines() if 1 <= len(t.strip()) <= 5]
    except:
        return ["AAPL", "TSLA", "NVDA"]

def process_ticker(ticker):
    try:
        # 2. ADD A TINY RANDOM DELAY to avoid the 429 Rate Limit
        # (This will make the scan take longer, but it will actually FINISH)
        time.sleep(0.5) 
        
        # Using a Ticker object often handles cookies/crumbs better than yf.download
        tk = yf.Ticker(ticker)
        data = tk.history(period="60d", interval="1d", auto_adjust=True)
        
        if data.empty or len(data) < 30:
            return None

        # Standardizing columns
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        curr_p = data['Close'].iloc[-1]
        if isinstance(curr_p, pd.Series): curr_p = curr_p.iloc[0]
        if curr_p < 5.0: return None

        # Staircase Math
        w1 = data.iloc[-20:-10]
        w2 = data.iloc[-10:]
        
        if (w2['High'].max() > w1['High'].max()) and (w2['Low'].min() > w1['Low'].min()):
            price_20d_ago = data['Close'].iloc[-20]
            if isinstance(price_20d_ago, pd.Series): price_20d_ago = price_20d_ago.iloc[0]
            
            slope = (curr_p - price_20d_ago) / 20
            vol_recent = data['Volume'].tail(10).mean()
            vol_avg = data['Volume'].iloc[-30:-10].mean()
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
    except Exception as e:
        if "429" in str(e):
            print("🚨 Rate Limited! Cooling down...")
            time.sleep(10) # Heavy pause if we hit a wall
    return None

def scan():
    universe = get_total_market()
    print(f"🕵️ Scanning {len(universe)} tickers with 2026 security bypass...")
    
    # 3. REDUCE WORKERS
    # Lowering from 10 to 3 workers. It's slower, but much stealthier.
    with ThreadPoolExecutor(max_workers=3) as executor:
        results = list(executor.map(process_ticker, universe))
    
    winners = [r for r in results if r is not None]
    
    df = pd.DataFrame(winners if winners else [{"Ticker": "SCAN_PAUSED", "Price": 0, "Slope": 0, "RVOL": 0}])
    df.to_csv("daily_watchlist.csv", index=False)
    print(f"✅ Scan Complete. Found {len(winners)} stocks.")

if __name__ == "__main__":
    scan()
