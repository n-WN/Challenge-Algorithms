#!/usr/bin/env python3

import base64
import hashlib
import hmac
import json
import socket
from Crypto.Cipher import AES
from Crypto.Util.number import GCD

def extended_gcd(a, b):
    """扩展欧几里得算法"""
    if a == 0:
        return b, 0, 1
    gcd, x1, y1 = extended_gcd(b % a, a)
    x = y1 - (b // a) * x1
    y = x1
    return gcd, x, y

def common_modulus_attack(c1, c2, e1, e2, n):
    """共模攻击恢复明文"""
    gcd, s, t = extended_gcd(e1, e2)
    
    if gcd != 1:
        raise ValueError("e1和e2不互质")
    
    # 处理负指数
    if s < 0:
        c1 = pow(c1, -1, n)
        s = -s
    if t < 0:
        c2 = pow(c2, -1, n)
        t = -t
    
    # 计算 m = c1^s * c2^t mod n
    m = pow(c1, s, n) * pow(c2, t, n) % n
    return m

def send_command(sock, command):
    """发送命令并接收响应"""
    sock.send((command + "\n").encode())
    import time
    time.sleep(0.2)  # 等待响应
    
    # 多次接收数据以确保获取完整响应
    response_parts = []
    sock.settimeout(1.0)
    try:
        while True:
            part = sock.recv(1024).decode()
            if not part:
                break
            response_parts.append(part)
            if part.endswith('\n') or '}' in part:
                break
    except socket.timeout:
        pass
    finally:
        sock.settimeout(None)
    
    response = ''.join(response_parts).strip()
    print(f"> {command}")
    print(response)
    
    # 提取JSON部分
    if "{" in response and "}" in response:
        start = response.find("{")
        end = response.rfind("}") + 1
        json_str = response[start:end]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}")
            print(f"JSON字符串: {json_str}")
    return None

def main():
    HOST = "103.213.97.75"
    PORT = 59929
    
    # 连接服务器
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((HOST, PORT))
        
        # 接收欢迎信息
        welcome = sock.recv(4096).decode()
        print(welcome)
        
        # 获取公钥信息
        pub_data = send_command(sock, "GET /pub")
        if not pub_data:
            print("获取公钥失败")
            return
            
        n = int(pub_data["n"])
        e1 = pub_data["e1"]
        e2 = pub_data["e2"]
        token = pub_data["token"]
        
        print(f"n = {n}")
        print(f"e1 = {e1}, e2 = {e2}")
        print(f"token = {token}")
        
        # 获取挑战数据
        challenge_data = send_command(sock, f"GET /challenge {token}")
        if not challenge_data:
            print("获取挑战失败")
            return
            
        cipher1_b64 = challenge_data["cipher1"]
        cipher2a_b64 = challenge_data["cipher2a"]
        cipher2b_b64 = challenge_data["cipher2b"]
        
        # 解码base64
        cipher1 = base64.b64decode(cipher1_b64)
        cipher2a = int.from_bytes(base64.b64decode(cipher2a_b64), "big")
        cipher2b = int.from_bytes(base64.b64decode(cipher2b_b64), "big")
        
        print(f"cipher1 (AES加密的secret): {cipher1.hex()}")
        print(f"cipher2a (RSA e1加密的AES密钥): {cipher2a}")
        print(f"cipher2b (RSA e2加密的AES密钥): {cipher2b}")
        
        # 使用共模攻击恢复AES密钥
        try:
            aes_key_int = common_modulus_attack(cipher2a, cipher2b, e1, e2, n)
            aes_key = aes_key_int.to_bytes(16, "big")
            print(f"恢复的AES密钥: {aes_key.hex()}")
            
            # 计算nonce
            nonce = hmac.new(aes_key, token.encode(), hashlib.sha256).digest()[:12]
            print(f"计算的nonce: {nonce.hex()}")
            
            # 使用AES解密cipher1得到secret
            cipher = AES.new(aes_key, AES.MODE_CTR, nonce=nonce)
            secret_bytes = cipher.decrypt(cipher1)
            secret = secret_bytes.decode()
            print(f"解密得到的secret: {secret}")
            
            # 提交答案
            answer_payload = json.dumps({"token": token, "secret": secret})
            answer_response = send_command(sock, f"POST /answer {answer_payload}")
            
            if answer_response and answer_response.get("ok"):
                flag = answer_response.get("flag")
                print(f"\\n🎉 成功获取flag: {flag}")
            else:
                print("提交答案失败")
                
        except Exception as e:
            print(f"解密过程出错: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
