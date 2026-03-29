import streamlit as st
import yfinance as yf
import pandas as pd
import time
import requests

# --- 1. THE UNIVERSE (Entire US Market) ---
@st.cache_data(ttl=86400)
def get_entire_us_universe():
    """Fetches a comprehensive list of all US-listed tickers."""
    try:
        # Using a reliable public source for NASDAQ/NYSE/AMEX tickers
        url = "https://pkgstore.datahub.io/core/nyse-other-listings/nyse-listed_csv/data/3c8b905153027da548f1840003b0286c/nyse-listed_csv.csv"
        nyse = pd.read_csv(url)['ACT Symbol'].tolist()
        
        url_other = "https://pkgstore.datahub.io/core/nyse-other-listings/other-listed_csv/data/9f3a267b14619f74e62e3914856f6b1e/other-listed_csv.csv"
        others = pd.read_csv(url_other)['NASDAQ Symbol'].tolist()
        
        return list(set(nyse + others))
    except:
        # Fallback to a smaller sample if the external source is down
        return ["AAPL", "TSLA", "NVDA", "MSFT", "AMD", "PLTR", "SOFI"]

def analyze_stock_logic(df):
    close, volume = df['Close'], df['Volume']
    curr_p = float(close.iloc[-1])
    high_6m = float(close.iloc[-126:-1].max())
    
    # Staircase check
    recent = df.tail(20)
    h1, l1 = float(recent['High'].iloc[0:10].max()), float(recent['Low'].iloc[0:10].min())
    h2, l2 = float(recent['High'].iloc[10:20].max()), float(recent['Low'].iloc[10:20].min())
    is_pattern = (curr_p > high_6m) and (h2 > h1) and (l2 > l1)
    
    # 10-Day RVOL
    rvol_list = [ (volume.iloc[-i] / volume.iloc[-(i+21):-i].mean()) for i in range(1, 11) ]
    return curr_p, max(rvol_list), is_pattern

# --- 2. SIDEBAR ---
st.sidebar.header("🛡️ Funnel Settings")
min_cap_m = st.sidebar.number_input("Market Cap Floor ($Millions)", value=300)
vol_req = st.sidebar.slider("Min 'Footprint' Surge", 1.0, 5.0, 2.0)

# --- 3. MAIN INTERFACE ---
st.title("🌌 Total US Market Funnel")
st.info(f"Scanning for breakouts across the entire US exchange. Cap Floor: ${min_cap_m}M")

if st.button("🔭 Launch Global Search"):
    universe = get_entire_us_universe()
    
    # Statistics Dashboard
    st.subheader("📊 Live Funnel Stats")
    f1, f2, f3 = st.columns(3)
    w_scanned = f1.empty()
    w_filtered = f2.empty()
    w_watchlist = f3.empty()
    
    prog = st.progress(0)
    
    # Counters
    c_scanned, c_small, c_matches = 0, 0, 0
    results_area = st.container()

    for idx, ticker in enumerate(universe):
        c_scanned += 1
        prog.progress((idx + 1) / len(universe))
        w_scanned.metric("Total Scanned", c_scanned)
        
        try:
            # Step 1: Rapid Cap Check
            stock = yf.Ticker(ticker)
            info = stock.info
            m_cap = info.get('marketCap', 0)
            
            if m_cap < (min_cap_m * 1_000_000):
                c_small += 1
                w_filtered.metric("Rejected (Small Cap)", c_small)
                continue

            # Step 2: History & Pattern Scan
            df = stock.history(period="1y")
            if df.empty or len(df) < 130: continue
            
            price, rvol, match = analyze_stock_logic(df)
            if rvol < vol_req: continue
            
            # Step 3: Display Results
            c_matches += 1
            w_watchlist.metric("Watchlist Hits", c_matches)
            
            with results_area:
                c1, c2, c3 = st.columns([1, 2, 1])
                c1.metric(ticker, f"${price:.2f}", f"Cap: ${m_cap/1e6:.0f}M")
                with c2:
                    st.write(f"📈 **Volume Surge:** {rvol:.2f}x")
                    if match: st.success("🎯 STAIRCASE PATTERN")
                with c3:
                    with st.expander("Chart"):
                        st.line_chart(df['Close'].tail(60))
                st.divider()
            
            time.sleep(1.2) # Essential delay

        except:
            continue
