import asyncio
from datetime import datetime

from rich.console import Console

from lib.proxy_injector import run

if __name__ == "__main__":

    get_time = lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    Console().clear()

    print(f"[{get_time()}] Ready! https://www.redbull.com/it-it/projects/estatescintillante\n")
    asyncio.run(run())
