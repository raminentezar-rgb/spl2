#!/usr/bin/env python
"""
دانلود داده‌های تاریخی از متاتریدر 5
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import pandas as pd
import MetaTrader5 as mt5
from datetime import datetime, timedelta
from src.utils.logger import setup_logger
from src.utils.helpers import load_config

logger = setup_logger(__name__)

def download_historical_data(symbol: str, timeframe: str, days: int = 30):
    """
    دانلود داده‌های تاریخی
    """
    config = load_config()
    
    # اتصال به متاتریدر
    if not mt5.initialize():
        logger.error("MT5 initialization failed")
        return
    
    try:
        # نقشه تایم‌فریم
        timeframe_map = {
            'M1': mt5.TIMEFRAME_M1,
            'M5': mt5.TIMEFRAME_M5,
            'M15': mt5.TIMEFRAME_M15,
            'M30': mt5.TIMEFRAME_M30,
            'H1': mt5.TIMEFRAME_H1,
            'H4': mt5.TIMEFRAME_H4,
            'D1': mt5.TIMEFRAME_D1
        }
        
        tf = timeframe_map.get(timeframe, mt5.TIMEFRAME_M5)
        
        # محاسبه تاریخ
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        logger.info(f"Downloading {symbol} {timeframe} from {start_date} to {end_date}")
        
        # دریافت داده
        rates = mt5.copy_rates_range(symbol, tf, start_date, end_date)
        
        if rates is None or len(rates) == 0:
            logger.error("No data received")
            return
        
        # تبدیل به دیتافریم
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        
        # ایجاد پوشه
        output_dir = Path(f"data/historical/{symbol}/{timeframe}")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # ذخیره فایل
        filename = f"{symbol}_{timeframe}_{start_date.date()}_{end_date.date()}.csv"
        filepath = output_dir / filename
        
        df.to_csv(filepath)
        logger.info(f"Data saved to {filepath}")
        logger.info(f"Total bars: {len(df)}")
        
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        mt5.shutdown()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbol', type=str, default='XAUUSD')
    parser.add_argument('--timeframe', type=str, default='M5')
    parser.add_argument('--days', type=int, default=60)
    
    args = parser.parse_args()
    
    download_historical_data(args.symbol, args.timeframe, args.days)