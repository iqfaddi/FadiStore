import os
from aiogram import Bot, Dispatcher
import db

BOT_TOKEN = os.getenv("BOT_TOKEN_STOCK")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

class StockBotSender:
    async def notify(self, order):
        text = f"""🆕 Stock Order
📱 Phone: {order['phone']}
📦 Service: {order['service_name']}
⏳ Months: {order['months']}
🧾 Order ID: {order['id']}
"""
        await bot.send_message(ADMIN_ID, text)

stock_sender = StockBotSender()

async def run_stock_bot():
    await dp.start_polling(bot)
