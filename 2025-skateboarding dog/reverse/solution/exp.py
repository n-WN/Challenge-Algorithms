# data 数组，注意负数是 signed char
data = [
    116, -7, -8, 3, 4, 21, -12, 2, 6,
    -20, 9, 9, 0, 1, -12, -1, 20, -12,
    -3, 3, 6, -8, 15, 13, -25, 22, -14,
    8, -6, 12, -7, 8, 0, -8, -67, 1, 1, 93,
    127
]

# 模拟寄存器
# r4 -> i (index)
# r7 -> acc (accumulator)

# 初始化
i = 0
acc = data[0]
flag = ""

# 循环
while True:
    # 1. 计算并打印字符
    char_code = (acc - (i + 1)) & 0xFF  # & 0xFF 确保结果是字节
    flag += chr(char_code)

    # 2. 更新索引
    i += 1
    
    # 3. 读取下一个数据并检查终止条件
    next_byte = data[i]
    if next_byte == 127:
        break
    
    # 4. 更新累加器
    acc += next_byte

print(flag)
