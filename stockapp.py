import streamlit as st

# --- SAFETY CHECK FOR IMPORTS ---
try:
    import yfinance as yf
    import pandas as pd
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    from datetime import datetime
except ImportError as e:
    st.error(f"""
    ❌ **Missing Library Error: {e.name}**
    
    To fix this on Streamlit Cloud, you must create a file named `requirements.txt` in your GitHub repository with the following content:
    
    ```text
    streamlit
    yfinance
    pandas
    plotly
    ```
    
    Once you add that file, reboot the app.
    """)
    st.stop()

# --- CONFIGURATION ---
st.set_page_config(page_title="Stock Trend Analyzer", layout="wide", page_icon="📈")

st.title("📈 Pro Stock Analyzer & Interpreter")
st.markdown("Analyze stock performance across key timeframes with automated technical interpretation.")

# --- SIDEBAR: SETTINGS ---
st.sidebar.header("Configuration")

# 1. Flexible Input: Ticker Selection
ticker_mode = st.sidebar.radio("Select Ticker Source", ["Popular List", "Custom Symbol"])

# Default list of major world indices/stocks
DEFAULT_TICKERS = {
    "Nifty 50 (India)": "^NSEI",
    "Sensex (India)": "^BSESN",
    "Reliance Industries": "RELIANCE.NS",
    "Tata Motors": "TATAMOTORS.NS",
    "S&P 500 (USA)": "^GSPC",
    "Nasdaq (USA)": "^IXIC",
    "Apple Inc.": "AAPL",
    "Tesla Inc.": "TSLA",
    "Nvidia": "NVDA",
    "Gold (Futures)": "GC=F",
    "Bitcoin (USD)": "BTC-USD"
}

if ticker_mode == "Popular List":
    selected_name = st.sidebar.selectbox("Select Asset", list(DEFAULT_TICKERS.keys()))
    ticker_symbol = DEFAULT_TICKERS[selected_name]
else:
    ticker_symbol = st.sidebar.text_input(
        "Enter Ticker Symbol", 
        value="AAPL", 
        help="Common Suffixes: India (.NS, .BO), London (.L), Paris (.PA). Example: TCS.NS"
    ).upper()

# 2. Chart Settings (Candlestick vs Line Control)
st.sidebar.subheader("Chart Settings")
chart_type = st.sidebar.radio("Chart Type", ["Candlestick", "Line"], index=0)
show_ma = st.sidebar.checkbox("Show 20-Day SMA", value=True)
show_vol = st.sidebar.checkbox("Show Volume", value=True) 

# --- FUNCTIONS ---

def get_data(ticker, period):
    """
    Fetches data from Yahoo Finance.
    """
    try:
        stock = yf.Ticker(ticker)
        # 1 Week isn't a direct period in yfinance, so we use 5d
        yf_period = "5d" if period == "1 Week" else \
                    "1mo" if period == "1 Month" else \
                    "3mo" if period == "3 Months" else \
                    "6mo" if period == "6 Months" else \
                    "1y" if period == "1 Year" else "1d"
        
        # Use 1m interval for 1 Day, otherwise 1d
        interval = "1m" if period == "1 Day" else "1d"
        
        df = stock.history(period=yf_period, interval=interval)
        
        if df.empty:
            return pd.DataFrame(), None
        
        return df, stock.info
    except Exception as e:
        return pd.DataFrame(), None

def calculate_indicators(df):
    """Calculates SMA and RSI for interpretation."""
    if len(df) < 15:
        return df 
    
    # Simple Moving Average (SMA)
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    
    # RSI (Relative Strength Index)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    return df

