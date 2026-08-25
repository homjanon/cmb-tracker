"""小散持仓回撤计算：读持仓 → 拉实时价 → 维护近12个月最高价 → 算盈利回落提醒。



- 价格：复用 query_stock（A/港/美股/ETF 腾讯；场外基金 天天基金/东财）。

- 基准最高价 ytd_high（前复权口径，**滚动12个月窗口，跨年不重置**）：

  首跑/新增标的用近12个月历史最高播种；每日破新高则上移；

  锚点滑出窗口（距今>365天）自动重播——2026-08-06 用户拍板。

- 派生指标（仅这些提交展示，成本/市值不进仓库）：

    最高盈利%   = (ytd_high - cost) / cost * 100

    当前盈利%   = (current - cost) / cost * 100

    盈利回落(pp)= 最高盈利% - 当前盈利%

    提醒         = 按「回落幅度」四档：≥10减仓 / ≥15接回 / ≥20加大 / ≥25加倍

                   （转亏禁减仓：当前盈利≤0 只提示买入类；滞回带防边界闪烁）

- 成本：GitHub Secret HOLDINGS_JSON 提供，**用户手动维护下修后成本**（分红除息日更新）。

"""

import json

import os

import sys

import datetime



sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from query_stock import price_of, stock_ytd_high, fund_ytd_high, us_ytd_high, hk_ytd_high



# 回落幅度档位触发阈值（百分点，0=持有 1=减仓 2=接回 3=加大 4=加倍）

LEVEL_TRIGGERS = (10, 15, 20, 25)

HYSTERESIS = 2  # 滞回带：降档需回落低于「当前档触发阈值−2」，防边界震荡反复提醒

LEVEL_TEXT = {

    1: '已回落≥10点，可考虑减仓锁利',

    2: '已回落≥15点，可考虑分批接回',

    3: '已回落≥20点，可考虑加大买入',

    4: '已回落≥25点，可考虑加倍',

}

# 转亏特化文案：当前盈利≤0 时禁用「减仓」，按名义档位显示真实回落幅度

# （修复 020602：回落仅10点却显示「≥15点接回」——转亏抬档后文案虚报幅度）

LOSS_TEXT = {

    1: '已回落≥10点，当前亏损中，暂不减仓锁利',

    2: '已回落≥15点，当前亏损中，可考虑分批接回',

    3: '已回落≥20点，当前亏损中，可考虑加大买入',

    4: '已回落≥25点，当前亏损中，可考虑加倍',

}





def _nominal_level(profit_dd):

    """按回落幅度(pp)算名义档位 0-4。"""

    for i, t in enumerate(LEVEL_TRIGGERS, 1):

        if profit_dd < t:

            return i - 1

    return 4





def _display_level(nominal, cur_profit):

    """转亏禁减仓：本应提示「减仓」(档1) 时若当前盈利≤0，改为「分批接回」(档2)。

    注意：名义档 0（回落未达任何档，本不提醒）**不得**因转亏被抬升——

    否则薄盈利标的转亏时会凭空出现「≥15点接回」提醒（020602 bug，2026-08-10 修复）。"""

    if cur_profit is not None and cur_profit <= 0 and nominal == 1:

        return 2

    return nominal



TYPE_MAP = {'a-stock': 'a_stock', 'hk-stock': 'hk', 'us-stock': 'us', 'fund': 'fund'}





def holdings_from_user_data(path, keep_codes=None):

    """预览用：从 user-data.json 读取。keep_codes: set of (code, round(cost,2)) 仅保留指定批次。"""

    d = json.load(open(path, encoding='utf-8'))

    out = []

    for a in d.get('assets', []):

        code = str(a.get('code', ''))

        t = TYPE_MAP.get(a.get('type'))

        if not code or not t:

            continue

        cost = float(a.get('cost') or 0)

        if keep_codes is not None and (code, round(cost, 2)) not in keep_codes:

            continue

        out.append({'code': code, 'name': a.get('name', ''), 'type': t, 'cost': cost})

    return out





