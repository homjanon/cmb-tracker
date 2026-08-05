"""小散持仓回撤表：CSS + HTML 容器 + 渲染脚本。

单一事实来源：本地预览与 cmb-tracker/scripts/render_html.py 共用。
列：标的 / 代码 / 今年最高盈利 / 当前回撤 / 回撤提醒。
不展示成本、不展示市值、不展示价格（仅百分比）。成本只在计算期使用，不进仓库。
回撤 >= 阈值（默认 10%）时，「回撤提醒」列显示红字「年内回撤已达10个点」。
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
  <div class="myh-hd">小散持仓回撤<span class="sub">年内最高价动态回撤 · 达10%提醒</span></div>
  <div class="myh-empty">持仓回撤数据加载中…</div>
</div>
<div class="myh-foot">
表格由脚本自动生成：<b>今年最高盈利</b>＝以年内最高价计算的代表盈亏（红涨绿跌）；
<b>当前回撤</b>＝（年内最高价 − 当前价）÷ 年内最高价，按自然年滚动、随新高刷新基准；
<b>回撤提醒</b>＝当前回撤≥10% 时提示「年内回撤已达10个点」。<b>不展示成本与市值</b>。
</div>
"""


def my_holdings_js():
    return r"""
(function(){
  var THRESH=10;
  function esc(s){return String(s==null?"":s).replace(/[&<>"]/g,function(c){
    return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c];});}
  function pct(v){
    if(v==null||isNaN(v)) return '<span style="color:#bbb">—</span>';
    var cls = v>=0 ? 'myh-pos':'myh-neg';
    var sign = v>0?'+':'';
    return '<span class="'+cls+'">'+sign+v.toFixed(2)+'%</span>';
  }
  function rowHtml(h){
    var alert = (h.reminder && h.current_drawdown_pct!=null && h.current_drawdown_pct>=THRESH);
    var dd = (h.current_drawdown_pct==null)?'<span style="color:#bbb">—</span>'
             : '<span class="myh-dd">'+h.current_drawdown_pct.toFixed(2)+'%</span>';
    var rem = alert ? '<span class="myh-alert">'+esc(h.reminder)+'</span>' : '<span style="color:#bbb">—</span>';
    return '<tr'+(alert?' class="alert"':'')+'>'+
      '<td><span class="myh-sym">'+esc(h.name)+'</span></td>'+
      '<td class="myh-code">'+esc(h.code)+'</td>'+
      '<td class="myh-num">'+pct(h.ytd_high_profit_pct)+'</td>'+
      '<td class="myh-num">'+dd+'</td>'+
      '<td>'+rem+'</td></tr>';
  }
  function render(list){
    var root=document.getElementById('myh-root');
    if(!root) return;
    if(!list || !list.length){root.innerHTML='<div class="myh-empty">（暂无持仓回撤数据）</div>';return;}
    var rows=list.map(rowHtml).join("");
    root.innerHTML='<table><thead><tr>'+
      '<th style="width:120px">标的</th><th style="width:80px">代码</th>'+
      '<th style="width:120px;text-align:right">今年最高盈利</th>'+
      '<th style="width:110px;text-align:right">当前回撤</th>'+
      '<th style="width:150px">回撤提醒</th>'+
      '</tr></thead><tbody>'+rows+'</tbody></table>';
  }
  if(window.__MY_HOLDINGS__) { render(window.__MY_HOLDINGS__); return; }
  // 兜底：若页面未内联，可在此加 fetch；当前 cmb 页面构建时已内联
})();
"""
