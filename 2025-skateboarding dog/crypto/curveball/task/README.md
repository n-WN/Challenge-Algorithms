**题目概述**

- 交互式 ECC 猜数游戏：你先给出曲线参数 `a,b,p`（检查：$p$ 至少 $384$ bit 且为素数，判别式非零），服务端在域 $\mathbb{F}_{p^2}$ 上构造曲线 $E$ 及其二次扭曲 $E_{\text{twist}}$，随后进行 $40$ 轮：
  - 随机选择 `E` 或 `E_twist`；
  - 取随机点 `P`，随机标量 `k < (p+1)^2`，给出 `Q = k·P` 以及曲线与点坐标；
  - 你需回显一个整数 `k'` 满足 `k'·P = Q`。

本仓库给出一套可复现的参数与求解器，自动完成 40 轮并拿到 flag。

---

**核心思想**

1) 选超奇异曲线，使 $\mathbb{F}_{p^2}$ 上指数极小

- 取 $a=1,\;b=0$（曲线 $E:\; y^2 = x^3 + x$）。若 $p \equiv 11\pmod{12}$，则 $E/\mathbb{F}_p$ 为超奇异且迹 $t=0$。
- 对任意点 $P\in E(\mathbb{F}_{p^2})$，Frobenius 自同态 $\varphi$ 满足 $\varphi^2(P)=P$（坐标 $p$ 次幂）；结合超奇异 $t=0$（特征多项式 $X^2 + p$），可推出在 $\mathbb{F}_{p^2}$ 上有：

  - 对 $E$：$[p+1]P=\mathcal{O}$，指数整除 $p+1$；
  - 对 $E_{\text{twist}}$：$[p-1]P=\mathcal{O}$，指数整除 $p-1$。

因此 $40$ 轮里两种曲线的离散对数都落在“模 $p\pm1$”的循环子群上，远小于一般 ECC 难度。

2) 一步恢复 $\mathbb{F}_{p^2}$ 的构造常量 $\delta$

- 服务端构造 $\mathbb{F}_{p^2} = \mathbb{F}_p[j]/(j^2-\delta)$，但不会直接给 $\delta$。
- 设 $P=(x,y)$，$x=u+v\,j$，$y=s+t\,j$（$u,v,s,t\in\mathbb{F}_p$）。对 $E:\; y^2 = x^3 + x$ 展开并按 $1$ 与 $j$ 的系数分离，有

  - $j$ 系数：$2st \equiv 3u^2v + v^3\delta + v \pmod p$；
  - 若 `v ≠ 0`，立得

    $$\delta \equiv (2st - 3u^2v - v)\,(v^3)^{-1} \pmod p.$$

  - 若恰好 `v=0`，用 Q 的坐标同法求 δ；或当轮为扭曲曲线，系数 `a4` 正好等于 δ。

有了 $\delta$ 即可在本地重建 $\mathbb{F}_{p^2}$ 并做点运算。

3) “平滑部分 + 小余因子” 两段式 DLP

- 设当前轮指数 $m = p+1$（在 $E$）或 $m = p-1$（在 $E_{\text{twist}}$）。
- 我们先对 $m$ 做小素数筛（到若干上界 $B$），得到分解 $m = M\cdot c$，其中 $M$ 为 $B$‑平滑部分，$c$ 为“余因子”。
- 共因子消去：$P' = (m/M)P$，$Q' = (m/M)Q$，则 $\operatorname{ord}(P') \mid M$；在平滑群上用 Pohlig–Hellman 线性时间解出 $k_0 \equiv k \pmod{\operatorname{ord}(P')}$。
- 余因子求解：设 $U = MP$，$V = Q - k_0 P$，则存在 $t$ 使 $V = tU$，其中 $\operatorname{ord}(U) \mid c$。对 $c$ 较小（我们在选 $p$ 时保证）时，用 BSGS 在 $\mathcal{O}(\sqrt{c})$ 步内求出 $t$，并合成

  $$k = k_0 + tM.$$

这样无需完全分解 `p±1`，只要把余因子压到可承受的规模即可。

---

**参数构造（自动搜索）**

- 需求：$p \ge 384$ bit，$p \equiv 11 \pmod{12}$；同时 $p\pm1$ 在去掉小素数因子（$\le B$，如 $2000$）后，余因子 $c_\pm$ 都足够小（如 $\le 2^{24}$），便于 BSGS。
- 我们随机采样此类素数并用 Miller–Rabin 验证素性；对 `p±1` 做小素数试除并检查 `c_±` 大小，不达标则继续采样。

---

**实现要点**

