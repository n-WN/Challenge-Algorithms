// g++ -O3 -march=native -std=c++17 solver_bf_gmp.cpp \
//   -I/opt/homebrew/opt/gmp/include -L/opt/homebrew/opt/gmp/lib \
//   -lgmpxx -lgmp -pthread -o solver_bf_gmp
//
// Usage:
//   ./solver_bf_gmp <n> <e> <c> [--threads 6] [--len 6]
//
// Reads RSA params and brute-forces all PINs from the Python string.printable
// alphabet using mpz_powm_ui, comparing pow(M, e, n) to c.
// Prints the found 6-byte PIN to stdout as raw bytes on success.
//
// WARNING: For alphabet size 100 and length 6, total space is 1e12 and is
// not tractable within 30 seconds. This program is provided per request and
// includes a live progress bar.

#include <gmpxx.h>
#include <atomic>
#include <chrono>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <string>
#include <thread>
#include <vector>
#include <algorithm>
#include <sstream>

using mpz = mpz_class;
using clock_type = std::chrono::steady_clock;

// Python string.printable replicated here (100 chars)
static const char* DEFAULT_ALPHABET =
    "0123456789"
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~ "
    "\t\n\r\x0b\x0c"; // tab, newline, carriage return, vertical tab, form feed

struct Args {
    mpz n;
    unsigned long e_ui {65537};
    mpz c;
    unsigned threads {6};
    unsigned pin_len {6};
};

// Default preset when no CLI params are provided
static const char* PRESET_N =
    "12797238567939373327290740181067928655036715140086366228695600354441701805042996693724492073962821232105794144227525679428233867878596111656619420618371273";
static const unsigned long PRESET_E = 65537ul;
static const char* PRESET_C =
    "3527077117699128297213675720714263452674443031519633052631407312233044869485683860610136570675841069826332336207623212194708283745914346102673061030089974";

static std::atomic<bool> g_found{false};
static std::string g_found_pin;

static inline void index_to_pin(uint64_t idx,
                                const std::string& alphabet,
                                unsigned pin_len,
                                char out_buf[]) {
    const uint64_t base = alphabet.size();
    for (int pos = static_cast<int>(pin_len) - 1; pos >= 0; --pos) {
        uint64_t digit = idx % base;
        idx /= base;
        out_buf[pos] = alphabet[static_cast<size_t>(digit)];
    }
}

static inline void import_bytes_be(mpz& out, const char* bytes, size_t len) {
    mpz_import(out.get_mpz_t(), len, 1, 1, 1, 0, bytes);
}

static void progress_printer(std::atomic<uint64_t>& attempts,
                             const uint64_t total_space) {
    using namespace std::chrono;
    auto start = clock_type::now();
    uint64_t last_attempts = 0;
    auto last = start;
    const int barWidth = 30;
    const char spinner[] = {'|','/','-','\\'};
    unsigned spin = 0;

    while (!g_found.load(std::memory_order_relaxed)) {
        auto now = clock_type::now();
        double elapsed = duration_cast<milliseconds>(now - start).count() / 1000.0;
        double interval = duration_cast<milliseconds>(now - last).count() / 1000.0;
        uint64_t cur = attempts.load(std::memory_order_relaxed);
        double rate = interval > 0 ? (cur - last_attempts) / interval : 0.0;
        double frac = total_space > 0 ? std::min(1.0, double(cur) / double(total_space)) : 0.0;
        int pos = static_cast<int>(barWidth * frac);

        std::ostringstream oss;
        oss << "\r[";
        for (int i = 0; i < barWidth; ++i) oss << (i < pos ? '#' : '-');
        oss << "] " << int(frac * 100.0) << "% " << spinner[spin++ % 4]
            << "  tried=" << cur << "/" << total_space
            << "  rate=" << rate << "/s";
        if (rate > 1e-9) {
            double remain = (double(total_space) - double(cur)) / rate;
            oss << "  eta=" << remain << "s";
        }
        std::cerr << oss.str() << std::flush;
        last = now; last_attempts = cur;
        std::this_thread::sleep_for(std::chrono::milliseconds(200));
        if (cur >= total_space) break;
    }
    std::cerr << "\r" << std::string(100, ' ') << "\r" << std::flush;
}

