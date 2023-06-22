# immersion-bot

TMW's immersion bot

## Setup

- Check `requirements.txt`, install via `pip install -r requirements.txt` (recommended in venv)
- Set bot token in environment variable `TOKEN`
- `cogs/jsons/settings.json` change `guild_id` and `channel_id`


## Run on Docker
```
docker build -t immersion-bot .
docker run -d -e TOKEN=<bot_token> immersion-bot
```

You need both prod.db and goals.db
