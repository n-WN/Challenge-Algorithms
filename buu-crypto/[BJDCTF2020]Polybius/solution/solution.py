#!/usr/bin/env python3
"""Decode the vowel-based Polybius square substitution from the challenge."""
from string import ascii_uppercase

CIPHER = "ouauuuoooeeaaiaeauieuooeeiea"
# The hint states the plaintext length is 14 (from base64 string "The length of this plaintext: 14").
# Exhaustive search over vowel->digit bijections reveals that the only mapping that yields a readable
# Polybius plaintext is {o:2, u:1, a:3, e:4, i:5}, producing "FLAGISPOLYBIUS".
VOWEL_TO_DIGIT = {
    "o": "2",
    "u": "1",
    "a": "3",
    "e": "4",
    "i": "5",
}
POLYBIUS_SQUARE = "ABCDEFGHIKLMNOPQRSTUVWXYZ"  # Standard I/J merged square


def decode(cipher: str) -> str:
    digits = "".join(VOWEL_TO_DIGIT[ch] for ch in cipher)
    output = []
    for i in range(0, len(digits), 2):
        row = int(digits[i]) - 1
        col = int(digits[i + 1]) - 1
        output.append(POLYBIUS_SQUARE[row * 5 + col])
    return "".join(output)


def main() -> None:
    plaintext = decode(CIPHER)
    flag = f"BJD{{{plaintext}}}"
    print(flag)


if __name__ == "__main__":
    main()
