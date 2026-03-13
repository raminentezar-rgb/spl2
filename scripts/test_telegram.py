"""
تست اتصال به تلگرام
"""
import sys
from pathlib import Path

# اضافه کردن مسیر پروژه
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.helpers import load_config
from src.utils.telegram_bot import TelegramBot

def test():
    print("🔄 Loading config and env...")
    config = load_config()
    
    bot = TelegramBot()
    
    print(f"📡 Sending test message to Chat ID: {bot.chat_id}...")
    success = bot.send_message("✅ <b>اتصال برقرار شد!</b>\nربات معاملاتی SP2L آماده ارسال سیگنال است.")
    
    if success:
        print("🚀 Test message sent successfully!")
    else:
        print("❌ Failed to send test message. Check your Token and Chat ID.")

if __name__ == "__main__":
    test()
