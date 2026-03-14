"""
دریافت داده‌های زنده از یاهو فایننس
"""
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from .logger import setup_logger

class YahooFinanceConnector:
    """
    جایگزین متاتریدر برای دریافت داده‌های رایگان و بدون نیاز به لاگین
    """
    
    def __init__(self):
        self.logger = setup_logger(__name__)
        # مپ کردن نمادهای متاتریدر به یاهو
        self.symbol_map = {
            'XAUUSD': 'GC=F',    # Gold Futures
            'XAGUSD': 'SI=F',    # Silver Futures
            'BTCUSD': 'BTC-USD', # Bitcoin
            'ETHUSD': 'ETH-USD', # Ethereum
        }

    def get_rates(self, symbol: str, timeframe: str, count: int = 100) -> pd.DataFrame:
        """
        دریافت داده‌های او‌اچ‌ال‌سی
        """
        try:
            # ۱. ترجمه نماد
            yf_symbol = self.symbol_map.get(symbol)
            
            # اگر در مپ نبود و شبیه فارکس بود (6 حرفی)، =X اضافه کن
            if not yf_symbol:
                if len(symbol) == 6 and not symbol.startswith('X'):
                    yf_symbol = f"{symbol}=X"
                else:
                    yf_symbol = symbol
            
            # تبدیل تایم‌فریم متاتریدر به یاهو
            interval_map = {
                'M1': '1m',
                'M5': '5m',
                'M15': '15m',
                'H1': '1h',
                'D1': '1d'
            }
            interval = interval_map.get(timeframe, '5m')
            
            # دریافت داده‌ها
            ticker = yf.Ticker(yf_symbol)
            # یاهو برای دقایق پایین فقط داده‌های اخیر را می‌دهد (مثلاً ۱ دقیقه فقط ۷ روز اخیر)
            df = ticker.history(period='5d', interval=interval)
            
            if df.empty:
                self.logger.warning(f"No Yahoo Finance data for {yf_symbol}")
                return None
                
            # فرمت کردن ستون‌ها مشابه متاتریدر
            df = df.rename(columns={
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'tick_volume' # یاهو حجم دقیق اسپات طلا را ندارد اما برای تحلیل کافیست
            })
            
            # برگرداندن آخرین N کندل
            return df.tail(count)
            
        except Exception as e:
            self.logger.error(f"Error fetching from Yahoo Finance: {e}")
            return None

    def get_news(self, symbol: str) -> list:
        """
        دریافت آخرین اخبار مربوط به نماد
        """
        try:
            yf_symbol = self.symbol_map.get(symbol, symbol)
            ticker = yf.Ticker(yf_symbol)
            news = ticker.news
            return news if news else []
        except Exception as e:
            self.logger.error(f"Error fetching news for {symbol}: {e}")
            return []
