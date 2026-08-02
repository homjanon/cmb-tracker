"""雪球「标的提及追踪」表格模块：CSS + HTML 容器 + 渲染脚本。

本文件是单一事实来源：本地预览与 cmb-tracker/scripts/render_html.py 共用，
避免预览版和线上版样式漂移。
"""

# ---------------------------------------------------------------- CSS
XQ_TABLE_CSS = """
 .xqm{margin-top:14px;border-top:1px solid #f0f0f0;padding-top:14px}
 .xqm-user{margin-bottom:18px}
 .xqm-user:last-child{margin-bottom:0}
 .xqm-hd{display:flex;align-items:baseline;flex-wrap:wrap;gap:8px;margin-bottom:4px}
 .xqm-name{font-size:14px;font-weight:600;color:#333}
 .xqm-acc{margin:1px 0 9px;font-size:12.5px;line-height:1.95}
 .xqm-acc-row{display:flex;align-items:baseline;gap:8px}
 .xqm-acc-k{flex:0 0 32px;color:#8a94a6;font-weight:600}
 .xqm-acc-v{color:#3a4a5e;font-weight:600}
 .xqm-acc-d{color:#b0b8c4;font-size:11px;font-variant-numeric:tabular-nums}
 .xqm-acc-q{color:#e6a23c;font-size:11px;margin-left:2px}
 .xqm table{margin:0;box-shadow:none;border:1px solid #f0f0f0}
 .xqm th{background:#fafafa;font-size:12px;padding:8px 10px}
 .xqm td{padding:8px 10px;font-size:13px;vertical-align:top}
 .xqm tr.stale td{color:#b0b0b0}
 .xqm tr.stale .xqm-sym{color:#999}
 .xqm-sym{font-weight:600;color:#333;white-space:nowrap}
 .xqm-unk{color:#e6a23c;font-size:11px;margin-left:2px;cursor:help}
 .xqm-t{color:#888;font-size:12px;white-space:nowrap;font-variant-numeric:tabular-nums}
 .xqm-age{color:#aaa;font-size:12px;white-space:nowrap}
 .xqm-q{color:#444;line-height:1.6}
 .xqm-qty{white-space:nowrap;font-variant-numeric:tabular-nums;color:#c23531;font-weight:600}
 .xqm-n{text-align:center;white-space:nowrap}
 .xqm-n button{border:none;background:#eef2f7;color:#3a4a5e;font-size:12px;font-weight:600;
   padding:2px 8px;border-radius:10px;cursor:pointer;font-family:inherit}
 .xqm-n button:hover{background:#dde5ee}
 .xqm-n button.flat{background:none;cursor:default;color:#bbb;font-weight:400}
 .xqm-n button.flat:hover{background:none}
 .xqm-his td{background:#fbfcfd;font-size:12px;color:#777;padding:6px 10px 6px 22px}
 .xqm-his .h{display:flex;gap:8px;padding:2px 0}
 .xqm-his .h span{color:#999;white-space:nowrap;font-variant-numeric:tabular-nums}
 .xqm-empty{color:#aaa;font-size:12px;padding:10px 0}
 .xqm-foot{font-size:11px;color:#aaa;margin-top:10px;line-height:1.7}
@media(max-width:720px){
 .xqm-age,.xqm thead th.c-age{display:none}
 .xqm td,.xqm th{padding:7px 6px;font-size:12px}
}
"""

# ---------------------------------------------------------------- HTML 容器
XQ_TABLE_HTML = """
<div class="xqm" id="xqm-root"><div class="xqm-empty">标的提及数据加载中…</div></div>
<div class="xqm-foot">
表格由脚本自动生成：仅摘录大V<b>点名提到</b>的标的与对应原话，<b>不判断买卖方向</b>——请看「原文摘录」自行判断。
账户栏的<b>仓位</b>（满融/X%仓位等）与<b>盈利</b>（账户整体盈亏/收益率）为脚本自动抽取，置于标的表上方。
转发引用段（//@ 之后）已剔除，不会把网友的持仓算到大V头上。
同一标的再次被提及则覆盖主行，点「次数」可展开历史；超过 60 天未再提及的条目置灰。
标的名后带 <span style="color:#e6a23c">?</span> 表示未收录进别名词典，可能与同一标的的其它叫法重复计算。
</div>
"""

