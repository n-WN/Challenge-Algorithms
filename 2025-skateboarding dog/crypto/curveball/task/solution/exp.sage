#!/usr/bin/env sage -python
# -*- coding: utf-8 -*-

from sage.all import GF, EllipticCurve
import os, sys, re, subprocess


def find_task_path(script_dir: str):
    # Priority: env > common relative paths
    env_path = os.environ.get('TASK') or os.environ.get('CHALLENGE') or os.environ.get('TASK_PATH')
    candidates = []
    if env_path:
        candidates.append(env_path)
    # relative to script dir
    candidates += [
        os.path.join(script_dir, '..', 'task', 'attachment.sage'),
        os.path.join(script_dir, '..', 'task', 'attachment.txt'),
        os.path.join(script_dir, 'task', 'attachment.sage'),
        os.path.join(script_dir, 'task', 'attachment.txt'),
    ]
    # relative to CWD
    cwd = os.getcwd()
    candidates += [
        os.path.join(cwd, 'task', 'attachment.sage'),
        os.path.join(cwd, 'task', 'attachment.txt'),
    ]
    for path in candidates:
        if path and os.path.exists(path):
            return os.path.abspath(path)
    return None


def parse_fp2_elem(s: str, p: int):
    s = s.strip().replace(' ', '')
    s = s.replace('+j', '+1*j').replace('-j', '-1*j')
    if s == 'j':
        s = '1*j'
    if s == '-j':
        s = '-1*j'
    terms = []
    cur = ''
    for i,ch in enumerate(s):
        if ch in '+-' and i != 0:
            terms.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        terms.append(cur)
    u = 0; v = 0
    for t in terms:
        if t.endswith('*j'):
            coef = t[:-2]
            if coef in ('+', '-'):
                coef += '1'
            v = (v + int(coef)) % p
        else:
            u = (u + int(t)) % p
    return u % p, v % p


def parse_fp2_pair(s: str, p: int):
    s = s.strip()
    assert s.startswith('(') and s.endswith(')')
    inner = s[1:-1]
    dep = 0; parts = []; cur = ''
    for ch in inner:
        if ch == ',' and dep == 0:
            parts.append(cur); cur = ''
        else:
            if ch == '(':
                dep += 1
            elif ch == ')':
                dep -= 1
            cur += ch
    if cur:
        parts.append(cur)
    (u,v) = parse_fp2_elem(parts[0], p)
    (s_,t) = parse_fp2_elem(parts[1], p)
    return (u,v),(s_,t)


def recover_delta_from_point(x_uv, y_st, A_uv, B_uv, p: int):
    # j-coeff compare for y^2 = x^3 + A x + B over Fp[j]/(j^2 - delta)
    u,v = x_uv; s,t = y_st
    A0,A1 = A_uv; B0,B1 = B_uv
    v %= p
    if v == 0:
        return None
    num = (2*s*t - (3*(u*u % p) % p)*v - A0*v - A1*u - B1) % p
    den = pow((v*v % p)*v % p, -1, p)
    return (num * den) % p


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    task_path = find_task_path(script_dir)
    if not task_path:
        print('[!] challenge not found. Tried TASK env and common paths under task/.')
        print('    请设置环境变量 TASK 指向题目脚本，或将题目放在 task/attachment.sage / task/attachment.txt')
        sys.exit(1)

    # parameters
    a = int(os.environ.get('A', '1'))
    b = int(os.environ.get('B', '0'))
    p_env = os.environ.get('P') or os.environ.get('P_OVERRIDE')
    if not p_env:
        print('[!] 请先提供满足“p±1 双平滑”的素数 p（384+ bit）。例如：')
        print('    P=<decimal prime> sage solution/exp.sage')
        sys.exit(2)
    p = int(p_env)

    # launch challenge
    # 显式转为 Python int，避免 Sage 将 0 转换为 Sage Integer 导致类型检查失败
    proc = subprocess.Popen(['sage', '-python', task_path], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=int(0))

    def sendln(s: str):
        proc.stdin.write(s + '\n'); proc.stdin.flush()

    # send a,b,p (无需等待提示)
    sendln(str(a)); sendln(str(b)); sendln(str(p))

    Fp = GF(p)
    while True:
        line = proc.stdout.readline()
        if not line:
            break
        sys.stdout.write(line); sys.stdout.flush()
        if line.strip().startswith('Curve is y^2 = x^3'):
            m = re.search(r"\+ \((.+)\)x \+ \((.+)\)$", line.strip())
            if m:
                a4_str, a6_str = m.group(1), m.group(2)
            else:
                a4_str, a6_str = '1', '0'
            Pline = proc.stdout.readline(); sys.stdout.write(Pline)
            Qline = proc.stdout.readline(); sys.stdout.write(Qline)
            Pstr = Pline.split('=',1)[1].strip()
            Qstr = Qline.split('=',1)[1].strip()

            (ux,vx),(sx,tx) = parse_fp2_pair(Pstr, p)
            (uq,vq),(sq,tq) = parse_fp2_pair(Qstr, p)
            def parse_coeff_pair(s):
                if s.startswith('(') and s.endswith(')'):
                    s = s[1:-1]
                return parse_fp2_elem(s, p)
            A0,A1 = parse_coeff_pair(a4_str)
            B0,B1 = parse_coeff_pair(a6_str)

            delta = recover_delta_from_point((ux,vx),(sx,tx),(A0,A1),(B0,B1), p)
            if delta is None:
                delta = recover_delta_from_point((uq,vq),(sq,tq),(A0,A1),(B0,B1), p)
            if delta is None:
                print('[!] 无法恢复 delta，回填 k=0 继续')
                sendln('0')
                continue

            Rj = Fp['j']; j = Rj.gen()
            Fp2 = GF(p**2, name='j', modulus=j**2 - Fp(delta))
            A = Fp2(A0) + Fp2(A1)*Fp2.gen()
            B = Fp2(B0) + Fp2(B1)*Fp2.gen()
            E = EllipticCurve(Fp2, [A,B])
            Px = Fp2(ux) + Fp2(vx)*Fp2.gen(); Py = Fp2(sx) + Fp2(tx)*Fp2.gen()
            Qx = Fp2(uq) + Fp2(vq)*Fp2.gen(); Qy = Fp2(sq) + Fp2(tq)*Fp2.gen()
            Ppt = E((Px, Py)); Qpt = E((Qx, Qy))
            try:
                k = Qpt.log(Ppt)
            except Exception as e:
                print('[!] Q.log 失败，回填 k=0 ：', e)
                k = 0
            sendln(str(int(k)))
        if 'flag{' in line or 'skbdg{' in line:
            break

    proc.wait()


if __name__ == '__main__':
    main()
