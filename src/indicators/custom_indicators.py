"""
اندیکاتورهای سفارشی برای استراتژی SP2L
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional

class BigCandleFilter:
    """
    فیلتر کردن کندل‌های غیرعادی بزرگ (Big Candles)
    """
    
    def __init__(self, multiplier: float = 5.0):
        self.multiplier = multiplier
        
    def is_big_candle(self, data: pd.DataFrame) -> bool:
        """
        بررسی اینکه آیا کندل آخر بیش از حد بزرگ است یا خیر
        """
        if len(data) < 20:
            return False
            
        # محاسبه اندازه بدنه کندل‌ها
        bodies = abs(data['close'] - data['open']).values
        last_body = bodies[-1]
        
        # میانگین بدنه 20 کندل اخیر (بدون احتساب آخرین کندل)
        avg_body = np.mean(bodies[-21:-1])
        
        # اگر بدنه آخرین کندل بیش از X برابر میانگین باشد، Big Candle محسوب می‌شود
        return last_body > (avg_body * self.multiplier)
