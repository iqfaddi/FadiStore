# Ushare Web + Telegram Admin (Free stack)

This project runs:
- A simple customer website (FastAPI)
- A Telegram admin bot (aiogram)

Both share the same SQLite database (`app.db`).

## Local run (Windows)
1) Create `.env` next to the files:
```
BOT_TOKEN=xxxxxxxx
ADMIN_ID=123456789
SECRET_KEY=any-random-string
```

2) Install:
```
py -3.11 -m pip install -r requirements.txt
```

3) Run:
```
py -3.11 start.py
```

Open http://127.0.0.1:8000

## Render deploy (Web Service - Free)
Build command:
`pip install -r requirements.txt`

Start command:
`python start.py`

Environment Variables on Render:
- `BOT_TOKEN`
- `ADMIN_ID`
- `SECRET_KEY`
- **Recommended:** `PYTHON_VERSION=3.11.9`

Note about SQLite:
- If your host resets the filesystem on redeploy, balances/orders can reset.
- For guaranteed persistence, switch DB to a free hosted Postgres (e.g., Supabase) later.
