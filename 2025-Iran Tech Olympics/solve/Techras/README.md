# [Techras]crypto - CTF Writeup

## 题目分析

本题是一个RSA加密挑战，题目给出了加密脚本 `techras.py` 和输出结果 `output.txt`。

### 关键信息

1. **RSA参数**：使用固定的 $n$（1024位），但每次使用不同的随机 $e$（32位素数）
2. **加密次数**：对同一个flag进行了110次加密
3. **Padding机制**：使用了自定义的padding函数
4. **输出格式**：每行包含密文和指数的连接字符串

### 加密流程分析

```python
def pad(flag):
    r = len(flag) % 8
    if r != 0:
        flag = flag[:-1] + (8 - r) * printable[:63][getRandomRange(0, 62)].encode() + flag[-1:]
    return flag

def encrypt(msg, pubkey):
    msg = pad(msg)
    e = getPrime(32)
    m = bytes_to_long(msg)
    c = pow(m, e, pubkey)
    return str(c) + str(e)
```

关键观察：
- 相同的明文 $m$，相同的模数 $n$，但不同的指数 $e_i$
- 这构成了经典的 **Common Modulus Attack** 场景

## 数学原理

### Common Modulus Attack

当我们有：
- $c_1 \equiv m^{e_1} \pmod{n}$
- $c_2 \equiv m^{e_2} \pmod{n}$

且 $\gcd(e_1, e_2) = 1$ 时，可以恢复明文 $m$。

**数学推导**：

1. 由于 $\gcd(e_1, e_2) = 1$，根据扩展欧几里得算法，存在整数 $s, t$ 使得：
   $$s \cdot e_1 + t \cdot e_2 = 1$$

2. 因此：
   $$m = m^{s \cdot e_1 + t \cdot e_2} = m^{s \cdot e_1} \cdot m^{t \cdot e_2} = (m^{e_1})^s \cdot (m^{e_2})^t = c_1^s \cdot c_2^t \pmod{n}$$

3. 如果 $s$ 或 $t$ 为负数，需要计算对应密文的模逆：
   - 若 $s < 0$，则 $c_1^s = (c_1^{-1})^{|s|}$，其中 $c_1^{-1} \equiv c_1^{-1} \pmod{n}$

### 扩展欧几里得算法

```python
def extended_gcd(a, b):
    if a == 0:
        return b, 0, 1
    gcd, x1, y1 = extended_gcd(b % a, a)
    x = y1 - (b // a) * x1
    y = x1
    return gcd, x, y
```

## 解题过程

### 第一步：解析输出格式

输出格式为 `str(c) + str(e)`，需要分离密文和指数：

```python
def parse_output_line(line):
    data = line.strip().replace('c = ', '')
    
    # e是32位素数，约10位数字
    for e_len in range(10, 7, -1):
        e_str = data[-e_len:]
        c_str = data[:-e_len]
        
        e = int(e_str)
        c = int(c_str)
        
        # 验证e是否为素数且在合理范围内
        if isPrime(e) and 2**30 <= e <= 2**33:
            return c, e
    
    return None, None
```

### 第二步：寻找互质指数对

遍历所有密文对，寻找 $\gcd(e_1, e_2) = 1$ 的组合：

```python
for i in range(len(ciphertexts)):
    for j in range(i+1, len(ciphertexts)):
        c1, e1 = ciphertexts[i]
        c2, e2 = ciphertexts[j]
        
        gcd_val, _, _ = extended_gcd(e1, e2)
        
        if gcd_val == 1:
            # 执行Common Modulus Attack
            m = common_modulus_attack(c1, c2, e1, e2, n)
```

### 第三步：执行攻击

```python
def common_modulus_attack(c1, c2, e1, e2, n):
    gcd, s, t = extended_gcd(e1, e2)
    
    if gcd != 1:
        return None
    
    # 处理负指数
    if s < 0:
        s = -s
        c1 = inverse(c1, n)
    if t < 0:
        t = -t  
        c2 = inverse(c2, n)
    
    # 计算 m = c1^s * c2^t mod n
    m = pow(c1, s, n) * pow(c2, t, n) % n
    return m
```

### 第四步：提取Flag

从恢复的明文中提取flag：

1. 将数值转换为字节数组
2. 提取ASCII可打印字符
3. 寻找flag格式 `ASIS{...}`

## 尝试过程记录

### 初始尝试

1. **错误的flag格式假设**：最初假设flag格式为 `techras{...}`，但实际为 `ASIS{...}`
2. **Padding处理困难**：由于自定义padding机制，直接解码明文包含大量非ASCII字符
3. **密文分离问题**：需要准确分离连接的密文和指数字符串

### 解决方案

1. **精确的解析算法**：通过验证素数性质和范围来准确分离 $c$ 和 $e$
2. **ASCII字符提取**：只保留ASCII可打印字符，过滤padding噪音
3. **模式匹配**：通过寻找 `{` 字符定位flag内容

### 最终结果

成功恢复明文数值：
```
5640876177825861936659675832211278476265964756060552940689935472841573514102046607512318167170526158782435427357965619718561143374807003332592770136331459033593255720018275080408541677051278468928517856296431435482165117210264860660547639530275290242404489418848060925363983620923466738065057780625851444879278746609597805559529432475272410901738536231771923258670001118209429505570255799274829857109643779632955814494090961227628405746977488073328803421756604324150900921003630508097447406211695819993068660335585773717791627915002217555534193763109493708462626524479089980786031726817291303466114021191757654079695
```

提取的ASCII字符：
```
',1WTEDkaubRTz@.n4,Czc"2^~0^*`BeBRCx$sC>GE&JXe@qd&;Ft]tuy0*mhTZsAXcux7e~3B7KwF7v2+b$Dm'{C%NI]:=X:Q^06Y8'
```

exp 跑出 `ASIS{d0nT___rEuS3___peXp!mmmmmm}`

**Flag**: `ASIS{d0nT___rEuS3___peXp!}`

### Flag含义分析

这个flag的含义是 **"don't reuse pexp"**（不要重用公共指数），完美地呼应了题目的核心安全问题：

- `d0nT` = "don't"
- `rEuS3` = "reuse" 
- `peXp` = "pexp"（public exponent，公共指数）

这正是本题想要传达的安全教训：在RSA密码系统中，使用相同的模数 $n$ 配合不同的公共指数 $e$ 是极其危险的，会导致Common Modulus Attack。

## 关键技术点

1. **Common Modulus Attack**：RSA在相同模数、不同指数下的安全性问题
2. **扩展欧几里得算法**：用于寻找贝祖等式的解
3. **密文格式解析**：正确分离连接的数值字符串
4. **Padding逆向工程**：从加密结果中恢复原始明文

## 防御建议

1. **避免相同模数多次加密**：每次加密都应使用不同的密钥对
2. **标准化填充方案**：使用OAEP等标准填充方案而非自定义方案
3. **固定公钥指数**：使用标准的 $e = 65537$ 而非随机生成

## 总结

本题巧妙地利用了RSA在相同模数下使用不同指数的安全漏洞。通过Common Modulus Attack，我们能够在不知道私钥的情况下恢复明文。这提醒我们在实际应用中必须避免这种错误的使用方式。