def holdings_from_secret(json_str):

    """生产用：Secret 已是用户精选的持仓列表 [{code,name,type,cost}]。"""

    arr = json.loads(json_str)

    out = []

    for a in arr:

        code = str(a.get('code', ''))

        t = a.get('type') or TYPE_MAP.get(a.get('asset_type'))

        if not code or not t:

            continue

        out.append({'code': code, 'name': a.get('name', code),

                    'type': t, 'cost': float(a.get('cost') or 0)})

    return out





def holdings_from_preset(path):

    """生产回退用：仓库内预置清单（无成本，仅 code/name/type）。

    未设 HOLDINGS_JSON 时驱动回撤表（盈利列显示 —）。"""

    if not os.path.exists(path):

        return []

    arr = json.load(open(path, encoding='utf-8'))

    out = []

    for a in arr:

        code = str(a.get('code', ''))

        t = a.get('type') or TYPE_MAP.get(a.get('asset_type'))

        if not code or not t:

            continue

        out.append({'code': code, 'name': a.get('name', code), 'type': t, 'cost': 0.0})

    return out





def seed_ytd_high(code, qtype, year, today_str):

    if qtype == 'fund':

        return fund_ytd_high(code, year, today_str)

    if qtype == 'us':

        return us_ytd_high(code, year, today_str)

    if qtype == 'hk':

        return hk_ytd_high(code, year, today_str)

    return stock_ytd_high(code, qtype, year, today_str)





def seed_state(holdings, year, today_str):

    """一次性播种近12个月最高价（本地预填 / 新增标的补种）。返回 state dict。



    窗口：近12个月（A股 腾讯 qfq；港股/美股 yfinance 剔除分红；基金 东财 pingzhongdata）。

    口径：均统一为前复权/纯剔除分红。播种后跨年不重置、滑出窗口自动重播。

    GitHub Action 无通达信，故播种统一走网络源。

    """

    state = {'year': year, 'items': {}}

    for h in holdings:

        yh = seed_ytd_high(h['code'], h['type'], year, today_str)

        if yh:

            state['items'][h['code']] = {'ytd_high': yh, 'ytd_high_date': today_str}

            print(f"[seed] {h['code']} {h['name']} 近12个月最高 {yh}")

        else:

            print(f"[seed] {h['code']} {h['name']} 取近12个月最高失败，留空（运行时以现价当高点）")

    return state





def compute(holdings, state, today=None):

    today = today or datetime.date.today()

    year = today.year

    today_str = today.strftime('%Y-%m-%d')

    items = state.setdefault('items', {})

    state['year'] = year  # 仅记录年份，**不再跨年清空**（持仓以来最高，跨年不重置）

    derived = []

    for h in holdings:

        code = h['code']

        cur = price_of(code, h['type'])

        it = items.get(code)

        if cur is None:

            # 取不到价：保留上次 high，标记暂无（不误报）

            derived.append({'code': code, 'name': h['name'],

                            'ytd_high_profit_pct': None,

                            'current_profit_pct': None,

                            'profit_drawdown_pct': None, 'reminder': ''})

            continue

        if not it or not it.get('ytd_high'):

            yh = seed_ytd_high(code, h['type'], year, today_str)

            it = {'ytd_high': yh if yh else cur,

                  'ytd_high_date': today_str if yh else ''}

        elif (it.get('ytd_high_date')

              and (today - datetime.date.fromisoformat(it['ytd_high_date'])) > datetime.timedelta(days=365)):

            # 滚动12个月窗口：锚点滑出窗口 → 重播近12个月最高（跨年不重置的滚动语义）

            yh = seed_ytd_high(code, h['type'], year, today_str)

            if yh:

                it = {'ytd_high': yh, 'ytd_high_date': today_str}

        elif cur > it['ytd_high']:

            it['ytd_high'] = cur

            it['ytd_high_date'] = today_str

        items[code] = it

        yh = it['ytd_high']

        cost = h['cost']

        cur_profit = (cur - cost) / cost * 100 if cost else None

        ytd_profit = (yh - cost) / cost * 100 if cost else None

        profit_dd = (ytd_profit - cur_profit) if (ytd_profit is not None

                                                  and cur_profit is not None) else None

        # 档位：回落幅度 + 滞回带（state 存显示档位，防边界闪烁）

        stored = int(it.get('level', 0))

        reminder = ''

        if profit_dd is not None:

            nominal = _nominal_level(profit_dd)

            disp = _display_level(nominal, cur_profit)

            if disp > stored:

                stored = disp

            elif disp < stored and profit_dd < (LEVEL_TRIGGERS[stored - 1] - HYSTERESIS):

                stored = disp

            it['level'] = stored

            # 文案：转亏时用特化文案（按名义档显示真实幅度，不虚报档位）；

            # 盈利时用 LEVEL_TEXT（按显示档，含滞回带的粘滞语义）

            if cur_profit is not None and cur_profit <= 0:

                reminder = LOSS_TEXT.get(nominal, '')

            else:

                reminder = LEVEL_TEXT.get(nominal, '')

        derived.append({

            'code': code, 'name': h['name'],

            'ytd_high_profit_pct': round(ytd_profit, 2) if ytd_profit is not None else None,

            'current_profit_pct': round(cur_profit, 2) if cur_profit is not None else None,

            'profit_drawdown_pct': round(profit_dd, 2) if profit_dd is not None else None,

            'reminder': reminder,

        })

    state['updated_at'] = today_str

    return derived





