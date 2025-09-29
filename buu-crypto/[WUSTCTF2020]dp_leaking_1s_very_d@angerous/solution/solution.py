#!/usr/bin/env python3
"""Recover the RSA plaintext when dp leaks."""
from sympy import gcd
from Crypto.Util.number import long_to_bytes

INPUT = "../task/challenge.txt"


def parse_params(path: str) -> dict[str, int]:
    values: dict[str, int] = {}
    with open(path) as fh:
        for line in fh:
            if '=' not in line:
                continue
            key, value = line.strip().split('=', 1)
            values[key.strip()] = int(value.strip())
    return values


def main() -> None:
    params = parse_params(INPUT)
    e, n, c, dp = params["e"], params["n"], params["c"], params["dp"]

    k = e * dp - 1  # multiple of p - 1
    p = None
    for base in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29):
        candidate = int(gcd(pow(base, k, n) - 1, n))
        if 1 < candidate < n:
            p = candidate
            break
    if p is None:
        raise RuntimeError("Failed to recover p from dp leak")
    q = n // p

    phi = (p - 1) * (q - 1)
    d = pow(e, -1, phi)
    plaintext = long_to_bytes(pow(c, d, n))
    print(plaintext.decode())


if __name__ == "__main__":
    main()
