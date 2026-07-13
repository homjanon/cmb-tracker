#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
行情抓取：价格 / PE / PB / 股息率

数据源（多源容错链，复用每日财经早报项目的 proven 模式）：
  价格    : 腾讯 qt.gtimg.cn（主）→ 新浪 hq.sinajs.cn（备）→ akshare stock_zh_a_spot_em（兜底，东财接口沙箱偶发不稳）
  PE / PB : 腾讯 qt.gtimg.cn 实时（parts[39]=市盈率TTM / parts[46]=市净率）→ baostock peTTM/pbMRQ（兜底）→ 现价÷BVPS（再兜底）
  股息率  : 每股分红(div_ps，来自 fundamentals.json) ÷ 现价（年度更新，无需实时接口）
  PB 兜底 : 现价 ÷ 每股净资产(BVPS，来自 yjbb 刷新)

注：腾讯 qt.gtimg.cn 的 parts[39]=市盈率(TTM)、parts[46]=市净率(PB) 均可靠可用（实测 6 家银行与真实值吻合）。
    旧注释"字段[31]非标准 PE"是把 parts[31](涨跌额)误当 PE；parts[40] 为空(市盈率静未填充)，PB 实际在 parts[46]。
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
    """腾讯行情主接口：一次拿 价格 / PE(TTM) / PB。返回 {code: {price, pe, pb}}。
    parts[3]=当前价, parts[39]=市盈率(TTM), parts[46]=市净率(PB)。
    注：parts[40] 为空（市盈率静未填充），勿误判 PB 缺失。"""
    codes = ",".join(b.tencent for b in banks)
    try:
        r = SESSION.get(f"https://qt.gtimg.cn/q={codes}", headers=TENCENT_H, timeout=25)
        r.encoding = "gbk"
        q = _parse_tencent(r.text)
        out = {}
        for b in banks:
            p = q.get(b.tencent)
            if not p or len(p) < 47:
                continue
            rec = {}
            try:
                if p[3]:
                    rec["price"] = float(p[3])
            except ValueError:
                pass
            try:
                if p[39]:
                    rec["pe"] = float(p[39])
            except ValueError:
                pass
            try:
                if p[46]:
                    rec["pb"] = float(p[46])
            except ValueError:
                pass
            if rec:
                out[b.code] = rec
        return out
    except Exception:
        return {}

def _fetch_sina_prices(banks):
    """新浪行情备接口。返回 {code: {price}}"""
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
                    out[code] = {"price": float(p[idx])}
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
                    out[b.code] = {"price": v}
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
    返回 {code: {price, pe, pb, div_yield, price_source, pe_source, pb_source, quote_time}}。
    bvps_map  : {code: 每股净资产} 用于 PB 兜底
    div_ps_map: {code: 每股分红}   用于股息率计算
    来源标注：区分实时（tencent / sina/akshare）与兜底（baostock / bvps），便于识别数据陈旧。
    """
    bvps_map = bvps_map or {}
    div_ps_map = div_ps_map or {}
    tencent = _fetch_tencent_prices(banks)          # 价/PE/PB 实时（一次请求）
    # 价容错链：腾讯 → 新浪 → akshare（均返回 {code:{price}} 结构，统一处理）
    price_chain = fallback_chain(
        lambda: tencent,
        lambda: _fetch_sina_prices(banks),
        lambda: _fetch_akshare_spot_prices(banks),
    )
    price_chain = price_chain or {}
    val = _fetch_baostock_val(banks)                # 价/PE/PB 兜底

    result = {}
    for b in banks:
        t = tencent.get(b.code) or {}
        pc = price_chain.get(b.code) or {}
        v = val.get(b.code) or {}
        # 价格：腾讯/新浪/akshare 优先；全部失败则用 baostock 收盘价兜底
        price = pc.get("price") or v.get("price")
        # PE：腾讯实时优先；baostock 兜底
        pe = t.get("pe") or v.get("pe")
        # PB：腾讯实时优先；baostock 兜底；再回退 现价÷BVPS
        if t.get("pb") is not None:
            pb, pb_src = t.get("pb"), "tencent"
        elif v.get("pb") is not None:
            pb, pb_src = v.get("pb"), "baostock"
        elif price and bvps_map.get(b.code):
            pb, pb_src = round(price / bvps_map[b.code], 3), "bvps"
        else:
            pb, pb_src = None, "none"
        # 股息率
        dy = None
        dps = div_ps_map.get(b.code)
        if dps and price:
            dy = round(dps / price * 100, 3)
        # 数据来源标注（区分实时 / 兜底，避免"以为没更新"误判）
        if t.get("price") is not None:
            price_src = "tencent"
        elif pc.get("price") is not None:
            price_src = "sina/akshare"
        elif v.get("price") is not None:
            price_src = "baostock"
        else:
            price_src = "none"
        pe_src = "tencent" if t.get("pe") is not None else (
            "baostock" if v.get("pe") is not None else "none")
        result[b.code] = {
            "price": round(price, 3) if price is not None else None,
            "pe": round(pe, 3) if pe is not None else None,
            "pb": round(pb, 3) if pb is not None else None,
            "div_yield": dy,
            "price_source": price_src,
            "pe_source": pe_src,
            "pb_source": pb_src,
        }
    # 行情抓取时间（北京时间，ISO8601 含时区）
    qt = datetime.now().astimezone().isoformat()
    for code in result:
        result[code]["quote_time"] = qt
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
