import json
with open(r'data\exports\backtest_results\backtest_XAUUSD_M5_20260305_154209.json') as f:
    d = json.load(f)
    print("Summary:")
    print("Total Trades:", d['total_trades'])
    print("Win Rate:", d['win_rate'])
    print("\nFirst 5 Trades:")
    for t in d['trades'][:5]:
        print(json.dumps(t, indent=2))
