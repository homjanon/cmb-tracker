# 招招五维模型 · 五大行每日追踪

基于 **招招五维模型** 的选股框架，每日盘后自动抓取招商银行、工商银行、建设银行、农业银行、中国银行、宁波银行的行情与财务数据，计算五维评分、买入信号与买入区间，并发布到 GitHub Pages。

> ⚠️ 本项目仅作个人投资研究记录，**不构成任何投资建议**。

- 线上看板：`https://cmb-tracker.hellohopo.dpdns.org`
- 机器可读报告：`https://raw.githubusercontent.com/homjanon/cmb-tracker/main/output/cmb_report.json`

---

## 标的范围

| 代码 | 银行 | 备注 | 估值风格 |
|------|------|------|----------|
| 600036 | 招商银行 | 零售之王，五维标杆 | 收益型 |
| 601398 | 工商银行 | 国有大行 | 收益型 |
| 601939 | 建设银行 | 国有大行 | 收益型 |
| 601288 | 农业银行 | 县域存款优势 | 收益型 |
| 601988 | 中国银行 | 海外布局 | 收益型 |
| 002142 | 宁波银行 | 高 ROE 成长型城商行 | 成长型（PE+ROE） |

- **交通银行**：默认排除（估值陷阱，通常不推荐）。
- **招商银行 H（03968）**：沙箱/接口稳定性待验证，默认 `INCLUDE_H=False`；数据源稳定后可置 `True` 纳入（`scripts/bank_universe.py`）。
- **估值风格差异**：招行/四大行为「收益型」银行（高分红、低估值），买入信号基于 PB 破净 + 股息率；宁波银行为「成长型」银行（高 ROE、低分红率），买入信号基于 PE + ROE，避免低股息率误判为「持有」。

---

## 五维模型

每维 0–20 分，总分 0–100：

1. **资产质量**：不良率↓、拨备覆盖率↑
2. **负债结构**：活期占比↑、零售存款占比↑
3. **中间业务**：非息收入占比↑
4. **资本实力**：RORWA↑、核心一级资本充足率↑
5. **管理层**：ROE、分红率连续性、零售护城河（代理指标）

评分阈值详见 [`docs/scoring.md`](docs/scoring.md)。

---

## 雪球大V 标的提及追踪表（雪球大V板块）

