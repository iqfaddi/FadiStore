import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

import db
from security import hash_password, gen_password, parse_amount

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def is_admin(uid: int) -> bool:
    return uid == ADMIN_ID

# ================== BOT SENDER ==================

class BotSender:
    async def notify_new_order(self, oid: int, order_type: str = "ushare"):
        if order_type == "premium":
            o = db.get_premium_order(oid)
        else:
            o = db.get_order(oid)
        if not o:
            return

        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Approve", callback_data=f"approve:{order_type}:{oid}"),
            InlineKeyboardButton(text="❌ Reject", callback_data=f"reject:{order_type}:{oid}")
        ]])

        if order_type == "premium":
            text = (
                "🆕 New Order\n\n"
                f"📱 Phone: {o['phone']}\n"
                f"🛍 Product: {o['product_title']}\n"
                f"📌 Type: {o['group_name']}\n"
                f"⏳ Duration: {o['duration_label']}\n"
                f"💵 Price: {float(o['price_usd']):.2f}$\n"
                f"💳 Deducted: {db.fmt_lbp(int(o['deducted_lbp']))} LBP\n"
                f"🆔 Order ID: {oid}"
            )
        else:
            text = (
                "🆕 New Order\n\n"
                f"📱 Phone: {o['phone']}\n"
                f"👤 Number: {o['user_number']}\n"
                f"📦 Package: {o['package_name']}\n"
                f"💰 Price: {db.fmt_lbp(int(o['package_price']))} LBP\n"
                f"🆔 Order ID: {oid}"
            )

        await bot.send_message(ADMIN_ID, text, reply_markup=kb)
bot_sender = BotSender()

# ================== COMMANDS ==================

@dp.message(Command("createuser"))
async def create_user_cmd(msg: types.Message):
    if not is_admin(msg.from_user.id):
        return

    parts = msg.text.split()
    if len(parts) < 2:
        await msg.answer("Usage: /createuser PHONE [PASSWORD]")
        return

    phone = parts[1]
    password = parts[2] if len(parts) >= 3 else gen_password(6)

    if db.get_user_by_phone(phone):
        await msg.answer("❌ User already exists")
        return

    db.create_user(phone, hash_password(password))
    await msg.answer(f"✅ User Created\n📱 {phone}\n🔑 {password}")

@dp.message(Command("addbalance"))
async def add_balance_cmd(msg: types.Message):
    if not is_admin(msg.from_user.id):
        return

    parts = msg.text.split(maxsplit=2)
    if len(parts) < 3:
        await msg.answer("Usage: /addbalance PHONE AMOUNT")
        return

    phone = parts[1]
    amount = parse_amount(parts[2])

    u = db.get_user_by_phone(phone)
    if not u:
        await msg.answer("❌ User not found")
        return

    db.add_balance(phone, amount)
    await msg.answer(
        f"✅ Balance Updated\n"
        f"📱 {phone}\n"
        f"💰 New Balance: {db.fmt_lbp(int(u['balance']) + amount)} LBP"
    )

@dp.message(Command("userinfo"))
async def user_info_cmd(msg: types.Message):
    if not is_admin(msg.from_user.id):
        return

    parts = msg.text.split()
    if len(parts) != 2:
        await msg.answer("Usage: /userinfo PHONE")
        return

    u = db.get_user_by_phone(parts[1])
    if not u:
        await msg.answer("❌ User not found")
        return

    await msg.answer(
        "👤 User Info\n\n"
        f"📱 Phone: {u['phone']}\n"
        f"💰 Balance: {db.fmt_lbp(int(u['balance']))} LBP\n"
        f"🆔 ID: {u['id']}"
    )


@dp.message(Command("deliverorder"))
async def deliver_order_cmd(msg: types.Message):
    if not is_admin(msg.from_user.id):
        return

    # Usage:
    # /deliverorder TYPE ORDER_ID PHONE [EMAIL] [PASSWORD] [NOTES...]
    parts = msg.text.split(maxsplit=5)
    if len(parts) < 4:
        await msg.answer("Usage: /deliverorder TYPE ORDER_ID PHONE [EMAIL] [PASSWORD] [NOTES]")
        return

    order_type = parts[1].strip().lower()
    oid = int(parts[2])
    phone = parts[3]

    email = None
    password = None
    notes = None

    if len(parts) >= 5:
        email = parts[4]
    if len(parts) >= 6:
        # parts[5] may include password + notes if spaces, so we keep it as one field
        rest = parts[5].split(maxsplit=1)
        password = rest[0]
        if len(rest) > 1:
            notes = rest[1]

    db.upsert_delivery(order_type, oid, phone=phone, email=email, password=password, notes=notes)
    await msg.answer(f"✅ Delivered saved for {order_type} #{oid}")
# ================== CALLBACKS ==================

@dp.callback_query()
async def callbacks(call: types.CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer()
        return

    try:
        action, order_type, oid_s = call.data.split(":")
        oid = int(oid_s)
    except Exception:
        await call.answer()
        return

    if order_type == "premium":
        o = db.get_premium_order(oid)
    else:
        o = db.get_order(oid)

    if not o:
        await call.answer("Order not found", show_alert=True)
        return

    if action == "approve":
        if order_type == "premium":
            db.update_premium_order_status(oid, "approved")
        else:
            db.update_order_status(oid, "approved")
        await call.message.edit_text("✅ Order Approved", reply_markup=None)
        await call.answer("Approved")
        return

    if action == "reject":
        if order_type == "premium":
            db.update_premium_order_status(oid, "rejected")
        else:
            db.update_order_status(oid, "rejected")
        await call.message.edit_text("❌ Order Rejected", reply_markup=None)
        await call.answer("Rejected")
        return

    await call.answer()
# ================== RUN ==================

async def run_polling():
    await dp.start_polling(bot)