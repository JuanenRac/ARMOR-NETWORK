"""The little of the DNS wire format this program needs: to ask a resolver one question, and to read what a device answers when it announces itself (mDNS).

Copyright (C) 2026 JuanenRac (Electro Hobby 3D). GPL-3.0-or-later.

Python's standard library only asks the system's resolver, and the internet check has to ask a chosen one (to tell a resolver that is down from an internet that is), so the
message is built here. The reader is strict about lengths and about compression pointers (a pointer may only go backwards, and only so many times), because it reads what
any device on the network sends.
"""

from __future__ import annotations

import struct

TYPE_A, TYPE_PTR, TYPE_TXT, TYPE_SRV = 1, 12, 16, 33
CLASS_IN = 1


def encode_name(name: str) -> bytes:
    out = b""
    for label in name.rstrip(".").split("."):
        raw = label.encode("idna") if label else b""
        if not raw or len(raw) > 63:
            raise ValueError("a DNS label is 1 to 63 bytes")
        out += bytes([len(raw)]) + raw
    return out + b"\x00"


def build_query(name: str, qtype: int = TYPE_A, query_id: int = 0x4152, recursion: bool = True) -> bytes:
    """A DNS question for one name (the header, then the question)."""
    flags = 0x0100 if recursion else 0
    return struct.pack(">HHHHHH", query_id, flags, 1, 0, 0, 0) + encode_name(name) + struct.pack(">HH", qtype, CLASS_IN)


def read_name(data: bytes, offset: int) -> tuple[str, int]:
    """The name at `offset` and the offset after it. Compression pointers are followed backwards only, at most ten times."""
    labels: list[str] = []
    end = -1
    jumps = 0
    position = offset
    while True:
        if position >= len(data):
            raise ValueError("a name runs past the end of the message")
        length = data[position]
        if length == 0:
            position += 1
            break
        if length & 0xC0 == 0xC0:
            if position + 1 >= len(data):
                raise ValueError("a pointer runs past the end of the message")
            target = ((length & 0x3F) << 8) | data[position + 1]
            if end < 0:
                end = position + 2
            jumps += 1
            if jumps > 10 or target >= position:
                raise ValueError("a name points forwards or loops")
            position = target
            continue
        if length & 0xC0:
            raise ValueError("an unknown label type")
        if position + 1 + length > len(data):
            raise ValueError("a label runs past the end of the message")
        labels.append(data[position + 1:position + 1 + length].decode("utf-8", "replace"))
        position += 1 + length
        if sum(len(label) + 1 for label in labels) > 255:
            raise ValueError("a name is too long")
    return ".".join(labels), (end if end >= 0 else position)


def parse_message(data: bytes) -> dict:
    """A DNS message: {"id", "flags", "questions": [(name, type)], "answers": [{"name", "type", "ttl", "data"}]}.

    `data` of a record is decoded for A (the address), PTR (the target name), SRV (port and target) and TXT (the strings); another type keeps the raw bytes.
    Answers, authority and additional records are all returned in `answers` (mDNS puts the useful ones in any of them). Raises ValueError on a malformed message.
    """
    if len(data) < 12:
        raise ValueError("shorter than a DNS header")
    ident, flags, qd, an, ns, ar = struct.unpack(">HHHHHH", data[:12])
    if qd > 32 or an + ns + ar > 256:
        raise ValueError("a message with too many records")
    offset = 12
    questions = []
    for _ in range(qd):
        name, offset = read_name(data, offset)
        if offset + 4 > len(data):
            raise ValueError("a question runs past the end of the message")
        qtype, _qclass = struct.unpack(">HH", data[offset:offset + 4])
        offset += 4
        questions.append((name, qtype))
    answers = []
    for _ in range(an + ns + ar):
        name, offset = read_name(data, offset)
        if offset + 10 > len(data):
            raise ValueError("a record runs past the end of the message")
        rtype, _rclass, ttl, rdlength = struct.unpack(">HHIH", data[offset:offset + 10])
        offset += 10
        if offset + rdlength > len(data):
            raise ValueError("a record's data runs past the end of the message")
        raw = data[offset:offset + rdlength]
        if rtype == TYPE_A and rdlength == 4:
            value: object = ".".join(str(b) for b in raw)
        elif rtype == TYPE_PTR:
            value = read_name(data, offset)[0]
        elif rtype == TYPE_SRV and rdlength >= 7:
            port = struct.unpack(">H", raw[4:6])[0]
            value = {"port": port, "target": read_name(data, offset + 6)[0]}
        elif rtype == TYPE_TXT:
            strings, i = [], 0
            while i < len(raw):
                size = raw[i]
                strings.append(raw[i + 1:i + 1 + size].decode("utf-8", "replace"))
                i += 1 + size
            value = strings
        else:
            value = raw
        offset += rdlength
        answers.append({"name": name, "type": rtype, "ttl": ttl, "data": value})
    return {"id": ident, "flags": flags, "questions": questions, "answers": answers}


def rcode(message: dict) -> int:
    return message["flags"] & 0x000F
