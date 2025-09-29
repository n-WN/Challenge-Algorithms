# HDCTF2019 Together Write-up

## 题目分析
- 两份公钥 `pubkey1.pem`、`pubkey2.pem` 在 OpenSSL 输出中共享同一模数 $n$，但公钥指数分别是 $e_1 = 2333$ 与 $e_2 = 23333$。
- 两个密文 `myflag1`、`myflag2` 均为 Base64，可视为相同明文 $m$ 在不同指数下的密文：$c_1 \equiv m^{e_1} \pmod n$ 与 $c_2 \equiv m^{e_2} \pmod n$。
- 公钥指数互质：$\gcd(e_1,e_2)=1$，因此满足公共模数攻击的前提。

## 攻击过程
1. 读取 PEM，验证模数一致，并提取 $e_1,e_2$。用 Base64 解码得到整数密文 $c_1,c_2$。
2. 用扩展欧几里得算法求 Bezout 系数 $a,b$，使得 $a e_1 + b e_2 = 1$。本题得到 $a=-7781,b=778$。
3. 根据恒等式
   $$c_1^a c_2^b \equiv m^{a e_1} m^{b e_2} \equiv m^{a e_1 + b e_2} \equiv m \pmod n$$
   需要注意当系数为负时要取密文的模逆。
4. 计算组合后的结果并转成 ASCII，即为 flag。

## 关键脚本
`solution/solution.py` 完整实现了上述流程：解析密钥、求解 Bezout、组合密文并输出明文。

## Flag
`flag{23re_SDxF_y78hu_5rFgS}`
