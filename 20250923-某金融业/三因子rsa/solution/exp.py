#!/usr/bin/env python3
import time
import math
import random
import concurrent.futures
from functools import reduce
from itertools import product
import sympy
from sympy.ntheory.modular import crt

# --- 核心修正: 明确定义全局标志位 ---
IS_PWNTOOLS_AVAILABLE = False
try:
    from pwn import log
    IS_PWNTOOLS_AVAILABLE = True
except ImportError:
    class MockLogger:
        def info(self, msg): print(f"[*] {msg}")
        def success(self, msg): print(f"[+] {msg}")
        def warning(self, msg): print(f"[!] {msg}")
        def progress(self, msg):
            class P:
                def __enter__(self): print(f"[*] {msg}...", end='', flush=True); return self
                def __exit__(self, exc_type, exc_val, exc_tb): print()
                def success(self, msg="Done"): print(f" {msg}")
                def status(self, msg): pass
            return P()
    log = MockLogger()

IS_GMPY2_AVAILABLE = False
try:
    import gmpy2
    power, inverse, gcd = gmpy2.powmod, gmpy2.invert, gmpy2.gcd
    IS_GMPY2_AVAILABLE = True
except ImportError:
    power, inverse, gcd = pow, lambda a, n: pow(a, -1, n), math.gcd

# --- 1. 配置信息 ---
CHALLENGE_DATA = {
    "n": 0x81647fb077e9b66b6a86b700f5bed99e5139dfe7484c28a5b7a27767e53266d971a19410554a127ae034440bf2f3b902e649470cdd44524cfcd2634e55d4defd7b83497d4135a05030a548730454edc18efc7a4bbd470f8bd273dbbd8a1382f7,
    "m_test": 0x861011b0af95e654458f84c57d638405319ea154501df412bba722c6768c0ff9,
    "c_test": 0x6ab0554ae8513a7cdfb96ba7fc2fbc5d8ab3f872746cfbf8f06660e78f402b7c3662ef896a1cde1aa9abc2a09a3590d3619941fb8621ea51d27803ff932ec43a5005f244497a4d3b254296d1c4699a4e7e8fc0e1cadd0a192905075d66a8187a,
    "ek": 0xe00000000000,
    "dk": 0x1211655116c24db65ea6553aecdabc06842fc485b8c89aa08e9a974d997b0842ddd142dd6712b40adff9442a4c340567568578ebdd509fb3483532f9d1e4f78d13a9a0e447935ed58bbf262bbc799c40227bcd5a5bc312531a8800000000000,
    "e2": 7,
    "enc": 0x3773fd7f928a0231c0a26e48678984fc36db84f4d63de0cdb36a3101e6e48e140a21b6a6fae834dfaa2670d36444a5f002d28a5d4a9efb6822af43d4d98f4aa9a18139b76527049d2c4419d7ad4ddd9ef65ec7176842aa9ced2f8b14af7bf731,
    "num_workers": 6,
}

# --- 2. 核心算法与辅助函数 ---
def lcm(a, b): return (a * b) // gcd(a, b) if a and b else 0

def giant_step_worker(args):
    """为并行 BSGS 设计的工作函数，在自己的区间内搜索 Giant Steps"""
    try: import gmpy2; power_local = gmpy2.powmod
    except ImportError: power_local = pow
    base, target, modulus, M, start_i, end_i, baby_steps = args
    factor = power_local(base, -M, modulus)
    giant_step_val = (target * power_local(factor, start_i, modulus)) % modulus
    for i in range(start_i, end_i):
        if giant_step_val in baby_steps:
            j = baby_steps[giant_step_val]
            x = i * M + j
            if power_local(base, x, modulus) == target: return x
        giant_step_val = (giant_step_val * factor) % modulus
    return None

def parallel_bsgs_v2(base, target, modulus, bound, num_workers, p_log):
    """最终优化版 BSGS: 串行构建 Baby Steps, 并行搜索 Giant Steps"""
    M = int(math.sqrt(bound)) + 1
    p_log.status(f"Phase 1: Serially building {M:,} baby steps...")
    baby_steps = {}; val = 1
    for j in range(M):
        if val not in baby_steps: baby_steps[val] = j
        val = (val * base) % modulus
    p_log.status(f"Phase 2: Searching {M:,} giant steps across {num_workers} cores...")
    chunk_size = (M + num_workers - 1) // num_workers; tasks = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
        for i in range(num_workers):
            start = i * chunk_size; end = min((i + 1) * chunk_size, M)
            if start >= end: continue
            tasks.append(executor.submit(giant_step_worker, (base, target, modulus, M, start, end, baby_steps)))
        for future in concurrent.futures.as_completed(tasks):
            result = future.result()
            if result is not None:
                executor.shutdown(wait=False, cancel_futures=True); return result
    return None

