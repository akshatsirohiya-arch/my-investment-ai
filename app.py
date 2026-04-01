import streamlit as st
import pandas as pd
import yfinance as yf
import os
import google.generativeai as genai
import time

# --- CONFIGURATION ---
st.set_page_config(layout="wide", page_title="AI 180-Day Breakout Hunter")

# Securely load Gemini API Key
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.sidebar.warning("🔑 Gemini API Key missing in Streamlit Secrets.")

st.title("🏹 180-Day Range Breakout Hunter")
st.subheader("Institutional Momentum & AI Geopolitical Intelligence")

# --- FUNCTIONS ---

@st.cache_data(ttl=86400)
def get_industry_safe(ticker):
    """Fetches industry with rate-limit protection."""
    try:
        time.sleep(0.2) # Avoid hitting Yahoo too hard
        tk = yf.Ticker(ticker)
        industry = tk.info.get('industry')
        return industry if industry else "Unknown 🔍"
    except: 
        return "Limit Reached ⏳"

def run_ai_analysis(top_stocks_df):
    """Analyzes the top 50 breakouts using Gemini with Google Search Grounding."""
    try:
        # Use Gemini 1.5 Flash for high-speed analysis
        model = genai.GenerativeModel(model_name='gemini-1.5-flash')
        
        # Prepare the stock data for the prompt
        summary_list = [
            f"{r['Ticker']} (${r['Price']:.2f}, {r['Annualized_Return']:.1f}% Velocity)" 
            for _, r in top_stocks_df.iterrows()
        ]
        data_string = "; ".join(summary_list)
        
        prompt = f"""
        Analyze these Top 50 stocks breaking 180-day highs: {data_string}.
        1. Identify Energy/Defense plays linked to the Iran/Middle-East conflict.
        2. Provide a 'War-Risk Warning' (Safe Haven vs Volatility Trap).
        3. Give a 1-sentence BUY/HOLD/AVOID verdict for each based on current April 2026 news.
        
        Format the response in a clean Markdown table or list.
        """

        # Correct 2026 syntax for Google Search tool
        # Note: If this fails, the 'except' block will handle it without the tool.
        response = model.generate_content(
            prompt,
            tools=[{
                "google_search_retrieval": {
                    "dynamic_retrieval_config": {
                        "mode": "unspecified",
                        "dynamic_threshold": 0.06  # Adjusts how often it uses search
                    }
                }
            }]
        )
        return response.text

    except Exception as e:
        # Fallback if the Search tool syntax is rejected or API is down
        try:
            model_basic = genai.GenerativeModel(model_name='gemini-1.5-flash')
            response = model_basic.generate_content(prompt)
            return f"*(Analysis running without live-search tool due to technical limit)*\n\n{response.text}"
        except:
            return f"AI Analysis Error: {str(e)}"

# --- MAIN APP LOGIC ---

if os.path.exists("daily_watchlist.csv"):
    df = pd.read_csv("daily_watchlist.csv")
    
    if not df.empty:
        # 1. CALCULATE ANNUALIZED RETURN %
        # (Price Change / Price) * 252 Days = Yearly velocity
        df['Annualized_Return'] = (df['Slope'] / df['Price']) * 252 * 100
        
        # 2. CLEANUP & SORT
        df['Chart'] = df['Ticker'].apply(lambda x: f"https://www.tradingview.com/symbols/{x}/")
        df = df.sort_values(by="Annualized_Return", ascending=False)

        # 3. SIDEBAR CONTROLS
        st.sidebar.header("🎚️ Filters")
        min_rvol = st.sidebar.slider("Min RVOL (Vol Surge)", 0.0, 10.0, 1.0)
        
        # Filter dataframe based on user input
        df_display = df[df['RVOL'] >= min_rvol].head(100).copy()

        # 4. INDUSTRY TOGGLE (Saves API limits)
        st.sidebar.markdown("---")
        show_industry = st.sidebar.checkbox("🔍 Fetch Industries (Slower)")
        if show_industry:
            with st.spinner("Classifying Sectors..."):
                df_display['Industry'] = df_display['Ticker'].apply(get_industry_safe)
        else:
            df_display['Industry'] = "Click sidebar to load"

        # 5. AI ANALYST TRIGGER (TOP 50)
        st.sidebar.markdown("---")
        st.sidebar.header("🤖 AI Analyst")
        if st.sidebar.button("Run AI Deep-Dive (Top 50)"):
            with st.status("Gemini is reading war news & checking charts...", expanded=True) as status:
                st.write("Aggregating Top 50 performers...")
                top_50 = df_display.head(50)
                st.write("Cross-referencing Geopolitical Data...")
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
                "High_180d": None, "Slope": None # Hide raw math columns
            }
        )
        
        # 7. MOMENTUM HIGHLIGHT
        if not df_display.empty:
            leader = df_display.iloc[0]
            st.success(f"🏆 **Momentum Leader:** {leader['Ticker']} is currently moving at a **{leader['Annualized_Return']:.1f}%** annualized pace.")

    else:
        st.warning("No stocks cleared their 180-day high in today's scan.")
else:
    st.error("Data file (daily_watchlist.csv) not found. Please run the scanner first.")
