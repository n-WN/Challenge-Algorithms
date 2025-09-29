# MRCTF2020 Easy_RSA Write-up

## 题目概览

- 给出生成脚本 `easy_RSA.py`，内部先各自生成两对 1024 位素数 $(p_1,q_1)$、$(p_2,q_2)$，再通过线性组合求 `nextprime` 得到最终的模数因子。
- 输出内容包括：
  - `P_n = p_1 q_1` 与 `P_F_n = (p_1 - 1)(q_1 - 1)`；
  - `Q_n = p_2 q_2` 与 `Q_E_D = e d`（注意是乘积，不是模意义下的 $ed\equiv1$）；
  - 最终密文 `Ciphertext`，指数固定为 $E=65537$。

任务是恢复最终的模数 $N = P' Q'$ 并解密密文。

## 第一阶段：由 $(n,\varphi(n))$ 直接分解

- 已知 $P_n$ 与 $P_{F_n}$，记 $\varphi_P = P_{F_n} = (p_1-1)(q_1-1)$。
- 根据恒等式
  $$\varphi_P = p_1 q_1 - (p_1 + q_1) + 1 = P_n - (p_1 + q_1) + 1$$
  可得 $s = p_1 + q_1 = P_n - \varphi_P + 1$。
- 代回二次方程 $X^2 - sX + P_n = 0$，判别式
  $$\Delta = s^2 - 4 P_n$$
  必为完全平方数，开方后即可得到 $(p_1,q_1)$。
- 最终根据脚本逻辑求得
  $$P' = \operatorname{nextprime}(2021 p_1 + 2020 q_1).$$

## 第二阶段：仅知 $(n, e\cdot d)$ 时的分解

- `gen_q` 函数不会打印 $\varphi_Q$，只给出 $Q_n$ 与 $Q_{E_D} = e d$。
- 设 $\varphi_Q = (p_2-1)(q_2-1)$，又因 $d \equiv e^{-1} \pmod{\varphi_Q}$，存在正整数 $k$ 使得
  $$e d - 1 = k\,\varphi_Q.\tag{1}$$
- 脚本中 $e$ 是 53 位随机奇数，故 $k < e < 2^{53}$。
- 记 $S = Q_{E_D} - 1$，则 $S$ 的所有因子中必须有一项等于 $\varphi_Q$。另一方面，$\varphi_Q$ 与 $Q_n$ 的差值为
  $$Q_n - \varphi_Q = p_2 + q_2 - 1 \approx 2\sqrt{Q_n},$$
  相比 $Q_n$ 极小（约 $2^{1024}$）。所以 $\varphi_Q$ 必须非常接近 $Q_n$。
- 令 $k_0 = \lfloor S / Q_n \rfloor$，由于 $\varphi_Q < Q_n$，有 $k_0 \le k$，并且差值不会太大。
- 枚举 $k = k_0, k_0 \pm 1, k_0 \pm 2, \dots$，检查：
  1. $k$ 是否整除 $S$；
  2. 令 $\varphi = S / k$ 后，利用第一阶段同样的公式分解 $Q_n$。
- 对于题目数据，$k_0 = \lfloor S/Q_n \rfloor = 4864856032156929$，而实际 $k = k_0 + 1$，迭代一次即可命中。
- 得到 $(p_2,q_2)$ 后，脚本计算
  $$Q' = \operatorname{nextprime}(|2021 p_2 - 2020 q_2|).$$

## 第三阶段：还原最终密钥并解密

- 终极模数 $N = P' Q'$，其欧拉函数为
  $$\Phi = (P' - 1)(Q' - 1).$$
- 由于题目固定指数 $E = 65537$，私钥指数 $D = E^{-1} \bmod \Phi$。
- 解密密文：
  $$M = C^D \bmod N,$$
  然后转为字节即为 flag。

核心脚本 `solution/solution.py` 实现了以上流程，其中对第二阶段的 $k$ 采用“从 $\lfloor S/Q_n \rfloor$ 起向两侧搜索”的策略，其复杂度由差值控制，这里仅需一次增量。

## Flag

`MRCTF{Ju3t_@_31mp13_que3t10n}`
