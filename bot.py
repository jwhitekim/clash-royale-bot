import asyncio
import logging
import os

import httpx
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from clash_api import get_player_full
from image_builder import build_deck_image
from scraper import search_player
from storage import load_my_decks, save_my_decks

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
MODE = os.getenv("MODE", "polling")
RAILWAY_DOMAIN = os.getenv("RAILWAY_DOMAIN", "")


TYPE_LABEL = {"riverRaceDuel": "듀얼", "riverRacePvP": "1v1"}


def _fmt_deck(cards: list[str]) -> str:
    return " · ".join(cards[:8]) if cards else "(카드 정보 없음)"


# ── 커맨드 핸들러 ──────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "⚔️ 클래시로얄 클랜전 듀얼 봇\n\n"
        "📌 사용법\n"
        "/search 닉네임 — 플레이어 검색 (최대 5명)\n"
        "/search 닉네임 클랜이름 — 클랜으로 좁혀서 검색\n"
        "예: /search Simply COWNAX\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "기타 명령어\n"
        "/setdecks — 내 듀얼 덱 등록\n"
        "/mydecks — 내 덱 확인\n"
    )
    await update.message.reply_text(text)


async def _send_player_result(update: Update, player_data: dict) -> None:
    await update.message.reply_text(
        f"👤 {player_data['name']} | 🏆 {player_data['trophies']} | Lv.{player_data['level']}\n"
        f"🏰 클랜: {player_data['clan']}"
    )
    duels = player_data.get("duels", [])
    if not duels:
        await update.message.reply_text("최근 클랜전 기록이 없습니다.")
    else:
        for i, duel in enumerate(duels, 1):
            label = TYPE_LABEL.get(duel.get("type", ""), "클랜전")
            caption = f"[{i}세트 — {label}]"
            try:
                img_bytes = await build_deck_image(duel["cards"])
                await update.message.reply_photo(photo=img_bytes, caption=caption)
            except Exception as e:
                logger.error("이미지 생성 실패: %s", e)
                names = " · ".join(c["name"] for c in duel["cards"])
                await update.message.reply_text(f"{caption}\n{names}")
    my_decks_data = load_my_decks()
    my_decks = my_decks_data.get("decks", [])
    if my_decks:
        lines = ["📋 내 듀얼 덱\n"]
        for i, deck in enumerate(my_decks, 1):
            lines.append(f"[덱{i}] {deck.get('name', '')}")
            lines.append(_fmt_deck(deck.get("cards", [])))
            lines.append("")
        await update.message.reply_text("\n".join(lines).strip())


async def cmd_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()

    # 번호 선택 처리
    pending = context.user_data.get("search_results")
    if pending and not context.args and text.isdigit():
        idx = int(text) - 1
        if idx < 0 or idx >= len(pending):
            await update.message.reply_text(f"1~{len(pending)} 사이 번호를 입력해주세요.")
            return
        selected = pending[idx]
        context.user_data.pop("search_results")
        await update.message.reply_text(f"⏳ {selected['name']} 덱 조회 중...")
        try:
            player_data = await get_player_full(selected["tag"])
        except Exception as e:
            logger.error("API 호출 실패 (%s): %s", selected["tag"], e)
            await update.message.reply_text("❌ 플레이어를 찾을 수 없습니다.")
            return
        await _send_player_result(update, player_data)
        return

    # 검색어 추출
    if context.args:
        nickname = context.args[0]
        clan_name = " ".join(context.args[1:])
    else:
        parts = text.split()
        if not parts:
            return
        nickname = parts[0]
        clan_name = " ".join(parts[1:])

    query_desc = f"'{nickname}'" + (f" (클랜: {clan_name})" if clan_name else "")
    await update.message.reply_text(f"🔍 {query_desc} 검색 중...")

    players = await search_player(nickname, clan_name)
    if not players:
        msg = "검색 결과가 없습니다. 클랜이름을 확인해주세요." if clan_name else "검색 결과가 없습니다."
        await update.message.reply_text(msg)
        return

    context.user_data["search_results"] = players
    lines = ["플레이어를 선택하세요 (번호 입력):\n"]
    for i, p in enumerate(players, 1):
        clan_info = f"  [{p['clan']}]" if p.get("clan") else ""
        lines.append(f"{i}. {p['name']}  {p['tag']}{clan_info}")
    await update.message.reply_text("\n".join(lines))


async def cmd_register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if not args:
        await update.message.reply_text("사용법: /register #태그\n예: /register #ABC123")
        return

    tag = args[0].upper()
    if not tag.startswith("#"):
        tag = f"#{tag}"

    data = load_my_decks()
    decks = data.get("decks", [])
    save_my_decks(tag, decks)
    await update.message.reply_text(f"✅ 태그 등록 완료: {tag}")


async def cmd_mydecks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    data = load_my_decks()
    decks = data.get("decks", [])
    tag = data.get("player_tag", "미등록")

    if not decks:
        await update.message.reply_text("저장된 덱이 없습니다.\n/setdecks로 등록해주세요.")
        return

    lines = [f"🃏 내 듀얼 덱 ({tag})\n"]
    for i, deck in enumerate(decks, 1):
        lines.append(f"[덱{i}] {deck.get('name', '')}")
        lines.append(_fmt_deck(deck.get("cards", [])))
        lines.append("")

    await update.message.reply_text("\n".join(lines).strip())


async def cmd_setdecks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text(
            "사용법: /setdecks 덱1카드1,카드2,...|덱2카드1,...|덱3카드1,...\n"
            "카드는 쉼표, 덱은 | 구분"
        )
        return

    raw = " ".join(context.args)
    parts = raw.split("|")
    if len(parts) != 3:
        await update.message.reply_text("덱 3개를 | 로 구분해서 입력해주세요.")
        return

    decks = []
    for i, part in enumerate(parts, 1):
        cards = [c.strip() for c in part.split(",") if c.strip()]
        if len(cards) != 8:
            await update.message.reply_text(f"덱{i}의 카드가 {len(cards)}장입니다. 8장이어야 합니다.")
            return
        decks.append({"name": f"덱{i}", "cards": cards})

    data = load_my_decks()
    tag = data.get("player_tag", "")
    save_my_decks(tag, decks)
    await update.message.reply_text("✅ 덱 3개 저장 완료!")


# ── 진입점 ────────────────────────────────────────────────────────────────────

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

    if MODE == "webhook":
        app.run_webhook(
            listen="0.0.0.0",
            port=int(os.environ.get("PORT", 8080)),
            webhook_url=f"https://{RAILWAY_DOMAIN}/{TOKEN}",
        )
    else:
        app.run_polling()


if __name__ == "__main__":
    main()
