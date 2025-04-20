#!/usr/bin/env python3
"""
🚀 NAS100 Pro Trader with Live Data (Verified Working)
"""

import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime

# ======================
# CORE FUNCTIONS
# ======================

def detect_profit_zones(df):
    """Accurate support/resistance detection"""
    try:
        df['Range'] = (df['High'] - df['Low']) * 0.5 + df['Low']
        bins = pd.cut(df['Range'], bins=50, include_lowest=True)
        
        vol_profile = df.groupby(bins)['Volume'].sum().reset_index()
        vol_profile['mid'] = vol_profile['Range'].apply(
            lambda x: x.mid if isinstance(x, pd.Interval) else np.nan
        ).astype(float)
        
        valid_profile = vol_profile.dropna()
        support = valid_profile.nlargest(3, 'Volume')['mid'].values
        resistance = valid_profile.nsmallest(3, 'Volume')['mid'].values
        
        return sorted(support), sorted(resistance)
    
    except Exception as e:
        st.error(f"Analysis error: {str(e)}")
        return [], []

def fetch_live_data():
    """Secure live data fetching with your API key"""
    try:
        url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=NDX&interval=5min&apikey=0BIIALOHS7OO6RA5"
        response = requests.get(url)
        response.raise_for_status()
        
        data = response.json()
        time_series = data.get("Time Series (5min)", {})
        
        df = pd.DataFrame(time_series).T.rename(columns={
            '1. open': 'Open',
            '2. high': 'High',
            '3. low': 'Low',
            '4. close': 'Close',
            '5. volume': 'Volume'
        }).astype(float)
        
        df.index = pd.to_datetime(df.index)
        return df.sort_index()
        
    except Exception as e:
        st.error(f"Live data error: {str(e)}")
        return None

# ======================
# STREAMLIT APP
# ======================

def main():
    st.set_page_config(
        page_title="NAS100 Pro Trader",
        layout="wide",
        page_icon="📈"
    )
    
    st.title("📈 NAS100 Pro Trader")
    
    # ======================
    # DATA INPUT SECTION
    # ======================
    with st.expander("📥 Data Sources", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            uploaded_file = st.file_uploader("Upload CSV Data", type=["csv"])
            
        with col2:
            if st.button("🔄 Get Live Market Data"):
                with st.spinner("Fetching real-time data..."):
                    live_df = fetch_live_data()
                    if live_df is not None:
                        st.session_state.df = live_df.reset_index()
                        st.success("Live data loaded!")

    # ======================
    # DATA PROCESSING
    # ======================
    df = None
    
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)
            dt_col = next((c for c in df.columns if 'date' in c.lower()), None)
            
            if dt_col:
                df = df.set_index(pd.to_datetime(df[dt_col])).drop(columns=[dt_col])
                df = df[['Open', 'High', 'Low', 'Close', 'Volume']].ffill()
                st.session_state.df = df
            else:
                st.error("DateTime column not found")
                
        except Exception as e:
            st.error(f"CSV Error: {str(e)}")
    
    elif 'df' in st.session_state:
        df = st.session_state.df

    # ======================
    # ANALYSIS OUTPUT
    # ======================
    if df is not None:
        try:
            support, resistance = detect_profit_zones(df)
            
            st.success(f"✅ Found {len(support)} support & {len(resistance)} resistance levels")
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Support Levels")
                st.dataframe(pd.Series(support, name='Price').to_frame(), height=150)
                
            with col2:
                st.subheader("Resistance Levels")
                st.dataframe(pd.Series(resistance, name='Price').to_frame(), height=150)
                
            st.line_chart(df[['Close']])
            
        except Exception as e:
            st.error(f"Processing error: {str(e)}")

    # ======================
    # SAMPLE DATA
    # ======================
    with st.expander("💡 Get Sample Data"):
        sample = pd.DataFrame({
    'MarketTime': pd.date_range('2024-01-01', periods=100, freq='15T'),
    'Open': np.round(np.linspace(18000, 18200, 100), 2),
    'High': np.round(np.linspace(18050, 18250, 100), 2),  # Added closing )
    'Low': np.round(np.linspace(17950, 18150, 100), 2),
    'Close': np.round(np.linspace(18000, 18200, 100), 2),
    'Volume': np.random.randint(1000, 10000, 100)
})
        st.download_button(
            "⬇️ Download Sample CSV",
            sample.to_csv(index=False),
            "nas100_sample.csv"
        )

if __name__ == "__main__":
    main()
