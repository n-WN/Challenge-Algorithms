#!/usr/bin/env python3
"""Recover the plaintext from the RSA-16M challenge by taking an integer 17th root."""
from gmpy2 import iroot

INPUT_PATH = "../task/tmp/rsa_16m"


def parse_params(path: str):
    values = {}
    with open(path) as fh:
        for line in fh:
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            values[key] = int(value, 16) if value.startswith("0x") else int(value)
    return values


def main() -> None:
    params = parse_params(INPUT_PATH)
    c = params["c"]
    e = params["e"]
    m, exact = iroot(c, e)
    if not exact:
        raise ValueError("Ciphertext is not a perfect e-th power; assumptions broken")
    plaintext = m.to_bytes((m.bit_length() + 7) // 8, "big").decode("ascii")
    print(plaintext)


if __name__ == "__main__":
    main()
