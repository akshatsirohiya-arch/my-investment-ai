import streamlit as st
import pandas as pd
import yfinance as yf
import os
import google.generativeai as genai

# --- CONFIGURATION ---
st.set_page_config(layout="wide", page_title="AI 180-Day Breakout Hunter")

# Setup Gemini (Securely pull API key from Streamlit secrets)
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    # Fallback for local testing if secrets.toml isn't used
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
    else:
        st.sidebar.warning("🔑 Gemini API Key missing. Please add to Streamlit Secrets.")

st.title("🏹 180-Day Range Breakout Hunter")
st.subheader("Institutional Momentum with AI Geopolitical Deep-Dive")

# --- FUNCTIONS ---

@st.cache_data(ttl=3600)
def get_industry(ticker):
    try:
        info = yf.Ticker(ticker).info
        return info.get('industry', 'N/A')
    except: return 'N/A'

def run_ai_analysis(top_stocks_df):
    """Feeds the top 50 performers to Gemini for Geopolitical & Fundamental Review."""
    try:
        # Using Gemini 1.5 Flash for speed and high token limits
        model = genai.GenerativeModel(
            model_name='gemini-1.5-flash',
            tools=[{"google_search": {}}] 
        )
        
        # Prepare the data summary for the AI
        summary_list = []
        for _, row in top_stocks_df.iterrows():
            summary_list.append(f"{row['Ticker']} (${row['Price']}, {row['Annualized_Return']:.1f}% Ann. Velocity)")
        
        data_string = "; ".join(summary_list)
        
        prompt = f"""
        You are a Senior Geopolitical and Equity Analyst. 
        Analyze the following Top 50 stocks currently breaking 180-day highs:
        {data_string}

        TASKS:
        1. Categorize these stocks by 'War Sensitivity' (High/Med/Low) regarding the Iran-Israel conflict.
        2. Identify the 'Top 5 Conviction Picks' based on current April 2026 news and supply chain safety.
        3. Flag any stocks that look like 'Volatility Traps' (overextended due to panic buying).
        4. Provide a structured summary including a 'Geopolitical Risk Outlook' for the energy sector.
        
        Format your response with clear headers and bullet points.
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI Analysis Error: {str(e)}"

# --- MAIN APP LOGIC ---

if os.path.exists("daily_watchlist.csv"):
    df = pd.read_csv("daily_watchlist.csv")
    
    if not df.empty:
        # 1. ANNUALIZED RETURN CALCULATION
        # (Slope / Price) * 252 trading days * 100 to get %
        df['Annualized_Return'] = (df['Slope'] / df['Price']) * 252 * 100
        
        # 2. DATA ENHANCEMENTS
        df['Chart'] = df['Ticker'].apply(lambda x: f"https://www.tradingview.com/symbols/{x}/")
        
        # Sort by the new Velocity Metric
        df = df.sort_values(by="Annualized_Return", ascending=False)
        
        with st.spinner("Classifying Industries..."):
            # Limit industry fetch to the top 100 to save time/API calls
            top_subset = df.head(100).copy()
            top_subset['Industry'] = top_subset['Ticker'].apply(get_industry)

        # 3. SIDEBAR FILTERS
        st.sidebar.header("🎚️ Filters")
        min_rvol = st.sidebar.slider("Min RVOL (Vol Surge)", 0.0, 5.0, 0.0)
        df_display = top_subset[top_subset['RVOL'] >= min_rvol]

        # 4. AI TRIGGER BUTTON (TOP 50)
        st.sidebar.markdown("---")
        st.sidebar.header("🤖 AI Analyst")
        if st.sidebar.button("Run AI Deep-Dive (Top 50)"):
            with st.status("Gemini analyzing Top 50 Breakouts...", expanded=True) as status:
                st.write("Aggregating trend data for 50 strongest tickers...")
                top_50 = df_display.head(50)
                st.write("Cross-referencing Iran Conflict news & Google Search...")
                ai_report = run_ai_analysis(top_50)
                status.update(label="Deep-Dive Complete!", state="complete", expanded=False)
            
            st.markdown("### 🛰️ Gemini Geopolitical Intelligence Report (Top 50)")
            st.markdown(ai_report)
            st.markdown("---")

        # 5. MAIN DATA TABLE
        st.dataframe(
            df_display,
            use_container_width=True,
            column_config={
                "Ticker": st.column_config.TextColumn("Ticker", width="small"),
                "Chart": st.column_config.LinkColumn("Chart 📈", display_text="View Setup"),
                "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
                "High_180d": st.column_config.NumberColumn("180D Resistance", format="$%.2f"),
                "Annualized_Return": st.column_config.NumberColumn("Trend Velocity (Ann. %)", format="%.1f%%"),
                "RVOL": st.column_config.NumberColumn("Rel Volume", format="%.2fx"),
                "Industry": st.column_config.TextColumn("Industry"),
                "Slope": None # Hiding raw slope to keep UI clean
            }
        )
        
        # 6. DASHBOARD INSIGHT
        if not df_display.empty:
            top_stock = df_display.iloc[0]
            st.success(f"🏆 **Top Velocity:** {top_stock['Ticker']} ({top_stock['Industry']}) is moving at an annualized rate of **{top_stock['Annualized_Return']:.1f}%**.")
        
    else:
        st.warning("No stocks cleared their 180-day high today.")
else:
    st.error("Data file missing. Please trigger the GitHub Action.")
