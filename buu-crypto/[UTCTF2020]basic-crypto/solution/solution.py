#!/usr/bin/env python3
"""Decode the multistage cipher from attachment.txt and print the flag."""
from __future__ import annotations

import re
from base64 import b64decode
from pathlib import Path

# Cipher alphabet discovered during manual analysis.
SUBSTITUTION_KEY = {
    "r": "c",
    "g": "o",
    "h": "n",
    "n": "g",
    "x": "r",
    "s": "a",
    "d": "t",
    "f": "u",
    "y": "l",
    "t": "i",
    "u": "s",
    "q": "y",
    "i": "h",
    "a": "v",
    "k": "e",
    "c": "f",
    "e": "d",
    "z": "b",
    "l": "p",
    "v": "w",
    "p": "j",
    "b": "k",
}


def binary_to_ascii(binary_payload: str) -> str:
    return "".join(chr(int(byte, 2)) for byte in binary_payload.split())


def caesar_decrypt(text: str, shift: int) -> str:
    chars = []
    for ch in text:
        if ch.isalpha():
            base = ord("A") if ch.isupper() else ord("a")
            chars.append(chr((ord(ch) - base - shift) % 26 + base))
        else:
            chars.append(ch)
    return "".join(chars)


def substitution_decrypt(text: str) -> str:
    chars = []
    for ch in text:
        lower = ch.lower()
        if lower in SUBSTITUTION_KEY:
            decoded = SUBSTITUTION_KEY[lower]
            if ch.isupper():
                decoded = decoded.upper()
            chars.append(decoded)
        else:
            chars.append(ch)
    return "".join(chars)


def solve(artifact: str = "attachment.txt") -> str:
    binary_payload = Path(artifact).read_text().strip()
    ascii_payload = binary_to_ascii(binary_payload)

    _, b64_blob = ascii_payload.split("\n", 1)
    stage_two = b64decode(b64_blob.replace("\n", "")).decode()

    intro_line, rest = stage_two.split("\n", 1)
    caesar_text, substitution_text = rest.rsplit("\n", 1)

    caesar_plain = caesar_decrypt(caesar_text, shift=10)
    substitution_plain = substitution_decrypt(substitution_text)

    report = "\n\n".join((intro_line, caesar_plain, substitution_plain))
    flag_match = re.search(r"utflag\{[^}]+\}", substitution_plain)
    if not flag_match:
        raise RuntimeError("Flag pattern not found in decoded text")
    flag = flag_match.group(0)
    return f"{report}\n\nFlag: {flag}"


def main() -> None:
    print(solve())


if __name__ == "__main__":
    main()
