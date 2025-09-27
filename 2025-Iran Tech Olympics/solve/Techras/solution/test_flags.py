#!/usr/bin/env python3

from Crypto.Util.number import *

# 从我的成功解题中获取的数据
n = 10866178428529981157987115394329389360278606067577446176161304157834299662440250814778457760406922023898610135768513737316904585017501144403986679160215797354457425256710863823747407954973402183410527062522462353515073160812876459761219098998726795539214771348809786648460810821925145318007272146274589980684836189732239027669376247035749029399038589379501688561012993299596697473285452261054584297849986566093260339702058294233923758263673918854410116019346076621928134803230643458333609390855532720651308634429292650444364338927565432496211742376830726971323046187944348136269280008949055735905468235681761048336811

# 找到的明文数值 - 这个产生了验证成功的结果
recovered_m = 29547489542442437543022758120842421650909715569237793218513280381008422464893

print("=== 分析恢复的明文 ===")
print(f"明文数值: {recovered_m}")

# 转换为字节
data_bytes = long_to_bytes(recovered_m)
print(f"字节长度: {len(data_bytes)}")
print(f"字节数据: {data_bytes}")

# 尝试解码
try:
    decoded = data_bytes.decode('utf-8')
    print(f"UTF-8解码: '{decoded}'")
except Exception as e:
    print(f"UTF-8解码失败: {e}")
    try:
        decoded = data_bytes.decode('latin-1', errors='ignore')
        print(f"Latin-1解码: '{decoded}'")
    except:
        pass

# 测试不同的flag候选
possible_flags = [
    'ASIS{d0nT___rEuS3___peXp!}',
    'ASIS{d0nT___rEuS3___peXp!MMMMMM}',
    'ASIS{d0nT___rEuS3___peXp!mmmmmm}'
]

print("\n=== 测试flag候选 ===")
for flag in possible_flags:
    print(f"\n测试flag: '{flag}'")
    flag_bytes = flag.encode('utf-8')
    flag_m = bytes_to_long(flag_bytes)
    
    print(f"  作为数值: {flag_m}")
    print(f"  匹配恢复的明文: {flag_m == recovered_m}")
    
    if flag_m == recovered_m:
        print(f"  ✅ 这是正确的flag!")

# 直接从明文数值反推flag
print(f"\n=== 从明文数值直接解码 ===")
correct_flag = long_to_bytes(recovered_m).decode('utf-8')
print(f"正确的flag: '{correct_flag}'")

# 验证这个flag的加密
# 使用我知道验证成功的密文对 (1, 43) 对应的指数
e1 = 3448105229  # 第1个密文的指数
e2 = 2250955207  # 第43个密文的指数

test_c1 = pow(recovered_m, e1, n)
test_c2 = pow(recovered_m, e2, n)

print(f"\n=== 验证加密结果 ===")
print(f"用e1={e1}加密得到: {test_c1}")
print(f"用e2={e2}加密得到: {test_c2}")