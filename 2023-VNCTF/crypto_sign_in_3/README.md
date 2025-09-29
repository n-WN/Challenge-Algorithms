# [VNCTF2023] crypto_sign_in_3 Write-up

## 题目复现
题目只给出生成脚本 `task/challenge.sage` 与一组输出：$N, x_1, C, F$。脚本利用 CRT 在未知的 $p,q$ 上构造了一条椭圆 $A_1^2 x^2 + C^2 y^2 = (A_1 C)^2$ 与一条抛物线 $A_2 x^2 + D x + F = -E y$，并保证同一明文点 $(x_0,y_0)$ 交于两曲线，同时泄露了另一交点 $(x_1,y_1)$。

## 解题思路
1. **恢复辅助参数 $E$**：代入已知交点得到
   $$E^2 \equiv C^2 (A_2 x_1^2 + D x_1 + F)^2 \big(A_1^2 (C^2 - x_1^2)\big)^{-1} \pmod N,$$
   $$E^2 \equiv \frac{C^2 (A_2 x_1^2 + D x_1 + F)^2}{A_1^2 (C^2 - x_1^2)} \pmod N$$
   逐项检查分母可逆即可在 $\mathbb{Z}_N$ 中取平方根获得 $E$。
2. **构造单变量多项式**：利用 $y = -(A_2 x^2 + D x + F)E^{-1}$ 消去 $y$，得到
   $$f(x) = A_1^2 E^2 x^2 + C^2(A_2 x^2 + D x + F)^2 - (A_1 C E)^2 \equiv 0 \pmod N,$$
   其中 $x_0, x_1$ 均为根。
3. **降次并保留未知根**：对 $f(x)$ 先做首项归一，再整除 $(x - x_1)$ 得到次数 3 的多项式 $g(x)$，其在模 $N$ 下仍拥有小根 $x_0$。
4. **Coppersmith 小根搜索**：flag 长度已知为 49 字节，令 $X = 2^{392}$，执行 `g.small_roots(X=X, beta=0.3)` 得到唯一小根 $x_0$。
5. **转换为明文**：将 $x_0$ 按大端转换成 bytes 即 `flag{With_great_power_comes_great_responsibility}`。

## 遇到的问题
- 直接对 $f(x)$ 调用 `small_roots` 会失败，必须先归一并除去显式根 $(x - x_1)$，否则格基不够短。
- Sage 默认在 `$HOME/.sage` 写缓存，沙箱下需先 `export HOME=/Users/lov3/Downloads/buu`。

## 复现脚本
运行：

```bash
HOME=/Users/lov3/Downloads/buu sage -python solution/solution.py
```

输出：

```
flag{With_great_power_comes_great_responsibility}
```

## 复杂度分析
核心步骤是 3 维格上的 LLL，复杂度约 $	ilde{O}(n^3)$，对 $2048$ 位模数仅需数百微秒，相比爆破明显更优。
