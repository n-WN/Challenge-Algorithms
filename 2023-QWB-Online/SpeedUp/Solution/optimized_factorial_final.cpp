/**
 * @file optimized_factorial_final.cpp
 * @brief 计算超大阶乘及其数位和的极致优化版本
 * g++ -o optimized_factorial optimized_factorial_final.cpp -O3 -std=c++17 -lgmpxx -lgmp -lcrypto -lpthread
 * g++ -o optimized_factorial optimized_factorial_final.cpp \
    -I$(brew --prefix gmp)/include \
    -L$(brew --prefix gmp)/lib \
    -I$(brew --prefix openssl)/include \
    -L$(brew --prefix openssl)/lib \
    -O3 -std=c++17 -lgmpxx -lgmp -lcrypto -lpthread
 *
 * 核心优化技术:
 * 1. 分段筛法 (Segmented Sieve): 高效计算阶乘的质因数分解。
 * 2. 并行分治乘法 (Parallel Divide & Conquer): 利用多核CPU加速最终结果的计算。
 * 3. 大基数求和 (Large Radix Summation): 避免昂贵的大数到字符串的转换，快速计算数位和。
 */

#include <iostream>
#include <vector>
#include <utility>
#include <cmath>
#include <chrono>
#include <future>
#include <algorithm>
#include <gmpxx.h>
#include <openssl/sha.h>
#include <iomanip>

// 使用标准命名空间
using namespace std;
using namespace std::chrono;

// 定义质因数分解表的类型
using PrimePower = pair<size_t, size_t>;
using PrimePowerTable = vector<PrimePower>;

/**
 * @brief [核心优化] 使用分段筛法和勒让德公式计算 n! 的质因数分解
 * @param n 上限
 * @return 一个包含 {质数, 幂次} 对的 vector
 */
PrimePowerTable SegmentedSieveFactorial(size_t n) {
    if (n < 2) return {};

    const size_t sqrt_n = static_cast<size_t>(sqrt(n));
    PrimePowerTable result;
    result.reserve(static_cast<size_t>(1.2 * n / log(n)));

    // 步骤 1: 预筛选 <= sqrt(n) 的素数 (base_primes)
    vector<size_t> base_primes;
    vector<bool> is_prime(sqrt_n + 1, true);
    is_prime[0] = is_prime[1] = false;
    for (size_t p = 2; p * p <= sqrt_n; ++p) {
        if (is_prime[p]) {
            for (size_t i = p * p; i <= sqrt_n; i += p)
                is_prime[i] = false;
        }
    }
    for (size_t p = 2; p <= sqrt_n; ++p) {
        if (is_prime[p]) {
            base_primes.push_back(p);
        }
    }

    // 步骤 2: 计算 base_primes 在 n! 中的幂次
    for (size_t p : base_primes) {
        size_t exponent = 0;
        for (size_t j = p; j <= n; j *= p) {
            exponent += n / j;
            if (j > n / p) break; // 防止溢出
        }
        result.emplace_back(p, exponent);
    }
    
    // 步骤 3: 分段筛处理 > sqrt(n) 的素数
    // 缓存友好的段大小，例如 64K
    const size_t SEGMENT_SIZE = 1 << 16; 
    vector<bool> is_composite(SEGMENT_SIZE);

    for (size_t low = sqrt_n + 1; low <= n; low += SEGMENT_SIZE) {
        fill(is_composite.begin(), is_composite.end(), false);
        const size_t high = min(low + SEGMENT_SIZE - 1, n);

        // 使用 base_primes 划掉段内的合数
        for (size_t p : base_primes) {
            size_t start_idx = (low + p - 1) / p * p;
            for (size_t j = start_idx; j <= high; j += p) {
                if (j >= low) {
                    is_composite[j - low] = true;
                }
            }
        }
        
        // 步骤 4: 收集段内的素数并计算其幂次
        for (size_t i = low; i <= high; ++i) {
            if (!is_composite[i - low]) {
                // 对于 > sqrt(n) 的素数 p，其在 n! 中的幂次就是 floor(n/p)
                result.emplace_back(i, n / i);
            }
        }
    }

    return result;
}


