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
    async def notify_new_order(self, oid: int):
        o = db.get_order(oid)
        if not o:
            return

        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Approve", callback_data=f"approve:{oid}"),
            InlineKeyboardButton(text="❌ Reject", callback_data=f"reject:{oid}")
        ]])

                if o.get("order_type") == "premium":
            rate = int(os.getenv("FX_RATE_LBP_PER_USD", "90000"))
            price_lbp = int(round(float(o.get("price_usd") or 0) * rate))
            text = (
                "🆕 New Order

"
                f"📱 Phone: {o['phone']}
"
                f"🛒 Product: {o.get('product_name') or '-'}
"
                f"⏳ Duration: {o.get('duration') or '-'}
"
                f"💰 Price: {float(o.get('price_usd') or 0):.2f}$ ({db.fmt_lbp(price_lbp)} LBP)
"
                f"🆔 Order ID: {o['id']}
"
            )
        else:
            text = (
                "🆕 New Order

"
                f"📱 Phone: {o['phone']}
"
                f"👤 Number: {o.get('user_number') or '-'}
"
                f"📦 Package: {o.get('package_name') or '-'}
"
                f"💰 Price: {db.fmt_lbp(int(o.get('package_price') or 0))} LBP
"
                f"🆔 Order ID: {o['id']}
"
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


@dp.message(Command("deliverorder"))
async def deliver_order_cmd(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        return
    parts = msg.text.split()
    if len(parts) < 3:
        await msg.answer("Usage: /deliverorder ORDER_ID PHONE [EMAIL] [PASSWORD] [NOTES]")
        return
    oid = int(parts[1])
    phone = parts[2]
    email = parts[3] if len(parts) >= 4 else None
    password = parts[4] if len(parts) >= 5 else None
    notes = " ".join(parts[5:]) if len(parts) >= 6 else None
    db.deliver_order(oid, phone=phone, email=email, password=password, notes=notes)
    await msg.answer("✅ Delivered / Updated order info")

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

# ================== CALLBACKS ==================

@dp.callback_query()
async def callbacks(call: types.CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer()
        return

    try:
        action, oid_s = call.data.split(":")
        oid = int(oid_s)
    except Exception:
        await call.answer()
        return

    o = db.get_order(oid)
    if not o:
        await call.answer("Order not found", show_alert=True)
        return

    if action == "approve":
        if int(o["balance"]) < int(o["package_price"]):
            await call.answer("Not enough balance", show_alert=True)
            return

        db.deduct_balance(o["phone"], int(o["package_price"]))
        db.update_order_status(oid, "approved")

        await call.message.edit_text("✅ Order Approved", reply_markup=None)
        await call.answer("Approved")

    elif action == "reject":
        db.update_order_status(oid, "rejected")

        await call.message.edit_text("❌ Order Rejected", reply_markup=None)
        await call.answer("Rejected")

# ================== RUN ==================

async def run_polling():
    await dp.start_polling(bot)