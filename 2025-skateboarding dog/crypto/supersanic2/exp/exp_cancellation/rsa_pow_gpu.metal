#include <metal_stdlib>
using namespace metal;

#define LIMBS 16 // 16 * 32 = 512 bits

struct Params {
    ulong startIndex;  // linear start index
    uint  count;       // number of pins in this batch
    uint  base;        // alphabet size (100)
    uint  pinLen;      // 6
};

// Compare a >= b (both 512-bit, little-endian 32-bit limbs)
inline bool big_ge(thread const uint a[LIMBS], thread const uint b[LIMBS]) {
    for (int i = LIMBS - 1; i >= 0; --i) {
        if (a[i] > b[i]) return true;
        if (a[i] < b[i]) return false;
    }
    return true; // equal
}

inline void big_sub(thread uint r[LIMBS], thread const uint a[LIMBS], thread const uint b[LIMBS]) {
    uint borrow = 0;
    for (uint i = 0; i < LIMBS; ++i) {
        uint bi = b[i];
        uint ai = a[i];
        uint tmp = ai - bi - borrow;
        borrow = (ai < bi + borrow) ? 1 : 0;
        r[i] = tmp;
    }
}

// Montgomery multiplication (CIOS), computes r = a*b*R^{-1} mod N, where n0 = -N^{-1} mod 2^32
inline void mont_mul(thread uint r[LIMBS], thread const uint a[LIMBS], thread const uint b[LIMBS], thread const uint N[LIMBS], uint n0) {
    uint T[LIMBS + 1];
    for (uint i = 0; i <= LIMBS; ++i) T[i] = 0;

    for (uint i = 0; i < LIMBS; ++i) {
        // T = T + a * b[i]
        ulong carry = 0;
        for (uint j = 0; j < LIMBS; ++j) {
            ulong uv = (ulong)T[j] + (ulong)a[j] * (ulong)b[i] + carry;
            T[j] = (uint)(uv & 0xFFFFFFFFull);
            carry = uv >> 32;
        }
        ulong tK = (ulong)T[LIMBS] + carry;
        T[LIMBS] = (uint)(tK & 0xFFFFFFFFull);
        ulong carry2 = tK >> 32; // typically zero

        // m = T[0] * n0 mod 2^32
        uint m = (uint)((ulong)T[0] * (ulong)n0);

        // T = T + m * N
        ulong carry3 = 0;
        for (uint j = 0; j < LIMBS; ++j) {
            ulong uv = (ulong)T[j] + (ulong)m * (ulong)N[j] + carry3;
            T[j] = (uint)(uv & 0xFFFFFFFFull);
            carry3 = uv >> 32;
        }
        ulong tK2 = (ulong)T[LIMBS] + carry3 + carry2;
        T[LIMBS] = (uint)(tK2 & 0xFFFFFFFFull);
        // shift right one word (divide by R)
        for (uint j = 0; j < LIMBS; ++j) {
            T[j] = T[j + 1];
        }
        T[LIMBS] = (uint)(tK2 >> 32); // keep high part into next limb slot
    }
    // Conditional subtract N
    if (big_ge(T, N)) {
        big_sub(T, T, N);
    }
    for (uint i = 0; i < LIMBS; ++i) r[i] = T[i];
}

inline void big_set_zero(thread uint x[LIMBS]) { for (uint i=0;i<LIMBS;++i) x[i]=0; }
inline void big_from_u64(thread uint x[LIMBS], ulong v) {
    x[0] = (uint)(v & 0xFFFFFFFFull);
    x[1] = (uint)((v >> 32) & 0xFFFFFFFFull);
    for (uint i=2;i<LIMBS;++i) x[i]=0;
}

inline void big_from_bytes_be(thread uint x[LIMBS], thread const uchar* bytes, uint len) {
    // Build up to 8 bytes into u64, then into limbs
    ulong v = 0;
    for (uint i = 0; i < len; ++i) { v = (v << 8) | (ulong)bytes[i]; }
    big_from_u64(x, v);
}

inline void mont_pow65537(thread uint out[LIMBS], thread const uint m[LIMBS], thread const uint N[LIMBS], thread const uint R2[LIMBS], uint n0) {
    uint one[LIMBS]; big_set_zero(one); one[0] = 1u;
    uint aR[LIMBS]; mont_mul(aR, m, R2, N, n0);      // a*R mod N
    uint res[LIMBS];
    // initialize res = aR
    for (uint i=0;i<LIMBS;++i) res[i] = aR[i];
    // 16 squarings: res = res^(2^16)
    for (uint i = 0; i < 16; ++i) {
        mont_mul(res, res, res, N, n0);
    }
    // multiply by a: res = res * aR
    mont_mul(res, res, aR, N, n0);
    // convert out: res * 1
    mont_mul(out, res, one, N, n0);
}

kernel void rsa_verify_kernel(
    constant Params&           params      [[buffer(0)]],
    constant uchar*            alphabet    [[buffer(1)]],
    constant uint*             N           [[buffer(2)]],
    constant uint*             R2          [[buffer(3)]],
    constant uint*             C           [[buffer(4)]],
    constant uint*             n0ptr       [[buffer(5)]],
    device atomic_uint*        foundFlag   [[buffer(6)]],
    device uchar*              outPin      [[buffer(7)]],
    device ulong*              outIndex    [[buffer(8)]],
    uint gid [[thread_position_in_grid]])
{
    if (gid >= params.count) return;
    if (atomic_load_explicit(foundFlag, memory_order_relaxed) != 0u) return;

    ulong idx = params.startIndex + (ulong)gid;
    // map idx -> pin bytes
    const uint L = params.pinLen; // 6
    uchar pin[8];
    ulong t = idx;
    for (int i = (int)L - 1; i >= 0; --i) {
        uint d = (uint)(t % (ulong)params.base);
        t /= (ulong)params.base;
        pin[i] = alphabet[d];
    }
    // copy constant inputs into thread-local arrays to satisfy address spaces
    uint Nloc[LIMBS]; uint R2loc[LIMBS]; uint Cloc[LIMBS];
    for (uint i=0;i<LIMBS;++i) { Nloc[i]=N[i]; R2loc[i]=R2[i]; Cloc[i]=C[i]; }
    // m from bytes
    uint m[LIMBS]; big_from_bytes_be(m, pin, L);
    // powmod
    uint r[LIMBS];
    uint n0 = n0ptr[0];
    mont_pow65537(r, m, Nloc, R2loc, n0);
    // compare r with C
    bool eq = true;
    for (uint i=0;i<LIMBS;++i) if (r[i] != Cloc[i]) { eq = false; break; }
    if (eq) {
        if (atomic_exchange_explicit(foundFlag, 1u, memory_order_relaxed) == 0u) {
            for (uint i=0;i<L; ++i) outPin[i] = pin[i];
            *outIndex = idx;
        }
    }
}
