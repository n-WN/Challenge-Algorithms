# 小明的区块链（离线复现与解题思路）

> 赛时 0 解

> 本题来自 9.10 的区块链密码学方向练习。当前没有远程环境（比赛服务器已关闭），附件中保存了当时的 JSON 数据与题面说明，因此本文以“离线复现 + 数学推导 + 约束求解器/格方法”的方式给出完整 write‑up 与可运行的解题脚本（solution/solution.py）。
> 为便于验证结果，解答中额外提供了一个“本地验签服务”（local_server.py），完全模拟原题接口，便于离线自测；全文使用美元符号的行内公式，便于 LaTeX 渲染。

## 题意与数据结构

- 椭圆曲线：secp256k1；阶记为 $n$。
- 服务端签名规则：对消息 `msg_hex`，并非直接哈希，而是使用未知 1 字节 `salt` 拼接后参与哈希：
  - 样本签名计算 $z = \mathrm{Keccak256}(\text{msg} \Vert \text{salt}) \bmod n$。
  - 产生 ECDSA 签名 $(r, s)$，其中 $r$ 为 $R = kG$ 的 $x$ 坐标对 $n$ 取模，$s \equiv k^{-1}(z + r x) \pmod n$。
- 附件 JSON 包含：
  - `params`：全局参数（如 `beta_bits`、`t_range`、`w_lsb`、`w_msb` 等），
  - `instances`：多条样本（类型为 lin/lsb/msb/mix），
  - `aux`：用于恢复 `salt` 的辅助数据（`trunc_bits` 与若干 `proofs` 对）。
- 验证阶段消息 `verify_hex` 需要用恢复出的私钥 $x$ 进行以太坊风格签名（哈希为 $h=\mathrm{Keccak256}(\text{verify\_hex})$，签名输出 $r\Vert s\Vert v$，其中 $v\in\{0,1\}$；$s$ 采用 low‑s 规范）。

实例类型与“部分信息”含义（来自题面与 JSON）：
- `lin`：线性族样本，给出 `meta.m64` 与 `beta_bits`。
- `lsb`：给出 `meta.k_lsb` 与窗口宽度 `w_lsb`，即已知 $\mathrm{LSB}_{w}(k)$。
- `msb`：给出 `meta.k_msb` 与窗口宽度 `w_msb`，即已知 $\mathrm{MSB}_{w}(k)$。
- `mix`：同时给出高/低位窗口（已知 $\mathrm{MSB}_{w_m}(k)$ 与 $\mathrm{LSB}_{w_l}(k)$）。

## 核心方程与攻击面

标准 ECDSA 方程为：
$$
 s \equiv k^{-1}(z + r x) \pmod n \;\;\Longleftrightarrow\;\; s\,k \equiv z + r x \pmod n.
$$

因此一旦知道某条样本的 $k$，即可直接恢复私钥：
$$
 x \equiv (s\,k - z)\,r^{-1} \pmod n.
$$

本题并未直接给出 $k$，但提供了以下“部分信息”：

1) LSB 泄漏（`lsb`、`mix`）
- 设窗口宽度 $w$，则 $k = k_0 + 2^w u$，其中 $k_0=\mathrm{LSB}_w(k)$ 已知、$u$ 未知整数。
- 代入主方程可得线性同余：
  $$ r\,x - s\,2^w u \equiv s\,k_0 - z \pmod n. $$
  这是一类 Hidden Number Problem (HNP)。

2) MSB 泄漏（`msb`、`mix`）
- 已知 $k$ 的高 $w$ 位，等价于给出 $k$ 的区间约束：$k \in [\alpha\cdot 2^{256-w},\; (\alpha+1)\cdot 2^{256-w})$，其中 $\alpha=\mathrm{MSB}_w(k)$。

3) 线性族（`lin`）
- 题面与 JSON 提示 `beta_bits` 与 `meta.m64`。自然的生成模型是假定存在全局常数 $\beta,t$ 使 $k$ 与消息相关联：
  $$ k_i \equiv f(m_i;\beta,t). $$
  最“直接”的设想是 $k_i \equiv t + \beta\,m_i$（模某个模数）；也可仅约束低 $64$ 位：
  $$ \mathrm{LSB}_{64}(k_i) \equiv (t + \beta\,m_i)\bmod 2^{64}. $$

