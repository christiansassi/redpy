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
        and swaps the encrypted msgpack body. Also short-circuits CORS
        preflight (OPTIONS) requests so the browser never sees a
        missing-header failure from upstream.

        Args:
            flow (http.HTTPFlow): The intercepted HTTP flow.

        Returns:
            None
        """

        global GAMEPLAY

        # Answer CORS preflight directly — echo back what the browser asked for.
        if flow.request.method == "OPTIONS":
            origin = flow.request.headers.get("Origin", "*")
            acrh = flow.request.headers.get("Access-Control-Request-Headers", "*")
            acrm = flow.request.headers.get("Access-Control-Request-Method", "*")
            flow.response = http.Response.make(
                204,
                b"",
                {
                    "Access-Control-Allow-Origin": origin,
                    "Access-Control-Allow-Credentials": "true",
                    "Access-Control-Allow-Headers": acrh,
                    "Access-Control-Allow-Methods": acrm,
                    "Access-Control-Max-Age": "86400",
                    "Vary": "Origin",
                },
            )
            return

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

    @staticmethod
    def _apply_cors(flow: http.HTTPFlow) -> None:
        """
        Stamps CORS headers onto flow.response so the browser will
        accept it. Credentialed requests require the exact Origin to
        be echoed back (not '*').
        """

        if flow.response is None:
            return

        origin = flow.request.headers.get("Origin")
        if not origin:
            return

        h = flow.response.headers
        h["Access-Control-Allow-Origin"] = origin
        h["Access-Control-Allow-Credentials"] = "true"
        h["Access-Control-Expose-Headers"] = "*"
        h["Vary"] = "Origin"

        # Strip headers that can cause the browser to reject the response
        # after we've touched it.
        for k in (
            "Content-Security-Policy",
            "Cross-Origin-Resource-Policy",
            "Cross-Origin-Opener-Policy",
            "Cross-Origin-Embedder-Policy",
        ):
            h.pop(k, None)

    def response(self, flow: http.HTTPFlow) -> None:
        """
        Rewrites response headers on every upstream response that
        passes through the proxy.
        """

        self._apply_cors(flow)

    def error(self, flow: http.HTTPFlow) -> None:
        """
        Fires when mitm cannot reach the upstream (DNS, TLS, connection
        reset, etc.). mitm's auto-generated error page does not go
        through the response hook, so we synthesize a CORS-friendly
        502 here. Without this, browsers report the underlying failure
        as a generic CORS error and the real cause is invisible.
        """

        origin = flow.request.headers.get("Origin", "*")
        reason = str(flow.error) if flow.error else "upstream error"

        flow.response = http.Response.make(
            502,
            f"mitm upstream error: {reason}".encode("utf-8"),
            {
                "Content-Type": "text/plain; charset=utf-8",
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Expose-Headers": "*",
                "Vary": "Origin",
            },
        )

        print(f"[!] Upstream error for {flow.request.pretty_url}: {reason}")

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

    opts = options.Options(
        listen_host="127.0.0.1",
        listen_port=8080,
        # Don't bail on upstream certs we don't like — abs-gateway.redbull.com
        # and other Red Bull endpoints can otherwise trigger a 502 inside mitm.
        ssl_insecure=True,
        # Negotiate HTTP/2 with upstream when offered; abs-gateway requires it.
        http2=True,
    )
    m = dump.DumpMaster(opts, with_termlog=False, with_dumper=False)
    m.addons.add(Injector())

    try:
        await m.run()
    except KeyboardInterrupt:
        await m.shutdown()
