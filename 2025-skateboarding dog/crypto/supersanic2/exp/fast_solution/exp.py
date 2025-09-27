#!/usr/bin/env python3
import subprocess
from pwn import *

# --- 配置 ---
HOST = "c.sk8.dog"
PORT = 30005
# 确保 C++ solver 编译后叫这个名字，且在同一目录
CPP_EXECUTABLE = "./solve"
# PoW solver 的路径
POW_SOLVER = "./pow.py"


def solve_challenge():
    """
    连接服务器，处理PoW，调用C++ solver，提交PIN，获取flag。
    """
    # 连接服务器
    conn = remote(HOST, PORT)

    # --- 1. 处理工作量证明 (PoW) ---
    try:
        conn.recvuntil(b"== proof of work: ")
        conn.recvline()  # 跳过 URL
        pow_challenge = conn.recvline().strip().decode()
        log.info(f"Received PoW challenge: {pow_challenge}")

        # 调用 pow-solver 工具
        solution = subprocess.check_output(
            ["python3", POW_SOLVER, "solve", pow_challenge]
        ).strip()
        log.success(f"PoW solution: {solution.decode()}")

        # 发送 PoW 答案
        conn.sendline(solution)
    except Exception as e:
        log.failure(f"PoW failed: {e}")
        conn.close()
        return

    # --- 2. 解析 RSA 参数 ---
    try:
        n_line = conn.recvline_contains(b"n = ").strip().decode()
        e_line = conn.recvline_contains(b"e = ").strip().decode()
        c_line = conn.recvline_contains(b"c = ").strip().decode()

        n = n_line.split(" = ")[1]
        e = e_line.split(" = ")[1]
        c = c_line.split(" = ")[1]

        log.info(f"n = {n}")
        log.info(f"e = {e}")
        log.info(f"c = {c}")
    except Exception as e:
        log.failure(f"Failed to parse RSA parameters: {e}")
        conn.close()
        return

    # --- 3. 调用 C++ Solver ---
    log.info("Running C++ solver... This may take a minute.")

    try:
        command = [CPP_EXECUTABLE, n, e, c]

        # 运行子进程，捕获其标准输出 (stdout)
        # stderr=subprocess.PIPE 会捕获C++的进度信息，并可以在这里打印
        result = subprocess.run(
            command,
            capture_output=True,
            check=True,  # 如果C++程序返回非0退出码，则抛出异常
            timeout=120,  # 设置2分钟超时
        )

        # 打印 C++ 程序的进度信息
        log.info("C++ solver output (stderr):\n" + result.stderr.decode())

        # 获取原始字节结果
        pin_bytes = result.stdout

        if len(pin_bytes) != 6:
            # 取前6字节作为PIN
            pin_bytes = pin_bytes[:6]
            log.failure(
                f"Solver returned invalid data (length {len(pin_bytes)}): {pin_bytes!r}"
            )
            # conn.close()
            # return

        log.success(f"Solver found PIN (bytes): {pin_bytes!r}")
    except subprocess.CalledProcessError as e:
        log.failure("C++ solver failed.")
        log.failure("Stderr:\n" + e.stderr.decode())
        conn.close()
        return
    except subprocess.TimeoutExpired:
        log.failure("C++ solver timed out.")
        conn.close()
        return

    # --- 4. 提交 PIN 并获取 Flag ---
    conn.sendlineafter(b"PIN: ", pin_bytes)

    # 接收并打印所有后续响应
    response = conn.recvall(timeout=5)
    log.success("Server response:\n" + response.decode())

    conn.close()


if __name__ == "__main__":
    solve_challenge()
