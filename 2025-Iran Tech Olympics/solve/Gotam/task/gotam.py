#!/usr/bin/env python3

import sys
from Crypto.Util.number import *
from flag import flag

def die(*args):
    pr(*args)
    quit()

def pr(*args):
    s = " ".join(map(str, args))
    sys.stdout.write(s + "\n")
    sys.stdout.flush()

def sc():
    return sys.stdin.buffer.readline()

def check_nr(a, p, q):
    return pow(a, (p - 1) // 2, p) == p - 1 and pow(a, (q - 1) // 2, q) == q - 1

def gotam(nbit):
    p, q = [getPrime(nbit) for _ in ':)']
    n = p * q
    while True:
        t = getRandomRange(1, n - 1)
        if check_nr(t, p, q):
            break
    return (n, t), (p, q)

def encrypt(msg, pubkey):
    n, t = pubkey
    M = bin(bytes_to_long(msg))[2:].zfill(1 << 10)
    l = len(M)
    E = [
        t ** int(M[_]) * getRandomNBitInteger(n.bit_length() - 1) ** 2 % n
        for _ in range(l)
    ]
    return E

def main():
    border = "┃"
    pr(
        "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓"
    )
    pr(
        border,
        "Unlock Gotam's tailored encryption—can you outsmart this custom asymmetric enigma?",
        border,
    )
    pr(
        "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛"
    )
    pubkey, privkey = gotam(128)
    del privkey
    while True:
        pr(
            f"{border} Options: \n{border}\t[E]ncrypt flag \n{border}\t[P]ublic data \n{border}\t[Q]uit"
        )
        ans = sc().decode().strip().lower()
        if ans == "e":
            enc = encrypt(flag, pubkey)
            for e in enc:
                pr(border, f"{hex(e) = }")
        elif ans == "p":
            pr(border, "n, t = ", ", ".join(map(hex, pubkey)))
        elif ans == "q":
            die(border, "Quitting...")
        else:
            die(border, "Bye...")

if __name__ == "__main__":
    main()