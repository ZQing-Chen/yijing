#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""环境就绪检查：只读，不修改配置、不输出凭据、不写文件。"""

import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "assets" / "data"
REQUIRED_FILES = ["base.json", "gua64.json", "ganzhi.json"]
MIN_PY = (3, 10)

problems = []
warnings = []
facts = []

py = sys.version_info[:2]
facts.append("Python %d.%d.%d" % sys.version_info[:3])
if py < MIN_PY:
    problems.append("Python 版本 %d.%d 低于要求 %d.%d" % (py[0], py[1], MIN_PY[0], MIN_PY[1]))

for name in REQUIRED_FILES:
    p = DATA / name
    if not p.exists():
        problems.append("数据文件缺失：%s" % name)
        continue
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        facts.append("%s 可解析" % name)
    except json.JSONDecodeError as exc:
        problems.append("数据文件损坏：%s（%s）" % (name, exc))

deps = BASE / "skill-dependencies.json"
if not deps.exists():
    warnings.append("缺少 skill-dependencies.json，依赖矩阵不可用")

print("## 环境检查")
print()
print("| 检查项 | 结果 |")
print("|---|---|")
for f in facts:
    print("| %s | 正常 |" % f)
for name in REQUIRED_FILES:
    p = DATA / name
    print("| %s | %s |" % (name, "存在" if p.exists() else "缺失"))
print("| 外部依赖 | 无（纯标准库） |")
print("| 网络需求 | 无 |")
print()

if problems:
    print("**结论**：needs_setup")
    print()
    print("缺失项：")
    for x in problems:
        print(" - " + x)
    print()
    print("恢复方式：见 `references/setup-guide.md`。")
    sys.exit(2)

if warnings:
    print("**结论**：partial")
    print()
    for x in warnings:
        print(" - " + x)
    sys.exit(0)

print("**结论**：ready")
print()
print("跳过配置引导，直接使用 `python scripts/yijing.py <指令>`。")
