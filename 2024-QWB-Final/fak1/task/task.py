from sage.all import *
from Crypto.Util.number import long_to_bytes
import os
import signal

def _handle_timeout(signum, frame):
    raise TimeoutError('function timeout')

timeout = 60
signal.signal(signal.SIGALRM, _handle_timeout)
signal.alarm(timeout)

load("ntru.sage")
p,n,q,dg,df = 3,117,1091,35,37


cs = []
def Game():
    while True:
        pk,sk = genKeys()
        try:
            1 / pk
            print(pk.list())
            break
        except:
            pass
                
    secret = os.urandom(23)
    secretPoly = MsgtoPoly(secret)
    print("Welcome to fak1. You can send some message to me. Have fun!")
    msgs = [[0 for _ in range(116)]]

    for _ in range(10):
        msg = [round(int(i,16) % 3329) for i in input("Give me a list of message (hex):").split(" ")]
        if len(msg) != 116 or (msg in msgs):
            print("You bad!")
            return
        msgs.append(msg)
        m = secretPoly + QR([round(i / 3329 * q) for i in msg])
        c = encrypt(pk,m)
        try:
            assert m == decrypt(sk,c)
        except:
            print("You bad!!")
            return
        print(c.list())

    if long_to_bytes(int(input("You wanner say something? :"), 16)) == secret:
        print(flag)
        print("You good!")
    else:
        print("OK, bye bye~") 

Game()