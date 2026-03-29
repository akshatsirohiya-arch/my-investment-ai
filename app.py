import streamlit as st
import pandas as pd

st.title("My AI Strategy Scanner")
st.write("Hello! This app is now live on GitHub.")

ticker = st.text_input("Enter a Stock Ticker", "AAPL")
st.write(f"You are looking at: {ticker}")