def load_state(path):

    try:

        with open(path, encoding='utf-8') as f:

            return json.load(f)

    except Exception:

        return {'year': 0, 'items': {}}





def save_state(state, path):

    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)

    with open(path, 'w', encoding='utf-8') as f:

        json.dump(state, f, ensure_ascii=False, indent=2)





def main():

    """生产入口：读 HOLDINGS_JSON（Secret） → 拉价 → 更新 state → 写派生文件。

    --seed-only：仅用 --preset 或 HOLDINGS_JSON 播种近12个月最高价到 state（本地预填/补种）。

    """

    import argparse

    ap = argparse.ArgumentParser()

    ap.add_argument('--state', default='data/holdings_drawdown_state.json')

    ap.add_argument('--out', default='data/holdings_drawdown.json')

    ap.add_argument('--preset', default='',

                    help='预填用：含 code/type/name 的持仓清单(JSON)，无需成本')

    ap.add_argument('--seed-only', action='store_true',

                    help='仅播种年内最高价到 state，不产出派生表')

    args = ap.parse_args()

    today = datetime.date.today()

    year, today_str = today.year, today.strftime('%Y-%m-%d')

    secret = os.environ.get('HOLDINGS_JSON')



    preset_holdings = None

    if args.preset:

        arr = json.load(open(args.preset, encoding='utf-8'))

        preset_holdings = [{'code': str(a['code']),

                            'name': a.get('name', a['code']),

                            'type': a.get('type') or TYPE_MAP.get(a.get('asset_type')),

                            'cost': float(a.get('cost') or 0)}

                           for a in arr

                           if (a.get('type') or TYPE_MAP.get(a.get('asset_type')))]



    if args.seed_only:

        src = preset_holdings or (holdings_from_secret(secret) if secret else None)

        if not src:

            print('[holdings] seed-only 需要 --preset 或 HOLDINGS_JSON')

            return

        state = seed_state(src, year, today_str)

        save_state(state, args.state)

        print(f'[holdings] 已播种 {len(state["items"])} 条近12个月最高价 → {args.state}')

        return



    if not secret:

        # 回退到仓库内预置清单：回撤表立即可见，盈利列待填成本后显示

        preset_path = 'data/holdings_preset.json'

        holdings = holdings_from_preset(preset_path)

        if not holdings:

            print('[holdings] 未设置 HOLDINGS_JSON 且无预置清单，跳过')

            return

        print(f'[holdings] 未设置 HOLDINGS_JSON，使用预置清单（{len(holdings)} 条，盈利列待填成本）')

    else:

        holdings = holdings_from_secret(secret)

    state = load_state(args.state)

    derived = compute(holdings, state)

    save_state(state, args.state)

    with open(args.out, 'w', encoding='utf-8') as f:

        json.dump({'updated_at': state.get('updated_at'), 'items': derived},

                  f, ensure_ascii=False, indent=2)

    print(f'[holdings] 已计算 {len(derived)} 条 → {args.out}')





if __name__ == '__main__':

    main()