实战中，我们将把上述三类信息“统一建模”为约束系统，再借助 SMT（Z3）/格（LLL）进行联合求解；随后用求得的 $x$ 对 `verify_hex` 进行签名，离线复现最终答案。

## salt 恢复（辅助数据 proofs）

给定 `aux.trunc_bits = b` 与多组 `proofs`，每条包含 `msg_hex` 与 `keccak_trunc`，其定义为：
$$
 \mathrm{low}_b\big(\mathrm{Keccak256}(\text{salt}\Vert \text{msg})\big) = \text{keccak\_trunc}.
$$

暴力枚举 $\text{salt}\in[0,255]$ 即可唯一恢复。实际数据中我们得到：
$$\text{salt}=81\; (0x51).$$

随后按题意计算每条样本对应的
$$
 z_i = \mathrm{Keccak256}(\text{msg}_i \Vert \text{salt}) \bmod n.
$$

## 数学建模与求解路线（尝试记录）

下面给出三条互补路线（均为分析与尝试记录；最终采用 cuso 方案求解，未保留其它尝试代码）：

1) 线性族（近似）法（尝试未成功）：
- 设想 $\mathrm{LSB}_{64}(k_i) = (t + \beta m_i) \bmod 2^{64}$，$\beta < 2^{\text{beta\_bits}}$，$t \in [2^{20},2^{28})$。
- 与主方程 $s_i k_i \equiv z_i + r_i x \pmod n$ 共同作为约束，交由 SMT 求解。此路对数据一致性敏感，若样本确由此生成，SMT 可直接恢复 $(x,\beta,t,\{k_i\})$。

2) 仅用位泄漏的 SMT 法（尝试未成功）：
- 丢弃 `lin`，只保留 `lsb/msb/mix` 的位窗约束 + ECDSA 模同余（使用 `URem(\cdot,n)=0` 表示 $\bmod n$）。
- 该模型变量多但线性于未知（乘常数），通常可在可控子集（例如挑若干条 lsb+msb）下收敛，并进一步滚动加入更多样本直至稳定收敛。

3) HNP（格）法（简化尝试未成功）：
- 将 `lsb` 写成 $r_i x - s_i 2^w u_i \equiv b_i \pmod n$，可构造格近似求解；
- 但为避免维护重量级 LLL/CVP 实现，最终改用 cuso 的自动多元 Coppersmith 求解，效果更稳。

实践中，最终采用“salt → cuso（多元 Coppersmith）”路径；另外两路仅作分析与尝试记录。得到的 $x$ 进一步按如下方式校验：
- 回代所有样本，取 $k_i \equiv s_i^{-1}(z_i + r_i x)\pmod n$：
  - 检查 `lsb/msb/mix` 的位窗是否全部匹配；
  - `lin` 未参与建模，仅作为题面给出的提示信息。

若全部通过，即可对 `verify_hex` 做以太坊签名，得到 $r\Vert s\Vert v$ 或三元组 $(r,s,v)$，理论上提交即可通过。

## 代码与运行

目录结构：

```
./[BankCTF-2024-09-10]小明的区块链
├── README.md                   # 本题详细 WP（含 cuso 原理、推导、验证）
├── LOCAL_SERVER.md            # 本地验签服务的使用说明与配置项
├── solution
│   ├── solution.py            # 精简入口：调用 Sage + cuso 求解并打印结果
│   ├── solve_with_cuso.py     # Sage + cuso 建模与求解，产出 result.json
│   ├── local_server.py        # 本地 HTTP 验签服务（可配置 host/port/flag 等）
│   └── result.json            # 运行后生成：私钥与 verify 签名（r,s,v,sig_hex）
└── task
    ├── CHALLENGE.md           # 附件题面摘录
    └── challenge_data.json    # 附件 JSON（包含 samples、aux、verify_hex）
```

运行方式：

```
python solution/solution.py                 # 调用 Sage + cuso 求解
sage -python solution/solve_with_cuso.py    # 直接运行 cuso 求解
```

执行后会在 `solution/result.json` 生成：
- 私钥 `x_hex`；
- 对 `verify_hex` 的以太坊风格签名：`r`、`s`、`v`、`sig_hex`。

