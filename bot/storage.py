import json
import os

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "my_decks.json")


def save_my_decks(player_tag: str, decks: list) -> None:
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    data = {"player_tag": player_tag, "decks": decks}
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_my_decks() -> dict:
    if not os.path.exists(DATA_PATH):
        return {}
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)
