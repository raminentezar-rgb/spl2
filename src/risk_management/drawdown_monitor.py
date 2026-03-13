"""
پایش دراو‌داون و هشدار
"""
import time
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from threading import Thread, Event
from ..utils.logger import get_logger

logger = get_logger(__name__)

class DrawdownMonitor:
    """
    پایش دراو‌داون و ارسال هشدار
    """
    
    def __init__(self, config: Dict, account_info, on_alert: Optional[Callable] = None):
        """
        Args:
            config: تنظیمات
            account_info: نمونه AccountInfo
            on_alert: تابع callback برای هشدار
        """
        self.config = config
        self.account_info = account_info
        self.on_alert = on_alert
        
        # آستانه‌ها
        self.alert_thresholds = {
            'warning': 10,    # 10% دراو‌داون
            'danger': 20,     # 20% دراو‌داون
            'critical': 30    # 30% دراو‌داون
        }
        
        # تاریخچه
        self.equity_history = []
        self.drawdown_history = []
        self.max_equity = 0
        self.current_drawdown = 0
        self.peak_equity_time = None
        
        # وضعیت
        self.monitoring = False
        self.monitor_thread = None
        self.stop_event = Event()
        
    def start_monitoring(self, interval: int = 60):
        """
        شروع پایش
        
        Args:
            interval: فاصله بررسی به ثانیه
        """
        if self.monitoring:
            logger.warning("Monitoring already started")
            return
        
        self.monitoring = True
        self.stop_event.clear()
        self.monitor_thread = Thread(target=self._monitor_loop, args=(interval,))
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        logger.info("Drawdown monitoring started")
    
    def stop_monitoring(self):
        """توقف پایش"""
        self.monitoring = False
        self.stop_event.set()
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        
        logger.info("Drawdown monitoring stopped")
    
    def _monitor_loop(self, interval: int):
        """
        حلقه اصلی پایش
        """
        while not self.stop_event.is_set():
            try:
                self.check_drawdown()
                time.sleep(interval)
                
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                time.sleep(interval)
    
    def check_drawdown(self):
        """
        بررسی دراو‌داون فعلی
        """
        try:
            # دریافت اطلاعات حساب
            account_info = self.account_info.get_info()
            if not account_info:
                return
            
            equity = account_info.get('equity', 0)
            balance = account_info.get('balance', 0)
            
            # ذخیره در تاریخچه
            self.equity_history.append({
                'time': datetime.now(),
                'equity': equity,
                'balance': balance
            })
            
            # نگهداری فقط 1000 رکورد آخر
            if len(self.equity_history) > 1000:
                self.equity_history = self.equity_history[-1000:]
            
            # به‌روزرسانی حداکثر equity
            if equity > self.max_equity:
                self.max_equity = equity
                self.peak_equity_time = datetime.now()
            
            # محاسبه دراو‌داون
            if self.max_equity > 0:
                self.current_drawdown = (self.max_equity - equity) / self.max_equity * 100
                
                self.drawdown_history.append({
                    'time': datetime.now(),
                    'drawdown': self.current_drawdown,
                    'max_equity': self.max_equity,
                    'current_equity': equity
                })
                
                # بررسی آستانه‌ها
                self._check_thresholds()
            
        except Exception as e:
            logger.error(f"Error checking drawdown: {e}")
    
    def _check_thresholds(self):
        """
        بررسی آستانه‌های هشدار
        """
        for level, threshold in self.alert_thresholds.items():
            if self.current_drawdown >= threshold:
                self._send_alert(level, threshold)
                break
    
    def _send_alert(self, level: str, threshold: float):
        """
        ارسال هشدار
        """
        message = f"⚠️ Drawdown Alert: {level.upper()}\n"
        message += f"Current Drawdown: {self.current_drawdown:.2f}%\n"
        message += f"Threshold: {threshold}%\n"
        message += f"Max Equity: ${self.max_equity:.2f}\n"
        message += f"Current Equity: ${self.equity_history[-1]['equity']:.2f}"
        
        logger.warning(message)
        
        if self.on_alert:
            try:
                self.on_alert(message)
            except Exception as e:
                logger.error(f"Error sending alert: {e}")
    
    def get_drawdown_report(self) -> Dict:
        """
        دریافت گزارش دراو‌داون
        """
        return {
            'current_drawdown': self.current_drawdown,
            'max_equity': self.max_equity,
            'peak_time': self.peak_equity_time,
            'current_equity': self.equity_history[-1]['equity'] if self.equity_history else 0,
            'max_drawdown_history': max([d['drawdown'] for d in self.drawdown_history]) if self.drawdown_history else 0,
            'average_drawdown': sum([d['drawdown'] for d in self.drawdown_history]) / len(self.drawdown_history) if self.drawdown_history else 0,
            'drawdown_duration': self._calculate_drawdown_duration()
        }
    
    def _calculate_drawdown_duration(self) -> Optional[timedelta]:
        """
        محاسبه مدت زمان دراو‌داون فعلی
        """
        if self.current_drawdown <= 0 or not self.peak_equity_time:
            return None
        
        return datetime.now() - self.peak_equity_time
    
    def is_safe_to_trade(self, max_allowed_drawdown: float = 15) -> bool:
        """
        بررسی امن بودن برای معامله
        
        Args:
            max_allowed_drawdown: حداکثر دراو‌داون مجاز
            
        Returns:
            bool: آیا معامله امن است
        """
        return self.current_drawdown < max_allowed_drawdown
    
    def reset_peak(self):
        """بازنشانی اوج equity (برای شروع مجدد)"""
        if self.equity_history:
            self.max_equity = self.equity_history[-1]['equity']
            self.peak_equity_time = datetime.now()
            logger.info("Peak equity reset")