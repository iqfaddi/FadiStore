import os
from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

import db
# from security import verify_password   # ❌ لن نستخدمه الآن


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
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": None}
        )

    # 🔴 LOGIN بدون تحقق من الباسورد (TEST MODE)
    @app.post("/login")
    async def login(
        request: Request,
        phone: str = Form(...),
        password: str = Form(...)  # يبقى موجود لكن لن يُستخدم
    ):
        user = db.get_user_by_phone(phone)

        if not user:
            return templates.TemplateResponse(
                "login.html",
                {"request": request, "error": "User not found"}
            )

        # تجاوز التحقق من كلمة المرور
        request.session["uid"] = int(user["id"])
        return RedirectResponse("/dashboard", status_code=302)

    @app.get("/dashboard", response_class=HTMLResponse)
    async def dashboard(request: Request):
        uid = require_login(request)
        if not uid:
            return RedirectResponse("/", status_code=302)

        user = db.get_user_by_id(uid)

        # group packages by category for sections
        pkgs = db.list_packages()
        sections = {}
        for p in pkgs:
            cat = p.get("category", "General")
            sections.setdefault(cat, []).append(p)

        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "phone": user["phone"],
                "balance": db.fmt_lbp(int(user["balance"])),
                "packages": pkgs,
                "sections": sections,
                "orders": db.list_user_orders(uid),
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
            except Exception as e:
                print("BOT ERROR:", e)

        return RedirectResponse("/dashboard", status_code=302)

    # --------------------
    # Health check
    # --------------------
    @app.get("/healthz")
    async def healthz():
        return {"status": "ok"}

    return app
