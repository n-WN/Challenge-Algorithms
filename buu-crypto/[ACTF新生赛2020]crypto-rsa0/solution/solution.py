from pathlib import Path


def long_to_bytes(n: int) -> bytes:
    if n == 0:
        return b"\x00"
    length = (n.bit_length() + 7) // 8
    return n.to_bytes(length, "big")


def main() -> None:
    data_path = Path("challenge") / "output"
    lines = [int(line.strip()) for line in data_path.read_text().splitlines() if line.strip()]
    if len(lines) != 3:
        raise ValueError("Expected three integers (p, q, c) in challenge/output")
    p, q, c = lines
    e = 65537
    n = p * q
    phi = (p - 1) * (q - 1)
    d = pow(e, -1, phi)
    m = pow(c, d, n)
    flag = long_to_bytes(m)
    try:
        print(flag.decode())
    except UnicodeDecodeError:
        print(flag)


if __name__ == "__main__":
    main()
