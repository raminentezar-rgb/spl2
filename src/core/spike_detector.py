"""
تشخیص اسپایک (حرکت قوی) در بازار
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from ..utils.logger import get_logger

logger = get_logger(__name__)

class SpikeDetector:
    """
    تشخیص اسپایک‌ها و حرکات قوی قیمت
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.min_spike_bars = config.get('strategy', {}).get('min_higher_lows', 3)
        self.breakout_threshold = config.get('strategy', {}).get('breakout_threshold', 0.001)  # 0.1%
        
    def detect(self, data: pd.DataFrame) -> Dict:
        """تشخیص اسپایک با بهینه‌سازی سرعت"""
        try:
            if len(data) < 10:
                return self._empty_result()
            
            # استفاده از مقادیر numpy برای سرعت بیشتر
            closes = data['close'].values[-20:]
            highs = data['high'].values[-20:]
            lows = data['low'].values[-20:]
            
            # تشخیص همزمان اسپایک صعودی و نزولی
            higher_lows = self._fast_higher_lows(lows)
            lower_highs = self._fast_lower_highs(highs)
            
            # تشخیص شکست
            breakout = self._fast_breakout(data)
            
            # تشخیص گپ
            gap = self._fast_gap(data)
            
            return {
                'has_spike': higher_lows >= self.min_spike_bars or lower_highs >= self.min_spike_bars,
                'spike_type': 'bullish' if higher_lows >= self.min_spike_bars else 'bearish' if lower_highs >= self.min_spike_bars else 'none',
                'direction': 'up' if higher_lows >= self.min_spike_bars else 'down' if lower_highs >= self.min_spike_bars else 'neutral',
                'strength': max(higher_lows, lower_highs) / 5,
                'breakout': {'detected': breakout},
                'gap': {'detected': gap}
            }
            
        except Exception as e:
            self.logger.error(f"Error in spike detection: {e}")
            return self._empty_result()
        
    def _fast_higher_lows(self, lows: np.ndarray) -> int:
            """تشخیص سریع کف‌های بالاتر"""
            count = 0
            for i in range(len(lows)-1, 1, -1):
                if lows[i] > lows[i-1]:
                    count += 1
                else:
                    break
            return count

    def _fast_lower_highs(self, highs: np.ndarray) -> int:
        """تشخیص سریع سقف‌های پایین‌تر"""
        count = 0
        for i in range(len(highs)-1, 1, -1):
            if highs[i] < highs[i-1]:
                count += 1
            else:
                break
        return count
    
    def _detect_bullish_spike(self, data: pd.DataFrame) -> Dict:
        """
        تشخیص اسپایک صعودی (کف‌های بالاتر)
        """
        try:
            lows = data['low'].values[-10:]  # 10 کندل آخر
            highs = data['high'].values[-10:]
            closes = data['close'].values[-10:]
            
            # بررسی کف‌های بالاتر
            higher_lows = 0
            for i in range(-5, -1):
                if len(lows) + i >= 0 and len(lows) + i - 1 >= 0:
                    if lows[i] > lows[i-1]:
                        higher_lows += 1
                    else:
                        higher_lows = 0
                        break
            
            # بررسی قدرت حرکت
            price_change = (closes[-1] - lows[-5]) / lows[-5] if len(lows) >= 5 else 0
            
            # بررسی حجم (اگه داده حجم داشتیم)
            volume_confirmation = True
            if 'tick_volume' in data.columns:
                recent_volume = data['tick_volume'].values[-3:].mean()
                prev_volume = data['tick_volume'].values[-6:-3].mean()
                volume_confirmation = recent_volume > prev_volume * 1.5
            
            detected = (higher_lows >= self.min_spike_bars and 
                       price_change > self.breakout_threshold and
                       volume_confirmation)
            
            return {
                'detected': detected,
                'higher_lows': higher_lows,
                'price_change': price_change,
                'strength': higher_lows / self.min_spike_bars if self.min_spike_bars > 0 else 0,
                'start_index': -higher_lows if higher_lows > 0 else 0,
                'volume_confirmed': volume_confirmation
            }
            
        except Exception as e:
            logger.error(f"Error in bullish spike detection: {e}")
            return {'detected': False, 'higher_lows': 0, 'strength': 0}
    
    def _detect_bearish_spike(self, data: pd.DataFrame) -> Dict:
        """
        تشخیص اسپایک نزولی (سقف‌های پایین‌تر)
        """
        try:
            highs = data['high'].values[-10:]  # 10 کندل آخر
            closes = data['close'].values[-10:]
            
            # بررسی سقف‌های پایین‌تر
            lower_highs = 0
            for i in range(-5, -1):
                if len(highs) + i >= 0 and len(highs) + i - 1 >= 0:
                    if highs[i] < highs[i-1]:
                        lower_highs += 1
                    else:
                        lower_highs = 0
                        break
            
            # بررسی قدرت حرکت
            price_change = (highs[-5] - closes[-1]) / highs[-5] if len(highs) >= 5 else 0
            
            # بررسی حجم
            volume_confirmation = True
            if 'tick_volume' in data.columns:
                recent_volume = data['tick_volume'].values[-3:].mean()
                prev_volume = data['tick_volume'].values[-6:-3].mean()
                volume_confirmation = recent_volume > prev_volume * 1.5
            
            detected = (lower_highs >= self.min_spike_bars and 
                       price_change > self.breakout_threshold and
                       volume_confirmation)
            
            return {
                'detected': detected,
                'lower_highs': lower_highs,
                'price_change': price_change,
                'strength': lower_highs / self.min_spike_bars if self.min_spike_bars > 0 else 0,
                'start_index': -lower_highs if lower_highs > 0 else 0,
                'volume_confirmed': volume_confirmation
            }
            
        except Exception as e:
            logger.error(f"Error in bearish spike detection: {e}")
            return {'detected': False, 'lower_highs': 0, 'strength': 0}
    
    def _detect_breakout(self, data: pd.DataFrame) -> Dict:
        """
        تشخیص شکست (Breakout)
        """
        try:
            if len(data) < 5:
                return {'detected': False, 'type': 'none'}
            
            last_close = data['close'].iloc[-1]
            prev_high = data['high'].iloc[-2]
            prev_low = data['low'].iloc[-2]
            
            # شکست به بالا
            if last_close > prev_high:
                # بررسی گپ
                gap = data['low'].iloc[-1] > prev_high
                
                return {
                    'detected': True,
                    'type': 'bullish',
                    'gap': gap,
                    'level': prev_high,
                    'strength': (last_close - prev_high) / prev_high
                }
            
            # شکست به پایین
            elif last_close < prev_low:
                # بررسی گپ
                gap = data['high'].iloc[-1] < prev_low
                
                return {
                    'detected': True,
                    'type': 'bearish',
                    'gap': gap,
                    'level': prev_low,
                    'strength': (prev_low - last_close) / prev_low
                }
            
            return {'detected': False, 'type': 'none'}
            
        except Exception as e:
            logger.error(f"Error in breakout detection: {e}")
            return {'detected': False, 'type': 'none'}
    
    def _detect_gap(self, data: pd.DataFrame) -> Dict:
        """
        تشخیص گپ قیمتی
        """
        try:
            if len(data) < 2:
                return {'detected': False, 'type': 'none'}
            
            current_open = data['open'].iloc[-1]
            prev_close = data['close'].iloc[-2]
            
            # گپ صعودی
            if current_open > prev_close * 1.0001:  # 0.01% اختلاف
                gap_size = (current_open - prev_close) / prev_close
                
                return {
                    'detected': True,
                    'type': 'bullish',
                    'size': gap_size,
                    'filled': data['low'].iloc[-1] <= prev_close  # آیا پر شده؟
                }
            
            # گپ نزولی
            elif current_open < prev_close * 0.9999:
                gap_size = (prev_close - current_open) / prev_close
                
                return {
                    'detected': True,
                    'type': 'bearish',
                    'size': gap_size,
                    'filled': data['high'].iloc[-1] >= prev_close  # آیا پر شده؟
                }
            
            return {'detected': False, 'type': 'none'}
            
        except Exception as e:
            logger.error(f"Error in gap detection: {e}")
            return {'detected': False, 'type': 'none'}
        
    def _fast_breakout(self, data: pd.DataFrame) -> bool:
        """تشخیص سریع شکست"""
        if len(data) < 2:
            return False
        
        last_close = data['close'].iloc[-1]
        prev_high = data['high'].iloc[-2]
        prev_low = data['low'].iloc[-2]
        
        return last_close > prev_high or last_close < prev_low

    def _fast_gap(self, data: pd.DataFrame) -> bool:
        """تشخیص سریع گپ"""
        if len(data) < 2:
            return False
        
        current_open = data['open'].iloc[-1]
        prev_close = data['close'].iloc[-2]
        
        return abs(current_open - prev_close) / prev_close > 0.0001

    def _empty_result(self) -> Dict:
        """برگرداندن نتیجه خالی"""
        return {
            'has_spike': False,
            'spike_type': 'none',
            'direction': 'neutral',
            'strength': 0,
            'breakout': {'detected': False},
            'gap': {'detected': False}
        }