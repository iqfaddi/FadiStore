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

    # --------------------
    # Routes
    # --------------------
    @app.get("/", response_class=HTMLResponse)
    async def login_page(request: Request):
        # If already logged in, go straight to dashboard
        if request.session.get("uid"):
            return RedirectResponse("/dashboard", status_code=302)
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": None}
        )

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

        request.session["uid"] = int(user["id"])
        return RedirectResponse("/dashboard", status_code=302)

    @app.get("/dashboard", response_class=HTMLResponse)
    async def dashboard(request: Request):
        uid = require_login(request)
        if not uid:
            return RedirectResponse("/", status_code=302)

        user = db.get_user_by_id(uid)

        products = db.list_products(active_only=True)

        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "phone": user["phone"],
                "balance": db.fmt_lbp(int(user["balance"])),
                "packages": db.list_packages(),
                "products": products,
                "orders": db.list_user_orders(uid),
                "fmt_lbp": db.fmt_lbp,
                "fmt_usd": db.fmt_usd,
            },
        )

    @app.post("/buy_alfa")
    async def buy_alfa(
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
            except Exception as e:
                print("BOT ERROR:", e)

        return RedirectResponse("/dashboard", status_code=302)

    @app.post("/buy_plan")
    async def buy_plan(
        request: Request,
        plan_id: int = Form(...)
    ):
        uid = require_login(request)
        if not uid:
            return RedirectResponse("/", status_code=302)

        oid = db.create_subscription_order(uid, plan_id)

        if bot_sender:
            try:
                await bot_sender.notify_new_order(oid)
            except Exception as e:
                print("BOT ERROR:", e)

        return RedirectResponse("/dashboard", status_code=302)

    @app.get("/logout")
    async def logout(request: Request):
        request.session.clear()
        return RedirectResponse("/", status_code=302)

    # --------------------
    # Health check
    # --------------------
    @app.get("/healthz")
    async def healthz():
        return {"status": "ok"}

    return app
