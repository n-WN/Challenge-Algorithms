#!/usr/bin/env python3
"""Solve MRCTF2020 Easy_RSA by reconstructing the custom primes and decrypting the ciphertext."""
from __future__ import annotations
from pathlib import Path
from math import isqrt
from sympy import nextprime
from Crypto.Util.number import long_to_bytes

DUMP_PATH = Path("../task/easy_RSA.py")


def parse_block() -> dict[str, int]:
    text = DUMP_PATH.read_text()
    block = text.split("'''", 2)[1]
    values: dict[str, int] = {}
    for line in block.strip().splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        values[key] = int(value)
    return values


def recover_primes_from_n_phi(n: int, phi: int) -> tuple[int, int]:
    s = n - phi + 1  # s = p + q
    disc = s * s - 4 * n
    root = isqrt(disc)
    if root * root != disc:
        raise ValueError("Discriminant is not a perfect square")
    p = (s - root) // 2
    q = (s + root) // 2
    if p * q != n:
        raise ValueError("Failed to factor modulus")
    return (p, q) if p < q else (q, p)


def recover_q_primes(n: int, ed: int) -> tuple[int, int]:
    s = ed - 1  # s = e*d - 1 = k * phi
    k0 = s // n
    for delta in range(1 << 20):
        for candidate in (k0 + delta, k0 - delta):
            if candidate <= 0:
                continue
            if s % candidate:
                continue
            phi = s // candidate
            if phi >= n:
                continue
            try:
                return recover_primes_from_n_phi(n, phi)
            except ValueError:
                continue
    raise RuntimeError("Failed to recover primes for Q")


def main() -> None:
    data = parse_block()

    # First generator: we know n and phi directly.
    p1, q1 = recover_primes_from_n_phi(data["P_n"], data["P_F_n"])
    big_p = nextprime(2021 * p1 + 2020 * q1)

    # Second generator: only n and e*d are known.
    p2, q2 = recover_q_primes(data["Q_n"], data["Q_E_D"])
    big_q = nextprime(abs(2021 * p2 - 2020 * q2))

    # Final RSA parameters.
    modulus = big_p * big_q
    phi = (big_p - 1) * (big_q - 1)
    e = 65537
    d = pow(e, -1, phi)

    plaintext = long_to_bytes(pow(data["Ciphertext"], d, modulus))
    print(plaintext.decode())


if __name__ == "__main__":
    main()
