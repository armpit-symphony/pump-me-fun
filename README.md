# 🚀 Pump Me Fun

 Telegram bot that monitors pump.fun for newly launched tokens with high liquidity — before they pump.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## What It Does

- Polls pump.fun for new tokens every 5 minutes
- Filters for tokens 1-48 hours old with **$200k+ liquidity**
- Sends Telegram alert when a "gem" is found
- Tracks seen tokens to avoid duplicates

## Use Case

Find tokens that have built up liquidity but haven't pumped yet. Get early alerts to potentially buy before the crowd.

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

The scanner runs in the background, polling every 5 minutes. When a gem is found, you'll get a Telegram message.

### 5. Run in Background (optional)

```bash
nohup python scanner.py > scanner.log 2>&1 &
```

## Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `MIN_LIQUIDITY` | 200,000 | Minimum liquidity in USD |
| `MAX_AGE_HOURS` | 48 | Max age of tokens to alert on |
| `POLL_INTERVAL` | 300 | Seconds between checks |
| `SEEN_TOKENS_FILE` | `seen_tokens.json` | File to track alerted tokens |

## Sample Alert

```
💎 PUMP.FUN GEM FOUND

MikeWayne (MIKE)
Cg2c2kfuLv9xdrU...

💧 Liquidity: $530,000
⏰ 2.5h old

🔗 https://pump.fun/...
```

## Requirements

- Python 3.10+
- Moralis API key (free)
- Telegram bot token
- Internet connection

## Cost

- **Moralis**: Free tier includes pump.fun API
- **Telegram**: Free
- **Hosting**: Your server (VPS, Raspberry Pi, etc.)

## Disclaimer

This tool is for informational purposes only. Not financial advice. Pump.fun tokens are high-risk — do your own research before trading.

## License

MIT