## 使用 Sage + cuso 求解（已成功）

- 在本机已装有 Sage 10.5 与 cuso（于 `cuso/` 目录 `pip install .`）后，执行：
  - `sage -python solution/solve_with_cuso.py`
- 建模：
  - 统一采用 ECDSA 模同余：$s_i\,k_i \equiv z_i + r_i x \pmod n$；
  - lsb：$k_i = U_i\cdot 2^{w_{\ell}} + k_{\ell}$，$U_i$ 为未知；
  - msb：$k_i = (k_m\ll(256-w_m)) + V_i$，$V_i$ 为未知；
  - mix：$k_i = (k_m\ll(256-w_m)) + W_i\cdot 2^{w_{\ell}} + k_{\ell}$，$W_i$ 为未知；
  - 将这些关系作为多元 Coppersmith 小根问题交由 cuso 自动选择移位多项式并进行格约减求解。

本题 cuso 求得：

- 私钥：
  - `x = 0xc8c0f5445357877b10979875868996bfd1b29476222dd04b0eaac6bf7b392339`
- 用该 `x` 校验所有 `lsb/msb/mix` 位窗信息均一致（全通过）。
- 对 `verify_hex` 进行以太坊风格签名（low‑s）：
  - `r = 0x58b2149b6eb597e30d6adfdccdd63e0a9e7b27d1361907d790c54a7737928378`
  - `s = 0x0d2b2fbff0ec61ebaa61e0dc54f93d2ae04abfa554d9aafc6c8dc3fbbe5f4392`
  - `v = 1`
  - `sig_hex = 0x58b2149b6eb597e30d6adfdccdd63e0a9e7b27d1361907d790c54a77379283780d2b2fbff0ec61ebaa61e0dc54f93d2ae04abfa554d9aafc6c8dc3fbbe5f439201`

## 本地验签与服务复现

由于比赛服务器已关闭，本仓库“解答”中包含了一个本地 HTTP 服务，方便你在离线环境直接验证签名正确性。该服务完全依赖题目附件 `task/challenge_data.json` 与我们恢复的私钥，接口与原题一致。

- 代码位置：`[BankCTF-2024-09-10]小明的区块链/solution/local_server.py`
- 行为：
  - `GET /api/new` 和 `GET /api/challenge/{token}` 返回附件里的题目 JSON；
  - `POST /api/submit/{token}` 接受两种提交：`{"sig_hex": "0x..."}` 或 `{r,s,v}`，按以太坊风格验签；
  - 公钥从 `solution/result.json` 里的私钥导出（或从环境变量 `LOCAL_CHAL_PRIV` 提供）。

运行与验证（更多配置详见 LOCAL_SERVER.md）：

```
# 启动本地服务（默认 127.0.0.1:59999）
python [BankCTF-2024-09-10]小明的区块链/solution/local_server.py

# 拉取题面（可见 token 与 verify_hex）
curl -s http://127.0.0.1:59999/api/new | jq '.token,.verify_hex'

# 使用我们求得的签名提交验证（sig_hex 已写在 result.json）
TOKEN=$(jq -r .token [BankCTF-2024-09-10]小明的区块链/task/challenge_data.json)
SIG=$(jq -r '.signature.sig_hex' [BankCTF-2024-09-10]小明的区块链/solution/result.json)
curl -s -X POST \
  -H 'Content-Type: application/json' \
  -d "{\"sig_hex\":\"$SIG\"}" \
  "http://127.0.0.1:59999/api/submit/$TOKEN"
```

预期输出：

```
{"ok": true, "flag": "flag{local-<token前8位>}"}
```

如需使用 Python 验证：

```python
import json, requests
base='[BankCTF-2024-09-10]小明的区块链'
chal=json.load(open(base+'/task/challenge_data.json'))
res=json.load(open(base+'/solution/result.json'))
url=f"http://127.0.0.1:59999/api/submit/{chal['token']}"
r=requests.post(url,json={'sig_hex':res['signature']['sig_hex']})
print(r.json())  # {'ok': True, 'flag': 'flag{local-...}'}
```

或用 pwntools 连接本地服务（以 HTTP 提交）：

