"""
نقطه ورود اصلی برنامه
اجرای ربات معاملاتی SP2L
"""
import time
import yaml
import schedule
from datetime import datetime
from pathlib import Path
from typing import Dict

from src.core.strategy import SP2LStrategy
from src.mt5_connector.connector import MT5Connector
from src.mt5_connector.order_manager import OrderManager
from src.risk_management.position_sizer import PositionSizer
from src.utils.logger import setup_logger
from src.utils.helpers import load_config
from src.utils.telegram_bot import TelegramBot
from src.utils.yfinance_connector import YahooFinanceConnector

class SP2LTradingBot:
    """
    ربات معاملاتی اصلی SP2L
    """
    
    def __init__(self, config_path: str = "config.yaml"):
        # بارگذاری تنظیمات
        self.config = load_config(config_path)
        self.logger = setup_logger(__name__)
        
        # کامپوننت‌ها
        self.connector = None
        self.strategy = None
        self.order_manager = None
        self.position_sizer = None
        
        # وضعیت
        self.is_running = False
        self.last_signal = None
        
        # تلگرام
        self.telegram = TelegramBot(
            self.config.get('telegram', {}).get('token'),
            self.config.get('telegram', {}).get('chat_id')
        )
        
    def initialize(self) -> bool:
        """
        مقداردهی اولیه همه کامپوننت‌ها
        """
        try:
            # ۱. انتخاب منبع داده
            self.data_source = self.config['trading'].get('data_source', 'mt5')
            
            if self.data_source == 'mt5':
                self.connector = MT5Connector(self.config)
                if not self.connector.connect():
                    self.logger.error("Failed to connect to MT5, falling back to Yahoo Finance")
                    self.data_source = 'yahoo'
                    self.yahoo_connector = YahooFinanceConnector()
            else:
                self.yahoo_connector = YahooFinanceConnector()
            
            # ۲. ایجاد استراتژی
            self.strategy = SP2LStrategy(self.config)
            
            # ۳. آماده‌سازی مدیریت سفارش (فقط اگر مود ترید فعال باشد)
            self.signal_only = self.config['trading'].get('signal_only', True)
            if not self.signal_only and self.data_source == 'mt5':
                symbol_info = self.connector.get_symbol_info(self.config['trading']['symbol'])
                self.order_manager = OrderManager(self.connector, self.config)
                self.position_sizer = PositionSizer(self.config, symbol_info)
            
            self.logger.info(f"Bot initialized in {self.data_source} mode (Signal Only: {self.signal_only})")
            return True
            
        except Exception as e:
            self.logger.error(f"Initialization error: {e}")
            return False
    
    def run_live(self):
        """
        اجرای زنده ربات
        """
        if not self.initialize():
            return
        
        self.is_running = True
        self.logger.info("Starting live trading...")
        
        # برنامه زمانبندی
        schedule.every(1).minutes.do(self.check_and_trade)
        
        try:
            while self.is_running:
                schedule.run_pending()
                time.sleep(1)
                
        except KeyboardInterrupt:
            self.logger.info("Bot stopped by user")
        finally:
            self.shutdown()
    
    def check_and_trade(self):
        """
        بررسی بازار و انجام معامله
        """
        try:
            # 1. دریافت داده‌های جدید
            symbol = self.config['trading']['symbol']
            timeframe = self.config['trading']['timeframe']
            
            if self.data_source == 'mt5':
                data = self.connector.get_rates(symbol, timeframe, count=100)
            else:
                data = self.yahoo_connector.get_rates(symbol, timeframe, count=100)
            
            if data is None or len(data) < 60:
                self.logger.warning(f"Insufficient data from {self.data_source}")
                return
            
            # 2. تحلیل با استراتژی
            analysis = self.strategy.analyze(data)
            self.last_signal = analysis
            
            # 3. بررسی و اعلام سیگنال
            if analysis['signal']['type'] != 'neutral':
                # ارسال به تلگرام (همیشه انجام می‌شود)
                self.telegram.send_signal(
                    symbol=symbol,
                    signal_type=analysis['signal']['type'],
                    entry=analysis['signal']['entry'],
                    sl=analysis['signal']['sl'],
                    tp=analysis['signal']['tp']
                )
                
                # اجرای معامله (فقط اگر سیگنال‌اونلی نباشد)
                if not self.signal_only and self.data_source == 'mt5':
                    account = self.connector.get_account_info()
                    positions = self.connector.get_positions(symbol)
                    self._execute_signal(analysis, account, positions)
            
        except Exception as e:
            self.logger.error(f"Error in check_and_trade: {e}")
    
    def _execute_signal(self, analysis, account, positions):
        """
        اجرای سیگنال معاملاتی
        """
        signal = analysis['signal']
        
        # محاسبه حجم معامله
        volume = self.position_sizer.calculate_position_size(
            account['balance'],
            signal['entry'],
            signal['sl'],
            self.config['risk_management']['max_risk_per_trade']
        )
        
        # اجرای معامله
        if signal['type'] == 'buy':
            result = self.order_manager.place_buy_order(
                symbol=self.config['trading']['symbol'],
                volume=volume,
                sl=signal['sl'],
                tp=signal['tp'],
                comment="SP2L Buy Signal"
            )
            
        elif signal['type'] == 'sell':
            result = self.order_manager.place_sell_order(
                symbol=self.config['trading']['symbol'],
                volume=volume,
                sl=signal['sl'],
                tp=signal['tp'],
                comment="SP2L Sell Signal"
            )
        
        if result:
            self.logger.info(f"Order executed: {signal['type']} at {signal['entry']}")
            # ارسال نوتیفیکیشن تلگرام
            self.telegram.send_signal(
                symbol=self.config['trading']['symbol'],
                signal_type=signal['type'],
                entry=signal['entry'],
                sl=signal['sl'],
                tp=signal['tp']
            )
        else:
            self.logger.error(f"Order failed: {signal['type']}")
            self.telegram.send_message(f"❌ <b>FAILED</b> to place {signal['type']} order for {self.config['trading']['symbol']}")
    
    def shutdown(self):
        """
        خاموش کردن ربات
        """
        self.is_running = False
        if self.connector:
            self.connector.disconnect()
        self.logger.info("Bot shutdown complete")

def main():
    """
    تابع اصلی
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='SP2L Trading Bot')
    parser.add_argument('--config', type=str, default='config.yaml',
                       help='Path to config file')
    parser.add_argument('--mode', type=str, default='live',
                       choices=['live', 'backtest', 'optimize'],
                       help='Running mode')
    parser.add_argument('--once', action='store_true', help='Run one iteration and exit')
    
    args = parser.parse_args()
    
    if args.mode == 'live':
        bot = SP2LTradingBot(args.config)
        if bot.initialize():
            if args.once:
                bot.check_and_trade()
                bot.shutdown()
            else:
                bot.run_live()
    elif args.mode == 'backtest':
        # اجرای بک‌تست
        from src.backtesting.backtest_engine import BacktestEngine
        engine = BacktestEngine(args.config)
        results = engine.run()
        engine.generate_report(results)
    elif args.mode == 'optimize':
        # بهینه‌سازی پارامترها
        from scripts.optimize_params import ParameterOptimizer
        optimizer = ParameterOptimizer(args.config)
        optimizer.run()

if __name__ == "__main__":
    main()