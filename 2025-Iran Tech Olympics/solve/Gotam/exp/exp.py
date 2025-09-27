#!/usr/bin/env python3

import subprocess
from pwn import *
from Crypto.Util.number import long_to_bytes

# Set pwntools context
context.log_level = "debug"

# --- Server Information ---
HOST = '65.109.194.34'
PORT = 13131

def get_public_data(r):
    """Fetches the public key (n, t) from the server."""
    r.sendlineafter(b'uit', b'P')
    r.recvuntil(b'n, t = ')
    line = r.recvline().decode().strip()
    n_hex, t_hex = line.split(', ')
    n = int(n_hex, 16)
    t = int(t_hex, 16)
    log.success(f"Received n = {n}")
    log.success(f"Received t = {t}")
    return n, t

def get_encrypted_flag(r):
    """Fetches the 1024 encrypted blocks of the flag."""
    r.sendlineafter(b'uit', b'E')
    encrypted_blocks = []
    # Loop until we have collected exactly 1024 blocks
    while len(encrypted_blocks) < 1024:
        line = r.recvline()
        if not line:
            # Connection closed prematurely
            log.error("Connection closed by server before receiving all data.")
            break
            
        line_str = line.decode().strip()
        
        # Only process lines that actually contain our data format
        if '=' in line_str and 'hex(e)' in line_str:
            try:
                hex_val = line_str.split('=')[1].strip().strip("'")
                encrypted_blocks.append(int(hex_val, 16))
            except (ValueError, IndexError):
                # This will catch any malformed lines that still contain '='
                log.warning(f"Skipping malformed data line: {line_str}")
    
    log.success(f"Successfully received {len(encrypted_blocks)} encrypted blocks.")
    return encrypted_blocks

def factor_with_sage(n):
    """
    Calls SageMath in a subprocess to factor the number n.
    Requires 'sage' to be in the system's PATH.
    """
    log.info(f"Attempting to factor n using SageMath...")
    command = ['sage', '-c', f'print(factor({n}))']
    
    try:
        # Execute the command
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,  # Raise an exception for non-zero exit codes
            timeout=300  # 5-minute timeout for factorization
        )
        output = result.stdout.strip()

        # Parse the output, e.g., "p * q"
        factors = output.split(' * ')
        if len(factors) == 2:
            p = int(factors[0])
            q = int(factors[1])
            log.success("SageMath successfully factored n.")
            return p, q
        else:
            log.error(f"SageMath returned an unexpected format: {output}")
            return None, None

    except FileNotFoundError:
        log.error("SageMath command not found. Is Sage installed and in your PATH?")
        return None, None
    except subprocess.CalledProcessError as e:
        log.error(f"SageMath process failed: {e.stderr}")
        return None, None
    except subprocess.TimeoutExpired:
        log.error("SageMath factorization timed out.")
        return None, None

def solve():
    """Main function to orchestrate the solution."""
    r = remote(HOST, PORT)

    # 1. Get the public key (n, t)
    n, t = get_public_data(r)

    # 3. Get the encrypted flag
    enc_flag = get_encrypted_flag(r)

    # 2. Factor n automatically using SageMath
    p, q = factor_with_sage(n)
    if p is None or q is None:
        log.failure("Could not factor n. Aborting.")
        r.close()
        return

    log.info(f"p = {p}")
    log.info(f"q = {q}")

    
    

    # 4. Decrypt the flag bit by bit
    log.info("Decrypting the flag...")
    binary_flag = ""
    for e in enc_flag:
        legendre_symbol = pow(e, (p - 1) // 2, p)
        if legendre_symbol == 1:
            binary_flag += '0'
        elif legendre_symbol == p - 1:
            binary_flag += '1'
        else:
            log.error(f"Error calculating Legendre symbol for {e}")
            r.close()
            return

    # 5. Convert the binary string back to the flag
    flag_int = int(binary_flag, 2)
    flag = long_to_bytes(flag_int)

    log.success(f"🎉 FLAG: {flag.decode().strip()}")

    r.close()

if __name__ == "__main__":
    solve()