import os
from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

import db


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

    # 🔥 دخول تلقائي للتجربة
    @app.get("/autologin")
    async def autologin(request: Request):
        # ضع رقم مستخدم موجود في قاعدة البيانات
        user = db.get_user_by_phone("03177862")  # عدّل الرقم إذا لزم
        if not user:
            return HTMLResponse("No test user found in database")

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


# ✅ هذا السطر هو المهم جداً لحل مشكلة Not Found على Render
app = create_app()
