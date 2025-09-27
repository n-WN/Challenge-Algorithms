#!/usr/bin/env python3

from Crypto.Util.number import *
from string import printable

# 分析padding逻辑
def analyze_padding():
    print("=== 分析Padding逻辑 ===")
    
    # 原始的pad函数逻辑
    print("原始pad函数:")
    print("def pad(flag):")
    print("    r = len(flag) % 8")
    print("    if r != 0:")
    print("        flag = flag[:-1] + (8 - r) * printable[:63][getRandomRange(0, 62)].encode() + flag[-1:]")
    print("    return flag")
    print()
    
    # 测试不同的原始flag长度
    original_flag = "ASIS{d0nT___rEuS3___peXp!}"
    print(f"假设原始flag: '{original_flag}'")
    print(f"原始长度: {len(original_flag)}")
    print(f"原始长度 % 8: {len(original_flag) % 8}")
    
    if len(original_flag) % 8 != 0:
        padding_needed = 8 - (len(original_flag) % 8)
        print(f"需要padding: {padding_needed} 字符")
        
        # 根据padding逻辑: flag = flag[:-1] + padding + flag[-1:]
        flag_prefix = original_flag[:-1]  # 除了最后一个字符
        flag_suffix = original_flag[-1:]  # 最后一个字符
        
        print(f"flag前缀: '{flag_prefix}'")
        print(f"flag后缀: '{flag_suffix}'")
        print(f"padding位置: 在'{flag_prefix}'和'{flag_suffix}'之间")
        
        # 模拟可能的padding
        possible_padded = flag_prefix + 'm' * padding_needed + flag_suffix
        print(f"可能的padded结果: '{possible_padded}'")
        
        return original_flag, possible_padded
    else:
        print("不需要padding")
        return original_flag, original_flag

# 验证我们恢复的明文
recovered_flag = "ASIS{d0nT___rEuS3___peXp!mmmmmm}"
print(f"恢复的flag: '{recovered_flag}'")
print(f"恢复flag长度: {len(recovered_flag)}")

original_flag, padded_flag = analyze_padding()

print(f"\n=== 比较结果 ===")
print(f"理论padded flag: '{padded_flag}'")
print(f"实际恢复flag:   '{recovered_flag}'")
print(f"匹配: {padded_flag == recovered_flag}")

if padded_flag == recovered_flag:
    print(f"\n✅ 确认: 恢复的flag包含了padding")
    print(f"真正的原始flag应该是: '{original_flag}'")
    
    # 验证原始flag的长度是否合理
    if len(original_flag) % 8 != 0:
        print(f"原始flag长度{len(original_flag)}不是8的倍数，确实需要padding")
    else:
        print(f"原始flag长度{len(original_flag)}是8的倍数，不应该需要padding")

print(f"\n=== 最终结论 ===")
print(f"带padding的完整flag: '{recovered_flag}'")
print(f"去掉padding的原始flag: '{original_flag}'")