#!/usr/bin/env python
"""
اسکریپت اجرای اصلی - در ریشه پروژه
"""
import sys
import os
from pathlib import Path

# اضافه کردن مسیر پروژه به PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

if __name__ == "__main__":
    # اجرای main.py با آرگومان‌های خط فرمان
    from src.main import main
    main()