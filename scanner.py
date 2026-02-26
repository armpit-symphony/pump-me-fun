#!/usr/bin/env python3
"""
Pump.fun Token Scanner - Improved
Monitors pump.fun for gems with advanced indicators.

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
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ============================================================
# LOGGING
# ============================================================

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
# CONFIG - Set via environment variables
# ============================================================

MORALIS_API_KEY    = os.environ.get("MORALIS_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "")

# ============================================================
# FILTERS - Tweak these to your taste
# ============================================================

MIN_LIQUIDITY    = 20_000   # Minimum liquidity in USD
MAX_AGE_HOURS    = 168      # Max token age (1 week)
MIN_AGE_HOURS    = 4        # Ignore brand-new tokens
POLL_INTERVAL    = 300      # Seconds between scans (5 min)
FETCH_LIMIT      = 100      # How many tokens to pull per scan (Moralis max is 100)

# Alert thresholds
MIN_PRICE_MOMENTUM        = 0.20   # Alert on 20%+ price rise
MIN_LIQUIDITY_GROWTH      = 1.5    # Alert on 50%+ liquidity increase
WEEKOLD_LIQ_MULTIPLIER    = 2.0    # Alert on 2x liquidity for tokens 7d+
MIN_VOLUME_SPIKE          = 5.0    # Alert on 5x transaction count spike
MIN_TXNS_FOR_SPIKE        = 10     # Ignore spikes if previous txn count was tiny (noise filter)

# Re-alert same token after this many hours (0 = never re-alert)
REALERT_HOURS = 6

# Clean up price history records older than this
HISTORY_MAX_AGE_HOURS = 200

# ============================================================
# STORAGE
# ============================================================

BASE_DIR           = Path(__file__).parent
SEEN_TOKENS_FILE   = BASE_DIR / "seen_tokens.json"
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
    """Returns dict: {address: iso_timestamp_of_last_alert}"""
    raw = load_json(SEEN_TOKENS_FILE, {})
    # Backwards-compat: old format was a list
    if isinstance(raw, list):
        return {addr: "2000-01-01T00:00:00+00:00" for addr in raw}
    return raw


def save_seen_tokens(tokens: dict):
    save_json(SEEN_TOKENS_FILE, tokens)


def load_price_history():
    return load_json(PRICE_HISTORY_FILE, {})


def save_price_history(history: dict):
    save_json(PRICE_HISTORY_FILE, history)


def prune_price_history(history: dict) -> dict:
    """Remove stale entries to keep the file from growing forever."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=HISTORY_MAX_AGE_HOURS)
    pruned = {}
    for addr, data in history.items():
        updated_str = data.get("updated")
        if updated_str:
            try:
                updated_dt = datetime.fromisoformat(updated_str)
                if updated_dt > cutoff:
                    pruned[addr] = data
                    continue
            except Exception:
                pass
        # Keep if we can't parse the date (safety)
        pruned[addr] = data
    removed = len(history) - len(pruned)
    if removed:
        logger.info(f"   🧹 Pruned {removed} stale history entries")
    return pruned


def should_alert(seen: dict, addr: str) -> bool:
    """Allow re-alerting the same token after REALERT_HOURS."""
    if REALERT_HOURS == 0:
        return addr not in seen
    last_str = seen.get(addr)
    if not last_str:
        return True
    try:
        last_dt = datetime.fromisoformat(last_str)
        return (datetime.now(timezone.utc) - last_dt).total_seconds() / 3600 >= REALERT_HOURS
    except Exception:
        return True


# ============================================================
# API CALLS
# ============================================================

def fetch_new_tokens(limit=FETCH_LIMIT):
    """Fetch tokens from Moralis pump.fun endpoint."""
    if not MORALIS_API_KEY:
        logger.error("MORALIS_API_KEY not set!")
        return []

    url = f"https://solana-gateway.moralis.io/token/mainnet/exchange/pumpfun/new?limit={limit}"
    headers = {
        "accept": "application/json",
        "X-API-Key": MORALIS_API_KEY
    }
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.json().get("result", [])
    except Exception as e:
        logger.error(f"Moralis fetch failed: {e}")
        return []


# Simple in-memory rate limiter for DexScreener calls
_dex_cache: dict = {}
_DEX_CACHE_TTL = 60  # seconds

