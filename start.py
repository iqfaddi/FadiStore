import os
import asyncio
import uvicorn

from webapp import create_app
from bot_admin import run_polling, bot_sender

async def main():
    port = int(os.getenv("PORT", "8000"))

    app = create_app(bot_sender=bot_sender)
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)

    # Run web server + telegram polling together
    await asyncio.gather(
        server.serve(),
        run_polling(),
    )

if __name__ == "__main__":
    asyncio.run(main())
