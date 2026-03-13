"""
موتور بک‌تست برای استراتژی SP2L
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import json

from ..core.strategy import SP2LStrategy
from ..risk_management.position_sizer import PositionSizer
from ..utils.logger import get_logger
from ..utils.helpers import load_config, safe_divide
from tqdm import tqdm


logger = get_logger(__name__)

class BacktestEngine:
    """
    موتور بک‌تست برای ارزیابی استراتژی
    """
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Args:
            config_path: مسیر فایل تنظیمات
        """
        self.config = load_config(config_path)
        self.logger = get_logger(__name__)
        
        # تنظیمات بک‌تست
        backtest_config = self.config.get('backtest', {})
        self.start_date = backtest_config.get('start_date', '2024-01-01')
        self.end_date = backtest_config.get('end_date', '2024-12-31')
        self.initial_balance = backtest_config.get('initial_balance', 10000)
        self.commission = backtest_config.get('commission', 0.0)
        self.slippage = backtest_config.get('slippage', 1)
        
        # نماد معاملاتی
        self.symbol = self.config.get('trading', {}).get('symbol', 'XAUUSD')
        self.timeframe = self.config.get('trading', {}).get('timeframe', 'M5')
        
        # استراتژی
        self.strategy = SP2LStrategy(self.config)
        
        # تاریخچه معاملات
        self.trades = []
        self.equity_curve = []
        self.balance = self.initial_balance
        self.equity = self.initial_balance
        
    def load_data(self, data_path: Optional[str] = None) -> pd.DataFrame:
        """
        بارگذاری داده‌های تاریخی - اولویت با داده‌های واقعی
        """
        try:
            # اگر مسیر داده شد، همان را بارگذاری کن
            if data_path and Path(data_path).exists():
                df = pd.read_csv(data_path, index_col=0, parse_dates=True)
                logger.info(f"Data loaded from {data_path}: {len(df)} bars")
                return df
            
            # دنبال فایل داده‌های واقعی بگرد
            data_dir = Path(f"data/historical/{self.symbol}/{self.timeframe}")
            if data_dir.exists():
                csv_files = list(data_dir.glob("*.csv"))
                if csv_files:
                    # جدیدترین فایل را انتخاب کن
                    latest_file = max(csv_files, key=lambda x: x.stat().st_mtime)
                    df = pd.read_csv(latest_file, index_col=0, parse_dates=True)
                    logger.info(f"Real data loaded from {latest_file}: {len(df)} bars")
                    return df
            
            # اگر داده‌ای نبود، داده ساختگی تولید کن
            logger.warning("No real data file found, generating synthetic data")
            return self._generate_synthetic_data()
            
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            return self._generate_synthetic_data()
    
    def _generate_synthetic_data(self) -> pd.DataFrame:
        """
        تولید داده‌های ساختگی برای تست
        """
        try:
            # تعداد کندل‌ها (حدود 3 ماه داده 5 دقیقه‌ای)
            num_bars = 3 * 30 * 24 * 12  # 3 ماه * 30 روز * 24 ساعت * 12 (5 دقیقه)
            
            start = datetime.strptime(self.start_date, '%Y-%m-%d')
            end = datetime.strptime(self.end_date, '%Y-%m-%d')
            
            # ایجاد ایندکس زمانی
            dates = pd.date_range(start=start, end=end, freq='5min')
            
            # تولید داده‌های قیمت با روند و نوسان
            np.random.seed(42)
            
            # قیمت پایه برای طلا
            base_price = 2000
            
            # روند
            trend = np.linspace(0, 200, len(dates))
            
            # نوسانات
            noise = np.random.randn(len(dates)) * 10
            volatility = np.sin(np.linspace(0, 50, len(dates))) * 20
            
            # ساخت داده‌ها
            close_prices = base_price + trend + noise + volatility
            close_prices = np.maximum(close_prices, base_price * 0.8)  # حداقل قیمت
            
            # ساخت OHLC
            df = pd.DataFrame(index=dates)
            df['close'] = close_prices
            df['open'] = df['close'].shift(1) + np.random.randn(len(df)) * 2
            df['high'] = df[['open', 'close']].max(axis=1) + abs(np.random.randn(len(df)) * 5)
            df['low'] = df[['open', 'close']].min(axis=1) - abs(np.random.randn(len(df)) * 5)
            df['tick_volume'] = np.random.randint(100, 1000, len(df))
            
            # پر کردن مقادیر اولیه
            df.loc[df.index[0], 'open'] = df.loc[df.index[0], 'close'] - 2
            df.loc[df.index[0], 'high'] = df.loc[df.index[0], 'close'] + 5
            df.loc[df.index[0], 'low'] = df.loc[df.index[0], 'close'] - 5
            
            logger.info(f"Synthetic data generated: {len(df)} bars")
            return df
            
        except Exception as e:
            logger.error(f"Error generating synthetic data: {e}")
            return pd.DataFrame()
    
    def run(self, data: Optional[pd.DataFrame] = None, show_progress: bool = True) -> Dict:
        try:
            if data is None:
                data = self.load_data()
            
            if data.empty:
                logger.error("No data for backtest")
                return {}
            
            logger.info(f"Starting backtest with {len(data)} bars")
            
            # بازنشانی متغیرها
            self.trades = []
            self.equity_curve = [{'time': data.index[0], 'equity': self.initial_balance}]
            self.balance = self.initial_balance
            self.equity = self.initial_balance
            self.in_trade_until = None
            
            # ایجاد حلقه با نوار پیشرفت
            iterator = tqdm(range(60, len(data)), desc="Backtesting") if show_progress else range(60, len(data))
            
            for i in iterator:
                current_time = data.index[i]
                current_data = data.iloc[:i+1]
                
                if self.in_trade_until is not None and current_time <= self.in_trade_until:
                    # Skip signal generation while in a trade
                    self._update_equity(current_data, current_time)
                    continue
                
                # بررسی سیگنال
                analysis = self.strategy.analyze(current_data)
                
                # اجرای معامله در صورت وجود سیگنال
                if analysis['signal']['type'] != 'neutral':
                    future_data = data.iloc[i+1:]
                    self._execute_backtest_trade(analysis, current_time, future_data)
                
                # به‌روزرسانی equity
                self._update_equity(current_data, current_time)
            
            # محاسبه آمار
            results = self._calculate_results()
            
            # ذخیره نتایج
            self._save_results(results)
            
            logger.info(f"Backtest completed. Total trades: {len(self.trades)}")
            return results
            
        except Exception as e:
            logger.error(f"Error in backtest: {e}")
            return {}
    
    def _simulate_real_trade(self, entry: float, sl: float, tp: float, volume: float, trade_type: str) -> float:
        """
        شبیه‌سازی واقعی معامله با احتمال رسیدن به حد سود و ضرر
        """
        try:
            import random
            
            # محاسبه فاصله به دلار (برای طلا)
            if trade_type == 'buy':
                profit_dollars = (tp - entry) * 100 * volume
                loss_dollars = (sl - entry) * 100 * volume
            else:  # sell
                profit_dollars = (entry - tp) * 100 * volume
                loss_dollars = (entry - sl) * 100 * volume
            
            # محاسبه نسبت ریسک به ریوارد
            risk_reward = abs(profit_dollars / loss_dollars) if loss_dollars != 0 else 1
            
            # احتمال موفقیت بر اساس نسبت ریسک به ریوارد
            # هرچه ریسک به ریوارد بالاتر، احتمال موفقیت کمتر
            success_probability = 1 / (1 + risk_reward)
            
            # شبیه‌سازی با احتمال واقعی
            if random.random() < success_probability:
                return round(profit_dollars, 2)
            else:
                return round(-abs(loss_dollars), 2)  # منفی برای ضرر
                
        except Exception as e:
            logger.error(f"Error simulating trade: {e}")
            return 0
    def _execute_backtest_trade(self, analysis: Dict, current_time: datetime, future_data: pd.DataFrame = None):
        """
        اجرای معامله در بک‌تست با بررسی داده‌های آینده
        """
        try:
            signal = analysis['signal']
            
            # حجم معامله ثابت و واقعی (مثلاً 0.1 لات استاندارد)
            volume = 0.1  # حجم ثابت برای جلوگیری از سودهای غیرواقعی
            
            trade_type = signal['type']
            entry_price = signal['entry']
            stop_loss = signal['sl']
            take_profit = signal['tp']
            
            profit = 0
            trade_closed = False
            close_time = None
            
            if trade_type not in ['buy', 'sell']:
                return
                
            if future_data is not None and not future_data.empty:
                highs = future_data['high'].values
                lows = future_data['low'].values
                
                for i in range(len(highs)):
                    high = highs[i]
                    low = lows[i]
                    current_future_time = future_data.index[i]
                    
                    if trade_type == 'buy':
                        if low <= stop_loss:
                            profit = (stop_loss - entry_price) * 100 * volume
                            trade_closed = True
                            close_time = current_future_time
                            break
                        elif high >= take_profit:
                            profit = (take_profit - entry_price) * 100 * volume
                            trade_closed = True
                            close_time = current_future_time
                            break
                    elif trade_type == 'sell':
                        if high >= stop_loss:
                            profit = (entry_price - stop_loss) * 100 * volume
                            trade_closed = True
                            close_time = current_future_time
                            break
                        elif low <= take_profit:
                            profit = (entry_price - take_profit) * 100 * volume
                            trade_closed = True
                            close_time = current_future_time
                            break
                
                if not trade_closed:
                    last_price = future_data.iloc[-1]['close']
                    if trade_type == 'buy':
                        profit = (last_price - entry_price) * 100 * volume
                    else:
                        profit = (entry_price - last_price) * 100 * volume
                    close_time = future_data.index[-1]
            else:
                profit = self._simulate_real_trade(entry_price, stop_loss, take_profit, volume, trade_type)
                close_time = current_time
            
            self.in_trade_until = close_time
            
            profit = round(profit, 2)
            
            # ثبت معامله
            trade = {
                'time': current_time,
                'type': signal['type'],
                'entry': signal['entry'],
                'sl': signal['sl'],
                'tp': signal['tp'],
                'volume': volume,
                'profit': profit,
                'balance_before': self.balance,
                'balance_after': self.balance + profit
            }
            
            self.trades.append(trade)
            self.balance += profit
            
            logger.debug(f"Trade executed: {trade['type']} at {trade['entry']:.2f}, profit: {profit:.2f}")
            
        except Exception as e:
            logger.error(f"Error executing backtest trade: {e}")
    
    def _update_equity(self, data: pd.DataFrame, current_time: datetime):
            """
            به‌روزرسانی equity
            """
            try:
                # در بک‌تست ساده، equity = balance
                self.equity = self.balance
                
                self.equity_curve.append({
                    'time': current_time,
                    'equity': self.equity,
                    'balance': self.balance
                })
                
            except Exception as e:
                logger.error(f"Error updating equity: {e}")
    
    def _calculate_results(self) -> Dict:
        """
        محاسبه آمار بک‌تست
        """
        try:
            if len(self.trades) == 0:
                return {
                    'total_trades': 0,
                    'initial_balance': self.initial_balance,
                    'final_balance': self.balance,
                    'total_profit': self.balance - self.initial_balance,
                    'return_percentage': 0
                }
            
            # محاسبه آمار پایه
            profits = [t['profit'] for t in self.trades]
            winning_trades = [p for p in profits if p > 0]
            losing_trades = [p for p in profits if p < 0]
            
            total_profit = self.balance - self.initial_balance
            return_pct = (total_profit / self.initial_balance) * 100
            
            win_rate = (len(winning_trades) / len(self.trades)) * 100 if self.trades else 0
            
            avg_win = np.mean(winning_trades) if winning_trades else 0
            avg_loss = abs(np.mean(losing_trades)) if losing_trades else 0
            
            profit_factor = safe_divide(sum(winning_trades), abs(sum(losing_trades)))
            
            # محاسبه دراو‌داون
            equity_values = [e['equity'] for e in self.equity_curve]
            max_equity = np.maximum.accumulate(equity_values)
            drawdowns = (max_equity - equity_values) / max_equity * 100
            max_drawdown = np.max(drawdowns) if len(drawdowns) > 0 else 0
            
            # محاسبه نسبت شارپ (ساده شده)
            returns = np.diff(equity_values) / equity_values[:-1]
            sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if len(returns) > 0 else 0
            
            results = {
                'total_trades': len(self.trades),
                'winning_trades': len(winning_trades),
                'losing_trades': len(losing_trades),
                'win_rate': win_rate,
                'initial_balance': self.initial_balance,
                'final_balance': self.balance,
                'total_profit': total_profit,
                'return_percentage': return_pct,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'profit_factor': profit_factor,
                'max_drawdown': max_drawdown,
                'sharpe_ratio': sharpe_ratio,
                'trades': self.trades,
                'equity_curve': self.equity_curve
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Error calculating results: {e}")
            return {}
    
    def _save_results(self, results: Dict):
        """
        ذخیره نتایج بک‌تست
        """
        try:
            output_dir = Path("data/exports/backtest_results")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"backtest_{self.symbol}_{self.timeframe}_{timestamp}.json"
            filepath = output_dir / filename
            
            # حذف داده‌های بزرگ برای ذخیره
            results_to_save = results.copy()
            if 'trades' in results_to_save:
                results_to_save['trades'] = len(results_to_save['trades'])
            if 'equity_curve' in results_to_save:
                results_to_save['equity_curve'] = len(results_to_save['equity_curve'])
            
            with open(filepath, 'w') as f:
                json.dump(results_to_save, f, indent=2, default=str)
            
            logger.info(f"Results saved to {filepath}")
            
        except Exception as e:
            logger.error(f"Error saving results: {e}")
    
    def generate_report(self, results: Dict) -> str:
        """
        تولید گزارش متنی از نتایج
        """
        try:
            report = []
            report.append("=" * 50)
            report.append("SP2L STRATEGY BACKTEST REPORT")
            report.append("=" * 50)
            report.append(f"Symbol: {self.symbol}")
            report.append(f"Timeframe: {self.timeframe}")
            report.append(f"Period: {self.start_date} to {self.end_date}")
            report.append("-" * 50)
            report.append(f"Initial Balance: ${results.get('initial_balance', 0):,.2f}")
            report.append(f"Final Balance: ${results.get('final_balance', 0):,.2f}")
            report.append(f"Total Profit: ${results.get('total_profit', 0):,.2f}")
            report.append(f"Return: {results.get('return_percentage', 0):.2f}%")
            report.append("-" * 50)
            report.append(f"Total Trades: {results.get('total_trades', 0)}")
            report.append(f"Winning Trades: {results.get('winning_trades', 0)}")
            report.append(f"Losing Trades: {results.get('losing_trades', 0)}")
            report.append(f"Win Rate: {results.get('win_rate', 0):.2f}%")
            report.append(f"Avg Win: ${results.get('avg_win', 0):,.2f}")
            report.append(f"Avg Loss: ${results.get('avg_loss', 0):,.2f}")
            report.append(f"Profit Factor: {results.get('profit_factor', 0):.2f}")
            report.append("-" * 50)
            report.append(f"Max Drawdown: {results.get('max_drawdown', 0):.2f}%")
            report.append(f"Sharpe Ratio: {results.get('sharpe_ratio', 0):.2f}")
            report.append("=" * 50)
            
            report_str = "\n".join(report)
            print(report_str)
            
            # ذخیره گزارش
            output_dir = Path("data/exports/backtest_results")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = output_dir / f"report_{timestamp}.txt"
            
            with open(report_file, 'w') as f:
                f.write(report_str)
            
            logger.info(f"Report saved to {report_file}")
            
            return report_str
            
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return ""