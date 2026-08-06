"""小散持仓回撤表：CSS + HTML 容器 + 渲染脚本。

单一事实来源：本地预览与 cmb-tracker/scripts/render_html.py 共用。
列：标的 / 代码 / 最高盈利 / 当前盈利 / 盈利回落 / 提醒（6列，2026-08-06 用户精简）。
不展示成本、不展示市值、不展示价格（仅百分比）。
提醒＝按「回落幅度」四档：≥10减仓锁利 / ≥15分批接回 / ≥20加大买入 / ≥25加倍；
     当前盈利≤0 只提示买入类（不提示减仓）；滞回带防边界闪烁。
基准＝近12个月前复权最高，跨年不重置、滑出窗口自动重播。
成本＝GitHub Secret 手动维护的下修后成本。
"""


def my_holdings_css():
    return """
 .myh{margin-top:6px;margin-bottom:18px}
 .myh-hd{font-size:14px;font-weight:600;color:#333;margin-bottom:8px;
   display:flex;align-items:baseline;gap:8px}
 .myh-hd .sub{font-size:11px;font-weight:400;color:#aaa}
 .myh table{margin:0;box-shadow:none;border:1px solid #f0f0f0}
 .myh th{background:#fafafa;font-size:12px;padding:8px 10px}
 .myh td{padding:8px 10px;font-size:13px;vertical-align:middle}
 .myh-sym{font-weight:600;color:#333;white-space:nowrap}
 .myh-code{color:#888;font-size:12px;white-space:nowrap;font-variant-numeric:tabular-nums}
 .myh-num{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
 .myh-pos{color:#c23531;font-weight:600}   /* 盈利为正：红 */
 .myh-neg{color:#1a9e57;font-weight:600}   /* 盈利为负：绿 */
 .myh-dd0{color:#bbb}                       /* 回落<10：灰 */
 .myh-dd1{color:#e08e0b;font-weight:600}    /* 回落≥10：橙 */
 .myh-dd2{color:#c23531;font-weight:700}    /* 回落≥20：红 */
 .myh-alert{color:#fff;background:#c23531;font-weight:700;font-size:12.5px;
   padding:3px 8px;border-radius:4px;white-space:nowrap}  /* 减仓：红底 */
 .myh-buy{color:#fff;background:#1a9e57;font-weight:700;font-size:12.5px;
   padding:3px 8px;border-radius:4px;white-space:nowrap}  /* 买入类：绿底 */
 .myh-empty{color:#aaa;font-size:12px;padding:10px 0}
 .myh-foot{font-size:11px;color:#aaa;margin-top:8px;line-height:1.7}
 .myh tr.alert td{background:#fdeaea}
 .myh tr.buy td{background:#e8f7ee}
"""


def my_holdings_html():
    return """
<div class="myh" id="myh-root">
  <div class="myh-hd">小散持仓回撤<span class="sub">近12个月最高 · 回落≥10点提醒减仓</span></div>
  <div class="myh-empty">持仓回撤数据加载中…</div>
</div>
<div class="myh-foot">
表格由脚本自动生成：<b>最高盈利</b>＝近12个月最高价（前复权）计算的代表盈亏（红涨绿跌）；
<b>当前盈利</b>＝（当前价 − 下修后成本）÷ 下修后成本；<b>盈利回落</b>＝最高盈利 − 当前盈利（百分点，≥10橙 ≥20红）。
<b>提醒</b>＝按回落幅度四档：<b>≥10点</b>减仓锁利（红）/<b>≥15点</b>分批接回/<b>≥20点</b>加大买入/<b>≥25点</b>加倍（绿）；
当前盈利≤0 时只提示买入类（不提示减仓）。基准近12个月滚动、跨年不重置。
成本由你在 GitHub Secret 手动维护（分红除息日更新为下修后成本）。<b>不展示成本与市值</b>。
</div>
"""


def my_holdings_js():
    return r"""
(function(){
  function esc(s){return String(s==null?"":s).replace(/[&<>"]/g,function(c){
    return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c];});}
  function pct(v){
    if(v==null||isNaN(v)) return '<span style="color:#bbb">—</span>';
    var cls = v>=0 ? 'myh-pos':'myh-neg';
    var sign = v>0?'+':'';
    return '<span class="'+cls+'">'+sign+v.toFixed(2)+'%</span>';
  }
  function ddCell(v){
    if(v==null||isNaN(v)) return '<span style="color:#bbb">—</span>';
    var cls = v>=20 ? 'myh-dd2' : (v>=10 ? 'myh-dd1' : 'myh-dd0');
    return '<span class="'+cls+'">-'+v.toFixed(2)+'pp</span>';
  }
  function remSpan(txt){
    var buy = /接回|加大|加倍/.test(txt);
    return '<span class="'+(buy?'myh-buy':'myh-alert')+'">'+esc(txt)+'</span>';
  }
  function rowHtml(h){
    var alert = !!h.reminder;
    var buy = alert && /接回|加大|加倍/.test(h.reminder);
    var rem = alert ? remSpan(h.reminder) : '<span style="color:#bbb">—</span>';
    return '<tr'+(buy?' class="buy"':(alert?' class="alert"':''))+'>'+
      '<td><span class="myh-sym">'+esc(h.name)+'</span></td>'+
      '<td class="myh-code">'+esc(h.code)+'</td>'+
      '<td class="myh-num">'+pct(h.ytd_high_profit_pct)+'</td>'+
      '<td class="myh-num">'+pct(h.current_profit_pct)+'</td>'+
      '<td class="myh-num">'+ddCell(h.profit_drawdown_pct)+'</td>'+
      '<td>'+rem+'</td></tr>';
  }
  function render(list){
    var root=document.getElementById('myh-root');
    if(!root) return;
    if(!list || !list.length){root.innerHTML='<div class="myh-empty">（暂无持仓回撤数据）</div>';return;}
    var rows=list.map(rowHtml).join("");
    root.innerHTML='<table><thead><tr>'+
      '<th style="width:120px">标的</th><th style="width:80px">代码</th>'+
      '<th style="width:110px;text-align:right">最高盈利</th>'+
      '<th style="width:110px;text-align:right">当前盈利</th>'+
      '<th style="width:100px;text-align:right">盈利回落</th>'+
      '<th style="width:180px">提醒</th>'+
      '</tr></thead><tbody>'+rows+'</tbody></table>';
  }
  if(window.__MY_HOLDINGS__) { render(window.__MY_HOLDINGS__); return; }
  // 兜底：若页面未内联，可在此加 fetch；当前 cmb 页面构建时已内联
})();
"""
