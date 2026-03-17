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
        یافتن پولبک در داده‌ها (Al Brooks Style)
        تریگر: شکستن سقف/کف کندل قبلی
        """
        try:
            if len(data) < 2:
                return {'is_pullback': False, 'pullback_type': 'none'}
            
            last_low = data['low'].iloc[-1]
            prev_low = data['low'].iloc[-2]
            last_high = data['high'].iloc[-1]
            prev_high = data['high'].iloc[-2]
            
            # تشخیص پولبک بر اساس شکست کندل قبلی
            is_bullish_pb = last_low < prev_low  # پولبک در حرکت صعودی (شکست کف قبلی)
            is_bearish_pb = last_high > prev_high # پولبک در حرکت نزولی (شکست سقف قبلی)
            
            if is_bullish_pb:
                return {
                    'is_pullback': True,
                    'pullback_type': 'bullish',
                    'trigger_price': last_low,
                    'prev_low': prev_low
                }
            elif is_bearish_pb:
                return {
                    'is_pullback': True,
                    'pullback_type': 'bearish',
                    'trigger_price': last_high,
                    'prev_high': prev_high
                }
            
            return {
                'is_pullback': False,
                'pullback_type': 'none'
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