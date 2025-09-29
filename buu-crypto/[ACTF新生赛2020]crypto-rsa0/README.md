# [ACTF 新生赛 2020] crypto-rsa0 Write-up

## 题目概览
- 挑战文件：`challenge.zip`
- 附加提示：`hint.txt`，内容为“怎么办呢，出题人也太坏了，竟然把压缩包给伪加密了！”
- 目标：恢复隐藏在 RSA 加密流程中的 `FLAG`

提示中的“伪加密”暗示压缩包并非真正使用密码学手段加密，而是通过 ZIP 标头上的标志位欺骗解压程序。这成为破解的切入点。

## 初始尝试
1. **列出压缩包内容**
   ```bash
   unzip -l challenge.zip
   ```
   输出显示压缩包包含 `challenge/output` 与 `challenge/rsa0.py` 两个文件，其中 `rsa0.py` 在常规解压时会提示需要密码。

2. **直接解压**
   ```bash
   unzip challenge.zip
   ```
   过程中提示 `challenge/rsa0.py` 需要密码，验证了伪加密的存在。

3. **读取未加密文件**
   `challenge/output` 已成功解压，内容为三行十进制大整数，对应 RSA 的 $p$、$q$、$c$（ciphertext）。

## ZIP 伪加密定位与修复
ZIP 文件头中的第 0x06-0x07 字节为 general purpose bit flag。若最低位为 `1` 则表示文件启用传统 PKZIP 密码。利用 `zipinfo -v challenge.zip` 可确认 `challenge/rsa0.py` 的该标志被设置为加密，但这只是伪装。

### 修改思路
1. 读取整个 ZIP 文件为字节数组。
2. 根据 `zipinfo` 给出的 local header 偏移（0x16d），将 general purpose bit flag 清零。
3. 同时修改 central directory 中对应文件条目的同一标志，确保解压工具不会再次拒绝。

### 实际操作
```python
with open('challenge.zip', 'rb') as f:
    data = bytearray(f.read())

local_offset = 0x16d  # 来自 zipinfo 报告
assert data[local_offset:local_offset+4] == b'PK\x03\x04'
# 清除 local header 的 general purpose bit flag
data[local_offset+6:local_offset+8] = b'\x00\x00'

# 再遍历 central directory，将同一标志清零
sig = b'PK\x01\x02'
pos = data.find(sig)
while pos != -1:
    name_len = int.from_bytes(data[pos+28:pos+30], 'little')
    extra_len = int.from_bytes(data[pos+30:pos+32], 'little')
    comment_len = int.from_bytes(data[pos+32:pos+34], 'little')
    name = data[pos+46:pos+46+name_len]
    if name == b'challenge/rsa0.py':
        data[pos+8:pos+10] = b'\x00\x00'
        break
    pos = data.find(sig, pos + 46 + name_len + extra_len + comment_len)

with open('challenge_fixed.zip', 'wb') as f:
    f.write(data)
```

修复后的文件命名为 `challenge_fixed.zip`，再次解压即可无密码提取全部内容。

## 恢复 RSA 参数
`challenge/rsa0.py` 揭示了题目逻辑：
- 生成两枚 $512$ 位素数 $p$、$q$
- 使用公钥指数 $e = 65537$
- 将 flag 转整型后执行 $c \equiv \text{flag}^e \pmod{N}$

Python 原始脚本如下（省略 `FLAG` 实值）：
```python
p = getPrime(512)
q = getPrime(512)
N = p * q
e = 65537
enc = pow(flag, e, N)
```

根据 `challenge/output` 提供的数据，我们得到：
$$
\begin{aligned}
p &= 9018588066434206\ldots 210411,\\
q &= 7547005673877738\ldots 740223,\\
c &= 5099620692596101\ldots 49472203390350.
\end{aligned}
$$

有了 $p$ 与 $q$，即可计算
$$N = p \times q,\qquad \varphi(N) = (p-1)(q-1),\qquad d \equiv e^{-1} \pmod{\varphi(N)}.$$ 
随后解密：
$$m \equiv c^d \pmod{N}.$$ 
利用 `long_to_bytes(m)` 将明文整数转回字节串即可得到 flag。

## 最终解密脚本
```python
from Crypto.Util.number import long_to_bytes

p = 9018588066434206377240277162476739271386240173088676526295315163990968347022922841299128274551482926490908399237153883494964743436193853978459947060210411
q = 7547005673877738257835729760037765213340036696350766324229143613179932145122130685778504062410137043635958208805698698169847293520149572605026492751740223
c = 50996206925961019415256003394743594106061473865032792073035954925875056079762626648452348856255575840166640519334862690063949316515750256545937498213476286637455803452890781264446030732369871044870359838568618176586206041055000297981733272816089806014400846392307742065559331874972274844992047849472203390350

N = p * q
phi = (p - 1) * (q - 1)
e = 65537
d = pow(e, -1, phi)
m = pow(c, d, N)
flag = long_to_bytes(m)
print(flag.decode())
```
运行输出：
```
actf{n0w_y0u_see_RSA}
```

## 经验小结
- 遇到“伪加密”类 ZIP 时，应检查 general purpose bit flag，是常见 CTF 小技巧。
- RSA 题目若直接给出素数或可因其他方式获得素数，即可直接逆向计算私钥。
- 保留尝试过程与失败信息有助于 analysis 与未来参考。
