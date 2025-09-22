#!/usr/bin/python3

import sympy
import sys
import random

# Random bytes
csprng = random.SystemRandom()

# Least Common Multiple
def lcm(a, b):
  return a*b/sympy.gcd(a,b)

def get_random_prime(bits):
  return sympy.randprime(2**(bits-1), 2**bits)

def get_ed(phi, bits):
    while True:
        e = get_random_prime(bits)
        if sympy.gcd(e, phi) == 1:
            d = sympy.mod_inverse(e, phi)
            return (e, d)

p = get_random_prime(256)
q = get_random_prime(256)
r = get_random_prime(256)
n = p*q*r
lamda=lcm(p-1, lcm(q-1,r-1))
(e,d) = get_ed(lamda, 48)

print("Modulus:")
print ("n: ", hex(n))

print("\ntest:")
m=get_random_prime(256)
c=pow(m,d,n)
w=pow(c,e,n)
print ("m: ", hex(m))
print ("c: ", hex(c))
print ("w: ", hex(w))
print(m==w)

ek = (e >> 44) << 44
dk = (d >> 44) << 44
print ("ek: ", hex(ek))
print ("dk: ", hex(dk))
# print (f"[debug] d_low = {d - dk}")

e2 = 0x7
h=csprng.randint(1, 2**160)
flag = 'flag{' + hex(h)[2:] + '}'
a=int.from_bytes(bytes(flag,'utf-8'), byteorder='big', signed=False)
enc=pow(a, e2, n)

print("\nencrypted flag via small e2:")
print ("e2: ", hex(e2))
print ("enc: ", hex(enc))

# EOF
