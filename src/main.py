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
        self.position_sizers = {}
        
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
            
            # ۳. آماده‌سازی مدیریت سفارش (فلط اگر مود ترید فعال باشد)
            self.signal_only = self.config['trading'].get('signal_only', True)
            if not self.signal_only and self.data_source == 'mt5':
                self.order_manager = OrderManager(self.connector, self.config)
                for symbol in self.config['trading'].get('symbols', []):
                    symbol_info = self.connector.get_symbol_info(symbol)
                    if symbol_info:
                        self.position_sizers[symbol] = PositionSizer(self.config, symbol_info)
                    else:
                        self.logger.warning(f"Could not get symbol info for {symbol}")
            
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
        بررسی بازار و انجام معامله برای تمام ارزها
        """
        try:
            symbols = self.config['trading'].get('symbols', [])
            timeframe = self.config['trading']['timeframe']
            
            for symbol in symbols:
                # 1. دریافت داده‌های جدید
                if self.data_source == 'mt5':
                    data = self.connector.get_rates(symbol, timeframe, count=100)
                else:
                    data = self.yahoo_connector.get_rates(symbol, timeframe, count=100)
                
                if data is None or len(data) < 60:
                    self.logger.warning(f"Insufficient data for {symbol} from {self.data_source}")
                    continue
                
                # 2. تحلیل با استراتژی
                analysis = self.strategy.analyze(data)
                self.last_signal = analysis # ذخیره آخرین تحلیل برای مانیتورینگ عمومی
                
                # 3. بررسی و اعلام سیگنال
                if analysis['signal']['type'] != 'neutral':
                    self.logger.info(f"Signal detected for {symbol}: {analysis['signal']['type']}")
                    
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
                        self._execute_signal(symbol, analysis, account, positions)
            
        except Exception as e:
            self.logger.error(f"Error in check_and_trade: {e}")
    
    def _execute_signal(self, symbol, analysis, account, positions):
        """
        اجرای سیگنال معاملاتی
        """
        signal = analysis['signal']
        
        # دریافت سایزر مخصوص این نماد
        sizer = self.position_sizers.get(symbol)
        if not sizer:
            self.logger.error(f"No position sizer found for {symbol}")
            return
            
        # محاسبه حجم معامله
        volume = sizer.calculate_position_size(
            account['balance'],
            signal['entry'],
            signal['sl'],
            self.config['risk_management']['max_risk_per_trade']
        )
        
        # اجرای معامله
        result = None
        if signal['type'] == 'buy':
            result = self.order_manager.place_buy_order(
                symbol=symbol,
                volume=volume,
                sl=signal['sl'],
                tp=signal['tp'],
                comment=f"SP2L Buy Signal {symbol}"
            )
            
        elif signal['type'] == 'sell':
            result = self.order_manager.place_sell_order(
                symbol=symbol,
                volume=volume,
                sl=signal['sl'],
                tp=signal['tp'],
                comment=f"SP2L Sell Signal {symbol}"
            )
        
        if result and result.get('success'):
            self.logger.info(f"Order executed: {symbol} {signal['type']} at {signal['entry']}")
            # تاییدیه در تلگرام
            self.telegram.send_message(f"✅ <b>ORDER EXECUTED</b>\nSymbol: {symbol}\nType: {signal['type']}\nVolume: {volume}\nEntry: {signal['entry']}")
        else:
            error_msg = result.get('error') if result else "Unknown error"
            self.logger.error(f"Order failed for {symbol}: {error_msg}")
            self.telegram.send_message(f"❌ <b>FAILED</b> to place {signal['type']} order for {symbol}\nError: {error_msg}")
    
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