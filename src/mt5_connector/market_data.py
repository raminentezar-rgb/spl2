"""
داده‌های بازار از متاتریدر 5
"""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
from ..utils.logger import get_logger

logger = get_logger(__name__)

class MarketData:
    """
    دریافت و مدیریت داده‌های بازار
    """
    
    def __init__(self, connector):
        self.connector = connector
        self.timeframe_map = {
            'M1': mt5.TIMEFRAME_M1,
            'M2': mt5.TIMEFRAME_M2,
            'M3': mt5.TIMEFRAME_M3,
            'M4': mt5.TIMEFRAME_M4,
            'M5': mt5.TIMEFRAME_M5,
            'M6': mt5.TIMEFRAME_M6,
            'M10': mt5.TIMEFRAME_M10,
            'M12': mt5.TIMEFRAME_M12,
            'M15': mt5.TIMEFRAME_M15,
            'M20': mt5.TIMEFRAME_M20,
            'M30': mt5.TIMEFRAME_M30,
            'H1': mt5.TIMEFRAME_H1,
            'H2': mt5.TIMEFRAME_H2,
            'H3': mt5.TIMEFRAME_H3,
            'H4': mt5.TIMEFRAME_H4,
            'H6': mt5.TIMEFRAME_H6,
            'H8': mt5.TIMEFRAME_H8,
            'H12': mt5.TIMEFRAME_H12,
            'D1': mt5.TIMEFRAME_D1,
            'W1': mt5.TIMEFRAME_W1,
            'MN1': mt5.TIMEFRAME_MN1
        }
        
    def get_rates(self, symbol: str, timeframe: str, count: int = 100) -> Optional[pd.DataFrame]:
        """
        دریافت داده‌های قیمتی
        
        Args:
            symbol: نماد معاملاتی
            timeframe: تایم‌فریم
            count: تعداد کندل‌ها
            
        Returns:
            pd.DataFrame: داده‌های OHLCV
        """
        try:
            if not self.connector.connected:
                logger.error("MT5 not connected")
                return None
            
            tf = self.timeframe_map.get(timeframe, mt5.TIMEFRAME_M5)
            
            rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
            
            if rates is None or len(rates) == 0:
                logger.warning(f"No data for {symbol} {timeframe}")
                return None
            
            # تبدیل به دیتافریم
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df.set_index('time', inplace=True)
            
            # اطمینان از وجود ستون‌های مورد نیاز
            required_cols = ['open', 'high', 'low', 'close', 'tick_volume']
            for col in required_cols:
                if col not in df.columns:
                    df[col] = 0
            
            return df
            
        except Exception as e:
            logger.error(f"Error getting rates: {e}")
            return None
    
    def get_rates_range(self, symbol: str, timeframe: str, 
                        start: datetime, end: datetime) -> Optional[pd.DataFrame]:
        """
        دریافت داده‌های قیمتی در بازه زمانی مشخص
        """
        try:
            if not self.connector.connected:
                logger.error("MT5 not connected")
                return None
            
            tf = self.timeframe_map.get(timeframe, mt5.TIMEFRAME_M5)
            
            rates = mt5.copy_rates_range(symbol, tf, start, end)
            
            if rates is None or len(rates) == 0:
                logger.warning(f"No data for {symbol} {timeframe} in range")
                return None
            
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df.set_index('time', inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Error getting rates range: {e}")
            return None
    
    def get_last_ticks(self, symbol: str, count: int = 1000) -> Optional[pd.DataFrame]:
        """
        دریافت آخرین تیک‌ها
        """
        try:
            ticks = mt5.copy_ticks_from(symbol, datetime.now(), count, mt5.COPY_TICKS_ALL)
            
            if ticks is None or len(ticks) == 0:
                return None
            
            df = pd.DataFrame(ticks)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df.set_index('time', inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Error getting ticks: {e}")
            return None
    
    def get_symbol_info(self, symbol: str) -> Dict:
        """
        دریافت اطلاعات نماد
        """
        try:
            info = mt5.symbol_info(symbol)
            if info is None:
                logger.warning(f"Symbol {symbol} not found")
                return {}
            
            return {
                'symbol': info.name,
                'digits': info.digits,
                'point': info.point,
                'spread': info.spread,
                'spread_float': info.spread_float,
                'trade_mode': info.trade_mode,
                'volume_min': info.volume_min,
                'volume_max': info.volume_max,
                'volume_step': info.volume_step,
                'trade_exce': info.trade_exce,
                'trade_stops_level': info.trade_stops_level,
                'swap_mode': info.swap_mode,
                'swap_long': info.swap_long,
                'swap_short': info.swap_short,
                'margin_initial': info.margin_initial,
                'margin_maintenance': info.margin_maintenance,
                'bid': info.bid,
                'ask': info.ask,
                'high': info.high,
                'low': info.low
            }
            
        except Exception as e:
            logger.error(f"Error getting symbol info: {e}")
            return {}
    
    def get_current_price(self, symbol: str) -> Tuple[float, float]:
        """
        دریافت قیمت‌های فعلی (bid/ask)
        """
        try:
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                return (0, 0)
            
            return (tick.bid, tick.ask)
            
        except Exception as e:
            logger.error(f"Error getting current price: {e}")
            return (0, 0)
    
    def calculate_atr(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        محاسبه ATR (Average True Range)
        """
        try:
            high = data['high']
            low = data['low']
            close = data['close'].shift(1)
            
            tr1 = high - low
            tr2 = abs(high - close)
            tr3 = abs(low - close)
            
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(window=period).mean()
            
            return atr
            
        except Exception as e:
            logger.error(f"Error calculating ATR: {e}")
            return pd.Series(index=data.index, data=0)
    
    def get_market_hours(self, symbol: str) -> Dict:
        """
        دریافت ساعات بازار
        """
        try:
            info = mt5.symbol_info(symbol)
            if info is None:
                return {}
            
            # این یک تخمین ساده است
            now = datetime.now()
            hour = now.hour
            
            # ساعات تقریبی بازارهای مختلف
            if 'XAU' in symbol or 'GOLD' in symbol:
                # طلا: 24 ساعته با بیشترین حجم در لندن و نیویورک
                london_open = 9 <= hour <= 17
                ny_open = 13 <= hour <= 22
                asia_open = 0 <= hour <= 8
                
                return {
                    'london_open': london_open,
                    'ny_open': ny_open,
                    'asia_open': asia_open,
                    'peak_hours': london_open or ny_open,
                    'low_liquidity': hour >= 22 or hour <= 2
                }
            else:
                return {'peak_hours': True, 'low_liquidity': False}
                
        except Exception as e:
            logger.error(f"Error getting market hours: {e}")
            return {}