def generate_interpretation(df, period):
    """Generates text analysis based on price action and indicators."""
    if df.empty or len(df) < 2:
        return "Not enough data to generate an interpretation."

    start_price = df['Close'].iloc[0]
    end_price = df['Close'].iloc[-1]
    change_pct = ((end_price - start_price) / start_price) * 100
    
    trend = "Bullish (Upward)" if change_pct > 0 else "Bearish (Downward)"
    color = "green" if change_pct > 0 else "red"
    
    interpretation = f"**Performance:** Over the last **{period}**, the stock is :{color}[**{trend}**], moving from ${start_price:.2f} to ${end_price:.2f} ({change_pct:.2f}%)."
    
    # RSI Interpretation
    if 'RSI' in df.columns and not pd.isna(df['RSI'].iloc[-1]):
        rsi = df['RSI'].iloc[-1]
        interpretation += f"\n\n**RSI Indicator ({rsi:.0f}):** "
        if rsi > 70:
            interpretation += "The stock is currently **Overbought** (>70). This suggests the price might be too high and could correct downwards soon."
        elif rsi < 30:
            interpretation += "The stock is currently **Oversold** (<30). This suggests the price might be undervalued and could bounce back."
        else:
            interpretation += "The RSI is in the **Neutral** zone (30-70), indicating a stable trend."

    # Moving Average Interpretation
    if 'SMA_20' in df.columns and not pd.isna(df['SMA_20'].iloc[-1]):
        sma = df['SMA_20'].iloc[-1]
        interpretation += f"\n\n**Trend Signal (20-SMA):** The stock is trading {'above' if end_price > sma else 'below'} its 20-period average (${sma:.2f}). "
        interpretation += "Trading above the average typically confirms a short-term uptrend." if end_price > sma else "Trading below the average often indicates weakness."

    return interpretation

# --- MAIN APP LOGIC ---

if ticker_symbol:
    # Timeframe Tabs
    tabs = st.tabs(["1 Day", "1 Week", "1 Month", "3 Months", "6 Months", "1 Year"])
    
    periods_map = {
        "1 Day": "1 Day", "1 Week": "1 Week", "1 Month": "1 Month",
        "3 Months": "3 Months", "6 Months": "6 Months", "1 Year": "1 Year"
    }
    
    for tab, (tab_name, period_key) in zip(tabs, periods_map.items()):
        with tab:
            with st.spinner(f"Analyzing {ticker_symbol} for {tab_name}..."):
                df, info = get_data(ticker_symbol, period_key)
                
                if not df.empty:
                    df = calculate_indicators(df)
                    
                    # 1. Metrics
                    latest_price = df['Close'].iloc[-1]
                    prev_close = df['Close'].iloc[-2] if len(df) > 1 else df['Open'].iloc[0]
                    daily_change = latest_price - prev_close
                    daily_pct = (daily_change / prev_close) * 100
                    
                    m1, m2, m3 = st.columns(3)
                    currency = info.get('currency', 'USD') if info else 'USD'
                    m1.metric("Current Price", f"{latest_price:.2f} {currency}", f"{daily_pct:.2f}%")
                    m2.metric("Period High", f"{df['High'].max():.2f}")
                    m3.metric("Period Low", f"{df['Low'].min():.2f}")
                    
                    # 2. Charts (Using Subplots for Volume)
                    if show_vol:
                        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                                            vertical_spacing=0.05, 
                                            row_heights=[0.7, 0.3],
                                            subplot_titles=(f"{ticker_symbol} Price Trend", "Volume"))
                    else:
                        fig = go.Figure()

                    # Chart Type Selection (Candlestick vs Line)
                    if chart_type == "Candlestick":
                        main_trace = go.Candlestick(x=df.index,
                                        open=df['Open'], high=df['High'],
                                        low=df['Low'], close=df['Close'], name="OHLC")
                    else:
                        main_trace = go.Scatter(x=df.index, y=df['Close'], 
                                        mode='lines', name='Close Price', 
                                        line=dict(color='#0052cc', width=2))
                    
                    # Add Main Trace
                    if show_vol:
                        fig.add_trace(main_trace, row=1, col=1)
                    else:
                        fig.add_trace(main_trace)

                    # Add Moving Average
                    if show_ma and 'SMA_20' in df.columns:
                        ma_trace = go.Scatter(x=df.index, y=df['SMA_20'], 
                                        mode='lines', name='20-SMA', 
                                        line=dict(color='orange', width=1, dash='dash'))
                        if show_vol:
                            fig.add_trace(ma_trace, row=1, col=1)
                        else:
                            fig.add_trace(ma_trace)

                    # Add Volume to Row 2
                    if show_vol:
                        # Color volume bars based on price change
                        colors = ['green' if (row['Open'] - row['Close']) >= 0 else 'red' for index, row in df.iterrows()]
                        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='Volume', marker_color='grey'), row=2, col=1)
                        fig.update_layout(height=600) 
                    else:
                        fig.update_layout(height=500)

                    # Common Layout Updates
                    fig.update_layout(xaxis_rangeslider_visible=False, showlegend=True)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # 3. Automated Interpretation
                    st.subheader("🤖 AI Analysis & Interpretation")
                    st.info(generate_interpretation(df, tab_name))
                    
                    with st.expander("View Raw Data"):
                        st.dataframe(df)
                else:
                    st.error("Data not available. Please check the ticker symbol.")
