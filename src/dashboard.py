"""
Streamlit Dashboard for SP2L Trading Robot
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import time
import os
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

# اضافه کردن مسیر پروژه به PYTHONPATH برای حل مشکل ModuleNotFoundError
sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml

from src.mt5_connector.connector import MT5Connector
from src.core.strategy import SP2LStrategy
from src.utils.helpers import load_config
from src.utils.yfinance_connector import YahooFinanceConnector

# پیکربندی صفحه
st.set_page_config(
    page_title="SP2L Trading Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# بارگذاری تنظیمات
@st.cache_data(ttl=600)
def get_config():
    return load_config("config.yaml")

# تابع کش شده برای تحلیل (برای جلوگیری از تکرار محاسبات سنگین)
@st.cache_data(ttl=30)
def cached_analysis(symbol, timeframe, _connector, _strategy):
    data = _connector.get_rates(symbol, timeframe, count=200)
    if data is not None:
        return _strategy.analyze(data), data
    return None, None

config = get_config()

# استایل‌دهی
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
        color: #ffffff;
    }
    .stMetric {
        background-color: #1e2130;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #3e4250;
    }
    </style>
    """, unsafe_allow_html=True)

# سایدبار
st.sidebar.title("🛠️ Control Panel")
data_source = st.sidebar.radio("Data Source", ["Yahoo Finance", "MetaTrader 5"])
symbols = config['trading'].get('symbols', [config['trading'].get('symbol', 'XAUUSD')])
symbol = st.sidebar.selectbox("Symbol", symbols)
timeframe = st.sidebar.selectbox("Timeframe", ["M1", "M5", "M15", "M30", "H1", "H4", "D1"], index=1)
update_interval = st.sidebar.slider("Update Interval (sec)", 5, 60, 30)

# مقداردهی اولیه کانکتورها
if 'mt5' not in st.session_state:
    st.session_state.mt5 = MT5Connector(config)
    st.session_state.mt5.connect()
if 'yahoo' not in st.session_state:
    st.session_state.yahoo = YahooFinanceConnector()

# انتخاب کانکتور فعلی
connector = st.session_state.mt5 if data_source == "MetaTrader 5" else st.session_state.yahoo

# هدر اصلی
st.title("🚀 SP2L Signal Robot")

# تعریف تب‌ها
tab1, tab2 = st.tabs(["📊 Live Trading", "📰 Market News"])

with tab1:
    st.subheader(f"Data: {data_source} | Symbol: {symbol} ({timeframe})")

# اگر متاتریدر انتخاب شده، اطلاعات حساب را نشان بده
if data_source == "MetaTrader 5":
    col1, col2, col3, col4 = st.columns(4)
    account_info = connector.get_account_info()
    if account_info:
        col1.metric("Balance", f"${account_info['balance']:.2f}")
        col2.metric("Equity", f"${account_info['equity']:.2f}")
        col3.metric("Free Margin", f"${account_info['free_margin']:.2f}")
        profit_color = "normal" if account_info['profit'] >= 0 else "inverse"
        col4.metric("Live Profit", f"${account_info['profit']:.2f}", delta_color=profit_color)
    else:
        st.warning("⚠️ MT5 disconnected. Showing market data only.")
else:
    st.info("💡 Running in Signal-Only Mode using Yahoo Finance (No Account Connection Required)")

# بخش خلاصه سیگنال‌ها (بهینه شده با اجرای موازی)
st.markdown("### 📊 Market Overview & Signals")
summary_cols = st.columns(len(symbols))
strategy = SP2LStrategy(config)

def process_symbol_summary(s, connector):
    # دریافت داده با تعداد کمتر برای سرعت بیشتر در خلاصه
    s_data = connector.get_rates(s, timeframe, count=70)
    if s_data is not None:
        s_analysis = strategy.analyze(s_data)
        return s, s_analysis['signal']['type']
    return s, 'neutral'

