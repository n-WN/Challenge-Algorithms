import random
from Crypto.Util.number import bytes_to_long,long_to_bytes

p,n,q,dg,df = 3,117,1091,35,37
R.<x> = PolynomialRing(Zmod(q))
RR.<xx> = PolynomialRing(Zmod(p))
QR = R.quotient(x ^ n + 1)
QRR = RR.quotient(xx ^ n + 1)
flag = b"flag{*******************************************}"

def balancemodlist(List,p):
    for i in range(len(List)):
        if int(List[i]) > p / 2:
            List[i] = int(List[i]) - p
    return List

def randomPoly(d = 0):
    if d == 0:
        poly = QR([random.randint(0,1) for _ in range(n)])
    else:
        L_0 = [0] * (n - 2 * d - 1)
        L_1 = (d + 1) * [1]
        L_2 = d * [-1]
        L = L_0 + L_1 + L_2
        for i in range(randint(5,10)):
            random.shuffle(L)
        poly = QR(L)
    return poly

def genPrivKey():
    while True:
        poly = randomPoly(df)
        try:
            poly_q = (1 / QR(poly))
            poly_p = (1 / QRR(RR(balancemodlist(poly.list(),q))))   
            break
        except:
            pass
    return poly, poly_q, poly_p

def MsgtoPoly(msg):
    msg = Integer(bytes_to_long(msg))
    m = msg.digits(p)
    for i in range(len(m)):
        if m[i] > p / 2:
            m[i] -= p
    return QR(m)

def genKeys():
    f, f_q, f_p = genPrivKey()
    g = randomPoly(dg)
    pk = QR(p * g * f_q)
    sk = (f,f_q,f_p,g)
    return pk,sk

def encrypt(pk, m):
    r = randomPoly()
    return pk * r + m

def decrypt(sk,c):
    f,_,f_p,_ = sk
    m = QR(balancemodlist((QRR(balancemodlist((f * c).list(),q)) * f_p).list(),p))
    return m
