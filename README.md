# 🚀 Pump Me Fun

 Telegram bot that monitors pump.fun for newly launched tokens with high liquidity — before they pump.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## What It Does

- Polls pump.fun every 5 minutes
- Filters for tokens 1-48 hours old with **$200k+ liquidity**
- Detects **price momentum** (20%+ price rise)
- Detects **liquidity growth** (50%+ increase)
- Sends Telegram alert when a "gem" is found
- Tracks token history to detect trends

## Use Case

Find tokens that have built up liquidity or showing early momentum — before the crowd jumps in.

## Quick Start

### 1. Clone

```bash
git clone https://github.com/armpit-symphony/pump-me-fun.git
cd pump-me-fun
```

### 2. Install Dependencies

```bash
pip install requests
```

### 3. Configure

Edit `scanner.py` and replace these values:

```python
# Get free API key at https://moralis.io
MORALIS_API_KEY = "your_key_here"

# Your Telegram bot token
TELEGRAM_BOT_TOKEN = "your_bot_token"

# Your Telegram chat ID
TELEGRAM_CHAT_ID = "your_chat_id"
```

### 4. Run

```bash
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
| `MIN_LIQUIDITY` | 200,000 | Minimum liquidity in USD |
| `MAX_AGE_HOURS` | 48 | Max age of tokens to alert |
| `MIN_AGE_HOURS` | 1 | Min age (avoid brand new) |
| `MIN_PRICE_MOMENTUM` | 0.20 | Alert on 20%+ price rise |
| `MIN_LIQUIDITY_GROWTH` | 1.5 | Alert on 50%+ liquidity growth |
| `POLL_INTERVAL` | 300 | Seconds between checks |

## Indicators

The scanner detects these signals:

| Indicator | Description |
|-----------|-------------|
| 📈 Price Momentum | Price rose 20%+ since last check |
| 💧 Liquidity Growth | Liquidity increased 50%+ |
| 💎 High Liquidity | Liquidity exceeds $400k |

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
- **Hosting**: Your server/VPS

## Disclaimer

This tool is for informational purposes only. Not financial advice. Pump.fun tokens are high-risk — do your own research before trading.

## License

MIT
