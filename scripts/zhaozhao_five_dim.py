#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
招招五维评分引擎（纯计算，无 IO）

五维模型（每维 0-20 分，总计 0-100）：
  维度1 资产质量  : 不良率(NPL)↓、拨备覆盖率↑、不良生成率↓
  维度2 负债结构  : 活期存款占比↑、存款占比↑、零售存款占比↑
  维度3 中间业务  : 非息收入占比↑（财富管理/结算/投行）
  维度4 资本实力  : RORWA↑、核心一级资本充足率↑
  维度5 管理层    : ROE 稳定性、分红率连续性与战略定力（用 ROE/分红率/零售护城河代理）

评分采用分段线性映射，阈值参照招招五维模型通用口径（详见 docs/scoring.md）。
所有输入缺失时该维给 0 分，并在备注标注「数据缺失」，不臆造。

买入信号（buy_signal）支持两种估值风格：
  - "yield"  收益型：基于 PB 破净程度 + 股息率（适用于高分红的招行/四大行）
  - "growth" 成长型：基于 PE + ROE（适用于高 ROE、低分红率的股份行/城商行，如宁波银行）
"""
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Fundamentals:
    """单只银行最新可得的季度财务原始输入（季度更新，非每日变化）。"""
    code: str
    name: str
    as_of: str                      # 数据截止（如 2026Q1）
    # 维度1 资产质量
    npl: Optional[float] = None     # 不良贷款率 %
    provision_coverage: Optional[float] = None   # 拨备覆盖率 %
    npl_generate: Optional[float] = None         # 不良生成率 %
    # 维度2 负债结构
    current_deposit_ratio: Optional[float] = None  # 活期存款占比 %
    deposit_ratio: Optional[float] = None          # 存款/负债 %
    retail_deposit_ratio: Optional[float] = None   # 零售存款占比 %
    # 维度3 中间业务
    non_interest_ratio: Optional[float] = None     # 非息收入占比 %
    # 维度4 资本实力
    rorwa: Optional[float] = None                  # 风险加权资产收益率 %
    core_tier1: Optional[float] = None             # 核心一级资本充足率 %
    # 维度5 管理层（代理指标）
    roe: Optional[float] = None                    # 加权 ROE %
    div_payout: Optional[float] = None             # 分红率 %
    retail_focus: Optional[float] = None           # 零售护城河（0-1，定性代理；招行/宁波高）
    # 估值（每日由行情注入，非财务原始）
    pb: Optional[float] = None
    pe: Optional[float] = None
    div_yield: Optional[float] = None
    price: Optional[float] = None

    def missing(self) -> list:
        fields = ["npl","provision_coverage","current_deposit_ratio","non_interest_ratio",
                  "rorwa","core_tier1","roe","div_payout"]
        return [f for f in fields if getattr(self, f) is None]


def _seg(v, breaks):
    """
    分段线性打分。breaks: [(阈值, 分值), ...] 升序；
    返回在 v 与相邻阈值间线性插值后的分值（0-20）。
    例：_seg(1.2, [(1.0,20),(1.3,14),(1.5,8),(2.0,0)]) -> 不良率1.2位于1.0~1.3间
    """
    if v is None:
        return 0.0
    pts = sorted(breaks, key=lambda x: x[0])
    if v <= pts[0][0]:
        return float(pts[0][1])
    if v >= pts[-1][0]:
        return float(pts[-1][1])
    for i in range(len(pts) - 1):
        x0, y0 = pts[i]
        x1, y1 = pts[i + 1]
        if x0 <= v <= x1:
            return y0 + (y1 - y0) * (v - x0) / (x1 - x0)
    return 0.0


def score_asset_quality(f: Fundamentals) -> tuple:
    """维度1：资产质量（满分20）"""
    s = 0.0
    notes = []
    # 不良率：越低越好
    s += _seg(f.npl, [(0.8, 10), (1.0, 9), (1.3, 6), (1.6, 3), (2.2, 0)])
    # 拨备覆盖率：越高越好
    s += _seg(f.provision_coverage, [(500, 10), (350, 8), (250, 6), (180, 3), (120, 0)])
    if f.npl is None: notes.append("不良率缺失")
    if f.provision_coverage is None: notes.append("拨备覆盖率缺失")
    return round(s, 1), notes


def score_liability(f: Fundamentals) -> tuple:
    """维度2：负债结构（满分20）"""
    s = 0.0
    notes = []
    s += _seg(f.current_deposit_ratio, [(55, 10), (50, 8), (42, 5), (35, 2), (28, 0)])
    if f.current_deposit_ratio is None: notes.append("活期占比缺失")
    if f.deposit_ratio is not None:
        s += _seg(f.deposit_ratio, [(85, 6), (80, 4), (72, 2), (65, 0)])
    elif f.retail_deposit_ratio is not None:
        s += _seg(f.retail_deposit_ratio, [(55, 6), (45, 4), (35, 2), (25, 0)])
    else:
        notes.append("存款结构缺失")
    return round(s, 1), notes


def score_intermediary(f: Fundamentals) -> tuple:
    """维度3：中间业务（满分20）"""
    s = 0.0
    notes = []
    s += _seg(f.non_interest_ratio, [(40, 20), (33, 16), (25, 10), (18, 5), (12, 0)])
    if f.non_interest_ratio is None: notes.append("非息占比缺失")
    return round(s, 1), notes


def score_capital(f: Fundamentals) -> tuple:
    """维度4：资本实力（满分20）"""
    s = 0.0
    notes = []
    s += _seg(f.rorwa, [(2.2, 10), (1.8, 8), (1.5, 5), (1.2, 2), (0.9, 0)])
    if f.rorwa is None: notes.append("RORWA缺失")
    s += _seg(f.core_tier1, [(13, 10), (11, 8), (9.5, 5), (8.5, 2), (7.5, 0)])
    if f.core_tier1 is None: notes.append("核心一级资本充足率缺失")
    return round(s, 1), notes


def score_management(f: Fundamentals) -> tuple:
    """维度5：管理层（满分20，用 ROE/分红率/零售护城河代理）"""
    s = 0.0
    notes = []
    s += _seg(f.roe, [(16, 8), (14, 6), (12, 4), (10, 2), (8, 0)])
    if f.roe is None: notes.append("ROE缺失")
    s += _seg(f.div_payout, [(40, 6), (33, 5), (30, 4), (25, 2), (15, 0)])
    if f.div_payout is None: notes.append("分红率缺失")
    if f.retail_focus is not None:
        s += round(f.retail_focus * 6, 1)   # 零售护城河 0-6
    else:
        notes.append("零售护城河未评级")
    return round(s, 1), notes


def score_all(f: Fundamentals) -> dict:
    """返回完整评分结果字典。"""
    d1, n1 = score_asset_quality(f)
    d2, n2 = score_liability(f)
    d3, n3 = score_intermediary(f)
    d4, n4 = score_capital(f)
    d5, n5 = score_management(f)
    total = round(d1 + d2 + d3 + d4 + d5, 1)
    return {
        "code": f.code,
        "name": f.name,
        "as_of": f.as_of,
        "dims": {
            "asset_quality": {"score": d1, "max": 20, "notes": n1},
            "liability": {"score": d2, "max": 20, "notes": n2},
            "intermediary": {"score": d3, "max": 20, "notes": n3},
            "capital": {"score": d4, "max": 20, "notes": n4},
            "management": {"score": d5, "max": 20, "notes": n5},
        },
        "total": total,
        "missing": f.missing(),
    }


def buy_signal(f: Fundamentals, valuation_style: str = "yield") -> dict:
    """
    买入信号 + 动态买入区间。
    支持两种估值风格（valuation_style）：
      - "yield"  收益型：基于 PB 破净程度与股息率，结合五维总分（招行/四大行）
      - "growth" 成长型：基于 PE 与 ROE，结合五维总分（高 ROE 低分红率的股份行/城商行）
    返回：signal, zone_low, zone_high, reason
    """
    total = score_all(f)["total"]
    dy = f.div_yield
    dy_s = f"{dy:.1f}%" if dy is not None else "—"
    pe = f.pe
    roe = f.roe
    roe_s = f"{roe:.1f}%" if roe is not None else "—"

    if valuation_style == "growth":
        # —— 成长型估值：PE + ROE ——
        if pe is None:
            return {"signal": "UNKNOWN", "zone_low": None, "zone_high": None,
                    "reason": "PE缺失，无法判定", "valuation_style": "growth"}
        if pe < 6 and (roe is None or roe >= 15):
            sig = "STRONG_BUY"
            reason = f"PE{pe:.1f}低 + ROE{roe_s}高，成长型黄金坑"
        elif pe < 8:
            sig = "BUY"
            reason = f"PE{pe:.1f}偏低，成长型合理估值"
        elif pe < 12:
            sig = "HOLD"
            reason = f"PE{pe:.1f}中性，观望"
        elif pe >= 15 and (roe is None or roe < 14):
            sig = "REDUCE"
            reason = f"PE{pe:.1f}偏高 + ROE{roe_s}走弱，性价比下降"
        else:
            sig = "HOLD"
            reason = f"PE{pe:.1f}中性，观望"
        if total >= 100 and sig == "HOLD":
            sig = "BUY"
            reason += "；五维总分极高，上调至买入"
        return {"signal": sig, "zone_low": None, "zone_high": None,
                "reason": reason, "valuation_style": "growth"}

    # —— 收益型估值：PB 破净 + 股息率 ——
    pb = f.pb
    if pb is None:
        return {"signal": "UNKNOWN", "zone_low": None, "zone_high": None,
                "reason": "PB缺失，无法判定", "valuation_style": "yield"}
    if pb < 0.7 and (dy is None or dy >= 5.0):
        sig = "STRONG_BUY"
        reason = f"PB{pb:.2f}深度破净 + 股息{dy_s}，黄金坑"
    elif pb < 0.9 and (dy is None or dy >= 4.0):
        sig = "BUY"
        reason = f"PB{pb:.2f}破净附近 + 股息{dy_s}，低估"
    elif pb < 1.2:
        sig = "HOLD"
        reason = f"PB{pb:.2f}接近净资产，合理偏高，持有"
    elif pb > 1.5 and (dy is None or dy < 3.0):
        sig = "REDUCE"
        reason = f"PB{pb:.2f}偏高 + 股息{dy_s}薄，性价比下降"
    else:
        sig = "HOLD"
        reason = f"PB{pb:.2f}中性，观望"
    # 五维加权：高评分可上调一档
    if total >= 105 and sig in ("HOLD",):
        sig = "BUY"
        reason += "；五维总分极高，上调至买入"
    return {"signal": sig, "zone_low": None, "zone_high": None,
            "reason": reason, "valuation_style": "yield"}


# 信号中文映射与配色（供 HTML 渲染）
SIGNAL_CN = {
    "STRONG_BUY": ("强烈买入", "#c23531"),
    "BUY": ("买入", "#d48265"),
    "HOLD": ("持有", "#e6a23c"),
    "REDUCE": ("减配", "#749f83"),
    "UNKNOWN": ("未知", "#999999"),
}
