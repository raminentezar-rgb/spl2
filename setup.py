# setup.py
from setuptools import setup, find_packages

setup(
    name="sp2l_trading_bot",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        'MetaTrader5',
        'pandas',
        'numpy',
        'TA-Lib',
        'pyyaml',
        'python-dotenv',
        'schedule',
    ],
)