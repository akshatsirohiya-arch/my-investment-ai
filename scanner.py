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
        # Fetching 252 days (1 year) to ensure a clean 180-day (6 month) window
        data = yf.download(ticker, period="1y", interval="1d", progress=False, threads=False, auto_adjust=True)
        if data.empty or len(data) < 180: return None
        
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        curr_p = data['Close'].iloc[-1]
        if isinstance(curr_p, pd.Series): curr_p = curr_p.iloc[0]
        if curr_p < 5.0: return None # Keep the $5 floor to avoid penny stock noise

        # --- 180-DAY BREAKOUT ANALYSIS ---
        # Lookback at the 180 days prior to today
        lookback_180 = data.iloc[-181:-1]
        high_180 = lookback_180['High'].max()

        # CRITERIA: Current Price must be >= 180-day High
        if curr_p >= high_180:
            
            # STAIRCASE TREND CONFIRMATION (10-day windows)
            w1, w2 = data.iloc[-20:-10], data.iloc[-10:]
            hh = w2['High'].max() > w1['High'].max()
            hl = w2['Low'].min() > w1['Low'].min()

            if hh and hl:
                # MOMENTUM SLOPE
                p_start = data['Close'].iloc[-20]
                if isinstance(p_start, pd.Series): p_start = p_start.iloc[0]
                slope = (curr_p - p_start) / 20
                
                # RVOL (Output only - No filtering)
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
    except: pass
    return None

def scan():
    universe = get_total_market()
    print(f"🕵️ Scanning for 180-Day Breakouts among {len(universe)} stocks...")
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(process_ticker, universe))
    
    winners = [r for r in results if r is not None]
    pd.DataFrame(winners).to_csv("daily_watchlist.csv", index=False)
    print(f"✅ Found {len(winners)} 180-day breakout setups.")

if __name__ == "__main__":
    scan()
