"""
محاسبه میانگین‌های متحرک
"""
import pandas as pd
import numpy as np
from typing import Union, Optional
from ..utils.logger import get_logger

logger = get_logger(__name__)

class MovingAverage:
    """
    کلاس محاسبه انواع میانگین متحرک
    """
    
    def __init__(self, period: int = 60, ma_type: str = 'sma'):
        """
        Args:
            period: دوره میانگین متحرک
            ma_type: نوع میانگین متحرک ('sma', 'ema', 'wma')
        """
        self.period = period
        self.ma_type = ma_type
        
    def calculate(self, data: pd.DataFrame, price_col: str = 'close') -> pd.Series:
        """
        محاسبه میانگین متحرک
        
        Args:
            data: دیتافریم قیمت
            price_col: ستون قیمت برای محاسبه
            
        Returns:
            pd.Series: مقادیر میانگین متحرک
        """
        try:
            prices = data[price_col]
            
            if self.ma_type == 'sma':
                return prices.rolling(window=self.period).mean()
            elif self.ma_type == 'ema':
                return prices.ewm(span=self.period, adjust=False).mean()
            elif self.ma_type == 'wma':
                return self._weighted_ma(prices)
            else:
                logger.warning(f"Unknown MA type: {self.ma_type}, using SMA")
                return prices.rolling(window=self.period).mean()
                
        except Exception as e:
            logger.error(f"Error calculating MA: {e}")
            return pd.Series(index=data.index, dtype=float)
    
    def _weighted_ma(self, prices: pd.Series) -> pd.Series:
        """
        محاسبه میانگین متحرک وزنی
        """
        weights = np.arange(1, self.period + 1)
        weights = weights / weights.sum()
        
        def weighted_mean(x):
            return np.sum(x * weights[-len(x):]) if len(x) == self.period else np.nan
        
        return prices.rolling(window=self.period).apply(weighted_mean)
    
    def get_signal(self, data: pd.DataFrame, fast_ma: Optional['MovingAverage'] = None) -> str:
        """
        دریافت سیگنال بر اساس میانگین متحرک
        
        Args:
            data: دیتافریم قیمت
            fast_ma: میانگین متحرک سریع‌تر برای تشخیص تقاطع
            
        Returns:
            str: سیگنال ('buy', 'sell', 'neutral')
        """
        try:
            ma_slow = self.calculate(data)
            
            if fast_ma:
                ma_fast = fast_ma.calculate(data)
                
                # تقاطع طلایی (خرید)
                if (ma_fast.iloc[-2] <= ma_slow.iloc[-2] and 
                    ma_fast.iloc[-1] > ma_slow.iloc[-1]):
                    return 'buy'
                
                # تقاطع مرگ (فروش)
                elif (ma_fast.iloc[-2] >= ma_slow.iloc[-2] and 
                      ma_fast.iloc[-1] < ma_slow.iloc[-1]):
                    return 'sell'
            
            # قیمت نسبت به میانگین متحرک
            last_price = data['close'].iloc[-1]
            last_ma = ma_slow.iloc[-1]
            
            if last_price > last_ma * 1.01:  # 1% بالاتر
                return 'bullish'
            elif last_price < last_ma * 0.99:  # 1% پایین‌تر
                return 'bearish'
            
            return 'neutral'
            
        except Exception as e:
            logger.error(f"Error getting MA signal: {e}")
            return 'neutral'