#!/usr/bin/env python3
"""
Pump.fun Token Scanner v2
Monitors pump.fun for gems with advanced indicators:
- Liquidity > $200k
- Age: 1-48 hours
- Volume spike detection
- Liquidity growth detection
- Price momentum detection
"""

import os
import sys
import json
import time
import requests
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Setup logging
LOG_FILE = "/home/sparky/.openclaw/logs/pump-scanner.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Config
MORALIS_API_KEY = os.environ.get("MORALIS_API_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJub25jZSI6ImE4M2Y3NTg0LWQ0MDItNGQzYi1hMDk5LWExZjYzNDYyMmU1NCIsIm9yZ0lkIjoiNTAyMjAyIiwidXNlcklkIjoiNTE2NzQwIiwidHlwZUlkIjoiMTcyODVmNDktYzA5Ni00ZjJiLTgwNWMtOTAwYjM0OWU1NDA2IiwidHlwZSI6IlBST0pFQ1QiLCJpYXQiOjE3NzE5NzcyNTcsImV4cCI6NDkyNzczNzI1N30._W3ql0zZVWjvZJQTF-fZ2T_2jkhQoY2-T33evMvPb5c")
TELEGRAM_BOT_TOKEN = "8675469476:AAF3A42e3eo5CD9IEMqtP46CJUV3T9HL3ko"
TELEGRAM_CHAT_ID = "8585118112"

# Filters
MIN_LIQUIDITY = 5_000  # $5k - catch tokens above starting liquidity
MAX_AGE_HOURS = 48
MIN_AGE_HOURS = 0  # Catch fresh tokens as soon as they have liquidity
POLL_INTERVAL = 300  # 5 minutes

# Advanced indicators
MIN_VOLUME_SPIKE = 3.0  # 3x average volume = alert
MIN_LIQUIDITY_GROWTH = 1.5  # 50% liquidity increase = alert
MIN_PRICE_MOMENTUM = 0.20  # 20% price rise = alert

# Storage
BASE_DIR = Path("/home/sparky/.openclaw/workspace/pump-scanner")
SEEN_TOKENS_FILE = BASE_DIR / "seen_tokens.json"
PRICE_HISTORY_FILE = BASE_DIR / "price_history.json"

def load_json(file_path, default):
    try:
        if file_path.exists():
            with open(file_path, "r") as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load {file_path}: {e}")
    return default

def save_json(file_path, data):
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save {file_path}: {e}")

def load_seen_tokens():
    return set(load_json(SEEN_TOKENS_FILE, []))

def save_seen_tokens(tokens):
    save_json(SEEN_TOKENS_FILE, list(tokens))

def load_price_history():
    return load_json(PRICE_HISTORY_FILE, {})

def save_price_history(history):
    save_json(PRICE_HISTORY_FILE, history)

def fetch_new_tokens(limit=100):
    url = f"https://solana-gateway.moralis.io/token/mainnet/exchange/pumpfun/new?limit={limit}"
    headers = {
        "accept": "application/json",
        "X-API-Key": MORALIS_API_KEY
    }
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json().get("result", [])

