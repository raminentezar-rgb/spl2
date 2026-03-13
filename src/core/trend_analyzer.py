"""
تحلیل روند بازار
"""
import pandas as pd
import numpy as np
from typing import Dict, List
from ..utils.logger import get_logger

logger = get_logger(__name__)

class TrendAnalyzer:
    """
    تحلیل روند و تشخیص سقف‌ها و کف‌ها
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.min_trend_bars = config.get('strategy', {}).get('min_higher_lows', 3)
        
    def analyze(self, data: pd.DataFrame) -> Dict:
        """
        تحلیل روند بازار
        
        Args:
            data: دیتافریم با OHLC داده‌ها
            
        Returns:
            Dict: اطلاعات روند
        """
        try:
            if len(data) < self.min_trend_bars:
                return {
                    'direction': 'neutral',
                    'strength': 0,
                    'higher_lows': 0,
                    'lower_highs': 0
                }
            
            # تشخیص سقف‌ها و کف‌ها
            highs = data['high'].values[-20:]  # 20 کندل آخر
            lows = data['low'].values[-20:]
            
            # شمارش کف‌های بالاتر
            higher_lows = self._count_higher_lows(lows)
            
            # شمارش سقف‌های پایین‌تر
            lower_highs = self._count_lower_highs(highs)
            
            # تعیین جهت روند
            if higher_lows >= self.min_trend_bars and higher_lows > lower_highs:
                direction = 'bullish'
                strength = higher_lows / 5  # نرمالایز شده
            elif lower_highs >= self.min_trend_bars and lower_highs > higher_lows:
                direction = 'bearish'
                strength = lower_highs / 5
            else:
                direction = 'neutral'
                strength = 0
            
            # تشخیص خط روند
            trendline = self._find_trendline(data, direction)
            
            # تشخیص سطوح حمایت و مقاومت
            support_resistance = self._find_support_resistance(data)
            
            return {
                'direction': direction,
                'strength': min(strength, 1.0),
                'higher_lows': higher_lows,
                'lower_highs': lower_highs,
                'trendline': trendline,
                'support_resistance': support_resistance,
                'momentum': self._calculate_momentum(data)
            }
            
        except Exception as e:
            logger.error(f"Error in trend analysis: {e}")
            return {
                'direction': 'neutral',
                'strength': 0,
                'higher_lows': 0,
                'lower_highs': 0
            }
    
    def _count_higher_lows(self, lows: np.ndarray) -> int:
        """
        شمارش کف‌های بالاتر متوالی
        """
        count = 0
        for i in range(len(lows)-1, 1, -1):
            if i-1 >= 0 and lows[i] > lows[i-1]:
                count += 1
            else:
                break
        return count
    
    def _count_lower_highs(self, highs: np.ndarray) -> int:
        """
        شمارش سقف‌های پایین‌تر متوالی
        """
        count = 0
        for i in range(len(highs)-1, 1, -1):
            if i-1 >= 0 and highs[i] < highs[i-1]:
                count += 1
            else:
                break
        return count
    
    def _find_trendline(self, data: pd.DataFrame, direction: str) -> Dict:
        """
        تشخیص خط روند
        """
        try:
            if direction == 'bullish':
                # خط روند صعودی: اتصال کف‌ها
                points = []
                for i in range(-10, 0):
                    if i-1 >= -len(data):
                        if data['low'].iloc[i] > data['low'].iloc[i-1]:
                            points.append((i, data['low'].iloc[i]))
                
                if len(points) >= 2:
                    return {
                        'detected': True,
                        'type': 'support',
                        'points': points,
                        'slope': (points[-1][1] - points[0][1]) / (points[-1][0] - points[0][0])
                    }
            
            elif direction == 'bearish':
                # خط روند نزولی: اتصال سقف‌ها
                points = []
                for i in range(-10, 0):
                    if i-1 >= -len(data):
                        if data['high'].iloc[i] < data['high'].iloc[i-1]:
                            points.append((i, data['high'].iloc[i]))
                
                if len(points) >= 2:
                    return {
                        'detected': True,
                        'type': 'resistance',
                        'points': points,
                        'slope': (points[-1][1] - points[0][1]) / (points[-1][0] - points[0][0])
                    }
            
            return {'detected': False}
            
        except Exception as e:
            logger.error(f"Error finding trendline: {e}")
            return {'detected': False}
    
    def _find_support_resistance(self, data: pd.DataFrame) -> Dict:
        """
        تشخیص سطوح حمایت و مقاومت
        """
        try:
            # استفاده از کندل‌های 20 تایی آخر
            recent_data = data.iloc[-20:]
            
            # سطوح کلیدی
            support = recent_data['low'].min()
            resistance = recent_data['high'].max()
            
            # نزدیکترین سطوح به قیمت فعلی
            current_price = data['close'].iloc[-1]
            
            return {
                'support': support,
                'resistance': resistance,
                'distance_to_support': (current_price - support) / current_price,
                'distance_to_resistance': (resistance - current_price) / current_price,
                'near_support': abs(current_price - support) / current_price < 0.01,
                'near_resistance': abs(resistance - current_price) / current_price < 0.01
            }
            
        except Exception as e:
            logger.error(f"Error finding support/resistance: {e}")
            return {'support': None, 'resistance': None}
    
    def _calculate_momentum(self, data: pd.DataFrame) -> Dict:
        """
        محاسبه مومنتوم
        """
        try:
            if len(data) < 14:
                return {'value': 0, 'direction': 'neutral'}
            
            # RSI ساده
            closes = data['close'].values[-14:]
            gains = []
            losses = []
            
            for i in range(1, len(closes)):
                change = closes[i] - closes[i-1]
                if change > 0:
                    gains.append(change)
                    losses.append(0)
                else:
                    gains.append(0)
                    losses.append(abs(change))
            
            avg_gain = np.mean(gains) if gains else 0
            avg_loss = np.mean(losses) if losses else 1
            
            rs = avg_gain / avg_loss if avg_loss != 0 else 100
            rsi = 100 - (100 / (1 + rs))
            
            return {
                'value': rsi,
                'direction': 'overbought' if rsi > 70 else 'oversold' if rsi < 30 else 'neutral',
                'strength': abs(rsi - 50) / 50
            }
            
        except Exception as e:
            logger.error(f"Error calculating momentum: {e}")
            return {'value': 50, 'direction': 'neutral'}