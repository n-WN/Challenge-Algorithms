#!/usr/bin/env sage -python
# -*- coding: utf-8 -*-

"""
Use Sage + cuso to solve ECDSA with partial nonces from challenge_data.json.

We rely purely on bit-window leaks (lsb/msb/mix) and ECDSA modular relation,
without assuming any structure for "lin" samples. After solving for x, we sign
verify_hex in Ethereum style and write solution/result.json.
"""

import json
import os
from typing import Dict, List

from sage.all import var, ZZ
from Crypto.Hash import keccak

import cuso


N = ZZ(0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141)


def keccak256(b: bytes) -> bytes:
    h = keccak.new(digest_bits=256)
    h.update(b)
    return h.digest()


def recover_salt(aux: Dict) -> int:
    trunc_bits = aux["trunc_bits"]
    mask = (1 << trunc_bits) - 1
    for s in range(256):
        ok = True
        for p in aux["proofs"]:
            msg = bytes.fromhex(p["msg_hex"])  # salt||msg in proofs
            ktr = int(p["keccak_trunc"], 16)
            low = int.from_bytes(keccak256(bytes([s]) + msg), "big") & mask
            if low != ktr:
                ok = False
                break
        if ok:
            return s
    raise ValueError("salt not found")


def build_problem(chal_path: str):
    with open(chal_path, "r") as f:
        data = json.load(f)

    aux = data["aux"]
    salt = recover_salt(aux)

    # Relations and bounds for cuso
    relations = []
    bounds = {}

    # Global unknown: private key x
    x = var("x")
    bounds[x] = (0, int(N))

    # Build per-instance equation using only lsb/msb/mix types
    idx = 0
    used = 0
    for inst in data["instances"]:
        typ = inst["type"]
        if typ not in ("lsb", "msb", "mix"):
            continue
        r = int(inst["r"], 16) % int(N)
        s = int(inst["s"], 16) % int(N)
        msg = bytes.fromhex(inst["msg_hex"])  # z = Keccak256(msg||salt) mod n
        z = int.from_bytes(keccak256(msg + bytes([salt])), "big") % int(N)

        if typ == "lsb":
            wl = inst["meta"]["w_lsb"]
            k_lsb = inst["meta"]["k_lsb"]
            Kmsb = var(f"k_{idx}_msb")
            k = Kmsb * (1 << wl) + k_lsb
            # unknown msb upper bound
            num_unknown_msbs = 256 - wl
            bounds[Kmsb] = (0, 1 << num_unknown_msbs)
        elif typ == "msb":
            wm = inst["meta"]["w_msb"]
            msb_val = inst["meta"]["k_msb"]
            prefix = msb_val << (256 - wm)
            Klsb = var(f"k_{idx}_lsb")
            k = prefix + Klsb
            num_unknown_lsbs = 256 - wm
            bounds[Klsb] = (0, 1 << num_unknown_lsbs)
        else:  # mix
            wl = inst["meta"]["w_lsb"]
            wm = inst["meta"]["w_msb"]
            k_lsb = inst["meta"]["k_lsb"]
            msb_val = inst["meta"]["k_msb"]
            prefix = msb_val << (256 - wm)
            Kmid = var(f"k_{idx}_mid")
            k = prefix + Kmid * (1 << wl) + k_lsb
            num_unknown_middle = 256 - wm - wl
            if num_unknown_middle < 0:
                # overlapping windows: directly fixed; treat as constant
                k = prefix + k_lsb
            else:
                bounds[Kmid] = (0, 1 << num_unknown_middle)

        rel = (s * k) == (z + r * x)
        relations.append(rel)
        idx += 1
        used += 1

    if used == 0:
        raise ValueError("No usable instances (lsb/msb/mix)")

    return relations, bounds


def main():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    chal_path = os.path.join(base, "task", "challenge_data.json")
    relations, bounds = build_problem(chal_path)
    # Solve modulo group order N
    roots = cuso.find_small_roots(relations=relations, bounds=bounds, modulus=int(N))
    if not roots:
        print("[cuso] No roots found.")
        return
    sol = roots[0]
    x = int(sol[var("x")])
    print(f"[cuso] Found x = 0x{x:064x}")

    # sign verify_hex in Ethereum style (low-s) and write result.json
    # Basic secp256k1 ops
    P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
    Gx = 55066263022277343669578718895168534326250603453777594175500187360389116729240
    Gy = 32670510020758816978083085130507043184471273380659243275938904335757337482424

    def inv(a, m=int(N)):
        return pow(a, -1, m)

    def p_add(P1, P2):
        if P1 is None:
            return P2
        if P2 is None:
            return P1
        x1, y1 = P1
        x2, y2 = P2
        if x1 == x2 and (y1 + y2) % P == 0:
            return None
        if x1 == x2 and y1 == y2:
            lam = (3 * x1 * x1) * pow(2 * y1, -1, P) % P
        else:
            lam = (y2 - y1) * pow(x2 - x1, -1, P) % P
        x3 = (lam * lam - x1 - x2) % P
        y3 = (lam * (x1 - x3) - y1) % P
        return (x3, y3)

    def p_mul(k, P0=(Gx, Gy)):
        k %= int(N)
        if k == 0:
            return None
        Q = None
        A = P0
        while k:
            if k & 1:
                Q = p_add(Q, A)
            A = p_add(A, A)
            k >>= 1
        return Q

    def sign_eth(x_int: int, verify_hex: str):
        h = int.from_bytes(keccak256(bytes.fromhex(verify_hex)), 'big') % int(N)
        # simple deterministic k seed
        from hashlib import sha256
        seed = sha256(x_int.to_bytes(32,'big') + h.to_bytes(32,'big')).digest()
        k = int.from_bytes(seed,'big') % int(N)
        if k == 0:
            k = 1
        for _ in range(1000):
            R = p_mul(k)
            if R is None:
                k = (k + 1) % int(N); continue
            r = R[0] % int(N)
            if r == 0:
                k = (k + 1) % int(N); continue
            s = (inv(k) * (h + r * x_int)) % int(N)
            if s == 0:
                k = (k + 1) % int(N); continue
            if s > int(N)//2:
                s = int(N) - s
            v = R[1] & 1
            sig_hex = "0x" + r.to_bytes(32, 'big').hex() + s.to_bytes(32, 'big').hex() + bytes([v]).hex()
            return r, s, v, sig_hex
        raise RuntimeError('failed sign')

    with open(chal_path, 'r') as f:
        chal = json.load(f)
    verify_hex = chal['verify_hex']
    r, s, v, sig_hex = sign_eth(x, verify_hex)

    out = {
        'x_hex': f"0x{x:064x}",
        'signature': {
            'r': f"0x{r:064x}",
            's': f"0x{s:064x}",
            'v': v,
            'sig_hex': sig_hex,
        }
    }
    out_path = os.path.join(base, 'solution', 'result.json')
    with open(out_path, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"[cuso] Wrote result to {out_path}")


if __name__ == "__main__":
    main()
