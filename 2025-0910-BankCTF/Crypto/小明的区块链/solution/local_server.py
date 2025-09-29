#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import re
import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler

from Crypto.Hash import keccak


P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
Gx = 55066263022277343669578718895168534326250603453777594175500187360389116729240
Gy = 32670510020758816978083085130507043184471273380659243275938904335757337482424


def inv(a, m=N):
    return pow(a, -1, m)


def p_add(P1, P2):
    if P1 is None:
        return P2
    if P2 is None:
        return P1
    x1, y1 = P1
    x2, y2 = P2
    if x1 == x2 and (y1 + y2) % P == 0:
        return None
    if x1 == x2 and y1 == y2:
        lam = (3 * x1 * x1) * pow(2 * y1, -1, P) % P
    else:
        lam = (y2 - y1) * pow(x2 - x1, -1, P) % P
    x3 = (lam * lam - x1 - x2) % P
    y3 = (lam * (x1 - x3) - y1) % P
    return (x3, y3)


def p_mul(k, P0=(Gx, Gy)):
    k %= N
    if k == 0:
        return None
    Q = None
    A = P0
    while k:
        if k & 1:
            Q = p_add(Q, A)
        A = p_add(A, A)
        k >>= 1
    return Q


def keccak256(b: bytes) -> bytes:
    h = keccak.new(digest_bits=256)
    h.update(b)
    return h.digest()


def verify_eth_sig(pubkey, msg_hex: str, r: int, s: int) -> bool:
    # Verify ECDSA signature with given pubkey Q
    if not (1 <= r < N and 1 <= s < N):
        return False
    Q = pubkey
    # compute h
    h = int.from_bytes(keccak256(bytes.fromhex(msg_hex)), 'big') % N
    w = inv(s)
    u1 = (h * w) % N
    u2 = (r * w) % N
    X = p_add(p_mul(u1), p_mul(u2, Q))
    if X is None:
        return False
    return (X[0] % N) == r


class ChallengeServer(BaseHTTPRequestHandler):
    # Load challenge data on server start
    chal = None
    token = None
    pubkey = None
    cfg = None  # namespace with config

    @classmethod
    def init_data(cls, cfg):
        cls.cfg = cfg
        # challenge json
        chal_path = cfg.chal_path
        with open(chal_path, 'r') as f:
            cls.chal = json.load(f)
        cls.token = cls.chal.get('token')
        # Load recovered x from result.json or env
        res_path = cfg.result_path
        if os.path.exists(res_path):
            with open(res_path, 'r') as f:
                x_hex = json.load(f).get('x_hex')
            x = int(x_hex, 16)
            Q = p_mul(x)
            cls.pubkey = Q
        else:
            # Fallback: parse x from environment or raise
            x_hex = os.environ.get('LOCAL_CHAL_PRIV')
            if not x_hex:
                raise RuntimeError('Missing solution/result.json or LOCAL_CHAL_PRIV for pubkey')
            x = int(x_hex, 16)
            cls.pubkey = p_mul(x)

    def _send_json(self, code: int, obj):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        # /api/new or /api/challenge/{token}
        if self.path == '/api/new':
            return self._send_json(200, self.chal)
        m = re.match(r'^/api/challenge/([0-9a-fA-F]+)$', self.path)
        if m:
            tok = m.group(1)
            if tok != self.token:
                return self._send_json(404, {"ok": False, "error": "invalid token"})
            return self._send_json(200, self.chal)
        return self._send_json(404, {"ok": False, "error": "not found"})

    def do_POST(self):
        m = re.match(r'^/api/submit/([0-9a-fA-F]+)$', self.path)
        if not m:
            return self._send_json(404, {"ok": False, "error": "not found"})
        tok = m.group(1)
        if tok != self.token:
            return self._send_json(404, {"ok": False, "error": "invalid token"})
        # read body
        try:
            length = int(self.headers.get('Content-Length', '0'))
            body = self.rfile.read(length)
            req = json.loads(body.decode())
        except Exception:
            return self._send_json(400, {"ok": False, "error": "bad json"})

        r = s = v = None
        if 'sig_hex' in req:
            sig = req['sig_hex']
            if sig.startswith('0x'):
                sig = sig[2:]
            if len(sig) != 130:
                return self._send_json(400, {"ok": False, "error": "bad sig len"})
            r = int(sig[:64], 16)
            s = int(sig[64:128], 16)
            v = int(sig[128:130], 16)
        else:
            try:
                r = int(req['r'], 16) if isinstance(req['r'], str) else int(req['r'])
                s = int(req['s'], 16) if isinstance(req['s'], str) else int(req['s'])
                v = int(req['v'])
            except Exception:
                return self._send_json(400, {"ok": False, "error": "bad fields"})

        # Normalize v to 0/1 if 27/28
        if v in (27, 28):
            v -= 27

        # Verify signature on verify_hex using derived pubkey
        Q = self.pubkey
        msg_hex = self.chal['verify_hex']
        ok = verify_eth_sig(Q, msg_hex, r, s)
        if not ok:
            return self._send_json(200, {"ok": False, "error": "bad signature"})

        # Accept
        # flag composition
        if self.cfg.flag is not None:
            flag = self.cfg.flag
        else:
            prefix = self.cfg.flag_prefix
            flag = f"flag{{{prefix}{self.token[:8]}}}"
        return self._send_json(200, {"ok": True, "flag": flag})


def run(host='127.0.0.1', port=59999, chal_path=None, result_path=None, flag_prefix='local-', flag=None):
    class Cfg:
        pass
    cfg = Cfg()
    cfg.chal_path = chal_path
    cfg.result_path = result_path
    cfg.flag_prefix = flag_prefix
    cfg.flag = flag

    ChallengeServer.init_data(cfg)
    httpd = HTTPServer((host, port), ChallengeServer)
    print(f"Serving HTTP on {host}:{port}\n- chal: {chal_path}\n- result: {result_path}\n- flag_prefix: {flag_prefix}\n- fixed_flag: {flag}")
    httpd.serve_forever()


if __name__ == '__main__':
    base = os.path.dirname(os.path.abspath(__file__))
    def env(k, d=None):
        return os.environ.get(k, d)
    parser = argparse.ArgumentParser(description='Local challenge server (verify signatures).')
    parser.add_argument('--host', default=env('LOCAL_SERVER_HOST', '127.0.0.1'))
    parser.add_argument('--port', type=int, default=int(env('LOCAL_SERVER_PORT', '59999')))
    # default challenge is in ../task when server is under solution/
    parser.add_argument('--chal', dest='chal_path', default=env('LOCAL_CHAL_JSON', os.path.join(base, '..', 'task', 'challenge_data.json')))
    # default result is in same folder as this server
    parser.add_argument('--result', dest='result_path', default=env('LOCAL_RESULT_JSON', os.path.join(base, 'result.json')))
    parser.add_argument('--flag-prefix', dest='flag_prefix', default=env('LOCAL_FLAG_PREFIX', 'local-'))
    parser.add_argument('--flag', dest='flag', default=env('LOCAL_FLAG', None), help='fixed flag string, e.g., flag{...}. If set, overrides prefix-based flag.')
    args = parser.parse_args()
    run(args.host, args.port, args.chal_path, args.result_path, args.flag_prefix, args.flag)
