# 环境配置指南

本 Skill 只有一个必需依赖：**Python 3.10 及以上运行时**，依赖 id 为 `python-runtime`。无账号、无 Token、无 Key、无网络请求。

## 检查当前状态

```bash
python scripts/check_environment.py
```

输出 `ready` 表示可直接用；`needs_setup` 会列出缺失项；`partial` 表示核心可用但有非关键缺失。

## 缺失 Python 时的安装

| 项目 | 内容 |
|---|---|
| 依赖 id | `python-runtime` |
| 官方主页 | https://www.python.org |
| 官方下载地址 | https://www.python.org/downloads/ |
| 官方文档 | https://docs.python.org/zh-cn/3/ |
| 版本要求 | 3.10 及以上 |
| 所需权限 | 本地安装权限，无需管理员亦可安装到用户目录 |
| 凭据 | 无 |
| 核验日期 | 2026-09-22 |

Windows 安装时在向导中勾选 **Add python.exe to PATH**，否则命令行找不到 `python`。安装后新开一个终端验证：

```bash
python --version
```

## 验证

```bash
python scripts/yijing.py env
```

应输出 Python 版本、三个数据文件均存在、64 卦八宫归属全部匹配、结论 `ready`。

## 升级与卸载

| 操作 | 方式 |
|---|---|
| 升级 Python | 从官方下载页安装新版本，无需改动本 Skill |
| 轮换 | 升级后重跑 `scripts/check_environment.py` 确认版本 |
| 撤销 | 卸载 Python 或直接删除本 Skill 所在目录即可，无凭据残留、无系统配置改动 |

## 数据文件缺失

若 `env` 报告某个 JSON 缺失或解析失败，说明包不完整。重新安装 Skill 包覆盖即可，不要手工编辑数据文件——手工改动会导致八宫归属校验失败。

## 已知限制（不是故障）

以下情况不会报错，但结果需人工核对，属设计范围：

- 节气按 21 世纪速算公式，误差 ±1 日
- 不内置公历转农历，时间起卦需自行提供农历年月日
- 不含真太阳时校正与晚子时换日处理
- 不含六爻旺衰、旬空、月破、用神选取等进阶判断