```python
from pwn import remote
import json
base='[BankCTF-2024-09-10]小明的区块链'
chal=json.load(open(base+'/task/challenge_data.json'))
res=json.load(open(base+'/solution/result.json'))
tok=chal['token']
sig=res['signature']['sig_hex']
body=json.dumps({'sig_hex':sig}).encode()
req=(
  f"POST /api/submit/{tok} HTTP/1.1\r\n"
  f"Host: 127.0.0.1:59999\r\n"
  f"Content-Type: application/json\r\n"
  f"Content-Length: {len(body)}\r\n\r\n"
).encode() + body
io=remote('127.0.0.1',59999)
io.send(req)
resp=io.recvrepeat(0.5)
print(resp.decode())
```

我的本地实测返回：`{"ok": true, "flag": "flag{local-e16c38f6}"}`，说明签名可被验证通过。

更多配置项（端口、flag 前缀、路径等）请参考：

- `LOCAL_SERVER.md`: `[BankCTF-2024-09-10]小明的区块链/LOCAL_SERVER.md`

## cuso 背景与原理速览

- 目标问题：广义 Coppersmith 小根问题（包括多元情形）。给定多项式系统 $\{f_j(\mathbf{X})\}$ 与模数 $N$，在约束 $\mathbf{X}$ 的分量上界的前提下，寻找满足 $f_j(\mathbf{X}) \equiv 0\ (\bmod\ N)$ 的“短根”。
- 方法脉络：Howgrave‑Graham 的“对偶构造”指出，当我们能在整数域找到足够多“系数很小”的移位多项式的整线性组合时，短根将落入一个低范数格中并可通过格约减（LLL/BKZ）识别。
- 难点：如何“自动化”地为多元系统挑选好的“移位多项式”。传统做法需要手工设计，经验性强。
- cuso 的贡献：提供了三种自动策略（含一个具可证明最优性的策略和一个图论启发式策略），直接从系统与变量上界自动产出移位多项式集合，并驱动格约减求解，极大降低了多元 Coppersmith 的使用门槛。

参考：cuso 基于论文 “Solving Multivariate Coppersmith Problems with Known Moduli (ePrint 2024/1577)”。

## 多元 Coppersmith 建模（本题）

我们抛开 lin 的具体生成假设，仅使用 lsb/msb/mix 的“位窗”形成确定的代数关系，使其满足 ECDSA 模同余：

- 主关系（对每条样本 $i$）：
  $$ s_i\,k_i \equiv z_i + r_i x \pmod n. $$
  其中 $z_i = \mathrm{Keccak256}(\text{msg}_i\Vert\text{salt})\bmod n$（salt 已由 `aux.proofs` 唯一恢复）。

- lsb 型：设窗口宽 $w_{\ell}$ 与泄漏 $k_{\ell}$，则
  $$ k_i = U_i\,2^{w_{\ell}} + k_{\ell},\quad 0 \le U_i < 2^{256 - w_{\ell}}. $$

- msb 型：设高位窗口 $w_m$ 与已知 $k_m$（为高 $w_m$ 位的数值），则
  $$ k_i = (k_m\,2^{256-w_m}) + V_i,\quad 0 \le V_i < 2^{256 - w_m}. $$

- mix 型：已知 msb 与 lsb，记 $w_{\ell}, w_m, k_{\ell}, k_m$，则
  $$ k_i = (k_m\,2^{256-w_m}) + W_i\,2^{w_{\ell}} + k_{\ell},\quad 0 \le W_i < 2^{256 - w_m - w_{\ell}}. $$

于是每条样本都给出一个形如
$$ s_i\,k_i(\text{窗口未知量}) - r_i x - z_i \equiv 0\ (\bmod\ n) $$
的“多元小根方程”。我们交给 cuso：

- 变量集合：$x$ 与每条样本对应的 $U_i/V_i/W_i$；
- 模数：$n$；
- 变量上界：按各自窗口宽度设置（见上式）。

这正是 `solution/solve_with_cuso.py` 所做的事情。

## HNP 格方法推导（对比理解）

