#!/usr/bin/env python3
import os

# 直接读取文件看原始格式
md_path = "./output/巴比伦最富有的人.md"

with open(md_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")
print("\n前30行内容：")
for i, line in enumerate(lines[:30]):
    repr_line = repr(line)  # 显示原始字符
    print(f"{i}: {repr_line}")