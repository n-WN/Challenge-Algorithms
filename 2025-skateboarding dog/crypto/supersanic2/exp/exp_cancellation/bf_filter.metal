#include <metal_stdlib>
using namespace metal;

struct Params {
    ulong startIndex;   // starting linear index in [0..total)
    uint  count;        // number of candidates to test in this dispatch
    uint  base;         // alphabet size
    uint  pinLen;       // 6
    uint  numPrimes;    // e.g., 8
    uint  maxOut;       // capacity of out arrays (entries)
};

kernel void filter_kernel(
    constant Params&               params          [[buffer(0)]],
    constant uchar*                alphabet        [[buffer(1)]],
    constant uint*                 primes          [[buffer(2)]],
    constant uint*                 cmods           [[buffer(3)]],
    device atomic_uint*            outCount        [[buffer(4)]],
    device uint*                   outIndices      [[buffer(5)]],
    device uchar*                  outPins         [[buffer(6)]],
    uint gid [[thread_position_in_grid]])
{
    if (gid >= params.count) { return; }
    ulong idx = params.startIndex + (ulong)gid;

    // Convert linear idx to base-N digits of length pinLen
    const uint L = params.pinLen; // expected 6
    uint digits[8]; // up to 8 if ever needed
    ulong tmp = idx;
    for (int i = (int)L - 1; i >= 0; --i) {
        uint d = (uint)(tmp % params.base);
        tmp /= params.base;
        digits[i] = d;
    }

    // Build candidate bytes
    uchar pinBytes[8];
    for (uint i = 0; i < L; ++i) {
        pinBytes[i] = alphabet[digits[i]];
    }

    // For each prime, compute m = bytes->int mod p; then compute m^(65537) mod p and compare to cmods
    for (uint ip = 0; ip < params.numPrimes; ++ip) {
        uint p = primes[ip];
        ulong acc = 0;
        for (uint i = 0; i < L; ++i) {
            acc = ((acc << 8) + (ulong)pinBytes[i]) % (ulong)p;
        }
        // t = acc^(2^16) mod p using 16 squarings
        ulong t = acc;
        for (uint k = 0; k < 16; ++k) {
            t = (t * t) % (ulong)p;
        }
        ulong r = (t * acc) % (ulong)p; // acc^(2^16+1)
        if ((uint)r != cmods[ip]) {
            return; // fails this filter
        }
    }

    // Passed all filters: record candidate
    uint slot = atomic_fetch_add_explicit(outCount, 1u, memory_order_relaxed);
    if (slot < params.maxOut) {
        outIndices[slot] = (uint)(idx & 0xFFFFFFFFu);
        if (outPins != nullptr) {
            for (uint i = 0; i < L; ++i) {
                outPins[slot * L + i] = pinBytes[i];
            }
        }
    }
}
