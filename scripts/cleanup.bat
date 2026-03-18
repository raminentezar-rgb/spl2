@echo off
echo Stopping all Python and MetaTrader 5 processes...
taskkill /F /IM terminal64.exe /T 2>nul
taskkill /F /IM python.exe /T 2>nul
echo.
echo ==========================================
echo Cleanup Complete.
echo Next Steps:
echo 1. Open your Pepperstone MT5 terminal MANUALLY.
echo 2. Ensure "Algo Trading" button is GREEN.
echo 3. Run the check_mt5.py script again.
echo ==========================================
pause
