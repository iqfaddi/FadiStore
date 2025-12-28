# Ushare Web + Telegram Admin (Free stack)

This project runs:
- A customer website (FastAPI)
- A Telegram admin bot for **Alfa Ushare** only (aiogram)
- A simple **Admin Panel (web)** for manual "Stock" fulfillment

All data is stored in Postgres via `DATABASE_URL` (works with Supabase Postgres).

## Local run (Windows)
1) Create `.env` next to the files:
```
BOT_TOKEN=xxxxxxxx
ADMIN_ID=123456789
SECRET_KEY=any-random-string
DATABASE_URL=postgresql://...

# Stock notifications (separate bot):
STOCK_NOTIFY_BOT_TOKEN=xxxxxxxx
STOCK_NOTIFY_CHAT_ID=123456789

# Admin web panel
ADMIN_PANEL_PASSWORD=strong-password
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

Admin panel:
- Open `.../admin` and login with `ADMIN_PANEL_PASSWORD` to fulfill Stock orders.
