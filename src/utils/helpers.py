"""
توابع کمکی عمومی
"""
import yaml
import json
import pandas as pd
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime
import pytz

from .env_loader import load_environment

def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """
    بارگذاری فایل تنظیمات با تزریق متغیرهای محیطی
    """
    # ۱. بارگذاری متغیرهای محیطی از .env یا سیستم
    env_vars = load_environment()
    
    # ۲. بررسی Streamlit Secrets (برای زمان دیپلوی روی کلود)
    try:
        import streamlit as st
        # اگر در محیط استریم‌لیت باشیم، سکرت‌ها را هم اضافه می‌کنیم
        for key in ['MT5_LOGIN', 'MT5_PASSWORD', 'MT5_SERVER', 'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID']:
            if key in st.secrets:
                env_vars[key.lower().replace('mt5_', '')] = str(st.secrets[key])
                # همچنین برای تلگرام
                if key.startswith('TELEGRAM'):
                    env_vars[key.lower()] = str(st.secrets[key])
    except:
        pass
    
    config_file = Path(config_path)
    
    # اگر فایل وجود نداشت، تنظیمات پیش‌فرض
    if not config_file.exists():
        return {
            'mt5': {
                'path': "C:/Program Files/MetaTrader 5/terminal64.exe",
                'login': int(env_vars.get('login', 0)),
                'server': env_vars.get('server', ''),
                'password': env_vars.get('password', ''),
                'timeout': 5000
            },
            'trading': {
                'symbol': 'XAUUSD',
                'timeframe': 'M5',
                'volume': 0.01,
                'magic_number': 234000
            },
            'strategy': {
                'min_higher_lows': 3,
                'ma_period': 60,
                'risk_reward_ratio': 2.0
            },
            'risk_management': {
                'max_risk_per_trade': 1.0,
                'max_open_positions': 1
            },
            'logging': {
                'level': 'INFO',
                'file': 'logs/trading.log'
            }
        }
    
    # خواندن فایل بر اساس پسوند
    with open(config_file, 'r', encoding='utf-8') as f:
        if config_file.suffix in ['.yaml', '.yml']:
            config = yaml.safe_load(f)
        elif config_file.suffix == '.json':
            config = json.load(f)
        else:
            raise ValueError(f"Unsupported config file format: {config_file.suffix}")
            
    # تزریق متغیرهای محیطی به تنظیمات mt5
    if 'mt5' in config:
        # فقط در صورتی که در .env تعریف شده باشند جایگزین کن
        if env_vars.get('login') and env_vars['login'] != '12345678':
            login_val = env_vars['login']
            try:
                config['mt5']['login'] = int(login_val)
            except ValueError:
                config['mt5']['login'] = login_val
        if env_vars.get('password'):
            config['mt5']['password'] = env_vars['password']
        if env_vars.get('server') and env_vars['server'] != 'BrokerServer':
            config['mt5']['server'] = env_vars['server']
            
    return config

def save_config(config: Dict[str, Any], config_path: str = "config.yaml"):
    """
    ذخیره تنظیمات در فایل
    
    Args:
        config: تنظیمات
        config_path: مسیر فایل تنظیمات
    """
    config_file = Path(config_path)
    config_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_file, 'w', encoding='utf-8') as f:
        if config_file.suffix == '.yaml' or config_file.suffix == '.yml':
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        elif config_file.suffix == '.json':
            json.dump(config, f, indent=2, ensure_ascii=False)

def safe_divide(a: float, b: float, default: float = 0.0) -> float:
    """
    تقسیم ایمن (جلوگیری از تقسیم بر صفر)
    """
    if b == 0 or b is None:
        return default
    return a / b

def pips_to_price(pips: float, point: float, digits: int) -> float:
    """
    تبدیل پیپ به قیمت
    
    Args:
        pips: تعداد پیپ
        point: مقدار point
        digits: تعداد ارقام اعشار
        
    Returns:
        float: معادل قیمت
    """
    pip_size = point * (10 if digits in [3, 5] else 1)
    return pips * pip_size

def price_to_pips(price_diff: float, point: float, digits: int) -> float:
    """
    تبدیل اختلاف قیمت به پیپ
    
    Args:
        price_diff: اختلاف قیمت
        point: مقدار point
        digits: تعداد ارقام اعشار
        
    Returns:
        float: تعداد پیپ
    """
    pip_size = point * (10 if digits in [3, 5] else 1)
    return price_diff / pip_size

def get_current_time(timezone: str = 'UTC') -> datetime:
    """
    دریافت زمان فعلی در منطقه زمانی مشخص
    
    Args:
        timezone: منطقه زمانی (مثلاً 'Asia/Tehran', 'UTC')
        
    Returns:
        datetime: زمان فعلی
    """
    tz = pytz.timezone(timezone)
    return datetime.now(tz)

def calculate_pip_value(symbol: str, volume: float, quote_currency: str = 'USD') -> float:
    """
    محاسبه ارزش هر پیپ
    
    Args:
        symbol: نماد معاملاتی
        volume: حجم معامله
        quote_currency: ارز پایه
        
    Returns:
        float: ارزش هر پیپ
    """
    # این تابع باید با توجه به بروکر تکمیل شود
    # یک پیپ استاندارد برای جفت‌ارزهای اصلی 10 واحد ارز پایه است
    if 'JPY' in symbol:
        return volume * 1000  # برای جفت‌ارزهای ینی
    else:
        return volume * 10  # برای سایر جفت‌ارزها

def format_number(number: float, decimals: int = 2) -> str:
    """
    فرمت عدد با جداکننده هزارگان
    
    Args:
        number: عدد
        decimals: تعداد اعشار
        
    Returns:
        str: عدد فرمت شده
    """
    return f"{number:,.{decimals}f}"

def create_directory(path: str) -> Path:
    """
    ایجاد پوشه در صورت عدم وجود
    
    Args:
        path: مسیر پوشه
        
    Returns:
        Path: آبجکت مسیر
    """
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path