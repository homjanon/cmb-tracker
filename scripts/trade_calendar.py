#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""交易日判据（全项目唯一来源）。

为什么单独一个模块
------------------
workflow 的 `check` 步骤此前内联复制了一份 akshare 调用，而写入侧（`run_daily._append_history`）
走本模块；两边在**周中法定假期**上曾不等价，会出现"门控判为非交易日、写入侧却照样落盘"的半闭环。
现在 workflow 的 `check` 步骤只调 `python scripts/trade_calendar.py --gate`，判据真正只有一处
（改一处漏一处的隐患随之消除）。

取数层级（2026-11-18 加固，三级）
--------------------------------
L1  akshare 日历：`calendar_trade_date_hist_sina`（新名，1.20.45 起）
    → `tool_trade_date_hist_sina`（旧名兜底）
    ⚠️ `requirements.txt` 写的是 `akshare>=1.14.0`（无上界），CI 每次都装最新版，
       akshare 一旦改名，旧名访问直接抛 AttributeError（2026-11-16~18 连续三天失败的原因）。
       故一律「新名优先 + 旧名兜底」，两个名字都缺时抛出可诊断的异常，绝不靠单一硬编码。
L2  腾讯行情时间戳兜底：读 600036 的 parts[30]（形如 20261118161458），日期 == 今天 → 交易日。
    属**不同数据源、不同风控面**，且是「今天确实有成交」的直接证据。
    ⚠️ 只在盘后可靠（本项目 16:30 触发）；开盘前/盘中跑会拿到上一交易日时间戳。
L3  两级都失败：
    - `is_trade_day()`（供 run_daily 写入闸门）→ 降级「周一~周五」并打 warn；
    - `--gate`（供 workflow 门控）→ **显式失败退出**，绝不静默放行。

