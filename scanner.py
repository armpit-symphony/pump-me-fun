#!/usr/bin/env python3
"""
Pump.fun Token Scanner
Monitors for new tokens with high liquidity before they pump
"""

import os
import json
import time
import requests
from datetime import datetime, timedelta, timezone

# Config
MORALIS_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJub25jZSI6ImE4M2Y3NTg0LWQ0MDItNGQzYi1hMDk5LWExZjYzNDYyMmU1NCIsIm9yZ0lkIjoiNTAyMjAyIiwidXNlcklkIjoiNTE2NzQwIiwidHlwZUlkIjoiMTcyODVmNDktYzA5Ni00ZjJiLTgwNWMtOTAwYjM0OWU1NDA2IiwidHlwZSI6IlBST0pFQ1QiLCJpYXQiOjE3NzE5NzcyNTcsImV4cCI6NDkyNzczNzI1N30._W3ql0zZVWjvZJQTF-fZ2T_2jkhQoY2-T33evMvPb5c"
TELEGRAM_BOT_TOKEN = "8675469476:AAF3A42e3eo5CD9IEMqtP46CJUV3T9HL3ko"
TELEGRAM_CHAT_ID = "8585118112"

# Filters
MIN_LIQUIDITY = 200_000  # $200k
MAX_AGE_HOURS = 48
POLL_INTERVAL = 300  # 5 minutes

SEEN_TOKENS_FILE = "/home/sparky/.openclaw/workspace/pump-scanner/seen_tokens.json"

def load_seen_tokens():
    try:
        with open(SEEN_TOKENS_FILE, "r") as f:
            return set(json.load(f))
    except:
        return set()

def save_seen_tokens(tokens):
    os.makedirs(os.path.dirname(SEEN_TOKENS_FILE), exist_ok=True)
    with open(SEEN_TOKENS_FILE, "w") as f:
        json.dump(list(tokens), f)

def fetch_new_tokens(limit=100):
    url = f"https://solana-gateway.moralis.io/token/mainnet/exchange/pumpfun/new?limit={limit}"
    headers = {
        "accept": "application/json",
        "X-API-Key": MORALIS_API_KEY
    }
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json().get("result", [])

def filter_gems(tokens, seen):
    gems = []
    now = datetime.now(timezone.utc)
    
    for token in tokens:
        # Skip if already seen
        if token.get("tokenAddress") in seen:
            continue
        
        # Check age - we want tokens OLDER than MAX_AGE_HOURS (had time to build liq but haven't pumped)
        created = token.get("createdAt")
        if not created:
            continue
        try:
            created_dt = datetime.fromisoformat(created.replace("Z", "+00:00")).replace(tzinfo=timezone.utc)
            age_hours = (now - created_dt).total_seconds() / 3600
            if age_hours < 1 or age_hours > MAX_AGE_HOURS:
                continue  # Skip too new OR too old
        except:
            pass
        
        # Check liquidity
        liquidity = token.get("liquidity")
        if liquidity is None:
            continue
        try:
            liq = float(liquidity)
            if liq >= MIN_LIQUIDITY:
                gems.append(token)
        except:
            pass
    
    return gems

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    resp = requests.post(url, data=data, timeout=10)
    return resp.ok

def format_alert(token):
    name = token.get("name", "Unknown")
    symbol = token.get("symbol", "???")
    addr = token.get("tokenAddress", "")
    short_addr = addr[:20] + "..." if len(addr) > 20 else addr
    liquidity = float(token.get("liquidity", 0))
    created = token.get("createdAt", "")
    
    # Calculate age
    try:
        created_dt = datetime.fromisoformat(created.replace("Z", "+00:00")).replace(tzinfo=timezone.utc)
        age_hours = (datetime.now(timezone.utc) - created_dt).total_seconds() / 3600
        age_str = f"{age_hours:.1f}h old"
    except:
        age_str = "unknown age"
    
    return f"""💎 *PUMP.FUN GEM FOUND*

*{name}* ({symbol})
`{short_addr}`

💧 Liquidity: ${liquidity:,.0f}
⏰ {age_str}

🔗 https://pump.fun/{addr}"""

def main():
    print("🚀 Pump.fun Scanner Starting...")
    print(f"   Min Liquidity: ${MIN_LIQUIDITY:,}")
    print(f"   Max Age: {MAX_AGE_HOURS}h")
    print(f"   Poll Interval: {POLL_INTERVAL}s")
    print()
    
    seen = load_seen_tokens()
    print(f"   Seen tokens: {len(seen)}")
    
    while True:
        try:
            tokens = fetch_new_tokens()
            gems = filter_gems(tokens, seen)
            
            now = datetime.now(timezone.utc).strftime("%H:%M:%S")
            print(f"[{now}] Checked {len(tokens)} tokens, found {len(gems)} gems")
            
            for gem in gems:
                msg = format_alert(gem)
                print(f"   🚨 ALERT: {gem.get('name')} - ${float(gem.get('liquidity', 0)):,.0f}")
                send_telegram(msg)
                seen.add(gem.get("tokenAddress"))
            
            # Save seen
            save_seen_tokens(seen)
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
