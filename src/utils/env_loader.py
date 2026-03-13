# src/utils/env_loader.py
import os
from pathlib import Path
from dotenv import load_dotenv

def load_environment():
    """
    بارگذاری متغیرهای محیطی از فایل .env
    """
    env_file = Path(__file__).parent.parent.parent / '.env'
    if env_file.exists():
        load_dotenv(env_file)
        print(f"✅ Environment loaded from {env_file}")
    else:
        print("⚠️  No .env file found, using default values")
    
    return {
        'login': os.getenv('MT5_LOGIN', '12345678'),
        'password': os.getenv('MT5_PASSWORD', ''),
        'server': os.getenv('MT5_SERVER', 'BrokerServer')
    }