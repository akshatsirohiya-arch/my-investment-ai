import yfinance as yf
import pandas as pd
import time
import requests

def get_universe():
    url = "https://raw.githubusercontent.com/rreichel3/US-Stock-Symbols/main/all/all_tickers.txt"
    try:
        r = requests.get(url, timeout=10)
        return [t.strip().upper() for t in r.text.splitlines() if t.strip()]
    except:
        return ["AAPL", "TSLA", "NVDA", "PLTR", "SOFI"]

def calculate_slope(series):
    # Simplified slope: (End - Start) / Length
    if len(series) < 2: return 0
    return (series.iloc[-1] - series.iloc[0]) / len(series)

def scan():
    universe = get_universe()
    winners = []
    yf_session = requests.Session()
    yf_session.headers.update({'User-Agent': 'Mozilla/5.0'})

    print(f"🔍 Filtering {len(universe)} tickers for Staircase Pattern...")
    
    for ticker in universe:
        try:
            stock = yf.Ticker(ticker, session=yf_session)
            # 1. Market Cap & Price Floor
            info = stock.info
            m_cap = info.get('marketCap', 0)
            if m_cap < 300_000_000: continue
            
            df = stock.history(period="60d") # Look at last 3 months
            if len(df) < 40: continue
            
            close = df['Close']
            curr_p = float(close.iloc[-1])
            if curr_p < 5.0: continue # Skip penny stocks

            # 2. Staircase Logic (Higher Highs & Higher Lows)
            # Compare last 10 days to the 10 days before that
            recent = df.tail(20)
            h1, l1 = recent['High'].iloc[0:10].max(), recent['Low'].iloc[0:10].min()
            h2, l2 = recent['High'].iloc[10:20].max(), recent['Low'].iloc[10:20].min()
            
            is_staircase = (h2 > h1) and (l2 > l1)
            
            if is_staircase:
                # 3. Volume & Momentum Slope
                vol = df['Volume']
                rvol_max = max([(vol.iloc[-i] / vol.iloc[-(i+21):-i].mean()) for i in range(1, 11)])
                
                if rvol_max >= 2.0:
                    # Gain Potential (Slope of the last 20 days)
                    slope = calculate_slope(close.tail(20))
                    
                    winners.append({
                        "Ticker": ticker,
                        "Price": round(curr_p, 2),
                        "RVOL": round(rvol_max, 2),
                        "Slope": round(slope, 4),
                        "Cap_M": round(m_cap / 1_000_000, 0)
                    })
            
            time.sleep(0.3) # Fast but safe
            
        except Exception:
            continue

    # Final Sort: Highest Slope (Momentum) at the top
    result_df = pd.DataFrame(winners)
    if not result_df.empty:
        result_df = result_df.sort_values(by="Slope", ascending=False)
        
    result_df.to_csv("daily_watchlist.csv", index=False)
    print(f"✅ Success! Saved {len(winners)} trending stocks.")

if __name__ == "__main__":
    scan()
