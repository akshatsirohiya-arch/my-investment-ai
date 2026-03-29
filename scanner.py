import yfinance as yf
import pandas as pd
import time
import requests

def scan():
    # 1. Get Tickers (Keep it to a manageable 500 for high quality)
    url = "https://raw.githubusercontent.com/rreichel3/US-Stock-Symbols/main/all/all_tickers.txt"
    all_tickers = requests.get(url).text.splitlines()
    universe = [t.strip() for t in all_tickers if t.strip()][:500] 
    
    winners = []
    
    # Use a persistent session to look 'human'
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})

    print(f"🚀 Starting Deep Scan of {len(universe)} tickers...")

    for ticker in universe:
        try:
            # FAST CHECK: Use history(period='1d') to get price/cap without calling .info
            # This is 10x faster and less likely to get you banned
            t = yf.Ticker(ticker, session=session)
            
            # Get 60 days of data in ONE shot
            df = t.history(period="60d")
            
            if df.empty or len(df) < 40:
                continue

            # PRE-FILTER: Only proceed if price > $5 (Prevents wasting time on junk)
            current_price = df['Close'].iloc[-1]
            if current_price < 5:
                continue

            # STAIRCASE LOGIC: Higher Highs & Higher Lows
            w1 = df.iloc[-20:-10] # Previous 10 days
            w2 = df.iloc[-10:]    # Last 10 days
            
            if (w2['High'].max() > w1['High'].max()) and (w2['Low'].min() > w1['Low'].min()):
                # CALCULATE MOMENTUM SLOPE
                slope = (df['Close'].iloc[-1] - df['Close'].iloc[-20]) / 20
                
                # VOLUME SURGE
                rvol = df['Volume'].tail(10).mean() / df['Volume'].iloc[-30:-10].mean()
                
                if rvol > 1.2:
                    # ONLY call .info for winners to save your rate limit!
                    info = t.info
                    winners.append({
                        "Ticker": ticker,
                        "Price": round(current_price, 2),
                        "Slope": round(slope, 4),
                        "RVOL": round(rvol, 2),
                        "Sector": info.get('sector', 'Unknown'),
                        "Cap_M": round(info.get('marketCap', 0) / 1_000_000, 0)
                    })
                    print(f"✅ Match: {ticker} (Slope: {slope:.2f})")

            # SMART DELAY: Randomize slightly to avoid bot detection
            time.sleep(0.5) 

        except Exception as e:
            # If we get a rate limit error, wait longer
            if "429" in str(e):
                print("🛑 Rate limited. Sleeping for 30 seconds...")
                time.sleep(30)
            continue

    # Final Save
    out_df = pd.DataFrame(winners)
    if not out_df.empty:
        out_df = out_df.sort_values(by="Slope", ascending=False)
    out_df.to_csv("daily_watchlist.csv", index=False)
    print(f"🏁 Done. Found {len(winners)} trending stocks.")

if __name__ == "__main__":
    scan()
