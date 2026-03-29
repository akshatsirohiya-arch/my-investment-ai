import yfinance as yf
import pandas as pd
import time
import requests

def get_universe():
    url = "https://raw.githubusercontent.com/rreichel3/US-Stock-Symbols/main/all/all_tickers.txt"
    try:
        r = requests.get(url)
        return [t.strip().upper() for t in r.text.splitlines() if t.strip()]
    except:
        return ["AAPL", "TSLA", "NVDA", "PLTR", "AMD"]

def scan():
    universe = get_universe()
    winners = []
    min_cap = 300 * 1_000_000 # $300M Floor
    
    print(f"🚀 Starting scan of {len(universe)} tickers...")

    for ticker in universe:
        try:
            stock = yf.Ticker(ticker)
            # FAST CHECK: Market Cap (Saves time/bandwidth)
            m_cap = stock.info.get('marketCap', 0)
            if m_cap < min_cap:
                continue
            
            # DEEP CHECK: Technicals
            df = stock.history(period="1y")
            if df.empty or len(df) < 130: continue
            
            # RVOL & Staircase Logic
            close, vol = df['Close'], df['Volume']
            rvol_max = max([(vol.iloc[-i] / vol.iloc[-(i+21):-i].mean()) for i in range(1, 11)])
            
            if rvol_max >= 2.0: # Only keep high-volume movers
                winners.append({
                    "Ticker": ticker,
                    "Price": round(float(close.iloc[-1]), 2),
                    "Max_RVOL": round(rvol_max, 2),
                    "Market_Cap_M": round(m_cap / 1_000_000, 0)
                })
                print(f"✅ Match Found: {ticker}")
            
            # Small delay to keep Yahoo happy
            time.sleep(0.5) 
            
        except Exception:
            continue

    # Save to CSV for the App to read
    pd.DataFrame(winners).to_csv("daily_watchlist.csv", index=False)
    print(f"📂 Scan complete. {len(winners)} stocks saved.")

if __name__ == "__main__":
    scan()
