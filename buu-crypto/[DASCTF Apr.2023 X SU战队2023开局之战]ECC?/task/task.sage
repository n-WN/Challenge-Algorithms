from Crypto.Util.number import *
from secret import flag, p, q, a, b, e1, e2, e3

assert isPrime(p) and isPrime(q)
assert flag.startswith("DASCTF{") and flag.endswith("}")

class ECC():
    def __init__(self, a, b, p, q, e):
        self.p, self.q = p, q
        self.a, self.b = a, b
        self.N         = p * q
        self.e         = e
        self.Kbits     = 8
        self.Ep        = EllipticCurve(IntegerModRing(p), [a, b])
        self.Eq        = EllipticCurve(IntegerModRing(q), [a, b])

        N1 = self.Ep.order()
        N2 = 2 * p + 2 - N1
        N3 = self.Eq.order()
        N4 = 2 * q + 2 - N3

        self.d = {
            ( 1,  1): inverse_mod(e, lcm(N1, N3)),
            ( 1, -1): inverse_mod(e, lcm(N1, N4)),
            (-1,  1): inverse_mod(e, lcm(N2, N3)),
            (-1, -1): inverse_mod(e, lcm(N2, N4))
        }

        self.E = EllipticCurve(IntegerModRing(self.N), [a, b])

    def enc(self, plaintext):
        msg_point = self.msg_to_point(plaintext, True)
        mp = self.Ep(msg_point)
        mq = self.Eq(msg_point)
        cp = (self.e * mp).xy()
        cq = (self.e * mq).xy()
        cp = (int(cp[0]), int(cp[1]))
        cq = (int(cq[0]), int(cq[1]))
        c  = (int(crt([cp[0], cq[0]], [self.p, self.q])), \
              int(crt([cp[1], cq[1]], [self.p, self.q])))
        c = self.E(c)
        return c.xy()

    def dec(self, ciphertext):
        x = ciphertext
        w = x^3 + self.a*x + self.b % self.N

        P.<Yp> = PolynomialRing(Zmod(self.p))
        fp = x^3 + self.a*x + self.b -Yp^2
        yp = fp.roots()[0][0]

        P.<Yq> = PolynomialRing(Zmod(self.q))
        fq = x^3 + self.a*x + self.b -Yq^2
        yq = fq.roots()[0][0]

        y = crt([int(yp), int(yq)], [self.p, self.q])

        cp, cq = self.Ep((x, y)), self.Eq((x, y))
        legendre_symbol_p = legendre_symbol(w, self.p)
        legendre_symbol_q = legendre_symbol(w, self.q)

        mp = (self.d[(legendre_symbol_p, legendre_symbol_q)] * cp).xy()
        mq = (self.d[(legendre_symbol_p, legendre_symbol_q)] * cq).xy()

        return crt([int(mp[0]), int(mq[0])], [self.p, self.q]) >> self.Kbits

    def msg_to_point(self, x, shift=False):
        if shift:
            x <<= self.Kbits
        res_point = None
        for _ in range(2 << self.Kbits):
            P.<Yp> = PolynomialRing(Zmod(self.p))
            fp = x^3 + self.a*x + self.b - Yp^2
            P.<Yq> = PolynomialRing(Zmod(self.q))
            fq = x^3 + self.a*x + self.b - Yq^2
            try:
                yp, yq = int(fp.roots()[0][0]), int(fq.roots()[0][0])
                y = crt([yp, yq], [self.p, self.q])
                E = EllipticCurve(IntegerModRing(self.p*self.q), [self.a, self.b])
                res_point = E.point((x, y))
                return res_point
            except:
                x += 1
        return res_point


ecc1 = ECC(a, b, p, q, e1)
ecc2 = ECC(a, b, p, q, e2)
ecc3 = ECC(a, b ,p, q, e3)
gift = p * q * getPrime(1000)

secret = bytes_to_long(flag[7:-1].encode())
ciphertext1 = ecc1.enc(secret)
ciphertext2 = ecc2.enc(secret)
ciphertext3 = ecc3.enc(secret)

with open("output.txt", "w") as f:
    
    f.write(f"e1 = {e1}\n")
    f.write(f"e2 = {e2}\n")
    f.write(f"e3 = {e3}\n")
    f.write(f"gift = {gift}\n")
    f.write(f"C1 = {ciphertext1}\n")
    f.write(f"C2 = {ciphertext2}\n")
    f.write(f"C3 = {ciphertext3}\n")
