#!/usr/bin/env python3

from Crypto.Util.number import *
import re

def extended_gcd(a, b):
    """扩展欧几里得算法"""
    if a == 0:
        return b, 0, 1
    gcd, x1, y1 = extended_gcd(b % a, a)
    x = y1 - (b // a) * x1
    y = x1
    return gcd, x, y

def common_modulus_attack(c1, c2, e1, e2, n):
    """Common Modulus Attack - 当gcd(e1,e2)=1时可恢复明文"""
    gcd, s, t = extended_gcd(e1, e2)
    
    if gcd != 1:
        return None
    
    # 如果s或t为负数，需要调整
    if s < 0:
        s = -s
        c1 = inverse(c1, n)
    if t < 0:
        t = -t  
        c2 = inverse(c2, n)
    
    # m = c1^s * c2^t mod n
    m = pow(c1, s, n) * pow(c2, t, n) % n
    return m

def parse_output_line(line):
    """解析输出行，分离密文和指数"""
    # 移除 'c = ' 前缀
    data = line.strip().replace('c = ', '')
    
    # e是32位素数，约10位数字
    # 尝试从10位到8位长度来分离e
    for e_len in range(10, 7, -1):  # 从10位到8位
        try:
            e_str = data[-e_len:]
            c_str = data[:-e_len]
            
            if not e_str or not c_str:
                continue
                
            e = int(e_str)
            c = int(c_str)
            
            # 验证e是否为素数且在合理范围内
            if isPrime(e) and 2**30 <= e <= 2**33:  # 放宽范围
                return c, e
        except:
            continue
    
    return None, None

def extract_flag_from_plaintext(m):
    """从恢复的明文中提取flag"""
    try:
        data_bytes = long_to_bytes(m)
        
        # 直接查找ASIS{...}格式
        try:
            decoded = data_bytes.decode('utf-8')
            # 寻找完整的ASIS{...}格式
            match = re.search(r'ASIS\{[^}]+\}', decoded)
            if match:
                return match.group(0)
        except:
            pass
        
        # 查找ASCII可打印字符中的模式
        ascii_chars = ''.join([chr(b) for b in data_bytes if 32 <= b <= 126])
        
        # 检查是否有完整的ASIS{...}
        match = re.search(r'ASIS\{[^}]+\}', ascii_chars)
        if match:
            return match.group(0)
        
        # 查找任何{...}模式，然后尝试添加ASIS前缀
        match = re.search(r'\{[^}]+\}', ascii_chars)
        if match:
            content = match.group(0)
            return f"ASIS{content}"
            
        return None
    except:
        return None

def solve():
    """主解题函数"""
    # 读取数据
    with open('../task/output.txt', 'r') as f:
        lines = f.readlines()
    
    # 解析n
    n_line = lines[0].strip()
    n = int(n_line.replace('n = ', ''))
    print(f"n = {str(n)[:50]}...")
    print(f"n bit length = {n.bit_length()}")
    
    # 解析所有密文和指数
    ciphertexts = []
    for i, line in enumerate(lines[1:], 1):
        c, e = parse_output_line(line)
        if c is not None and e is not None:
            ciphertexts.append((c, e))
            if i <= 5:  # 显示前几个用于验证
                print(f"c{i}: e={e}")
        else:
            print(f"Failed to parse line {i}: {line.strip()}")
    
    print(f"\n成功解析了 {len(ciphertexts)} 个密文")
    
    # 尝试Common Modulus Attack
    print("\n开始尝试 Common Modulus Attack...")
    
    for i in range(len(ciphertexts)):
        for j in range(i+1, len(ciphertexts)):
            c1, e1 = ciphertexts[i]
            c2, e2 = ciphertexts[j] 
            
            # 检查gcd(e1, e2) = 1
            gcd_val, _, _ = extended_gcd(e1, e2)
            
            if gcd_val == 1:
                print(f"\n找到互质指数对: e1={e1}, e2={e2}")
                print(f"尝试攻击密文对 ({i+1}, {j+1})")
                
                # 执行攻击
                try:
                    m = common_modulus_attack(c1, c2, e1, e2, n)
                    if m:
                        print(f"恢复的明文数值: {m}")
                        
                        # 提取flag
                        flag_candidate = extract_flag_from_plaintext(m)
                        
                        if flag_candidate:
                            print(f"提取的flag: {flag_candidate}")
                            
                            # 验证flag正确性
                            try:
                                test_m = bytes_to_long(flag_candidate.encode('utf-8'))
                                test_c1 = pow(test_m, e1, n)
                                test_c2 = pow(test_m, e2, n)
                                
                                if test_c1 == c1 and test_c2 == c2:
                                    print(f"\n🎉 验证成功！正确的flag: {flag_candidate}")
                                    return flag_candidate
                                else:
                                    print(f"验证失败，继续尝试其他密文对")
                            except:
                                print(f"验证时出错，继续尝试其他密文对")
                        else:
                            # 显示ASCII供参考
                            data_bytes = long_to_bytes(m)
                            ascii_chars = ''.join([chr(b) for b in data_bytes if 32 <= b <= 126])
                            if len(ascii_chars) > 30:
                                print(f"ASCII字符: {ascii_chars[:100]}...")
                        
                except Exception as e:
                    print(f"攻击失败: {e}")
                    continue
    
    print("未能通过Common Modulus Attack恢复flag")
    return None

if __name__ == "__main__":
    flag = solve()
    if flag:
        print(f"\n最终答案: {flag}")
    else:
        print("\n解题失败")