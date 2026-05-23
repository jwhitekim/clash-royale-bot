import asyncio
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://proxy.royaleapi.dev/v1"
CLAN_WAR_TYPES = {"riverRaceDuel", "riverRacePvP"}

_CARD_META: dict = {}  # card id -> cards.json entry


async def _load_card_meta() -> dict:
    global _CARD_META
    if _CARD_META:
        return _CARD_META
    url = "https://royaleapi.github.io/cr-api-data/json/cards.json"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()
    _CARD_META = {c["id"]: c for c in data if "id" in c}
    return _CARD_META


def _headers() -> dict:
    return {"Authorization": f"Bearer {os.getenv('CR_API_KEY', '')}"}


def _encode_tag(tag: str) -> str:
    return tag.replace("#", "%23")


async def get_player(tag: str) -> dict:
    url = f"{BASE_URL}/players/{_encode_tag(tag)}"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, headers=_headers())
        resp.raise_for_status()
        data = resp.json()

    return {
        "name": data.get("name", ""),
        "trophies": data.get("trophies", 0),
        "level": data.get("expLevel", 0),
        "clan": data.get("clan", {}).get("name", "없음"),
        "tag": tag,
    }


_RARITY_OFFSET = {
    "Common":    1,  # 14 → 15
    "Rare":      3,  # 12 → 15
    "Epic":      5,  # 10 → 15
    "Legendary": 6,  #  9 → 15
    "Champion":  6,  #  9 → 15
}

# cards.json 업데이트 지연 대비 하드코딩 보완 목록
_CHAMPION_NAMES = {
    "Archer Queen",
    "Golden Knight",
    "Skeleton King",
    "Mighty Miner",
    "Monk",
    "Little Prince",
    "Dagger Duchess",
}


def _parse_card(raw: dict, meta: dict) -> dict:
    card_info = meta.get(raw.get("id"), {})
    rarity = card_info.get("rarity", "Common")
    name = raw.get("name", "")
    max_level = raw.get("maxLevel", 15)
    display_level = min(raw.get("level", 1) + _RARITY_OFFSET.get(rarity, 0), max_level)

    is_champion = name in _CHAMPION_NAMES or rarity == "Champion"
    evo_level = raw.get("evolutionLevel", 0)
    is_hero = evo_level >= 2
    is_evo = evo_level == 1

    icon_urls = raw.get("iconUrls", {})
    icon_url = icon_urls.get("heroMedium") or icon_urls.get("evolutionMedium") or icon_urls.get("medium", "")

    return {
        "name": name,
        "iconUrl": icon_url,
        "level": display_level,
        "is_champion": is_champion,
        "is_hero": is_hero,
        "evolved": is_evo,
    }


async def get_battlelog(tag: str) -> list[dict]:
    url = f"{BASE_URL}/players/{_encode_tag(tag)}/battlelog"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, headers=_headers())
        resp.raise_for_status()
        battles = resp.json()

    meta = await _load_card_meta()
    duels = []
    for battle in battles:
        battle_type = battle.get("type", "")
        if battle_type not in CLAN_WAR_TYPES:
            continue

        player = battle.get("team", [{}])[0]

        if battle_type == "riverRaceDuel":
            for round_data in player.get("rounds", []):
                round_cards = [_parse_card(c, meta) for c in round_data.get("cards", [])]
                duels.append({"type": battle_type, "cards": round_cards[:8]})
        else:
            cards = [_parse_card(c, meta) for c in player.get("cards", [])]
            duels.append({"type": battle_type, "cards": cards[:8]})

    return duels


async def search_clans(clan_name: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{BASE_URL}/clans",
            headers=_headers(),
            params={"name": clan_name, "limit": 10},
        )
        resp.raise_for_status()
        return [
            {"name": c["name"], "tag": c["tag"], "members": c.get("members", 0)}
            for c in resp.json().get("items", [])
        ]


async def get_clan_members(clan_tag: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{BASE_URL}/clans/{_encode_tag(clan_tag)}/members",
            headers=_headers(),
        )
        resp.raise_for_status()
        return [
            {"name": m["name"], "tag": m["tag"]}
            for m in resp.json().get("items", [])
        ]


async def get_player_full(tag: str) -> dict:
    player, battlelog = await asyncio.gather(
        get_player(tag),
        get_battlelog(tag),
    )
    player["duels"] = battlelog
    return player
