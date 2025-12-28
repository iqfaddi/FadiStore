import os
import asyncio
import uvicorn

from webapp import create_app
from bot_admin import run_polling, bot_sender

async def main():
    port = int(os.getenv("PORT", "10000"))

    app = create_app(bot_sender=bot_sender)
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)

    run_bot = os.getenv("RUN_BOT", "1") == "1" and os.getenv("BOT_TOKEN")
    if run_bot:
        await asyncio.gather(server.serve(), run_polling())
    else:
        await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
