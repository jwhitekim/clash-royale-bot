import asyncio
import logging
import os

import httpx
from dotenv import load_dotenv
from telegram.error import Conflict
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from bot.handlers import (
    cmd_mydecks,
    cmd_register,
    cmd_search,
    cmd_setdecks,
    cmd_start,
)

load_dotenv()
logging.basicConfig(level=logging.INFO)
logging.getLogger("api").setLevel(logging.DEBUG)
logging.getLogger("bot").setLevel(logging.DEBUG)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")


async def _print_server_ip() -> None:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get("https://ifconfig.me")
            print(f"서버 IP: {r.text.strip()}")
    except Exception:
        pass


logger = logging.getLogger(__name__)


async def _error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    if isinstance(context.error, Conflict):
        logger.warning("Conflict: 다른 봇 인스턴스가 실행 중입니다. 이전 인스턴스가 종료될 때까지 대기합니다.")
    else:
        logger.error("처리되지 않은 에러: %s", context.error, exc_info=context.error)


def main() -> None:
    asyncio.run(_print_server_ip())
    app = (
        Application.builder()
        .token(TOKEN)
        .read_timeout(30)
        .write_timeout(30)
        .connect_timeout(30)
        .pool_timeout(30)
        .build()
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("search", cmd_search))
    app.add_handler(CommandHandler("register", cmd_register))
    app.add_handler(CommandHandler("mydecks", cmd_mydecks))
    app.add_handler(CommandHandler("setdecks", cmd_setdecks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, cmd_search))
    app.add_error_handler(_error_handler)

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
