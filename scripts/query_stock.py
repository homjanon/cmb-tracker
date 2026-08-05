"""行情查询：A/港/美股/ETF + 公募基金（适配自 homjanon/douban-tracker/query_stock.py）。

数据源（极简直查）：
  A/港/美股/ETF : 腾讯 qt.gtimg.cn（唯一源；查询失败即返回 None）
  基金(场外/净值型/QDII) : 天天基金 JSONP 直连 fundgz.1234567.com.cn（主）
                         → 东方财富 lsjz 历史净值 api.fund.eastmoney.com（备，含 QDII）

本文件对外只暴露两个函数：
  - price_of(code, qtype) -> float | None   （qtype: a_stock / hk / us / fund）
  - 供 holdings_drawdown.seed_ytd_high 复用内部 _fetch_* 拉取年内最高价
持仓表按 user-data.json 的 type 直接路由，不靠代码前缀猜，避开 00 开头基金误判。
"""
import re
import requests

SESSION = requests.Session()
SESSION.trust_env = False
SESSION.verify = False
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
TENCENT_H = {"User-Agent": "Mozilla/5.0", "Referer": "https://gu.qq.com/"}

KNOWN_FUNDS = {
    '001532', '166001', '016372', '005698', '002891', '000906',
    '006555', '100055', '008253', '008254', '539002', '160213',
    '450010', '012920', '007540', '018984', '006227', '006328',
    '005656', '006452',
}
ETF_PREFIXES = ('15', '50', '51', '52', '55', '56', '58')
FUND_PREFIXES = ('01', '02', '11', '16', '18', '27')


def _classify(code_str):
    if re.search(r'[A-Z]', code_str) and not code_str.startswith(('SH', 'SZ', 'HK')):
        return 'us', code_str
    if code_str.startswith(('SH', 'SZ')):
        return 'a_stock', code_str[2:]
    if code_str.startswith('HK'):
        return 'hk', code_str[2:]
    if code_str.isdigit():
        if len(code_str) == 6:
            if code_str.startswith(ETF_PREFIXES):
                return 'a_stock', code_str
            if code_str in KNOWN_FUNDS:
                return 'fund', code_str
            if code_str.startswith('00') and code_str[2:3] in ('0', '1', '2'):
                return 'a_stock', code_str
            if code_str.startswith(FUND_PREFIXES):
                return 'fund', code_str
            return 'a_stock', code_str
        if len(code_str) <= 5:
            return 'hk', code_str
        return 'a_stock', code_str
    return 'a_stock', code_str


def _tencent_prefix(code):
    if code.startswith(('60', '68', '90', '50', '51', '52', '55', '56', '58')):
        return 'sh'
    return 'sz'


def _parse_tencent(text):
    out = {}
    for line in text.strip().split("\n"):
        if "=" not in line:
            continue
        k = line.split("=")[0].replace("v_", "").strip()
        v = line.split("=", 1)[1].strip().strip('"')
        parts = v.split("~")
        if len(parts) > 3:
            out[k] = parts
    return out


def _fetch_tencent(codes):
    if not codes:
        return {}
    try:
        r = SESSION.get(f"https://qt.gtimg.cn/q={','.join(codes)}",
                        headers=TENCENT_H, timeout=25)
        r.encoding = "gbk"
        q = _parse_tencent(r.text)
        res = {}
        for raw, parts in q.items():
            res[raw] = {
                "name": parts[1] if len(parts) > 1 else raw,
                "price": parts[3] if len(parts) > 3 else "",
                "change": parts[32] if len(parts) > 32 else "",
                "source": "tencent",
            }
        return res
    except Exception as e:
        print(f"[query] 腾讯行情失败: {e}")
        return {}


def _fetch_fund_tiantian(code_str):
    try:
        url = f"https://fundgz.1234567.com.cn/js/{code_str}.js"
        r = SESSION.get(url, headers={"Referer": "https://fund.eastmoney.com/"}, timeout=10)
        if r.status_code == 200:
            m = re.search(r'\{[^{}]+\}', r.text)
            if m:
                import json
                raw = m.group(0)
                try:
                    d = json.loads(raw)
                except Exception:
                    try:
                        d = json.loads(raw.replace("'", '"'))
                    except Exception:
                        d = {}
                if d:
                    return {
                        "name": d.get("name", ""),
                        "price": d.get("gsz", d.get("dwjz", "")),
                        "change": d.get("gszzl", ""),
                        "date": d.get("jzrq", ""),
                        "source": "tiantian",
                    }
    except Exception as e:
        print(f"[query] 天天基金失败: {e}")
    return None


