try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    mt5 = None
    MT5_AVAILABLE = False

import pandas as pd
from typing import Optional, Dict
from datetime import datetime
import time
from ..utils.logger import setup_logger

class MT5Connector:
    """
    کلاس مدیریت اتصال به متاتریدر 5
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.logger = setup_logger(__name__)
        self.connected = False
        
        if MT5_AVAILABLE:
            self.timeframe_map = {
                'M1': mt5.TIMEFRAME_M1,
                'M5': mt5.TIMEFRAME_M5,
                'M15': mt5.TIMEFRAME_M15,
                'M30': mt5.TIMEFRAME_M30,
                'H1': mt5.TIMEFRAME_H1,
                'H4': mt5.TIMEFRAME_H4,
                'D1': mt5.TIMEFRAME_D1
            }
        else:
            self.timeframe_map = {}
    
    def connect(self) -> bool:
        """
        اتصال به متاتریدر 5
        """
        if not MT5_AVAILABLE:
            self.logger.error("MetaTrader5 library not available on this system.")
            return False
            
        try:
            # سعی برای اتصال با مسیر مشخص شده در تنظیمات
            path = self.config['mt5'].get('path')
            
            if path:
                success = mt5.initialize(path=path)
            else:
                success = mt5.initialize()
                
            # اگر با مسیر شکست خورد، یک بار بدون مسیر هم تست می‌کنیم
            if not success:
                self.logger.warning("MT5 initialize with path failed, trying without path...")
                if not mt5.initialize():
                    self.logger.error(f"MT5 initialize failed: {mt5.last_error()}")
                    return False
            
            # ورود به حساب (در صورت نیاز)
            login = self.config['mt5'].get('login')
            if login and str(login).isdigit() and int(login) != 12345678:
                authorized = mt5.login(
                    int(login),
                    password=self.config['mt5'].get('password'),
                    server=self.config['mt5'].get('server')
                )
                if not authorized:
                    self.logger.error(f"MT5 login failed for account {login}: {mt5.last_error()}")
                    return False
            else:
                self.logger.warning("No valid MT5 login found in config. Using current terminal session.")
            
            self.connected = True
            self.logger.info("MT5 connected successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"MT5 connection error: {e}")
            return False
    
    def disconnect(self):
        """قطع اتصال"""
        if self.connected and MT5_AVAILABLE:
            mt5.shutdown()
            self.connected = False
            self.logger.info("MT5 disconnected")
    
    def get_rates(self, symbol: str, timeframe: str, count: int = 100) -> Optional[pd.DataFrame]:
        """
        دریافت داده‌های قیمتی
        
        Args:
            symbol: نماد معاملاتی (مثلاً XAUUSD)
            timeframe: تایم‌فریم (M1, M5, ...)
            count: تعداد کندل‌ها
            
        Returns:
            دیتافریم با OHLCV داده‌ها
        """
        if not MT5_AVAILABLE:
            self.logger.warning("MT5 library not available. Cannot fetch rates.")
            return None
            
        try:
            tf = self.timeframe_map.get(timeframe, mt5.TIMEFRAME_M5)
            
            rates = mt5.copy_rates_from_pos(
                symbol, tf, 0, count
            )
            
            if rates is None or len(rates) == 0:
                self.logger.warning(f"No data for {symbol}")
                return None
            
            # تبدیل به دیتافریم
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df.set_index('time', inplace=True)
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error getting rates: {e}")
            return None
    
    def get_account_info(self) -> Dict:
        """دریافت اطلاعات حساب"""
        if not self.connected or not MT5_AVAILABLE:
            return {}
        
        try:
            account = mt5.account_info()
            if account is None:
                return {}
            
            return {
                'balance': account.balance,
                'equity': account.equity,
                'margin': account.margin,
                'free_margin': account.margin_free,
                'profit': account.profit,
                'leverage': account.leverage
            }
        except:
            return {}
    
    def get_positions(self, symbol: str = None) -> pd.DataFrame:
        """دریافت پوزیشن‌های باز"""
        if not self.connected or not MT5_AVAILABLE:
            return pd.DataFrame()
        
        if symbol:
            positions = mt5.positions_get(symbol=symbol)
        else:
            positions = mt5.positions_get()
        
        if positions is None or len(positions) == 0:
            return pd.DataFrame()
        
        df = pd.DataFrame(list(positions), columns=positions[0]._asdict().keys())
        df['time'] = pd.to_datetime(df['time'], unit='s')
        
        return df
    
    def get_symbol_info(self, symbol: str) -> Dict:
        """دریافت اطلاعات نماد"""
        info = mt5.symbol_info(symbol)
        if info is None:
            return {}
        
        return {
            'spread': info.spread,
            'digits': info.digits,
            'point': info.point,
            'trade_mode': info.trade_mode,
            'volume_min': info.volume_min,
            'volume_max': info.volume_max,
            'volume_step': info.volume_step
        }