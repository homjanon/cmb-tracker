"""小散持仓回撤表：CSS + HTML 容器 + 渲染脚本。

单一事实来源：本地预览与 cmb-tracker/scripts/render_html.py 共用。
列：标的 / 代码 / 最高盈利 / 当前盈利 / 盈利回撤 / 市场回撤 / 提醒。
不展示成本、不展示市值、不展示价格（仅百分比）。成本只在计算期使用，不进仓库。
提醒：当前盈利 ≥5% 且从最高盈利相对回撤 ≥10% 时，红字「盈利回撤≥X%，考虑止盈」。
基准为持仓以来最高（前复权），跨年不重置、只升不降（2026-08-06 用户决策）。
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
 .myh-dd{color:#1a9e57;font-weight:600}    /* 回撤为跌：绿 */
 .myh-alert{color:#fff;background:#c23531;font-weight:700;font-size:12.5px;
   padding:3px 8px;border-radius:4px;white-space:nowrap}
 .myh-empty{color:#aaa;font-size:12px;padding:10px 0}
 .myh-foot{font-size:11px;color:#aaa;margin-top:8px;line-height:1.7}
@keyframes myhblink{0%,100%{opacity:1}50%{opacity:.55}}
 .myh tr.alert td{background:#fdeaea}
"""


def my_holdings_html():
    return """
<div class="myh" id="myh-root">
  <div class="myh-hd">小散持仓回撤<span class="sub">持仓以来最高 · 盈利回撤≥10%提醒止盈</span></div>
  <div class="myh-empty">持仓回撤数据加载中…</div>
</div>
<div class="myh-foot">
表格由脚本自动生成：<b>最高盈利</b>＝以持仓以来最高价（前复权）计算的代表盈亏（红涨绿跌）；
<b>当前盈利</b>＝（当前价 − 成本）÷ 成本；<b>盈利回撤</b>＝最高盈利 − 当前盈利（百分点，跌为绿）；
<b>市场回撤</b>＝（持仓以来最高价 − 当前价）÷ 最高价（仅参考，不触发提醒）。
<b>提醒</b>＝当前盈利 ≥5% 且从最高盈利相对回撤 ≥10% 时提示「考虑止盈」。
基准为持仓以来最高、<b>跨年不重置</b>（只升不降）。<b>不展示成本与市值</b>。
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
  function rowHtml(h){
    var alert = !!h.reminder;
    var cur = (h.current_profit_pct==null)?'<span style="color:#bbb">—</span>':pct(h.current_profit_pct);
    var pdd = (h.profit_drawdown_pct==null)?'<span style="color:#bbb">—</span>'
             : '<span class="myh-dd">-'+h.profit_drawdown_pct.toFixed(2)+'pp</span>';
    var mkt = (h.current_drawdown_pct==null)?'<span style="color:#bbb">—</span>'
             : '<span class="myh-dd">'+h.current_drawdown_pct.toFixed(2)+'%</span>';
    var rem = alert ? '<span class="myh-alert">'+esc(h.reminder)+'</span>' : '<span style="color:#bbb">—</span>';
    return '<tr'+(alert?' class="alert"':'')+'>'+
      '<td><span class="myh-sym">'+esc(h.name)+'</span></td>'+
      '<td class="myh-code">'+esc(h.code)+'</td>'+
      '<td class="myh-num">'+pct(h.ytd_high_profit_pct)+'</td>'+
      '<td class="myh-num">'+cur+'</td>'+
      '<td class="myh-num">'+pdd+'</td>'+
      '<td class="myh-num">'+mkt+'</td>'+
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
      '<th style="width:100px;text-align:right">盈利回撤</th>'+
      '<th style="width:100px;text-align:right">市场回撤</th>'+
      '<th style="width:160px">提醒</th>'+
      '</tr></thead><tbody>'+rows+'</tbody></table>';
  }
  if(window.__MY_HOLDINGS__) { render(window.__MY_HOLDINGS__); return; }
  // 兜底：若页面未内联，可在此加 fetch；当前 cmb 页面构建时已内联
})();
"""
