import os
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import yaml
import sys

# افزودن مسیر اصلی پروژه برای ایمپورت‌ها
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.strategy import SP2LStrategy
from src.utils.yfinance_connector import YahooFinanceConnector

def run_recent_backtest():
    # ۱. بارگذاری تنظیمات
    with open('config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    strategy = SP2LStrategy(config)
    connector = YahooFinanceConnector()
    
    symbols = config['trading']['symbols']
    timeframes = config['trading']['timeframes']
    
    results = []
    
    print("🚀 Starting Recent Performance Backtest (Last 7 Days)...")
    print("========================================================")
    
    for symbol in symbols:
        print(f"📊 Analyzing {symbol}...")
        
        # دریافت دیتای تمام تایم‌فریم‌ها برای MTF Alignment
        tf_data = {}
        for tf in ["M1", "M5", "M15", "H1", "H4", "D1"]:
            data = connector.get_rates(symbol, tf, count=1000)
            if data is not None and not data.empty:
                tf_data[tf] = data
        
        if "M5" not in tf_data or "H1" not in tf_data:
            print(f"⚠️ Missing data for {symbol}, skipping.")
            continue
            
        # شبیه‌سازی روی تایم‌فریم M5 (به عنوان تایم‌فریم اصلی سیگنال)
        m5_df = tf_data["M5"]
        
        for i in range(50, len(m5_df)):
            current_slice = m5_df.iloc[:i+1]
            current_time = current_slice.index[-1]
            
            # تحلیل استراتژی
            analysis = strategy.analyze(current_slice)
            signal = analysis.get('signal', {})
            
            if signal.get('type') in ['buy', 'sell']:
                # بررسی MTF Alignment (ساده شده برای بک‌تست)
                # در اینجا فرض می‌کنیم اگر روند H1 و H4 همسو باشد، معامله انجام می‌شود
                h1_dir = _get_trend_at_time(tf_data.get("H1"), current_time)
                h4_dir = _get_trend_at_time(tf_data.get("H4"), current_time)
                
                signal_type = signal['type']
                trend_match = False
                
                if signal_type == 'buy' and h1_dir == 'bullish' and h4_dir == 'bullish':
                    trend_match = True
                elif signal_type == 'sell' and h1_dir == 'bearish' and h4_dir == 'bearish':
                    trend_match = True
                
                if trend_match:
                    # ثبت معامله و بررسی نتیجه (بر اساس قیمت‌های بعدی)
                    # برای سادگی، اگر قیمت در ۳۰ کندل بعدی به TP رسید = Win، اگر به SL رسید = Loss
                    outcome = _evaluate_trade(m5_df.iloc[i+1:], signal)
                    results.append({
                        'symbol': symbol,
                        'time': current_time,
                        'type': signal_type,
                        'entry': signal['entry'],
                        'sl': signal['sl'],
                        'tp': signal['tp'],
                        'outcome': outcome
                    })

    # نمایش نتایج
    _print_summary(results, config)

def _get_trend_at_time(df, timestamp):
    if df is None or df.empty: return 'neutral'
    # پیدا کردن آخرین کندل قبل از زمان مورد نظر
    idx = df.index.get_indexer([timestamp], method='pad')[0]
    if idx <= 10: return 'neutral'
    
    # متد ساده تشخیص روند: اگر Close > MA20 باشد
    ma = df['close'].rolling(20).mean()
    if df['close'].iloc[idx] > ma.iloc[idx]: return 'bullish'
    if df['close'].iloc[idx] < ma.iloc[idx]: return 'bearish'
    return 'neutral'

def _evaluate_trade(future_data, signal):
    if future_data.empty: return 'Pending'
    tp = signal['tp']
    sl = signal['sl']
    
    for _, row in future_data.iterrows():
        if signal['type'] == 'buy':
            if row['high'] >= tp: return 'Win'
            if row['low'] <= sl: return 'Loss'
        else:
            if row['low'] <= tp: return 'Win'
            if row['high'] >= sl: return 'Loss'
    return 'Expired'

def _print_summary(results, config):
    if not results:
        print("❌ No signals found in the last 7 days.")
        return
        
    df = pd.DataFrame(results)
    total = len(df)
    wins = len(df[df['outcome'] == 'Win'])
    losses = len(df[df['outcome'] == 'Loss'])
    win_rate = (wins / (wins + losses)) * 100 if (wins + losses) > 0 else 0
    
    # محاسبه سود و ضرر دلاری
    initial_balance = 1000.0
    current_balance = initial_balance
    volume = config['trading'].get('volume', 0.01)
    
    for _, row in df.iterrows():
        symbol = row['symbol'].upper()
        # اصلاح ضرایب برای واقع‌گرایی بیشتر (Mini lot = 0.01)
        multiplier = 1000 # 0.01 lot of Forex = $1000 position
        if 'XAU' in symbol or 'GOLD' in symbol:
            multiplier = 1 # 0.01 lot Gold = 1 oz
        elif 'BTC' in symbol or 'ETH' in symbol:
            multiplier = 0.01 # 0.01 lot BTC
            
        if row['outcome'] == 'Win':
            price_change = abs(row['tp'] - row['entry'])
            profit = price_change * multiplier
            current_balance += profit
        elif row['outcome'] == 'Loss':
            price_change = abs(row['entry'] - row['sl'])
            loss = price_change * multiplier
            current_balance -= loss
        
        # جلوگیری از منفی شدن مضحک بالانس
        if current_balance < 0:
            current_balance = 0
            break
            
    print("\n" + "="*40)
    print("📊 PROFITABILITY REPORT (Last 7 Days)")
    print("="*40)
    print(f"💰 Initial Balance: ${initial_balance:.2f}")
    print(f"📈 Final Balance:   ${current_balance:.2f}")
    print(f"💵 Net Profit/Loss: ${current_balance - initial_balance:+.2f}")
    print(f"🎯 Win Rate:        {win_rate:.2f}%")
    print(f"✅ Total Trades:    {wins + losses}")
    print("="*40)
    
    # ذخیره در فایل آرتفکت
    with open('backtest_results.txt', 'w', encoding='utf-8') as f:
        f.write(f"Initial: {initial_balance}, Final: {current_balance}\n")
        f.write(df.to_string())

if __name__ == "__main__":
    run_recent_backtest()
