"""
اطلاعات حساب معاملاتی
"""
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    mt5 = None
    MT5_AVAILABLE = False

from typing import Dict, Optional
from datetime import datetime
from ..utils.logger import get_logger

logger = get_logger(__name__)

class AccountInfo:
    """
    دریافت و مدیریت اطلاعات حساب
    """
    
    def __init__(self, connector):
        self.connector = connector
        
    def get_info(self) -> Dict:
        """
        دریافت اطلاعات کامل حساب
        """
        if not MT5_AVAILABLE or not self.connector.connected:
            return {}
            
        try:
            account = mt5.account_info()
            if account is None:
                return {}
            
            return {
                'login': account.login,
                'name': account.name,
                'balance': account.balance,
                'equity': account.equity,
                'margin': account.margin,
                'margin_free': account.margin_free,
                'profit': account.profit
            }
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return {}
    
    def get_balance(self) -> float:
        """دریافت موجودی حساب"""
        info = self.get_info()
        return info.get('balance', 0)
    
    def get_equity(self) -> float:
        """دریافت equity حساب"""
        info = self.get_info()
        return info.get('equity', 0)
    
    def get_daily_profit(self) -> float:
        """محاسبه سود روزانه"""
        if not MT5_AVAILABLE:
            return 0
            
        try:
            today = datetime.now().date()
            history = mt5.history_deals_get(
                datetime(today.year, today.month, today.day, 0, 0),
                datetime.now()
            )
            if history is None or len(history) == 0:
                return 0
            return sum(deal.profit for deal in history)
        except Exception as e:
            logger.error(f"Error calculating daily profit: {e}")
            return 0
    
    def get_risk_metrics(self) -> Dict:
        """
        محاسبه معیارهای ریسک
        """
        if not MT5_AVAILABLE:
            return {}
            
        try:
            info = self.get_info()
            positions = self.connector.get_positions()
            
            balance = info.get('balance', 1)
            return {
                'total_risk_usd': 0,
                'risk_percentage': 0,
                'open_positions': len(positions) if not positions.empty else 0,
                'margin_level': info.get('margin_level', 0),
                'free_margin': info.get('margin_free', 0)
            }
        except Exception as e:
            logger.error(f"Error calculating risk metrics: {e}")
            return {}
    
    def is_trading_allowed(self) -> bool:
        """بررسی مجاز بودن معامله"""
        if not MT5_AVAILABLE:
            return False
        return True