static void worker(uint64_t start_idx,
                   uint64_t end_idx,
                   const std::string& alphabet,
                   unsigned pin_len,
                   const mpz& n,
                   unsigned long e_ui,
                   const mpz& c,
                   std::atomic<uint64_t>& attempts) {
    mpz M, ctest;
    std::vector<char> pin(pin_len);
    const uint64_t report_stride = 256;
    uint64_t local = 0;

    for (uint64_t i = start_idx; i < end_idx && !g_found.load(std::memory_order_relaxed); ++i) {
        index_to_pin(i, alphabet, pin_len, pin.data());
        import_bytes_be(M, pin.data(), pin_len);
        mpz_powm_ui(ctest.get_mpz_t(), M.get_mpz_t(), e_ui, n.get_mpz_t());
        if (ctest == c) {
            g_found_pin.assign(pin.data(), pin_len);
            g_found.store(true, std::memory_order_relaxed);
            break;
        }
        if (++local == report_stride) {
            attempts.fetch_add(local, std::memory_order_relaxed);
            local = 0;
        }
    }
    if (local) attempts.fetch_add(local, std::memory_order_relaxed);
}

static bool parse_args(int argc, char** argv, Args& out) {
    if (argc == 1) {
        // No args: use preset defaults per user request
        out.n = mpz(PRESET_N);
        out.e_ui = PRESET_E;
        out.c = mpz(PRESET_C);
        out.threads = 6;
        out.pin_len = 6;
        return true;
    }
    if (argc < 4) return false;
    out.n = mpz(argv[1]);
    out.e_ui = std::stoul(argv[2]);
    out.c = mpz(argv[3]);
    for (int i = 4; i < argc; ++i) {
        std::string a = argv[i];
        if (a == "--threads" && i + 1 < argc) {
            out.threads = std::stoul(argv[++i]);
        } else if (a == "--len" && i + 1 < argc) {
            out.pin_len = std::stoul(argv[++i]);
        }
    }
    return true;
}

int main(int argc, char** argv) {
    Args args;
    if (!parse_args(argc, argv, args)) {
        std::cerr << "Usage: ./solver_bf_gmp <n> <e> <c> [--threads N] [--len L]\n"
                  << "(No args -> uses preset: -len 6 -threads 6 -timeout 0 with built-in n/e/c)\n";
        return 2;
    }

    std::string alphabet(DEFAULT_ALPHABET);
    const uint64_t base = alphabet.size();
    const unsigned L = args.pin_len;

    // compute total = base^L (fits in 64-bit for base<=100 and L<=10)
    uint64_t total = 1;
    for (unsigned i = 0; i < L; ++i) total *= base;

    unsigned threads = std::min<unsigned>(args.threads, std::max(1u, std::thread::hardware_concurrency()));

    // partition space evenly
    std::vector<std::thread> pool;
    std::atomic<uint64_t> attempts{0};

    // progress thread
    std::thread prog(progress_printer, std::ref(attempts), total);

    for (unsigned t = 0; t < threads; ++t) {
        uint64_t start_idx = (total * t) / threads;
        uint64_t end_idx   = (total * (t + 1)) / threads;
        pool.emplace_back(worker, start_idx, end_idx,
                          std::cref(alphabet), L,
                          std::cref(args.n), args.e_ui, std::cref(args.c),
                          std::ref(attempts));
    }

    for (auto& th : pool) th.join();
    g_found.store(true, std::memory_order_relaxed); // stop progress
    if (prog.joinable()) prog.join();

    if (!g_found_pin.empty()) {
        std::cout.write(g_found_pin.data(), g_found_pin.size());
        return 0;
    }
    std::cerr << "Not found." << std::endl;
    return 1;
}
