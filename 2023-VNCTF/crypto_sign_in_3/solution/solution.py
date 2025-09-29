from sage.all import Integer, PolynomialRing, Zmod, sqrt


def long_to_bytes(n: int) -> bytes:
    if n == 0:
        return b"\x00"
    length = (n.bit_length() + 7) // 8
    return n.to_bytes(length, "big")


# public parameters extracted from the provided Sage script
N = Integer(0x5da08737d91b4845151da8e22d4d591c82dc7247015a314ae41cc8283496102c5121f8c6cd1e6cba7cd1b982be45f9692085330c7f35fd632d638f8de2cd544f278ee4f4a9043db668a15d088284f60d63f9320bc23164f07cb4ada050d26993cf31161ea42bc4ecddf8244d26eff338669ca43bae6b26a6296c4dd6a3771f7ee3aade8a2752d1daecf0d476f1a9c92cf933effb2e811a67d5cae1a370fd7d96088c895ad6496fe0fc9709209301a58b131d9ef97804fb01578309c6c0bcdfbe71430cffaa9f53d272b194e6d3d981f8a4a6ba7b98d0f63745b30b89d3cd549babd7b9a15a1a1b6344b7057a0b499319311182879bec0d6fb8e694a98c990eb9)
x1 = Integer(0x17ad784481184d91239601adbb358489c241fa70b9938fd8adcca5eaaaab44f3c707d6a0595acaf43f35c03e226d965d62e7b53403b5610df9c0d3863768714a3264f1e0b09f8a5dbc37c5fa9dc34ad86875917a0d0805d9520cf0d34fd3851880aed1d0a93240555643b14652f592416de5acfee4c49c93f3f777c6654b82d3a10d50a612db1416600c34408e64d3a53424132fa87aed6f47dcce07dd467f00b1d3f8138fbe2cf404a6764aea2e64dd6c48ab4f8c66b0495cfde2cdfc9d8ed98bfa41ead86bfa10a6d7db2dbbae1d24f10be02ac42a631679097ac665a1436071748b56527e74cabdeded41f85bff18ceeafa2fcb692fa5959af952663b1137)
C = Integer(0x57754258622da2566497ed635f8c25a898c9fc95e8571e113074d6fe874cf75c8e722beb7eba0dc86913cf647447591ec8888b617548f088992d5eb4cb84e90ca7b4eb950fb0d7b8d4c5c64904db968721ae9af263c7ddd47955da7056444f558ec5db233cb1381c9fe1f0dc935d686e689d0f6ec9c98f74b988332a092267c1152801b5ca618e3efc066fce916f6d522c8619b2b9cdc341ecd7124d247890c9af90d1d4c526a6c77a634f9aa39ca941b876ff539a91df5c029a7b08e5f13be1dd72c600bf51e34b91736012f5e9aa68e0e21f770c57c576976186a5dfbe4c374c0b08950720396bfb16c64ae4213ea519b8f27f8747f763abeff001f5010a41)
F = Integer(0x5da08737d91b4845151da8e22d4d591c82dc7247015a314ae41cc8283496102c5121f8c6cd1e6cba7cd1b982be45f9692085330c7f35fd632d638f8de2cd544f278ee4f4a9043db668a15d088284f60d63f9320bc23164f07cb4ada050d26993cf31161ea42bc4ecddf814c1073fd8e50b7f5491bfa9fae2df3233e9f4220f04e6a47876d6e347f18f018310e973e06b782c67949d73d0c4d5a77e2685d6aaa92d5afdc28961e41dcd9242dcaa51a8b9ac2e42ba19320f933ae2aba5aa2642664f0a13d19a939c320417108ffbcc6fc5a50bba55f157cabfdf51ca37a73c2b3e3c65b2e3ad0666e2cacbdfe1d2e8f91e23bf128f714f390bdb992058b06107de)
A1 = Integer(int.from_bytes(b"? uoy lliw .em nodnaba ,meht ekil eb lliw uoy ,os", "big"))
A2 = Integer(int.from_bytes(b"a me no o to yu ri no ka o ri pu ra i do no ta ka sa", "big"))
D = Integer(int.from_bytes(b"mu shi ta me ka na su ko e de ka i ka ba n ki ta na i ku tsu", "big"))

numerator = (C**2 * (A2 * x1**2 + D * x1 + F)**2) % N
denominator = (A1**2 * (C**2 - x1**2)) % N
den_inv = Integer(pow(int(denominator), -1, int(N)))
E_sq = (numerator * den_inv) % N
E = Integer(sqrt(E_sq))

R = PolynomialRing(Zmod(N), "x")
x = R.gen()
inner = (A2 * x**2 + D * x + F)
poly = (A1**2 * E**2 % N) * x**2 + (C**2 % N) * inner**2 - (A1 * C * E % N)**2
poly = poly * poly.leading_coefficient().inverse()
poly = (poly // (x - x1)).monic()
roots = poly.small_roots(X=2**(49 * 8), beta=0.3)
if not roots:
    raise RuntimeError("No small roots found; expected plaintext not recovered")
plaintext_int = Integer(roots[0])
flag = long_to_bytes(int(plaintext_int))
print(flag.decode())
