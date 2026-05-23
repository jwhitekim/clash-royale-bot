import asyncio
import io

import httpx
from PIL import Image, ImageDraw, ImageFont

CARD_W = 120
CARD_H = 120
TEXT_H = 22
CELL_H = CARD_H + TEXT_H
COLS = 4
ROWS = 2
BG_COLOR = (25, 25, 35)
TEXT_COLOR = (220, 220, 220)

_FONT_CANDIDATES = [
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
]


def _draw_outlined_text(draw, pos, text, font, fill, anchor="rb"):
    x, y = pos
    for dx, dy in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(1,-1),(-1,1),(1,1)]:
        draw.text((x+dx, y+dy), text, font=font, fill=(0, 0, 0), anchor=anchor)
    draw.text((x, y), text, font=font, fill=fill, anchor=anchor)


def _get_font(size: int = 10):
    for path in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


async def _fetch_image(url: str, client: httpx.AsyncClient):
    if not url:
        return None
    try:
        resp = await client.get(url, timeout=10)
        resp.raise_for_status()
        img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
        img.thumbnail((CARD_W, CARD_H), Image.LANCZOS)
        canvas = Image.new("RGBA", (CARD_W, CARD_H), (0, 0, 0, 0))
        offset_x = (CARD_W - img.width) // 2
        offset_y = (CARD_H - img.height) // 2
        canvas.paste(img, (offset_x, offset_y))
        return canvas
    except Exception:
        return None


async def build_deck_image(cards: list[dict]) -> bytes:
    """
    cards: [{"name": str, "iconUrl": str, "level": int, "evolved": bool, "is_champion": bool}, ...]
    2행 4열 카드 그리드 PNG를 bytes로 반환.
    """
    cards = cards[:8]
    async with httpx.AsyncClient() as client:
        images = await asyncio.gather(
            *[_fetch_image(c.get("iconUrl", ""), client) for c in cards]
        )

    grid = Image.new("RGBA", (COLS * CARD_W, ROWS * CELL_H), (*BG_COLOR, 255))
    draw = ImageDraw.Draw(grid)
    font = _get_font(10)
    badge_font = _get_font(9)
    placeholder = Image.new("RGBA", (CARD_W, CARD_H), (60, 60, 70, 255))

    for i, (card, img) in enumerate(zip(cards, images)):
        col = i % COLS
        row = i // COLS
        x, y = col * CARD_W, row * CELL_H
        grid.paste(img if img else placeholder, (x, y))

        if card.get("is_champion"):
            draw.rectangle([x, y, x + 22, y + 15], fill=(200, 150, 0))
            draw.text((x + 3, y + 2), "CH", font=badge_font, fill=(255, 255, 255))
        elif card.get("is_hero"):
            draw.rectangle([x, y, x + 30, y + 15], fill=(160, 0, 200))
            draw.text((x + 3, y + 2), "HERO", font=badge_font, fill=(255, 255, 255))
        elif card.get("evolved"):
            draw.rectangle([x, y, x + 26, y + 15], fill=(0, 160, 230))
            draw.text((x + 3, y + 2), "EVO", font=badge_font, fill=(255, 255, 255))

        level = card.get("level")
        if level is not None:
            lv_color = (255, 215, 0) if level == 15 else (255, 255, 255)
            _draw_outlined_text(draw, (x + CARD_W - 3, y + CARD_H - 3), str(level), badge_font, lv_color)

        draw.text(
            (x + CARD_W // 2, y + CARD_H + 2),
            card.get("name", ""),
            font=font,
            fill=TEXT_COLOR,
            anchor="mt",
        )

    buf = io.BytesIO()
    grid.convert("RGB").save(buf, format="PNG")
    buf.seek(0)
    return buf.read()