def _fetch_fund_eastmoney(code_str):
    try:
        url = "https://api.fund.eastmoney.com/f10/lsjz"
        params = {"fundCode": code_str, "pageIndex": 1, "pageSize": 3}
        r = SESSION.get(url, params=params,
                        headers={"Referer": "https://fund.eastmoney.com/"}, timeout=10)
        if r.status_code == 200:
            data = r.json()
            records = data.get("Data", {}).get("LSJZList", [])
            if records:
                latest = records[0]
                return {
                    "name": code_str,
                    "price": latest.get("DWJZ", ""),
                    "change": latest.get("JZZZL", ""),
                    "date": latest.get("FSRQ", ""),
                    "source": "eastmoney",
                }
    except Exception as e:
        print(f"[query] 东方财富基金失败: {e}")
    return None


def price_of(code, qtype):
    """统一取现价/NAV（float），失败返回 None。qtype: a_stock/hk/us/fund。"""
    code_str = str(code).strip()
    if qtype == 'fund':
        r = _fetch_fund_tiantian(code_str) or _fetch_fund_eastmoney(code_str)
        if r and r.get('price') not in (None, ''):
            try:
                return float(r['price'])
            except Exception:
                return None
        return None
    if qtype == 'hk':
        prefix = 'hk'
    elif qtype == 'us':
        prefix = 'us'
    else:
        prefix = _tencent_prefix(code_str)
    raw = f"{prefix}{code_str}"
    t = _fetch_tencent([raw])
    if t and raw in t and t[raw].get('price') not in (None, ''):
        try:
            return float(t[raw]['price'])
        except Exception:
            return None
    return None


def stock_ytd_high(code_str, qtype, year, today_str):
    """A股/港股 腾讯日K(前复权/qfq)取年内最高价。返回 float 或 None。

    要点：
      - 用 ,qfq（前复权）后缀：前复权锚定最新日现价，历史最高价按累计分红下修，
        与 qt.gtimg.cn 的实时现价（同锚定最新日）口径一致，回撤计算才正确。
        （若用不复权/bfq，已拿到的分红会被算回历史高价，导致回撤被高估、双重计入分红）
      - day 节点数组格式: [日期, 开, 收, 高, 低, 量, ...] → 高点取 index 3。
      - 美股(us)腾讯 K线不支持，由 us_ytd_high 走 yfinance；本函数仅服务 A股/港股。
    """
    if qtype == 'hk':
        raw = f"hk{code_str}"
    else:
        raw = f"{_tencent_prefix(code_str)}{code_str}"
    url = (f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
           f"?param={raw},day,{year}-01-01,{today_str},320,qfq")
    try:
        r = SESSION.get(url, headers=TENCENT_H, timeout=25)
        d = r.json()
        node = None
        for k in ('day', 'qfqday'):
            node = d.get('data', {}).get(raw, {}).get(k)
            if node:
                break
        if not node:
            return None
        hi = max(float(x[3]) for x in node if x and len(x) > 3)
        return hi
    except Exception as e:
        print(f"[query] 腾讯K线失败 {raw}: {e}")
        return None


def _yf_history_with_retry(ticker, year, max_retries=5):
    """yfinance 拉 YTD 不复权日K + 分红，带限流(429)指数退避重试。

    返回 pandas.DataFrame（index=日期，含 High/Dividends 列）；失败抛异常由调用方捕获。
    """
    import time
    import yfinance as yf
    last = None
    for attempt in range(max_retries):
        try:
            tk = yf.Ticker(ticker)
            hist = tk.history(start=f"{year}-01-01", auto_adjust=False, actions=True)
            return hist
        except Exception as e:
            last = e
            msg = str(e)
            if 'Rate' in msg or 'Too Many' in msg or '429' in msg:
                wait = 3 * (2 ** attempt)
                print(f"[query] yfinance 限流 {ticker}，第{attempt+1}次重试，{wait}s: {msg[:80]}")
                time.sleep(wait)
                continue
            raise
    raise last