def fetch_dexscreener_data(token_address: str):
    """Fetch volume/txn data from DexScreener (free, no key needed).
    Results are cached for 60s to avoid rate limits."""
    now = time.time()
    cached = _dex_cache.get(token_address)
    if cached and (now - cached["ts"]) < _DEX_CACHE_TTL:
        return cached["data"]

    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
        resp = requests.get(url, timeout=10)
        if resp.ok:
            data = resp.json()
            if data.get("pairs"):
                pair = data["pairs"][0]
                txns  = pair.get("txns", {})
                volume = pair.get("volume", {})
                result = {
                    "txns_h1":   txns.get("h1", {}).get("buys", 0)  + txns.get("h1", {}).get("sells", 0),
                    "txns_h24":  txns.get("h24", {}).get("buys", 0) + txns.get("h24", {}).get("sells", 0),
                    "volume_h1": volume.get("h1", 0),
                    "volume_h24": volume.get("h24", 0),
                }
                _dex_cache[token_address] = {"ts": now, "data": result}
                return result
    except Exception as e:
        logger.debug(f"DexScreener failed for {token_address}: {e}")

    _dex_cache[token_address] = {"ts": now, "data": None}
    return None


def send_telegram(message: str, retries: int = 3) -> bool:
    """Send alert to Telegram with retry logic."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram not configured - skipping alert")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }

    for attempt in range(1, retries + 1):
        try:
            resp = requests.post(url, data=payload, timeout=10)
            if resp.ok:
                return True
            logger.warning(f"Telegram attempt {attempt} failed: {resp.status_code} {resp.text[:100]}")
        except Exception as e:
            logger.warning(f"Telegram attempt {attempt} error: {e}")
        if attempt < retries:
            time.sleep(2 ** attempt)  # exponential back-off

    logger.error("Telegram: all retries exhausted")
    return False


def test_telegram():
    """Send a startup ping to confirm Telegram is working."""
    ok = send_telegram("🟢 *Pump.fun Scanner started* — Telegram connection OK!")
    if ok:
        logger.info("   ✅ Telegram test message sent")
    else:
        logger.warning("   ⚠️  Telegram test message FAILED — check your token/chat ID")


# ============================================================
# ANALYSIS
# ============================================================

def analyze_token(token: dict, history: dict, seen: dict):
    """Analyze a single token. Returns gem dict or None."""
    addr = token.get("tokenAddress")
    if not addr:
        return None

    # Re-alert check (replaces simple "seen" exclusion)
    if not should_alert(seen, addr):
        return None

    # Age filter
    created = token.get("createdAt")
    if not created:
        return None
    try:
        created_dt = datetime.fromisoformat(created.replace("Z", "+00:00")).replace(tzinfo=timezone.utc)
        age_hours = (datetime.now(timezone.utc) - created_dt).total_seconds() / 3600
        if age_hours < MIN_AGE_HOURS or age_hours > MAX_AGE_HOURS:
            return None
    except Exception:
        return None

    # Liquidity filter
    try:
        liq = float(token.get("liquidity") or 0)
        if liq < MIN_LIQUIDITY:
            return None
    except Exception:
        return None

    price_usd = token.get("priceUsd")
    current_price = float(price_usd) if price_usd else None

    indicators = []

    # --- Price + liquidity momentum (requires history) ---
    if addr in history and current_price:
        prev = history[addr]
        prev_price = prev.get("priceUsd")
        prev_liq   = prev.get("liquidity")

        if prev_price and prev_liq:
            try:
                price_change = (current_price - float(prev_price)) / float(prev_price)
                liq_ratio    = liq / float(prev_liq)

                if price_change >= MIN_PRICE_MOMENTUM:
                    indicators.append(f"📈 Price +{price_change*100:.0f}%")

                if liq_ratio >= MIN_LIQUIDITY_GROWTH:
                    indicators.append(f"💧 Liquidity +{(liq_ratio-1)*100:.0f}%")

                # Fixed: true "week-old" check is 7 days = 168h
                if age_hours >= 168 and liq_ratio >= WEEKOLD_LIQ_MULTIPLIER:
                    indicators.append(f"🗓️ Week-old 2x Liquidity")

            except Exception:
                pass

    # --- Volume / txn spike (only fetch DexScreener when we have history) ---
    dex_data = None
    if addr in history:
        dex_data = fetch_dexscreener_data(addr)
        if dex_data:
            prev_txns    = history[addr].get("txns_h1", 0)
            current_txns = dex_data.get("txns_h1", 0)

            if prev_txns >= MIN_TXNS_FOR_SPIKE and current_txns > 0:
                try:
                    spike = current_txns / prev_txns
                    if spike >= MIN_VOLUME_SPIKE:
                        indicators.append(f"📊 Volume spike {spike:.0f}x ({current_txns} txns/h)")
                except Exception:
                    pass

    # Update history record
    history[addr] = {
        "priceUsd":   price_usd,
        "liquidity":  str(liq),
        "name":       token.get("name"),
        "txns_h1":    dex_data.get("txns_h1", 0) if dex_data else history.get(addr, {}).get("txns_h1", 0),
        "txns_h24":   dex_data.get("txns_h24", 0) if dex_data else 0,
        "volume_h1":  dex_data.get("volume_h1", 0) if dex_data else 0,
        "updated":    datetime.now(timezone.utc).isoformat(),
    }

    if indicators:
        return {
            "token":      token,
            "indicators": indicators,
            "age_hours":  age_hours,
            "liquidity":  liq,
            "dex_data":   dex_data,
        }

    return None


def filter_gems(tokens: list, seen: dict):
    history = load_price_history()
    history = prune_price_history(history)
    gems = []

    for token in tokens:
        result = analyze_token(token, history, seen)
        if result:
            gems.append(result)

    save_price_history(history)
    return gems


# ============================================================
# FORMATTING
# ============================================================

def format_alert(gem: dict) -> str:
    token      = gem["token"]
    indicators = gem["indicators"]
    dex        = gem.get("dex_data") or {}

    name    = token.get("name", "Unknown")
    symbol  = token.get("symbol", "???")
    addr    = token.get("tokenAddress", "")
    liq     = gem["liquidity"]
    age     = gem["age_hours"]
    vol_h1  = dex.get("volume_h1", 0)
    txns_h1 = dex.get("txns_h1", 0)

    indicator_text = "\n".join(f"  {ind}" for ind in indicators)

    vol_line = f"📊 Vol 1h: ${vol_h1:,.0f}  |  Txns: {txns_h1}" if vol_h1 else ""

    return f"""💎 *PUMP.FUN GEM ALERT*

