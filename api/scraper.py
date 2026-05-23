import logging

from curl_cffi.requests import AsyncSession
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

SEARCH_URL = "https://royaleapi.com/player/search/results"


async def search_player(name: str, clan_name: str = "") -> list[dict]:
    """닉네임으로 플레이어 검색. clan_name 지정 시 클랜명으로 필터링. 최대 5명 반환."""
    params = {"q": name}
    try:
        async with AsyncSession(impersonate="chrome124") as session:
            resp = await session.get(SEARCH_URL, params=params, timeout=10)
            resp.raise_for_status()
    except Exception as e:
        logger.error("scraper 요청 실패: %s", e)
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    items = soup.select(".player_search_results__result_container")
    logger.debug("scraper HTML 파싱: %d개 항목 발견 (HTTP %s)", len(items), resp.status_code)

    players = []

    for item in items:
        name_el = item.select_one(".header")
        tag_el = item.select_one(".player_tag")

        if not name_el or not tag_el:
            continue

        clan_el = item.select_one(".meta")
        clan = clan_el.get_text(strip=True) if clan_el else ""

        if clan_name and clan_name.lower() not in clan.lower():
            continue

        players.append({
            "name": name_el.get_text(strip=True),
            "tag": tag_el.get_text(strip=True),
            "clan": clan,
        })

        if len(players) >= 5:
            break

    return players
