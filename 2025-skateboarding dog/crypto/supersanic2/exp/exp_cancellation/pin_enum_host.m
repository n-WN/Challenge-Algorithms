#import <Metal/Metal.h>
#import <Foundation/Foundation.h>
#include <gmp.h>

// Build: clang -fobjc-arc -framework Metal -framework Foundation -O3 pin_enum_host.m -o pin_enum
// Note: This host expects a precompiled Metallib or uses source JIT from rsa_pow_gpu.metal

static NSString* readFile(NSString* path) {
    NSError* err = nil;
    NSString* src = [NSString stringWithContentsOfFile:path encoding:NSUTF8StringEncoding error:&err];
    if (!src) { NSLog(@"read %@ failed: %@", path, err); return nil; }
    return src;
}

typedef struct { uint64_t startIndex; uint32_t count, base, pinLen; } Params;

int main(int argc, const char* argv[]) {
    @autoreleasepool {
        if (argc < 8) {
            fprintf(stderr, "Usage: %s <start> <total> <batch> <alphabet:file|inline> <n_hex_le32x16> <R2_hex_le32x16> <c_hex_le32x16> <n0_hex32>\n", argv[0]);
            fprintf(stderr, "Example alphabet: 0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!\"#$%%&'()*+,-./:;<=>?@[\\]^_`{|}~ \t\n\r\x0b\x0c\n");
            return 2;
        }
        uint64_t start = strtoull(argv[1], NULL, 10);
        uint64_t total = strtoull(argv[2], NULL, 10);
        uint32_t batch = (uint32_t)strtoul(argv[3], NULL, 10);
        // If argv[4] looks like a readable file, load it; else treat as inline string
        const char* alphabet = NULL;
        NSData* alphabetData = nil;
        NSString* aPath = [NSString stringWithUTF8String:argv[4]];
        if ([[NSFileManager defaultManager] isReadableFileAtPath:aPath]) {
            alphabetData = [NSData dataWithContentsOfFile:aPath];
            alphabet = (const char*)alphabetData.bytes;
            if (!alphabet) { fprintf(stderr, "alphabet file load failed\n"); return 2; }
        } else {
            alphabet = argv[4];
        }
        const char* nArg = argv[5];
        const char* eArg = argv[6];
        const char* cArg = argv[7];
        const char* n0HexOpt = (argc >= 9 ? argv[8] : NULL);

        id<MTLDevice> dev = MTLCreateSystemDefaultDevice();
        if (!dev) { NSArray<id<MTLDevice>> *ds = MTLCopyAllDevices(); if (ds.count) dev = ds.firstObject; }
        if (!dev) { NSLog(@"No Metal device"); return 1; }
        NSLog(@"Using Metal device: %@", dev.name);

        NSString* src = readFile(@"rsa_pow_gpu.metal");
        NSError* err = nil;
        id<MTLLibrary> lib = [dev newLibraryWithSource:src options:nil error:&err];
        if (!lib) { NSLog(@"lib error: %@", err); return 3; }
        id<MTLFunction> fn = [lib newFunctionWithName:@"rsa_verify_kernel"];
        id<MTLComputePipelineState> pso = [dev newComputePipelineStateWithFunction:fn error:&err];
        if (!pso) { NSLog(@"pso error: %@", err); return 3; }
        id<MTLCommandQueue> q = [dev newCommandQueue];

        uint32_t base = (uint32_t)strlen(alphabet);
        uint32_t pinLen = 6;

        // Decide mode: strict hex mode only if n/r2/c are exactly 128 hex chars and n0 is provided (8 hex)
        bool hexMode = false; {
            size_t Ln = strlen(nArg);
            size_t Le = strlen(eArg);
            size_t Lc = strlen(cArg);
            size_t Ln0 = n0HexOpt ? strlen(n0HexOpt) : 0;
            int ok = 1;
            if (!(Ln==128 && Le==128 && Lc==128 && Ln0==8)) ok = 0;
            int int_is_hex(const char* s, size_t L) {
                for (size_t i=0;i<L;i++) {
                    char ch = s[i];
                    if (!((ch>='0'&&ch<='9')||(ch>='a'&&ch<='f')||(ch>='A'&&ch<='F'))) return 0;
                }
                return 1;
            }
            if (ok) ok = int_is_hex(nArg,Ln) && int_is_hex(eArg,Le) && int_is_hex(cArg,Lc) && int_is_hex(n0HexOpt,Ln0);
            hexMode = ok ? true : false;
        }

        uint32_t nBuf[16], r2Buf[16], cBuf[16]; memset(nBuf,0,sizeof(nBuf)); memset(r2Buf,0,sizeof(r2Buf)); memset(cBuf,0,sizeof(cBuf));
        uint32_t n0 = 0;
        if (hexMode) {
            const char* nHex = nArg; const char* r2Hex = eArg; const char* cHex = cArg; const char* n0Hex = n0HexOpt;
            if (strlen(nHex) < 128 || strlen(r2Hex) < 128 || strlen(cHex) < 128) { fprintf(stderr, "bad hex input length\n"); return 2; }
            for (int i = 0; i < 16; ++i) { char tmp[9]={0}; memcpy(tmp, nHex + i*8, 8);  nBuf[i]  = (uint32_t)strtoul(tmp, NULL, 16); }
            for (int i = 0; i < 16; ++i) { char tmp[9]={0}; memcpy(tmp, r2Hex+ i*8, 8);  r2Buf[i] = (uint32_t)strtoul(tmp, NULL, 16); }
            for (int i = 0; i < 16; ++i) { char tmp[9]={0}; memcpy(tmp, cHex + i*8, 8);  cBuf[i]  = (uint32_t)strtoul(tmp, NULL, 16); }
            n0 = (uint32_t)strtoul(n0Hex, NULL, 16);
        } else {
            // decimal mode: argv[5]=n_dec, argv[6]=e_dec, argv[7]=c_dec
            mpz_t nDec, cDec; mpz_init(nDec); mpz_init(cDec);
            if (mpz_set_str(nDec, nArg, 10)!=0) { fprintf(stderr, "invalid n decimal\n"); return 2; }
            if (mpz_set_str(cDec, cArg, 10)!=0) { fprintf(stderr, "invalid c decimal\n"); return 2; }
            // compute n0 = -n^{-1} mod 2^32 (uses only low 32-bit of n)
            uint32_t nLow = (uint32_t)mpz_get_ui(nDec);
            // extended gcd to get inverse mod 2^32
            uint64_t mod = 0x100000000ull;
            int64_t t=0, newt=1; int64_t r=(int64_t)mod, newr=nLow;
            while (newr != 0) { int64_t q = r / newr; int64_t tmp=t - q*newt; t=newt; newt=tmp; tmp=r - q*newr; r=newr; newr=tmp; }
            if (r != 1) { fprintf(stderr, "n low 32 not invertible\n"); return 2; }
            if (t < 0) t += mod; uint32_t inv = (uint32_t)t; n0 = (uint32_t)(0u - inv);
            // compute R^2 mod n where R=2^512
            mpz_t R, R2, tmp; mpz_init(R); mpz_init(R2); mpz_init(tmp);
            mpz_set_ui(R, 0); mpz_setbit(R, 512);
            mpz_mod(R, R, nDec);
            mpz_mul(R2, R, R); mpz_mod(R2, R2, nDec);
            // export little-endian 32-bit words
            mpz_t tN; mpz_init_set(tN, nDec);
            for (int i=0;i<16;i++){ nBuf[i]=(uint32_t)mpz_get_ui(tN); mpz_fdiv_q_2exp(tN, tN, 32); }
            mpz_t tR2; mpz_init_set(tR2, R2);
            for (int i=0;i<16;i++){ r2Buf[i]=(uint32_t)mpz_get_ui(tR2); mpz_fdiv_q_2exp(tR2, tR2, 32); }
            mpz_t tC; mpz_init_set(tC, cDec);
            for (int i=0;i<16;i++){ cBuf[i]=(uint32_t)mpz_get_ui(tC); mpz_fdiv_q_2exp(tC, tC, 32); }
            mpz_clears(nDec, cDec, R, R2, tmp, tN, tR2, tC, NULL);
        }
        const uint32_t* n = nBuf; const uint32_t* r2 = r2Buf; const uint32_t* c = cBuf;

        id<MTLBuffer> bAlphabet = [dev newBufferWithBytes:alphabet length:base options:MTLResourceStorageModeShared];
        id<MTLBuffer> bN = [dev newBufferWithBytes:n length:16*4 options:MTLResourceStorageModeShared];
        id<MTLBuffer> bR2= [dev newBufferWithBytes:r2 length:16*4 options:MTLResourceStorageModeShared];
        id<MTLBuffer> bC = [dev newBufferWithBytes:c length:16*4 options:MTLResourceStorageModeShared];
        id<MTLBuffer> bN0= [dev newBufferWithBytes:&n0 length:4 options:MTLResourceStorageModeShared];
        id<MTLBuffer> bFound = [dev newBufferWithLength:4 options:MTLResourceStorageModeShared]; memset(bFound.contents, 0, 4);
        id<MTLBuffer> bOutPin= [dev newBufferWithLength:pinLen options:MTLResourceStorageModeShared];
        id<MTLBuffer> bOutIdx= [dev newBufferWithLength:8 options:MTLResourceStorageModeShared];

        uint64_t cursor = start, end = start + total; const int barW = 30; NSDate* t0 = [NSDate date]; double last=0; const double throttle=1.0; const char spin[4]={'|','/','-','\\'}; int sp=0;
        while (cursor < end) {
            uint32_t thisCount = (uint32_t)MIN((uint64_t)batch, end - cursor);

            Params p = { cursor, thisCount, base, pinLen };
            id<MTLBuffer> bParams = [dev newBufferWithBytes:&p length:sizeof(Params) options:MTLResourceStorageModeShared];
            id<MTLBuffer> bOutPins = [dev newBufferWithLength:(NSUInteger)thisCount * pinLen options:MTLResourceStorageModeShared];

            id<MTLCommandBuffer> cb = [q commandBuffer];
            id<MTLComputeCommandEncoder> enc = [cb computeCommandEncoder];
            [enc setComputePipelineState:pso];
            [enc setBuffer:bParams offset:0 atIndex:0];
            [enc setBuffer:bAlphabet offset:0 atIndex:1];
            [enc setBuffer:bN offset:0 atIndex:2];
            [enc setBuffer:bR2 offset:0 atIndex:3];
            [enc setBuffer:bC offset:0 atIndex:4];
            [enc setBuffer:bN0 offset:0 atIndex:5];
            [enc setBuffer:bFound offset:0 atIndex:6];
            [enc setBuffer:bOutPin offset:0 atIndex:7];
            [enc setBuffer:bOutIdx offset:0 atIndex:8];
            MTLSize grid = MTLSizeMake(thisCount, 1, 1);
            NSUInteger tg = MIN((NSUInteger)pso.maxTotalThreadsPerThreadgroup, (NSUInteger)1024);
            [enc dispatchThreads:grid threadsPerThreadgroup:MTLSizeMake(tg,1,1)];
            [enc endEncoding];
            [cb commit];
            [cb waitUntilCompleted];

            // Check found
            if (*(uint32_t*)bFound.contents) {
                fwrite(bOutPin.contents, 1, pinLen, stdout);
                fflush(stdout);
                fprintf(stderr, "\nFound at idx=%llu\n", *(unsigned long long*)bOutIdx.contents);
                return 0;
            }

            cursor += thisCount;
            NSTimeInterval el = [[NSDate date] timeIntervalSinceDate:t0]; if (el - last >= throttle || cursor >= end) {
                double frac = (double)(cursor - start)/(double)total; if (frac>1.0) frac=1.0; int filled=(int)(frac*barW);
                NSMutableString* bar=[NSMutableString stringWithCapacity:barW]; for(int i=0;i<barW;++i)[bar appendString:(i<filled?@"#":@"-")];
                double rate=(el>0)?((double)(cursor-start)/el):0; double remain=(rate>1e-9)?((double)total-(double)(cursor-start))/rate:INFINITY;
                fprintf(stderr, "\r[%s] %5.1f%% %c processed=%llu/%llu rate=%.0f/s eta=%s", [bar UTF8String], frac*100.0, spin[sp++%4], (unsigned long long)(cursor-start), (unsigned long long)total, rate, isfinite(remain)?[[NSString stringWithFormat:@"%.1fs", remain] UTF8String]:"∞"); fflush(stderr);
                lastLog = elapsed;
            }
        }
        fprintf(stderr, "\nDone, not found in window.\n");
    }
    return 0;
}