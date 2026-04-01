import streamlit as st
import pandas as pd
import yfinance as yf
import os
import google.generativeai as genai
import time

# --- CONFIGURATION ---
st.set_page_config(layout="wide", page_title="AI 180-Day Breakout Hunter")

# Setup Gemini
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.sidebar.warning("🔑 Gemini API Key missing in Secrets.")

st.title("🏹 180-Day Range Breakout Hunter")
st.subheader("Institutional Momentum with AI Geopolitical Deep-Dive")

# --- FUNCTIONS ---

@st.cache_data(ttl=86400) # Cache for 24 hours to prevent redundant pings
def get_industry_safe(ticker):
    """Fetches industry with a delay and error handling to avoid N/A."""
    try:
        time.sleep(0.2) # Small delay to respect Yahoo's rate limits
        tk = yf.Ticker(ticker)
        industry = tk.info.get('industry')
        if not industry or industry == 'N/A':
            return "Check Google 🔍"
        return industry
    except: 
        return "Limit Reached ⏳"

def run_ai_analysis(top_stocks_df):
    try:
        model = genai.GenerativeModel(
            model_name='gemini-1.5-flash',
            tools=[{"google_search": {}}] 
        )
        summary_list = [f"{r['Ticker']} (${r['Price']}, {r['Annualized_Return']:.1f}% Velocity)" for _, r in top_stocks_df.iterrows()]
        data_string = "; ".join(summary_list)
        
        prompt = f"""
        Analyze the following Top 50 stocks breaking 180-day highs: {data_string}.
        1. Categorize by 'War Sensitivity' (Iran conflict).
        2. Top 5 Conviction Picks for April 2026.
        3. Flag 'Volatility Traps'.
        Format as markdown.
        """
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI Analysis Error: {str(e)}"

# --- MAIN APP LOGIC ---

if os.path.exists("daily_watchlist.csv"):
    df = pd.read_csv("daily_watchlist.csv")
    
    if not df.empty:
        # Calculate Annualized Return %
        df['Annualized_Return'] = (df['Slope'] / df['Price']) * 252 * 100
        df['Chart'] = df['Ticker'].apply(lambda x: f"https://www.tradingview.com/symbols/{x}/")
        df = df.sort_values(by="Annualized_Return", ascending=False)

        # Filters
        st.sidebar.header("🎚️ Filters")
        min_rvol = st.sidebar.slider("Min RVOL (Vol Surge)", 0.0, 5.0, 1.0) # Default to 1.0 to hide junk
        df_display = df[df['RVOL'] >= min_rvol].head(100).copy()

        # Only fetch industry for what we are actually seeing
        if st.checkbox("🔍 Show Industries (Slows loading)"):
            with st.spinner("Fetching Sector Data..."):
                df_display['Industry'] = df_display['Ticker'].apply(get_industry_safe)
        else:
            df_display['Industry'] = "Click to Load"

        # AI Analyst Trigger
        st.sidebar.markdown("---")
        if st.sidebar.button("🤖 Run AI Deep-Dive (Top 50)"):
            with st.status("Gemini analyzing Top 50...", expanded=True):
                ai_report = run_ai_analysis(df_display.head(50))
            st.markdown(ai_report)

        # Main Table
        st.dataframe(
            df_display,
            use_container_width=True,
            column_config={
                "Ticker": st.column_config.TextColumn("Ticker"),
                "Chart": st.column_config.LinkColumn("Chart 📈", display_text="View Setup"),
                "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
                "Annualized_Return": st.column_config.NumberColumn("Ann. Velocity %", format="%.1f%%"),
                "RVOL": st.column_config.NumberColumn("Rel Volume", format="%.2fx"),
                "Industry": st.column_config.TextColumn("Industry"),
                "High_180d": None, "Slope": None # Clean up columns
            }
        )
    else:
        st.warning("No breakouts found today.")
else:
    st.error("Data file missing. Run the scanner first.")
