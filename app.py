import streamlit as st
import pandas as pd
import yfinance as yf
import os
import google.generativeai as genai
import time

# --- CONFIGURATION ---
st.set_page_config(layout="wide", page_title="AI 180-Day Breakout Hunter")

# Securely load Gemini API Key from Streamlit Cloud Secrets
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.sidebar.warning("🔑 Gemini API Key missing in Streamlit Secrets.")

st.title("🏹 180-Day Range Breakout Hunter")
st.subheader("Institutional Momentum & AI Geopolitical Intelligence (April 2026)")

# --- FUNCTIONS ---

@st.cache_data(ttl=86400)
def get_industry_safe(ticker):
    """Fetches industry with rate-limit protection and 24h caching."""
    try:
        time.sleep(0.2) # Small delay to respect Yahoo Finance limits
        tk = yf.Ticker(ticker)
        industry = tk.info.get('industry')
        return industry if industry else "Unknown Sector 🔍"
    except: 
        return "Limit Reached ⏳"

def run_ai_analysis(top_stocks_df):
    """Analyzes the top 50 breakouts using a Multi-Model Fallback system."""
    # List of models to try in order of 2026 stability/availability
    model_names = ['gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-pro']
    
    # Prepare the stock data for the AI prompt
    summary_list = [
        f"{r['Ticker']} (${r['Price']:.2f}, {r['Annualized_Return']:.1f}% Velocity)" 
        for _, r in top_stocks_df.iterrows()
    ]
    data_string = "; ".join(summary_list)
    
    prompt = f"""
    You are a Senior Geopolitical Analyst. Analyze these Top 50 stocks breaking 180-day highs:
    {data_string}

    TASKS:
    1. Identify Energy/Defense plays heavily linked to the Iran/Middle-East conflict.
    2. Provide a 'War-Risk Warning' (Is it a Safe Haven or a Volatility Trap?).
    3. Give a 1-sentence BUY/HOLD/AVOID verdict for each based on latest April 2026 news.
    
    Format the response as a professional Markdown report.
    """

    for m_name in model_names:
        try:
            model = genai.GenerativeModel(model_name=m_name)
            # Using the 2026 Google Search Grounding tool
            response = model.generate_content(
                prompt,
                tools=[{"google_search_retrieval": {}}]
            )
            return response.text
        except Exception as e:
            # If this is the last model in the list and it fails, return the error
            if m_name == model_names[-1]:
                return f"AI Analysis Error: All models failed. Last error: {str(e)}"
            # Otherwise, 'continue' to the next model in the list
            continue

# --- MAIN APP LOGIC ---

if os.path.exists("daily_watchlist.csv"):
    df = pd.read_csv("daily_watchlist.csv")
    
    if not df.empty:
        # 1. CALCULATE TREND VELOCITY (ANNUALIZED %)
        # Formula: (Daily Slope / Price) * 252 Trading Days * 100
        df['Annualized_Return'] = (df['Slope'] / df['Price']) * 252 * 100
        
        # 2. ADD TRADINGVIEW LINKS & SORT BY VELOCITY
        df['Chart'] = df['Ticker'].apply(lambda x: f"https://www.tradingview.com/symbols/{x}/")
        df = df.sort_values(by="Annualized_Return", ascending=False)

        # 3. SIDEBAR FILTERS
        st.sidebar.header("🎚️ Filters")
        min_rvol = st.sidebar.slider("Min RVOL (Vol Surge)", 0.0, 10.0, 1.0)
        
        # Filter dataframe for display
        df_display = df[df['RVOL'] >= min_rvol].head(100).copy()

        # 4. INDUSTRY TOGGLE (Optional to prevent Yahoo N/A blocks)
        st.sidebar.markdown("---")
        show_industry = st.sidebar.checkbox("🔍 Load Industries (Slower)")
        if show_industry:
            with st.spinner("Fetching Sector Data from Yahoo..."):
                df_display['Industry'] = df_display['Ticker'].apply(get_industry_safe)
        else:
            df_display['Industry'] = "Click sidebar to load"

        # 5. AI ANALYST TRIGGER (TOP 50)
        st.sidebar.markdown("---")
        st.sidebar.header("🤖 AI Analyst")
        if st.sidebar.button("Run AI Deep-Dive (Top 50)"):
            with st.status("Gemini is searching 2026 war news...", expanded=True) as status:
                st.write("Extracting top 50 breakout candidates...")
                top_50 = df_display.head(50)
                st.write("Consulting Geopolitical Intelligence...")
                ai_report = run_ai_analysis(top_50)
                status.update(label="Analysis Complete!", state="complete")
            
            st.markdown("### 🛰️ Gemini Geopolitical Intelligence Report")
            st.markdown(ai_report)
            st.markdown("---")

        # 6. DATA TABLE DISPLAY
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
                "High_180d": None, "Slope": None # Hiding raw technical columns
            }
        )
        
        # 7. MOMENTUM HIGHLIGHT
        if not df_display.empty:
            leader = df_display.iloc[0]
            st.success(f"🏆 **Momentum Leader:** {leader['Ticker']} is trending at an annualized velocity of **{leader['Annualized_Return']:.1f}%**.")

    else:
        st.warning("No stocks cleared their 180-day high in today's scan.")
else:
    st.error("Data file (daily_watchlist.csv) not found. Ensure scanner.py has run successfully.")
