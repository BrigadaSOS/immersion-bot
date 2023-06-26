# immersion-bot

Language learning immersion tracking tools

## Setup (bot)

- Use `npm install --dev`
- Set the following environment variables (can use a `.env` file):
  - TOKEN: <discord_bot_token>
  - GUILD_ID: <discord_guild_id>
  - CHANNEL_ID: <discord_channel_id>
- Use `cd bot && npm run dev`

## Run on Docker

Image has to be build from the root folder of the repo, since there are references
between the different packages and `common` package.

```
docker build -t nadelog-bot -f bot/Dockerfile .
docker run -d -e TOKEN=<bot_token> -e GUILD_ID=<guild_id> -e CHANNEL_ID=<channel_id> nadelog-bot
```