// 定义迭代器类型别名
using PrimePowIter = PrimePowerTable::const_iterator;

/**
 * @brief [并行分治] 从质因数分解递归地计算阶乘
 */
mpz_class ProductParallel(PrimePowIter beg, PrimePowIter end) {
    auto dist = distance(beg, end);
    if (dist == 0) return 1;
    if (dist == 1) {
        mpz_class res;
        mpz_pow_ui(res.get_mpz_t(), mpz_class(beg->first).get_mpz_t(), beg->second);
        return res;
    }

    // 任务规模较小时，串行计算以避免线程开销
    if (dist < 32) {
        mpz_class res = 1;
        for (auto it = beg; it != end; ++it) {
            mpz_class term;
            mpz_pow_ui(term.get_mpz_t(), mpz_class(it->first).get_mpz_t(), it->second);
            res *= term;
        }
        return res;
    }

    auto mid = beg + dist / 2;
    auto future_left = async(launch::async, ProductParallel, beg, mid);
    mpz_class right_res = ProductParallel(mid, end);
    return future_left.get() * right_res;
}

/**
 * @brief [核心优化] 高效计算大整数的各位数字之和
 */
mpz_class SumDigitsFast(mpz_class n) {
    mpz_class total_sum = 0;
    // 使用一个 unsigned long long 范围内的10的幂作为基数
    // FIX: 使用构造函数进行初始化
    mpz_class base("1000000000000000000", 10); // 10^18

    while (n > 0) {
        mpz_class remainder_mpz = n % base;
        n /= base;
        unsigned long long rem_ull = mpz_get_ui(remainder_mpz.get_mpz_t());
        while (rem_ull > 0) {
            // FIX: 显式类型转换以消除歧义
            total_sum += static_cast<unsigned long int>(rem_ull % 10);
            rem_ull /= 10;
        }
    }
    return total_sum;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    const size_t i = 134217728;
    cout << "计算 " << i << "! 中，请稍候..." << endl;
    
    auto start = high_resolution_clock::now();
    PrimePowerTable prime_factors = SegmentedSieveFactorial(i);
    auto stop = high_resolution_clock::now();
    auto duration = duration_cast<milliseconds>(stop - start);
    cout << "质因数分解耗时: " << duration.count() << "ms" << endl;

    start = high_resolution_clock::now();
    mpz_class answer = ProductParallel(prime_factors.cbegin(), prime_factors.cend());
    stop = high_resolution_clock::now();
    duration = duration_cast<milliseconds>(stop - start);
    cout << "并行计算阶乘耗时: " << duration.count() << "ms" << endl;

    start = high_resolution_clock::now();
    mpz_class sum = SumDigitsFast(answer);
    stop = high_resolution_clock::now();
    duration = duration_cast<milliseconds>(stop - start);
    cout << "高效计算数位和耗时: " << duration.count() << "ms" << endl;

    cout << "数位和为: " << sum << endl;

    start = high_resolution_clock::now();
    string sumString = sum.get_str();
    
    unsigned char hash[SHA224_DIGEST_LENGTH];
    SHA256(reinterpret_cast<const unsigned char*>(sumString.c_str()), sumString.length(), hash);
    
    cout << "SHA-256 哈希结果为: ";
    cout << hex << setfill('0');
    for (size_t j = 0; j < SHA256_DIGEST_LENGTH; ++j) {
        cout << setw(2) << static_cast<int>(hash[j]);
    }
    cout << endl;
    
    stop = high_resolution_clock::now();
    duration = duration_cast<milliseconds>(stop - start);
    cout << "计算哈希耗时: " << duration.count() << "ms" << endl;

    return 0;
}