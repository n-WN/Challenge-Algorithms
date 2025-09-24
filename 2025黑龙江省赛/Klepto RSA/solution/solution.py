#!/usr/bin/env python3
"""Recover the DASCTF Klepto RSA flag from the provided parameters."""
from decimal import Decimal, getcontext
from hashlib import sha256

from Crypto.Util.number import long_to_bytes, isPrime

Y_STR = "60049738486696908487231121025269793292548565960737278476220709990679165953635153104491094974628316084371654377585462272642687866305392991428376968598549858595796752684661518920220626239975437691414064895642463676733108498345231004527683320732728661177764423285639576892985616687815606169375520520854166583759"
K_STR = "1.06812177272694811108821438927797561876590572464367384334840322606084373799328804487773995960179784838848538993019220719502814807202955112701807418079613602940791848787261960139482608971673561931336173876089308647681376289122381010092727824756392956350935980563710637885021397814775089163341890368162802502836735432396236993201871889127669888514064460137235655"
N = int("3596023580695592789457907802183196756399681015977233295242340936238317018973691599034589854880732384096820035377138261693940394499711123250057901177534616478446934890712142462629287889087402878855602205118569066176847336006999797783812847405621452976590905189308318494920580036460265251370023160444010457343969742500140268145656657584719331223994655918529509324803740906083657280801194613866731974952982345953343515716799498889563560737063361265021629014810595064645026641575740759888841089351365082040998384669205706549841999836035376731041737200044788780457487328828468423385665897008481229300042703829197546732297")
C_FLAG = int("203888967389001610610181601143476417134547238322566249798330454501234719047131239762883296665497911055217805585041450651162745276917488079657459750899771802796714955681333597780415365371810254651462195430523242672381668466268361140273008469445121296185425908790295844531556528841683074107174953571777339913744310027149457799483986132530251645062422885009777650388210633336745992191168809481176500394999589620122461747721066331478829996392011933366508176327335982681077308808332600144583212089054079237839958737870002427686663368647458455780051253327602251757646876642924573210398563421295133998467381134193365066426")
E = 65537
PRECISION = 1200


def recover_primes():
    """Recover P, Q and Y from the leaked Y and ratio k."""
    getcontext().prec = PRECISION
    y_decimal = Decimal(Y_STR)
    k_decimal = Decimal(K_STR)
    q_decimal = (y_decimal / k_decimal).sqrt()
    Q = int(q_decimal.to_integral_value(rounding="ROUND_HALF_UP"))
    Y = int(y_decimal)
    P = Y // Q
    assert P * Q == Y, "Recovered primes do not multiply back to Y"
    return P, Q, Y


def recover_seed(Y, P, Q):
    """Recover the klepto seed s (prior to hashing)."""
    phi_y = (P - 1) * (Q - 1)
    d_y = pow(E, -1, phi_y)
    c_embed = N >> 1024
    s_mod = pow(c_embed, d_y, Y)

    candidates = []
    for k_mul in range(3):
        s_candidate = s_mod + k_mul * Y
        if 1023 <= s_candidate.bit_length() <= 1024:
            candidates.append(s_candidate)
    if not candidates:
        raise ValueError("Failed to find 1024-bit lift for s")
    return candidates


def next_prime(n):
    """Return the next prime greater than n using a wheel/Trial division speed-up."""
    if n < 2:
        return 2
    small_primes = (3, 5, 7, 11, 13, 17, 19, 23, 29)
    candidate = n + 1
    if candidate % 2 == 0:
        candidate += 1
    wheel = (4, 2, 4, 2, 4, 6, 2, 6)
    idx = 0
    while True:
        divisible = False
        for p in small_primes:
            if candidate % p == 0:
                divisible = candidate != p
                break
        if not divisible and isPrime(candidate):
            return candidate
        candidate += wheel[idx]
        idx = (idx + 1) % len(wheel)


def derive_factors(seed_candidates):
    """Try each seed lift until p divides N, return the factors."""
    for s in seed_candidates:
        digest = int(sha256(str(s).encode() * 4).hexdigest(), 16)
        p = next_prime(digest)
        if N % p == 0:
            q = N // p
            return p, q, s
    raise ValueError("Failed to derive factors from any seed candidate")


def decrypt_flag(p, q):
    phi_n = (p - 1) * (q - 1)
    d_n = pow(E, -1, phi_n)
    m = pow(C_FLAG, d_n, N)
    return long_to_bytes(m)


def main():
    P, Q, Y = recover_primes()
    seed_candidates = recover_seed(Y, P, Q)
    p, q, s = derive_factors(seed_candidates)
    flag = decrypt_flag(p, q)

    print(f"Recovered P: {P}")
    print(f"Recovered Q: {Q}")
    print(f"Recovered klepto seed s: {s}")
    print(f"Recovered factors p, q: {p}, {q}")
    print(f"Flag: {flag.decode()}")


if __name__ == "__main__":
    main()
