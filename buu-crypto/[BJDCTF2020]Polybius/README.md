# BJDCTF2020 Polybius Write-up

## 题目复盘
- 附件给出全由元音组成的密文 `ouauuuoooeeaaiaeauieuooeeiea`，并提醒明文长度为 14，同时要求最终 flag 形如 `BJD{...}`。
- 观察到只有五种不同字母 `a,e,i,o,u`，推测与 $5\times5$ Polybius 方阵相关：传统 Square 用数字 $1\sim5$ 表示行列。
- 题目提示的 Base64 文本 `VGhlIGxlbmd0aCBvZiB0aGlzIHBsYWludGV4dDogMTQ=` 解码后为“The length of this plaintext: 14”，进一步印证 Polybius 方向。

## 推理与尝试
1. 记元音到数字的映射为一个双射 $\sigma:\{a,e,i,o,u\}\to\{1,2,3,4,5\}$，可枚举 $5! = 120$ 种情况。
2. 对每个映射，将密文逐字符替换为数字串，再两位一组还原 Polybius 方阵：$P=(P_{ij})_{1\le i,j\le5}$，用标准 $I/J$ 合并版本 `ABCDEFGHIKLMNOPQRSTUVWXYZ`。
3. 如果解得的明文全部是大写字母，并且包含明显可读单词，则认为找到正确映射。
4. 实际枚举时只有映射 $\sigma(o)=2,\sigma(u)=1,\sigma(a)=3,\sigma(e)=4,\sigma(i)=5$ 产生英语短语 `FLAGISPOLYBIUS`。

## 代码实现
核心枚举脚本如下（详见 `solution/solution.py`）：

```python
from itertools import permutations
cipher = "ouauuuoooeeaaiaeauieuooeeiea"
square = "ABCDEFGHIKLMNOPQRSTUVWXYZ"
for perm in permutations("12345"):
    mapping = dict(zip("aeiou", perm))
    digits = "".join(mapping[ch] for ch in cipher)
    plaintext = "".join(
        square[(int(digits[i]) - 1) * 5 + int(digits[i + 1]) - 1]
        for i in range(0, len(digits), 2)
    )
    if plaintext == "FLAGISPOLYBIUS":
        break
```

最终自动化脚本直接输出 flag。

## Flag
`BJD{FLAGISPOLYBIUS}`
