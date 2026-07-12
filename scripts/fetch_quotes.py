#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
行情抓取：价格 / PE / PB / 股息率

数据源（多源容错链，复用每日财经早报项目的 proven 模式）：
  价格    : 腾讯 qt.gtimg.cn（主）→ 新浪 hq.sinajs.cn（备）→ akshare stock_zh_a_spot_em（兜底，东财接口沙箱偶发不稳）
  PE / PB : baostock query_history_k_data_plus（peTTM / pbMRQ，可靠，与收盘价同日）
  股息率  : 每股分红(div_ps，来自 fundamentals.json) ÷ 现价（年度更新，无需实时接口）
  PB 兜底 : 现价 ÷ 每股净资产(BVPS，来自 yjbb 刷新)

注：腾讯 qt.gtimg.cn 的字段[31]并非标准 PE（实测为异常小值），故 PE 不取自腾讯，统一走 baostock。
"""
import re
import requests
from datetime import datetime, timedelta
from retry_utils import fallback_chain

SESSION = requests.Session()
SESSION.trust_env = False
SINA_H = {"User-Agent": "Mozilla/5.0", "Referer": "https://finance.sina.com.cn"}
TENCENT_H = {"User-Agent": "Mozilla/5.0", "Referer": "https://gu.qq.com/"}

def _parse_tencent(text):
    r = {}
    for line in text.strip().split("\n"):
        if "=" not in line:
            continue
        k = line.split("=")[0].replace("v_", "").strip()
        v = line.split("=", 1)[1].strip().strip('"')
        parts = v.split("~")
        if len(parts) < 6:
            continue
        r[k] = parts
    return r

def _fetch_tencent_prices(banks):
    """腾讯行情主接口：一次拿全部价格。返回 {code: price}"""
    codes = ",".join(b.tencent for b in banks)
    try:
        r = SESSION.get(f"https://qt.gtimg.cn/q={codes}", headers=TENCENT_H, timeout=25)
        r.encoding = "gbk"
        q = _parse_tencent(r.text)
        out = {}
        for b in banks:
            p = q.get(b.tencent)
            if p and len(p) > 3 and p[3]:
                try:
                    out[b.code] = float(p[3])
                except ValueError:
                    pass
        return out
    except Exception:
        return {}

def _fetch_sina_prices(banks):
    """新浪行情备接口。返回 {code: price}"""
    items = []
    for b in banks:
        items.append(f"rt_hk{b.code}" if b.is_hk else b.tencent)
    try:
        r = SESSION.get("https://hq.sinajs.cn/list=" + ",".join(items),
                        headers=SINA_H, timeout=25)
        r.encoding = "gbk"
        out = {}
        for line in r.text.strip().split("\n"):
            m = re.match(r'var hq_str_(?:rt_hk)?([^=]+)="([^"]*)"', line)
            if not m:
                continue
            code = m.group(1).replace("sh", "").replace("sz", "")
            p = m.group(2).split(",")
            idx = 6 if "rt_hk" in line else 3
            if len(p) > idx and p[idx]:
                try:
                    out[code] = float(p[idx])
                except ValueError:
                    pass
        return out
    except Exception:
        return {}

def _fetch_akshare_spot_prices(banks):
    """akshare 现货兜底价格（仅价格；东财接口沙箱偶发 RemoteDisconnected，作最后兜底）。"""
    out = {}
    try:
        import akshare as ak
        df = ak.stock_zh_a_spot_em()
        for b in banks:
            if b.is_hk:
                continue
            row = df[df["代码"] == b.code]
            if not row.empty:
                v = _f(row.iloc[0].get("最新价"))
                if v:
                    out[b.code] = v
    except Exception:
        pass
    return out

def _fetch_baostock_val(banks):
    """baostock close / peTTM / pbMRQ（可靠，作价格兜底）。返回 {code: {price, pe, pb}}"""
    out = {}
    try:
        import baostock as bs
        lg = bs.login()
        if lg.error_code != "0":
            bs.logout()
            return out
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=12)).strftime("%Y-%m-%d")
        for b in banks:
            if b.is_hk:
                continue
            rs = bs.query_history_k_data_plus(
                b.baostock, "date,close,peTTM,pbMRQ",
                start_date=start, end_date=end, frequency="d")
            rows = []
            while rs.error_code == "0" and rs.next():
                rows.append(rs.get_row_data())
            if rows:
                d = rows[-1]  # 最近交易日
                out[b.code] = {"price": _f(d[1]), "pe": _f(d[2]), "pb": _f(d[3])}
        bs.logout()
    except Exception:
        pass
    return out

def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None

def fetch_quotes(banks, bvps_map=None, div_ps_map=None):
    """
    返回 {code: {price, pe, pb, div_yield}}。
    bvps_map  : {code: 每股净资产} 用于 PB 兜底
    div_ps_map: {code: 每股分红}   用于股息率计算
    """
    bvps_map = bvps_map or {}
    div_ps_map = div_ps_map or {}
    prices = fallback_chain(
        _fetch_tencent_prices,
        _fetch_sina_prices,
        lambda: _fetch_akshare_spot_prices(banks),
    )
    prices = prices or {}
    val = _fetch_baostock_val(banks)

    result = {}
    for b in banks:
        # 价格：腾讯/新浪/akshare 优先；全部失败则用 baostock 收盘价兜底
        price = prices.get(b.code) or (val.get(b.code) or {}).get("price")
        pe = (val.get(b.code) or {}).get("pe")
        pb = (val.get(b.code) or {}).get("pb")
        # PB 兜底：现价 ÷ 缓存 BVPS
        if (pb is None or pb <= 0) and price and bvps_map.get(b.code):
            pb = round(price / bvps_map[b.code], 3)
        # 股息率
        dy = None
        dps = div_ps_map.get(b.code)
        if dps and price:
            dy = round(dps / price * 100, 3)
        result[b.code] = {
            "price": round(price, 3) if price else None,
            "pe": round(pe, 3) if pe else None,
            "pb": round(pb, 3) if pb else None,
            "div_yield": dy,
        }
    return result

if __name__ == "__main__":
    from bank_universe import all_banks
    import json
    print(json.dumps(
        fetch_quotes(all_banks(),
                     {"600036": 44.9, "601398": 11.06, "601939": 13.56,
                      "601288": 8.08, "601988": 8.48, "002142": 35.2},
                     {"600036": 2.0, "601398": 0.32, "601939": 0.42,
                      "601288": 0.25, "601988": 0.25, "002142": 0.65}),
        ensure_ascii=False, indent=2))
