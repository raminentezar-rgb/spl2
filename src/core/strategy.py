"""
کلاس اصلی استراتژی SP2L
ترکیب تمام اجزا برای تصمیم‌گیری نهایی
"""
from typing import Dict, Optional, Tuple
import pandas as pd
from .spike_detector import SpikeDetector
from .pullback_finder import PullbackFinder
from .trend_analyzer import TrendAnalyzer
from ..indicators.moving_averages import MovingAverage
from ..indicators.fvg import FVGIndicator
from ..indicators.pivot_points import PivotPoints
from ..indicators.custom_indicators import BigCandleFilter
from ..utils.logger import setup_logger
import numpy as np
from typing import Dict, Optional, Tuple
try:
    import talib
    TALIB_AVAILABLE = True
except ImportError:
    TALIB_AVAILABLE = False
    print("Warning: TA-Lib not installed. Using fallback calculations.")

class SP2LStrategy:
    """
    استراتژی اصلی SP2L:
    - تشخیص اسپایک (حرکت قوی)
    - شناسایی پولبک به میانگین متحرک
    - ورود در جهت روند اصلی
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.logger = setup_logger(__name__)
        
        # کامپوننت‌ها
        self.spike_detector = SpikeDetector(config)
        self.pullback_finder = PullbackFinder(config)
        self.trend_analyzer = TrendAnalyzer(config)
        self.ma = MovingAverage(config['strategy']['ma_period'])
        self.fvg_indicator = FVGIndicator(config)
        self.pivots = PivotPoints(config)
        self.big_candle_filter = BigCandleFilter(config.get('strategy', {}).get('big_candle_filter_x', 5))
        
        # پارامترها
        self.symbol = config['trading']['symbol']
        self.timeframe = config['trading']['timeframe']
        self.min_higher_lows = config['strategy']['min_higher_lows']
        
    def analyze(self, data: pd.DataFrame) -> Dict:
        """
        تحلیل کامل بازار و برگرداندن سیگنال
        
        Args:
            data: دیتافریم با OHLCV داده‌ها
            
        Returns:
            دیکشنری شامل سیگنال و اطلاعات تحلیلی
        """
        try:
            # 1. تحلیل روند
            trend = self.trend_analyzer.analyze(data)
            
            # 2. تشخیص اسپایک
            spike_result = self.spike_detector.detect(data)
            
            # 3. تشخیص پولبک
            pullback_result = self.pullback_finder.find(data)
            
            # 4. محاسبه میانگین متحرک
            ma_values = self.ma.calculate(data)
            
            # 5. محاسبه سطوح پیوت
            pivot_levels = self.pivots.get_latest_pivots(data)
            
            # 6. بررسی فیلترهای جدید
            fvg_present = self.fvg_indicator.is_present(data)
            is_big_candle = self.big_candle_filter.is_big_candle(data)
            
            # 7. تصمیم‌گیری نهایی
            signal = self._generate_signal(
                trend, spike_result, pullback_result, ma_values, data, pivot_levels, fvg_present, is_big_candle
            )
            
            return {
                'signal': signal,
                'trend': trend,
                'spike': spike_result,
                'pullback': pullback_result,
                'ma': float(ma_values.iloc[-1]) if not ma_values.empty else 0,
                'pivots': pivot_levels,
                'fvg': fvg_present,
                'is_big_candle': is_big_candle,
                'timestamp': data.index[-1]
            }
            
        except Exception as e:
            self.logger.error(f"Error in strategy analysis: {e}")
            return {
                'signal': {'type': 'neutral'}, 
                'trend': {}, 
                'spike': {}, 
                'pullback': {}, 
                'ma': 0,
                'error': str(e)
            }
    
    def _generate_signal(self, trend, spike, pullback, ma, data, pivots, fvg, is_big_candle):
        """تولید سیگنال نهایی بر اساس ترکیب عوامل (توالی زمانی)"""
        last_price = data['close'].iloc[-1]
        
        # فیلتر Big Candle - فقط زمانی که به دنبال تریگر هستیم چک می‌شود
        # برای الان کامنت می‌کنیم تا ببینیم فرکانس معاملات چقدر تغییر می‌کند
        # if is_big_candle:
        #     self.logger.info("Signal skipped: Big Candle detected")
        #     return {'type': 'neutral'}
            
        # فقط در صورتی که در ناحیه پولبک باشیم بررسی را ادامه می‌دهیم
        if pullback.get('is_pullback', False):
            
            pullback_type = pullback.get('pullback_type')
            
            if pullback_type == 'bullish':
                # فیلتر FVG صعودی
                if self.config.get('strategy', {}).get('fvg_bull', True) and not fvg.get('bullish', False):
                    return {'type': 'neutral'}
                    
                # بررسی وجود اسپایک صعودی در کندل‌های گذشته
                has_recent_spike, confidence, base_price, peak_price = self._find_recent_spike(data, 'bullish')
                if has_recent_spike and base_price > 0:
                    sl = self._calculate_stop_loss(data, direction='buy', base_price=base_price, pivots=pivots)
                    
                    if last_price <= sl:
                        return {'type': 'neutral'}
                        
                    tp = self._calculate_take_profit(data, direction='buy', entry=last_price, sl=sl, pivots=pivots)
                    
                    return {
                        'type': 'buy',
                        'entry': float(last_price),
                        'sl': sl,
                        'tp': tp,
                        'confidence': float(confidence / 5)
                    }
                    
            elif pullback_type == 'bearish':
                # فیلتر FVG نزولی
                if self.config.get('strategy', {}).get('fvg_bear', True) and not fvg.get('bearish', False):
                    return {'type': 'neutral'}
                    
                # بررسی وجود اسپایک نزولی در کندل‌های گذشته
                has_recent_spike, confidence, base_price, peak_price = self._find_recent_spike(data, 'bearish')
                if has_recent_spike and base_price > 0:
                    sl = self._calculate_stop_loss(data, direction='sell', base_price=base_price, pivots=pivots)
                    
                    if last_price >= sl:
                        return {'type': 'neutral'}
                        
                    tp = self._calculate_take_profit(data, direction='sell', entry=last_price, sl=sl, pivots=pivots)
                    
                    return {
                        'type': 'sell',
                        'entry': float(last_price),
                        'sl': sl,
                        'tp': tp,
                        'confidence': float(confidence / 5)
                    }
                    
        return {'type': 'neutral'}
    
    def _find_recent_spike(self, data: pd.DataFrame, direction: str) -> Tuple[bool, int, float, float]:
        """جستجوی بهینه اسپایک در کندل‌های اخیر (حداکثر 60 کندل قبل - 5 ساعت در M5)"""
        if len(data) < 70:
            return False, 0, 0.0, 0.0
            
        # محدوده جستجو (Lookback)
        lookback = 60
        
        # برای بهینه‌سازی، اول چک می‌کنیم آیا اصلاً اسپایکی در این حوالی بوده یا نه
        # به جای لوپ کامل سنگین، از تشخیص سریع استفاده می‌کنیم
        for i in range(1, lookback + 1):
            # بررسی بازه زمانی i کندل قبل
            idx = len(data) - i
            historical_data = data.iloc[:idx]
            if len(historical_data) < 10: break
            
            # فقط بخش‌های ضروری از دیتا رو می‌فرستیم برای سرعت بیشتر
            spike = self.spike_detector.detect(historical_data)
            
            if spike.get('has_spike', False) and spike.get('spike_type') == direction:
                # اگر اسپایک پیدا شد، جزئیات روند رو چک می‌کنیم
                trend = self.trend_analyzer.analyze(historical_data)
                
                if direction == 'bullish':
                    higher_lows_count = trend.get('higher_lows', 0)
                    if higher_lows_count >= self.min_higher_lows and (spike.get('breakout', {}).get('detected', False) or spike.get('gap', {}).get('detected', False)):
                        # پیداکردن ریشه اسپایک
                        start_idx = max(0, len(historical_data) - higher_lows_count - 3)
                        base_price = historical_data['low'].iloc[start_idx:].min()
                        peak_price = historical_data['high'].iloc[-1]
                        
                        # بررسی باطل شدن (شکست ریشه در فاصله بین اسپایک تا الان)
                        recent_low = data['low'].iloc[idx:].min()
                        if recent_low < base_price:
                            continue 
                            
                        return True, higher_lows_count, float(base_price), float(peak_price)
                
                elif direction == 'bearish':
                    lower_highs_count = trend.get('lower_highs', 0)
                    if lower_highs_count >= self.min_higher_lows and (spike.get('breakout', {}).get('detected', False) or spike.get('gap', {}).get('detected', False)):
                        start_idx = max(0, len(historical_data) - lower_highs_count - 3)
                        base_price = historical_data['high'].iloc[start_idx:].max()
                        peak_price = historical_data['low'].iloc[-1]
                        
                        recent_high = data['high'].iloc[idx:].max()
                        if recent_high > base_price:
                            continue
                            
                        return True, lower_highs_count, float(base_price), float(peak_price)
            
        return False, 0, 0.0, 0.0

    def _calculate_stop_loss(self, data: pd.DataFrame, direction: str, base_price: float, pivots: Dict) -> float:
        """محاسبه حد ضرر بر اساس استراتژی منتخب"""
        sl_type = self.config.get('strategy', {}).get('stop_loss_type', 'ATR')
        
        if sl_type == 'Pivot Point' and pivots and pivots.get('s1') and pivots.get('r1'):
            if direction == 'buy':
                # استاپ زیر نزدیک‌ترین سطح حمایتی پیوت یا ریشه اسپایک (هر کدام دورتر بود برای امنیت بیشتر)
                sl = min(pivots.get('s1', base_price), base_price)
            else:
                # استاپ بالای نزدیک‌ترین سطح مقاومتی پیوت یا ریشه اسپایک
                sl = max(pivots.get('r1', base_price), base_price)
            return float(sl)
            
        elif sl_type == 'ATR':
            try:
                atr_len = self.config.get('strategy', {}).get('atr_length', 14)
                # استفاده از ATR برای سقف حد ضرر (Max SL)
                highs = data['high'].values
                lows = data['low'].values
                closes = data['close'].values
                
                tr = np.maximum(highs[1:] - lows[1:], 
                                np.maximum(abs(highs[1:] - closes[:-1]), 
                                          abs(lows[1:] - closes[:-1])))
                atr = np.mean(tr[-atr_len:])
                
                multiplier = self.config.get('strategy', {}).get('stop_loss_atr_multiplier', 1.9)
                atr_dist = atr * multiplier
                
                if direction == 'buy':
                    sl = data['close'].iloc[-1] - atr_dist
                else:
                    sl = data['close'].iloc[-1] + atr_dist
                return float(sl)
            except:
                pass
                
        # پیش‌فرض: ریشه اسپایک با محدودیت ATR
        # اگر ریشه اسپایک خیلی دور بود (بیش از 3 برابر ATR)، از ATR استفاده می‌کنیم
        try:
            highs = data['high'].values
            lows = data['low'].values
            closes = data['close'].values
            tr = np.maximum(highs[1:] - lows[1:], np.maximum(abs(highs[1:] - closes[:-1]), abs(lows[1:] - closes[:-1])))
            atr_val = np.mean(tr[-14:])
            
            dist_to_base = abs(data['close'].iloc[-1] - base_price)
            if dist_to_base > (atr_val * 3.5): # خیلی دوره
                if direction == 'buy':
                    return float(data['close'].iloc[-1] - (atr_val * 2.5))
                else:
                    return float(data['close'].iloc[-1] + (atr_val * 2.5))
        except:
            pass

        return float(base_price)

    def _calculate_take_profit(self, data: pd.DataFrame, direction: str, entry: float, sl: float, pivots: Dict) -> float:
        """محاسبه حد سود بر اساس استراتژی منتخب"""
        sl_type = self.config.get('strategy', {}).get('stop_loss_type', 'ATR')
        risk = abs(entry - sl)
        
        if sl_type == 'Pivot Point':
            rr = self.config.get('strategy', {}).get('risk_to_reward_pivot', 1.0)
        else:
            rr = self.config.get('strategy', {}).get('risk_reward_ratio', 2.0)
            
        if direction == 'buy':
            return float(entry + (risk * rr))
        else:
            return float(entry - (risk * rr))