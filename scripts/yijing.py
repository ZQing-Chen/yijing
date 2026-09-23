#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""易经推演引擎：起卦、纳甲装卦、干支换算、五行与类象查询。

纯 Python 标准库实现，无网络、无子进程、不写文件、不读取用户个人数据。
"""

import argparse
import json
import random
import sys
from datetime import date, datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "assets" / "data"

# 六十甲子日锚点：公历 2026-09-22 为「己亥」日，序号 35（甲子为 0）
GANZHI_ANCHOR_DATE = (2026, 9, 22)
GANZHI_ANCHOR_INDEX = 35

# 21 世纪二十四节气速算公式常数，顺序自小寒起
TERM_NAMES = [
    "小寒", "大寒", "立春", "雨水", "惊蛰", "春分", "清明", "谷雨",
    "立夏", "小满", "芒种", "夏至", "小暑", "大暑", "立秋", "处暑",
    "白露", "秋分", "寒露", "霜降", "立冬", "小雪", "大雪", "冬至",
]
TERM_C = [
    5.4055, 20.12, 3.87, 18.73, 5.63, 20.646, 4.81, 20.1,
    5.52, 21.04, 5.678, 21.37, 7.108, 22.83, 7.5, 23.13,
    7.646, 23.042, 8.318, 23.438, 7.438, 22.36, 7.18, 21.94,
]
# 速算公式在这些年份需 -1 天修正
TERM_MINUS_ONE = {
    "小寒": [2019, 2082], "大寒": [2082], "立春": [], "雨水": [2026],
    "惊蛰": [], "春分": [2084], "清明": [], "谷雨": [2008],
    "立夏": [1911], "小满": [2008], "芒种": [1902], "夏至": [2016],
    "小暑": [2016, 1925], "大暑": [1922], "立秋": [2002], "处暑": [],
    "白露": [1927], "秋分": [1942], "寒露": [2088], "霜降": [2089],
    "立冬": [2089], "小雪": [1978], "大雪": [1954], "冬至": [2021],
}
TERM_PLUS_ONE = {
    "大寒": [2000], "雨水": [2026], "惊蛰": [2084], "春分": [],
    "清明": [], "谷雨": [], "立夏": [], "小满": [], "芒种": [],
    "夏至": [], "小暑": [], "大暑": [], "立秋": [], "处暑": [],
    "白露": [], "秋分": [], "寒露": [], "霜降": [], "立冬": [],
    "小雪": [], "大雪": [], "冬至": [], "小寒": [1982], "立春": [],
}

TIANGAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
DIZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
BRANCH_INDEX = {b: i + 1 for i, b in enumerate(DIZHI)}
SHICHEN = [
    ("子", 23, 1), ("丑", 1, 3), ("寅", 3, 5), ("卯", 5, 7),
    ("辰", 7, 9), ("巳", 9, 11), ("午", 11, 13), ("未", 13, 15),
    ("申", 15, 17), ("酉", 17, 19), ("戌", 19, 21), ("亥", 21, 23),
]

# 年上起月：正月天干起点，索引对应年干序号
YUE_GAN_START = {"甲": 2, "己": 2, "乙": 4, "庚": 4, "丙": 6, "辛": 6,
                 "丁": 8, "壬": 8, "戊": 0, "癸": 0}
# 日上起时：子时天干起点，索引对应日干序号
SHI_GAN_START = {"甲": 0, "己": 0, "乙": 2, "庚": 2, "丙": 4, "辛": 4,
                 "丁": 6, "壬": 6, "戊": 8, "癸": 8}


def load(name):
    path = DATA_DIR / name
    if not path.exists():
        fail("数据文件缺失：%s。请检查 Skill 包完整性。" % path.name)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail("数据文件解析失败：%s（%s）" % (path.name, exc))


def fail(msg):
    print("【错误】%s" % msg)
    sys.exit(2)


def warn(msg):
    print("【提示】%s" % msg)


# ---------------------------------------------------------------- 基础数据

def gua64():
    return load("gua64.json")["guas"]


def find_gua(token):
    """按序号、卦名、全名或拼音定位卦。"""
    guas = gua64()
    token = str(token).strip()
    for g in guas:
        if token in (str(g["no"]), g["name"], g.get("full", ""), g.get("pinyin", "")):
            return g
    for g in guas:  # 容错：部分匹配全名
        if token and token in g.get("full", ""):
            return g
    return None


def base():
    return load("base.json")


def trigram_lines(name):
    """八卦三爻，返回自下而上的 0/1 列表。"""
    return [int(c) for c in base()["trigrams"][name]["lines"]]


def hex_lines(gua):
    """六爻，自下而上 0/1。"""
    return trigram_lines(gua["lower"]) + trigram_lines(gua["upper"])


def draw(lines):
    """渲染卦画，自上而下。"""
    return [("▅▅▅▅▅" if v else "▅▅ ▅▅") for v in reversed(lines)]


def lines_to_gua(lines):
    """由六爻反查卦。"""
    for g in gua64():
        if hex_lines(g) == list(lines):
            return g
    return None


def gua_title(gua):
    return "%s（%s）第 %d 卦" % (gua.get("full", gua["name"]), gua["name"], gua["no"])


# ---------------------------------------------------------------- 干支换算

def ganzhi_index(n):
    return "%s%s" % (TIANGAN[n % 10], DIZHI[n % 12])


def day_ganzhi(y, m, d):
    ordinal = date(y, m, d).toordinal()
    anchor = date(*GANZHI_ANCHOR_DATE).toordinal()
    return (GANZHI_ANCHOR_INDEX + (ordinal - anchor)) % 60


def term_day(year, term_name):
    """21 世纪节气日期速算，返回该节气公历日。"""
    idx = TERM_NAMES.index(term_name)
    month = idx // 2 + 1
    yy = year % 100
    day = int(yy * 0.2422 + TERM_C[idx]) - int((yy - 1) / 4)
    if year in TERM_MINUS_ONE.get(term_name, []):
        day -= 1
    if year in TERM_PLUS_ONE.get(term_name, []):
        day += 1
    return date(year, month, day)


def year_pillar(y, m, d):
    """以立春为界定年柱。"""
    lichun = term_day(y, "立春")
    gy = y if date(y, m, d) >= lichun else y - 1
    return (gy - 4) % 60


def month_pillar(y, m, d):
    """以节气月为界定月柱，寅月为正月。"""
    # 节气月支：丑月(小寒起)、寅月(立春起)…… 起算点用「节」而非「气」
    jie_names = ["立春", "惊蛰", "清明", "立夏", "芒种", "小满", "立秋", "白露",
                 "寒露", "立冬", "大雪", "小寒"]
    # 校正：十二节顺序为 寅、卯、辰、巳、午、未、申、酉、戌、亥、子、丑
    jie_names = ["小寒", "立春", "惊蛰", "清明", "立夏", "芒种", "小暑",
                 "立秋", "白露", "寒露", "立冬", "大雪"]
    cur = date(y, m, d)
    starts = []
    for i, nm in enumerate(jie_names):
        mm = term_day(y, nm).month
        dd = term_day(y, nm).day
        starts.append((date(y, mm, dd), (i + 1) % 12))  # 小寒->丑(1)
    starts.sort()
    branch = 1
    for st, br in starts:
        if cur >= st:
            branch = br
    if cur < starts[0][0]:
        branch = 1
    # 月支序号：寅=2，与正月对应
    month_no = (branch - 2) % 12 + 1  # 1..12，1 为正月（寅月）
    year_gan = TIANGAN[(year_pillar(y, m, d)) % 10]
    start = YUE_GAN_START[year_gan]
    gan = (start + month_no - 1) % 10
    return (gan, branch % 12)


def hour_pillar(day_index, hour):
    day_gan = TIANGAN[day_index % 10]
    start = SHI_GAN_START[day_gan]
    branch = 0
    for name, h1, h2 in SHICHEN:
        if name == hour:
            branch = DIZHI.index(name)
            break
    else:
        fail("时辰无效：%s（可用：%s）" % (hour, " ".join(n for n, _, _ in SHICHEN)))
    gan = (start + branch) % 10
    return (gan, branch)


def branch_of_hour(hour24):
    h = hour24 % 24
    if h >= 23 or h < 1:
        return "子"
    return SHICHEN[(h + 1) // 2][0]


# ---------------------------------------------------------------- 纳甲装卦

# ---------------------------------------------------------------- 八字批命

GAN_YANG = set(["甲", "丙", "戊", "庚", "壬"])
JIE_NAMES = ["立春", "惊蛰", "清明", "立夏", "芒种", "小暑",
             "立秋", "白露", "寒露", "立冬", "大雪", "小寒"]


def gan_yinyang(gan):
    return "阳" if gan in GAN_YANG else "阴"


def idx_of(gan_idx, zhi_idx):
    """由天干序号与地支序号反查六十甲子序号。"""
    for i in range(60):
        if i % 10 == gan_idx and i % 12 == zhi_idx:
            return i
    return 0


def shishen(day_gan, other_gan):
    """日主与另一天干的十神关系。"""
    b = base()
    dw = b["tiangan_wu"][day_gan]
    ow = b["tiangan_wu"][other_gan]
    rel = wuxing_relation(dw, ow)
    if dw == ow:
        key = "同我"
    elif rel == "生":
        key = "我生"
    elif rel == "克":
        key = "我克"
    elif rel == "被克":
        key = "克我"
    else:
        key = "生我"
    same = gan_yinyang(day_gan) == gan_yinyang(other_gan)
    return load("bazi.json")["shishen"][key]["same" if same else "diff"]


def shishen_of_zhi(day_gan, zhi):
    """地支藏干（本气／中气／余气）相对日主的十神。"""
    cang = load("ganzhi.json")["canggan"][zhi]
    pos_names = ["本气", "中气", "余气"]
    out = []
    for i, cg in enumerate(cang):
        out.append((cg, pos_names[i] if i < 3 else "余气", shishen(day_gan, cg)))
    return out


def jie_dates(year):
    return [(term_day(year, nm), nm) for nm in JIE_NAMES]


def nearest_jie(dt, forward):
    """出生日之后（forward）或之前最近的一个「节」。"""
    best = None
    for y in (dt.year - 1, dt.year, dt.year + 1):
        for d, nm in jie_dates(y):
            if forward:
                if d > dt and (best is None or d < best[0]):
                    best = (d, nm)
            else:
                if d <= dt and (best is None or d > best[0]):
                    best = (d, nm)
    return best


def build_pillars(y, m, d, hour_name):
    yp = year_pillar(y, m, d)
    mg, mb = month_pillar(y, m, d)
    dp = day_ganzhi(y, m, d)
    hg, hb = hour_pillar(dp, hour_name)
    return [
        {"name": "年柱", "idx": yp, "gan": TIANGAN[yp % 10], "zhi": DIZHI[yp % 12]},
        {"name": "月柱", "idx": idx_of(mg, mb), "gan": TIANGAN[mg], "zhi": DIZHI[mb]},
        {"name": "日柱", "idx": dp, "gan": TIANGAN[dp % 10], "zhi": DIZHI[dp % 12]},
        {"name": "时柱", "idx": idx_of(hg, hb), "gan": TIANGAN[hg], "zhi": DIZHI[hb]},
    ]


def dayun_list(month_gan, month_zhi, forward, steps=8):
    out = []
    for i in range(1, steps + 1):
        sign = 1 if forward else -1
        out.append("%s%s" % (TIANGAN[(month_gan + sign * i) % 10],
                             DIZHI[(month_zhi + sign * i) % 12]))
    return out


def kongwang_of(day_idx):
    """日柱旬空，返回两个空亡地支。"""
    xun = (day_idx // 10) * 10
    return [DIZHI[(xun - 2) % 12], DIZHI[(xun - 1) % 12]]


def strength_score(day_gan, pillars):
    """得令、得地、得势三端打分。"""
    bz = load("bazi.json")["strength"]
    b = base()
    dw = b["tiangan_wu"][day_gan]
    month_zhi = pillars[1]["zhi"]
    mw = b["dizhi_wu"][month_zhi]
    rel = wuxing_relation(dw, mw)
    deling_key = {"比和": "同气", "被生": "生我", "生": "我生",
                  "被克": "克我", "克": "我克"}[rel]
    deling = bz["deling"][deling_key]
    rows = [("得令", "月支%s（%s）对日主%s（%s）：%s" % (
        month_zhi, mw, day_gan, dw, deling_key), deling)]
    total = deling
    for p in pillars:
        for cg, pos, _ in shishen_of_zhi(day_gan, p["zhi"]):
            if b["tiangan_wu"][cg] == dw:
                val = bz["dedi"][pos]
                total += val
                rows.append(("得地", "%s地支%s藏%s（%s）为日主根" % (
                    p["name"], p["zhi"], cg, pos), val))
    for p in pillars:
        if p["name"] == "日柱":
            continue
        rel2 = wuxing_relation(dw, b["tiangan_wu"][p["gan"]])
        key2 = {"比和": "同我", "被生": "生我", "生": "我生",
                "被克": "克我", "克": "我克"}[rel2]
        val = bz["deshi"][key2]
        total += val
        rows.append(("得势", "%s天干%s（%s）：%s" % (
            p["name"], p["gan"], b["tiangan_wu"][p["gan"]], key2), val))
    return total, rows


def judge_geju(day_gan, pillars):
    """月令透干取格；不透则取月令本气。"""
    month_zhi = pillars[1]["zhi"]
    cang = [c for c, _, _ in shishen_of_zhi(day_gan, month_zhi)]
    tian_gan = [pillars[0]["gan"], pillars[1]["gan"], pillars[3]["gan"]]
    pos_names = ["本气", "中气", "余气"]
    for i, cg in enumerate(cang):
        if cg in tian_gan:
            ss = shishen(day_gan, cg)
            where = [p["name"] for p in pillars if p["gan"] == cg][0]
            return ss, "月令%s（%s%s）透于%s" % (month_zhi, pos_names[i], cg, where)
    return shishen(day_gan, cang[0]), \
        "月令%s本气%s未透天干，按月令本气定格" % (month_zhi, cang[0])


def geju_label(ss):
    if ss in ("比肩", "劫财"):
        return "月令为比劫——不属八格，通论作建禄／月刃论，用神另寻财官食伤"
    return "%s格" % ss


def shensha_hits(day_gan, pillars):
    bz = load("bazi.json")
    zhis = {p["name"]: p["zhi"] for p in pillars}
    gans = {p["name"]: p["gan"] for p in pillars}
    key_map = {"日干": day_gan, "年支": zhis["年柱"], "月支": zhis["月柱"]}
    hits = []
    for item in bz["shensha"]:
        key = key_map.get(item["by"])
        if key is None or key not in item["table"]:
            continue
        targets = item["table"][key]
        pool = gans if item["by"] == "月支" else zhis
        for pname, val in pool.items():
            if val in targets:
                hits.append((item["name"], "%s=%s" % (item["by"], key), pname, item["desc"]))
    for item in bz["shensha_pillar"]:
        gz = pillars[2]["gan"] + pillars[2]["zhi"]
        if gz in item["pillars"]:
            hits.append((item["name"], "日柱%s" % gz, "日柱", item["desc"]))
    return hits


def wuxing_count(pillars):
    b = base()
    cnt = {"金": 0, "木": 0, "水": 0, "火": 0, "土": 0}
    for p in pillars:
        cnt[b["tiangan_wu"][p["gan"]]] += 1
        cnt[b["dizhi_wu"][p["zhi"]]] += 1
    return cnt


def tongguan_hint(cnt):
    """两行相战时的通关用神：取「我所生、又能生对方」的那一行。"""
    b = base()
    order = ["木", "火", "土", "金", "水"]
    pairs = []
    for a in order:
        for c in order:
            if a != c and cnt[a] >= 2 and cnt[c] >= 2 and b["wuxing"]["ke"][a] == c:
                pairs.append((cnt[a] + cnt[c], a, c))
    if not pairs:
        return None
    pairs.sort(reverse=True)
    _, a, c = pairs[0]
    for x in order:
        if b["wuxing"]["sheng"][a] == x and b["wuxing"]["sheng"][x] == c:
            if cnt[x] > 0:
                return "%s 与 %s 两行皆旺而相战，可取 %s 通关（%s生%s、%s生%s）" % (
                    a, c, x, a, x, x, c)
            return "%s 与 %s 两行皆旺而相战，宜取 %s 通关；命局本气未见 %s，需待岁运补足" % (
                a, c, x, x)
    return None


def gong_of(gua):
    b = base()
    for gname, info in b["gongs"].items():
        members = info["members"]
        if gua["name"] in members:
            return gname, info, members.index(gua["name"])
    fail("卦「%s」未在任何八宫中找到，数据异常。" % gua["name"])


def shi_ying(pos_in_gong):
    """0 本宫、1-5 一世至五世、6 游魂、7 归魂 → 世爻爻位（1-6）。"""
    if pos_in_gong == 0:
        shi = 6
    elif pos_in_gong <= 5:
        shi = pos_in_gong
    elif pos_in_gong == 6:
        shi = 4
    else:
        shi = 3
    return shi, (shi + 2) % 6 + 1


def liuqin(gong_wu, yao_wu):
    if yao_wu == gong_wu:
        return "兄弟"
    if base()["wuxing"]["sheng"][yao_wu] == gong_wu:
        return "父母"
    if base()["wuxing"]["sheng"][gong_wu] == yao_wu:
        return "子孙"
    if base()["wuxing"]["ke"][gong_wu] == yao_wu:
        return "妻财"
    if base()["wuxing"]["ke"][yao_wu] == gong_wu:
        return "官鬼"
    return "未知"


def najia_table(gua):
    gname, ginfo, pos = gong_of(gua)
    lines = hex_lines(gua)
    zhi_seq = ginfo["zhi"]
    gan_seq = ginfo["gan"]
    gong_wu = ginfo["wu"]
    shi, ying = shi_ying(pos)
    rows = []
    for i in range(6):
        gan = gan_seq[i]
        zhi = zhi_seq[i]
        zw = base()["dizhi_wu"][zhi]
        rows.append({
            "yao": i + 1,
            "line": lines[i],
            "ganzhi": "%s%s" % (gan, zhi),
            "wu": zw,
            "liuqin": liuqin(gong_wu, zw),
            "mark": ("世" if shi == i + 1 else "") + ("应" if ying == i + 1 else ""),
        })
    return {
        "gong": gname, "gong_wu": gong_wu, "pos": pos,
        "shi": shi, "ying": ying, "rows": rows,
    }


# ---------------------------------------------------------------- 命令实现

def cmd_list(args):
    guas = gua64()
    print("| 序号 | 卦名 | 全称 | 上卦 | 下卦 | 宫 | 宫序 |")
    print("|---|---|---|---|---|---|---|")
    for g in guas:
        gname, _, pos = gong_of(g)
        print("| %d | %s | %s | %s | %s | %s宫 | %s |" % (
            g["no"], g["name"], g.get("full", ""), g["upper"], g["lower"],
            gname, ["本宫", "一世", "二世", "三世", "四世", "五世", "游魂", "归魂"][pos]))
    print()
    print("共 64 卦。查某卦全文：`gua <卦名或序号>`。")


def cmd_gua(args):
    g = find_gua(args.target)
    if not g:
        fail("未找到卦「%s」。用 `list` 查看全部 64 卦名称与序号。" % args.target)
    print("## %s" % gua_title(g))
    print()
    print("**卦画**（自上而下）")
    print()
    for ln in draw(hex_lines(g)):
        print("    %s" % ln)
    print()
    print("**卦辞**：%s" % g["judgment"])
    if g.get("tuan"):
        print()
        print("**彖传**：%s" % g["tuan"])
    if g.get("image"):
        print()
        print("**象传**：%s" % g["image"])
    if g.get("yao"):
        print()
        print("**爻辞**")
        print()
        print("| 爻位 | 爻辞 | 小象传 |")
        print("|---|---|---|")
        for y in g["yao"]:
            print("| %s | %s | %s |" % (y["pos"], y["text"], y.get("xiang", "—")))
        for y in g.get("extra", []):
            print("| %s | %s | %s |" % (y["pos"], y["text"], y.get("xiang", "—")))
    print()
    gname, ginfo, pos = gong_of(g)
    print("**归属**：%s宫（五行属%s），%s" % (
        gname, ginfo["wu"],
        ["本宫卦", "一世卦", "二世卦", "三世卦", "四世卦", "五世卦", "游魂卦", "归魂卦"][pos]))
    print()
    warn("卦爻辞为通行本原文，解读属象征性、哲理性参考，不作为现实决策依据。")


def normalize_toss(values):
    """接受 6/7/8/9（自初爻到上爻），返回六爻与动爻。"""
    if len(values) != 6:
        fail("需要 6 个爻值（自初爻到上爻），收到 %d 个。" % len(values))
    out = []
    for v in values:
        if v not in (6, 7, 8, 9):
            fail("爻值只能是 6（老阴）、7（少阳）、8（少阴）、9（老阳），收到 %s。" % v)
        out.append(v)
    return out


def toss_to_lines(toss):
    lines = [1 if v in (7, 9) else 0 for v in toss]
    moving = [i + 1 for i, v in enumerate(toss) if v in (6, 9)]
    return lines, moving


def cmd_cast_coin(args):
    if args.random:
        toss = [random.choice([6, 7, 8, 9]) for _ in range(6)]
        source = "随机生成"
    elif args.backs is not None:
        if len(args.backs) != 6:
            fail("需要 6 个背数（每爻铜钱背面个数 0-3）。")
        toss = []
        for b in args.backs:
            if b not in (0, 1, 2, 3):
                fail("背数只能是 0-3，收到 %s。" % b)
            toss.append({0: 6, 1: 7, 2: 8, 3: 9}[b])
        source = "铜钱背数（初→上）%s" % fmt_list(args.backs)
    elif args.values:
        toss = normalize_toss(args.values)
        source = "爻值（初→上）%s" % fmt_list(args.values)
    else:
        fail("需提供 --random、--backs 或 6 个爻值（6/7/8/9）。")

    lines, moving = toss_to_lines(toss)
    ben = lines_to_gua(lines)
    if not ben:
        fail("本卦解析失败，数据异常。")
    changed = list(lines)
    for m in moving:
        changed[m - 1] = 1 - changed[m - 1]
    bian = lines_to_gua(changed) if moving else None

    print("## 金钱卦起卦结果")
    print()
    print("**来源**：%s" % source)
    print()
    print("| 爻位 | 爻值 | 阴阳 | 本卦 | 变卦 | 动爻 |")
    print("|---|---|---|---|---|---|")
    names = ["初爻", "二爻", "三爻", "四爻", "五爻", "上爻"]
    for i in range(6):
        changed_line = changed[i]
        print("| %s | %d | %s | %s | %s | %s |" % (
            names[i], toss[i], "阳" if lines[i] else "阴",
            draw([lines[i]])[0],
            draw([changed_line])[0] if moving else "—",
            "动" if (i + 1) in moving else ""))
    print()
    print("**本卦**：%s" % gua_title(ben))
    if bian:
        print("**变卦**：%s" % gua_title(bian))
        print("**动爻**：%s" % "、".join(names[m - 1] for m in moving))
    else:
        print("**变卦**：无（六爻皆静，以本卦卦辞断）")
    print()
    if bian:
        print("**断卦要点**：以本卦卦辞为体、变卦卦辞为用；动爻取该爻爻辞。")
        for m in moving:
            yao = ben["yao"][m - 1] if m - 1 < len(ben["yao"]) else None
            if yao:
                print("- %s：%s" % (yao["pos"], yao["text"]))
    else:
        print("**断卦要点**：六爻安静，取本卦卦辞「%s」" % ben["judgment"])
    print()
    warn("起卦为象征性推演，结果不作为现实决策依据。")


def cmd_cast_time(args):
    if args.numbers:
        if len(args.numbers) < 2:
            fail("数字起卦至少给两个数（上卦数、下卦数）。")
        a, b = args.numbers[0], args.numbers[1]
        up = (a - 1) % 8
        down = (b - 1) % 8
        moving = (args.numbers[2] - 1) % 6 + 1 if len(args.numbers) > 2 else \
                 (a + b - 1) % 6 + 1
        src = "数字 %s" % args.numbers
    elif args.lunar:
        vals = args.lunar
        if len(vals) != 4:
            fail("农历起卦需 4 个参数：年支序号 月 日 时支序号（如 7 8 12 6）。")
        y, mo, d, h = vals
        up = (y + mo + d - 1) % 8
        down = (y + mo + d + h - 1) % 8
        moving = (y + mo + d + h - 1) % 6 + 1
        src = "农历 年支%d %d月%d日 时支%d" % (y, mo, d, h)
    else:
        fail("需提供 --numbers 或 --lunar 参数。本引擎不内置农历换算，请自行提供农历年月日。")

    b = base()
    order = b["xiantian_order"]  # 先天卦序：乾1兑2离3震4巽5坎6艮7坤8
    up_name = order[up]
    down_name = order[down]
    ben = None
    for g in gua64():
        if g["upper"] == up_name and g["lower"] == down_name:
            ben = g
            break
    if not ben:
        fail("由上下卦 %s/%s 未匹配到卦，数据异常。" % (up_name, down_name))
    lines = hex_lines(ben)
    changed = list(lines)
    changed[moving - 1] = 1 - changed[moving - 1]
    bian = lines_to_gua(changed)
    hu_lines = [lines[1], lines[2], lines[3], lines[2], lines[3], lines[4]]
    hu = lines_to_gua(hu_lines)

    print("## 梅花易数起卦结果")
    print()
    print("**来源**：%s" % src)
    print()
    print("| 项目 | 内容 |")
    print("|---|---|")
    print("| 上卦 | %s |" % up_name)
    print("| 下卦 | %s |" % down_name)
    print("| 本卦 | %s |" % gua_title(ben))
    print("| 互卦 | %s |" % (gua_title(hu) if hu else "—"))
    print("| 变卦 | %s |" % (gua_title(bian) if bian else "—"))
    print("| 动爻 | 第 %d 爻 |" % moving)
    print("| 体卦 | %s（下卦） |" % down_name)
    print("| 用卦 | %s（上卦） |" % up_name)
    print()
    ti_wu = b["trigrams"][down_name]["wu"]
    yong_wu = b["trigrams"][up_name]["wu"]
    print("**体用关系**：体卦%s（五行属%s），用卦%s（五行属%s）→ %s" % (
        down_name, ti_wu, up_name, yong_wu, relation_tiyong(ti_wu, yong_wu)))
    print()
    if moving - 1 < len(ben["yao"]):
        y = ben["yao"][moving - 1]
        print("**动爻爻辞**：%s：%s" % (y["pos"], y["text"]))
    print()
    warn("梅花易数为象征性推演，结果不作为现实决策依据。")


def wuxing_relation(a, b):
    """a 对 b 的关系：生、被生、克、被克、比和。"""
    bdata = base()
    if bdata["wuxing"]["sheng"][a] == b:
        return "生"
    if bdata["wuxing"]["sheng"][b] == a:
        return "被生"
    if bdata["wuxing"]["ke"][a] == b:
        return "克"
    if bdata["wuxing"]["ke"][b] == a:
        return "被克"
    return "比和"


def relation_plain(a, b):
    rel = wuxing_relation(a, b)
    return {
        "生": "%s 生 %s（%s泄气）" % (a, b, a),
        "被生": "%s 生 %s（%s受补）" % (b, a, a),
        "克": "%s 克 %s（%s受抑）" % (a, b, b),
        "被克": "%s 克 %s（%s受抑）" % (b, a, a),
        "比和": "%s 与 %s 比和（同类）" % (a, b),
    }[rel]


def relation_tiyong(ti, yong):
    rel = wuxing_relation(ti, yong)
    return {
        "生": "体生用（耗，小吝）",
        "被生": "用生体（吉）",
        "克": "体克用（吉，费力而成）",
        "被克": "用克体（凶）",
        "比和": "比和（同类，吉）",
    }[rel]


def fmt_list(seq):
    return " ".join(str(x) for x in seq)


def cmd_najia(args):
    g = find_gua(args.target)
    if not g:
        fail("未找到卦「%s」。用 `list` 查看全部卦名。" % args.target)
    t = najia_table(g)
    print("## %s 纳甲装卦" % gua_title(g))
    print()
    print("**卦宫**：%s宫（五行属%s）　**世爻**：第%d爻　**应爻**：第%d爻" % (
        t["gong"], t["gong_wu"], t["shi"], t["ying"]))
    print()
    print("| 爻位 | 卦画 | 纳甲干支 | 爻五行 | 六亲 | 世应 |")
    print("|---|---|---|---|---|---|")
    names = ["初爻", "二爻", "三爻", "四爻", "五爻", "上爻"]
    for r in t["rows"]:
        print("| %s | %s | %s | %s | %s | %s |" % (
            names[r["yao"] - 1], draw([r["line"]])[0], r["ganzhi"],
            r["wu"], r["liuqin"], r["mark"] or "—"))
    print()
    print("**纳甲歌**：%s" % base()["gongs"][t["gong"]]["najia_ge"])
    print()
    print("**六亲取法**：以卦宫五行「%s」为我——生我者父母，同我者兄弟，我克者妻财，"
          "我生者子孙，克我者官鬼。" % t["gong_wu"])
    print()
    warn("装卦仅为干支与六亲装配，不含旺衰、旬空、月日建等进阶判断，不作现实决策依据。")


def cmd_ganzhi(args):
    if args.year:
        y = args.year
        idx = (y - 4) % 60
        print("## 干支纪年")
        print()
        print("| 公历年份 | 干支 | 生肖 |")
        print("|---|---|---|")
        print("| %d | %s | %s |" % (y, ganzhi_index(idx),
                                    base()["shengxiao"][DIZHI[idx % 12]]))
        print()
        warn("纪年以农历正月初一/立春为界的流派不同，此处按立春分界取近似，"
             "交节气当日需人工核对。")
        return
    if args.date:
        try:
            dt = datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError:
            fail("日期格式需为 YYYY-MM-DD，收到 %s。" % args.date)
    else:
        dt = date.today()
    y, m, d = dt.year, dt.month, dt.day
    yp = year_pillar(y, m, d)
    mg, mb = month_pillar(y, m, d)
    dp = day_ganzhi(y, m, d)
    print("## 干支换算")
    print()
    print("**公历**：%s" % dt.isoformat())
    print()
    print("| 柱 | 干支 | 说明 |")
    print("|---|---|---|")
    print("| 年柱 | %s | 以立春分界 |" % ganzhi_index(yp))
    print("| 月柱 | %s%s | %s月，以节气分界 |" % (
        TIANGAN[mg], DIZHI[mb], ["正", "二", "三", "四", "五", "六",
                                 "七", "八", "九", "十", "十一", "十二"][(mb - 2) % 12]))
    print("| 日柱 | %s | 精确计算 |" % ganzhi_index(dp))
    hour = args.hour if args.hour else None
    if hour:
        hg, hb = hour_pillar(dp, hour)
        print("| 时柱 | %s%s | %s时 |" % (TIANGAN[hg], DIZHI[hb], hour))
    else:
        print("| 时柱 | — | 需 --hour 指定时辰 |")
    print()
    print("**纳音**：年柱 %s" % load("ganzhi.json")["nayin"][yp % 60])
    print()
    warn("节气按 21 世纪速算公式，误差 ±1 日；交节前后一日、真太阳时与晚子时换日"
         "需人工核对。日柱为精确值。")


def cmd_bazi(args):
    bz = load("bazi.json")
    b = base()
    nayin = load("ganzhi.json")["nayin"]
    try:
        dt = datetime.strptime(args.date, "%Y-%m-%d").date()
    except ValueError:
        fail("日期格式需为 YYYY-MM-DD，收到 %s。" % args.date)
    gender = args.gender
    if gender not in ("男", "女"):
        fail("--gender 只能是 男 或 女，收到 %s。" % gender)
    hour = args.hour
    if hour.isdigit():
        hour = branch_of_hour(int(hour))
    if hour not in DIZHI:
        fail("时辰无效：%s（用子丑寅卯辰巳午未申酉戌亥，或 0-23 的小时数）" % hour)

    pillars = build_pillars(dt.year, dt.month, dt.day, hour)
    day_gan = pillars[2]["gan"]
    day_wu = b["tiangan_wu"][day_gan]

    print("## 八字排盘：%s %s时（%s命）" % (dt.isoformat(), hour, gender))
    print()
    print("**日主**：%s（五行属%s，%s干）" % (day_gan, day_wu, gan_yinyang(day_gan)))
    print()

    print("### 四柱")
    print()
    print("| 柱 | 干支 | 纳音 | 天干十神 | 地支藏干（十神） | 宫位 |")
    print("|---|---|---|---|---|---|")
    for p in pillars:
        cang_txt = "、".join("%s(%s)" % (cg, ss)
                            for cg, _, ss in shishen_of_zhi(day_gan, p["zhi"]))
        print("| %s | %s%s | %s | %s | %s | %s |" % (
            p["name"], p["gan"], p["zhi"], nayin[p["idx"] % 60],
            shishen(day_gan, p["gan"]), cang_txt,
            bz["gongwei"][p["name"]].split("；")[0]))

    total, rows = strength_score(day_gan, pillars)
    th = bz["strength"]["threshold"]
    if total >= th["strong"]:
        verdict = "偏强"
    elif total <= th["weak"]:
        verdict = "偏弱"
    else:
        verdict = "中和"
    print()
    print("### 日主强弱（得分 %+d → %s）" % (total, verdict))
    print()
    print("| 端 | 依据 | 分值 |")
    print("|---|---|---|")
    for k, why, val in rows:
        print("| %s | %s | %+d |" % (k, why, val))
    print()
    print("**判定阈值**：≥ %d 偏强，≤ %d 偏弱，其间为中和。"
          "权重为本引擎设定（非古籍定论），可按上表逐条复核。" % (th["strong"], th["weak"]))

    y_gan = pillars[0]["gan"]
    yang_year = y_gan in GAN_YANG
    forward = (yang_year and gender == "男") or (not yang_year and gender == "女")
    target = nearest_jie(dt, forward)
    days = abs((target[0] - dt).days) if target else 0
    years = days // bz["dayun"]["days_per_year"]
    months = (days % bz["dayun"]["days_per_year"]) * bz["dayun"]["months_per_day"]
    print()
    print("### 大运（%s行）" % ("顺" if forward else "逆"))
    print()
    print("**顺逆**：年干%s为%s干、%s命 → %s行" % (
        y_gan, gan_yinyang(y_gan), gender, "顺" if forward else "逆"))
    print()
    print("**起运**：%s（%s）距出生 %d 天 → 约 %d 岁 %d 个月起运" % (
        target[1], target[0].isoformat(), days, years, months))
    print()
    print("| 步 | 大运 | 十神 | 起运岁 | 约起运年 | 纳音 |")
    print("|---|---|---|---|---|---|")
    mg0, mb0 = month_pillar(dt.year, dt.month, dt.day)
    for i, gz in enumerate(dayun_list(mg0, mb0, forward)):
        age = years + i * bz["dayun"]["years_per_step"]
        gi = TIANGAN.index(gz[0])
        zi = DIZHI.index(gz[1])
        print("| %d | %s | %s | %d 岁 | %d | %s |" % (
            i + 1, gz, shishen(day_gan, gz[0]), age, dt.year + age, nayin[idx_of(gi, zi)]))

    if years > 0:
        print()
        print("### 小运（起运前逐年）")
        print()
        xy = bz["xiaoyun"][gender]
        s_idx = idx_of(TIANGAN.index(xy["start"][0]), DIZHI.index(xy["start"][1]))
        print("**起法**：%s命一岁起 %s %s行（%s）" % (
            gender, xy["start"], xy["dir"], bz["xiaoyun"]["note"].split("（")[0]))
        print()
        print("| 岁 | 小运 |")
        print("|---|---|")
        for n in range(1, min(years, 12) + 1):
            k = (s_idx + (n - 1)) % 60 if xy["dir"] == "顺" else (s_idx - (n - 1)) % 60
            print("| %d | %s |" % (n, ganzhi_index(k)))

    print()
    print("### 神煞")
    print()
    hits = shensha_hits(day_gan, pillars)
    kw = kongwang_of(pillars[2]["idx"])
    print("| 神煞 | 判定依据 | 落在 | 含义 |")
    print("|---|---|---|---|")
    for nm, why, where, desc in hits:
        print("| %s | %s | %s | %s |" % (nm, why, where, desc))
    kw_in = [p["name"] for p in pillars if p["zhi"] in kw]
    print("| 空亡 | 日柱旬空 %s%s | %s | 该柱力量减、事易落空 |" % (
        kw[0], kw[1], "、".join(kw_in) if kw_in else "命局不犯"))
    if not hits:
        print()
        print("（未命中内置神煞表，仅列空亡）")

    ss, reason = judge_geju(day_gan, pillars)
    print()
    print("### 格局")
    print()
    print("**%s** —— %s" % (geju_label(ss), reason))

    print()
    print("### 用神喜忌")
    print()
    print("**扶抑**：日主%s → 宜 %s" % (verdict, "、".join(bz["yongshen"][verdict])))
    print("**调候**：%s" % bz["diaohou"][pillars[1]["zhi"]])
    cnt = wuxing_count(pillars)
    tg = tongguan_hint(cnt)
    if tg:
        print("**通关**：%s" % tg)
    print()
    print("**五行分布**：%s" % "　".join("%s %d" % (w, cnt[w])
                                   for w in ["木", "火", "土", "金", "水"]))
    print()
    print("【注意】用神取法各派不一，此处按子平扶抑通论，另附调候与通关线索，"
          "非唯一结论。")

    if args.liunian:
        ly = args.liunian
        li = (ly - 4) % 60
        lg, lz = TIANGAN[li % 10], DIZHI[li % 12]
        print()
        print("### 流年 %d（%s%s）" % (ly, lg, lz))
        print()
        print("| 项目 | 内容 |")
        print("|---|---|")
        print("| 流年十神 | %s |" % shishen(day_gan, lg))
        rels = []
        for p in pillars:
            for cat, pairs in b["dizhi_relations"].items():
                for k in pairs:
                    pz = p["zhi"]
                    if len(k) == 2 and ((k[0] == lz and k[1] == pz) or
                                        (k[1] == lz and k[0] == pz)):
                        rels.append("与%s%s%s（%s）" % (p["name"], pz, cat, k))
        print("| 与命局作用 | %s |" % ("；".join(sorted(set(rels)))
                                   if rels else "未构成既定冲合刑害"))

    print()
    if args.city:
        lon = bz["cities"].get(args.city)
        if lon is not None:
            print("【真太阳时】%s 经度约 %.2f°，地方时与北京时间相差约 %+.0f 分钟。"
                  "本引擎按北京时间排盘不作换算；若出生时刻接近时辰交界，需人工核对。"
                  % (args.city, lon, (lon - 120.0) * 4.0))
        else:
            print("【真太阳时】未收录城市「%s」，按北京时间排盘。内置城市见 bazi.json。" % args.city)
    warn("节气按 21 世纪速算公式，误差 ±1 日；起运岁数相应约 ±0.4 岁偏差；"
         "交节当日、晚子时出生需人工核对。日柱为精确值。"
         "批命结果为传统文化参考，不定论吉凶，不作为医疗、法律、投资、生育等现实决策依据。")


def cmd_wuxing(args):
    b = base()
    w = b["wuxing"]
    if len(args.items) == 1:
        x = args.items[0]
        if x not in w["sheng"]:
            fail("五行只能是 金木水火土，收到 %s。" % x)
        print("## 五行「%s」" % x)
        print()
        print("| 关系 | 对象 |")
        print("|---|---|")
        print("| 我生（泄） | %s |" % w["sheng"][x])
        print("| 生我（补） | %s |" % [k for k, v in w["sheng"].items() if v == x][0])
        print("| 我克（耗） | %s |" % w["ke"][x])
        print("| 克我（抑） | %s |" % [k for k, v in w["ke"].items() if v == x][0])
        print()
        print("**方位**：%s　**季节**：%s　**天干**：%s　**地支**：%s" % (
            b["wuxing_info"][x]["fang"], b["wuxing_info"][x]["ji"],
            b["wuxing_info"][x]["gan"], b["wuxing_info"][x]["zhi"]))
        return
    if len(args.items) != 2:
        fail("wuxing 接受 1 个或 2 个五行参数。")
    a, c = args.items
    if a not in w["sheng"] or c not in w["sheng"]:
        fail("五行只能是 金木水火土。")
    print("## 五行关系：%s 与 %s" % (a, c))
    print()
    print("**结论**：%s" % relation_plain(a, c))
    print()
    print("| 关系 | 判定 |")
    print("|---|---|")
    print("| %s 生 %s | %s |" % (a, c, "是" if w["sheng"][a] == c else "否"))
    print("| %s 生 %s | %s |" % (c, a, "是" if w["sheng"][c] == a else "否"))
    print("| %s 克 %s | %s |" % (a, c, "是" if w["ke"][a] == c else "否"))
    print("| %s 克 %s | %s |" % (c, a, "是" if w["ke"][c] == a else "否"))


def cmd_xiang(args):
    b = base()
    name = args.target
    if name in b["trigrams"]:
        t = b["trigrams"][name]
        print("## 八卦类象：%s" % name)
        print()
        print("| 项目 | 内容 |")
        print("|---|---|")
        print("| 卦画 | %s |" % " ".join(draw([int(c) for c in t["lines"]])))
        print("| 自然 | %s |" % t["nature"])
        print("| 五行 | %s |" % t["wu"])
        print("| 卦德 | %s |" % t["de"])
        print("| 先天方位 | %s |" % t["xt_fang"])
        print("| 后天方位 | %s |" % t["ht_fang"])
        print("| 人物 | %s |" % t["person"])
        print("| 身体 | %s |" % t["body"])
        print("| 动物 | %s |" % t["animal"])
        print("| 时序 | %s |" % t["time"])
        print("| 人事 | %s |" % t["matter"])
        print("| 数字 | %s |" % t["number"])
        return
    g = find_gua(name)
    if g:
        print("## %s 卦象组合" % gua_title(g))
        print()
        print("| 项目 | 上卦（%s） | 下卦（%s） |" % (g["upper"], g["lower"]))
        print("|---|---|---|")
        keys = [("nature", "自然"), ("wu", "五行"), ("de", "卦德"),
                ("body", "身体"), ("person", "人物")]
        for k, label in keys:
            print("| %s | %s | %s |" % (
                label, b["trigrams"][g["upper"]][k], b["trigrams"][g["lower"]][k]))
        print()
        print("**象传**：%s" % g.get("image", "—"))
        print()
        print("**卦辞**：%s" % g["judgment"])
        return
    fail("未找到八卦「%s」或对应卦名。八卦为：%s。" % (
        name, "".join(b["trigrams"].keys())))


def cmd_relation(args):
    b = base()
    items = [x.strip() for x in args.items]
    is_dz = all(x in DIZHI for x in items)
    is_tg = all(x in TIANGAN for x in items)
    if not (is_dz or is_tg):
        fail("请全部输入地支（子丑寅卯辰巳午未申酉戌亥）"
             "或全部输入天干（甲乙丙丁戊己庚辛壬癸）。")
    table = b["dizhi_relations"] if is_dz else b["tiangan_relations"]
    print("## 干支关系：%s" % " ".join(items))
    print()
    hits = []
    for cat, pairs in table.items():
        for k, v in pairs.items():
            if len(items) == 1:
                if items[0] in k:
                    hits.append((cat, k, v))
            elif len(set(k)) == len(set(items)) and set(k) == set(items):
                hits.append((cat, k, v))
    if not hits:
        print("关系表中未收录该组合的既定关系。")
        print()
        print("收录范围：六合、六冲、三合局、三会方、六害、相刑、相破"
              "（天干为五合、相冲）。")
        return
    print("| 关系类别 | 组合 | 结果 |")
    print("|---|---|---|")
    for cat, k, v in hits:
        print("| %s | %s | %s |" % (cat, k, v))


def cmd_env(args):
    print("## 环境自检")
    print()
    print("| 检查项 | 结果 |")
    print("|---|---|")
    print("| Python 版本 | %d.%d.%d |" % sys.version_info[:3])
    ok = True
    for f in ("base.json", "gua64.json", "ganzhi.json", "bazi.json"):
        p = DATA_DIR / f
        exists = p.exists()
        ok = ok and exists
        print("| 数据文件 %s | %s |" % (f, "存在" if exists else "缺失"))
    print("| 外部依赖 | 无（纯标准库） |")
    print("| 网络访问 | 无 |")
    print()
    if ok:
        guas = gua64()
        bad = []
        for g in guas:
            try:
                gong_of(g)
            except SystemExit:
                bad.append(g["name"])
        print("| 64 卦八宫归属 | %s |" % ("全部匹配" if not bad else "异常：%s" % bad))
        print("| 数据条目 | %d 卦 |" % len(guas))
        print()
        print("**结论**：%s" % ("ready" if not bad else "partial：存在卦宫归属异常"))
    else:
        print("**结论**：needs_setup：缺少数据文件，请重新安装 Skill 包。")
        sys.exit(2)


def main():
    p = argparse.ArgumentParser(
        prog="yijing.py",
        description="易经推演引擎：起卦、查卦辞爻辞、纳甲装卦、干支换算、五行与类象查询")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="列出 64 卦总表").set_defaults(func=cmd_list)

    q = sub.add_parser("gua", help="查卦全文：卦辞、彖传、象传、爻辞")
    q.add_argument("target", help="卦名、全称、拼音或 1-64 序号")
    q.set_defaults(func=cmd_gua)

    c = sub.add_parser("cast-coin", help="金钱卦起卦")
    c.add_argument("values", nargs="*", type=int, help="6 个爻值 6/7/8/9，自初爻到上爻")
    c.add_argument("--random", action="store_true", help="随机生成六爻")
    c.add_argument("--backs", nargs=6, type=int, metavar="N",
                   help="每爻铜钱背面个数 0-3，自初爻到上爻")
    c.set_defaults(func=cmd_cast_coin)

    t = sub.add_parser("cast-time", help="梅花易数起卦（数字或农历年月日时）")
    t.add_argument("--numbers", nargs="+", type=int,
                   help="数字起卦：上卦数 下卦数 [动爻数]")
    t.add_argument("--lunar", nargs=4, type=int, metavar=("年支", "月", "日", "时支"),
                   help="农历起卦：年支序号 月 日 时支序号（子1..亥12）")
    t.set_defaults(func=cmd_cast_time)

    n = sub.add_parser("najia", help="纳甲装卦：世应、六亲、干支")
    n.add_argument("target", help="卦名或序号")
    n.set_defaults(func=cmd_najia)

    g = sub.add_parser("ganzhi", help="干支换算")
    g.add_argument("--date", help="公历日期 YYYY-MM-DD，默认今天")
    g.add_argument("--year", type=int, help="仅查年份干支")
    g.add_argument("--hour", help="时辰名，如 午、子")
    g.set_defaults(func=cmd_ganzhi)

    z = sub.add_parser("bazi", help="八字排盘与批命：四柱、十神、大运、神煞、格局、用神")
    z.add_argument("--date", required=True, help="公历出生日期 YYYY-MM-DD")
    z.add_argument("--hour", required=True,
                   help="出生时辰：子丑寅卯辰巳午未申酉戌亥，或 0-23 的小时数")
    z.add_argument("--gender", required=True, help="性别：男 / 女（大运顺逆依据）")
    z.add_argument("--city", help="出生城市，用于提示真太阳时偏差（不自动改盘）")
    z.add_argument("--liunian", type=int, help="查询指定流年与命局作用")
    z.set_defaults(func=cmd_bazi)

    w = sub.add_parser("wuxing", help="五行生克查询")
    w.add_argument("items", nargs="+", help="1 个或 2 个五行：金木水火土")
    w.set_defaults(func=cmd_wuxing)

    x = sub.add_parser("xiang", help="八卦类象查询")
    x.add_argument("target", help="八卦名或卦名")
    x.set_defaults(func=cmd_xiang)

    r = sub.add_parser("relation", help="干支冲合刑害查询")
    r.add_argument("items", nargs="+", help="1-3 个地支或天干")
    r.set_defaults(func=cmd_relation)

    e = sub.add_parser("env", help="环境自检")
    e.set_defaults(func=cmd_env)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
