import subprocess
import time
import sys
import logging
from datetime import datetime

# تنظیم لاگر اختصاصی برای نگهبان
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - WATCHDOG - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/watchdog.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def run_bot():
    """اجرای ربات و نظارت بر آن"""
    cmd = [sys.executable, "src/main.py"]
    
    while True:
        logger.info("Starting SP2L Trading Bot...")
        try:
            # اجرای پردازش و انتظار برای اتمام
            process = subprocess.Popen(cmd)
            process.wait()
            
            # اگر برنامه با خطا بسته شد (کد غیر صفر)
            if process.returncode != 0:
                logger.error(f"Bot crashed with exit code {process.returncode}. Restarting in 10 seconds...")
            else:
                logger.warning("Bot stopped normally. Restarting in 30 seconds...")
                
            time.sleep(10 if process.returncode != 0 else 30)
            
        except Exception as e:
            logger.error(f"Error in watchdog: {e}. Retrying in 60 seconds...")
            time.sleep(60)

if __name__ == "__main__":
    logger.info("Watchdog started. Press Ctrl+C to stop both watchdog and bot.")
    try:
        run_bot()
    except KeyboardInterrupt:
        logger.info("Watchdog stopped by user.")