def factor_from_k(n, k):
    """使用 k = e*d - 1 分解 n"""
    t = k
    while t % 2 == 0: t //= 2
    for _ in range(100):
        a = random.randrange(2, int(n) - 1); x = power(a, t, n)
        if x in (1, n - 1): continue
        y = x
        for _ in range(int(math.log2(k))):
            y = power(x, 2, n);
            if y == 1: return gcd(x - 1, n)
            if y == n - 1: break
            x = y
        else: continue
    raise ValueError("Failed to find a factor.")

def factor_all(n, k):
    """完全分解 n"""
    factors = set(); stack = [n]
    while stack:
        m = stack.pop()
        if m == 1: continue
        if sympy.isprime(m): factors.add(m); continue
        try:
            f = factor_from_k(m, k)
            stack.append(f); stack.append(m // f)
        except ValueError: factors.add(m)
    return sorted(list(factors))

def crt_worker(args):
    """接收一组 CRT 参数，计算并验证候选 Flag"""
    moduli, rems = args
    a_candidate, _ = crt(moduli, rems)
    flag_bytes = a_candidate.to_bytes((a_candidate.bit_length() + 7) // 8, 'big').lstrip(b'\x00')
    try:
        if flag_bytes.decode('utf-8').startswith('flag{'): return flag_bytes.decode('utf-8')
    except UnicodeDecodeError: pass
    return None

# --- 3. 主执行流程 ---
def main():
    cfg = CHALLENGE_DATA
    with log.progress("Step 1: Recovering d_low") as p:
        target_d = (cfg["c_test"] * inverse(power(cfg["m_test"], cfg["dk"], cfg["n"]), cfg["n"])) % cfg["n"]
        d_low = parallel_bsgs_v2(cfg["m_test"], target_d, cfg["n"], 1 << 44, cfg["num_workers"], p)
        d = cfg["dk"] + d_low
        p.success(f"Found d_low: {hex(d_low)}")
    log.info(f"Reconstructed full d: {hex(d)}")

    with log.progress("Step 2: Recovering e_low") as p:
        target_e = (cfg["m_test"] * inverse(power(cfg["c_test"], cfg["ek"], cfg["n"]), cfg["n"])) % cfg["n"]
        e_low = parallel_bsgs_v2(cfg["c_test"], target_e, cfg["n"], 1 << 44, cfg["num_workers"], p)
        e = cfg["ek"] + e_low
        p.success(f"Found e_low: {hex(e_low)}")
    log.info(f"Reconstructed full e: {hex(e)}")

    with log.progress("Step 3: Factoring n") as p:
        k = e * d - 1
        factors = factor_all(cfg["n"], k)
        p_val, q_val, r_val = factors
        p.success(f"Found factors: {[hex(f) for f in factors]}")

    with log.progress("Step 4: Decrypting with CRT") as p:
        p.status("Calculating remainders...")
        primes = [p_val, q_val, r_val]
        remainders = []
        for prime in primes:
            phi = prime - 1
            if gcd(cfg["e2"], phi) == 1:
                d_part = inverse(cfg["e2"], phi); a_part = power(cfg["enc"], d_part, prime)
                remainders.append([a_part])
            else:
                a_parts = sympy.ntheory.nthroot_mod(cfg["enc"], cfg["e2"], prime, all_roots=True)
                remainders.append(a_parts)
        
        p.status("Preparing CRT candidate jobs...")
        tasks = [((primes, rem_combo),) for rem_combo in product(*remainders)]
        final_flag = None
        p.status(f"Verifying {len(tasks)} candidates across {cfg['num_workers']} cores...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=cfg['num_workers']) as executor:
            results = executor.map(crt_worker, *zip(*tasks))
            for result in results:
                if result is not None:
                    final_flag = result
                    break
        p.success("Decryption complete!")

    log.success(f"DECRYPTED FLAG: {final_flag}")

if __name__ == "__main__":
    # 将日志打印移入主保护块，确保只执行一次
    if not IS_PWNTOOLS_AVAILABLE:
        log.warning("pwntools not found. Using basic logger. For better output, run: pip install pwntools")
    
    if IS_GMPY2_AVAILABLE:
        log.info("gmpy2 library found, using for accelerated math.")
    else:
        log.warning("gmpy2 not found, falling back to standard Python math. Performance will be slower.")
    
    main()
