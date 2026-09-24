"""雪球「大V投资画像」卡片区模块：CSS + HTML 容器 + 渲染脚本。

与 xq_table_block.py 同构（单一事实来源，render_html.py 注入共用）。
数据源：xueqiu-tracker 的 data/vip_profiles.json。
数据链（2026-09-24 定稿）：① 用户自有 Cloudflare 代理（proxy.hellohopo.dpdns.org，
no-store 实时、CORS 全开，实测最快）→ ② GitHub Contents API（b64 解析兜底）
→ ③ jsDelivr（末级兜底）。全挂显示兜底文案。
"""

# ---------------------------------------------------------------- CSS
VIP_PROFILE_CSS = """
 .xqp{margin-top:14px;border-top:1px solid #f0f0f0;padding-top:14px}
 .xqp-hd{font-size:13px;font-weight:700;color:#333;margin-bottom:8px}
 .xqp-hd .xqp-sub{font-weight:400;font-size:11px;color:#aaa;margin-left:6px}
 .xqp-user{margin-bottom:14px}
 .xqp-user:last-child{margin-bottom:0}
 .xqp-u-hd{display:flex;align-items:baseline;flex-wrap:wrap;gap:8px;margin-bottom:3px}
 .xqp-name{font-size:14px;font-weight:600;color:#333}
 .xqp-date{color:#b0b8c4;font-size:11px;font-variant-numeric:tabular-nums}
 .xqp-u-hd button{margin-left:auto;border:none;background:#eef2f7;color:#3a4a5e;
   font-size:12px;font-weight:600;padding:2px 10px;border-radius:10px;cursor:pointer;
   font-family:inherit}
 .xqp-u-hd button:hover{background:#dde5ee}
 .xqp-sum{font-size:13px;line-height:1.7;color:#3a4a5e;font-weight:600;margin:2px 0 4px}
 .xqp-det{font-size:13px;line-height:1.8;color:#444}
 .xqp-row{display:flex;gap:10px;padding:5px 0;border-top:1px dashed #f0f0f0}
 .xqp-k{flex:0 0 128px;color:#8a94a6;font-weight:600}
 .xqp-v{flex:1;color:#3a4a5e}
 .xqp-evo{margin-top:8px;padding:6px 10px;background:#fbfcfd;border-radius:6px;
   font-size:11.5px;color:#999;line-height:1.8}
 .xqp-evo .t{font-weight:600;color:#8a94a6}
 .xqp-empty{color:#aaa;font-size:12px;padding:8px 0}
 .xqp-foot{font-size:11px;color:#aaa;margin-top:10px;line-height:1.7}
"""

# ---------------------------------------------------------------- HTML 容器
VIP_PROFILE_HTML = """
<div class="xqp" id="xqp-root"><div class="xqp-empty">大V画像数据加载中…</div></div>
<div class="xqp-foot">
画像由 LLM 依据各人<b>历史发言</b>每日增量修订（重写式、幂等消费），只记录<b>稳定特质</b>，
不含行情判断与操作建议——<b>仅供参考，不构成投资建议</b>。点「展开画像」查看 5 维度细节与近期演化。
</div>
"""

# ---------------------------------------------------------------- 渲染脚本
VIP_PROFILE_JS = r"""
(function(){
  var RAW="https://raw.githubusercontent.com/homjanon/xueqiu-tracker/main/data/vip_profiles.json";
  var PROXY="https://proxy.hellohopo.dpdns.org/?url="+encodeURIComponent(RAW);
  var API="https://api.github.com/repos/homjanon/xueqiu-tracker/contents/data/vip_profiles.json";
  var CDN="https://cdn.jsdelivr.net/gh/homjanon/xueqiu-tracker@main/data/vip_profiles.json";
  var DIMS=["投资理念","选股与分析方法","交易与仓位习惯","关注领域与常谈标的","风险态度与心理特质"];

  function esc(s){return String(s==null?"":s).replace(/[&<>"]/g,function(c){
    return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c];});}

  function userCard(u,seq){
    var p=(u&&u.profile)||{};
    var rows="";
    DIMS.forEach(function(k){
      if(p[k]) rows+='<div class="xqp-row"><span class="xqp-k">'+k+'</span>'+
        '<span class="xqp-v">'+esc(p[k])+'</span></div>';
    });
    if(!rows) return "";
    var evo=(u.evolution||[]).slice(-3).map(function(l){
      return '<div>'+esc(l)+'</div>';}).join("");
    var det='<div class="xqp-det" id="xqp-d'+seq+'" style="display:none">'+rows+
      (evo?'<div class="xqp-evo"><span class="t">近期演化</span>'+evo+'</div>':'')+'</div>';
    return '<div class="xqp-user"><div class="xqp-u-hd">'+
      '<span class="xqp-name">'+esc(u.name||'')+'</span>'+
      (u.last_profile_date?'<span class="xqp-date">画像更新 '+esc(u.last_profile_date)+'</span>':'')+
      '<button type="button" data-p="'+seq+'">展开画像</button></div>'+
      '<div class="xqp-sum">'+esc(u.summary||'')+'</div>'+det+'</div>';
  }

  function render(d){
    var root=document.getElementById('xqp-root');
    if(!root) return;
    var users=(d&&d.users)?d.users:{};
    var html=Object.keys(users).map(function(k,i){return userCard(users[k],i);})
      .join("").replace(/^\s+|\s+$/g,"");
    root.innerHTML=html||'<div class="xqp-empty">（画像尚未生成，等 xueqiu-tracker 首轮运行后出现）</div>';
    root.addEventListener('click',function(e){
      var b=e.target.closest('button[data-p]'); if(!b) return;
      var det=document.getElementById('xqp-d'+b.getAttribute('data-p'));
      if(!det) return;
      var open=det.style.display!=='none';
      det.style.display=open?'none':'';
      b.textContent=open?'展开画像':'收起画像';
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
  tryUrl(PROXY,false)
    .catch(function(){return tryUrl(API,true);})
    .catch(function(){return tryUrl(CDN,false);})
    .then(render)
    .catch(function(){
      var root=document.getElementById('xqp-root');
      if(root) root.innerHTML='<div class="xqp-empty">（大V画像数据暂不可得）</div>';
    });
})();
"""
