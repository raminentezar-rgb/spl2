"""
مدیریت لاگ‌گیری پروژه
"""
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional
import colorlog

# تنظیمات پیش‌فرض
DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DEFAULT_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# رنگ‌ها برای کنسول
COLORED_FORMAT = '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s'
COLORS = {
    'DEBUG': 'cyan',
    'INFO': 'green',
    'WARNING': 'yellow',
    'ERROR': 'red',
    'CRITICAL': 'red,bg_white',
}

def setup_logger(
    name: str,
    log_file: Optional[str] = None,
    level: int = DEFAULT_LOG_LEVEL,
    console: bool = True,
    max_bytes: int = 10485760,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    تنظیم و ایجاد logger
    
    Args:
        name: نام logger
        log_file: مسیر فایل لاگ (اختیاری)
        level: سطح لاگ
        console: نمایش در کنسول
        max_bytes: حداکثر حجم فایل لاگ
        backup_count: تعداد فایل‌های پشتیبان
        
    Returns:
        logging.Logger: نمونه logger تنظیم شده
    """
    logger = logging.getLogger(name)
    
    # جلوگیری از اضافه شدن چندباره هندلرها
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    # فرمت لاگ
    formatter = logging.Formatter(
        DEFAULT_LOG_FORMAT,
        datefmt=DEFAULT_DATE_FORMAT
    )
    
    # هندلر فایل (اگر مسیر داده شده باشد)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # هندلر کنسول
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        
        # استفاده از رنگ‌ها برای کنسول
        color_formatter = colorlog.ColoredFormatter(
            COLORED_FORMAT,
            datefmt=DEFAULT_DATE_FORMAT,
            log_colors=COLORS
        )
        console_handler.setFormatter(color_formatter)
        logger.addHandler(console_handler)
    
    return logger

def get_logger(name: str) -> logging.Logger:
    """
    دریافت یک logger موجود یا ایجاد logger جدید با تنظیمات پیش‌فرض
    
    Args:
        name: نام logger
        
    Returns:
        logging.Logger: نمونه logger
    """
    logger = logging.getLogger(name)
    
    # اگر logger تنظیمات ندارد، با تنظیمات پیش‌فرض ایجاد کن
    if not logger.handlers:
        # تلاش برای خواندن از config
        try:
            from ..utils.helpers import load_config
            config = load_config()
            log_config = config.get('logging', {})
            
            logger = setup_logger(
                name,
                log_file=log_config.get('file', 'logs/trading.log'),
                level=getattr(logging, log_config.get('level', 'INFO'))
            )
        except:
            # اگر config در دسترس نیست، از تنظیمات پیش‌فرض استفاده کن
            logger = setup_logger(name, log_file='logs/trading.log')
    
    return logger

# مثال استفاده:
if __name__ == "__main__":
    # تست logger
    log = setup_logger('test', console=True)
    log.debug("This is a debug message")
    log.info("This is an info message")
    log.warning("This is a warning message")
    log.error("This is an error message")
    log.critical("This is a critical message")