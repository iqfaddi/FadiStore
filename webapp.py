import os
from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

import db
from security import verify_password


def create_app(bot_sender=None):
    app = FastAPI()
    templates = Jinja2Templates(directory="templates")

    app.add_middleware(
        SessionMiddleware,
        secret_key=os.getenv("SECRET_KEY", "change-me")
    )

    db.init_db()

    def require_login(request: Request):
        return request.session.get("uid")

    def must_login(request: Request):
        uid = require_login(request)
        if not uid:
            return None, RedirectResponse("/login", status_code=302)
        return int(uid), None

    # --------------------
    # Auth
    # --------------------
    @app.get("/login", response_class=HTMLResponse)
    async def login_page(request: Request):
        return templates.TemplateResponse("login.html", {"request": request, "error": None})

    @app.post("/login")
    async def login(
        request: Request,
        phone: str = Form(...),
        password: str = Form(...)
    ):
        user = db.get_user_by_phone(phone)
        if not user or not verify_password(password, user["password_hash"]):
            return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})
        request.session["uid"] = int(user["id"])
        return RedirectResponse("/", status_code=302)

    @app.get("/logout")
    async def logout(request: Request):
        request.session.clear()
        return RedirectResponse("/login", status_code=302)

    # --------------------
    # Sections
    # --------------------
    @app.get("/", response_class=HTMLResponse)
    async def home(request: Request):
        uid, redir = must_login(request)
        if redir:
            return redir
        user = db.get_user_by_id(uid)
        return templates.TemplateResponse(
            "home.html",
            {"request": request, "phone": user["phone"], "balance": db.fmt_lbp(int(user["balance"]))}
        )

    @app.get("/ushare", response_class=HTMLResponse)
    async def ushare(request: Request):
        uid, redir = must_login(request)
        if redir:
            return redir
        user = db.get_user_by_id(uid)
        return templates.TemplateResponse(
            "ushare.html",
            {
                "request": request,
                "phone": user["phone"],
                "balance": db.fmt_lbp(int(user["balance"])),
                "packages": db.list_packages(),
                "fmt": db.fmt_lbp,
                "title": "Alfa uShare"
            }
        )

    @app.post("/buy-ushare")
    async def buy_ushare(
        request: Request,
        package_id: int = Form(...),
        user_number: str = Form(...)
    ):
        uid, redir = must_login(request)
        if redir:
            return redir
        oid = db.create_order(uid, package_id, user_number)
        if bot_sender:
            try:
                await bot_sender.notify_new_order(oid, order_type="ushare")
            except Exception as e:
                print("BOT ERROR:", e)
        return RedirectResponse("/my-orders", status_code=302)

    # --------------------
    # Premium sections
    # --------------------
    def premium_page(request: Request, slug: str, title: str, perks_html: str):
        uid, redir = must_login(request)
        if redir:
            return redir
        user = db.get_user_by_id(uid)
        groups = db.list_premium_groups(slug)
        return templates.TemplateResponse(
            "premium.html",
            {
                "request": request,
                "phone": user["phone"],
                "balance": db.fmt_lbp(int(user["balance"])),
                "product_title": title,
                "perks": perks_html,
                "groups": groups,
                "title": title
            }
        )

    @app.get("/netflix", response_class=HTMLResponse)
    async def netflix(request: Request):
        return premium_page(
            request,
            slug="netflix",
            title="Netflix",
            perks_html="Premium Subscription<br>- Instant Delivery<br>- 4k Quality<br>- 4 Screens<br>- Unlimited Offline Downloads"
        )

    @app.get("/shahid", response_class=HTMLResponse)
    async def shahid(request: Request):
        return premium_page(
            request,
            slug="shahid",
            title="Shahid VIP",
            perks_html="Premium Subscription<br>- Instant Delivery<br>- 4k Quality"
        )

    @app.post("/buy-premium")
    async def buy_premium(request: Request, plan_id: int = Form(...)):
        uid, redir = must_login(request)
        if redir:
            return redir

        fx = int(os.getenv("FX_RATE_LBP_PER_USD", "90000"))
        poid = db.create_premium_order(uid, plan_id, fx_rate=fx)

        if bot_sender:
            try:
                await bot_sender.notify_new_order(poid, order_type="premium")
            except Exception as e:
                print("BOT ERROR:", e)

        return RedirectResponse("/my-orders", status_code=302)

    # --------------------
    # My Orders
    # --------------------
    @app.get("/my-orders", response_class=HTMLResponse)
    async def my_orders(request: Request):
        uid, redir = must_login(request)
        if redir:
            return redir
        user = db.get_user_by_id(uid)
        orders = db.list_all_user_orders(uid)
        return templates.TemplateResponse(
            "orders.html",
            {"request": request, "phone": user["phone"], "balance": db.fmt_lbp(int(user["balance"])), "orders": orders, "title": "My Orders"}
        )

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok"}

    return app
