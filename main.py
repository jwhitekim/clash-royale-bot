import asyncio
import logging
import os

import httpx
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from bot.handlers import (
    cmd_mydecks,
    cmd_register,
    cmd_search,
    cmd_setdecks,
    cmd_start,
)

load_dotenv()
logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")


async def _print_server_ip() -> None:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get("https://ifconfig.me")
            print(f"서버 IP: {r.text.strip()}")
    except Exception:
        pass


def main() -> None:
    asyncio.get_event_loop().run_until_complete(_print_server_ip())
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("search", cmd_search))
    app.add_handler(CommandHandler("register", cmd_register))
    app.add_handler(CommandHandler("mydecks", cmd_mydecks))
    app.add_handler(CommandHandler("setdecks", cmd_setdecks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, cmd_search))

    app.run_polling()


if __name__ == "__main__":
    main()
