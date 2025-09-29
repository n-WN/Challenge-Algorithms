# WUSTCTF2020 dp_leaking_1s_very_d@angerous Write-up

## 题目分析
- 提供 $e=65537$、模数 $n$、密文 $c$ 和泄漏的 $d_p = d \bmod (p-1)$。
- RSA 私钥满足 $ed \equiv 1 \pmod{(p-1)(q-1)}$，因此 $e d_p \equiv 1 \pmod{p-1}$，于是
  $$k = e\,d_p - 1 = h (p-1)$$
  对某个整数 $h$ 成立。
- 也就是说 $p-1$ 是 $k$ 的因子。利用费马小定理，若 $a$ 与 $p$ 互素，则 $a^{p-1} \equiv 1 \pmod{p}$，进而 $a^{k} \equiv 1 \pmod{p}$。
- 对模 $q$ 并不一定成立，因此 $\gcd(a^{k} - 1, n)$ 大概率就是 $p$。

## 利用步骤
1. 计算 $k = e d_p - 1$。
2. 依次选择若干小底数 $a$，求 $g = \gcd(a^{k} - 1, n)$。
   - 若 $g \neq 1, n$ 则成功恢复质因数 $p$。
3. 得到 $q = n/p$，进而计算 $\varphi(n) = (p-1)(q-1)$ 和私钥指数 $d = e^{-1} \bmod \varphi(n)$。
4. 用 $m = c^d \bmod n$ 还原明文。

## 关键代码
详见 `solution/solution.py`。核心片段如下：

```python
k = e * dp - 1
for base in (2, 3, 5, 7, 11):
    g = gcd(pow(base, k, n) - 1, n)
    if 1 < g < n:
        p = int(g)
        break
```

## Flag
`wctf2020{dp_leaking_1s_very_d@angerous}`
