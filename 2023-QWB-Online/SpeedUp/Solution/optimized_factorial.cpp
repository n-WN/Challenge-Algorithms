// g++ -o optimized_factorial optimized_factorial.cpp -O3 -std=c++17 -lgmpxx -lgmp -lcrypto -lpthread

#include <iostream>
#include <sstream>
#include <iomanip>
#include <openssl/sha.h>
#include <gmpxx.h>
#include <bits/stdc++.h>
#include <chrono> // 引入计时器库
using namespace std;
using namespace std::chrono;
auto getPrimePow(size_t n)
{
    vector<pair<size_t,size_t>> tab; 
    vector<bool> ar;
    ar.resize(n+1);
    tab.reserve(2*n/log(n));
    for (size_t i=2;i<=n;++i)
    {
        if (!ar[i])
        {
            size_t cnt=0;
            for (size_t j=i;j<=n;j+=i)
            {
                ar[j]=true;
            }
            for (size_t j=i;j<=n;j*=i)
            {
                cnt+=n/j;
            }
            tab.emplace_back(i,cnt);
        }
    }
    return tab;
}

template<typename iter>
mpz_class cal_odd(iter beg,iter end)
{
    if (beg==end)
    {
        if (beg->second%2)
        {
            beg->second/=2;
            return beg->first;
        }
        else
        {
            beg->second/=2;
            return 1;
        }
    }
    auto mid=beg+(end-beg)/2;
    return cal_odd(beg,mid)*cal_odd(mid+1,end);
}

mpz_class cal(std::vector<std::pair<size_t, size_t>>&tab)
{
    mpz_class ans=1;
    if (tab.size())
    {
        ans=cal_odd(tab.begin(),tab.end());
        while (tab.size()&&tab.back().second==0)
            tab.pop_back();
        auto subans=cal(tab);
        ans*=subans*subans;
    }
    return ans;
}

mpz_class Factorial(size_t n)
{
    auto tab=getPrimePow(n);
    return cal(tab);
}

mpz_class Sum(string str){
    mpz_class cnt=0;
    for(int i=0;i<str.size();i++){
        cnt+=str[i]-'0';
    }
    return cnt;
}

int main()
{
    size_t i = 134217728;
    auto start = high_resolution_clock::now(); // 记录开始时间
    // i = 5;
    auto answer = Factorial(i);
    auto stop = high_resolution_clock::now(); // 记录阶乘结束时间
    auto duration = duration_cast<milliseconds>(stop - start); // 计算阶乘所需时间
    cout << "计算阶乘耗时 (ms): " << duration.count() << "ms" << endl;


    start = high_resolution_clock::now(); // 记录开始时间
    // 初始化数位和为 0
    mpz_class sum = 0;

    // 求阶乘结果的数位和
    // while (answer > 0) {
    //     sum = sum + (answer % 10); // 求得当前位的数值并加到 sum 上
    //     answer /= 10; // 去除当前位，继续计算下一位
    // }
    std::ostringstream oss;
    oss << answer;
    std::string ansString = oss.str();
    sum = Sum(ansString);
    stop = high_resolution_clock::now();
    duration = duration_cast<milliseconds>(stop - start);
    cout << "计算数位和耗时 (ms): " << duration.count() << "ms" << endl;

    // 输出数位和
    std::cout << "数位和为: " << sum << std::endl;

    start = high_resolution_clock::now(); // 记录开始时间
    // 将数位和转换为字符串
    std::ostringstream osss;
    osss << sum;
    std::string sumString = osss.str();

    stop = high_resolution_clock::now();
    duration = duration_cast<milliseconds>(stop - start);
    cout << "计算将数位和转换为字符串耗时 (ms): " << duration.count() << "ms" << endl;
    std::cout << sumString << '\n';
    start = high_resolution_clock::now(); // 记录开始时间
    // 计算 SHA-256 哈希
    unsigned char hash[SHA256_DIGEST_LENGTH];
    SHA256_CTX ctx;
    SHA256_Init(&ctx);
    SHA256_Update(&ctx, sumString.c_str(), sumString.length());
    SHA256_Final(hash, &ctx);
    
    // 输出 SHA-256 哈希结果
    std::cout << "SHA-256 哈希结果为: ";
    for (size_t i = 0; i < SHA256_DIGEST_LENGTH; ++i) {
        printf("%02x", hash[i]);
    }
    std::cout << std::endl;

    stop = high_resolution_clock::now();
    duration = duration_cast<milliseconds>(stop - start);
    cout << "计算hash耗时 (ms): " << duration.count() << "ms" << endl;

    return 0;
}