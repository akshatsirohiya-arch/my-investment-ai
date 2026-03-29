import yfinance as yf
import pandas as pd
import time
import requests
from concurrent.futures import ThreadPoolExecutor

def get_total_market():
    # Full US Market ~6,000+ tickers
    url = "https://raw.githubusercontent.com/rreichel3/US-Stock-Symbols/main/all/all_tickers.txt"
    r = requests.get(url)
    # Filter for standard tickers (avoiding long warrants/options symbols)
    return [t.strip().upper() for t in r.text.splitlines() if 1 <= len(t.strip()) <= 5]

def process_ticker(ticker):
    try:
        # Download 60 days of data
        data = yf.download(ticker, period="60d", interval="1d", progress=False, threads=False)
        
        if data.empty or len(data) < 30:
            return None

        # Calculate current price and basic filters
        curr_p = float(data['Close'].iloc[-1])
        if curr_p < 5.0: return None # Price Floor

        # --- THE STAIRCASE PATTERN LOGIC ---
        # Window 1: 20 days ago to 10 days ago
        # Window 2: Last 10 days
        w1 = data.iloc[-20:-10]
        w2 = data.iloc[-10:]
        
        # Pattern: Higher High (HH) and Higher Low (HL)
        if (w2['High'].max() > w1['High'].max()) and (w2['Low'].min() > w1['Low'].min()):
            
            # Momentum Slope: Rate of change over last 20 days
            slope = (curr_p - float(data['Close'].iloc[-20])) / 20
            
            # Relative Volume (RVOL)
            vol_recent = data['Volume'].tail(10).mean()
            vol_avg = data['Volume'].iloc[-30:-10].mean()
            rvol = vol_recent / vol_avg if vol_avg > 0 else 0

            if rvol > 1.2:
                return {
                    "Ticker": ticker,
                    "Price": round(curr_p, 2),
                    "Slope": round(slope, 4),
                    "RVOL": round(rvol, 2)
                }
    except:
        pass
    return None

def scan():
    universe = get_total_market()
    print(f"🕵️ Scanning TOTAL MARKET ({len(universe)} tickers)...")
    
    # max_workers=10 is the "sweet spot" for speed vs stability
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(process_ticker, universe))
    
    winners = [r for r in results if r is not None]
    
    df = pd.DataFrame(winners)
    if not df.empty:
        df = df.sort_values(by="Slope", ascending=False)
        
    df.to_csv("daily_watchlist.csv", index=False)
    print(f"✅ Found {len(winners)} stocks in a Staircase Trend.")

if __name__ == "__main__":
    scan()
