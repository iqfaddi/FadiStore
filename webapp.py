from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

app = FastAPI()
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

@app.get("/ushare", response_class=HTMLResponse)
def ushare(request: Request):
    return templates.TemplateResponse("ushare.html", {"request": request})

@app.get("/netflix", response_class=HTMLResponse)
def netflix(request: Request):
    return templates.TemplateResponse("netflix.html", {"request": request})

@app.get("/shahid", response_class=HTMLResponse)
def shahid(request: Request):
    return templates.TemplateResponse("shahid.html", {"request": request})
