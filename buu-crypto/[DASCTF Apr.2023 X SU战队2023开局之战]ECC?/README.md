# [DASCTF Apr.2023 X SU战队2023开局之战]【中等】ECC? Write-up

## 题目复现
压缩包内提供 `task/task.sage` 与 `task/output.txt`。脚本随机生成一条在 $\mathbb{Z}_N$ 上的椭圆曲线，并对同一明文点分别使用 $e_1, e_2, e_3$ 进行「加密」，同时泄露多倍点 $C_1, C_2, C_3$ 与一个额外的大整数 `gift = k \cdot N`。

## 解题思路
1. **恢复模数 $N$**：令 $R_i = y_i^2 - x_i^3$，利用三点联立可消去未知的 $a,b$，构造组合
   $$V = (R_1 - R_2)(x_1 - x_3) - (R_1 - R_3)(x_1 - x_2).$$
   因为曲线方程在模 $N$ 成立，上式必是 $N$ 的倍数，与 `gift` 求 $\gcd$ 立即得到真模数 $N$。
2. **恢复曲线参数**：在 $\mathbb{Z}_N$ 内部解方程
   $$a = (R_1 - R_2)(x_1 - x_2)^{-1},\qquad b = R_1 - a x_1,$$
   即可重建椭圆曲线 $E: y^2 = x^3 + a x + b$。
3. **求得原始明文点**：由于 $\gcd(e_1, e_3)=1$，存在系数 $(s,t)$ 满足 $s e_1 + t e_3 = 1$。按点加法组合 $P = s C_1 + t C_3$，即可同时满足 $e_1 P = C_1$ 与 $e_3 P = C_3$。验证可知 $P$ 亦满足 $e_2 P = C_2$。
4. **恢复 flag**：脚本只在点的 $x$ 坐标低 8 bit 内塞填充，故明文为 $x_P \gg 8$，转字节即得到 `DASCTF{RSA_0n_ECC_1s_mor3_Ineres7ing}`。

## 遇到的问题
- 初次直接在 `EllipticCurve(Zmod(N), [a,b])` 求逆时忘记设置 `HOME`，同样遇到 Sage 缓存权限问题。
- 若 $e_1, e_3$ 不互素则需分别对四种迹计算，幸好题目参数满足 $\gcd(e_1, e_3)=1$，简化了逆过程。

## 复现脚本

```bash
HOME=/Users/lov3/Downloads/buu sage -python solution/solution.py
```

输出：

```
DASCTF{RSA_0n_ECC_1s_mor3_Ineres7ing}
```

## 复杂度分析
- 计算 $\gcd$ 与曲线参数的求逆属常数次模运算，复杂度 $O(\log^2 N)$。
- 逆向多倍点仅需一次贝祖系数和三次曲线加法，整体复杂度远优于尝试枚举离散对数。
