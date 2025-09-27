#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import time
import math
import threading
import multiprocessing as mp
import argparse
import itertools
import string
import os
from typing import List

try:
    import gmpy2
    from gmpy2 import mpz, powmod
except Exception as exc:
    print("[ERROR] gmpy2 not installed. Install with: pip install gmpy2", file=sys.stderr)
    raise

# Default printable alphabet (Python's string.printable)
DEFAULT_ALPHABET = string.printable  # length == 100

# Preset defaults (used when -n/-c not provided)
PRESET_N = mpz("12797238567939373327290740181067928655036715140086366228695600354441701805042996693724492073962821232105794144227525679428233867878596111656619420618371273")
PRESET_E = mpz(65537)
PRESET_C = mpz("3527077117699128297213675720714263452674443031519633052631407312233044869485683860610136570675841069826332336207623212194708283745914346102673061030089974")


class AtomicCounter:
    def __init__(self):
        self._val = 0
        self._lock = threading.Lock()
    def add(self, n: int) -> None:
        with self._lock:
            self._val += n
    def get(self) -> int:
        with self._lock:
            return self._val


def fast_powmod_65537(base: mpz, n: mpz) -> mpz:
    # Compute base^65537 mod n using 16 squarings + multiply
    t = mpz(base)
    for _ in range(16):
        t = (t * t) % n
    return (t * base) % n


def worker_thread(idx: int, step: int, alphabet_bytes: List[int], pin_len: int,
                  n: mpz, e: mpz, c: mpz, found_evt: threading.Event,
                  result_box: List[str], attempts: AtomicCounter, batch: int = 256):
    L = len(alphabet_bytes)

    # Pre-allocate pin bytes array
    pin = bytearray(pin_len)

    # Helper to test a full pin (pin as bytearray)
    def test_current_pin() -> bool:
        # Build mpz from bytes using CPython C fastpath to reduce GIL contention
        m = mpz(int.from_bytes(pin, 'big', signed=False))
        # Use gmpy2.powmod (fast, C-level)
        ct = powmod(m, e, n)
        if ct == c:
            try:
                result_box[0] = pin.decode('latin-1', errors='ignore')
            except Exception:
                # Fallback: keep raw bytes mapped via latin-1
                result_box[0] = bytes(pin).decode('latin-1', errors='ignore')
            return True
        return False

    local = 0
    # Partition by first character position
    for i0 in range(idx, L, step):
        if found_evt.is_set():
            break
        pin[0] = alphabet_bytes[i0]

        for i1 in range(L):
            pin[1] = alphabet_bytes[i1]
            for i2 in range(L):
                pin[2] = alphabet_bytes[i2]
                for i3 in range(L):
                    pin[3] = alphabet_bytes[i3]
                    for i4 in range(L):
                        pin[4] = alphabet_bytes[i4]
                        for i5 in range(L):
                            if found_evt.is_set():
                                break
                            pin[5] = alphabet_bytes[i5]
                            if test_current_pin():
                                found_evt.set()
                                return
                            local += 1
                            if local == batch:
                                attempts.add(local)
                                local = 0
                    if found_evt.is_set():
                        break
                if found_evt.is_set():
                    break
            if found_evt.is_set():
                break
    if local:
        attempts.add(local)


def progress_thread(total: int, attempts: AtomicCounter, start_ts: float, stop_evt: threading.Event):
    spinner = ['|', '/', '-', '\\']
    s = 0
    while not stop_evt.wait(0.2):
        tried = attempts.get()
        elapsed = time.time() - start_ts
        rate = tried / elapsed if elapsed > 0 else 0.0
        frac = min(1.0, tried / total) if total > 0 else 0.0
        barw = 30
        filled = int(barw * frac)
        bar = '#' * filled + '-' * (barw - filled)
        eta = (total - tried) / rate if rate > 1e-9 else float('inf')
        sys.stderr.write(f"\r[{bar}] {frac*100:5.1f}% {spinner[s%4]} tried={tried}/{total} rate={rate:,.0f}/s eta={'∞' if math.isinf(eta) else f'{eta:,.1f}s'}")
        sys.stderr.flush()
        s += 1
    # clear line
    sys.stderr.write("\r" + " " * 100 + "\r")
    sys.stderr.flush()


