#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
精简版解题脚本：调用 Sage + cuso 求解器并输出结果。

说明：
- 之前尝试过 Z3/SMT 与简化格方法，但未能在本数据上稳定收敛，相关代码已移除。
- 本脚本会调用 `solve_with_cuso.py` 完成求解，并在 solution/result.json 写出 x 与签名。
"""

import json
import os
import subprocess
import sys


def main():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    solver = os.path.join(base, 'solution', 'solve_with_cuso.py')

    # 调用 Sage 的 Python 运行 cuso 解法
    try:
        subprocess.check_call(['sage', '-python', solver])
    except FileNotFoundError:
        print('[!] 未找到 sage 命令，请在已安装 SageMath 的环境中运行或直接执行 solve_with_cuso.py')
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print('[!] cuso 求解器运行失败', e)
        sys.exit(2)

    # 显示结果
    res_path = os.path.join(base, 'solution', 'result.json')
    if os.path.exists(res_path):
        with open(res_path, 'r') as f:
            res = json.load(f)
        print('[+] 恢复的私钥 x =', res.get('x_hex'))
        print('[+] 签名 sig_hex =', res.get('signature', {}).get('sig_hex'))
    else:
        print('[!] 未找到 result.json，请检查 solve_with_cuso.py 输出')


if __name__ == '__main__':
    main()
