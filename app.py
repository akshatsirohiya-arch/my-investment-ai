import streamlit as st
import pandas as pd
import os
import urllib.parse

# --- CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Institutional Momentum Hub")

st.title("🏹 Momentum Strategy Command Center")
st.subheader("180-Day Range Breakouts & Manual AI Deep-Dives")

# --- HELPER: GENERATE GEMINI LINK ---
def get_gemini_link(ticker, price, velocity):
    base_url = "https://gemini.google.com/app"
    # A professional-grade prompt for the Gemini App
    prompt = f"""Act as a hedge fund analyst. Perform a deep-dive on {ticker} currently trading at ${price}. 
    It just broke a 180-day price range with a momentum velocity of {velocity}%.
    1. Check for recent news or earnings gaps.
    2. Analyze if this breakout is sustainable or a 'blow-off top'.
    3. Look for institutional accumulation patterns in the last 30 days.
    4. Provide a Final Verdict: Buy, Watch, or Avoid."""
    
    # URL Encode the prompt
    encoded_prompt = urllib.parse.quote(prompt)
    return f"https://gemini.google.com/app?q={encoded_prompt}"

# --- MAIN LOGIC ---
if os.path.exists("daily_watchlist.csv"):
    df = pd.read_csv("daily_watchlist.csv")
    
    if not df.empty:
        # 1. Calculations
        df['Annualized_Return'] = (df['Slope'] / df['Price']) * 252 * 100
        
        # 2. Add the "Deep Dive" Link Column
        df['AI Deep Dive'] = df.apply(lambda x: get_gemini_link(x['Ticker'], x['Price'], round(x['Annualized_Return'], 1)), axis=1)
        
        # 3. Sidebar Filters
        st.sidebar.header("🎯 Quality Filters")
        min_rvol = st.sidebar.slider("Min Relative Volume (RVOL)", 0.5, 5.0, 1.2, help="Filter out low-volume breakouts")
        min_velocity = st.sidebar.slider("Min Velocity %", 10, 200, 30)
        
        # Apply filters to a display copy, NOT the AI source
        df_filtered = df[(df['RVOL'] >= min_rvol) & (df['Annualized_Return'] >= min_velocity)].copy()
        df_filtered = df_filtered.sort_values(by="Annualized_Return", ascending=False)

        # 4. Display the Full Watchlist
        st.markdown(f"Showing **{len(df_filtered)}** high-momentum setups.")
        
        st.dataframe(
            df_filtered,
            use_container_width=True,
            column_config={
                "Ticker": st.column_config.TextColumn("Ticker"),
                "AI Deep Dive": st.column_config.LinkColumn("🤖 Deep Dive", display_text="Ask Gemini"),
                "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
                "Annualized_Return": st.column_config.NumberColumn("Velocity %", format="%.1f%%"),
                "RVOL": st.column_config.NumberColumn("Rel Volume", format="%.2fx"),
                "High_180d": None, "Slope": None # Hide these technical cols
            },
            hide_index=True
        )

    else:
        st.warning("Scanner found 0 stocks. Try loosening filters in your scanner.py script.")
else:
    st.error("Missing daily_watchlist.csv. Run your 6AM IST GitHub Action.")