def yf_ytd_high(ticker, year, today_str):
    """yfinance 取美股/港股 年内最高（纯前复权=剔除分红，与A股口径统一）。

    纯前复权口径：adjusted_high = raw_high - sum(分红 where ex_date > high_date)
      - 前复权锚定最新日现价，历史价按「高点之后累计分红」下修；
      - 与腾讯 qfq 的 A股口径完全一致，确保回撤不被双重计入分红。
    ticker 形如 'QQQM' / '03968.HK'。取数失败返回 None。
    """
    try:
        import pandas as pd
        hist = _yf_history_with_retry(ticker, year)
        if hist is None or hist.empty:
            return None
        highs = hist['High'].dropna()
        if highs.empty:
            return None
        raw_high = float(highs.max())
        high_date = highs.idxmax()
        div_col = hist['Dividends'].dropna()
        adj = float(div_col[div_col.index > high_date].sum())
        return raw_high - adj
    except Exception as e:
        print(f"[query] yfinance失败 {ticker}: {e}")
        return None


def us_ytd_high(code_str, year, today_str):
    """美股/ETF 年内最高：优先 yfinance(纯前复权)；失败回退 Nasdaq(不复权)。"""
    h = yf_ytd_high(code_str, year, today_str)
    if h is not None:
        return h
    return _nasdaq_ytd_high(code_str, year, today_str)


def hk_ytd_high(code_str, year, today_str):
    """港股 年内最高：优先 yfinance(纯前复权)；失败回退 腾讯 qfq K线。"""
    h = yf_ytd_high(f"{code_str}.HK", year, today_str)
    if h is not None:
        return h
    return stock_ytd_high(code_str, 'hk', year, today_str)


def _nasdaq_ytd_high(code_str, year, today_str):
    """Nasdaq 历史日K 取年内最高(美股/美股ETF)，作 yfinance 兜底。返回 float 或 None。

    Nasdaq historical API 分页(每页~15条)，assetclass 需区分 etf/stocks；
    先试 etf 再试 stocks，合并取年内最高 high。
    """
    try:
        H = {'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}
        best = None
        for asset in ('etf', 'stocks'):
            hi = []
            off = 0
            while off < 400:
                url = (f"https://api.nasdaq.com/api/quote/{code_str}/historical"
                       f"?assetclass={asset}&fromdate={year}-01-01&todate={today_str}&offset={off}")
                r = SESSION.get(url, headers=H, timeout=25)
                tbl = r.json().get('data', {}).get('tradesTable', {})
                rows = tbl.get('rows', [])
                if not rows:
                    break
                for x in rows:
                    h = x.get('high')
                    if h not in (None, ''):
                        try:
                            hi.append(float(h))
                        except Exception:
                            pass
                off += len(rows)
            if hi:
                best = max(hi)
                break
        return best
    except Exception as e:
        print(f"[query] Nasdaq失败 {code_str}: {e}")
        return None


def fund_ytd_high(code_str, year, today_str):
    """东财 lsjz 取年内最高 NAV。返回 float 或 None。"""
    try:
        url = "https://api.fund.eastmoney.com/f10/lsjz"
        params = {"fundCode": code_str, "pageIndex": 1, "pageSize": 90}
        r = SESSION.get(url, params=params,
                        headers={"Referer": "https://fund.eastmoney.com/"}, timeout=10)
        if r.status_code == 200:
            recs = r.json().get("Data", {}).get("LSJZList", [])
            vals = [float(x["DWJZ"]) for x in recs
                    if x.get("FSRQ", "") >= f"{year}-01-01" and x.get("DWJZ")]
            return max(vals) if vals else None
    except Exception as e:
        print(f"[query] 东财净值失败 {code_str}: {e}")
    return None


if __name__ == "__main__":
    import json
    for c, t in [("600036", "a_stock"), ("3968", "hk"), ("QQQM", "us"),
                 ("020741", "fund"), ("016452", "fund")]:
        print(c, t, "→", price_of(c, t))
