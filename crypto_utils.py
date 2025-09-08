import base64
import hashlib
import json
import os
import random
import time
import urllib.parse

from typing import Dict

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

BASE_KEY: str = "932748hfidufdwofuyfiuys8ryf7r8"

def encrypt(d: Dict, t: int = None, base_key: str = BASE_KEY) -> Dict:
    """
    Encrypts a dictionary payload using AES-256-CBC with an OpenSSL-style salt header.

    Args:
        d (Dict): The dictionary to encrypt.
        t (int, optional): Timestamp or numeric seed used for key derivation. If None, a random value is generated.
        base_key (str, optional): Base key string used for deriving AES key and IV.

    Returns:
        Dict: A dictionary containing:
            - "t" (int): The timestamp used for key derivation.
            - "d" (str): The Base64-encoded encrypted payload.
    """

    t = int(1e8 * random.random() + int(time.time() * 1000) / 3) if t is None else t
    passphrase = base_key + str(t // 2)
    salt = os.urandom(8)

    key_iv = b""
    last = b""

    while len(key_iv) < 48:
        last = hashlib.md5(last + passphrase.encode("utf-8") + salt).digest()
        key_iv += last

    key = key_iv[:32]
    iv = key_iv[32:48]

    cipher = AES.new(key, AES.MODE_CBC, iv)
    plaintext = json.dumps(d).encode("utf-8")
    ciphertext = cipher.encrypt(pad(plaintext, AES.block_size))

    encrypted = b"Salted__" + salt + ciphertext
    encoded = base64.b64encode(encrypted).decode("utf-8")

    return {"t": t, "d": encoded}

def decrypt(d: str, t: int, base_key: str = BASE_KEY) -> Dict:
    """
    Decrypts a Base64-encoded AES-256-CBC encrypted payload.

    Args:
        d (str): The Base64-encoded ciphertext string.
        t (int): Timestamp used for key derivation.
        base_key (str, optional): Base key string used for deriving AES key and IV.

    Returns:
        Dict: The decrypted JSON payload as a dictionary.
    """

    passphrase = base_key + str(t // 2)
    data = base64.b64decode(d)

    if data[:8] != b"Salted__":
        raise ValueError("Invalid format, expected OpenSSL Salted__ header")

    salt = data[8:16]
    ciphertext = data[16:]

    key_iv = b""
    last = b""

    while len(key_iv) < 48:
        last = hashlib.md5(last + passphrase.encode("utf-8") + salt).digest()
        key_iv += last

    key = key_iv[:32]
    iv = key_iv[32:48]

    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted = unpad(cipher.decrypt(ciphertext), AES.block_size)
    return json.loads(decrypted.decode("utf-8"))

def encode(body: Dict) -> str:
    """
    Encodes a dictionary as URL-safe, Base64-encoded JSON.

    Args:
        body (Dict): The dictionary to encode.

    Returns:
        str: The encoded string.
    """

    json_str = json.dumps(body, separators=(",", ":"))
    url_encoded = urllib.parse.quote(json_str)
    encoded_bytes = base64.b64encode(url_encoded.encode("utf-8"))
    return encoded_bytes.decode("utf-8")

def decode(body: str) -> Dict:
    """
    Decodes a URL-safe, Base64-encoded JSON string back to a dictionary.

    Args:
        body (str): The encoded body string.

    Returns:
        Dict: The decoded dictionary.
    """

    decoded_bytes = base64.b64decode(s=body)
    url_decoded = urllib.parse.unquote(decoded_bytes.decode("utf-8"))
    return json.loads(url_decoded)
