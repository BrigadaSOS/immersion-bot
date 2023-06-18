# immersion-bot

TMW's immersion bot

## Setup

- Check `requirements.txt`, install via `pip install -r requirements.txt` (recommended in venv)
- Set bot token in environment variable `TOKEN`
- Create a `.env` file on your root and add `CHANNEL_ID='{your_immersion_logs_channel_id}'`
- `cogs/jsons/settings.json` change `guildId`


## Run on Docker
```
docker build -t immersion-bot .
docker run -d -e TOKEN=<bot_token> immersion-bot
```

You need both prod.db and goals.db
