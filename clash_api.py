import asyncio
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://proxy.royaleapi.dev/v1"
CLAN_WAR_TYPES = {"riverRaceDuel", "riverRacePvP"}


def _headers() -> dict:
    return {"Authorization": f"Bearer {os.getenv('CR_API_KEY', '')}"}


def _encode_tag(tag: str) -> str:
    return tag.replace("#", "%23")


async def get_player(tag: str) -> dict:
    """기본 정보 조회. 닉네임, 트로피, 레벨, 클랜명 반환."""
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


async def get_battlelog(tag: str) -> list[dict]:
    """배틀로그에서 최근 듀얼 3경기 반환. 각 경기의 덱(카드 8장) 포함."""
    url = f"{BASE_URL}/players/{_encode_tag(tag)}/battlelog"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, headers=_headers())
        resp.raise_for_status()
        battles = resp.json()

    duels = []
    for battle in battles:
        battle_type = battle.get("type", "")
        if battle_type not in CLAN_WAR_TYPES:
            continue

        player = battle.get("team", [{}])[0]

        if battle_type == "riverRaceDuel":
            for round_data in player.get("rounds", []):
                round_cards = [
                    {"name": c.get("name", ""), "iconUrl": c.get("iconUrls", {}).get("medium", "")}
                    for c in round_data.get("cards", [])
                ]
                duels.append({"type": battle_type, "cards": round_cards[:8]})
        else:
            cards = [
                {"name": c.get("name", ""), "iconUrl": c.get("iconUrls", {}).get("medium", "")}
                for c in player.get("cards", [])
            ]
            duels.append({"type": battle_type, "cards": cards[:8]})

    return duels


async def get_player_full(tag: str) -> dict:
    """get_player + get_battlelog 병렬 호출."""
    player, battlelog = await asyncio.gather(
        get_player(tag),
        get_battlelog(tag),
    )
    player["duels"] = battlelog
    return player
