
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.backtesting.backtest_engine import BacktestEngine
from src.utils.yfinance_connector import YahooFinanceConnector
from src.utils.helpers import load_config

def run_comprehensive_backtest():
    config = load_config("config.yaml")
    symbols = config['trading'].get('symbols', ['XAUUSD'])
    timeframes = config['trading'].get('timeframes', ['M5', 'M15'])
    
    connector = YahooFinanceConnector()
    results_summary = []
    
    print(f"Starting Backtest for {len(symbols)} symbols across {len(timeframes)} timeframes...")
    
    for symbol in symbols:
        for tf in timeframes:
            print(f"\nProcessing {symbol} @ {tf}...")
            
            # 1. Fetch historical data (Yahoo gives up to 60d for 5m/15m)
            # We want as much as possible for a good backtest
            days_to_fetch = '60d' if tf in ['M5', 'M15'] else 'max'
            
            try:
                yf_symbol = connector.symbol_map.get(symbol, symbol)
                if not connector.symbol_map.get(symbol) and len(symbol) == 6 and not symbol.startswith('X'):
                    yf_symbol = f"{symbol}=X"
                
                interval_map = {'M1': '1m', 'M5': '5m', 'M15': '15m', 'H1': '1h', 'D1': '1d'}
                interval = interval_map.get(tf, '5m')
                
                ticker = yf_symbol if not connector.symbol_map.get(symbol) else connector.symbol_map.get(symbol)
                import yfinance as yf
                data = yf.Ticker(ticker).history(period=days_to_fetch, interval=interval)
                
                if data.empty:
                    print(f"Skipping {symbol} @ {tf}: No data found.")
                    continue
                
                # Standardize columns
                data = data.rename(columns={
                    'Open': 'open', 'High': 'high', 'Low': 'low', 
                    'Close': 'close', 'Volume': 'tick_volume'
                })
                
                # 2. Run Backtest
                engine = BacktestEngine("config.yaml")
                engine.symbol = symbol
                engine.timeframe = tf
                
                res = engine.run(data=data, show_progress=False)
                
                if res and res.get('total_trades', 0) > 0:
                    summary = {
                        'Symbol': symbol,
                        'Timeframe': tf,
                        'Win Rate': f"{res['win_rate']:.1f}%",
                        'Total Trades': res['total_trades'],
                        'Total Profit': f"${res['total_profit']:.2f}",
                        'Return %': f"{res['return_percentage']:.2f}%",
                        'Profit Factor': f"{res['profit_factor']:.2f}",
                        'Max Drawdown': f"{res['max_drawdown']:.2f}%"
                    }
                    results_summary.append(summary)
                    print(f"DONE: Win Rate: {summary['Win Rate']}, Profit: {summary['Total Profit']}")
                else:
                    print(f"No trades generated for {symbol} @ {tf}.")
            
            except Exception as e:
                print(f"Error backtesting {symbol} @ {tf}: {e}")
    
    # 3. Save Summary to JSON for later use
    if results_summary:
        df_summary = pd.DataFrame(results_summary)
        print("\n" + "="*50)
        print("BACKTEST SUMMARY RESULTS")
        print("="*50)
        print(df_summary.to_string(index=False))
        
        output_path = Path("data/exports/backtest_summary.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df_summary.to_json(output_path, orient='records', indent=2)
        print(f"\nSummary saved to {output_path}")
    else:
        print("\nNo backtest results were generated.")

if __name__ == "__main__":
    run_comprehensive_backtest()
