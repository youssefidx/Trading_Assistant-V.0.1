#!/usr/bin/env python3
"""
🚀 NAS100 Pro Trading Assistant (Complete Edition)
"""

import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import smtplib
import requests
from datetime import datetime
from email.message import EmailMessage

# ======================
# CORE FUNCTIONALITY
# ======================

class TradingAssistant:
    def __init__(self):
        self.conn = sqlite3.connect('trading_db.sqlite')
        self._init_db()
        
    def _init_db(self):
        """Initialize database structure"""
        self.conn.execute('''CREATE TABLE IF NOT EXISTS positions
                          (timestamp DATETIME, asset TEXT, 
                           quantity REAL, entry_price REAL)''')
        self.conn.execute('''CREATE TABLE IF NOT EXISTS audit_log
                          (timestamp DATETIME, action TEXT, details TEXT)''')
    
    def detect_levels(self, df):
        """Advanced support/resistance detection"""
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
            st.error(f"Level detection error: {str(e)}")
            return [], []

    def fetch_live_data(self):
        """Secure live data fetching"""
        try:
            api_key = st.secrets["alpha_vantage"]["api_key"]
            url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=NDX&interval=5min&apikey={api_key}"
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

    def send_alert(self, receiver, message):
        """Email notification system"""
        try:
            msg = EmailMessage()
            msg.set_content(f"Trading Alert:\n{message}")
            msg['Subject'] = "🚨 NAS100 Trading Alert"
            msg['From'] = st.secrets["email"]["sender"]
            msg['To'] = receiver
            
            with smtplib.SMTP_SSL(st.secrets["email"]["smtp_server"], 
                                st.secrets["email"]["port"]) as server:
                server.login(st.secrets["email"]["sender"], 
                            st.secrets["email"]["password"])
                server.send_message(msg)
            st.success("Alert sent successfully!")
        except Exception as e:
            st.error(f"Email error: {str(e)}")

# ======================
# STREAMLIT INTERFACE
# ======================

def main():
    st.set_page_config(
        page_title="NAS100 Trading Assistant",
        layout="wide",
        page_icon="📊"
    )
    
    st.title("📊 NAS100 Pro Trading Assistant")
    assistant = TradingAssistant()
    
    # ======================
    # DATA INPUT SECTION
    # ======================
    with st.expander("📥 Data Input", expanded=True):
        col1, col2 = st.columns([2, 1])
        
        with col1:
            uploaded_file = st.file_uploader("Upload Historical Data", 
                                            type=["csv"],
                                            help="CSV with DateTime, Open, High, Low, Close, Volume")
            
        with col2:
            if st.button("🔄 Fetch Live Data", help="Get real-time NAS100 data"):
                with st.spinner("Fetching live prices..."):
                    live_data = assistant.fetch_live_data()
                    if live_data is not None:
                        st.session_state.df = live_data.reset_index()
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
                df = df.set_index(pd.to_datetime(df[dt_col]))[['Open', 'High', 'Low', 'Close', 'Volume']]
                st.session_state.df = df.ffill()
            else:
                st.error("DateTime column not found in uploaded file")
                
        except Exception as e:
            st.error(f"CSV Error: {str(e)}")
    
    elif 'df' in st.session_state:
        df = st.session_state.df

    # ======================
    # ANALYSIS & TRADING
    # ======================
    if df is not None:
        try:
            # Support/Resistance Analysis
            support, resistance = assistant.detect_levels(df)
            
            # Results Display
            st.success(f"✅ Identified {len(support)} support & {len(resistance)} resistance levels")
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Key Support Levels")
                st.dataframe(pd.Series(support, name='Price').to_frame(), height=150)
                
            with col2:
                st.subheader("Key Resistance Levels")
                st.dataframe(pd.Series(resistance, name='Price').to_frame(), height=150)
            
            # Price Visualization
            st.subheader("Price Analysis")
            st.line_chart(df[['Close']])
            
            # Alert System
            with st.expander("🔔 Alert Configuration"):
                email = st.text_input("Notification Email")
                if st.button("Set Price Alerts"):
                    assistant.send_alert(email, 
                        f"New levels detected:\nSupport: {support}\nResistance: {resistance}")
            
            # Portfolio Management
            with st.expander("💰 Portfolio Management"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Current Positions")
                    positions = pd.read_sql("SELECT * FROM positions", assistant.conn)
                    st.dataframe(positions.style.highlight_max(subset=['quantity'], color='lightgreen'))
                    
                with col2:
                    st.subheader("New Trade")
                    trade_qty = st.number_input("Shares", 1, 1000, 100)
                    trade_price = st.number_input("Price", value=df['Close'].iloc[-1])
                    
                    if st.button("📈 Execute Buy Order"):
                        assistant.conn.execute('''
                            INSERT INTO positions VALUES (?,?,?,?)
                        ''', (datetime.now(), "NAS100", trade_qty, trade_price))
                        assistant.conn.commit()
                        st.success("Trade executed successfully!")

        except Exception as e:
            st.error(f"Analysis error: {str(e)}")

    # ======================
    # SAMPLE DATA & HELP
    # ======================
    with st.expander("💡 Getting Started"):
        st.markdown("""
        **Sample Data Format:**
        ```csv
        DateTime,Open,High,Low,Close,Volume
        2024-01-01 09:30:00,18000.50,18050.75,17995.25,18025.00,5000
        ```
        """)
        
        sample = pd.DataFrame({
            'DateTime': pd.date_range('2024-01-01', periods=100, freq='15T'),
            'Open': np.round(np.linspace(18000, 18200, 100), 2),
            'High': np.round(np.linspace(18050, 18250, 100), 2),
            'Low': np.round(np.linspace(17950, 18150, 100), 2),
            'Close': np.round(np.linspace(18000, 18200, 100), 2),
            'Volume': np.random.randint(1000, 10000, 100)
        })
        
        st.download_button(
            "⬇️ Download Sample Data",
            sample.to_csv(index=False),
            "nas100_sample.csv"
        )

if __name__ == "__main__":
    main()
