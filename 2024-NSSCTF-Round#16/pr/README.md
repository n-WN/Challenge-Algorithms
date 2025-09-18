# 题目分析

这是一个基于 **RSA** 密码体制的变种问题。我们来梳理一下题目给出的信息和加密流程：

1.  **密钥生成**:
    * 选取了三个 512 位的素数：`prime_p`、`prime_q`、`prime_r`。
    * 构造了两个 RSA 模数 (modulus)：
        * $n_1 = \text{prime_p} \cdot \text{prime_q}$
        * $n_2 = \text{prime_q} \cdot \text{prime_r}$
    * 最关键的一点是，这两个模数 **共享一个公共的素数因子** `prime_q`。
    * 公钥指数 (public exponent) $e$ 是一个给定的常数 `31413537523`。

2.  **加密过程**:
    * 明文 `plaintext` 是由 flag 和随机字符填充到 100 字节后，转换为一个大整数 `message`（记为 $m$）。
    * 断言 `assert message < (1 << 1024)` 告诉我们 $m$ 是一个小于 1024 比特的整数。确切地说，100 字节是 800 比特，所以 $m < 2^{800}$。
    * 明文 $m$ 被加密了两次：
        * $c_1 = m^e \pmod{n_1}$
        * $c_2 = m^e \pmod{n_2}$

3.  **已知信息**:
    * 我们得到了两个密文 $c_1$ 和 $c_2$。
    * 我们还直接得到了两个素数 `prime_p` 和 `prime_r`。
    * 我们不知道 `prime_q`、`n1`、`n2` 和明文 `m`。

**目标**：恢复出原始明文 `message`，从而得到 flag。

---

## 核心漏洞与解题思路

常规的 **共模攻击 (Common Modulus Attack)** 指的是两个不同的 $e$ 加密同一个 $m$ 到同一个 $n$。而常规的 **共因子攻击 (Common Factor Attack)** 指的是我们已知两个模数 $n_1$ 和 $n_2$，通过计算 $\text{gcd}(n_1, n_2)$ 来直接求出公共因子 $q$。

本题的情况介于两者之间，但更为简单。虽然我们不知道 $n_1$ 和 $n_2$ 无法直接求最大公约数，但我们已知构成它们的一部分素数 $p$ 和 $r$。这使得我们可以绕过求解 $q$ 的过程，直接恢复明文。

**核心思路**如下：
1.  我们有两个关于 $m^e$ 的同余方程。
2.  第一个方程 $c_1 \equiv m^e \pmod{p \cdot q}$ 隐含了 $c_1 \equiv m^e \pmod p$。
3.  第二个方程 $c_2 \equiv m^e \pmod{q \cdot r}$ 隐含了 $c_2 \equiv m^e \pmod r$。
4.  由于我们已知 $p$ 和 $r$，我们可以分别在这两个模环境下进行 RSA 解密，得到 $m \pmod p$ 和 $m \pmod r$ 的值。
5.  一旦我们得到了 $m$ 关于两个互素的模数 $p$ 和 $r$ 的余数，我们就可以使用**中国剩余定理 (Chinese Remainder Theorem, CRT)** 来恢复出 $m \pmod{p \cdot r}$ 的值。
6.  根据题目信息，$m < 2^{800}$，而模数 $p \cdot r$ 是一个 $512+512=1024$ 比特的数，即 $p \cdot r \approx 2^{1024}$。由于 $m < p \cdot r$，那么通过 CRT 恢复出来的值就是 $m$ 本身。

---

## 数学推理与攻击路径

让我们一步步进行详细的数学推导。

### 1. 符号定义

* $p, q, r$: 三个 512 比特的素数。
* $e$: 公钥指数。
* $m$: 原始明文消息（大整数）。
* $n_1 = p \cdot q$, $n_2 = q \cdot r$: 两个 RSA 模数。
* $c_1, c_2$: 两个密文。

我们已知 $p, r, e, c_1, c_2$，目标是求 $m$。

### 2. 从同余方程中提取信息

给定的加密方程是：
$$c_1 \equiv m^e \pmod{n_1} \implies c_1 \equiv m^e \pmod{p \cdot q}$$
$$c_2 \equiv m^e \pmod{n_2} \implies c_2 \equiv m^e \pmod{q \cdot r}$$

根据同余的性质，如果一个数对模 $ab$ 同余，那么它也一定对模 $a$ 和模 $b$ 分别同余。因此，我们可以从上述两个方程中推导出：

1.  从第一个方程，我们可以得到关于模 $p$ 的关系：
    $$c_1 \equiv m^e \pmod p$$
2.  从第二个方程，我们可以得到关于模 $r$ 的关系：
    $$c_2 \equiv m^e \pmod r$$

### 3. 分别在模 $p$ 和模 $r$ 的环境下解密

我们现在有了两个独立的、规模更小的 RSA 问题。

* **对于模 $p$**:
    我们有 $c_1 \equiv m^e \pmod p$。为了解出 $m \pmod p$，我们需要计算对应的私钥指数 $d_p$。根据欧拉定理，私钥指数 $d_p$ 满足：
    $$d_p \equiv e^{-1} \pmod{\phi(p)}$$
    因为 $p$ 是素数，所以 $\phi(p) = p - 1$。于是：
    $$d_p = \text{inverse}(e, p-1)$$
    得到 $d_p$ 后，我们就可以计算出 $m \pmod p$：
    $$m_p \equiv m \pmod p \equiv c_1^{d_p} \pmod p$$

