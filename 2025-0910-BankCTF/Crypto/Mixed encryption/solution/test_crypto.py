#!/usr/bin/env python3

import base64
import hashlib
import hmac
import json
import secrets
from Crypto.Cipher import AES
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes

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

class MockSession:
    def __init__(self):
        key = RSA.generate(1024)
        self.n = key.n
        self.e1 = 65537
        self.e2 = 17
        self.token = base64.urlsafe_b64encode(secrets.token_bytes(12)).decode()
        self.aes_key = get_random_bytes(16)
        self.secret = base64.urlsafe_b64encode(secrets.token_bytes(12)).decode()
        self.cipher1_b64, self.c2a_b64, self.c2b_b64 = self._make_challenge()

    def _make_challenge(self):
        nonce = hmac.new(self.aes_key, self.token.encode(), hashlib.sha256).digest()[:12]
        cipher = AES.new(self.aes_key, AES.MODE_CTR, nonce=nonce)
        pt = self.secret.encode()
        ct1 = cipher.encrypt(pt)
        m = int.from_bytes(self.aes_key, "big")
        c2a = pow(m, self.e1, self.n)
        c2b = pow(m, self.e2, self.n)
        klen = (self.n.bit_length() + 7) // 8
        return (
            base64.b64encode(ct1).decode(),
            base64.b64encode(c2a.to_bytes(klen, "big")).decode(),
            base64.b64encode(c2b.to_bytes(klen, "big")).decode(),
        )

def test_attack():
    print("=== 本地测试共模攻击 ===")
    
    # 创建模拟会话
    session = MockSession()
    
    print(f"原始AES密钥: {session.aes_key.hex()}")
    print(f"原始secret: {session.secret}")
    print(f"token: {session.token}")
    
    # 模拟服务器响应
    pub_data = {
        "n": str(session.n),
        "e1": session.e1,
        "e2": session.e2,
        "token": session.token
    }
    
    challenge_data = {
        "cipher1": session.cipher1_b64,
        "cipher2a": session.c2a_b64,
        "cipher2b": session.c2b_b64
    }
    
    print(f"\\nn = {session.n}")
    print(f"e1 = {session.e1}, e2 = {session.e2}")
    
    # 解析数据
    n = int(pub_data["n"])
    e1 = pub_data["e1"]
    e2 = pub_data["e2"]
    token = pub_data["token"]
    
    cipher1 = base64.b64decode(challenge_data["cipher1"])
    cipher2a = int.from_bytes(base64.b64decode(challenge_data["cipher2a"]), "big")
    cipher2b = int.from_bytes(base64.b64decode(challenge_data["cipher2b"]), "big")
    
    print(f"\\ncipher1 (AES加密的secret): {cipher1.hex()}")
    print(f"cipher2a (RSA e1加密的AES密钥): {cipher2a}")
    print(f"cipher2b (RSA e2加密的AES密钥): {cipher2b}")
    
    try:
        # 执行共模攻击
        print("\\n=== 执行共模攻击 ===")
        aes_key_int = common_modulus_attack(cipher2a, cipher2b, e1, e2, n)
        recovered_aes_key = aes_key_int.to_bytes(16, "big")
        
        print(f"恢复的AES密钥: {recovered_aes_key.hex()}")
        print(f"原始AES密钥:   {session.aes_key.hex()}")
        print(f"密钥匹配: {'✓' if recovered_aes_key == session.aes_key else '✗'}")
        
        if recovered_aes_key == session.aes_key:
            # 计算nonce并解密
            nonce = hmac.new(recovered_aes_key, token.encode(), hashlib.sha256).digest()[:12]
            print(f"\\n计算的nonce: {nonce.hex()}")
            
            cipher = AES.new(recovered_aes_key, AES.MODE_CTR, nonce=nonce)
            secret_bytes = cipher.decrypt(cipher1)
            recovered_secret = secret_bytes.decode()
            
            print(f"\\n恢复的secret: {recovered_secret}")
            print(f"原始secret:   {session.secret}")
            print(f"secret匹配: {'✓' if recovered_secret == session.secret else '✗'}")
            
            if recovered_secret == session.secret:
                print("\\n🎉 攻击成功！解密逻辑正确")
                return True
        
    except Exception as e:
        print(f"攻击失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return False

if __name__ == "__main__":
    test_attack()
