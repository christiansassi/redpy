import base64

from typing import Dict

import msgpack

def derive_key(game_id: str) -> int:
    """
    Collapses the game ID string to the single-byte XOR key used by the
    Spot-It bundle. Matches the Ws() function in app-vars-BVMCShud.js:

        [...gameId].reduce((s, c) => s ^ c.charCodeAt(0), 0)

    Args:
        game_id (str): The game ID returned by /game/new.

    Returns:
        int: The XOR key byte in the range 0..255.
    """

    k = 0

    for c in game_id:
        k ^= ord(c)

    return k & 0xff

def encrypt(d: Dict, game_id: str) -> bytes:
    """
    Encodes a gameplay action log the way the bundle's Rc -> Tc -> lc
    chain does: MessagePack-encode the dict, XOR every byte with the
    key derived from the game ID, then base64-encode the result.

    Frame keys are sorted numerically before encoding so the byte layout
    matches what the real client produces (which always emits the keys
    in ascending numeric order).

    Args:
        d (Dict): The gameplay action log, keyed by frame index as
            strings.
        game_id (str): The game ID used to derive the XOR key.

    Returns:
        bytes: The base64-encoded encrypted payload, ready to use as
            the body of a /game/submit/ request.
    """

    sorted_d = {k: d[k] for k in sorted(d.keys(), key=lambda x: int(x))}
    key = derive_key(game_id=game_id)

    packed = msgpack.packb(sorted_d, use_bin_type=True)
    xored = bytes(b ^ key for b in packed)
    return base64.b64encode(xored)

def decrypt(body: bytes, game_id: str) -> Dict:
    """
    Reverses encrypt(): base64-decode, XOR each byte with the
    game-ID-derived key, then MessagePack-decode.

    Args:
        body (bytes): The encrypted /game/submit/ body.
        game_id (str): The game ID used to derive the XOR key.

    Returns:
        Dict: The decoded gameplay action log.
    """

    key = derive_key(game_id=game_id)

    raw = base64.b64decode(body)
    xored = bytes(b ^ key for b in raw)
    return msgpack.unpackb(xored, raw=False, strict_map_key=False)
