"""
محاسبه حجم موقعیت معاملاتی بر اساس مدیریت ریسک
"""
import math
from typing import Dict, Optional
from ..utils.logger import get_logger
from ..utils.helpers import safe_divide

logger = get_logger(__name__)

class PositionSizer:
    """
    محاسبه حجم معامله بر اساس ریسک
    """
    
    def __init__(self, config: Dict, symbol_info: Dict):
        """
        Args:
            config: تنظیمات
            symbol_info: اطلاعات نماد معاملاتی
        """
        self.config = config
        self.symbol_info = symbol_info
        self.risk_config = config.get('risk_management', {})
        
        # پارامترهای ریسک
        self.max_risk_per_trade = self.risk_config.get('max_risk_per_trade', 2.0)  # درصد
        self.max_daily_risk = self.risk_config.get('max_daily_risk', 5.0)  # درصد
        self.max_open_positions = self.risk_config.get('max_open_positions', 3)
        self.use_dynamic_sizing = self.risk_config.get('use_dynamic_sizing', True)
        
        # اطلاعات نماد
        self.volume_min = symbol_info.get('volume_min', 0.01)
        self.volume_max = symbol_info.get('volume_max', 100)
        self.volume_step = symbol_info.get('volume_step', 0.01)
        self.digits = symbol_info.get('digits', 5)
        self.point = symbol_info.get('point', 0.00001)
        
    def calculate_position_size(self, 
                                balance: float,
                                entry_price: float,
                                stop_loss: float,
                                risk_percentage: Optional[float] = None) -> float:
        """
        محاسبه حجم موقعیت
        
        Args:
            balance: موجودی حساب
            entry_price: قیمت ورود
            stop_loss: قیمت حد ضرر
            risk_percentage: درصد ریسک (اگر None باشد از مقدار پیش‌فرض استفاده می‌شود)
            
        Returns:
            float: حجم معامله
        """
        try:
            if risk_percentage is None:
                risk_percentage = self.max_risk_per_trade
            
            # محاسبه فاصله تا حد ضرر به پیپ
            stop_distance_pips = self._calculate_stop_distance(entry_price, stop_loss)
            
            if stop_distance_pips <= 0:
                logger.warning(f"Invalid stop distance: {stop_distance_pips}")
                return self.volume_min
            
            # محاسبه ارزش هر پیپ
            pip_value = self._calculate_pip_value(entry_price)
            
            # محاسبه ریسک به دلار
            risk_amount = balance * (risk_percentage / 100)
            
            # محاسبه حجم
            volume = risk_amount / (stop_distance_pips * pip_value)
            
            # گرد کردن به حجم مجاز
            volume = self._round_to_step(volume)
            
            # محدودیت‌ها
            volume = max(self.volume_min, min(volume, self.volume_max))
            
            logger.info(f"Position size calculated: {volume:.2f} lots (Risk: ${risk_amount:.2f})")
            
            return volume
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return self.volume_min
    
    def calculate_risk_amount(self, 
                             volume: float,
                             entry_price: float,
                             stop_loss: float) -> float:
        """
        محاسبه مقدار ریسک به دلار
        
        Args:
            volume: حجم معامله
            entry_price: قیمت ورود
            stop_loss: قیمت حد ضرر
            
        Returns:
            float: ریسک به دلار
        """
        try:
            stop_distance_pips = self._calculate_stop_distance(entry_price, stop_loss)
            pip_value = self._calculate_pip_value(entry_price)
            
            risk_amount = volume * stop_distance_pips * pip_value
            return risk_amount
            
        except Exception as e:
            logger.error(f"Error calculating risk amount: {e}")
            return 0
    
    def _calculate_stop_distance(self, entry: float, stop: float) -> float:
        """
        محاسبه فاصله تا حد ضرر به پیپ
        """
        try:
            diff = abs(entry - stop)
            # تبدیل به پیپ (برای جفت‌ارزهای 5 رقم اعشار، هر پیپ = 10 نقطه)
            if self.digits in [3, 5]:
                pips = diff / (self.point * 10)
            else:
                pips = diff / self.point
            
            return pips
            
        except Exception as e:
            logger.error(f"Error calculating stop distance: {e}")
            return 0
    
    def _calculate_pip_value(self, price: float) -> float:
        """
        محاسبه ارزش هر پیپ به دلار
        
        تخمین ساده: برای جفت‌ارزهای اصلی با حجم 1 لات، هر پیپ 10 دلار است
        """
        try:
            # این یک تخمین ساده است - در عمل باید با توجه به جفت‌ارز محاسبه شود
            symbol = self.symbol_info.get('symbol', 'XAUUSD')
            
            if 'JPY' in symbol:
                # برای جفت‌ارزهای ینی
                return 10 * (100 / price) if price > 0 else 10
            elif 'XAU' in symbol or 'GOLD' in symbol:
                # برای طلا
                return 10.0
            elif 'XAG' in symbol or 'SILVER' in symbol:
                # برای نقره
                return 50.0  # بر اساس مشخصات اکثر بروکرها
            elif 'BTC' in symbol:
                # برای بیت‌کوین
                return 1.0
            else:
                # برای بیشتر جفت‌ارزها
                return 10  # هر پیپ 10 دلار برای 1 لات
                
        except Exception as e:
            logger.error(f"Error calculating pip value: {e}")
            return 10
    
    def _round_to_step(self, volume: float) -> float:
        """
        گرد کردن حجم به گام مجاز
        """
        try:
            if self.volume_step <= 0:
                return volume
            
            steps = round(volume / self.volume_step)
            return steps * self.volume_step
            
        except Exception as e:
            logger.error(f"Error rounding volume: {e}")
            return volume
    
    def check_daily_risk_limit(self, 
                              balance: float,
                              daily_profit: float,
                              proposed_risk: float) -> bool:
        """
        بررسی محدودیت ریسک روزانه
        
        Args:
            balance: موجودی حساب
            daily_profit: سود/ضرر روزانه
            proposed_risk: ریسک معامله پیشنهادی
            
        Returns:
            bool: آیا مجاز به معامله است
        """
        try:
            # محاسبه ضرر روزانه (اگر منفی باشد)
            daily_loss = abs(min(0, daily_profit))
            
            # محاسبه ریسک کل روز
            total_daily_risk = daily_loss + proposed_risk
            risk_percentage = (total_daily_risk / balance) * 100 if balance > 0 else 100
            
            if risk_percentage > self.max_daily_risk:
                logger.warning(f"Daily risk limit exceeded: {risk_percentage:.2f}% > {self.max_daily_risk}%")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking daily risk: {e}")
            return False
    
    def get_max_position_size_for_risk(self, 
                                      balance: float,
                                      risk_percentage: float) -> float:
        """
        حداکثر حجم مجاز برای یک ریسک مشخص
        """
        try:
            max_risk_amount = balance * (risk_percentage / 100)
            # تخمین با فرض 50 پیپ فاصله حد ضرر
            estimated_pips = 50
            pip_value = 10  # تقریبی
            
            max_volume = max_risk_amount / (estimated_pips * pip_value)
            max_volume = self._round_to_step(max_volume)
            max_volume = max(self.volume_min, min(max_volume, self.volume_max))
            
            return max_volume
            
        except Exception as e:
            logger.error(f"Error calculating max position size: {e}")
            return self.volume_min
    
    def adjust_for_correlation(self, 
                              volume: float,
                              open_positions: list,
                              max_correlation_risk: float = 0.5) -> float:
        """
        تنظیم حجم بر اساس همبستگی با پوزیشن‌های باز
        """
        try:
            if not open_positions or len(open_positions) == 0:
                return volume
            
            # اگر پوزیشن‌های مشابه زیاد است، حجم را کم کن
            similar_positions = 0
            for pos in open_positions:
                if pos.get('type') == self.symbol_info.get('position_type'):
                    similar_positions += 1
            
            if similar_positions >= 2:
                # کاهش حجم برای پوزیشن‌های همبسته
                adjustment = 1 - (similar_positions * max_correlation_risk / 100)
                volume = volume * max(0.5, adjustment)
                volume = self._round_to_step(volume)
                
            return volume
            
        except Exception as e:
            logger.error(f"Error adjusting for correlation: {e}")
            return volume