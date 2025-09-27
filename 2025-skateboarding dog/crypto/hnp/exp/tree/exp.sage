from Crypto.Util.number import getPrime, long_to_bytes, isPrime
from Crypto.Cipher import AES
from itertools import product
from tqdm import trange
import multiprocessing as mp

cl = [
150446291068140049563320772229191257428,
30274497893933825999264440472646873791,
43867575705590228789129962680194301102,
215435877342780673372868219690346172147,
99919967040475127359053542571984408741,
1418241424975041702003923185520387792,
185934806776900279451263515202940787830,
9915399472284561223892051362047539015,
128538985168972255782337580802434396984,
66625731371269352564215497563133736582,
208818196421195854278004492989600277886,
99906814947789931207521912729518463975,
71965491875756016264158124104626078247,
17142191919773459556570465854141914661,
79550053952325692474643350015142936377,
133451730769263639095159572044716238586]


M = column_matrix(cl)
K = M.left_kernel_matrix().LLL()
K = K[:12, :]
E_ = K.right_kernel_matrix().T

cnt = 0
E_candidates = []
for a1 in range(-10, 11):
    for a2 in range(-10, 11):
        for a3 in range(-10, 11):
            for a4 in range(-10, 11):
                v = E_ * vector([a1, a2, a3, a4])
                if all(0 <= i <= 255 for i in v):
                    E_candidates.append(v)
                    cnt += 1
print(cnt)
print(cnt * (cnt - 1) * (cnt - 2) // 6)
AllComb = list(Combinations(range(cnt), 3))
cl_vec = vector(cl)

def worker(begin, end):
    for idx in range(begin,end):
        if idx >= len(AllComb):
            return
        if idx % 20000 == 0:
            print(((idx - begin) / (end - begin)).n())
        comb = AllComb[idx]
        e1, e2, e3 = E_candidates[comb[0]], E_candidates[comb[1]], E_candidates[comb[2]]
        L = (getPrime(64) * column_matrix([e1, e2, e3])).augment(identity_matrix(ZZ, 16))
        L = L.LLL()
        K = []
        for v in L:
            if v[0] == v[1] == v[2] == 0:
                K.append(v[3:])  
        p = abs(gcd(matrix(K)* cl_vec))
        if p.bit_length() == 128:
            if isPrime(p):
                # try:
                #     p1, p2, p3 = column_matrix(GF(p), [e1, e2, e3]).solve_right(cl_vec).change_ring(ZZ)
                # except Exception as e:
                #     continue
                p1, p2, p3 = column_matrix(GF(p), [e1, e2, e3]).solve_right(cl_vec).change_ring(ZZ)
                
                if p1.bit_length() < 128:
                    p1 = (p1 + p)
                if p2.bit_length() < 128:
                    p2 = (p2 + p)
                if p3.bit_length() < 128:
                    p3 = (p3 + p)
                if isPrime(p1) and isPrime(p2) and isPrime(p3):
                    print(p1, p2, p3, p)
                    print(e1, e2, e3)
                    key = long_to_bytes(p1 ^^ p2 ^^ p3 ^^ p)
                    aes = AES.new(key, AES.MODE_ECB)
                    all_e = [[e1, e2, e3], [e1, e3, e2], [e2, e1, e3], [e2, e3, e1], [e3, e1, e2], [e3, e2, e1]]
                    for e1, e2, e3 in all_e:
                        cipher = e1 + e2 + e3
                        print(aes.decrypt(bytes(cipher)))

total = len(AllComb)
NUM_PROCESS = 10
gap = total // NUM_PROCESS

ps = []
for x in range(NUM_PROCESS):
    p = mp.Process(target=worker, args=(gap * x, gap * (x + 1)))
    p.start()
    ps.append(p)
    
for p in ps:
    p.join()