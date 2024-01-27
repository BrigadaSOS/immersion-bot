# immersion-bot

BrigadaSOS's immersion bot, forked from TMW's immersion bot.

## Setup

- Use `pipenv install` or `pip -m venv .venv && pip install -r requirements.txt`
- Set the following environment variables (can use a `.env` file):
  - TOKEN: <discord_bot_token>
  - GUILD_ID: <discord_guild_id>
  - CHANNEL_ID: <discord_channel_id>
- Run `python ./immersion-bot/launch_bot.py`

## Run on Docker
```
docker build -t immersion-bot .
docker run -d -e TOKEN=<bot_token> -e GUILD_ID=<guild_id> -e CHANNEL_ID=<channel_id> immersion-bot
```
