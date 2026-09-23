# yijing — 易经八卦与子平八字 Agent Skill

一个**自包含、零依赖**的《易经》知识体系与推演工具包，供 Claude Code、WorkBuddy 及任意支持 SKILL.md 约定的 Agent 直接加载。

卦爻辞原文、六十甲子这类冷数据以 JSON 落盘、按需读取（不占上下文）；推演规则以 Markdown 供阅读；所有计算由**纯 Python 标准库**脚本完成，结果确定、可复现、可校验——不靠模型临场回忆，不联网、不写文件。

## 用途

| 能力 | 说明 |
|---|---|
| 六十四卦全文 | 卦辞、彖传、象传、386 爻辞 + 小象传（含用九用六），通行本王弼本 |
| 起卦 | 金钱卦（三枚硬币/铜钱摇六次）、梅花易数（数字或时间），出本卦、互卦、变卦、动爻、体用 |
| 纳甲装卦 | 京房八宫、纳甲纳支、世应、六亲装配 |
| 干支换算 | 公历日期 → 四柱干支、六十甲子、纳音、藏干、十二长生 |
| 五行与类象 | 生克制化、旺相休囚死、八卦万物类象、地支冲合刑害 |
| 子平八字 | 四柱十神、大运小运起运、日主强弱、神煞、格局、用神喜忌、流年作用 |

## 加载方式

### 方式一：Claude Code

```bash
# 用户级（所有项目可用）
git clone https://github.com/ZQing-Chen/yijing.git ~/.claude/skills/yijing

# 项目级（仅当前项目）
git clone https://github.com/ZQing-Chen/yijing.git .claude/skills/yijing
```

目录内 `SKILL.md` 的 frontmatter 含 `name` 与 `description`，Claude Code 会在命中触发词时自动加载。也可显式调用 `/yijing`。

### 方式二：WorkBuddy

```bash
git clone https://github.com/ZQing-Chen/yijing.git ~/.workbuddy/skills/yijing
```

### 方式三：任意 Agent

把 `SKILL.md` 作为系统提示词或指令文件读入即可。脚本以**相对路径**引用数据（`assets/data/*.json`），不改代码即可整体搬迁。

### 环境要求

Python 3.10 及以上，**无需任何第三方包**。自检：

```bash
cd yijing
python scripts/yijing.py env     # 输出 ready 即为可用
```

## 使用示例

工作目录为 Skill 根目录：

```bash
python scripts/yijing.py list                                   # 64 卦总表
python scripts/yijing.py gua 乾                                 # 卦辞、彖传、象传、爻辞全文
python scripts/yijing.py gua 3                                  # 也支持 1-64 序号
python scripts/yijing.py cast-coin --backs 3 2 2 1 0 3          # 金钱卦：6 次背面个数（初→上）
python scripts/yijing.py cast-coin --random                     # 随机摇一卦
python scripts/yijing.py cast-time --numbers 12 8               # 梅花易数起卦
python scripts/yijing.py najia 屯                               # 纳甲装卦：世应 + 六亲 + 干支
python scripts/yijing.py ganzhi --date 2026-09-22 --hour 午     # 四柱干支与纳音
python scripts/yijing.py wuxing 木 火                           # 五行生克
python scripts/yijing.py xiang 离                               # 八卦类象
python scripts/yijing.py relation 申 子 辰                      # 地支冲合刑害
python scripts/yijing.py bazi --date 1997-02-12 --hour 丑 \
        --gender 男 --liunian 2026                              # 八字排盘批命
```

自然语言触发（由 Agent 自动路由）：占一卦、起卦、摇卦、金钱卦、梅花易数、体用、纳甲、排盘、六爻、世应六亲、五行生克、六十甲子、纳音、干支冲合刑害、先天八卦方位、八字、批命、十神、大运、起运、流年、用神喜忌、身强身弱、神煞。

## 目录结构

```text
yijing/
├── SKILL.md                      # 主入口：frontmatter + 边界条款 + 指令路由 + 输出规范
├── skill-dependencies.json       # 依赖声明（仅 Python 3.10+，无网络、无密钥）
├── README.md
├── LICENSE                       # MIT
├── .gitignore
├── assets/data/
│   ├── gua64.json                # 64 卦卦辞、彖传、象传、386 爻辞、小象传
│   ├── ganzhi.json               # 六十甲子、纳音、藏干、十二长生
│   ├── base.json                 # 八卦、京房八宫纳甲、五行、干支关系
│   └── bazi.json                 # 十神、神煞、藏干透出、强弱权重、格局调候
├── references/
│   ├── 01-bagua.md               # 八卦卦形、先天/后天方位、万物类象
│   ├── 02-wuxing.md              # 五行生克制化、旺相休囚死、十二长生
│   ├── 03-ganzhi.md              # 天干地支、藏干、冲合刑害、六十甲子纳音
│   ├── 04-najia-liuyao.md        # 京房八宫、纳甲纳支、世应六亲、装卦步骤
│   ├── 05-meihua.md              # 梅花易数起卦、体用关系、金钱卦
│   ├── 06-io-contract.md         # 调用契约、输入输出格式、数据文件说明
│   ├── 07-bazi.md                # 子平八字：十神、大运、神煞、格局、用神
│   └── setup-guide.md            # 环境配置指南
└── scripts/
    ├── yijing.py                 # 确定性计算引擎（纯标准库）
    └── check_environment.py      # 环境自检
```

## 边界与限制

本 Skill 定位为**传统文化研究与象征性推演参考**，内置以下硬约束：

- 卦爻辞一律取自数据文件，查不到明说「未收录」，不凭记忆补全
- 梅花易数体用与六爻世应属两套体系，不混用
- 不宣称「必定发生」，不定论吉凶，不预测具体事件、日期、数字
- **不用于医疗、法律、金融投资、生育、人身安全等现实决策**
- 不联网、不外传，脚本只读本地数据文件

已知精度边界（每次相关输出都会提示）：

| 项目 | 误差 |
|---|---|
| 日柱干支 | 精确 |
| 年柱、月柱（按节气） | 速算公式，±1 日 |
| 八字起运岁数 | 约 ±0.4 岁 |
| 真太阳时、晚子时换日、交节精确时刻 | 未实现 |
| 农历公历互转 | 未内置（时间起卦需自行提供农历） |

## 许可

MIT，详见 [LICENSE](LICENSE)。