顺带堵一个静默坑：日历数据本身过期（最晚日期 < 今天）时，旧逻辑会把「每一天」都判成
非交易日 → 静默天天跳过、Actions 全绿。现在这种情况下 `--gate` 直接报错。
"""
import datetime
import os
import sys
import time

CST = datetime.timezone(datetime.timedelta(hours=8))

_CAL = {"loaded": False, "days": set(), "max": ""}
_PROBE = {"done": False, "date": ""}

# 腾讯行情探针（招商银行，本仓核心标的）
_PROBE_SYMBOL = "sh600036"
_PROBE_URL = "https://qt.gtimg.cn/q=" + _PROBE_SYMBOL
_PROBE_DATE_IDX = 30  # parts[30] = YYYYMMDDHHMMSS


def _today():
    return datetime.datetime.now(CST).strftime("%Y-%m-%d")


def _trade_date_df(ak):
    """新名优先、旧名兜底。akshare 1.20.45 起 tool_trade_date_hist_sina → calendar_trade_date_hist_sina。"""
    fn = (getattr(ak, "calendar_trade_date_hist_sina", None)
          or getattr(ak, "tool_trade_date_hist_sina", None))
    if fn is None:
        raise RuntimeError(
            "akshare 交易日历接口不存在：新名 calendar_trade_date_hist_sina 与旧名 "
            "tool_trade_date_hist_sina 均缺失（akshare 又改名了，对照 "
            "https://akshare.akfamily.xyz/changelog.html#changelog-rename）"
        )
    return fn()


def _load_calendar():
    """L1：akshare 日历，3 次短退避重试（sina 源偶发抖动）。"""
    if _CAL["loaded"]:
        return
    _CAL["loaded"] = True
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    last = None
    for attempt in range(3):
        try:
            import akshare as ak
            df = _trade_date_df(ak)
            days = {str(x)[:10] for x in df["trade_date"].tolist()}
            if days:
                _CAL["days"] = days
                _CAL["max"] = max(days)
                return
            last = RuntimeError("akshare 交易日历返回空表")
        except Exception as e:  # noqa: BLE001
            last = e
        if attempt < 2:
            time.sleep(1 + 2 * attempt)
    print(f"[warn] 交易日历加载失败（akshare）：{last}")


def _tencent_market_date():
    """L2：腾讯行情时间戳。返回 'YYYY-MM-DD' 或 ''（失败/无该字段）。"""
    if _PROBE["done"]:
        return _PROBE["date"]
    _PROBE["done"] = True
    try:
        import requests
        s = requests.Session()
        s.trust_env = False  # 绕开本机/沙箱代理，腾讯行情直连即可
        r = s.get(_PROBE_URL,
                  headers={"User-Agent": "Mozilla/5.0", "Referer": "https://gu.qq.com/"},
                  timeout=15)
        r.encoding = "gbk"
        parts = r.text.split('="', 1)[1].rstrip('";\r\n').split("~")
        raw = parts[_PROBE_DATE_IDX] if len(parts) > _PROBE_DATE_IDX else ""
        if len(raw) >= 8 and raw[:8].isdigit():
            _PROBE["date"] = raw[0:4] + "-" + raw[4:6] + "-" + raw[6:8]
    except Exception as e:  # noqa: BLE001
        print(f"[warn] 腾讯行情时间戳兜底失败：{e}")
    return _PROBE["date"]


def calendar_ok():
    """日历是否可用（供外部判断当前判据可信度）。"""
    _load_calendar()
    return bool(_CAL["days"])


def is_trade_day(d=None):
    """d: 'YYYY-MM-DD' / date / datetime / None(=北京今天)。返回是否 A 股交易日。"""
    _load_calendar()
    if d is None:
        d = _today()
    s = str(d)[:10]
    if _CAL["days"]:
        return s in _CAL["days"]

    # 日历全挂 → 只有「今天」能用腾讯时间戳兜底（历史/未来日期无意义）
    if s == _today():
        md = _tencent_market_date()
        if md:
            print(f"[warn] 交易日历不可用，改用腾讯行情时间戳判定：行情日={md}，今天={s}")
            return md == s

    print("[warn] 交易日历不可用，降级为「周一~周五」判定（注意：周中法定假期会被误判为交易日）")
    try:
        y, m, dd = map(int, s.split("-"))
        return datetime.date(y, m, dd).weekday() < 5
    except Exception:  # noqa: BLE001
        return False


def _emit(key, val):
    line = f"{key}={val}\n"
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write(line)
    else:
        print(f"[github_output] {line.strip()}")


def _gate():
    """workflow 门控模式：只输出 trade=1/0；判据不可用则显式失败（不静默放行）。"""
    _load_calendar()
    today = _today()

    if _CAL["days"]:
        # 防「日历本身过期」→ 天天被静默跳过、Actions 还全绿
        if _CAL["max"] and _CAL["max"] < today:
            print(f"::error::交易日历数据陈旧（最晚 {_CAL['max']} < 今天 {today}），"
                  "无法判定，已终止以免误判或静默跳过")
            return 1
        ok = today in _CAL["days"]
        src = f"akshare 交易日历（最晚 {_CAL['max']}）"
    else:
        md = _tencent_market_date()
        if not md:
            print("::error::交易日判据完全不可用（akshare 日历 + 腾讯行情时间戳均失败），"
                  "为避免非交易日污染历史，本次运行终止")
            return 1
        ok = md == today
        src = f"腾讯行情时间戳兜底（行情日={md}）"

    if not ok:
        print(f"{today} 非交易日（判据：{src}），跳过当日计算（勾选 force 可强制运行）")
        _emit("trade", "0")
        return 0
    print(f"{today} 交易日（判据：{src}），执行五维追踪")
    _emit("trade", "1")
    return 0


if __name__ == "__main__":
    if "--gate" in sys.argv[1:]:
        sys.exit(_gate())
    for x in ["2026-09-24", "2026-09-25", "2026-09-30", "2026-10-01", "2026-10-02", "2026-10-03", "2026-10-08"]:
        print(x, "交易日" if is_trade_day(x) else "非交易日")
