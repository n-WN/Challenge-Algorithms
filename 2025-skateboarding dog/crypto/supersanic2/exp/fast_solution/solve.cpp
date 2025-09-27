// g++ -std=c++17 -O3 -o solve solve.cpp -I/opt/homebrew/opt/gmp/include -L/opt/homebrew/opt/gmp/lib -lgmp -pthread
// g++ -std=c++17 -O3 -o solve solve.cpp -lgmp -pthread

#include <iostream>
#include <string>
#include <vector>
#include <thread>
#include <mutex>
#include <atomic>
#include <unordered_map>
#include <gmp.h>
#include <algorithm> // For std::min
#include <cstdio>    // For fprintf, stderr

// ... (SharedState 结构体和 build_map_worker, search_worker 函数保持不变) ...
struct SharedState {
    std::unordered_map<std::string, unsigned long> M;
    std::mutex map_mutex;
    std::atomic<bool> solution_found;
    std::atomic<unsigned long> final_r1;
    std::atomic<unsigned long> final_r2;

    SharedState() : solution_found(false), final_r1(0), final_r2(0) {}
};

void build_map_worker(
    unsigned long start_r1,
    unsigned long end_r1,
    SharedState& state,
    const mpz_t c,
    const mpz_t e,
    const mpz_t n
) {
    mpz_t r1_mpz, r1_e, r1_e_inv, key, temp;
    mpz_inits(r1_mpz, r1_e, r1_e_inv, key, temp, NULL);

    for (unsigned long r1 = start_r1; r1 < end_r1; ++r1) {
        mpz_set_ui(r1_mpz, r1);
        mpz_powm(r1_e, r1_mpz, e, n);
        if (mpz_invert(r1_e_inv, r1_e, n) == 0) {
            continue;
        }
        mpz_mul(temp, c, r1_e_inv);
        mpz_mod(key, temp, n);

        char* key_str = mpz_get_str(NULL, 16, key);
        std::string key_s(key_str);
        free(key_str);

        std::lock_guard<std::mutex> lock(state.map_mutex);
        state.M[key_s] = r1;
    }
    mpz_clears(r1_mpz, r1_e, r1_e_inv, key, temp, NULL);
}

void search_worker(
    unsigned long start_r2,
    unsigned long end_r2,
    SharedState& state,
    const mpz_t e,
    const mpz_t n
) {
    mpz_t r2_mpz, x;
    mpz_inits(r2_mpz, x, NULL);

    for (unsigned long r2 = start_r2; r2 < end_r2; ++r2) {
        if (state.solution_found.load()) {
            break;
        }

        mpz_set_ui(r2_mpz, r2);
        mpz_powm(x, r2_mpz, e, n);

        char* x_str = mpz_get_str(NULL, 16, x);
        std::string x_s(x_str);
        free(x_str);

        auto it = state.M.find(x_s);
        if (it != state.M.end()) {
            if (!state.solution_found.exchange(true)) {
                state.final_r1.store(it->second);
                state.final_r2.store(r2);
            }
            break;
        }
    }
    mpz_clears(r2_mpz, x, NULL);
}


// --- main 函数 ---
// CHANGED: 修改函数签名以接收命令行参数
int main(int argc, char *argv[]) {
    // CHANGED: 检查命令行参数的数量
    if (argc != 4) {
        // 向标准错误输出用法信息，避免干扰脚本捕获 stdout
        fprintf(stderr, "Usage: %s <n> <e> <c>\n", argv[0]);
        return 1; // 返回错误码
    }

    const unsigned int NUM_THREADS = 14;
    const unsigned long BIT = 1 << 24;

    mpz_t n, e, c;
    // CHANGED: 从命令行参数 argv 初始化 GMP 大数
    // argv[0] 是程序名, argv[1] 是第一个参数 (n)
    // argv[2] 是第二个参数 (e), argv[3] 是第三个参数 (c)
    mpz_init_set_str(n, argv[1], 10);
    mpz_init_set_str(e, argv[2], 10);
    mpz_init_set_str(c, argv[3], 10);

    SharedState state;
    std::vector<std::thread> threads;

    // --- 阶段一：并行构建 Map ---
    // std::cout << "Phase 1: Building map with " << NUM_THREADS << " threads..." << std::endl;
    unsigned long chunk_size1 = (BIT + NUM_THREADS - 1) / NUM_THREADS;
    for (unsigned int i = 0; i < NUM_THREADS; ++i) {
        unsigned long start = i * chunk_size1 + 1;
        unsigned long end = std::min((i + 1) * chunk_size1 + 1, BIT);
        if (start < end) {
            threads.emplace_back(build_map_worker, start, end, std::ref(state), std::cref(c), std::cref(e), std::cref(n));
        }
    }

    for (auto& t : threads) {
        t.join();
    }
    threads.clear();
    // std::cout << "Phase 1: Map built. Size: " << state.M.size() << std::endl;

    // --- 阶段二：并行搜索 ---
    // std::cout << "Phase 2: Searching for match with " << NUM_THREADS << " threads..." << std::endl;
    unsigned long chunk_size2 = (BIT + NUM_THREADS - 1) / NUM_THREADS;
    for (unsigned int i = 0; i < NUM_THREADS; ++i) {
        unsigned long start = i * chunk_size2 + 1;
        unsigned long end = std::min((i + 1) * chunk_size2 + 1, BIT);
         if (start < end) {
            threads.emplace_back(search_worker, start, end, std::ref(state), std::cref(e), std::cref(n));
        }
    }

    for (auto& t : threads) {
        t.join();
    }

    // --- 输出结果 ---
    if (state.solution_found.load()) {
        unsigned long r1 = state.final_r1.load();
        unsigned long r2 = state.final_r2.load();
        // std::cout << "\nSolution found!" << std::endl;
        // std::cout << "r1 = " << r1 << std::endl;
        // std::cout << "r2 = " << r2 << std::endl;

        mpz_t m, r1_mpz, r2_mpz;
        mpz_inits(m, r1_mpz, r2_mpz, NULL);

        mpz_set_ui(r1_mpz, r1);
        mpz_set_ui(r2_mpz, r2);
        mpz_mul(m, r1_mpz, r2_mpz);

        // gmp_printf("m = r1 * r2 = %Zd\n", m);

        size_t size = 6;
        unsigned char pin[size];
        mpz_export(pin, NULL, 1, sizeof(unsigned char), 1, 0, m);

        // std::cout << "PIN (as bytes): ";
        for(size_t i = 0; i < size; ++i) {
            std::cout << pin[i];
        }
        std::cout << std::endl;

        mpz_clears(m, r1_mpz, r2_mpz, NULL);
    } else {
        std::cout << "\nSolution not found in the given range." << std::endl;
    }

    mpz_clears(n, e, c, NULL);

    return 0;
}
