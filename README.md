# 🚀 Pump Me Fun

A Telegram bot that monitors pump.fun for promising tokens before they pump. Get alerts when tokens show momentum or liquidity growth.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## What It Does

- Polls pump.fun every 5 minutes (configurable)
- Fetches up to 200 tokens per scan via Moralis
- Filters tokens by age (4h–1 week) and liquidity ($20k+)
- Detects **price momentum** (20%+ price rise since last check)
- Detects **liquidity growth** (50%+ increase since last check)
- Detects **volume spikes** (5x+ transaction count increase)
- Tracks **week-old tokens** (168h+) with 2x liquidity
- Sends Telegram alerts with retry logic when gems are found
- Re-alerts on the same token after 6 hours if it keeps pumping
- Auto-prunes price history to keep disk usage low

## Quick Start

### 1. Clone

```bash
git clone https://github.com/armpit-symphony/pump-me-fun.git
cd pump-me-fun
```

### 2. Get API Keys

| Service | How to Get |
|---------|------------|
| **Moralis** | Sign up free at [moralis.io](https://moralis.io) |
| **Telegram** | Message @BotFather to create a bot |

### 3. Configure

```bash
export MORALIS_API_KEY="your_moralis_api_key"
export TELEGRAM_BOT_TOKEN="your_telegram_bot_token"
export TELEGRAM_CHAT_ID="your_chat_id"
```

Find your chat ID: Message @userinfobot on Telegram.

### 4. Install & Run

```bash
pip install requests
python scanner.py
```

On startup the scanner sends a Telegram test message so you know immediately if the connection is working.

### 5. Run in Background with tmux (recommended for servers)

```bash
tmux new -s scanner
python scanner.py
# Detach: Ctrl+B then D
# Reattach later: tmux attach -t scanner
```

Or with nohup:

```bash
nohup python scanner.py > scanner.log 2>&1 &
```

## Configuration

Edit the config section at the top of `scanner.py`:

| Variable | Default | Description |
|----------|---------|-------------|
| `MIN_LIQUIDITY` | 20,000 | Minimum liquidity in USD |
| `MAX_AGE_HOURS` | 168 | Max age (1 week) |
| `MIN_AGE_HOURS` | 4 | Min age to avoid brand new tokens |
| `POLL_INTERVAL` | 300 | Seconds between scans |
| `FETCH_LIMIT` | 200 | Tokens fetched per scan |
| `MIN_PRICE_MOMENTUM` | 0.20 | Alert on 20%+ price rise |
| `MIN_LIQUIDITY_GROWTH` | 1.5 | Alert on 50%+ liquidity growth |
| `WEEKOLD_LIQ_MULTIPLIER` | 2.0 | Alert on 2x liq for 7d+ tokens |
| `MIN_VOLUME_SPIKE` | 5.0 | Alert on 5x transaction spike |
| `MIN_TXNS_FOR_SPIKE` | 10 | Min previous txns before spike counts (noise filter) |
| `REALERT_HOURS` | 6 | Re-alert same token after N hours (0 = never) |
| `HISTORY_MAX_AGE_HOURS` | 200 | Prune history entries older than this |

## Indicators

| Indicator | Description |
|-----------|-------------|
| 📈 Price Momentum | Price rose 20%+ since last check |
| 💧 Liquidity Growth | Liquidity increased 50%+ since last check |
| 📊 Volume Spike | Transaction count jumped 5x+ (min 10 prev txns) |
| 🗓️ Week-old 2x | Token is 7+ days old with 2x liquidity |

## Sample Alert

```
💎 PUMP.FUN GEM ALERT

MikeWayne (MIKE)
Cg2c2kfuLv9xdrUeokR4JGGm...

💧 Liquidity: $530,000
⏰ Age: 6.5h
📊 Vol 1h: $12,400  |  Txns: 87

Indicators:
  📈 Price +25%
  💧 Liquidity +60%

🔗 https://pump.fun/...
📈 https://dexscreener.com/solana/...
```

## Requirements

- Python 3.10+
- `requests` library (`pip install requests`)
- Moralis API key (free tier works)
- Telegram bot token + chat ID
- Internet connection / VPS

## Cost

- **Moralis**: Free tier includes pump.fun API
- **Telegram**: Free
- **DexScreener**: Free, no key needed
- **Hosting**: Your server/VPS/Raspberry Pi

## Disclaimer

This tool is for informational purposes only. Not financial advice. Pump.fun tokens are extremely high-risk — do your own research before trading.

## License

MIT
