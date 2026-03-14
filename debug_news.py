import yfinance as yf
import json

symbols = ['GC=F', 'SI=F', 'EURUSD=X', 'BTC-USD']

for s in symbols:
    print(f"--- News for {s} ---")
    ticker = yf.Ticker(s)
    news = ticker.news
    if news:
        # Print the first news item completely to see keys
        print(json.dumps(news[0], indent=2))
    else:
        print("No news found.")
    print("\n")
