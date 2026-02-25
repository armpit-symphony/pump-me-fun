# 🚀 Pump Me Fun

A Telegram bot that monitors pump.fun for promising tokens before they pump. Get alerts when tokens show momentum or liquidity growth.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## What It Does

- Polls pump.fun every 5 minutes
- Filters tokens by age (4h - 1 week) and liquidity ($20k+)
- Detects **price momentum** (20%+ price rise)
- Detects **liquidity growth** (50%+ increase)
- Tracks **week-old tokens** with 2x liquidity
- Sends Telegram alerts when gems are found

## Use Case

Find tokens that have built up liquidity and community interest — before the crowd jumps in. Get early alerts to research and potentially trade.

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
# Set environment variables
export MORALIS_API_KEY="your_moralis_api_key"
export TELEGRAM_BOT_TOKEN="your_telegram_bot_token"
export TELEGRAM_CHAT_ID="your_chat_id"
```

Find your chat ID: Message @userinfobot on Telegram.

### 4. Run

```bash
pip install requests
python scanner.py
```

The scanner runs in the background. When a gem is found, you'll get a Telegram message.

### 5. Run in Background (optional)

```bash
nohup python scanner.py > scanner.log 2>&1 &
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `MIN_LIQUIDITY` | 20,000 | Minimum liquidity in USD |
| `MAX_AGE_HOURS` | 168 | Max age (1 week) |
| `MIN_AGE_HOURS` | 4 | Min age to avoid brand new |
| `MIN_PRICE_MOMENTUM` | 0.20 | Alert on 20%+ price rise |
| `MIN_LIQUIDITY_GROWTH` | 1.5 | Alert on 50%+ liquidity growth |
| `WEEKOLD_MULTIPLIER` | 2.0 | Alert on 2x liq for week-old |
| `POLL_INTERVAL` | 300 | Seconds between checks |

Edit the config section in `scanner.py` to customize.

## Indicators

The scanner detects these signals:

| Indicator | Description |
|-----------|-------------|
| 📈 Price Momentum | Price rose 20%+ since last check |
| 💧 Liquidity Growth | Liquidity increased 50%+ |
| 🗓️ Week-old 2x | Token 1+ week old with 2x liquidity |

## Sample Alert

```
💎 PUMP.FUN GEM ALERT

MikeWayne (MIKE)
Cg2c2kfuLv9xdrUeokR4JGGm...

💧 Liquidity: $530,000
⏰ Age: 6.5h

*Indicators:*
  📈 Price +25%
  💧 Liquidity +60%

🔗 https://pump.fun/...
```

## Requirements

- Python 3.10+
- Moralis API key (free tier works)
- Telegram bot token
- Internet connection

## Cost

- **Moralis**: Free tier includes pump.fun API
- **Telegram**: Free
- **Hosting**: Your server/VPS/Raspberry Pi

## Disclaimer

This tool is for informational purposes only. Not financial advice. Pump.fun tokens are high-risk — do your own research before trading.

## License

MIT
