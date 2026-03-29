import yfinance as yf
import pandas as pd
import requests
import time
from concurrent.futures import ThreadPoolExecutor

# Force standard caching
yf.set_tz_cache_location("cache")

def get_total_market():
    """Fetches tickers, with a hardcoded fallback if the URL fails."""
    url = "https://raw.githubusercontent.com/rreichel3/US-Stock-Symbols/main/all/all_tickers.txt"
    try:
        r = requests.get(url, timeout=10)
        tickers = [t.strip().upper() for t in r.text.splitlines() if 1 <= len(t.strip()) <= 5]
        if len(tickers) > 100:
            return tickers
    except:
        print("⚠️ URL Fetch failed. Using fallback major tickers.")
    
    # Fallback to top 100 liquid stocks if the master list fails
    return ["AAPL", "NVDA", "TSLA", "MSFT", "AMD", "GOOGL", "META", "AMZN", "NFLX", "INTC"]

def process_ticker(ticker, session):
    try:
        # 0.1s delay to avoid "burst" detection
        time.sleep(0.1)
        
        tk = yf.Ticker(ticker, session=session)
        # Fetching 1y data
        data = tk.history(period="1y", interval="1d", auto_adjust=True)
        
        if data.empty or len(data) < 130:
            return None
            
        # Standardize columns
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        curr_p = float(data['Close'].iloc[-1])
        if curr_p < 5.0: return None

        # --- 180-DAY (6 MO) ANALYSIS ---
        # Get the max high from the last 180 trading days (excluding today)
        hist_180 = data.iloc[-181:-1]
        high_180 = float(hist_180['High'].max())

        # BREAKOUT: Is today's price >= 99% of that high?
        if curr_p >= (high_180 * 0.99):
            
            # STAIRCASE: Simple Trend Check (5-day avg > prior 5-day avg)
            recent_5 = data['High'].iloc[-5:].mean()
            prior_5 = data['High'].iloc[-10:-5].mean()

            if recent_5 > prior_5:
                p_20d_ago = float(data['Close'].iloc[-20])
                slope = (curr_p - p_20d_ago) / 20
                
                vol_recent = data['Volume'].tail(10).mean()
                vol_avg = data['Volume'].iloc[-180:].mean()
                rvol = vol_recent / vol_avg if vol_avg > 0 else 0

                return {
                    "Ticker": ticker, "Price": round(curr_p, 2),
                    "High_180d": round(high_180, 2), "Slope": round(slope, 4),
                    "RVOL": round(rvol, 2)
                }
    except Exception as e:
        # Only print errors for major tickers to keep logs clean
        if ticker in ["AAPL", "NVDA"]: print(f"DEBUG {ticker}: {e}")
    return None

def scan():
    # Setup session with real-world headers
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    })

    universe = get_total_market()
    print(f"🕵️ Starting scan for {len(universe)} tickers...")
    
    # Low worker count (3-5) is essential to stay under the radar
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(lambda x: process_ticker(x, session), universe))
    
    winners = [r for r in results if r is not None]
    
    # Save results - even an empty list to prevent app crash
    df = pd.DataFrame(winners if winners else [])
    df.to_csv("daily_watchlist.csv", index=False)
    
    print(f"✅ Scan Finished. Found: {len(winners)}")

if __name__ == "__main__":
    scan()