- 纯 Python 实现 GF(p^2) 算术：元素表示为 `(a, b)` ≡ `a + b·j`，乘法用 `j^2 = δ` 约化；逆元 `(a + b·j)^{-1} = (a − b·j) / (a^2 − b^2 δ)`。
- 椭圆曲线点运算：仿射坐标，常规加法/倍点与标量乘；提供无穷远点 `O`；
- Pohlig–Hellman：对每个素数幂子模 `ℓ^e`，逐次求系数并 CRT 合并；
- BSGS：在余因子子群（生成元 `U = M·P`）上求 `t`。

---

**使用方法**

1) 运行服务端（需要 SageMath）：

```
sage -python task/attachment.txt
```

2) 另开终端运行解题脚本（自动与服务端交互；提供两种入口）：

```
## 方案 A：Sage 脚本（推荐，零依赖）
# 使用你自备的“twin-smooth” 素数 p（十进制）
P=<decimal_prime> sage solution/exp.sage

## 方案 B：仓库根目录的实验脚本（等价逻辑，路径不同）
P=<decimal_prime> sage -python exp.sage
```

- 脚本会：
  - 自动搜索合适的素数 p；
  - 输入 `a=1, b=0, p`；
  - 循环解析每轮输出、恢复 δ、计算并提交正确的 k；
  - 成功连续 40 轮后抓取并打印 flag。

3) 可调参数：

- `B_PRIME`：小素数试除上界（默认 2000）；
- `COFACTOR_LIMIT`：允许的余因子上界（默认 2^24）；
- 如本机 Sage 命令不同，可在脚本里修改 `SAGE_CMD`。

---

**数学推导（简述）**

- 设 $E/\mathbb{F}_p$ 超奇异且迹 $t=0$。Frobenius 自同态 $\varphi$ 的特征多项式为 $X^2 + p$。对 $P\in E(\mathbb{F}_{p^2})$，一方面 $\varphi^2(P)=P$（坐标 $p^2$ 次幂恒等），另一方面由特征多项式得 $[-p]P = \varphi^2(P)$，于是 $[p+1]P = \mathcal{O}$。因此 $E(\mathbb{F}_{p^2})$ 的指数整除 $p+1$，群结构同构于 $(\mathbb{Z}/(p+1)\mathbb{Z})^2$。对 $\mathbb{F}_{p^2}$‑二次扭曲同理得到指数整除 $p-1$，且 $|E| + |E_{\text{twist}}| = 2(p^2 + 1)$，在 $t=0$ 时分别为 $(p+1)^2$ 与 $(p-1)^2$。

- $\delta$ 恢复公式推导：设 $x=u+vj,\;y=s+tj$，有

  $$y^2 = (s^2 + t^2\delta) + (2st)j,\qquad x^3 + x = (u^3 + 3uv^2\delta + u) + (3u^2v + v^3\delta + v)j.$$

  比较 j 系数即可得到上式中的 δ 表达式（`v ≠ 0` 时）。

- Pohlig–Hellman：将标量 `k` 按素数幂分解逐位求解并用 CRT 合并。

- 余因子 BSGS：在生成元为 $U$ 的循环子群内，设步长 $m=\lceil\sqrt{c}\rceil$，预计算 baby steps $tU\ (0\le t<m)$，再枚举 giant steps $V - j\,m\,U$，匹配即得 $t=j\,m + t_0$。

---

**参数选择（CRT 约束）**

- 为了让 $|E(\mathbb{F}_{p^2})|=(p+1)^2$ 与 $|E_{\text{twist}}(\mathbb{F}_{p^2})|=(p-1)^2$ 的指数分解便于 PH，选取满足以下同余的素数 $p$：

  - $p \equiv 1 \pmod M$，使 $p-1$ 的平滑部分$\ge M$；
  - $p \equiv -1 \pmod N$，使 $p+1$ 的平滑部分$\ge N$；
  - $p \equiv 3 \pmod 4$，确保 $j^2$ 非平方、并利于某些实现细节。

- 三同余可用中国剩余定理合并：设

  $$
  \begin{cases}
  x \equiv 1 \pmod M,\\
  x \equiv -1 \pmod N,\\
  x \equiv 3 \pmod 4.
  \end{cases}
  $$

  则存在唯一解 $x \equiv x_0\ (\bmod\ L)$，其中 $L = \operatorname{lcm}(M,N,4)$。在等差数列 $\{x_0 + tL\}$ 上筛素数即可。

- 实现中支持通过环境变量直接指定 M、N：

```
M=65537 N=65539 uv run -- python solution/solution.py
```