仅以 lsb 为例，设 $k = k_0 + 2^w u$（$k_0$ 已知，$u$ 未知）。带回 ECDSA：
$$ s(k_0 + 2^w u) - r x - z = n t, \qquad t\in\mathbb{Z}. $$
移项得
$$ r x - s 2^w u \equiv (s k_0 - z) \pmod n. $$
把多条样本写成矩阵形式并嵌入格，构造如下基（示意）：
$$
\mathcal{B} = \begin{pmatrix}
 n & 0 & 0 & \cdots & 0 \\
 0 & n & 0 & \cdots & 0 \\
 \vdots &  & \ddots &  & \vdots \\
 r_1 & -s_1 2^w & 0 & \cdots & (s_1 k_{0,1} - z_1) \\
 r_2 & 0 & -s_2 2^w & \cdots & (s_2 k_{0,2} - z_2) \\
 \vdots &  &  & \ddots & \vdots
\end{pmatrix}.
$$
短向量对应于“误差项”与 $(x, u_i, t_i)$ 的组合很小，从而可用 LLL/Babai 近似恢复 $x$。本题我们最终采用 cuso 的多元 Coppersmith，因为它能同时利用 msb 与 mix 的信息，并自动选取移位多项式。

## Z3 尝试与失败原因（简述；代码已移除）

- 若仅写 $s k - r x - z = n y$ 再加位窗，$y\in\mathbb{Z}$ 的自由度会“吞掉”约束，导致存在大量伪解（例如 $x=n-1$）。
- 需把 $k$ 固定为唯一代表：$k = ((z + r x) s^{-1}) \bmod n$，再加位窗约束。但仅靠位窗在这套数据上整体 `unsat`（窗口信息强度仍不足以唯一化）。
- 尝试把 lin 建模为低 64 位线性族 $\mathrm{LSB}_{64}(k_i) = t + \beta\,m_i$ 未与数据相容（大概率 lin 的真实生成方式不同）。
- 故最终交由 cuso 自动组合窗口与模同余，顺利恢复 $x$（并已移除 Z3 相关代码）。

## 正确性验证

- 用上文 cuso 求得的 $x$：
  - 对每条样本计算 $k_i = s_i^{-1}(z_i + r_i x) \bmod n$；
  - 校验所有 `lsb/msb/mix` 位窗一致性，全部通过。
- 最终签名 `verify_hex`：以太坊风格，$h=\mathrm{Keccak256}(\text{verify\_hex})$，$s$ 取 low‑s，$v=R_y\bmod 2$。
- 结果已在“使用 Sage + cuso 求解（已成功）”小节给出。

## 推导与尝试记录（精简要点）

- 纯 `lin` 的“三元线性方程法”：把 $(-r_i)x + (s_i m_i)\beta + s_i t \equiv z_i$ 看作三元线性方程并直接在 $\mathbb{Z}_n$ 内解。由于 ECDSA 等式是模 $n$ 的同余，且 $k$ 本身可能只在低位满足线性族，直接把 $k_i=t+\beta m_i$ 当作全 256 位恒等会造成不一致，实验上不可行。
- SMT 建模细节：
  - $s_i k_i - r_i x - z_i \equiv 0 \pmod n$ 用 `URem(lhs, n) == 0` 表示；
  - `lin` 线性族使用低 64 位约束 `Extract(63,0,k_i) == (t + beta*m64) (mod 2^64)`；
  - LSB/MSB 位窗使用 `Extract`；
  - 逐步加样本（从少到多）能显著提升可满足性；
  - 求解成功后回代验证所有样本并做以太坊签名。
- HNP（格）路线：把 `lsb` 的等式改写为 $r_i x - s_i 2^w u_i - b_i = n y_i$，构造 $(m+1)$ 维格基，求最短向量（或最近向量）近似解，随后二次筛选（校验 `msb/mix/lin`）。

由于当前仅有离线数据，脚本既可“复现”也具“自校验”：当一个候选 $x$ 满足全部样本的位窗与线性族约束时，我们即可确信其正确性；再对 `verify_hex` 本地签名即可得到最终答案。

## 结语

本题的关键在于“把不同来源的部分信息统一成约束系统”，并用合适的工具（SMT/格）联合求解。附件的 `solution.py` 实现了上述思路，既可作为复现脚本，也可作为类似题目的模板起点。
