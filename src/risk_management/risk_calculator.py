"""
محاسبات ریسک معاملاتی
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from ..utils.logger import get_logger
from ..utils.helpers import safe_divide

logger = get_logger(__name__)

class RiskCalculator:
    """
    محاسبه معیارهای ریسک
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self.risk_config = config.get('risk_management', {})
        
    def calculate_sharpe_ratio(self, returns: List[float], risk_free_rate: float = 0.02) -> float:
        """
        محاسبه نسبت شارپ
        """
        try:
            if len(returns) < 2:
                return 0
            
            returns_array = np.array(returns)
            avg_return = np.mean(returns_array)
            std_return = np.std(returns_array)
            
            if std_return == 0:
                return 0
            
            # نسبت شارپ سالانه (با فرض 252 روز معاملاتی)
            sharpe = (avg_return - risk_free_rate/252) / std_return * np.sqrt(252)
            return sharpe
            
        except Exception as e:
            logger.error(f"Error calculating Sharpe ratio: {e}")
            return 0
    
    def calculate_sortino_ratio(self, returns: List[float], risk_free_rate: float = 0.02) -> float:
        """
        محاسبه نسبت سورتینو (فقط ریسک نزولی)
        """
        try:
            if len(returns) < 2:
                return 0
            
            returns_array = np.array(returns)
            avg_return = np.mean(returns_array)
            
            # فقط بازده‌های منفی
            negative_returns = returns_array[returns_array < 0]
            
            if len(negative_returns) == 0:
                return 10  # اگر بازده منفی نداشتیم، ریسک خیلی کم است
            
            downside_std = np.std(negative_returns)
            
            if downside_std == 0:
                return 0
            
            sortino = (avg_return - risk_free_rate/252) / downside_std * np.sqrt(252)
            return sortino
            
        except Exception as e:
            logger.error(f"Error calculating Sortino ratio: {e}")
            return 0
    
    def calculate_max_drawdown(self, equity_curve: List[float]) -> Dict:
        """
        محاسبه حداکثر دراو‌داون
        """
        try:
            if len(equity_curve) < 2:
                return {'max_drawdown': 0, 'max_drawdown_percentage': 0}
            
            equity_array = np.array(equity_curve)
            
            # محاسبه اوج‌ها
            peak = np.maximum.accumulate(equity_array)
            
            # محاسبه دراو‌داون
            drawdown = (peak - equity_array) / peak * 100
            drawdown_value = peak - equity_array
            
            max_dd_percentage = np.max(drawdown)
            max_dd_index = np.argmax(drawdown)
            
            # پیدا کردن مدت دراو‌داون
            dd_start = None
            dd_end = None
            
            for i in range(max_dd_index, -1, -1):
                if equity_array[i] == peak[i]:
                    dd_start = i
                    break
            
            for i in range(max_dd_index, len(equity_array)):
                if equity_array[i] >= peak[dd_start]:
                    dd_end = i
                    break
            
            dd_duration = (dd_end - dd_start) if dd_end and dd_start else 0
            
            return {
                'max_drawdown': max_dd_percentage,
                'max_drawdown_value': drawdown_value[max_dd_index],
                'drawdown_start': dd_start,
                'drawdown_end': dd_end,
                'drawdown_duration': dd_duration
            }
            
        except Exception as e:
            logger.error(f"Error calculating max drawdown: {e}")
            return {'max_drawdown': 0, 'max_drawdown_percentage': 0}
    
    def calculate_win_rate(self, trades: List[Dict]) -> Dict:
        """
        محاسبه نرخ برد
        """
        try:
            if len(trades) == 0:
                return {'win_rate': 0, 'total_trades': 0}
            
            winning_trades = [t for t in trades if t.get('profit', 0) > 0]
            losing_trades = [t for t in trades if t.get('profit', 0) < 0]
            
            win_rate = len(winning_trades) / len(trades) * 100
            
            # میانگین سود و ضرر
            avg_win = np.mean([t['profit'] for t in winning_trades]) if winning_trades else 0
            avg_loss = abs(np.mean([t['profit'] for t in losing_trades])) if losing_trades else 0
            
            # نسبت سود به ضرر
            profit_factor = avg_win / avg_loss if avg_loss > 0 else float('inf')
            
            return {
                'win_rate': win_rate,
                'total_trades': len(trades),
                'winning_trades': len(winning_trades),
                'losing_trades': len(losing_trades),
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'profit_factor': profit_factor
            }
            
        except Exception as e:
            logger.error(f"Error calculating win rate: {e}")
            return {'win_rate': 0, 'total_trades': 0}
    
    def calculate_risk_of_ruin(self, win_rate: float, risk_per_trade: float) -> float:
        """
        محاسبه ریسک ورشکستگی
        """
        try:
            if win_rate <= 0 or risk_per_trade <= 0:
                return 1.0
            
            # فرمول ساده ریسک ورشکستگی
            q = 1 - win_rate/100
            p = win_rate/100
            
            if p <= q:
                return 1.0
            
            # احتمال ورشکستگی با فرض 1000 معامله
            ruin_prob = (q/p) ** 1000
            return min(ruin_prob, 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating risk of ruin: {e}")
            return 1.0
    
    def calculate_kelly_criterion(self, win_rate: float, avg_win: float, avg_loss: float) -> float:
        """
        محاسبه معیار کلی برای حجم بهینه
        """
        try:
            if win_rate <= 0 or avg_win <= 0 or avg_loss <= 0:
                return 0
            
            p = win_rate / 100
            q = 1 - p
            b = avg_win / avg_loss  # نسبت سود به ضرر
            
            kelly = (p * b - q) / b
            return max(0, min(kelly, 0.25))  # محدود به 25 درصد
            
        except Exception as e:
            logger.error(f"Error calculating Kelly criterion: {e}")
            return 0
    
    def calculate_var(self, returns: List[float], confidence: float = 0.95) -> float:
        """
        محاسبه Value at Risk (VaR)
        """
        try:
            if len(returns) < 10:
                return 0
            
            returns_array = np.array(returns)
            var = np.percentile(returns_array, (1 - confidence) * 100)
            return abs(var)
            
        except Exception as e:
            logger.error(f"Error calculating VaR: {e}")
            return 0
    
    def calculate_expected_shortfall(self, returns: List[float], confidence: float = 0.95) -> float:
        """
        محاسبه Expected Shortfall (CVaR)
        """
        try:
            if len(returns) < 10:
                return 0
            
            returns_array = np.array(returns)
            var = np.percentile(returns_array, (1 - confidence) * 100)
            
            # میانگین بازده‌های بدتر از VaR
            cvar = returns_array[returns_array <= var].mean()
            return abs(cvar)
            
        except Exception as e:
            logger.error(f"Error calculating Expected Shortfall: {e}")
            return 0