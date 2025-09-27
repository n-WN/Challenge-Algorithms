#!/usr/bin/env python3

from pwn import *
from Crypto.Util.number import bytes_to_long

# 连接到远程服务器
# context.log_level = 'debug' # 如果需要查看详细的通信过程，可以取消注释
r = remote('c.sk8.dog', 30004)

# 接收欢迎信息
r.recvuntil(b'Welcome to supeRSAnic-v1.0\n')

# 接收并解析 n, e, c
n = int(r.recvline().strip().split(b' = ')[1])
e = int(r.recvline().strip().split(b' = ')[1])
c = int(r.recvline().strip().split(b' = ')[1])

log.info(f"n = {n}")
log.info(f"e = {e}")
log.info(f"c = {c}")

# 暴力破解 PIN
for i in range(1000000):
    # 将数字格式化为 6 位 PIN 字符串，不足的前面补 0
    # 例如: 123 -> "000123"
    pin_guess = f'{i:06d}'
    
    # 将字符串转换为整数 (模拟服务器端的加密过程)
    m_guess = bytes_to_long(pin_guess.encode())
    
    # 使用公钥进行加密
    c_guess = pow(m_guess, e, n)
    
    # 检查我们计算出的密文是否与服务器给出的密文匹配
    if c_guess == c:
        log.success(f"Found PIN: {pin_guess}")
        
        # 找到了正确的 PIN，发送给服务器
        r.sendlineafter(b'PIN: ', pin_guess.encode())
        
        # 接收并打印 FLAG
        flag = r.recvline().decode()
        log.success(f"FLAG: {flag}")
        
        # 成功后退出循环
        break
    
    # 打印进度，避免感觉程序卡死
    if i % 10000 == 0:
        log.info(f"Trying PIN: {pin_guess}")

# 关闭连接
r.close()
