import yfinance as yf
import pandas as pd
import time
import requests

def calculate_slope(series):
    if len(series) < 20: return 0
    # Linear trend: (Current - Start) / Time
    return (series.iloc[-1] - series.iloc[0]) / 20

def scan():
    url = "https://raw.githubusercontent.com/rreichel3/US-Stock-Symbols/main/all/all_tickers.txt"
    universe = requests.get(url).text.splitlines()
    winners = []
    
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0'})

    print(f"🚀 Scanning for Staircase Patterns in {len(universe)} stocks...")

    for ticker in universe[:1500]: # Start with a smaller batch to test speed
        try:
            t = yf.Ticker(ticker.strip(), session=session)
            
            # 1. Quick Fundamentals Filter
            info = t.info
            m_cap = info.get('marketCap', 0)
            if m_cap < 300_000_000: continue
            
            # 2. Get 60 days of history for pattern recognition
            df = t.history(period="60d")
            if len(df) < 40: continue
            
            # 3. Staircase Logic: Higher High (HH) & Higher Low (HL)
            # Compare current 10-day window to previous 10-day window
            w1 = df.iloc[-20:-10]
            w2 = df.iloc[-10:]
            
            is_staircase = (w2['High'].max() > w1['High'].max()) and (w2['Low'].min() > w1['Low'].min())
            
            if is_staircase:
                close = df['Close']
                vol = df['Volume']
                rvol = vol.tail(10).mean() / vol.iloc[-30:-10].mean()
                
                if rvol > 1.5:
                    slope = calculate_slope(close.tail(20))
                    winners.append({
                        "Ticker": ticker,
                        "Price": round(close.iloc[-1], 2),
                        "Slope": round(slope, 4),
                        "RVOL": round(rvol, 2),
                        "Sector": info.get('sector', 'N/A'),
                        "Industry": info.get('industry', 'N/A'),
                        "Cap_M": round(m_cap / 1_000_000, 0)
                    })
                    print(f"🎯 Staircase Found: {ticker} (Slope: {slope})")
            
            time.sleep(0.2)
        except Exception:
            continue

    # Save and sort by Slope (Momentum)
    out = pd.DataFrame(winners)
    if not out.empty:
        out = out.sort_values(by="Slope", ascending=False)
    out.to_csv("daily_watchlist.csv", index=False)

if __name__ == "__main__":
    scan()
