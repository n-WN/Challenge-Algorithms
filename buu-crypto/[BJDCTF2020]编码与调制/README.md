# BJDCTF2020 编码与调制 Write-up

## 题目回顾
- 压缩包内提供密文串 `2559659965656A9A...` 以及提示图片，图片展示同一串比特在 `NRZ`、`Manchester`、`差分 Manchester` 三种编码下的波形。
- PNG 中绿色波形对应差分 Manchester，说明真正的比特信息是通过该编码隐藏。

## 信息抽取过程
1. 先观察十六进制串只包含 `2,5,6,9,A` 五种符号。将其视作十六进制数字后转为二进制，得到的 4-bit 块分别是 `0010,0101,0110,1001,1010`，每个块都拥有两次跳变，符合 Manchester 半比特的特点。
2. 以字符串整体拼接的二进制序列记为 $b$。尝试分别跳过 $0\sim3$ 位，使得截断后的序列按 2 位分组仅出现 `01` 或 `10`，这样才能对应差分 Manchester 的低高、高潮形式。实测在偏移 $2$ 时满足条件。
3. 差分 Manchester 下“0”与“1”的判决依赖电平变化方式。与题图对照，可确定 `01 \mapsto 0`、`10 \mapsto 1`，从而恢复逻辑比特串 $c$。
4. 得到的比特长度为 175，非 $8$ 的倍数，说明采样丢失了左侧的同步位。补上一个前导 $0$（即在 $c$ 前加 $8 - (|c|\bmod 8)$ 个 $0$），就能整齐拆分为字节。
5. 按 ASCII 还原得到明文 `BJD{DifManchestercode}`。

## 关键脚本
详细实现位于 `solution/solution.py`，核心步骤概括如下：

```python
pairs = manchester_pairs(bit_stream)  # 自动寻找能全部落在 {01,10} 的相位
bit_string = ''.join('0' if p == '01' else '1' for p in pairs)
if len(bit_string) % 8:
    bit_string = '0' * (8 - len(bit_string) % 8) + bit_string
plaintext = bytes(int(bit_string[i:i+8], 2) for i in range(0, len(bit_string), 8))
```

## Flag
`BJD{DifManchestercode}`
