import yfinance as yf
import pandas as pd
import time
import requests

def get_full_universe():
    # Fetches ~6,000+ US Tickers
    url = "https://raw.githubusercontent.com/rreichel3/US-Stock-Symbols/main/all/all_tickers.txt"
    try:
        r = requests.get(url, timeout=10)
        return [t.strip().upper() for t in r.text.splitlines() if t.strip()]
    except:
        return ["AAPL", "TSLA", "NVDA", "AMD", "PLTR"] # Fallback

def scan():
    universe = get_full_universe()
    winners = []
    
    # 1. Batching Logic: Process 50 stocks at a time
    batch_size = 50 
    print(f"🌪️ Starting FULL MARKET scan of {len(universe)} tickers...")

    for i in range(0, len(universe), batch_size):
        batch = universe[i:i + batch_size]
        print(f"Scanning batch {i//batch_size + 1}: {batch[0]} to {batch[-1]}")
        
        try:
            # Vectorized Download: Gets 60 days of data for 50 stocks at once!
            data = yf.download(batch, period="60d", group_by='ticker', threads=True, progress=False)
            
            for ticker in batch:
                try:
                    df = data[ticker]
                    if df.empty or len(df) < 40: continue

                    # Basic Price/Vol Filters
                    curr_p = df['Close'].iloc[-1]
                    if curr_p < 5.0: continue

                    # STAIRCASE LOGIC (Higher Highs & Higher Lows)
                    w1 = df.iloc[-20:-10] # Prev 10 days
                    w2 = df.iloc[-10:]    # Last 10 days
                    
                    hh = w2['High'].max() > w1['High'].max()
                    hl = w2['Low'].min() > w1['Low'].min()

                    if hh and hl:
                        # MOMENTUM SLOPE (The Gain Potential)
                        slope = (df['Close'].iloc[-1] - df['Close'].iloc[-20]) / 20
                        
                        # VOLUME SURGE
                        rvol = df['Volume'].tail(10).mean() / df['Volume'].iloc[-30:-10].mean()
                        
                        if rvol > 1.2:
                            winners.append({
                                "Ticker": ticker,
                                "Price": round(curr_p, 2),
                                "Slope": round(slope, 4),
                                "RVOL": round(rvol, 2)
                            })
                except:
                    continue
            
            # Tiny rest so we don't get blocked
            time.sleep(2) 

        except Exception as e:
            print(f"Batch failed: {e}")
            time.sleep(10)
            continue

    # Final Save & Sort
    out_df = pd.DataFrame(winners)
    if not out_df.empty:
        # Sort by the "Gain Potential" Slope
        out_df = out_df.sort_values(by="Slope", ascending=False)
        
    out_df.to_csv("daily_watchlist.csv", index=False)
    print(f"🏁 MISSION COMPLETE. Found {len(winners)} Staircase Patterns.")

if __name__ == "__main__":
    scan()
