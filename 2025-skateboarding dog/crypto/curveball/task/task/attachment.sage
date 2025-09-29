#!/bin/env python3

from sage.all import (
    EllipticCurve,
    GF,
    is_prime,
    randint,
    Integer,
    PolynomialRing
)
import os
import secrets

# 挑战常量
HITS_TO_WIN = 40
FLAG = os.getenv("FLAG", "skbdg{test_flag}")

def get_user_parameters():
    """
    获取用户输入的椭圆曲线参数 a, b 和大素数 p，并进行有效性检查。
    此函数保留了输入和验证逻辑，但去除了所有用户提示和错误print。
    """
    while True:
        try:
            # 假设输入来自标准输入或其他源，但去除了提示
            a = int(input('a: '))
            b = int(input('b: '))
            p = int(input('p: '))

            # 检查 p 的位数
            if p.bit_length() < 384:
                print("p is too small")
                continue

            # 检查 p 是否为素数
            if not is_prime(p):
                print("p is not prime")
                continue

            # 检查曲线的判别式
            if (4 * a**3 + 27 * b**2) % p == 0:
                print("Invalid curve parameters")
                continue

            return a, b, p

        except (ValueError, TypeError):
            print("Invalid input")
            continue


def construct_fp2(p):
    """
    构造有限域 $\text{GF}(p^2)$
    """
    Fp = GF(p)
    non_residue = Fp.quadratic_nonresidue()
    R, j = PolynomialRing(Fp, 'j').objgen()
    modulus = j**2 - non_residue
    Fp2 = GF(p**2, name='j', modulus=modulus)
    return Fp2, modulus


def main():
    """
    主函数：初始化挑战并运行游戏循环
    """
    hit_counter = 0

    # 1. 获取参数并构造 $\text{GF}(p^2)$
    a, b, p = get_user_parameters()
    Fp2, modulus = construct_fp2(p)

    try:
        # 2. 构造椭圆曲线 $E$ 及其二次扭曲 $E_{\text{twist}}$
        E = EllipticCurve(Fp2, [a, b])
    except Exception:
        print("Failed to construct the elliptic curve")
        return

    E_twist = E.quadratic_twist()

    # 3. 游戏循环：连续 $HITS\_TO\_WIN$ 次挑战
    while hit_counter < HITS_TO_WIN:
        # 随机选择原曲线 $E$ 或扭曲曲线 $E_{\text{twist}}$
        use_twist = secrets.randbits(1)
        current_curve = E_twist if use_twist else E
        print(f"Current curve: {'E_twist' if use_twist else 'E'}")

        try:
            # 4. 生成挑战：$Q = k \cdot P$
            P = current_curve.random_point()
            k = secrets.randbelow(int((p + 1)**2))
            Q = k * P

        except Exception:
            return

        print(f"\nCurve is y^2 = x^3 + ({current_curve.a4()})x + ({current_curve.a6()})")
        print(f"P = {P.xy()}")
        print(f"Q = {Q.xy()}")
        # 5. 提示用户输入 $k$ 的相关输出全部移除，但保留了输入操作
        # 注意：此处输入操作 `input()` 仍会阻塞程序等待输入，只是没有了提示
        try:
            # 假设用户知道需要输入 k
            user_k = int(input('k: '))

            # 6. 验证用户输入的 $k$
            if Integer(user_k) * P == Q:
                hit_counter += 1
                print(f"Hit {hit_counter} out of {HITS_TO_WIN}!")
            else:
                print(f"Missed! The correct answer was {k}.")
                return

        except (ValueError, TypeError):
            print(f"Invalid input!")
            return

    print(f"You've hit {HITS_TO_WIN} pitches in a row!")
    print("Here is your flag:")
    print(f"\n    {FLAG}\n")
    print("=" * 60)

if __name__ == "__main__":
    main()
