## GPU 暴力破解优化策略（Metal + RSA 模幂）

### 目标与设定
- **PIN 空间**：字母表大小 $B$，长度 $L$。总空间 $\;|\mathcal{S}| = B^L\;$.
- **映射**：对线性索引 $i \in [0, B^L)$，按基数 $B$ 展开为“位”
  $$
  d_k = \left\lfloor \frac{i}{B^{\,L-1-k}} \right\rfloor \bmod B,\quad k=0,\dots,L-1,\quad \text{PIN}[k] = \text{alphabet}[d_k].
  $$
- **消息编码（大端）**：PIN 字节 $p_0\ldots p_{L-1}$ 组成整数
  $$
  m = \sum_{k=0}^{L-1} p_k\,256^{\,L-1-k}.
  $$
- **RSA 校验**：给定 $(n,e,c)$，判断 $m^e \equiv c\pmod n$. 本实现固定 $e=65537=2^{16}+1$，N 为 512-bit（可扩展）。

---

### Montgomery 乘法与快速幂（GPU 侧）
- **参数**：
  - 进制 $\beta = 2^{32}$，小端 32-bit limb（CIOS 变体），$\text{LIMBS}=16\Rightarrow 512$ 位。
  - $R = \beta^{\text{LIMBS}} = 2^{512}$, 预计算 $R^2 \bmod n$ 与 $n_0 = -n^{-1} \bmod 2^{32}$.
- **Montgomery 乘法** $\operatorname{MontMul}(a,b)$: 计算
  $$
  \operatorname{mont}(a,b) = a\,b\,R^{-1} \pmod n,
  $$
  采用 CIOS：逐字乘加 + 消去最低位 + 条件减法；时间复杂度 $\Theta(\text{LIMBS}^2)$。
- **域转换**：
  $$
  a_R = a\,R \bmod n, \quad 1_R = R \bmod n.
  $$
- **$e=65537$ 快速幂**：
  $$
  m^{65537} = m^{2^{16}+1} = \big(\underbrace{((((m^2)^2)\cdots)^2}_{16\,\text{次平方}}\cdot m\big).
  $$
  在 Montgomery 域：
  $$
  \begin{aligned}
  &\text{res} \leftarrow m_R,\\
  &\text{重复 16 次：}\quad \text{res} \leftarrow \operatorname{mont}(\text{res},\text{res}),\\
  &\text{res} \leftarrow \operatorname{mont}(\text{res}, m_R),\\
  &\text{out} \leftarrow \operatorname{mont}(\text{res}, 1_R)\quad(\text{退出 Montgomery 域}).
  \end{aligned}
  $$

---

### Metal 内核设计要点
- **地址空间**：将常量缓冲（$N,R^2,C,n_0$）从 `constant` 拷贝到 `thread` 局部数组，避免地址空间不匹配；中间数组全部为 `thread` 局部，便于寄存器/局部存储优化。
- **原子停止**：使用 `atomic_uint foundFlag` 与单个 `outPin/outIndex`：一旦某工作项命中，CAS 置位并写出 PIN/索引；其它工作项早停。
- **批处理**：一次调度 $N_{\text{batch}}$ 个候选；吞吐 $T \approx \dfrac{N_{\text{batch}}}{t}$. 批量越大，提交/回拷开销占比越小；显存约束下建议 $N_{\text{batch}}\in[2\cdot10^7,5\cdot10^7]$。
- **进度条节流**：主机侧每 $\approx 1\,\text{s}$ 刷新一次，$\text{ETA} \approx \dfrac{N_{\text{remain}}}{T}$.
- **线程组大小**：`threadsPerThreadgroup = min(pso.maxTotalThreadsPerThreadgroup, 1024)`；实际可按设备特性调优（目标是高占用与良好 ALU 利用）。

---

### 主机侧（宿主）职责
- **十进制模式（推荐）**：仅需 $(n,e,c)$ 十进制输入；主机计算：
  $$
  R = 2^{512},\quad R^2 \bmod n,\quad n_0 = -n^{-1} \bmod 2^{32}.
  $$
  然后转换为 16×32-bit 小端 limb 传入 GPU。
- **十六进制模式**：直接传入 `nHex, r2Hex, cHex, n0Hex`（小端，每个 32-bit 为 8 hex，共 16 个拼接，长度 128 hex）。
- **分片与并行**：
  - 总空间 $B^L$；选择窗口 $W$，从 $i_0$ 开始：`start=i0, total=W`。
  - 多进程/多机并行：$i_0 \in \{0, W, 2W, \dots\}$；命中即停。

---

### 正确性与边界
- **字节序一致性**：GPU 使用大端拼装 $m$，与 Python `bytes_to_long` 一致。
- **位宽**：当前 $\text{LIMBS}=16\Rightarrow 512$ 位。若 $n\ge 2^{512}$，需将 $\text{LIMBS}$ 扩展为 24/32，并同步调整所有大整数内核。
- **条件减法**：$\operatorname{mont}$ 末尾保证 $r<n$（$r\ge n$ 时单次减法）。
- **复杂度**：单次 Montgomery 乘 $\Theta(\text{LIMBS}^2)$；幂模 $\approx 18$ 次乘（16 平方 + 2 乘）——常量小，适合 GPU 并行展开。

---

### 性能与扩展建议
- **分块与流水**：$\text{GPU 枚举}\to\text{GPU 幂模}\to\text{命中即停}$。避免回拷所有 PIN，仅回传命中结果。
- **减少分支**：内核无数据依赖分叉；仅在末尾比较与原子写有分支，分歧极小。
- **32-bit Limb**：Apple GPU 上 32-bit 整数 ALU 更高效；64-bit 乘法可能更慢。保持 32-bit 乘加与显式进位传播。
- **常量缓存**：将 $N,R^2,C$ 先从 `constant` 拷贝到 `thread` 局部，减少不同地址空间带来的编译器限制；有条件可尝试 `threadgroup` 存放共享常量（需按设备调试）。
- **向更大 $n$**：把 $\text{LIMBS}$ 参数化，循环按常量展开，或用 `constexpr`/宏生成不同位宽版本；注意寄存器压力与占用的取舍。

---

### 验证与单元测试
- **单点自检**：选定已知 $\text{PIN}$，计算 $m$，在 GPU 内核仅对 $\text{count}=1$ 进行幂模并回传，与 CPU `powmod` 比对：
  $$
  \text{GPU}(m^{65537}\bmod n) \stackrel{?}{=} \text{CPU}(m^{65537}\bmod n).
  $$
- **窗口命中**：针对微型字母表 $B=6$、$L=6\Rightarrow 6^6=46656$，遍历全窗口应能稳定命中（例如 PIN=234055，alphabet="012345"）。

---

### 运行参数设计
- **窗口**：$W\in[2\cdot10^7, 5\cdot10^7]$，$\text{batch}=W$ 或按显存拆分多个 batch。
- **全空间**：$B=100, L=6\Rightarrow 10^{12}$。推荐多进程分片：
  $$
  \text{start} = k\,W,\quad \text{total}=W,\quad k=0,1,2,\dots, \left\lceil\frac{B^L}{W}\right\rceil-1.
  $$
- **停止条件**：命中即停（原子标志），主机终止其余分片。

---

### 备注
- 本实现针对暴力破解优化，未特别硬化侧信道；Montgomery 算法的乘法路径固定，有利于规避分支带来的波动。
- 若部署到更高位宽或不同 GPU，需要重新评估 $\text{LIMBS}$、线程组大小与批量规模对吞吐的影响。
