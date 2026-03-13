"""
تشخیص پولبک (اصلاح) به میانگین متحرک
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional
from ..utils.logger import get_logger
from ..indicators.moving_averages import MovingAverage

logger = get_logger(__name__)

class PullbackFinder:
    """
    شناسایی پولبک‌ها به میانگین متحرک
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.ma_period = config.get('strategy', {}).get('ma_period', 60)
        self.ma = MovingAverage(self.ma_period)
        self.pullback_threshold = config.get('strategy', {}).get('pullback_threshold', 0.002)  # 0.2%
        
    def find(self, data: pd.DataFrame) -> Dict:
        """
        یافتن پولبک در داده‌ها
        
        Args:
            data: دیتافریم با OHLC داده‌ها
            
        Returns:
            Dict: اطلاعات پولبک
        """
        try:
            if len(data) < self.ma_period + 5:
                return {
                    'is_pullback': False,
                    'pullback_type': 'none',
                    'distance_to_ma': None,
                    'ma_value': None
                }
            
            # محاسبه میانگین متحرک
            ma_values = self.ma.calculate(data)
            current_ma = ma_values.iloc[-1]
            last_price = data['close'].iloc[-1]
            
            # فاصله تا میانگین متحرک
            distance = abs(last_price - current_ma) / current_ma
            
            # تشخیص نوع پولبک
            if distance < self.pullback_threshold:
                # نزدیک به میانگین متحرک
                
                # تشخیص جهت
                if last_price > current_ma:
                    pullback_type = 'bullish'  # قیمت بالای MA (اصلاح نزولی به MA)
                else:
                    pullback_type = 'bearish'  # قیمت پایین MA (اصلاح صعودی به MA)
                
                # بررسی واگرایی
                divergence = self._check_divergence(data, ma_values)
                
                return {
                    'is_pullback': True,
                    'pullback_type': pullback_type,
                    'distance_to_ma': distance,
                    'ma_value': current_ma,
                    'price': last_price,
                    'divergence': divergence,
                    'confidence': 1 - (distance / self.pullback_threshold)
                }
            
            return {
                'is_pullback': False,
                'pullback_type': 'none',
                'distance_to_ma': distance,
                'ma_value': current_ma,
                'price': last_price,
                'confidence': 0
            }
            
        except Exception as e:
            logger.error(f"Error in pullback finding: {e}")
            return {
                'is_pullback': False,
                'pullback_type': 'none',
                'distance_to_ma': None,
                'ma_value': None
            }
    
    def _check_divergence(self, data: pd.DataFrame, ma_values: pd.Series) -> Dict:
        """
        بررسی واگرایی بین قیمت و میانگین متحرک
        """
        try:
            if len(data) < 10:
                return {'has_divergence': False}
            
            # قیمت‌های اخیر
            recent_prices = data['close'].values[-10:]
            recent_ma = ma_values.values[-10:]
            
            # روند قیمت
            price_trend = recent_prices[-1] > recent_prices[0]
            
            # روند MA
            ma_trend = recent_ma[-1] > recent_ma[0]
            
            # واگرایی وقتی روندها مخالف هم باشن
            divergence = price_trend != ma_trend
            
            return {
                'has_divergence': divergence,
                'price_trend': 'up' if price_trend else 'down',
                'ma_trend': 'up' if ma_trend else 'down',
                'strength': abs(recent_prices[-1] - recent_ma[-1]) / recent_ma[-1]
            }
            
        except Exception as e:
            logger.error(f"Error in divergence check: {e}")
            return {'has_divergence': False}