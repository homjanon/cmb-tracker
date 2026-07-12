# 招招五维模型 · 五大行每日追踪

基于 **招招五维模型** 的选股框架，每日盘后自动抓取招商银行、工商银行、建设银行、农业银行、中国银行、宁波银行的行情与财务数据，计算五维评分、买入信号与买入区间，并发布到 GitHub Pages。

> ⚠️ 本项目仅作个人投资研究记录，**不构成任何投资建议**。

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
- **招商银行 H（03968）**：沙箱/接口稳定性待验证，默认 `INCLUDE_H=False`。数据源稳定后可置 `True` 纳入（`scripts/bank_universe.py`）。
- **估值风格差异**：招行/四大行为「收益型」银行（高分红、低估值），买入信号基于 PB 破净 + 股息率；宁波银行为「成长型」银行（高 ROE、低分红率），买入信号基于 PE + ROE，避免低股息率误判为"持有"。

## 五维模型

每维 0–20 分，总分 0–100：

1. **资产质量**：不良率↓、拨备覆盖率↑
2. **负债结构**：活期占比↑、零售存款占比↑
3. **中间业务**：非息收入占比↑
4. **资本实力**：RORWA↑、核心一级资本充足率↑
5. **管理层**：ROE、分红率连续性、零售护城河（代理指标）

评分阈值详见 [`docs/scoring.md`](docs/scoring.md)。

## 数据源与架构（关键）

银行的五维财务字段（不良率/拨备/非息/资本充足率/RORWA）是**季度**数据，每日不变；而现价/PE/PB/股息率是**每日**变化。因此：

- **行情（每日）**：腾讯 `qt.gtimg.cn`（主）→ 新浪 `hq.sinajs.cn`（备）→ akshare `stock_zh_a_spot_em`（兜底）。这一多源容错链复用自「每日财经早报」项目。
- **财务底表（季度真源）**：`fundamentals.json` 保存各银行最新季度五维原始输入。
  - `scripts/fetch_fundamentals.py → refresh_light()`：**每日**用 akshare `stock_yjbb_em` 刷新每股净资产(BVPS)/ROE/EPS，保证 PB 精确。
  - `refresh_deep()`：季度/手动调用，按 **akshare 原始报表 → 必盈API → 东财F10 → 手工兜底** 的优先级链尝试自动解析五维质量字段；失败则保留缓存。
- **为什么不全自动**：akshare 1.18.x 的 `stock_financial_analysis_indicator` 已失效，利润表/资产负债表原始科目列名漂移，港股接口在沙箱不稳定。故采用「底表为真源 + 每日轻量刷新」的稳健设计。

## 每日运行

```bash
pip install -r requirements.txt
cd scripts
python run_daily.py
```

产出：
- `fundamentals.json` — 财务底表（refresh_light 刷新后写回）
- `history.jsonl` — 每日评分历史（按日期去重累积）
- `docs/index.html` — 仪表盘（表格 + 五维雷达 + 各维条形）
- `docs/history.html` — 历史趋势（总分 / PB）

## GitHub Actions 自动运行

- 触发：`cron` 北京时间每交易日 16:30（UTC 08:30，周一至周五）+ 手动 `workflow_dispatch`
- 流程：checkout → 装依赖 → `run_daily.py` → 自动 commit `fundamentals.json`/`history.jsonl`/`docs/`
- Pages：仓库 Settings → Pages → Source 选 `main` 分支 `/docs` 目录

## 维护财务报表

五维质量字段需随季报更新。两种方式：
1. **手工**：直接编辑 `fundamentals.json` 对应字段，并改 `as_of`。
2. **自动尝试**：`python -c "import fetch_fundamentals as ff, bank_universe as bu, json; print(ff.refresh_deep(bu.all_banks(), json.load(open('../fundamentals.json'))))"` 看能否解析。

运行 `python calibration.py` 可查看当前评分与缺失字段。

## 目录结构

```
cmb-tracker/
├── .github/workflows/daily.yml   # 每日自动化
├── scripts/
│   ├── bank_universe.py          # 标的清单
│   ├── fetch_quotes.py           # 行情（腾讯/新浪/akshare）
│   ├── fetch_fundamentals.py     # 财务底表刷新（轻量+深度兜底链）
│   ├── zhaozhao_five_dim.py      # 五维评分引擎（纯计算）
│   ├── render_html.py            # HTML 渲染
│   ├── run_daily.py              # 每日编排器
│   ├── calibration.py            # 校准/缺失检查
│   └── retry_utils.py            # 重试/多源容错
├── fundamentals.json             # 财务底表（季度真源）
├── history.jsonl                 # 每日历史
├── docs/                         # GitHub Pages 产物
└── requirements.txt
```

---
*以招招五维框架构建，仅供个人研究。*
