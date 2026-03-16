"""
اندیکاتورهای تشخیص روند و قدرت روند
"""
import pandas as pd
import numpy as np

class ADXIndicator:
    """
    محاسبه Average Directional Index (ADX)
    بدون نیاز به کتابخانه‌های خارجی برای سازگاری کامل
    """
    def __init__(self, period: int = 14):
        self.period = period

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        """
        محاسبه ADX, +DI, -DI
        """
        try:
            high = data['high']
            low = data['low']
            close = data['close']
            
            plus_dm = high.diff()
            minus_dm = low.diff()
            
            plus_dm[plus_dm < 0] = 0
            minus_dm[minus_dm > 0] = 0
            minus_dm = abs(minus_dm)
            
            # True Range
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            
            # Smoothing (Wilder's Smoothing)
            atr = tr.rolling(window=self.period).mean() # ساده شده برای شروع
            plus_di = 100 * (plus_dm.rolling(window=self.period).mean() / atr)
            minus_di = 100 * (minus_dm.rolling(window=self.period).mean() / atr)
            
            dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
            adx = dx.rolling(window=self.period).mean()
            
            return adx
        except Exception as e:
            return pd.Series(index=data.index, data=0)

class MovingAverageTrend:
    """
    تشخیص جهت روند بر اساس چندین میانگین متحرک
    """
    def __init__(self, fast_period: int = 20, slow_period: int = 50):
        self.fast_period = fast_period
        self.slow_period = slow_period

    def get_trend_status(self, data: pd.DataFrame) -> str:
        fast_ma = data['close'].rolling(window=self.fast_period).mean()
        slow_ma = data['close'].rolling(window=self.slow_period).mean()
        
        last_fast = fast_ma.iloc[-1]
        last_slow = slow_ma.iloc[-1]
        
        if last_fast > last_slow:
            return "bullish"
        elif last_fast < last_slow:
            return "bearish"
        else:
            return "neutral"

class RSIIndicator:
    """
    محاسبه شاخص قدرت نسبی (RSI)
    """
    def __init__(self, period: int = 14):
        self.period = period

    def calculate(self, data: pd.DataFrame) -> pd.Series:
        delta = data['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.period).mean()
        
        rs = gain / loss
        return 100 - (100 / (1 + rs))

class DivergenceDetector:
    """
    تشخیص واگرایی بین قیمت و اندیکاتور (مثلاً RSI)
    یکی از حرفه‌ای‌ترین تاییدورهای بازگشت روند
    """
    def __init__(self, rsi_period: int = 14):
        self.rsi = RSIIndicator(rsi_period)

    def detect(self, data: pd.DataFrame) -> Dict:
        """
        Returns: { 'bullish_div': bool, 'bearish_div': bool }
        """
        if len(data) < 30:
            return {'bullish_div': False, 'bearish_div': False}
            
        rsi_vals = self.rsi.calculate(data)
        close = data['close']
        
        # ساده شده: مقایسه کف/سقف فعلی با قبلی (در بازه ۲۰ کندل اخیر)
        # واگرایی مثبت (صعودی): قیمت کف پایین‌تر، RSI کف بالاتر
        curr_price_low = close.iloc[-1]
        prev_price_low = close.iloc[-20:-5].min()
        
        curr_rsi_low = rsi_vals.iloc[-1]
        prev_rsi_low = rsi_vals.iloc[-20:-5].min()
        
        bull_div = curr_price_low < prev_price_low and curr_rsi_low > prev_rsi_low
        
        # واگرایی منفی (نزولی): قیمت سقف بالاتر، RSI سقف پایین‌تر
        curr_price_high = close.iloc[-1]
        prev_price_high = close.iloc[-20:-5].max()
        
        curr_rsi_high = rsi_vals.iloc[-1]
        prev_rsi_high = rsi_vals.iloc[-20:-5].max()
        
        bear_div = curr_price_high > prev_price_high and curr_rsi_high < prev_rsi_high
        
        return {'bullish_div': bull_div, 'bearish_div': bear_div}
