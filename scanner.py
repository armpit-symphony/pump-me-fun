#!/usr/bin/env python3
"""
Pump.fun Token Scanner
Monitors pump.fun for gems with advanced indicators.

Features:
- Liquidity & age filters
- Price momentum detection
- Liquidity growth tracking
- Week-old token alerts
- Telegram notifications

Usage:
    export MORALIS_API_KEY="your_key"
    export TELEGRAM_BOT_TOKEN="your_bot_token"
    export TELEGRAM_CHAT_ID="your_chat_id"
    python scanner.py
"""

import os
import sys
import json
import time
import requests
import logging
from datetime import datetime, timezone
from pathlib import Path

# Setup logging
LOG_FILE = "scanner.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ============================================================
# CONFIGURATION - Set via environment variables
# ============================================================

# Required: Get free API key at https://moralis.io
MORALIS_API_KEY = os.environ.get("MORALIS_API_KEY", "")

# Required: Telegram bot token from @BotFather
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

# Required: Your Telegram chat ID (use @userinfobot to find)
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# ============================================================
# FILTERS - Customize these
# ============================================================

MIN_LIQUIDITY = 20_000   # Minimum liquidity in USD
MAX_AGE_HOURS = 168      # Max age (1 week)
MIN_AGE_HOURS = 4        # Min age to avoid brand new tokens
POLL_INTERVAL = 300      # Seconds between checks (5 min)

# Alert thresholds
MIN_PRICE_MOMENTUM = 0.20        # Alert on 20%+ price rise
MIN_LIQUIDITY_GROWTH = 1.5       # Alert on 50%+ liquidity increase
WEEKOLD_LIQUIDITY_MULTIPLIER = 2.0  # Alert on 2x liquidity for older tokens
MIN_VOLUME_SPIKE = 5.0           # Alert on 5x+ transaction count increase

# Storage
BASE_DIR = Path(__file__).parent
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
    """Fetch new tokens from Moralis API"""
    if not MORALIS_API_KEY:
        logger.error("MORALIS_API_KEY not set!")
        return []
    
    url = f"https://solana-gateway.moralis.io/token/mainnet/exchange/pumpfun/new?limit={limit}"
    headers = {
        "accept": "application/json",
        "X-API-Key": MORALIS_API_KEY
    }
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json().get("result", [])

def fetch_dexscreener_data(token_address):
    """Fetch volume/txn data from DexScreener (free, no key needed)"""
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
        resp = requests.get(url, timeout=10)
        if resp.ok:
            data = resp.json()
            if data.get("pairs") and len(data["pairs"]) > 0:
                pair = data["pairs"][0]
                txns = pair.get("txns", {})
                volume = pair.get("volume", {})
                return {
                    "txns_h1": (txns.get("h1", {}).get("buys", 0) + txns.get("h1", {}).get("sells", 0)),
                    "txns_h24": (txns.get("h24", {}).get("buys", 0) + txns.get("h24", {}).get("sells", 0)),
                    "volume_h1": volume.get("h1", 0),
                    "volume_h24": volume.get("h24", 0)
                }
    except Exception as e:
        logger.debug(f"DexScreener fetch failed for {token_address}: {e}")
    return None

def analyze_token(token, history, seen):
    """Analyze a single token for indicators"""
    addr = token.get("tokenAddress")
    
    if addr in seen:
        return None
    
    created = token.get("createdAt")
    if not created:
        return None
    
    try:
        created_dt = datetime.fromisoformat(created.replace("Z", "+00:00")).replace(tzinfo=timezone.utc)
        age_hours = (datetime.now(timezone.utc) - created_dt).total_seconds() / 3600
        
        if age_hours < MIN_AGE_HOURS or age_hours > MAX_AGE_HOURS:
            return None
    except:
        return None
    
    liquidity = token.get("liquidity")
    if liquidity is None:
        return None
    try:
        liq = float(liquidity)
        if liq < MIN_LIQUIDITY:
            return None
    except:
        return None
    
    price_usd = token.get("priceUsd")
    current_price = float(price_usd) if price_usd else None
    
    # Fetch DexScreener data for volume/txn detection
    dex_data = fetch_dexscreener_data(addr)
    
    indicators = []
    
    # Check price history for momentum
    if addr in history and current_price:
        prev_data = history[addr]
        prev_price = prev_data.get("priceUsd")
        prev_liquidity = prev_data.get("liquidity")
        
        if prev_price and prev_liquidity:
            try:
                price_change = (current_price - float(prev_price)) / float(prev_price)
                liquidity_change = float(liquidity) / float(prev_liquidity)
                
                if price_change >= MIN_PRICE_MOMENTUM:
                    indicators.append(f"📈 Price +{price_change*100:.0f}%")
                
                if liquidity_change >= MIN_LIQUIDITY_GROWTH:
                    indicators.append(f"💧 Liquidity +{(liquidity_change-1)*100:.0f}%")
                
                if age_hours >= 24 and liquidity_change >= WEEKOLD_LIQUIDITY_MULTIPLIER:
                    indicators.append(f"🗓️ Week-old 2x Liquidity")
            except:
                pass
    
    # Volume spike detection
    if dex_data and addr in history:
        prev_data = history.get(addr, {})
        prev_txns = prev_data.get("txns_h1", 0)
        current_txns = dex_data.get("txns_h1", 0)
        
        if prev_txns > 0 and current_txns > 0:
            try:
                txn_spike = current_txns / prev_txns
                if txn_spike >= MIN_VOLUME_SPIKE:
                    indicators.append(f"📊 Volume {txn_spike:.0f}x ({current_txns} txns/h)")
            except:
                pass
    
    # Build history record
    history[addr] = {
        "priceUsd": price_usd,
        "liquidity": liquidity,
        "name": token.get("name"),
        "txns_h1": dex_data.get("txns_h1", 0) if dex_data else 0,
        "txns_h24": dex_data.get("txns_h24", 0) if dex_data else 0,
        "volume_h1": dex_data.get("volume_h1", 0) if dex_data else 0,
        "updated": datetime.now(timezone.utc).isoformat()
    }
    
    if indicators:
        return {
            "token": token,
            "indicators": indicators,
            "age_hours": age_hours,
            "liquidity": liq,
            "dex_data": dex_data
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
    
    save_price_history(history)
    return gems

def send_telegram(message):
    """Send alert to Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram not configured - skipping alert")
        return False
    
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
    """Format Telegram alert message"""
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
    # Validate config
    if not MORALIS_API_KEY:
        logger.error("Please set MORALIS_API_KEY environment variable")
        logger.info("Get free key at: https://moralis.io")
        sys.exit(1)
    
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram not configured - alerts disabled")
    
    logger.info("🚀 Pump.fun Scanner Starting...")
    logger.info(f"   Min Liquidity: ${MIN_LIQUIDITY:,}")
    logger.info(f"   Age Range: {MIN_AGE_HOURS}-{MAX_AGE_HOURS}h")
    logger.info(f"   Price Momentum: >{MIN_PRICE_MOMENTUM*100:.0f}%")
    logger.info(f"   Liquidity Growth: >{(MIN_LIQUIDITY_GROWTH-1)*100:.0f}%")
    logger.info(f"   Volume Spike: >{MIN_VOLUME_SPIKE}x txns")
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
