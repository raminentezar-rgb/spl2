import requests
import os
from datetime import datetime
from .logger import get_logger

logger = get_logger(__name__)

class TelegramBot:
    """
    ارسال نوتیفیکیشن و سیگنال به تلگرام
    """
    
    def __init__(self, token: str = None, chat_ids: list = None):
        self.token = token or os.getenv('TELEGRAM_BOT_TOKEN')
        # تبدیل ورودی به لیست اگر تکی باشد
        if isinstance(chat_ids, str):
            self.chat_ids = [chat_ids]
        else:
            self.chat_ids = chat_ids or [os.getenv('TELEGRAM_CHAT_ID')]
        
        self.base_url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        
    def send_message(self, text: str) -> bool:
        """ارسال پیام متنی به همه گیرنده‌ها"""
        if not self.token or not self.chat_ids:
            logger.warning("Telegram Token or Chat IDs not set")
            return False
            
        success = True
        for chat_id in self.chat_ids:
            try:
                payload = {
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "HTML"
                }
                response = requests.post(self.base_url, json=payload, timeout=10)
                
                if response.status_code != 200:
                    logger.error(f"Telegram error for {chat_id}: {response.text}")
                    success = False
            except Exception as e:
                logger.error(f"Error sending to {chat_id}: {e}")
                success = False
        
        return success
            
    def send_signal(self, symbol: str, signal_type: str, entry: float, sl: float, tp: float, timeframe: str = "N/A"):
        """ارسال سیگنال معاملاتی با فرمت زیبا"""
        emoji = "🚀" if signal_type == 'buy' else "📉"
        type_str = "BUY" if signal_type == 'buy' else "SELL"
        
        message = (
            f"{emoji} <b>SP2L NEW SIGNAL</b> {emoji}\n\n"
            f"<b>Symbol:</b> {symbol}\n"
            f"<b>Timeframe:</b> {timeframe}\n"
            f"<b>Type:</b> {type_str}\n"
            f"<b>Entry:</b> {entry:.5f}\n"
            f"<b>Stop Loss:</b> {sl:.5f}\n"
            f"<b>Take Profit:</b> {tp:.5f}\n\n"
            f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        return self.send_message(message)