# اجرای موازی برای تمام نمادها
with ThreadPoolExecutor(max_workers=min(len(symbols), 8)) as executor:
    # ارسال کانکتور به تابع برای جلوگیری از مشکلات threading در دسترسی به session_state
    results = list(executor.map(lambda s: process_symbol_summary(s, connector), symbols))

for i, (s, sig_type) in enumerate(results):
    with summary_cols[i]:
        if sig_type == 'buy':
            st.markdown(f"**{s}**\n🟢 BUY")
        elif sig_type == 'sell':
            st.markdown(f"**{s}**\n🔴 SELL")
        else:
            st.markdown(f"**{s}**\n⚪ Neutral")

# دریافت داده اصلی برای نماد انتخابی (با استفاده از کش برای سرعت)
analysis, data = cached_analysis(symbol, timeframe, connector, strategy)

if data is not None:
    # نمودار شمعی
    fig = go.Figure(data=[go.Candlestick(x=data.index,
                    open=data['open'],
                    high=data['high'],
                    low=data['low'],
                    close=data['close'],
                    name="Market Data")])
    
    # اضافه کردن میانگین متحرک
    ma_period = config['strategy'].get('ma_period', 60)
    ma_values = data['close'].rolling(window=ma_period).mean()
    fig.add_trace(go.Scatter(x=data.index, y=ma_values, line=dict(color='yellow', width=1.5), name=f"EMA {ma_period}"))
    
    # نمایش سیگنال فعلی
    signal = analysis['signal']
    if signal['type'] != 'neutral':
        st.sidebar.success(f"🔥 ACTIVE SIGNAL: {signal['type'].upper()} @ {signal['entry']:.5f}")
        
        # علامت‌گذاری روی نمودار
        color = "green" if signal['type'] == 'buy' else "red"
        symbol_marker = "triangle-up" if signal['type'] == 'buy' else "triangle-down"
        
        fig.add_trace(go.Scatter(
            x=[data.index[-1]],
            y=[signal['entry']],
            mode="markers",
            marker=dict(symbol=symbol_marker, size=15, color=color, line=dict(width=2, color="white")),
            name=f"Signal: {signal['type'].upper()}"
        ))
        
        # خطوط SL و TP
        fig.add_hline(y=signal['sl'], line_dash="dash", line_color="red", annotation_text="SL")
        fig.add_hline(y=signal['tp'], line_dash="dash", line_color="green", annotation_text="TP")

    fig.update_layout(
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        height=600,
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # نمایش پوزیشن‌ها (فقط برای متاتریدر)
if data_source == "MetaTrader 5":
    st.markdown("---")
    st.subheader("💼 Active Positions")
    positions = connector.get_positions(symbol)
    if positions:
        df_pos = pd.DataFrame(positions)
        st.dataframe(df_pos, use_container_width=True)
    else:
        st.info("No active positions.")
    with st.expander("🔍 Strategy Technical Details"):
        st.write(analysis)

with tab2:
    st.header("📰 Top Market News")
    
    yahoo_conn = st.session_state.yahoo
    
    # دریافت اخبار برای تمام ارزها به صورت موازی
    def fetch_symbol_news(s, connector):
        return s, connector.get_news(s)
    
    with ThreadPoolExecutor(max_workers=min(len(symbols), 8)) as executor:
        # استفاده از lambda یا functools.partial برای پاس دادن کانکتور
        news_results = list(executor.map(lambda s: fetch_symbol_news(s, yahoo_conn), symbols))
    
    for s, news_items in news_results:
        with st.expander(f"News for {s} ({len(news_items)} items)"):
            if not news_items:
                st.write("No recent news found.")
            for item in news_items:
                st.markdown(f"### [{item.get('title')}]({item.get('link')})")
                st.caption(f"Source: {item.get('publisher')} | Type: {item.get('type')}")
                # اگر تصویر داشت (بعضی خبرها دارن)
                if item.get('thumbnail') and item['thumbnail'].get('resolutions'):
                    st.image(item['thumbnail']['resolutions'][0]['url'], width=200)
                st.divider()

# رفرش خودکار
time.sleep(update_interval)
st.rerun()
