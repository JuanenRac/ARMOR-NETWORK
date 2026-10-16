"""A secret sealed for this node by the server (ARMOR-SERVER, credential_seal.ts): base64 of nonce (16) + cipher text + HMAC-SHA256 tag (32).
The key comes from this node's own token; the tag is checked before anything is opened, so a changed or foreign message gives None. Standard library only.
Copyright (C) 2026 JuanenRac (Electro Hobby 3D). GPL-3.0-or-later.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import hmac


def _sub_key(token: str, label: str) -> bytes:
    return hmac.new(token.encode(), f"armor-seal:{label}".encode(), hashlib.sha256).digest()


def _stream(key: bytes, nonce: bytes, length: int) -> bytes:
    out = b""
    counter = 0
    while len(out) < length:
        out += hmac.new(key, nonce + counter.to_bytes(4, "big"), hashlib.sha256).digest()
        counter += 1
    return out[:length]


def open_sealed(token: str, sealed: str) -> str | None:
    try:
        raw = base64.b64decode(sealed, validate=True)
    except (binascii.Error, ValueError):
        return None
    if len(raw) < 48:
        return None
    nonce, cipher, tag = raw[:16], raw[16:-32], raw[-32:]
    expected = hmac.new(_sub_key(token, "mac"), nonce + cipher, hashlib.sha256).digest()
    if not hmac.compare_digest(tag, expected):
        return None
    try:
        return bytes(a ^ b for a, b in zip(cipher, _stream(_sub_key(token, "enc"), nonce, len(cipher)))).decode("utf-8")
    except UnicodeDecodeError:
        return None
