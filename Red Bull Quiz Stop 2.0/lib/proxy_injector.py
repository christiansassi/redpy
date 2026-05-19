import json

from mitmproxy import http, options
from mitmproxy.tools import dump

from crypto_utils import decrypt, encrypt, decode

SESSION = None
STARTED = False
POWERUP = False

class Injector:
    """
    mitmproxy addon for intercepting and modifying game requests/responses.
    """

    def request(self, flow: http.HTTPFlow) -> None:
        """
        Intercepts outgoing POST requests to the game actions endpoint and
        modifies their payload before sending.

        Args:
            flow (http.HTTPFlow): The intercepted HTTP flow.

        Returns:
            None
        """

        global SESSION, POWERUP

        if SESSION is None:
            return

        if flow.request.pretty_url.startswith(
            "https://p-p.redbull.com/rb-global-muiz-stop-20-72-prod/api/game/actions/"
        ):
            
            payload = json.loads(flow.request.content.decode())
            t = payload["t"]
            d = decrypt(d=payload["d"], t=t)

            if any(action["type"] == "move" for action in d.get("actions", [])):
                d["actions"] = [
                    {"type": "move", "value": {"index": 0, "row": 0}, "frame": 1},
                    {"type": "submit", "value": [0, 1, 2, 3, 4, 5], "frame": 60},
                ]
        
            else:
                d["actions"] = [
                    {"type": "select", "value": 0, "frame": 12},
                    {"type": "submit", "value": True, "frame": 15},
                ]

                if not POWERUP:
                    d["actions"].insert(0, {"type": "powerup", "frame": 11})
                    POWERUP = True

            new_body = json.dumps({"t": t, "d": encrypt(d=d, t=t)["d"]})
            new_body_encoded = new_body.encode()

            flow.request.content = new_body_encoded
            flow.request.headers["Content-Length"] = str(len(new_body_encoded))

            print(f"[+] Injected answer: {new_body}")

        elif flow.request.pretty_url.startswith(
            "https://p-p.redbull.com/rb-global-muiz-stop-20-72-prod/api/game/score/"
        ):
            SESSION = None

    def response(self, flow: http.HTTPFlow) -> None:
        """
        Intercepts responses for the game session creation endpoint and
        replaces the session payload.

        Args:
            flow (http.HTTPFlow): The intercepted HTTP flow.

        Returns:
            None
        """

        global SESSION, STARTED, POWERUP

        if SESSION is None:
            return

        if flow.request.pretty_url.startswith(
            "https://p-p.redbull.com/rb-global-muiz-stop-20-72-prod/api/game/new/"
        ):
            
            if STARTED:
                SESSION = None
                return
        
            print(f"[+] Injected game session with ID: {decode(body=json.loads(SESSION.decode())["body"])["gameid"]}")

            flow.response.content = SESSION
            flow.response.headers["Content-Length"] = str(len(SESSION))

            STARTED = True

async def run(s: bytes):
    """
    Starts a mitmproxy DumpMaster instance with the Injector addon, using the provided game session data.

    This function sets the global session state, configures mitmproxy
    to listen on 127.0.0.1:8080, and blocks until the proxy is shut down.

    Args:
        s (bytes): The raw game session data to inject into the first intercepted "new game" response.

    Returns:
        None
    """

    global SESSION

    SESSION = s

    opts = options.Options(listen_host="127.0.0.1", listen_port=8080)
    m = dump.DumpMaster(opts, with_termlog=False, with_dumper=False)
    m.addons.add(Injector())

    try:
        await m.run()
    except KeyboardInterrupt:
        await m.shutdown()
