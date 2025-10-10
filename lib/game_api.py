from typing import Optional

import requests
from fake_useragent import UserAgent

from crypto_utils import decode, encrypt

def get_zoeid() -> Optional[str]:
    """
    Retrieves the Zoe ID from the Red Bull API.

    Returns:
        Optional[str]: The Zoe ID if found, otherwise None.
    """

    url = (
        "https://www.redbull.com/v3/api/graphql/v1/v3/query/"
        "?filter[type]=project-profiles"
        "&filter[uriSlug]=red-bull-quiz-stop-motorsport"
        "&rb3Schema=v1:mainSubPage&rb3Locale=us-en"
    )

    response = requests.get(url=url, headers={"User-Agent": UserAgent().random})

    for item in response.json().get("data", {}).get("items", []):
        zoe_id = item.get("scriptConfig", {}).get("zoeId")
        if zoe_id:
            return zoe_id

    return None

def new(zoe_id: str) -> bytes:
    """
    Requests a new game session from the Red Bull API, looping until a
    "double" power-up game is found.

    Args:
        zoe_id (str): Zoe ID retrieved from `get_zoeid()`.

    Returns:
        bytes: The raw HTTP response content of the game session.
    """

    payload = encrypt(d={"localization": zoe_id})
    url = "https://p-p.redbull.com/rb-global-muiz-stop-20-72-prod/api/game/new/"

    while True:
        response = requests.post(
            url=url, headers={"User-Agent": UserAgent().random}, data=payload
        )

        game = decode(body=response.json()["body"])

        if game.get("powerUp") == "double":
            break

    return response.content
