import MetaTrader5 as mt5
import os
from dotenv import load_dotenv

def test_connection():
    load_dotenv()
    
    login = int(os.getenv("MT5_LOGIN", 0))
    password = os.getenv("MT5_PASSWORD", "")
    server = os.getenv("MT5_SERVER", "")
    path = "C:/Program Files/Pepperstone MetaTrader 5/terminal64.exe"
    
    print(f"Testing with: Login={login}, Server={server}, Path={path}")
    print(f"MT5 Package Version: {mt5.__version__}")
    
    # Check if terminal64.exe is running
    import subprocess
    tasks = subprocess.check_output(['tasklist'], shell=True).decode('utf-8')
    if "terminal64.exe" in tasks.lower():
        print("INFO: terminal64.exe is already running in background.")
    else:
        print("INFO: No terminal64.exe found running.")

    # Try initialize without path first (connect to already open terminal)
    print("Step 1: Trying to connect to the ALREADY OPEN terminal...")
    init_success = mt5.initialize()
    if not init_success:
        print(f"FAILED: mt5.initialize() failed. Error: {mt5.last_error()}")
        
        print(f"\nStep 2: Trying to launch terminal from path: {path}")
        init_success = mt5.initialize(path=path)
        if not init_success:
            err = mt5.last_error()
            print(f"FAILED: mt5.initialize(path=...) failed. Error: {err}")
            return
            
    print("SUCCESS: MT5 initialized.")
    
    # Check if terminal is actually connected to a server
    terminal_info = mt5.terminal_info()
    if terminal_info:
        print(f"Terminal Connected to Network: {terminal_info.connected}")
        if not terminal_info.connected:
            print("!!! WARNING: Your MT5 terminal is NOT connected to any server (0/0 Kb). !!!")
            print("Please login manually in the MT5 app first.")
    
    # Try login
    # We will try the server name from your screenshot: "Pepperstone-Demo"
    servers_to_try = ["Pepperstone-Demo", server]
    
    for srv in servers_to_try:
        if not srv: continue
        print(f"\nAttempting mt5.login({login}, ..., {srv})...")
        login_success = mt5.login(login, password=password, server=srv)
        if login_success:
            print(f"SUCCESS: MT5 logged in using server: {srv}")
            account_info = mt5.account_info()
            if account_info:
                print(f"Account Balance: {account_info.balance} {account_info.currency}")
                print(f"Expert Trading Allowed: {account_info.trade_expert}")
            break
        else:
            print(f"FAILED for server {srv}. Error: {mt5.last_error()}")
            
    mt5.shutdown()
            
    mt5.shutdown()

if __name__ == "__main__":
    test_connection()