*{name}* ({symbol})
`{addr[:24]}...`

💧 Liquidity: ${liq:,.0f}
⏰ Age: {age:.1f}h
{vol_line}

*Indicators:*
{indicator_text}

🔗 https://pump.fun/{addr}
📈 https://dexscreener.com/solana/{addr}""".strip()


# ============================================================
# MAIN LOOP
# ============================================================

def main():
    if not MORALIS_API_KEY:
        logger.error("Please set MORALIS_API_KEY environment variable")
        logger.info("Get free key at: https://moralis.io")
        sys.exit(1)

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("⚠️  Telegram not configured — alerts will only appear in logs")
    else:
        test_telegram()

    logger.info("🚀 Pump.fun Scanner running")
    logger.info(f"   Liquidity: ${MIN_LIQUIDITY:,}+   Age: {MIN_AGE_HOURS}-{MAX_AGE_HOURS}h")
    logger.info(f"   Thresholds — Price: {MIN_PRICE_MOMENTUM*100:.0f}%  Liq: {(MIN_LIQUIDITY_GROWTH-1)*100:.0f}%  Vol spike: {MIN_VOLUME_SPIKE}x")
    logger.info(f"   Re-alert window: {REALERT_HOURS}h   Poll: {POLL_INTERVAL}s")

    seen = load_seen_tokens()
    logger.info(f"   Loaded {len(seen)} previously-seen tokens")

    while True:
        try:
            tokens = fetch_new_tokens()
            gems   = filter_gems(tokens, seen)

            now = datetime.now(timezone.utc).strftime("%H:%M:%S")
            logger.info(f"[{now}] Scanned {len(tokens)} tokens → {len(gems)} gem(s) found")

            for gem in gems:
                addr = gem["token"].get("tokenAddress")
                name = gem["token"].get("name", addr)
                msg  = format_alert(gem)

                logger.info(f"   🚨 ALERT: {name}")

                if send_telegram(msg):
                    seen[addr] = datetime.now(timezone.utc).isoformat()
                    logger.info(f"   ✅ Alert sent for {name}")
                else:
                    logger.error(f"   ❌ Alert FAILED for {name}")

            save_seen_tokens(seen)

        except Exception as e:
            logger.exception(f"Unexpected error in main loop: {e}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
