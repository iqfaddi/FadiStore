
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import os, db

def create_app():
    app = FastAPI()
    templates = Jinja2Templates(directory="templates")
    app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY","change-me"))
    db.init_db()

    @app.get("/", response_class=HTMLResponse)
    async def login(request: Request):
        return templates.TemplateResponse("login.html", {"request": request})

    @app.get("/dashboard", response_class=HTMLResponse)
    async def dashboard(request: Request):
        return templates.TemplateResponse("dashboard.html", {"request": request})

    return app
