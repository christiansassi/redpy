import asyncio
import json
from datetime import datetime

from rich.console import Console

from crypto_utils import decode
from game_api import get_zoeid, new
from proxy_injector import run

if __name__ == "__main__":

    get_time = lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    Console().clear()

    print(f"[{get_time()}] Retrieving ZOE ID...")
    zoe_id = get_zoeid()
    print(f"[{get_time()}] Zoe ID: {zoe_id}")

    print(f"[{get_time()}] Looking for a valid game ID (game with DOUBLE power-up)...")
    session = new(zoe_id=zoe_id)
    print(f"[{get_time()}] Game ID: {decode(body=json.loads(session.decode())['body'])['gameid']}")

    print(f"[{get_time()}] Ready! https://www.redbull.com/it-it/projects/red-bull-quiz-stop-motorsport\n")
    asyncio.run(run(s=session))
