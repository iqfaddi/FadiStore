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
        secret_key=os.getenv("SECRET_KEY", "change-me"),
    )

    # Init DB
    db.init_db()

    # --------------------
    # Helpers
    # --------------------
    def require_login(request: Request):
        uid = request.session.get("uid")
        return int(uid) if uid else None

    async def notify_bot_order(oid: int):
        if not bot_sender:
            return
        try:
            await bot_sender.notify_new_order(oid)
        except Exception as e:
            print("BOT ERROR:", e)

    # --------------------
    # Auth
    # --------------------
    @app.get("/", response_class=HTMLResponse)
    async def root(request: Request):
        uid = require_login(request)
        if uid:
            user = db.get_user_by_id(uid)
            return templates.TemplateResponse(
                "home.html",
                {
                    "request": request,
                    "title": "Home",
                    "header_title": "Fadi Store",
                    "phone": user["phone"],
                    "balance": db.fmt_lbp(int(user["balance"])),
                },
            )
        return templates.TemplateResponse("login.html", {"request": request})

    @app.post("/login")
    async def login(request: Request, phone: str = Form(...), password: str = Form(...)):
        user = db.get_user_by_phone(phone)
        if not user or not verify_password(password, user["password_hash"]):
            return templates.TemplateResponse(
                "login.html",
                {"request": request, "error": "Invalid credentials"},
            )
        request.session["uid"] = int(user["id"])
        return RedirectResponse("/", status_code=302)

    @app.get("/logout")
    async def logout(request: Request):
        request.session.clear()
        return RedirectResponse("/", status_code=302)

    # --------------------
    # Sections
    # --------------------
    @app.get("/ushare", response_class=HTMLResponse)
    async def ushare_page(request: Request):
        uid = require_login(request)
        if not uid:
            return RedirectResponse("/", status_code=302)
        user = db.get_user_by_id(uid)
        return templates.TemplateResponse(
            "ushare.html",
            {
                "request": request,
                "title": "Alfa uShare",
                "header_title": "Alfa uShare",
                "phone": user["phone"],
                "balance": db.fmt_lbp(int(user["balance"])),
                "packages": db.list_packages(),
                "orders": db.list_user_orders(uid),
                "fmt": db.fmt_lbp,
            },
        )

    @app.post("/buy-ushare")
    async def buy_ushare(
        request: Request,
        package_id: int = Form(...),
        user_number: str = Form(...),
    ):
        uid = require_login(request)
        if not uid:
            return RedirectResponse("/", status_code=302)

        user = db.get_user_by_id(uid)
        pkg = db.get_package(package_id)
        if not pkg:
            return RedirectResponse("/ushare", status_code=302)

        price_lbp = int(pkg["price"])
        if int(user["balance"]) < price_lbp:
            # render same page with error
            return templates.TemplateResponse(
                "ushare.html",
                {
                    "request": request,
                    "title": "Alfa uShare",
                    "header_title": "Alfa uShare",
                    "phone": user["phone"],
                    "balance": db.fmt_lbp(int(user["balance"])),
                    "packages": db.list_packages(),
                    "orders": db.list_user_orders(uid),
                    "fmt": db.fmt_lbp,
                    "error": "Insufficient balance",
                },
            )

        db.deduct_balance(user["phone"], price_lbp)
        oid = db.create_ushare_order(uid, package_id, user_number)
        await notify_bot_order(oid)
        return RedirectResponse("/ushare", status_code=302)

    def premium_context(uid: int, slug: str, page_title: str):
        user = db.get_user_by_id(uid)
        variants = db.list_variants_with_plans(slug)
        return {
            "phone": user["phone"],
            "balance": db.fmt_lbp(int(user["balance"])),
            "variants": variants,
            "orders": db.list_user_orders(uid),
            "page_title": page_title,
            "title": page_title,
            "header_title": page_title,
        }

    @app.get("/netflix", response_class=HTMLResponse)
    async def netflix_page(request: Request):
        uid = require_login(request)
        if not uid:
            return RedirectResponse("/", status_code=302)
        ctx = premium_context(uid, "netflix", "Netflix")
        ctx["request"] = request
        return templates.TemplateResponse("premium.html", ctx)

    @app.get("/shahid", response_class=HTMLResponse)
    async def shahid_page(request: Request):
        uid = require_login(request)
        if not uid:
            return RedirectResponse("/", status_code=302)
        ctx = premium_context(uid, "shahid", "Shahid VIP")
        ctx["request"] = request
        return templates.TemplateResponse("premium.html", ctx)

    @app.post("/buy-premium")
    async def buy_premium(request: Request, variant_id: int = Form(...), plan_id: int = Form(...)):
        uid = require_login(request)
        if not uid:
            return RedirectResponse("/", status_code=302)

        user = db.get_user_by_id(uid)
        plan = db.get_plan(plan_id)
        variant = db.get_variant(variant_id)
        if not plan or not variant:
            return RedirectResponse("/", status_code=302)

        # Deduct as LBP at rate
        rate = int(os.getenv("FX_RATE_LBP_PER_USD", "90000"))
        price_lbp = int(round(float(plan["price_usd"]) * rate))
        if int(user["balance"]) < price_lbp:
            # redirect back to section
            back = "/netflix" if variant["product_slug"] == "netflix" else "/shahid"
            return RedirectResponse(back, status_code=302)

        db.deduct_balance(user["phone"], price_lbp)
        oid = db.create_premium_order(
            user_id=uid,
            product_name=f"{variant['product_title']} - {variant['name']}",
            duration=plan["duration"],
            price_usd=float(plan["price_usd"]),
        )
        await notify_bot_order(oid)
        back = "/netflix" if variant["product_slug"] == "netflix" else "/shahid"
        return RedirectResponse(back, status_code=302)

    @app.get("/my-orders", response_class=HTMLResponse)
    async def my_orders(request: Request):
        uid = require_login(request)
        if not uid:
            return RedirectResponse("/", status_code=302)
        user = db.get_user_by_id(uid)
        return templates.TemplateResponse(
            "orders.html",
            {
                "request": request,
                "title": "My Order",
                "header_title": "My Order",
                "phone": user["phone"],
                "balance": db.fmt_lbp(int(user["balance"])),
                "orders": db.list_user_orders(uid),
            },
        )

    # --------------------
    # Health check
    # --------------------
    @app.get("/healthz")
    async def healthz():
        return {"status": "ok"}

    return app
