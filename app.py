import streamlit as st
import pandas as pd

st.set_page_config(layout="wide", page_title="Momentum Funnel")

st.title("🏹 The Momentum Funnel")
st.subheader("Elite 'Staircase' Patterns Sorted by Trend Velocity")

try:
    df = pd.read_csv("daily_watchlist.csv")
    
    # 1. Sector Distribution Sidebar
    if 'Sector' in df.columns:
        selected_sector = st.sidebar.multiselect("Filter by Sector", options=df['Sector'].unique())
        if selected_sector:
            df = df[df['Sector'].isin(selected_sector)]

    # 2. Main Table
    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "Slope": st.column_config.ProgressColumn("Momentum Score", min_value=0, max_value=float(df['Slope'].max()) if not df.empty else 1),
            "RVOL": st.column_config.NumberColumn("Vol Surge", format="%.1fx"),
            "Cap_M": st.column_config.NumberColumn("Cap ($M)", format="$%d")
        }
    )
    
    # 3. Top Pick Analysis
    if not df.empty:
        top = df.iloc[0]
        st.info(f"💡 **Top Pick Analysis:** {top['Ticker']} is leading the market with a slope of {top['Slope']}. It operates in the **{top['Industry']}** industry.")

except FileNotFoundError:
    st.warning("Daily scan in progress. Check back shortly.")
