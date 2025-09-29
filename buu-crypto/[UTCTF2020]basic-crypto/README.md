# [UTCTF 2020] basic-crypto 解题报告

## 题目回顾与初始尝试
下载目录中只给出一个 `attachment.txt`，内容是一整行由空格分隔的 0/1 串。每个分段恰好 $8$ 位，于是首先猜测是逐字节的二进制 ASCII 编码。使用 Python 快速脚本将每个分块按二进制转十进制再映射到字符，得到了首段英文提示：

> Uh-oh, looks like we have another block of text, ... only characters present are A-Z, a-z, 0-9, and sometimes / and +.

提示的字符集合正好对应 Base64 字符集，于是确认第一阶段成功，将剩余串认定为 Base64。

## 阶段一：二进制转 ASCII
考虑任一字节 $b_7b_6\cdots b_0$，其十进制值为
$$
\text{val} = \sum_{i=0}^7 b_i \cdot 2^{7-i},
$$
再将 $\text{val}$ 映射到 ASCII 表即可。批量转换后得到字符串 $S_1$，拆分为提示段 $H$ 与 Base64 数据段 $B$。

## 阶段二：Base64 解码
Base64 本质是将每 $3$ 个字节映射到 $4$ 个可显示字符。对 $B$ 去除换行后执行 `base64.b64decode`，得到新的明文 $S_2$。$S_2$ 由两部分组成：

1. 一段说明文字，指出接下来是恺撒移位，并给出“罗马人物”的暗示。
2. 一段看似随机的字母串，显然是被移位后的密文。

## 阶段三：恺撒位移
恺撒密码满足 $C = (P + k) \bmod 26$，逆向时 $P = (C - k) \bmod 26$。

我编写脚本枚举 $k \in \{0,1,\dots,25\}$，寻找可读英文。结果当 $k = 10$ 时得到通顺句子：“alright, you're almost there! ... a substitution cipher.” 说明第三阶段的密文 $C_1$ 对应明文 $P_1$ 采用左移 $10$ 的恺撒密码。

## 阶段四：单表替换
最后一行仍是替换后的文本。题面提示 flag 形式为 `utflag{...}`，在密文中找到片段 `fdcysn{`. 由此建立映射
$$
\begin{aligned}
 f &\mapsto u,\\
 d &\mapsto t,\\
 c &\mapsto f,\\
 y &\mapsto l,\\
 s &\mapsto a,\\
 n &\mapsto g.
\end{aligned}
$$

将这一部分映射回明文后可见若干高频词片段，例如 `congratulations`、`you` 等。继续利用出现的常见词（如 `the`、`challenge`、`hard`）补全映射，直至全部 22 个字母的映射表构建完毕。最终明文如下：

```
congratulations! you have finished the beginner cryptography challenge. here is a flag for all your hard efforts: utflag{n0w_th4ts_wh4t_i_c4ll_crypt0}. you will find that a lot of cryptography is just building off this sort of basic knowledge, and it really is not so bad after all. hope you enjoyed the challenge!
```

## 自动化脚本与验证
为复现上述步骤，编写了 `solution.py`：

1. `binary_to_ascii`：按字节解析二进制并输出字符串。
2. `caesar_decrypt`：实现 $P = (C - k) \bmod 26$ 的通用函数。
3. `substitution_decrypt`：应用推导出的单表映射。
4. `solve()`：串联三阶段并用正则提取 flag。

运行 `python3 solution.py`，脚本打印全部中间文本并输出最终 flag：

```
Flag: utflag{n0w_th4ts_wh4t_i_c4ll_crypt0}
```

## 总结
- 题目依次考察二进制 ASCII、Base64、恺撒移位、单表替换四个基础密码环节。
- 各阶段之间的提示层层递进，善用提示可以迅速定位算法。
- 单表替换的突破口来自 flag 模板与常见英文词频，结合频率分析即可完成映射。

最终 flag 为 $\texttt{utflag\{n0w_th4ts_wh4t_i_c4ll_crypt0\}}$。
