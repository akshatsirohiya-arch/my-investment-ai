# --- THE BOUNCER (STRICT FILTERING) ---
for ticker in tickers:
    try:
        stock = yf.Ticker(ticker)
        # 1. Immediate check: Is this company big enough?
        info = stock.info
        mkt_cap = info.get('marketCap', 0)
        
        # 300,000,000 is our "floor"
        if mkt_cap < 300_000_000:
            continue # This skips the stock entirely and moves to the next
            
        # 2. If it passed, now we get the price history
        df = stock.history(period="1y")
        
        # 3. Calculate our "Footprint" (10-Day Max RVOL)
        price, max_vol, is_match = analyze_with_volume_lookback(df, info)
        
        # 4. Only show it if it has our required volume surge
        if max_vol >= vol_threshold:
            display_stock_match(ticker, price, max_vol, is_match)
            
    except Exception:
        continue # Skip errors (like delisted stocks)
