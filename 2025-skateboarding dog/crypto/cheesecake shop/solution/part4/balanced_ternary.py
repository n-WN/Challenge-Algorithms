# Sh1n

def balanced_ternary_sum(n):
    """计算数的平衡三进制表示的数字和"""
    if n == 0:
        return 0
    
    digits = []
    num = n
    while num != 0:
        num, remainder = divmod(num, 3)
        if remainder == 2:
            remainder = -1
            num += 1
        digits.append(remainder)
    
    return sum(digits)

# 测试1337
n = 1337
sum_digits = balanced_ternary_sum(n)

print(f"{n}的平衡三进制数字和为: {sum_digits}")

# 验证平衡三进制表示
def to_balanced_ternary(n):
    if n == 0:
        return "0"
    
    digits = []
    num = n
    while num != 0:
        num, remainder = divmod(num, 3)
        if remainder == 2:
            remainder = -1
            num += 1
        digits.append(remainder)
    return digits

balanced_ternary = to_balanced_ternary(n)

print(f"{n}的平衡三进制表示为: {balanced_ternary}")