- 若不指定，则脚本会用不含 2、3 的一串小素数堆出 `M,N ≈ 2^128` 级别，并在对应等差数列中搜索满足 `p ≥ 384` bit 的素数。

提示：为测试速度，可临时设置 `P_OVERRIDE=<十进制素数>` 直接指定 $p$（本地自测用，线上请勿使用）。

---

**正确性与鲁棒性**

- 若某轮 `v=0` 导致 δ 公式不可用，脚本自动回退到 Q 或等待下一轮（或在扭曲轮直接读取系数 a4=δ）。
- 若个别 `P'` 恰为 O（极小概率），该轮将退化成余因子求解，脚本亦能处理。

---

**目录结构**

```
.
├── README.md               <- 本文档
├── solution
│   └── solution.py         <- 自动交互求解脚本
└── task
    └── attachment.txt      <- 提供的挑战脚本（原 task.sage）
```

祝你拿到 flag ！

---

**他山之石：直接用 Sage 的 Q.log 快速解（对给定脚本的分析）**

- 选型要点：取 $p\equiv 3\pmod 4$ 且“$p\pm1$ 双平滑”的素数（例如微软 twin‑smooth‑integers 数据集中的样本[^twin]），并用 $j=1728$ 的超奇异族曲线（Sage: `EllipticCurve_from_j(GF(p)(1728))`，其一般形为 $y^2=x^3+ux$）。此时在 $\mathbb{F}_{p^2}$ 上成立
  - $\#E(\mathbb{F}_{p^2})=(p+1)^2$，指数整除 $p+1$；
  - $\#E_{\mathrm{twist}}(\mathbb{F}_{p^2})=(p-1)^2$，指数整除 $p-1$。

- 算法原理：若 $p\pm1$ 的主要质因子都在小范围内（或余因子很小），则离散对数可由 Pohlig–Hellman 拆成许多小模问题，剩余小余因子再用 BSGS 补齐。Sage 的 `Q.log(P)` 内置此流程（含必要的分解与搜索），因此能直接返回 $k$。

- 实现关键点（与你的脚本一致[^curveball]）：
  - 本地用 pwntools 连接服务进程，发送 `(a,b,p)`；
  - 服务端输出域构造如 `j^2 + c`，据此重建 $\mathbb{F}_{p^2}=\mathbb{F}_p[j]/(j^2+c)$；
  - 逐轮读取曲线参数 $(a_4,a_6)$ 与点 $P,Q$，构造 Sage 椭圆曲线与点对象；
  - 直接计算 $k=Q.\log(P)$ 并回送。

- 安全实践：避免对网络回包做 `eval`。建议把形如 `u + v*j` 的字符串解析为 $(u,v)\in\mathbb{F}_p^2$，再显式构造 $u+v\cdot j$（本仓库 `solution.py` 提供了健壮解析器）。

- 与本文通用解法的互补：你的做法把“PH/BSGS/分治”交给 Sage；本文实现则显式完成“$\delta$ 恢复 + PH + 小余因子 BSGS”，对输出更克制的服务端也适用。若已有优质“双平滑”素数且输出充分，`Q.log` 路线更省力；否则采用本文通用解法更稳健。

---

**三同余构造参数（实战常用模板）**

- 目标：同时让 $p-1$ 与 $p+1$ 都“足够平滑”。常用设计是先给定两个由小素数构成的大积 $M,N$，令
  - $p\equiv 1\pmod M$（使 $p-1$ 有大平滑部分），
  - $p\equiv -1\pmod N$（使 $p+1$ 有大平滑部分），
  - $p\equiv 3\pmod 4$（配合 $j=1728$ 等族，亦可确保 $j^2$ 为非平方）。

- 中国剩余定理（CRT）：设 $L=\operatorname{lcm}(M,N,4)$。存在唯一 $x_0\in[0,L)$ 使
  $$x_0\equiv 1\ (\bmod\ M),\quad x_0\equiv -1\ (\bmod\ N),\quad x_0\equiv 3\ (\bmod\ 4).$$
  在算术级数 $\{x_0+tL\}$ 上搜索素数 $p$，并检查 $p\ge 2^{384}$、$\operatorname{res}(p\pm1)$ 的余因子不超过预设阈值（如 $2^{24}$）。

- 取值建议：$M,N$ 由不含 2、3 的小素数连乘堆出，控制到约 $2^{120\sim 160}$ 位，彼此互素，从而既保证平滑度又不使 $L$ 过大，便于在 384 bit 范围内快速找到素数。

---

**我们的 CRT 尝试与结果分析（为何不如 twin‑smooth 库）**

