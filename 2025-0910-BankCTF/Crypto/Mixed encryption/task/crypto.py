class Session:
    def __init__(self):
        key = RSA.generate(1024)
        self.n = key.n
        self.e1 = 65537
        self.e2 = 17
        self.token = base64.urlsafe_b64encode(secrets.token_bytes(12)).decode()
        self.token_used = False  
        self.answer_attempted = False  
        self.aes_key = get_random_bytes(16)
        self.secret = base64.urlsafe_b64encode(secrets.token_bytes(12)).decode()
        self.cipher1_b64, self.c2a_b64, self.c2b_b64 = self._make_challenge()

    def _make_challenge(self) -> Tuple[str, str, str]:
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
