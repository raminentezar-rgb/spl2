# scripts/optimize_params.py
import itertools
import json
from pathlib import Path
from src.backtesting.backtest_engine import BacktestEngine
from src.utils.helpers import load_config, save_config

def optimize():
    """بهینه‌سازی پارامترها"""
    
    # محدوده پارامترها برای تست
    params_to_test = {
        'min_higher_lows': [2, 3, 4],
        'ma_period': [40, 50, 60],
        'risk_reward_ratio': [1.8, 2.0, 2.2, 2.5],
        'pullback_threshold': [0.0005, 0.0008, 0.001]
    }
    
    best_result = None
    best_params = None
    best_profit = -float('inf')
    
    all_results = []
    
    # تولید همه ترکیبات
    keys = params_to_test.keys()
    for values in itertools.product(*params_to_test.values()):
        params = dict(zip(keys, values))
        
        print(f"\nTesting: {params}")
        
        # آپدیت config
        config = load_config()
        config['strategy'].update(params)
        save_config(config, 'config_optimize.yaml')
        
        # اجرای بک‌تست
        engine = BacktestEngine('config_optimize.yaml')
        results = engine.run(show_progress=False)
        
        profit = results.get('total_profit', 0)
        win_rate = results.get('win_rate', 0)
        total_trades = results.get('total_trades', 0)
        
        print(f"Profit: ${profit:.2f}")
        
        # DEBUG FIRST 5 TRADES:
        trades_list = results.get('trades', [])
        if isinstance(trades_list, list) and len(trades_list) > 0:
            print(f"first 5 trades of {total_trades}:")
            for t in trades_list[:5]:
                print(f"  {t['time']} - {t['type']} @ {t['entry']:.5f} (SL: {t['sl']:.5f}, TP: {t['tp']:.5f}, Profit: {t['profit']})")
                
        # Add to all results
        res_entry = params.copy()
        res_entry['Profit'] = profit
        res_entry['WinRate'] = win_rate
        res_entry['TotalTrades'] = total_trades
        res_entry['MaxDrawdown'] = results.get('max_drawdown', 0)
        all_results.append(res_entry)
        
        if profit > best_profit:
            best_profit = profit
            best_params = params
            best_result = results
            
    # Save all results to CSV
    import pandas as pd
    from datetime import datetime
    
    if not all_results:
        print("\nNo results to save.")
        return

    df_results = pd.DataFrame(all_results)
    if 'Profit' in df_results.columns:
        df_results = df_results.sort_values(by='Profit', ascending=False)
    
    out_dir = Path("data/exports/optimization")
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = out_dir / f"opt_results_{timestamp}.csv"
    df_results.to_csv(out_file, index=False)
    print(f"\nAll results saved to {out_file}")
    
    print("\n" + "="*50)
    print("BEST PARAMETERS:")
    if best_params:
        print(json.dumps(best_params, indent=2))
        print(f"Profit: ${best_profit:.2f}")
        print(f"Win Rate: {best_result.get('win_rate', 0):.2f}%")
    else:
        print("No best parameters found.")
    print("="*50)

if __name__ == "__main__":
    optimize()