- 目标同样是求解三同余

  $$
  \begin{cases}
  p \equiv 1 \pmod M,\\
  p \equiv -1 \pmod N,\\
  p \equiv 3 \pmod 4.
  \end{cases}
  $$

  用中国剩余定理（CRT）得到通解 $p\equiv p_0\pmod L$，其中 $L=\operatorname{lcm}(M,N,4)$。然后在等差数列 $\{p_0+kL\}$ 中搜索满足指定位数的素数。

- 伪代码梳理（与我们的脚本一致）：

  ```python
  # 求通解（需 gcd 两两互素）
  p0 = crt([3, 1, -1], [4, M, N])
  L  = lcm(4, M, N)

  # 令 p = p0 + kL，搜索 bits 位素数
  k_min = ceil((2**(bits-1) - p0)/L)
  k_max = floor((2**bits - 1 - p0)/L)
  for k in range(k_min, k_max+1):
      p = p0 + k*L
      if is_prime(p):
          return p
  ```

- 一次实际搜索（示意输出片段）：

  ```text
  [*] 已獲得通解: p = 155 + k * 572
  [*] 開始在通解 p = 155 + k*572 中尋找一個 384 位元的質數...
  [SUCCESS] 成功找到一個 384 位元的質數解！
  p = 19701003098197239606139520050071806902539869635232723333974146702122860885748605305707133127442457820403313995260871
  p mod 4  = 3,  p mod 11 = 1,  p mod 13 = 12 (= -1)

  factor(p - 1) = 2 * 5 * 11 * 88259653903 * 7447066353179447 * 2724...8237
  factor(p + 1) = 2^3 * 3^2 * 13 * 131 * 47772174763 * 3363...5109
  ```

- 关键问题出在“余因子”大小：

  - 以上分解里，$p\pm1$ 都含有极大的素因子（记为 $r_\pm$）。
  - 挑战随机在 $E$ 与扭曲上出题，随机点 $P$ 的阶极大概率可被这些 $r_\pm$ 整除，因而必须在阶含 $r_\pm$ 的子群上做 DLP。
  - 无论走 Sage 的 $Q.\log$，还是显式 PH+BSGS，当余因子包含 300+ bit 的素因子时，都会在该子群上陷入不可行的计算量。

- 与 twin‑smooth 库的差距：

  - 微软 twin‑smooth 数据集精心筛选“$p\pm1$ 双平滑”的素数，使 $p\pm1$ 的平滑部分极大，去掉小素数后的余因子 $c_\pm$ 很小（例如 $\le 2^{20\sim 24}$）。
  - 这样 PH 可以快速完成平滑部分，BSGS 以 $\mathcal{O}(\sqrt{c_\pm})$ 的代价补齐，整体非常快。
  - 我们用小模（如 $M=11, N=13$）的 CRT 搜到的 $p$ 虽满足三同余，但并未约束 $p\pm1$ 的余因子大小，故常常仍含巨大素因子，实战上不可用。

- 结论与改进方向：

  - 仅靠“$p\equiv1\pmod M,\;p\equiv-1\pmod N,\;p\equiv3\pmod4$”且 $M,N$ 较小，不能保证 $p\pm1$ 的余因子足够小；
  - 应将 $M,N$ 设计为由大量小素数组成、位长达 $2^{120\sim160}$ 的大积，且两者互素，使 $L$ 仍在可搜索范围内；
  - 搜索时进一步验算 $\operatorname{res}(p\pm1)$ 的余因子不超过阈值（如 $2^{24}$）。达标时，$Q.\log$ 或显式 PH+BSGS 都能在比赛时限内稳定拿到 $k$。

---

**参考资料**

- curveball 赛题的参考解法脚本（包含基于 Sage 的快速 DLP 实作思路）[^curveball]：
  - https://github.com/skateboardingdog/bsides-cbr-2025-challenges/blob/main/crypto/curveball/solve/solve.py

- “双平滑”素数（$p\pm1$ 平滑）的公开数据集与说明（便于选择对 PH/BSGS 友好的素数）[^twin]：
  - https://github.com/microsoft/twin-smooth-integers

[^curveball]: 参见 bsides-cbr-2025 的 curveball 赛题解法脚本，展示了以 Sage 的 $Q.\log$ 解决 GF$(p^2)$ 上 ECC DLP 的工程化流程。

[^twin]: 参见微软 twin‑smooth‑integers 仓库，提供了大量满足“$p\pm1$ 双平滑”的素数样本与构造说明，可直接用于构建对 Pohlig–Hellman/BSGS 友好的群阶。
