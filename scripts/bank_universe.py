#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
银行标的清单（谷子地五维模型追踪对象）

标的范围（用户决策 2026-07-12）：
  - 6 只 A 股：招商银行 / 工商银行 / 建设银行 / 农业银行 / 中国银行 / 宁波银行
  - 交通银行：默认排除（估值陷阱，谷子地点评明确不推荐）
  - 招商银行 H（03968）：若数据源可稳定获取则纳入，否则取消（INCLUDE_H 开关）

每只银行需要三类代码：
  - tencent : 腾讯行情 qt.gtimg.cn 的代码（sh/sz/r_hk 前缀）
  - baostock: baostock 历史数据代码（sh./sz. 前缀，港股不支持）
  - akshare : akshare 财务接口 symbol（SH/SZ 前缀，港股单独处理）
"""
from dataclasses import dataclass, field

# 是否纳入招商银行 H 股（探针验证可获取后改 True）
INCLUDE_H = False

@dataclass
class Bank:
    code: str          # 用户可读的 A 股/港股代码
    name: str          # 中文名
    short: str         # 简称（用于图表/表格）
    tencent: str       # 腾讯行情代码
    baostock: str      # baostock 代码（港股为空）
    akshare: str       # akshare 财务 symbol
    is_hk: bool = False
    color: str = "#5470c6"   # 图表配色

# ---- A 股六大行 ----
BANKS_A = [
    Bank("600036", "招商银行", "招行", "sh600036", "sh.600036", "SH600036", color="#c23531"),
    Bank("601398", "工商银行", "工行", "sh601398", "sh.601398", "SH601398", color="#2f4554"),
    Bank("601939", "建设银行", "建行", "sh601939", "sh.601939", "SH601939", color="#61a0a8"),
    Bank("601288", "农业银行", "农行", "sh601288", "sh.601288", "SH601288", color="#d48265"),
    Bank("601988", "中国银行", "中行", "sh601988", "sh.601988", "SH601988", color="#91c7ae"),
    Bank("002142", "宁波银行", "宁波", "sz002142", "sz.002142", "SZ002142", color="#749f83"),
]

# ---- 招商银行 H 股（可选）----
BANK_CMB_H = Bank("03968", "招商银行H", "招行H", "r_hk03968", "", "",
                  is_hk=True, color="#ca8622")

def all_banks() -> list:
    """返回当前生效的全部标的（含 H 当且仅当 INCLUDE_H=True）。"""
    if INCLUDE_H:
        return BANKS_A + [BANK_CMB_H]
    return list(BANKS_A)

def tencent_codes() -> list:
    return [b.tencent for b in all_banks()]

if __name__ == "__main__":
    for b in all_banks():
        print(b.code, b.name, b.tencent, b.baostock, b.akshare)
