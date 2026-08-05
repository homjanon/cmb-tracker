"""本地预览构建：生成 preview_my.html（小散持仓回撤表 + 雪球大V 表，均内联数据，可离线打开）。

- 小散持仓：读取 data/holdings_preset.json（5 个预设标的，无成本）→ 用已预填的
  data/holdings_drawdown_state.json（年内最高价）＋实时价计算回撤。
  - 600036 用真实成本 36.56；其余 4 个成本留空（演示用，待你在 HOLDINGS_JSON 设真实成本），
    故「今年最高盈利」列显示 —，但「年内最高价/当前回撤」为真实值。
- 雪球表：本地 mentions.json 内联，演示「数量固定显示」（五粮液 109手）。
- 银行表用 2 行假数据保持页面结构。
"""
import json
import os
import sys
import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'cmb-tracker', 'scripts'))
import render_html
import holdings_drawdown as hd

PRESET = os.path.join(ROOT, 'cmb-tracker', 'data', 'holdings_preset.json')
STATE = os.path.join(ROOT, 'cmb-tracker', 'data', 'holdings_drawdown_state.json')
XQ_MENTIONS = os.path.join(ROOT, 'xueqiu-tracker', 'data', 'mentions.json')
OUT = os.path.join(ROOT, 'preview_my.html')

# 真实成本仅 600036 已知；其余留 0（compute 中 cost=0 → 今年最高盈利显示 —）
COST_MAP = {'600036': 36.56}


def main():
    preset = json.load(open(PRESET, encoding='utf-8'))
    holdings = [{'code': a['code'], 'name': a['name'], 'type': a['type'],
                 'cost': COST_MAP.get(a['code'], 0.0)} for a in preset]
    state = hd.load_state(STATE)
    derived = hd.compute(holdings, state, datetime.date.today())
    print('[preview] 小散持仓派生:', json.dumps(derived, ensure_ascii=False, indent=1))

    mentions = json.load(open(XQ_MENTIONS, encoding='utf-8'))

    rows = [
        {"name": "招商银行", "code": "600036", "short": "招行", "color": "#c23531",
         "price": 40.36, "pe": 7.0, "pb": 0.9, "div_yield": 4.5,
         "price_source": "t", "quote_time": "2026-08-06", "pe_source": "t", "pb_source": "t",
         "score": {"dims": {k: {"score": 15.0} for k in render_html.DIM_KEYS}, "total": 75.0},
         "signal": {"zone_low": 30.0, "zone_high": 40.0, "signal": "HOLD"}},
        {"name": "宁波银行", "code": "002142", "short": "宁波", "color": "#749f83",
         "price": 25.0, "pe": 6.0, "pb": 0.8, "div_yield": 3.0,
         "price_source": "t", "quote_time": "2026-08-06", "pe_source": "t", "pb_source": "t",
         "score": {"dims": {k: {"score": 14.0} for k in render_html.DIM_KEYS}, "total": 70.0},
         "signal": {"zone_low": 20.0, "zone_high": 28.0, "signal": "HOLD"}},
    ]

    render_html.render(rows, {}, datetime.datetime.now(), OUT,
                       my_holdings=derived, xqm_inline=mentions)
    print('[preview] 已写出:', OUT)


if __name__ == '__main__':
    main()
