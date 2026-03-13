"""
اطلاعات حساب معاملاتی
"""
import MetaTrader5 as mt5
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
        try:
            if not self.connector.connected:
                logger.error("MT5 not connected")
                return {}
            
            account = mt5.account_info()
            if account is None:
                logger.error("Failed to get account info")
                return {}
            
            return {
                'login': account.login,
                'name': account.name,
                'balance': account.balance,
                'equity': account.equity,
                'margin': account.margin,
                'margin_free': account.margin_free,
                'margin_level': account.margin_level,
                'profit': account.profit,
                'leverage': account.leverage,
                'currency': account.currency,
                'server': account.server,
                'company': account.company,
                'trade_mode': account.trade_mode,
                'limit_orders': account.limit_orders
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
    
    def get_margin_level(self) -> float:
        """دریافت سطح مارجین"""
        info = self.get_info()
        return info.get('margin_level', 0)
    
    def get_daily_profit(self) -> float:
        """محاسبه سود روزانه"""
        try:
            today = datetime.now().date()
            history = mt5.history_deals_get(
                datetime(today.year, today.month, today.day, 0, 0),
                datetime.now()
            )
            
            if history is None or len(history) == 0:
                return 0
            
            profit = sum(deal.profit for deal in history)
            return profit
            
        except Exception as e:
            logger.error(f"Error calculating daily profit: {e}")
            return 0
    
    def get_weekly_profit(self) -> float:
        """محاسبه سود هفتگی"""
        try:
            from datetime import timedelta
            
            today = datetime.now()
            # پیدا کردن اولین روز هفته (دوشنبه)
            days_to_monday = today.weekday()
            week_start = today - timedelta(days=days_to_monday)
            week_start = datetime(week_start.year, week_start.month, week_start.day, 0, 0)
            
            history = mt5.history_deals_get(week_start, datetime.now())
            
            if history is None or len(history) == 0:
                return 0
            
            profit = sum(deal.profit for deal in history)
            return profit
            
        except Exception as e:
            logger.error(f"Error calculating weekly profit: {e}")
            return 0
    
    def get_monthly_profit(self) -> float:
        """محاسبه سود ماهانه"""
        try:
            today = datetime.now()
            month_start = datetime(today.year, today.month, 1, 0, 0)
            
            history = mt5.history_deals_get(month_start, datetime.now())
            
            if history is None or len(history) == 0:
                return 0
            
            profit = sum(deal.profit for deal in history)
            return profit
            
        except Exception as e:
            logger.error(f"Error calculating monthly profit: {e}")
            return 0
    
    def get_risk_metrics(self) -> Dict:
        """
        محاسبه معیارهای ریسک
        """
        try:
            info = self.get_info()
            positions = self.connector.get_positions()
            
            total_risk = 0
            if not positions.empty:
                # محاسبه ریسک کل (فقط یک تخمین ساده)
                for _, pos in positions.iterrows():
                    if pos['type'] == mt5.POSITION_TYPE_BUY:
                        risk = (pos['price_open'] - pos['sl']) * pos['volume'] * 100000 if pos['sl'] > 0 else 0
                    else:
                        risk = (pos['sl'] - pos['price_open']) * pos['volume'] * 100000 if pos['sl'] > 0 else 0
                    total_risk += max(0, risk)
            
            balance = info.get('balance', 1)
            return {
                'total_risk_usd': total_risk,
                'risk_percentage': (total_risk / balance) * 100 if balance > 0 else 0,
                'open_positions': len(positions) if not positions.empty else 0,
                'margin_level': info.get('margin_level', 0),
                'free_margin': info.get('margin_free', 0)
            }
            
        except Exception as e:
            logger.error(f"Error calculating risk metrics: {e}")
            return {}
    
    def is_trading_allowed(self) -> bool:
        """بررسی مجاز بودن معامله"""
        info = self.get_info()
        if not info:
            return False
        
        # بررسی سطح مارجین
        margin_level = info.get('margin_level', 100)
        if margin_level < 100:  # کمتر از 100% ریسک داره
            logger.warning(f"Low margin level: {margin_level}%")
            return False
        
        # بررسی موجودی
        if info.get('balance', 0) < 100:  # کمتر از 100 دلار
            logger.warning("Balance too low")
            return False
        
        return True