# ---------------------------------------------------------------- 渲染脚本
XQ_TABLE_JS = r"""
(function(){
  var MENT_API="https://api.github.com/repos/homjanon/xueqiu-tracker/contents/data/mentions.json";
  var MENT_CDN="https://cdn.jsdelivr.net/gh/homjanon/xueqiu-tracker@main/data/mentions.json";
  var STALE_DAYS=60;

  function esc(s){return String(s==null?"":s).replace(/[&<>"]/g,function(c){
    return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c];});}
  function pad(n){return n<10?"0"+n:""+n;}
  function fmt(ts){var d=new Date(ts);
    return pad(d.getMonth()+1)+"-"+pad(d.getDate())+" "+pad(d.getHours())+":"+pad(d.getMinutes());}
  function ageDays(ts){return Math.floor((Date.now()-ts)/86400000);}

  function accTag(acc){
    if(!acc) return "";
    var rows="";
    if(acc.position){
      rows+='<div class="xqm-acc-row"><span class="xqm-acc-k">仓位</span>'+
        '<span class="xqm-acc-v">'+esc(acc.position)+'</span>'+
        (acc.position_at?'<span class="xqm-acc-d">'+fmt(acc.position_at)+'</span>':'')+
        (acc.position_quoted?'<span class="xqm-acc-q">引述</span>':'')+'</div>';
    }
    if(acc.pnl){
      rows+='<div class="xqm-acc-row"><span class="xqm-acc-k">盈利</span>'+
        '<span class="xqm-acc-v">'+esc(acc.pnl)+'</span>'+
        (acc.pnl_at?'<span class="xqm-acc-d">'+fmt(acc.pnl_at)+'</span>':'')+
        (acc.pnl_quoted?'<span class="xqm-acc-q">引述</span>':'')+'</div>';
    }
    return rows?'<div class="xqm-acc">'+rows+'</div>':"";
  }

  function rowHtml(name,s,idx){
    var L=s.latest||{}, age=ageDays(L.at), stale=age>STALE_DAYS;
    var his=(s.history||[]);
    var nCell=his.length
      ? '<button type="button" data-t="'+idx+'">'+s.mention_count+'</button>'
      : '<button type="button" class="flat">'+s.mention_count+'</button>';
    var h='<tr'+(stale?' class="stale"':'')+'>'+
      '<td><span class="xqm-sym">'+esc(name)+'</span>'+
        (s.normalized?'':'<span class="xqm-unk" title="未收录进别名词典">?</span>')+'</td>'+
      '<td class="xqm-t">'+fmt(L.at)+'</td>'+
      '<td class="xqm-age c-age">'+age+'天</td>'+
      '<td class="xqm-q">'+esc(L.quote)+'</td>'+
      '<td class="xqm-qty">'+(L.qty?esc(L.qty):'<span style="color:#ccc">—</span>')+'</td>'+
      '<td class="xqm-n">'+nCell+'</td></tr>';
    if(his.length){
      var inner=his.map(function(r){
        return '<div class="h"><span>'+fmt(r.at)+'</span><em style="font-style:normal">'+
               esc(r.quote)+(r.qty?'（'+esc(r.qty)+'）':'')+'</em></div>';}).join("");
      h+='<tr class="xqm-his" id="xqm-h'+idx+'" style="display:none"><td colspan="6">'+inner+'</td></tr>';
    }
    return h;
  }

  function userHtml(u,seq){
    var syms=u.symbols||{};
    var keys=Object.keys(syms).sort(function(a,b){
      return (syms[b].latest.at||0)-(syms[a].latest.at||0);});
    var body="";
    if(!keys.length){
      body='<div class="xqm-empty">暂无点名提及的标的</div>';
    }else{
      var rows=keys.map(function(k,i){return rowHtml(k,syms[k],seq+"_"+i);}).join("");
      body='<table><thead><tr>'+
        '<th style="width:92px">标的</th><th style="width:92px">最近提及</th>'+
        '<th class="c-age" style="width:52px">距今</th><th>原文摘录</th>'+
        '<th style="width:66px">数量</th><th style="width:52px">次数</th>'+
        '</tr></thead><tbody>'+rows+'</tbody></table>';
    }
    return '<div class="xqm-user"><div class="xqm-hd"><span class="xqm-name">'+
      esc(u.name)+'</span></div>'+accTag(u.account)+body+'</div>';
  }

  function render(d){
    var root=document.getElementById('xqm-root');
    if(!root) return;
    var users=(d&&d.users)?Object.keys(d.users).map(function(k){return d.users[k];}):[];
    if(!users.length){root.innerHTML='<div class="xqm-empty">（暂无标的提及数据）</div>';return;}
    root.innerHTML=users.map(function(u,i){return userHtml(u,i);}).join("");
    root.addEventListener('click',function(e){
      var b=e.target.closest('button[data-t]'); if(!b) return;
      var tr=document.getElementById('xqm-h'+b.getAttribute('data-t'));
      if(tr) tr.style.display=(tr.style.display==='none')?'':'none';
    });
  }

  function b64ToObj(b64){
    var bin=atob(b64.replace(/\s/g,''));
    var bytes=new Uint8Array(bin.length);
    for(var i=0;i<bin.length;i++) bytes[i]=bin.charCodeAt(i);
    return JSON.parse(new TextDecoder('utf-8').decode(bytes));
  }
  function tryUrl(url,isApi){
    return fetch(url,{cache:'no-store'}).then(function(r){
      if(!r.ok) throw new Error(r.status);
      return r.json();
    }).then(function(d){
      return isApi ? (d&&d.content ? b64ToObj(d.content)
                                   : (function(){throw new Error('empty');})()) : d;
    });
  }
  if(window.__XQM_INLINE__){ render(window.__XQM_INLINE__); return; }
  tryUrl(MENT_API,true).catch(function(){return tryUrl(MENT_CDN,false);}).then(render)
    .catch(function(){
      var root=document.getElementById('xqm-root');
      if(root) root.innerHTML='<div class="xqm-empty">（标的提及数据暂不可得）</div>';
    });
})();
"""
