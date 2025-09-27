#include <metal_stdlib>
using namespace metal;

struct Params {
    ulong startIndex;  // linear start index
    uint  count;       // number of pins to generate in this batch
    uint  base;        // alphabet size
    uint  pinLen;      // typically 6
};

kernel void enum_kernel(
    constant Params& params     [[buffer(0)]],
    constant uchar*  alphabet   [[buffer(1)]],
    device  uchar*   outPins    [[buffer(2)]],
    uint tid [[thread_position_in_grid]])
{
    if (tid >= params.count) return;
    ulong idx = params.startIndex + (ulong)tid;

    // Decompose idx into base-N digits (big-endian order into pin bytes)
    uint L = params.pinLen;
    uint b = params.base;
    // We compute digits from last to first
    uchar pinBytes[16];
    ulong t = idx;
    for (int i = (int)L - 1; i >= 0; --i) {
        uint d = (uint)(t % (ulong)b);
        t /= (ulong)b;
        pinBytes[i] = alphabet[d];
    }
    // Write to out buffer
    device uchar* dst = outPins + (ulong)tid * (ulong)L;
    for (uint i = 0; i < L; ++i) {
        dst[i] = pinBytes[i];
    }
}
