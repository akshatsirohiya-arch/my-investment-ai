import streamlit as st
import yfinance as yf
import pandas as pd
import time

# --- SETUP ---
st.set_page_config(layout="wide", page_title="Institutional Scanner")

# --- CALCULATION ENGINE ---
def analyze_stock(df):
    close = df['Close']
    volume = df['Volume']
    curr_p = float(close.iloc[-1])
    
    # Technical Pattern
    high_6m = float(close.iloc[-126:-1].max())
    recent = df.tail(20)
    h1, h2 = float(recent['High'].iloc[0:10].max()), float(recent['High'].iloc[10:20].max())
    l1, l2 = float(recent['Low'].iloc[0:10].min()), float(recent['Low'].iloc[10:20].min())
    is_pattern = (curr_p > high_6m) and (h2 > h1) and (l2 > l1)
    
    # 10-Day Volume Surge
    rvol_list = []
    for i in range(1, 11):
        target_vol = volume.iloc[-i]
        hist_avg = volume.iloc[-(i+21):-i].mean()
        rvol_list.append(target_vol / hist_avg if hist_avg > 0 else 0)
    
    return curr_p, max(rvol_list), is_pattern

# --- SIDEBAR ---
st.sidebar.header("Filter Settings")
min_cap_val = st.sidebar.number_input("Min Cap ($M)", value=300)
min_cap = min_cap_val * 1_000_000
vol_req = st.sidebar.slider("Min RVOL Surge", 1.0, 5.0, 1.5)

# --- MAIN UI ---
st.title("💎 Institutional Breakout Hunter")

user_input = st.text_area("Paste Tickers (Comma separated)", "PLTR, SOFI, HOOD, TSLA, NVDA, AMD, CELH, RKLB, IONQ, OKLO, LUNR", height=100)

if st.button("🚀 Start Scan"):
    tickers = [t.strip().upper() for t in user_input.split(",") if t.strip()]
    
    # --- NEW: STATS WIDGET AREA ---
    st.subheader("📊 Scan Statistics")
    stat_col1, stat_col2, stat_col3 = st.columns(3)
    total_widget = stat_col1.empty()
    skipped_widget = stat_col2.empty()
    matches_widget = stat_col3.empty()
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Counters
    count_scanned = 0
    count_skipped_cap = 0
    count_matches = 0

    results_container = st.container()

    for idx, ticker in enumerate(tickers):
        # Update Progress
        count_scanned += 1
        progress_bar.progress((idx + 1) / len(tickers))
        status_text.text(f"Processing {ticker}...")
        
        # Update Stats Widgets in Real-Time
        total_widget.metric("Total Scanned", count_scanned)
        skipped_widget.metric("Skipped (<$300M)", count_skipped_cap)
        matches_widget.metric("Matches Found", count_matches)

        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            mkt_cap = info.get('marketCap', 0)
            
            # --- FILTER 1: MARKET CAP ---
            if mkt_cap < min_cap:
                count_skipped_cap += 1
                skipped_widget.metric("Skipped (<$300M)", count_skipped_cap)
                continue
                
            df = stock.history(period="1y")
            if df.empty: continue
            
            price, max_vol, is_match = analyze_stock(df)
            
            # --- FILTER 2: VOLUME ---
            if max_vol < vol_req:
                continue
            
            # If we reach here, it's a match!
            count_matches += 1
            matches_widget.metric("Matches Found", count_matches)

            with results_container:
                c1, c2, c3 = st.columns([1, 2, 1])
                with c1:
                    st.subheader(ticker)
                    st.metric("Price", f"${price:.2f}")
                    st.caption(f"Cap: ${mkt_cap/1_000_000:.0f}M")
                
                with c2:
                    st.write(f"📈 **Max Volume Surge:** {max_vol:.2f}x")
                    if is_match:
                        st.success("🎯 STAIRCASE CONFIRMED")
                    else:
                        st.info("High Volume detected. Pattern forming.")
                
                with c3:
                    with st.expander("View Chart"):
                        st.line_chart(df['Close'].tail(60))
                st.divider()
            
            time.sleep(1.2)
            
        except Exception:
            continue

    status_text.success(f"✅ Finished! Found {count_matches} stocks out of {count_scanned} scanned.")
