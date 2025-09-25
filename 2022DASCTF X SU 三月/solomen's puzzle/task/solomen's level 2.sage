# type: ignore

G = GF(2 ^ 8, repr = 'int')

from random import randrange
from tqdm import trange


def F(integer):
    assert 0 <= integer < 256
    return G(Integer(integer).digits(2))

alpha = G([1,1,0,0,0,0,0,1])
PR.<x> = PolynomialRing(G)
gx = (x - alpha ^ 0) * (x - alpha ^ 1) * (x - alpha ^ 2) * (x - alpha ^ 3)


def encode_block(message):
    assert isinstance(message, list)

    message = [F(each) for each in message]

    f = PR([G(0)] * 4 + message)
    px = f % gx
    mx = f + px
    c = [_ for _ in mx]
    return [int(str(each)) for each in (c + (8 - len(c)) * [G(0)])]


def encode(byte_stream):

    length = len(byte_stream)
    if length % 4 != 0:
        padding = (length // 4 + 1) * 4 - length
        byte_stream += padding * b'\x00'
        length += padding
    code = b''
    for i in trange(0, length, 4):
        block = byte_stream[i:i+4]
        block_code = encode_block([each for each in block])

        idx1 = randrange(4, 8)
        idx2 = randrange(4, 8)
        value1 = randrange(0, 256)
        value2 = randrange(0, 256)

        block_code = block_code[:idx1] + [value1] + block_code[idx1+1:]
        block_code = block_code[:idx2] + [value2] + block_code[idx2+1:]
        
        code += bytes(block_code)
    
    return code


f = open("flag.jpg", 'rb')
data = f.read()
f.close()

code = encode(data)

f = open("flag.enc", 'wb')
f.write(code)
f.close()

