from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
import db
from bot_stock import stock_sender

def create_app():
    app = FastAPI()
    db.init_db()

    @app.get("/", response_class=HTMLResponse)
    async def home():
        return "<h2>Ushare + Stock Ready</h2>"

    @app.post("/buy_stock")
    async def buy_stock(phone: str = Form(...), service: str = Form(...), months: int = Form(...)):
        order = db.create_stock_order(phone, service, months)
        await stock_sender.notify(order)
        return {"status": "ok"}

    return app
