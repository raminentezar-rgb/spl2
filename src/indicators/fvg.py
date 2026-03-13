"""
تشخیص گپ ارزش منصفانه (Fair Value Gap - FVG)
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional

class FVGIndicator:
    """
    شناسایی FVG صعودی و نزولی
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
    def calculate(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        محاسبه FVG در کل دیتافریم
        
        Args:
            data: دیتافریم شامل Open, High, Low, Close
            
        Returns:
            pd.DataFrame: دیتافریم با ستون‌های fvg_bull و fvg_bear
        """
        df = data.copy()
        df['fvg_bull'] = False
        df['fvg_bear'] = False
        df['fvg_top'] = np.nan
        df['fvg_bottom'] = np.nan
        
        # FVG نیاز به حداقل 3 کندل دارد
        # Bullish FVG: Low(i) > High(i-2)
        # Bearish FVG: High(i) < Low(i-2)
        
        highs = df['high'].values
        lows = df['low'].values
        
        for i in range(2, len(df)):
            # Bullish FVG
            if lows[i] > highs[i-2]:
                df.at[df.index[i-1], 'fvg_bull'] = True
                df.at[df.index[i-1], 'fvg_top'] = lows[i]
                df.at[df.index[i-1], 'fvg_bottom'] = highs[i-2]
                
            # Bearish FVG
            elif highs[i] < lows[i-2]:
                df.at[df.index[i-1], 'fvg_bear'] = True
                df.at[df.index[i-1], 'fvg_top'] = lows[i-2]
                df.at[df.index[i-1], 'fvg_bottom'] = highs[i]
                
        return df

    def is_present(self, data: pd.DataFrame, lookback: int = 5) -> Dict[str, bool]:
        """
        بررسی وجود FVG در کندل‌های اخیر
        """
        if len(data) < 3:
            return {'bullish': False, 'bearish': False}
            
        df_fvg = self.calculate(data.tail(lookback + 2))
        
        return {
            'bullish': df_fvg['fvg_bull'].any(),
            'bearish': df_fvg['fvg_bear'].any()
        }
