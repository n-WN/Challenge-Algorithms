#!/usr/bin/env python3
"""Common modulus attack on the pair of RSA ciphertexts."""
from base64 import b64decode
from Crypto.PublicKey import RSA
from Crypto.Util.number import inverse, long_to_bytes

PUB1_PATH = "../task/pubkey1.pem"
PUB2_PATH = "../task/pubkey2.pem"
C1_PATH = "../task/myflag1"
C2_PATH = "../task/myflag2"


def egcd(a: int, b: int):
    if b == 0:
        return 1, 0, a
    x, y, g = egcd(b, a % b)
    return y, x - (a // b) * y, g


def main() -> None:
    key1 = RSA.import_key(open(PUB1_PATH, "rb").read())
    key2 = RSA.import_key(open(PUB2_PATH, "rb").read())
    assert key1.n == key2.n, "Moduli must match for common modulus attack"
    n = key1.n
    e1, e2 = key1.e, key2.e

    c1 = int.from_bytes(b64decode(open(C1_PATH, "rb").read()), "big")
    c2 = int.from_bytes(b64decode(open(C2_PATH, "rb").read()), "big")

    a, b, g = egcd(e1, e2)
    if g != 1:
        raise ValueError("Public exponents are not coprime")

    if a < 0:
        term1 = pow(inverse(c1, n), -a, n)
    else:
        term1 = pow(c1, a, n)

    if b < 0:
        term2 = pow(inverse(c2, n), -b, n)
    else:
        term2 = pow(c2, b, n)

    m = (term1 * term2) % n
    print(long_to_bytes(m).decode("ascii"))


if __name__ == "__main__":
    main()
