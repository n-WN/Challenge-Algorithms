#!/usr/bin/env python3
"""Recover the plaintext hidden via differential Manchester coding."""
from typing import List

HEX_STREAM = "2559659965656A9A65656996696965A6695669A9695A699569666A5A6A6569666A59695A69AA696569666AA6"
VALID_TRANSITIONS = {"01", "10"}


def hex_to_bits(hex_stream: str) -> str:
    return "".join(f"{int(ch, 16):04b}" for ch in hex_stream)


def manchester_pairs(bit_stream: str) -> List[str]:
    for offset in range(4):
        tail = bit_stream[offset:]
        pairs = [tail[i : i + 2] for i in range(0, len(tail), 2) if len(tail[i : i + 2]) == 2]
        if set(pairs).issubset(VALID_TRANSITIONS):
            return pairs
    raise ValueError("Failed to align Manchester pairs")


def decode_diff_manchester(hex_stream: str) -> bytes:
    pairs = manchester_pairs(hex_to_bits(hex_stream))
    # Differential Manchester in this task maps low-high (01) to logical 0, high-low (10) to logical 1
    bit_string = "".join("0" if pair == "01" else "1" for pair in pairs)
    remainder = len(bit_string) % 8
    if remainder:
        # The capture is missing one leading reference bit; pad to recover the leftmost byte.
        bit_string = "0" * (8 - remainder) + bit_string
    return bytes(int(bit_string[i : i + 8], 2) for i in range(0, len(bit_string), 8))


def main() -> None:
    plaintext = decode_diff_manchester(HEX_STREAM).decode("ascii")
    print(plaintext)


if __name__ == "__main__":
    main()
