import os
from datetime import date, timedelta

import httpx
from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

import db
from security import verify_password


def create_app(bot_sender=None):
    app = FastAPI()

    templates = Jinja2Templates(directory="templates")

    # Sessions
    app.add_middleware(
        SessionMiddleware,
        secret_key=os.getenv("SECRET_KEY", "change-me")
    )

    # Init DB
    db.init_db()

    # --------------------
    # Helpers
    # --------------------
    def require_login(request: Request):
        return request.session.get("uid")

    def require_admin(request: Request):
        return bool(request.session.get("is_admin"))

    async def notify_stock_order(soid: int):
        token = os.getenv("STOCK_NOTIFY_BOT_TOKEN", "").strip()
        chat_id = os.getenv("STOCK_NOTIFY_CHAT_ID", "").strip()
        if not token or not chat_id:
            return

        o = db.get_stock_order(soid)
        if not o:
            return

        text = (
            "🆕 New STOCK Order\n\n"
            f"📱 Phone: {o['phone']}\n"
            f"📦 Service: {o['product_name']}\n"
            f"🗓️ Months: {o['months']}\n"
            f"🧾 Order ID: {o['id']}"
        )

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(url, data={"chat_id": chat_id, "text": text})

    # --------------------
    # Routes
    # --------------------
    @app.get("/", response_class=HTMLResponse)
    async def login_page(request: Request):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": None}
        )

    @app.get("/logout")
    async def logout(request: Request):
        request.session.clear()
        return RedirectResponse("/", status_code=302)

    @app.post("/login")
    async def login(
        request: Request,
        phone: str = Form(...),
        password: str = Form(...)
    ):
        user = db.get_user_by_phone(phone)

        if not user or not verify_password(password, user["password_hash"]):
            return templates.TemplateResponse(
                "login.html",
                {"request": request, "error": "Invalid credentials"}
            )

        request.session["uid"] = user["id"]
        request.session["phone"] = user["phone"]
        return RedirectResponse("/dashboard", status_code=302)

    @app.get("/dashboard", response_class=HTMLResponse)
    async def dashboard(request: Request):
        uid = require_login(request)
        if not uid:
            return RedirectResponse("/", status_code=302)

        phone = request.session.get("phone")
        user = db.get_user_by_phone(phone)

        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "phone": user["phone"],
                "balance": db.fmt_lbp(int(user["balance"])),
                "packages": db.list_packages(),
                "orders": db.list_user_orders(uid),
                "stock_products": db.list_stock_products(),
                "stock_orders": db.list_user_stock_orders(phone),
                "stock_accounts": db.list_user_stock_accounts(phone),
                "fmt": db.fmt_lbp,
            }
        )

    @app.post("/buy")
    async def buy(
        request: Request,
        package_id: int = Form(...),
        user_number: str = Form(...)
    ):
        uid = require_login(request)
        if not uid:
            return RedirectResponse("/", status_code=302)

        oid = db.create_order(uid, package_id, user_number)

        if bot_sender:
            try:
                await bot_sender.notify_new_order(oid)
            except Exception:
                pass

        return RedirectResponse("/dashboard", status_code=302)

    # --------------------
    # STOCK purchase
    # --------------------
    @app.post("/buy_stock")
    async def buy_stock(
        request: Request,
        product_id: int = Form(...),
        months: int = Form(...),
    ):
        phone = request.session.get("phone")
        if not phone:
            return RedirectResponse("/", status_code=302)

        months = max(1, min(int(months), 24))
        soid = db.create_stock_order(phone, product_id, months)

        try:
            await notify_stock_order(soid)
        except Exception:
            pass

        return RedirectResponse("/dashboard", status_code=302)

    # --------------------
    # Admin panel
    # --------------------
    @app.get("/admin", response_class=HTMLResponse)
    async def admin_login_page(request: Request):
        return templates.TemplateResponse(
            "admin_login.html",
            {"request": request, "error": None},
        )

    @app.post("/admin/login")
    async def admin_login(
        request: Request,
        password: str = Form(...),
    ):
        admin_password = os.getenv("ADMIN_PANEL_PASSWORD", "").strip()
        if not admin_password or password != admin_password:
            return templates.TemplateResponse(
                "admin_login.html",
                {"request": request, "error": "Invalid admin password"},
            )
        request.session["is_admin"] = True
        return RedirectResponse("/admin/dashboard", status_code=302)

    @app.get("/admin/logout")
    async def admin_logout(request: Request):
        request.session.pop("is_admin", None)
        return RedirectResponse("/admin", status_code=302)

    @app.get("/admin/dashboard", response_class=HTMLResponse)
    async def admin_dashboard(request: Request):
        if not require_admin(request):
            return RedirectResponse("/admin", status_code=302)

        pending = db.list_pending_stock_orders()
        return templates.TemplateResponse(
            "admin_dashboard.html",
            {"request": request, "pending": pending},
        )

    @app.post("/admin/fulfill_stock")
    async def admin_fulfill_stock(
        request: Request,
        soid: int = Form(...),
        account_email: str = Form(...),
        account_password: str = Form(...),
        profile_name: str = Form(""),
        start_date: str = Form(...),
        end_date: str = Form(...),
    ):
        if not require_admin(request):
            return RedirectResponse("/admin", status_code=302)

        db.fulfill_stock_order(
            soid,
            account_email.strip(),
            account_password.strip(),
            profile_name.strip(),
            start_date,
            end_date,
        )
        return RedirectResponse("/admin/dashboard", status_code=302)

    # --------------------
    # Health check
    # --------------------
    @app.get("/healthz")
    async def healthz():
        return {"status": "ok"}

    return app
