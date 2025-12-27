import asyncio, os
import uvicorn
from webapp import create_app
from bot_admin import run_polling
from bot_stock import run_stock_bot

async def main():
    app = create_app()
    port = int(os.getenv("PORT", "8000"))
    config = uvicorn.Config(app, host="0.0.0.0", port=port)
    server = uvicorn.Server(config)
    await asyncio.gather(server.serve(), run_polling(), run_stock_bot())

if __name__ == "__main__":
    asyncio.run(main())
