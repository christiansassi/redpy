from os.path import join

import json

from mitmproxy import http, options
from mitmproxy.tools import dump

from lib.crypto_utils import encrypt

GAMEPLAY: dict = json.load(open(join("lib", "payload.json"), "r", encoding="utf-8"))

class Injector:
    """
    mitmproxy addon for intercepting and modifying game requests.
    """

    def request(self, flow: http.HTTPFlow) -> None:
        """
        Intercepts outgoing POST requests to the /game/submit/ endpoint
        and swaps the encrypted msgpack body

        Args:
            flow (http.HTTPFlow): The intercepted HTTP flow.

        Returns:
            None
        """

        global GAMEPLAY

        if not flow.request.pretty_url.startswith(
            "https://p-p.redbull.com/rb-global-mter-spot-it-qh-prod/game/submit/"
        ):
            return

        game_id = flow.request.headers.get("X-Game")

        if not game_id:
            return

        new_body = encrypt(d=GAMEPLAY, game_id=game_id)

        flow.request.content = new_body
        flow.request.headers["Content-Length"] = str(len(new_body))

        print(f"[+] Injected game session with ID: {game_id}")

async def run():
    """
    Starts a mitmproxy DumpMaster instance with the Injector addon.

    This function configures mitmproxy to listen on 127.0.0.1:8080, 
    and blocks until the proxy is shut down.

    Args:
        None

    Returns:
        None
    """

    opts = options.Options(listen_host="127.0.0.1", listen_port=8080)
    m = dump.DumpMaster(opts, with_termlog=False, with_dumper=False)
    m.addons.add(Injector())

    try:
        await m.run()
    except KeyboardInterrupt:
        await m.shutdown()
