# filename: decode.sage (Version 3 - Final)

# ------------------------------------------------------------------
# 1. 初始化与编码器完全相同的环境
# ------------------------------------------------------------------
print("Initializing the environment exactly as the encoder...")

G = GF(2^8, repr='int')
alpha = G([1, 1, 0, 0, 0, 0, 0, 1])
PR.<x> = PolynomialRing(G)

gx = (x - alpha^0) * (x - alpha^1) * (x - alpha^2) * (x - alpha^3)

def F(integer):
    assert 0 <= integer < 256
    return G.fetch_int(integer)

print("Environment set up successfully.")
# 修正点: 使用 int(str()) 进行转换，以避免 AttributeError
print(f"Using the same alpha as encoder: {alpha} (int: {int(str(alpha))})")
print(f"Generator polynomial gx degree = {gx.degree()}")

# ------------------------------------------------------------------
# 2. 核心解码函数
# ------------------------------------------------------------------
def decode_block(block_bytes):
    """
    对一个 8 字节的块进行里德-所罗门解码，纠正最多 2 个错误。
    """
    assert len(block_bytes) == 8

    received_coeffs = [F(b) for b in block_bytes]
    Rx = PR(received_coeffs)

    syndromes = [Rx(alpha^i) for i in range(4)]
    
    if all(s == 0 for s in syndromes):
        corrected_coeffs = Rx.list()
        corrected_coeffs += [G(0)] * (8 - len(corrected_coeffs))
        message_coeffs = corrected_coeffs[4:]
        # 修正点: 使用 int(str())
        return bytes([int(str(c)) for c in message_coeffs])

    S0, S1, S2, S3 = syndromes

    M_lambda = Matrix(G, [[S1, S0], [S2, S1]])
    b_lambda = vector(G, [S2, S3])

    try:
        solution = M_lambda.solve_right(b_lambda)
        L1, L2 = solution[0], solution[1]
    except ZeroDivisionError:
        print("Failed to solve for Lambda coefficients.")
        return None

    Lambda_x = PR([G(1), L1, L2])

    error_locations = []
    for k in range(8):
        if Lambda_x(alpha^(-k)) == 0:
            error_locations.append(k)

    if len(error_locations) != 2:
        print(f"Error: Expected to find 2 error locations, but found {len(error_locations)}.")
        return None
    
    j1, j2 = error_locations[0], error_locations[1]

    alpha_j1, alpha_j2 = alpha**j1, alpha**j2
    M_err = Matrix(G, [[1, 1], [alpha_j1, alpha_j2]])
    b_err = vector(G, [S0, S1])
    
    try:
        error_values = M_err.solve_right(b_err)
        e1, e2 = error_values[0], error_values[1]
    except ZeroDivisionError:
        print("Failed to solve for error magnitudes.")
        return None

    error_coeffs = [G(0)] * 8
    error_coeffs[j1], error_coeffs[j2] = e1, e2
    Ex = PR(error_coeffs)
    mx = Rx + Ex
    
    corrected_coeffs = mx.list()
    corrected_coeffs += [G(0)] * (8 - len(corrected_coeffs))
    message_coeffs = corrected_coeffs[4:8]
    
    # 修正点: 使用 int(str())
    return bytes([int(str(c)) for c in message_coeffs])

# ------------------------------------------------------------------
# 3. 主程序：读取文件并解码
# ------------------------------------------------------------------
def decode_file(input_filename, output_filename):
    print(f"\nStarting decoding of '{input_filename}'...")
    decoded_data = b''
    block_count = 0
    
    try:
        with open(input_filename, 'rb') as f_in:
            while True:
                block = f_in.read(8)
                if not block: break
                if len(block) != 8:
                    print("Warning: Trailing data in file is not a full block. Ignoring.")
                    break
                
                recovered_message = decode_block(block)
                if recovered_message:
                    decoded_data += recovered_message
                    block_count += 1
                    if block_count % 5000 == 0:
                        print(f"Processed {block_count} blocks...")
                else:
                    print(f"Critical Error: Failed to decode block at position {f_in.tell() - 8}. Aborting.")
                    return

        with open(output_filename, 'wb') as f_out:
            f_out.write(decoded_data)
        
        print(f"\nDecoding complete!")
        print(f"Successfully processed {block_count} blocks.")
        print(f"Recovered data saved to '{output_filename}'.")

    except FileNotFoundError:
        print(f"Error: Input file '{input_filename}' not found.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

# 执行解码
decode_file('flag.enc', 'flag_recovered.jpg')
