import requests
import yaml

def test_telegram():
    with open("config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    token = config.get('telegram', {}).get('token')
    chat_ids = config.get('telegram', {}).get('chat_ids', [])
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    for chat_id in chat_ids:
        payload = {
            "chat_id": chat_id,
            "text": f"🤖 **تست نهایی اتصال ربات به {chat_id}**\nاتصال با موفقیت برقرار شد! ✅",
            "parse_mode": "Markdown"
        }
        
        print(f"Sending test to {chat_id}...")
        response = requests.post(url, json=payload)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")

if __name__ == "__main__":
    test_telegram()
