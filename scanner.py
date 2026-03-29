import yfinance as yf
import pandas as pd
import requests
import time
from concurrent.futures import ThreadPoolExecutor

# Crucial: This allows yfinance to use its own internal stealth session
yf.set_tz_cache_location("cache")

def get_total_market():
    url = "https://raw.githubusercontent.com/rreichel3/US-Stock-Symbols/main/all/all_tickers.txt"
    try:
        r = requests.get(url, timeout=10)
        tickers = [t.strip().upper() for t in r.text.splitlines() if 1 <= len(t.strip()) <= 5]
        if len(tickers) > 100:
            return tickers
    except:
        return ["AAPL", "NVDA", "TSLA", "MSFT", "AMD", "GOOGL", "META"]

def process_ticker(ticker):
    try:
        # We stop passing a 'session' and let yfinance handle the curl_cffi handshake
        data = yf.download(
            ticker, 
            period="1y", 
            interval="1d", 
            progress=False, 
            threads=False, 
            auto_adjust=True
        )
        
        if data.empty or len(data) < 130:
            return None
            
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        curr_p = float(data['Close'].iloc[-1])
        if curr_p < 5.0: return None

        # --- 180-DAY (6 MO) ANALYSIS ---
        # Get max high from last 180 trading days (excluding today)
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
                    "Ticker": ticker, 
                    "Price": round(curr_p, 2),
                    "High_180d": round(high_180, 2), 
                    "Slope": round(slope, 4),
                    "RVOL": round(rvol, 2)
                }
    except Exception:
        pass 
    return None

def scan():
    universe = get_total_market()
    print(f"🕵️ Starting scan for {len(universe)} tickers...")
    
    # We use a smaller worker count to avoid getting IP-banned 
    # since we are now letting the library handle individual handshakes.
    with ThreadPoolExecutor(max_workers=3) as executor:
        results = list(executor.map(process_ticker, universe))
    
    winners = [r for r in results if r is not None]
    
    # Save results
    df = pd.DataFrame(winners if winners else [])
    df.to_csv("daily_watchlist.csv", index=False)
    
    print(f"✅ Scan Finished. Found: {len(winners)}")

if __name__ == "__main__":
    scan()
