import yfinance as yf
import json

def test_extraction(symbol):
    print(f"--- Testing extraction for {symbol} ---")
    ticker = yf.Ticker(symbol)
    news_items = ticker.news
    if not news_items:
        print("No news found.")
        return

    for i, item in enumerate(news_items[:2]):
        print(f"Item {i} keys: {list(item.keys())}")
        content = item.get('content', item) if isinstance(item, dict) else {}
        print(f"Content keys: {list(content.keys()) if isinstance(content, dict) else 'Not a dict'}")
        
        title = content.get('title') or content.get('heading') or item.get('title')
        print(f"Extracted title: {title} (type: {type(title)})")
        
        provider = content.get('provider') or item.get('publisher')
        print(f"Extracted provider: {provider} (type: {type(provider)})")
        
        link = "None"
        if isinstance(content, dict):
            if content.get('canonicalUrl'):
                link = content['canonicalUrl'].get('url')
            elif content.get('clickThroughUrl'):
                link = content['clickThroughUrl'].get('url')
        print(f"Extracted link: {link}")
        print("-" * 20)

test_extraction('GC=F')
test_extraction('SI=F')
test_extraction('EURUSD=X')