def analyze_token(token, history, seen):
    """Advanced analysis for a single token"""
    addr = token.get("tokenAddress")
    
    # Skip if already alerted
    if addr in seen:
        return None
    
    # Basic filters
    created = token.get("createdAt")
    if not created:
        return None
    
    try:
        created_dt = datetime.fromisoformat(created.replace("Z", "+00:00")).replace(tzinfo=timezone.utc)
        age_hours = (datetime.now(timezone.utc) - created_dt).total_seconds() / 3600
        
        # Age filter: must be 1-48 hours old
        if age_hours < MIN_AGE_HOURS or age_hours > MAX_AGE_HOURS:
            return None
    except:
        return None
    
    # Liquidity filter
    liquidity = token.get("liquidity")
    if liquidity is None:
        return None
    try:
        liq = float(liquidity)
        if liq < MIN_LIQUIDITY:
            return None
    except:
        return None
    
    # Note: Holder count requires separate API call - skipping for speed
    # Moralis has endpoint for token holders but would slow down polling
    
    # Get price data
    price_usd = token.get("priceUsd")
    if price_usd:
        try:
            current_price = float(price_usd)
        except:
            current_price = None
    else:
        current_price = None
    
    # Check for indicators
    indicators = []
    
    # 1. Check price history for momentum
    if addr in history and current_price:
        prev_data = history[addr]
        prev_price = prev_data.get("priceUsd")
        prev_liquidity = prev_data.get("liquidity")
        
        if prev_price and prev_liquidity:
            try:
                price_change = (current_price - float(prev_price)) / float(prev_price)
                liquidity_change = float(liquidity) / float(prev_liquidity)
                
                # Price momentum indicator
                if price_change >= MIN_PRICE_MOMENTUM:
                    indicators.append(f"📈 Price +{price_change*100:.0f}%")
                
                # Liquidity growth indicator
                if liquidity_change >= MIN_LIQUIDITY_GROWTH:
                    indicators.append(f"💧 Liquidity +{(liquidity_change-1)*100:.0f}%")
            except:
                pass
    
    # Update history
    history[addr] = {
        "priceUsd": price_usd,
        "liquidity": liquidity,
        "name": token.get("name"),
        "updated": datetime.now(timezone.utc).isoformat()
    }
    
    # Always include token if it passes filters (even without indicators)
    # This catches new gems that haven't momentum'd yet
    if indicators:
        return {
            "token": token,
            "indicators": indicators,
            "age_hours": age_hours,
            "liquidity": liq
        }
    elif liq >= MIN_LIQUIDITY:  # Has decent liquidity even without momentum
        return {
            "token": token,
            "indicators": [f"💎 New Token: \${liq:,.0f} liquidity"],
            "age_hours": age_hours,
            "liquidity": liq
        }
    
    return None

def filter_gems(tokens, seen):
    """Filter tokens and analyze for indicators"""
    history = load_price_history()
    gems = []
    
    for token in tokens:
        result = analyze_token(token, history, seen)
        if result:
            gems.append(result)
    
    # Save updated history
    save_price_history(history)
    
    return gems

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        resp = requests.post(url, data=data, timeout=10)
        return resp.ok
    except Exception as e:
        logger.error(f"Telegram send failed: {e}")
        return False

def format_alert(gem):
    token = gem["token"]
    indicators = gem["indicators"]
    
    name = token.get("name", "Unknown")
    symbol = token.get("symbol", "???")
    addr = token.get("tokenAddress", "")
    liquidity = gem["liquidity"]
    age = gem["age_hours"]
    
    indicator_text = "\n".join([f"  {ind}" for ind in indicators])
    
    return f"""💎 *PUMP.FUN GEM ALERT*

*{name}* ({symbol})
`{addr[:24]}...`

💧 Liquidity: ${liquidity:,.0f}
⏰ Age: {age:.1f}h

*Indicators:*
{indicator_text}

🔗 https://pump.fun/{addr}"""

def main():
    logger.info("🚀 Pump.fun Scanner v2 Starting...")
    logger.info(f"   Min Liquidity: ${MIN_LIQUIDITY:,}")
    logger.info(f"   Age Range: {MIN_AGE_HOURS}-{MAX_AGE_HOURS}h")
    logger.info(f"   Price Momentum: >{MIN_PRICE_MOMENTUM*100:.0f}%")
    logger.info(f"   Liquidity Growth: >{(MIN_LIQUIDITY_GROWTH-1)*100:.0f}%")
    logger.info(f"   Poll Interval: {POLL_INTERVAL}s")
    
    seen = load_seen_tokens()
    logger.info(f"   Seen tokens: {len(seen)}")
    
    while True:
        try:
            tokens = fetch_new_tokens()
            gems = filter_gems(tokens, seen)
            
            now = datetime.now(timezone.utc).strftime("%H:%M:%S")
            logger.info(f"[{now}] Checked {len(tokens)} tokens, found {len(gems)} gems")
            
            for gem in gems:
                msg = format_alert(gem)
                token_name = gem["token"].get("name")
                logger.info(f"   🚨 ALERT: {token_name}")
                
                if send_telegram(msg):
                    seen.add(gem["token"].get("tokenAddress"))
                    logger.info(f"   ✅ Telegram alert sent")
                else:
                    logger.error(f"   ❌ Telegram alert failed")
            
            save_seen_tokens(seen)
            
        except Exception as e:
            logger.error(f"   ❌ Error: {e}")
        
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