仪表盘「雪球大V 追踪」板块在每日观点汇总（`xq-summary`，读 xueqiu-tracker 的 `latest.json`）之下，附一张**标的提及追踪表**，数据来自 xueqiu-tracker 的 [`data/mentions.json`](https://raw.githubusercontent.com/homjanon/xueqiu-tracker/main/data/mentions.json)。

**大V投资画像卡**：在标的提及表下方，读取 xueqiu-tracker 的 [`data/vip_profiles.json`](https://raw.githubusercontent.com/homjanon/xueqiu-tracker/main/data/vip_profiles.json)。每位大V一张卡：姓名 + 画像更新日期 + 一句话总评常显，点「展开画像」查看 5 维度（投资理念 / 选股与分析方法 / 交易与仓位习惯 / 关注领域与常谈标的 / 风险态度与心理特质）与近期演化记录。画像由 LLM 依据该大V历史发言每日幂等修订，只记稳定特质、不含行情判断，**仅供参考不构成投资建议**。

**数据链（三级兜底）**：用户自有 Cloudflare 代理 `proxy.hellohopo.dpdns.org`（no-store 实时）首选 → GitHub Contents API → jsDelivr。

**表格内容（全自动，不判断买卖方向）**

- **账户栏（每人）**：上方「仓位」+ 下方「盈亏」，各带命中时间与是否来自自引段（引述）标记。
- **标的行**：标的名称、最近点名时间（按时间倒序）、距今天数、原文摘录、数量。同一标的再次被点名则覆盖主行，「次数」可展开历史（保留最近 3 条）。超过 60 天未再提及的整行置灰。
- 标名后带 `?` 表示该别名未收录进别名词典，可能与其他叫法重复计数。

> 表由脚本自动生成：仅摘录大V**点名提到**的标的与对应原话，**不判断买卖方向**——请看「原文摘录」自行判断。转发引用段（`//@` 之后）已剔除。页面由 `scripts/xq_table_block.py` 提供 CSS/HTML/JS，注入 `scripts/render_html.py` 共同生成 `docs/index.html`。

**数量列的「🔒 人工」角标（人工锁定标的）**

- 「数量」列默认由 xueqiu-tracker 自动抽取（标的近 15 字内明写的数量）；**名单内的标的除外**——上游 `xueqiu-tracker` 的 `config.QTY_LOCKED` 里登记的 `(user_id, 标的名)`，其数量**只保留人工维护值**，自动抽取一律不覆盖，并在看板上于数量右侧显示「**🔒 人工**」角标（悬停提示「人工维护，不随自动抽取更新」）。
- 现登记：**ice_招行谷子地 × 招商银行**（876000股）。原因见上游 README 的踩坑记录：他对招行几乎只买不卖，发言里的数量多为**增量**（如「mnp 抢了 1500 股」= 在底仓上又加了 1500 股），抽取层无法区分 增量 / 存量 / 做 T，曾把 1500股 误当持仓总量覆盖掉人工值。**刻意不做自动累加**——判错会永久漂移且不能自愈，锁定则永远以人工值为准。
- **要改这个数字**：改 `xueqiu-tracker` 的 `data/mentions.json` → `users.1821992043.symbols.招商银行.latest.qty`（改完下一轮 run 不会被冲掉，无需改代码）；要**增删锁定标的**才需动上游 `config.py` 一行。
- 未登记的标的完全走原逻辑，不受影响。

---

## 小散持仓回撤提醒表（持仓回撤板块）

仪表盘在「雪球大V 追踪」板块**上方**附一张**小散持仓回撤提醒表**，按**近 12 个月最高盈利**动态跟踪个人持仓的盈利回落，按回落幅度分档提醒。

**表格内容（6 列）**

| 列 | 含义 |
|----|------|
| 标的 / 代码 | 持仓标的名称与代码 |
| 最高盈利 | `(近12个月前复权最高价 − 下修后成本) / 下修后成本`（需填成本；未填显示 —） |
| 当前盈利 | `(当前价 − 下修后成本) / 下修后成本` |
| 盈利回落 | 最高盈利 − 当前盈利（百分点；≥10 橙 ≥20 红） |
| 提醒 | 按回落幅度四档：≥10 点减仓锁利 / ≥15 点分批接回 / ≥20 点加大买入 / ≥25 点加倍；**当前盈利 ≤0 只提示买入类**；文案按**本次实际回落幅度**的名义档位显示；滞回带防边界闪烁 |

**提醒规则**：≥10 点「可考虑减仓锁利」/ ≥15 点「分批接回」/ ≥20 点「加大买入」/ ≥25 点「加倍」；**当前盈利 ≤0 时不提示减仓**（只提示买入类，文案按实际回落幅度显示）；**滞回带**：触发后需回落收窄 2 点才降档，防边界闪烁。`state.level` 仅作边界防抖存档，**不决定文案**（文案永远反映真实回落）。

**动态基准（核心）**

- 近 12 个月最高价 `ytd_high`（前复权）：首跑/新增标的用**严格滚动 12 个月**（今天 −365 天）历史最高**播种**（A股/港股：腾讯 qfq；美股：yfinance 剔除分红；基金：东财 pingzhongdata 全量净值）；之后每日破新高则**上移**（同时刷新**高点实际发生日**）；高点实际发生日距今 >365 天自动重播（滚动窗口）。
- **跨年不重置**：滚动 12 个月窗口连续跨年，避免 1 月开年即跌时信号失效。
- 价格口径统一用**前复权（纯剔除分红）**，与 A 股一致：实时价锚定最新日（前复权最新日 = 现价），历史最高按「高点之后累计分红」下修，两者口径一致，回撤才不会被**双重计入分红**。

**隐私设计**

- 仓库只提交**派生指标**（回撤%、盈利%、提醒），**成本与市值永不进公开仓库**。
- 成本来自 GitHub Secret `HOLDINGS_JSON`（格式 `[{"code","name","type","cost"}]`，`type` 取 `a_stock`/`hk`/`us`/`fund`），由每日 workflow 在运行时注入。
- 未设 Secret 时回退到仓库内 `data/holdings_preset.json`（仅 code/name/type，无成本）→ 回撤表立即可见，盈利列显示 —，待填成本后自动补全。
- **成本 = 下修后成本（手动维护）**：盈利% 用「前复权价 − 下修后成本」计算，与历史价扣除分红的口径一致。分红后成本会自然降低，请在**分红除息日**把 Secret 里的 `cost` 更新为下修后数值（如 36.56 → 34.54），否则盈利会被低估。

```json
[{"code":"600036","name":"招商银行","type":"a_stock","cost":34.54}]
```

**数据源（近 12 个月最高价播种 / 每日实时价）**

- A股/港股/ETF/美股实时价：腾讯 `qt.gtimg.cn`（锚定最新日）
- 场外基金：天天基金 / 东方财富净值
- 港股/美股播种：yfinance 近 12 个月不复权日K + 手动剔除分红（纯前复权，与 A 股一致）；港股代码自动转雅虎 4 位格式（03968 → 3968.HK）
- 播种兜底：美股 → Nasdaq 历史接口（不复权）；港股 → 腾讯 qfq 日K；基金 → 天天基金/东财 pingzhongdata（NAV 本身已除权，无需再调整）
- 相关脚本：`scripts/query_stock.py`（价格/近 12 个月最高）、`scripts/holdings_drawdown.py`（计算+状态）、`scripts/my_holdings_block.py`（注入 `render_html.py` 的 CSS/HTML/JS）

**本地预填近 12 个月最高价（可选，借本地网络源一次性播种）**

```bash
python -m scripts.holdings_drawdown --seed-only --preset data/holdings_preset.json
```

---

## 数据源与架构（关键）

银行的五维财务字段中，质量字段（不良率/拨备/资本充足率/存款结构/RORWA）是**季度**数据、每日不变；而现价/PE/PB/股息率与部分财务字段是**每日**变化。因此采用「底表为真源 + 每日轻量刷新」的设计：

- **行情（每日）**：腾讯 `qt.gtimg.cn`（主）→ 新浪 `hq.sinajs.cn`（备）→ akshare `stock_zh_a_spot_em`（兜底）。**价格与 PE/PB 均取自腾讯实时**：`parts[3]`=现价、`parts[39]`=市盈率(TTM)、`parts[46]`=市净率(PB)；腾讯缺失时 PE/PB 退 baostock `peTTM/pbMRQ`，再退 现价÷BVPS。
- **财务底表（真源）**：`fundamentals.json` 保存各银行五维原始输入与每日刷新结果。
  - `refresh_light()`：**每日**用 akshare `stock_yjbb_em` 刷新每股净资产(BVPS)/ROE/**EPS（按报告期年化）**，保证 PB 与派息率口径精确。
  - `refresh_nii()`：非息收入占比**兜底** —— 仅当东财 `REVENUE_RATIO` 缺失且设 `BIYING_API_KEY` 时，用必盈利润表 API 推算；否则保持东财自动值或手工值。
  - `refresh_div()`：每股分红 `div_ps` —— **自动**，按股权登记日倒序取最新 2 次「已实施」派息（元/10 股）求和 ÷10，等于最近一个完整年度（本组合均为半年派，规避滚动 365 天窗口跨年抓到 3 次导致股息率/派息率虚高）。
  - 派息率 `div_payout`：**自动**，由 `div_ps ÷ 年化EPS` 计算。
  - `refresh_deep()`：**已启用**，每日用 akshare `stock_financial_analysis_indicator_em`（`按报告期`取最新一期）刷新银行专属指标并写回底表：净息差 NIM / 价差、`npl` 不良率(%)、`capital_adequacy` 资本充足率(总)、`tier1_adequacy` 一级资本充足率、`provision_ratio` 拨贷比（**非**拨备覆盖率）、`non_interest_ratio` 非息收入占比（**自动主源**，替代必盈；必盈仅作缺失兜底）。所有字段含 NaN 守卫（NaN != NaN），EM 返回 nan 时跳过、保留底表手工值。
  - `refresh_research()`：**每日**用 akshare `stock_research_report_em` 抓取分析师研报评级（东财评级 + 近一月研报数 + 最新机构），写回底表并在网页「分析师研报评级」面板展示。**仅作展示，不进入五维评分**。
- **进分与不进分**：`npl` → 资产质量维、`non_interest_ratio` → 中间业务维，进五维评分；`tier1_adequacy` / `capital_adequacy` / `provision_ratio` / 研报评级仅写回底表参考或展示。五维评分仍用人工维护的 `core_tier1`（核心一级）与 `provision_coverage`（拨备覆盖率）。
- **仍人工季度维护的字段**：拨备覆盖率 / 核心一级资本充足率 / 存款结构 / RORWA / 零售护城河（东财 `_em` 接口无对应字段）。
- **未接入**：北向资金个股持股 —— 实测 `stock_hsgt_individual_em` 数据止于 2024-08-16，2024-08-19 起沪深港通暂停北向披露，免费源已无当前数据，留待付费源或仅用南向。

**手工字段更新流程**：新报告期披露后，对照「招招投资风格」skill 的量化标准（拨备 >300% / 核心一级 >11% / 活期 >50% / 零售 >40% / RORWA >1.5%，零售护城河为主观 0–1 评分），更新 `fundamentals.json` 对应银行的 `as_of` + 5 个手工字段。**当前 6 家均已更新至 2026H1 中报（`as_of=2026Q2`）**。

---

## 每日运行

```bash
pip install -r requirements.txt
cd scripts
python run_daily.py
```

> 本地依赖（akshare / pandas / baostock 等）需装在 **Python 3.11+** 虚拟环境；请先 `cd scripts` 再运行（脚本内部按仓库根目录定位文件）。可选环境变量：`BIYING_API_KEY`（仅当东财 `REVENUE_RATIO` 缺失时作非息占比兜底）。

产出：

- `fundamentals.json` — 财务底表（每日刷新 BVPS/ROE/EPS/div_ps/非息占比/净息差/不良率 后写回）
- `history.jsonl` — 每日评分历史（按日期去重累积；**仅交易日写入**）
- `docs/index.html` — 仪表盘（表格 + 五维雷达 + 各维条形 + 雪球大V追踪表 + 小散持仓回撤表）
- `docs/history.html` — 历史趋势（总分 / PB）
- `data/holdings_drawdown.json` — 当日派生回撤表（注入仪表盘；无成本/市值，仅回撤% 与盈利%）
- `output/cmb_report.json` — 机器可读报告

---

## GitHub Actions 自动运行

**触发（单通道）**：Cloudflare Worker `qdii-dispatch`（心跳每 5 分钟）每日**北京时间 16:30** 调用 `workflow_dispatch`。GitHub 侧**无 schedule**。16:30 时 A 股已收盘、数据完整。

**门控**：`check` 步骤用交易日历 `tool_trade_date_hist_sina` 判定当日是否交易日（北京时间），输出 `trade=1/0`；后续各步骤条件为

```yaml
if: steps.check.outputs.trade == '1' || github.event.inputs.force == 'true'
```

- Worker 自动调度**不传** `force` → 严格走门控，非交易日（周末 / 法定假期）**全部步骤 skip**。
- 人工在 Actions 页面**勾选 `force=true`** → 忽略门控强制运行（补算 / 盘中快照）。
- ⚠️ 绝不可改回 `github.event_name == 'workflow_dispatch'` —— 单通道下该条件恒为真，门控会**永久失效**（详见「踩坑记录」）。

**流程**：checkout → 装依赖 → 交易日判断 → `holdings_drawdown.py`（设 `HOLDINGS_JSON`，可选）→ `run_daily.py`（设 `BIYING_API_KEY`）→ 自动 commit。

> ⚠️ **顺序不能反**：`holdings_drawdown.py` 必须先于 `run_daily.py`。`run_daily` 读取 `data/holdings_drawdown.json` 注入网页，若渲染在前，新增标的/改成本要再触发一次才生效。

**提交范围**：`fundamentals.json`、`history.jsonl`、`docs/`、`output/`、`data/holdings_drawdown_state.json`、`data/holdings_drawdown.json`、`data/holdings_preset.json`。

**Pages**：Settings → Pages → Source 选 `main` 分支 `/docs` 目录。

> 本机 `git push` 若被网络限制，可用仓库根目录的 `_api_sync.py`（GitHub Contents API 推送，需 `GITHUB_TOKEN`）替代。

---

## JSON 产出（output/cmb_report.json）

每日自动生成机器可读报告，供外部系统（如投资看板）直接 fetch：

```
https://raw.githubusercontent.com/homjanon/cmb-tracker/main/output/cmb_report.json
```

顶层结构：

```json
{
  "tracker": "cmb-tracker",
  "model": "招招五维模型",
  "generated_at": "2026-07-13T00:10:00+08:00",
  "data_date": "2026-07-13",
  "summary": { "total_banks": 6, "strong_buy": 0, "buy": 0, "hold": 6, "reduce": 0 },
  "banks": [
    {
      "code": "600036", "name": "招商银行", "as_of": "2026Q1",
      "price": 43.5, "pe": 7.3, "pb": 0.97, "div_yield": 4.6,
      "score_total": 82.5,
      "score_dims": { "asset_quality": 18, "liability": 16, "intermediary": 15, "capital": 14, "management": 19.5 },
      "signal": "HOLD", "signal_cn": "持有",
      "valuation_style": "yield",
      "zone_low": 31.44, "zone_high": 40.43,
      "reason": "PB 0.97 高于破净线，股息率 4.6% ..."
    }
  ]
}
```

字段说明：`score_dims` 为五维得分（0–20 各维）；`zone_low`/`zone_high` 为模型给出的买入区间上下限；`signal`/`signal_cn` 为买入信号（`STRONG_BUY`/`BUY`/`HOLD`/`REDUCE`）及中文；`price_source`/`pe_source`/`pb_source` 标注取值来源（`tencent`=实时 / `baostock`=上一交易日兜底 / `bvps`=现价÷BVPS 推算 / `sina`/`akshare`=备源），`quote_time` 为行情抓取时间（ISO8601 含时区），用于识别数据是否陈旧。

---

## 维护财务报表

| 自动化 | 字段 | 来源 |
|--------|------|------|
| 自动 | BVPS / ROE / EPS(年化) / div_ps(每股分红) | akshare（`refresh_light` / `refresh_div`） |
| 自动 | 不良率(npl) / 资本充足率(总) / 一级资本充足率 / 拨贷比 / 非息收入占比 | 东财 `refresh_deep`（NaN 守卫：EM 返回 nan 则保留底表值） |
| 兜底 | 非息收入占比 | 必盈利润表 API（`refresh_nii`，仅当东财 `REVENUE_RATIO` 缺失且设 `BIYING_API_KEY` 时） |
| 展示 | 分析师研报评级（东财评级/近一月研报数/最新机构） | 东财 `refresh_research`（**不进五维评分**） |
| 手工 | 拨备覆盖率 / 核心一级资本充足率 / 存款结构 / RORWA / 零售护城河 | 季度人工更新 `fundamentals.json` |

- **手工字段随季报更新**：直接编辑 `fundamentals.json` 对应字段并改 `as_of`（如 `2026Q2`）。这些字段在 `_manual_maintain` 列表中标记、`refresh_deep` 不返回故不被覆盖。
- **派息率 `div_payout`** 由 `div_ps ÷ 年化EPS` 自动算出，无需手工填。
- 运行 `python calibration.py` 可查看当前评分与缺失字段。

---

## 页面移动端适配

看板为纯静态 HTML（`docs/index.html`），桌面与手机共用一套产物，靠媒体查询切换：

| 断点 | 布局 |
|------|------|
| **≤740px** | 表格转卡片：卡片内 2 列网格，标签左对齐、数值右对齐（形成两条整齐的值列竖线）；成对字段同行（现价\|PE、PB\|股息率、总分\|信号、最高盈利\|当前盈利、最近提及\|距今、评级\|研报数），长内容整宽（买入区间/五维/盈利回落/提醒/数量/原文摘录） |
| **≤350px** | 字号收敛（标签 11px、数值 12.5px），提醒徽标允许折行，最近提及与距今整宽——防极窄屏挤压 |
| **>740px** | 原表格布局，与桌面端一致 |

**实现要点**（全部包在媒体查询内，桌面端零改动）：

- 四个表格模块的单元格均带 `data-label`（`render_html.py` 主表/研报表、`my_holdings_block.py`、`xq_table_block.py`），卡片模式用 `td::before{content:attr(data-label)}` 还原字段名；
- 含多个子节点的值（买入区间/五维/总分/信号）用 `<span class="v">` 包裹，`margin-left:auto` 推至所在列右端；
- 持仓回撤表**无提醒时该行整行隐藏**（`rem-empty` 类），避免空的「提醒 —」白占一行；
- 卡片标题行分隔线用「左格 `margin-right:-14px; padding-right:14px`」弥合网格列间距，保证细线连续；
- 断点取 740px（非 640px）是为修掉 641–737px 区间的横向溢出（实测最大 96px）。

**回归口径**：320/340/360/375/390/414/600/700/739/740/768/1200 共十二档实测，页面横向溢出与单元格内容挤压均为 **0**；桌面端 9/6/6 列表头表体列数一致、名与代码仍为两行。

---

## 目录结构

```
cmb-tracker/
├── .github/workflows/daily.yml   # 由 Cloudflare qdii-dispatch 触发（每天 16:30 · 无 schedule）
├── _api_sync.py                  # GitHub Contents API 推送（替代被墙的 git push）
├── scripts/
│   ├── bank_universe.py          # 标的清单
│   ├── fetch_quotes.py           # 行情（腾讯/新浪/akshare）
│   ├── fetch_fundamentals.py     # 财务底表刷新（light/nii/div/deep/research 多路）
│   ├── zhaozhao_five_dim.py      # 五维评分引擎（纯计算）
│   ├── trade_calendar.py         # 交易日判据（唯一来源，门控与写入闸门共用）
│   ├── render_html.py            # HTML 渲染（仪表盘/历史，注入雪球大V 追踪表 + 小散持仓回撤表）
│   ├── xq_table_block.py         # 雪球大V 标的提及追踪表（CSS/HTML/JS，注入 render_html.py）
│   ├── my_holdings_block.py      # 小散持仓回撤提醒表（CSS/HTML/JS，注入 render_html.py）
│   ├── query_stock.py            # 实时价 + 近12个月最高价（A/港/美/ETF/基金，多源）
│   ├── holdings_drawdown.py      # 盈利回落四档提醒计算（成本Secret → 近12个月最高 → 派生表）
│   ├── build_my_preview.py       # 本地预览构建（桌面持仓 + mentions.json 合成整页）
│   ├── render_report.py          # JSON 产出（output/cmb_report.json）
│   ├── run_daily.py              # 每日编排器（含注入回撤表）
│   ├── calibration.py            # 校准/缺失检查
│   └── retry_utils.py            # 重试/多源容错
├── fundamentals.json             # 财务底表（真源 + 每日刷新结果）
├── history.jsonl                 # 每日历史
├── data/
│   ├── holdings_preset.json      # 预置标的清单（无成本，无 Secret 时驱动回撤表）
│   ├── holdings_drawdown_state.json  # 近12个月最高价动态基准状态（滚动窗口、跨年不重置、提交）
│   └── holdings_drawdown.json    # 当日派生回撤表（注入仪表盘）
├── output/
│   └── cmb_report.json           # 机器可读报告
├── docs/                         # GitHub Pages 产物
│   ├── index.html
│   ├── history.html
│   ├── scoring.md                # 评分阈值说明
│   └── vendor/chart.umd.min.js   # 本地内置 Chart.js（离线渲染图表）
└── requirements.txt
```

---

## 踩坑记录

> 已修复的历史问题，保留根因与约束，避免重蹈。

**① 门控被事件类型条件永久绕过（2026-10-03）**
- **现象**：中秋（09-25 周五）、国庆（10-01 周四 / 10-02 周五）等法定假期照常运行，`history.jsonl` 多出非交易日行（数据为上一交易日的重复值）。
- **根因**：步骤条件写成 `… || github.event_name == 'workflow_dispatch'`。该分支本意是「人工手动触发时强制运行」，但 2026-09-02 触发通道改为 Worker 每日 `workflow_dispatch` 后，**自动调度也命中同一分支** → `check` 算出的 `trade=0` 完全失效。
- **修复**：改用**显式输入** `github.event.inputs.force == 'true'`，并声明 `on.workflow_dispatch.inputs.force`（boolean，默认 false）；同时新增 `scripts/trade_calendar.py` 作为**全项目唯一交易日判据**，`run_daily._append_history` 与 workflow 的 `check` 步骤共用，禁止再写 `weekday() < 5` 之类的近似判定（识别不了周中法定假期，与门控不等价）。
- **约束**：**改了触发通道，必须回头审计所有 `github.event_name` 判断**。「自动」与「人工」在单通道下无法靠事件类型区分。

**② `check` 步骤原用容器 UTC 日期（同批修复）**
- `datetime.date.today()` 在 Actions 容器里是 UTC；仅因 16:30 北京 = 08:30 UTC 同日才没出错。已改为显式北京时间（`timezone(timedelta(hours=8))`）。

**③ 锚点粘滞：播种把「播种当天」当高点日期（2026-09-03）**
- **现象**：招行 2025-07-10 的前复权高点 44.534 一直粘到 2026-09 仍作基准，盈利回落虚报 **9.47pp**（真实约 1.9pp）。
- **根因**：播种写入 `ytd_high_date` 用的是播种当天，锚点虽旧、日期却是新的 → 「锚点滑出窗口 → 重播」永远不触发；叠加取数起点为 `year-01-01`（约 20 个月跨度）把窗口外旧高点捞了进来。
- **修复**：`ytd_high_date` 记录**高点实际发生日**；播种窗口收紧为 `today-365`；state 引入 `anchor_ver`（v1 旧 state 首次运行强制重播完成校准）。yfinance 口径同步改为「逐高点分红下修补正后取最高」，与「A股 qfq 锚定最新日」严格等价。

**④ 转亏文案虚报档位（2026-08-18）**
- 当前盈利 ≤0 时，文案曾因「转亏禁减仓」抬档而虚报更高档位的幅度（020602 回落 10 点却提示「≥15 点接回」）。已改为按**名义档位**显示真实回落幅度。

**⑤ 文案被 state 旧档绑架（2026-08-25）**
- 滞回带「只升不降 + 降档需跌破阈值 −2」把曾触发过高档的标的粘在旧档（招行回落 13.77pp 却显示「≥15 点接回」）。已改为**文案永远反映真实回落**，`state.level` 仅作边界防抖存档。

**⑥ 回撤表与渲染的顺序依赖（2026-08-06）**
- `run_daily` 读取 `data/holdings_drawdown.json` 注入网页；若渲染在前，新增标的/改成本要**再触发一次**才生效。故 workflow 中 `holdings_drawdown.py` 必须排在 `run_daily.py` 之前。

**⑦ 移动端断点取 740px 而非 640px（2026-09-27）**
- 641–737px 区间存在横向溢出（实测最大 96px），断点设 640px 会漏掉该区间，故取 740px。

**⑧ 非交易日推送前端改动不会生效（2026-10-04）**
- **现象**：改了雪球板块的数量角标并推送成功、CI 也 success，但线上看板看不到改动。
- **根因**：workflow 的「仅交易日」门控同时挡住了 `run daily tracker` 与 `Commit & push` → `docs/index.html` **根本没被重新渲染**（当天成功的那次运行只是 Pages 的 Jekyll 发布，用的是仓库里的旧 HTML）。
- **做法**：前端（`scripts/*.py` 模板 / CSS / JS）改动若需立即上线，**手动触发时勾 `force=true`** 强制渲染一轮，等 `chore: daily update` 提交 + Pages 部署完成再验收；否则等到下一个交易日自动生效。判断依据：`git log` 里是否出现新的 `chore: daily update` 提交。

---

*以招招五维框架构建，仅供个人研究。*
