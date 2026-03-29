import yfinance as yf
import pandas as pd
import requests
import time
from concurrent.futures import ThreadPoolExecutor

# Force caching to prevent redundant 'crumb' requests
yf.set_tz_cache_location("cache")

def get_total_market():
    """Fetches the current US stock universe."""
    url = "https://raw.githubusercontent.com/rreichel3/US-Stock-Symbols/main/all/all_tickers.txt"
    try:
        r = requests.get(url, timeout=15)
        return [t.strip().upper() for t in r.text.splitlines() if 1 <= len(t.strip()) <= 5]
    except:
        return ["AAPL", "NVDA", "TSLA", "MSFT", "AMD"]

def process_ticker(ticker, session):
    """Analyzes a single stock with 2026 browser impersonation."""
    try:
        # 1. AUTHENTICATION: Use a session with a real browser User-Agent
        tk = yf.Ticker(ticker, session=session)
        
        # 2. DATA FETCH: 1y gives us enough room for 180d (6mo) analysis
        data = tk.history(period="1y", interval="1d", auto_adjust=True)
        
        if data.empty or len(data) < 185:
            return None
            
        # Standardize columns (remove MultiIndex if present)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        curr_p = data['Close'].iloc[-1]
        if isinstance(curr_p, pd.Series): curr_p = curr_p.iloc[0]
        
        # $5 Minimum Price Filter (Standard institutional floor)
        if curr_p < 5.0: return None

        # --- 180-DAY (6 MONTH) BREAKOUT ANALYSIS ---
        # Trading days in 6 months is ~126, but we check 180 for a "Major Range"
        lookback_180 = data.iloc[-181:-1]
        high_180 = lookback_180['High'].max()

        # CRITERIA: Is price at or above the 180-day ceiling?
        if curr_p >= (high_180 * 0.995): # Within 0.5% of or above
            
            # --- STAIRCASE CONFIRMATION ---
            # Last 10 days vs the 10 days before that
            w1 = data.iloc[-20:-10]
            w2 = data.iloc[-10:]
            
            hh = w2['High'].max() > w1['High'].max()
            hl = w2['Low'].min() > w1['Low'].min()

            if hh and hl:
                # MOMENTUM SCORE (Slope over 20 days)
                p_20d_ago = data['Close'].iloc[-20]
                if isinstance(p_20d_ago, pd.Series): p_20d_ago = p_20d_ago.iloc[0]
                slope = (curr_p - p_20d_ago) / 20
                
                # RVOL (Relative Volume vs 180-day average)
                vol_recent = data['Volume'].tail(10).mean()
                vol_avg = data['Volume'].iloc[-180:].mean()
                rvol = vol_recent / vol_avg if vol_avg > 0 else 0

                return {
                    "Ticker": ticker,
                    "Price": round(float(curr_p), 2),
                    "High_180d": round(float(high_180), 2),
                    "Slope": round(float(slope), 4),
                    "RVOL": round(float(rvol), 2)
                }
    except Exception:
        pass # Silently skip errors to keep the console clean
    return None

def scan():
    # Setup the 'Stealth Session'
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    })

    universe = get_total_market()
    print(f"🕵️ Scanning {len(universe)} stocks for 180-day breakouts...")
    
    # We use 5 workers. 10+ usually triggers Yahoo's "Robot" detection.
    with ThreadPoolExecutor(max_workers=5) as executor:
        # Pass the session to every worker
        results = list(executor.map(lambda x: process_ticker(x, session), universe))
    
    winners = [r for r in results if r is not None]
    
    # Save results
    if winners:
        df = pd.DataFrame(winners)
        df.to_csv("daily_watchlist.csv", index=False)
        print(f"✅ Success! Found {len(winners)} stocks.")
    else:
        print("⚠️ Scan complete, but no stocks matched the criteria.")
        # Create empty file to avoid App crashes
        pd.DataFrame(columns=["Ticker","Price","High_180d","Slope","RVOL"]).to_csv("daily_watchlist.csv", index=False)

if __name__ == "__main__":
    scan()
