import yfinance as yf
import pandas as pd
import time
import requests

def get_universe():
    # High-reliability ticker list for 2026
    url = "https://raw.githubusercontent.com/rreichel3/US-Stock-Symbols/main/all/all_tickers.txt"
    try:
        r = requests.get(url, timeout=10)
        return [t.strip().upper() for t in r.text.splitlines() if t.strip()]
    except:
        return ["AAPL", "TSLA", "NVDA", "PLTR", "SOFI"]

def scan():
    universe = get_universe()
    winners = []
    # 2026 Tip: Using a session header reduces 429 'Too Many Requests' errors
    yf_session = requests.Session()
    yf_session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})

    print(f"🔍 Scanning {len(universe)} tickers...")
    
    for ticker in universe:
        try:
            # Stage 1: Fast Market Cap Filter
            stock = yf.Ticker(ticker, session=yf_session)
            m_cap = stock.info.get('marketCap', 0)
            
            if m_cap < 300_000_000: # Skip stocks under $300M
                continue
                
            # Stage 2: Technical Analysis
            df = stock.history(period="1y")
            if df.empty or len(df) < 130: 
                continue
                
            close = df['Close']
            vol = df['Volume']
            
            # 10-Day Max RVOL calculation
            rvol_max = max([(vol.iloc[-i] / vol.iloc[-(i+21):-i].mean()) for i in range(1, 11)])
            
            if rvol_max >= 2.0:
                winners.append({
                    "Ticker": ticker,
                    "Price": round(float(close.iloc[-1]), 2),
                    "Max_RVOL": round(rvol_max, 2),
                    "Cap_Millions": round(m_cap / 1_000_000, 0)
                })
                print(f"⭐ Match: {ticker} (RVOL: {rvol_max:.2f})")
            
            time.sleep(0.4) # Ethical delay to avoid IP ban
            
        except Exception:
            continue

    # Final Output
    pd.DataFrame(winners).to_csv("daily_watchlist.csv", index=False)
    print("✅ Scan Complete. File Saved.")

if __name__ == "__main__":
    scan()