* **对于模 $r$**:
    同理，我们有 $c_2 \equiv m^e \pmod r$。计算对应的私钥指数 $d_r$：
    $$d_r \equiv e^{-1} \pmod{\phi(r)}$$
    因为 $r$ 是素数，所以 $\phi(r) = r - 1$。于是：
    $$d_r = \text{inverse}(e, r-1)$$
    得到 $d_r$ 后，我们就可以计算出 $m \pmod r$：
    $$m_r \equiv m \pmod r \equiv c_2^{d_r} \pmod r$$

### 4. 使用中国剩余定理 (CRT) 合并结果

现在我们得到了一个关于 $m$ 的同余方程组：
$$
\begin{cases}
m \equiv m_p \pmod p \\
m \equiv m_r \pmod r
\end{cases}
$$
由于 $p$ 和 $r$ 是两个不同的巨大素数，它们必然互素，即 $\text{gcd}(p, r) = 1$。因此，根据中国剩余定理，在模 $p \cdot r$ 的范围内，这个方程组有唯一解。

我们可以通过扩展欧几里得算法或者直接套用公式来求解。解为：
$$m \equiv m_p + p \cdot [ (m_r - m_p) \cdot p^{-1} \pmod r ] \pmod{p \cdot r}$$
这里 $p^{-1} \pmod r$ 是 $p$ 对模 $r$ 的乘法逆元。

计算出的这个解，我们称之为 $m_{pr}$，它满足 $0 \le m_{pr} < p \cdot r$。

### 5. 利用明文范围确定唯一解

CRT 告诉我们的是：
$$m \equiv m_{pr} \pmod{p \cdot r}$$
这意味着 $m$ 和 $m_{pr}$ 之间相差 $p \cdot r$ 的整数倍。即，存在一个整数 $k$，使得：
$$m = m_{pr} + k \cdot (p \cdot r)$$

现在，我们利用题目给出的明文大小信息：
* 明文 $m$ 是由 100 字节的字符串转换而来，所以 $m < 256^{100} = (2^8)^{100} = 2^{800}$。
* 模数 $p \cdot r$ 是由两个 512 比特的素数相乘得到，所以 $p \cdot r \approx (2^{512}) \cdot (2^{512}) = 2^{1024}$。

我们比较一下 $m$ 和 $p \cdot r$ 的大小：
$$m < 2^{800} \ll 2^{1024} \approx p \cdot r$$
同时，我们知道 $0 \le m_{pr} < p \cdot r$ 且 $m > 0$。

将这些条件代入方程 $m = m_{pr} + k \cdot (p \cdot r)$：
* 如果 $k=1$ 或更大，那么 $m \ge p \cdot r$，这与 $m \ll p \cdot r$ 矛盾。
* 如果 $k=-1$ 或更小，那么 $m \le m_{pr} - p \cdot r < 0$，这与 $m$ 是正整数矛盾。

因此，唯一可能的整数解就是 **$k=0$**。

这意味着：
$$m = m_{pr}$$
我们通过 CRT 计算出的解 $m_{pr}$ 就是原始的明文 $m$。

---

## 解题步骤与代码实现

总结一下，完整的解题流程如下：

1.  从题目给出的数据中提取 $c_1, c_2, p, r$ 和公钥指数 $e$。
2.  计算模 $p$ 下的私钥指数：`dp = inverse(e, p - 1)`。
3.  计算明文模 $p$ 的余数：`mp = pow(c1, dp, p)`。
4.  计算模 $r$ 下的私钥指数：`dr = inverse(e, r - 1)`。
5.  计算明文模 $r$ 的余数：`mr = pow(c2, dr, r)`。
6.  使用中国剩余定理，根据 `(mp, p)` 和 `(mr, r)` 求解出唯一的 `m`。
7.  将得到的大整数 `m` 转换回字节字符串，即可得到包含 flag 的明文。

### Python 实现代码

```python
from Crypto.Util.number import inverse, long_to_bytes

# 从题目输出中获取这些值
c1 = ...
c2 = ...
p = ...
r = ...
e = 31413537523

# 步骤 1 & 2: 在模 p 环境下解密
phi_p = p - 1
dp = inverse(e, phi_p)
mp = pow(c1, dp, p)

# 步骤 3 & 4: 在模 r 环境下解密
phi_r = r - 1
dr = inverse(e, phi_r)
mr = pow(c2, dr, r)

# 步骤 5: 使用中国剩余定理 (CRT) 求解
# 我们需要求解同余方程组:
# m ≡ mp (mod p)
# m ≡ mr (mod r)
#
# 根据 CRT 公式 m = m1*M1*M1_inv + m2*M2*M2_inv (mod N)
# 在这里 N = p*r, M1 = r, M2 = p
# M1_inv = inverse(r, p)
# M2_inv = inverse(p, r)
#
# term1 = mr * p * inverse(p, r)
# term2 = mp * r * inverse(r, p)
# m = (term1 + term2) % (p * r)
# 这是一个标准的 CRT 实现

def chinese_remainder_theorem(remainders, moduli):
    """
    接收两个列表：余数列表和模数列表，返回 CRT 的唯一解。
    """
    if len(remainders) != len(moduli):
        raise ValueError("输入列表长度必须相等")
    
    N = 1
    for n_i in moduli:
        N *= n_i
        
    result = 0
    for r_i, n_i in zip(remainders, moduli):
        N_i = N // n_i
        # 计算 N_i 在模 n_i 下的逆元
        inv_N_i = inverse(N_i, n_i)
        result = (result + r_i * N_i * inv_N_i) % N
        
    return result

# 使用 CRT 函数求解 m
m = chinese_remainder_theorem([mp, mr], [p, r])

# 步骤 6: 将结果转换回字符串
plaintext_bytes = long_to_bytes(m)
plaintext = plaintext_bytes.decode('utf-8')

print("Recovered message:")
print(plaintext)
```

这段代码实现了上述完整的攻击逻辑，最终可以成功恢复出 flag。