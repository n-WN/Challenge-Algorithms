from Crypto.Util.number import *
from random import *
from pwn import *

p,n,q,dg,df = 3,117,1091,35,37
R.<x> = PolynomialRing(Zmod(q))
RR.<xx> = PolynomialRing(Zmod(p))
PRq = R.quotient(x ^ n + 1)
PRp = RR.quotient(xx ^ n + 1)

sh = process(["sage", "task.py"])
pk = PRq(eval(sh.recvline().strip().decode()))
sh.recvuntil(b"Welcome to fak1. You can send some message to me. Have fun!")

msgs = [[randint(0, 1) for _ in range(116)] for i in range(10)]
msgs_send = [" ".join([hex(i)[2:].zfill(2) for i in msg]).encode() for msg in msgs]
ms = [PRq([round(i / 3329 * q) for i in msg]) for msg in msgs]

cs = []
for i in range(10):
    sh.recvuntil(b"Give me a list of message (hex):")
    sh.sendline(msgs_send[i])
    cs.append(PRq(eval(sh.recvline().strip().decode())))

r0_ri = []
for i in range(1, 10):
    r0_ri.append((cs[0]-cs[i] - (ms[0]-ms[i]))*pk^(-1))

r0 = ["*" for i in range(117)]
for i in r0_ri:
    temp = i.list()
    for j, t in enumerate(temp):
        if(t == 1):
            r0[j] = 1
        if(t == 1090):
            r0[j] = 0
r0 = PRq(r0)

sh.recvuntil(b"You wanner say something? :")
s = cs[0] - ms[0] - r0*pk
s = s.list()
ss = []

for i in s:
    if(i == 1090):
        ss.append(2)
    else:
        ss.append(i)
secret = 0
for i in range(len(ss)):
    secret += int(3^i*int(ss[i]))

sh.sendline(hex(secret)[2:].encode())
print(sh.recvline())