def proc_worker(proc_idx: int, proc_cnt: int, alphabet_str: str, pin_len: int,
                n_str: str, e_str: str, c_str: str,
                found: 'mp.Event', out_q: 'mp.Queue', attempts_shm: 'mp.Value'):
    # Re-import inside process
    import gmpy2
    from gmpy2 import mpz, powmod
    n_loc = mpz(n_str)
    e_loc = mpz(e_str)
    c_loc = mpz(c_str)
    # Use bytes for faster indexing
    ab = alphabet_str.encode('latin-1', 'ignore')
    Lloc = len(ab)
    pin = bytearray(pin_len)
    batch = 256
    local = 0

    def test_pin() -> bool:
        m = mpz(int.from_bytes(pin, 'big', signed=False))
        return powmod(m, e_loc, n_loc) == c_loc

    for i0 in range(proc_idx, Lloc, proc_cnt):
        if found.is_set():
            break
        pin[0] = ab[i0]
        for i1 in range(Lloc):
            pin[1] = ab[i1]
            for i2 in range(Lloc):
                pin[2] = ab[i2]
                for i3 in range(Lloc):
                    pin[3] = ab[i3]
                    for i4 in range(Lloc):
                        pin[4] = ab[i4]
                        for i5 in range(Lloc):
                            if found.is_set():
                                break
                            pin[5] = ab[i5]
                            if test_pin():
                                try:
                                    out_q.put_nowait(bytes(pin).decode('latin-1', 'ignore'))
                                except Exception:
                                    out_q.put_nowait(bytes(pin).decode('latin-1', 'ignore'))
                                found.set()
                                return
                            local += 1
                            if local == batch:
                                with attempts_shm.get_lock():
                                    attempts_shm.value += local
                                local = 0
                    if found.is_set():
                        break
                if found.is_set():
                    break
            if found.is_set():
                break
    if local:
        with attempts_shm.get_lock():
            attempts_shm.value += local


def main():
    ap = argparse.ArgumentParser(description="PIN brute-force using gmpy2.powmod with multithreading")
    ap.add_argument('-n', type=str, default='', help='modulus n (decimal)')
    ap.add_argument('-e', type=str, default='65537', help='public exponent e (decimal)')
    ap.add_argument('-c', type=str, default='', help='ciphertext c (decimal)')
    ap.add_argument('-len', dest='pin_len', type=int, default=6, help='PIN length (default: 6)')
    ap.add_argument('-threads', dest='threads', type=int, default=6, help='thread count (default: 6)')
    ap.add_argument('-alphabet', dest='alphabet', type=str, default=DEFAULT_ALPHABET, help='alphabet to search')
    ap.add_argument('-timeout', dest='timeout', type=int, default=0, help='timeout seconds (0=no timeout)')
    args = ap.parse_args()

    # Apply defaults if missing n/c
    if not args.n or not args.c:
        n = PRESET_N
        e = PRESET_E
        c = PRESET_C
        args.pin_len = 6
        args.threads = 6
        args.timeout = 0
        alphabet = DEFAULT_ALPHABET
        sys.stderr.write("[INFO] Using preset n/e/c and defaults: -len 6 -threads 6 -timeout 0\n")
    else:
        n = mpz(args.n)
        e = mpz(args.e)
        c = mpz(args.c)
        alphabet = args.alphabet

    pin_len = args.pin_len
    threads = max(1, int(args.threads))

    # Prepare alphabet as bytes list
    alphabet_bytes = [ord(ch) for ch in alphabet]
    base = len(alphabet_bytes)
    total = base ** pin_len

    sys.stderr.write(f"[INFO] alphabet={base}, len={pin_len}, total={total}\n")
    sys.stderr.write(f"[INFO] threads={threads}\n")

    # Switch to multi-processing to fully utilize multiple cores
    ctx = mp.get_context("spawn")
    attempts_val = ctx.Value('Q', 0)  # unsigned long long
    found_evt = ctx.Event()
    result_q = ctx.Queue(1)

    # progress (reads attempts_val via small wrapper)
    class ProcAttempts:
        def __init__(self, val): self.val = val
        def add(self, n):
            with self.val.get_lock():
                self.val.value += n
        def get(self):
            return self.val.value

    attempts_proxy = ProcAttempts(attempts_val)
    stop_progress_evt = threading.Event()
    start_ts = time.time()
    prog = threading.Thread(target=progress_thread, args=(total, attempts_proxy, start_ts, stop_progress_evt), daemon=True)
    prog.start()

    # spawn processes
    procs: list[mp.Process] = []
    for i in range(threads):
        p = ctx.Process(target=proc_worker, args=(i, threads, alphabet, pin_len, str(n), str(e), str(c), found_evt, result_q, attempts_val))
        p.daemon = True
        p.start()
        procs.append(p)

    # Optional timeout
    deadline = time.time() + args.timeout if args.timeout and args.timeout > 0 else None

    result_pin = None
    try:
        while True:
            if not result_q.empty():
                result_pin = result_q.get_nowait()
                found_evt.set()
                break
            if found_evt.is_set():
                break
            if deadline is not None and time.time() >= deadline:
                break
            if all(not p.is_alive() for p in procs):
                break
            time.sleep(0.05)
    finally:
        stop_progress_evt.set()
        prog.join(timeout=1)

    for p in procs:
        try:
            p.terminate()
        except Exception:
            pass
        p.join(timeout=0.1)

    if result_pin:
        print(result_pin)
        sys.exit(0)
    else:
        if deadline is not None and time.time() >= deadline:
            sys.stderr.write("\n[FAILURE] Timeout\n")
        else:
            sys.stderr.write("\n[FAILURE] Not found\n")
        sys.exit(1)


if __name__ == '__main__':
    main()
