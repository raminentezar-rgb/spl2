"""
محاسبه نقاط پیوت (Pivot Points)
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional

class PivotPoints:
    """
    محاسبه سطوح پیوت استاندارد
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
    def calculate(self, high: float, low: float, close: float) -> Dict[str, float]:
        """
        محاسبه سطوح بر اساس HLC دوره قبلی
        """
        p = (high + low + close) / 3
        
        r1 = (p * 2) - low
        s1 = (p * 2) - high
        
        r2 = p + (high - low)
        s2 = p - (high - low)
        
        r3 = high + 2 * (p - low)
        s3 = low - 2 * (high - p)
        
        return {
            'p': p,
            'r1': r1, 's1': s1,
            'r2': r2, 's2': s2,
            'r3': r3, 's3': s3
        }

    def get_latest_pivots(self, data: pd.DataFrame, period: str = 'D') -> Dict[str, float]:
        """
        دریافت آخرین سطوح پیوت بر اساس تایم‌فریم مشخص (پیش‌فرض روزانه)
        """
        if len(data) < 2:
            return {}
            
        # در اینجا فرض می‌کنیم دیتای ورودی شامل اوپن روزانه است یا 
        # باید منطق تجمیع (Resample) داشته باشیم.
        # برای سادگی، فعلاً از High/Low/Close کل دیتا استفاده می‌کنیم
        
        h = data['high'].max()
        l = data['low'].min()
        c = data['close'].iloc[-1]
        
        return self.calculate(h, l, c)
