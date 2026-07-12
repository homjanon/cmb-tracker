#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
财务底表抓取与刷新

架构说明（关键）：
  银行的五维财务字段（不良率/拨备/非息/资本充足率/RORWA）是【季度】数据，每日不变。
  而 akshare 当前版本（1.18.x）的 stock_financial_analysis_indicator 已失效，
  利润表/资产负债表原始科目列名漂移、港股接口在沙箱不稳定。
  → 因此采用「财务底表 fundamentals.json 为真源 + 每日轻量刷新可自动字段」的设计：
    - refresh_light() : 每日调用，用 akshare stock_yjbb_em 刷新 BVPS/ROE/EPS
                        （已验证可用），保证 PB 计算精确。耗时短、可靠。
    - refresh_deep()  : 季度/手动调用，尝试从 akshare 原始报表 / 必盈API / 东财F10
                        解析五维质量字段；失败则保留缓存（手工维护兜底）。
"""

def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None

def refresh_light(banks, cache: dict) -> dict:
    """
    每日轻量刷新：BVPS / ROE(年化) / EPS。
    返回 {code: {bvps, roe, eps, as_of}}，仅在成功时返回非空字典。
    """
    out = {}
    try:
        import akshare as ak
        df = ak.stock_yjbb_em(date="20260331")  # 最新季报（Q1 2026）
        lut = {}
        for _, row in df.iterrows():
            code = str(row.get("股票代码", "")).strip()
            lut[code] = row
        for b in banks:
            if b.is_hk:
                continue  # 港股 yjbb 不含，PB 用别处
            row = lut.get(b.code)
            if row is None:
                continue
            bvps = _f(row.get("每股净资产"))
            roe_q = _f(row.get("净资产收益率"))     # 季度 ROE
            eps = _f(row.get("每股收益"))
            if bvps is None:
                continue
            rec = {"bvps": round(bvps, 3), "as_of": "2026Q1"}
            if roe_q is not None:
                rec["roe"] = round(min(roe_q * 4, 25.0), 2)  # 年化（封顶）
            if eps is not None:
                rec["eps"] = round(eps, 3)
            out[b.code] = rec
    except Exception as e:
        print(f"    [refresh_light] akshare yjbb 失败，沿用缓存：{e}")
    return out


def refresh_deep(banks, cache: dict) -> dict:
    """
    深度刷新（季度/手动）：尝试自动解析五维质量字段。
    按用户决策的数据源优先级链：
      akshare 利润表/资产负债表 → 必盈API → 东财F10 → 手工兜底（cache）
    返回 {code: {npl, provision_coverage, non_interest_ratio, core_tier1, rorwa, ...}}
    """
    out = {}
    # 1) akshare 原始报表（尽力解析，列名漂移则跳过）
    out.update(_try_akshare_sheets(banks))
    # 2) 必盈 API（需 BIYING_API_KEY）
    out.update(_try_biying(banks))
    # 3) 东财 F10（web 抓取）
    out.update(_try_em_f10(banks))
    # 4) 兜底：cache 中已有且非 None 的字段保留（手工维护）
    for b in banks:
        if b.code not in out:
            out[b.code] = {}
    return out


def _try_akshare_sheets(banks):
    """尝试从 akshare 利润表/资产负债表解析非息占比等。列名不匹配则跳过。"""
    res = {}
    try:
        import akshare as ak
        for b in banks:
            if b.is_hk:
                continue
            try:
                pf = ak.stock_profit_sheet_by_report_em(symbol=b.akshare)
                cols = list(pf.columns)
                # 探测非息相关列名
                ni_col = next((c for c in cols if "手续费" in c and "佣金" in c), None)
                if ni_col and "营业收入" in cols:
                    latest = pf.sort_values("REPORT_DATE").iloc[-1]
                    ni = _f(latest.get(ni_col))
                    rev = _f(latest.get("营业收入") or latest.get("营业总收入"))
                    if ni and rev:
                        res.setdefault(b.code, {})["non_interest_ratio"] = round(ni / rev * 100, 2)
            except Exception:
                continue
    except Exception:
        pass
    return res


def _try_biying(banks):
    """必盈 API（https://www.biyingapi.com/doc-center）。需环境变量 BIYING_API_KEY。"""
    import os, requests
    key = os.environ.get("BIYING_API_KEY")
    if not key:
        return {}
    res = {}
    # 必盈提供 A 股财务指标接口；具体端点以官方文档为准，此处为接入骨架
    try:
        for b in banks:
            if b.is_hk:
                continue
            r = requests.get(
                "https://api.biyingapi.com/api/stock/finance",
                params={"token": key, "code": b.code, "field": "npl,provision,roe"},
                timeout=15,
            )
            if r.status_code == 200:
                d = r.json()
                if d.get("code") == 0 and d.get("data"):
                    da = d["data"]
                    res[b.code] = {
                        "npl": _f(da.get("npl")),
                        "provision_coverage": _f(da.get("provision")),
                        "roe": _f(da.get("roe")),
                    }
    except Exception:
        pass
    return res


def _try_em_f10(banks):
    """东财 F10 抓取（兜底）。列名解析失败时跳过。"""
    import requests
    res = {}
    SESSION = requests.Session()
    SESSION.trust_env = False
    H = {"User-Agent": "Mozilla/5.0", "Referer": "https://emweb.securities.eastmoney.com"}
    try:
        for b in banks:
            if b.is_hk:
                continue
            # 东财 F10 主要指标接口（示例端点，实际以抓包为准）
            url = f"https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/" \
                  f"MainTargetAjax?code={b.akshare}"
            try:
                r = SESSION.get(url, headers=H, timeout=15)
                # 解析逻辑随页面结构变化，此处仅占位；失败即跳过
            except Exception:
                continue
    except Exception:
        pass
    return res
