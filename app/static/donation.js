const msg=document.getElementById('donation-message');
async function post(url,data){const reply=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}),body=await reply.json();if(!reply.ok)throw new Error(body.message||'操作失败');return body}
function act(task){return async()=>{msg.textContent='处理中…';try{await task();location.reload()}catch(err){msg.textContent=err.message}}}
const val=id=>document.getElementById(id).value;
document.getElementById('library-form').addEventListener('submit',e=>{e.preventDefault();act(async()=>{const gaps=val('lib-gaps').split('\n').map(s=>s.trim()).filter(Boolean).map(line=>{const[issn,title,year,issue,since]=line.split(/[,，]/).map(s=>(s||'').trim());return{issn,title,year,issue,since:since||undefined}});await post('/api/8/libraries',{name:val('lib-name'),gaps})})()});
document.getElementById('donation-form').addEventListener('submit',e=>{e.preventDefault();act(async()=>{await post('/api/8/donations',{issn:val('don-issn'),title:val('don-title'),year:val('don-year'),issues:val('don-issues'),donor:val('don-donor')})})()});
document.querySelectorAll('[data-claim-submit]').forEach(btn=>btn.onclick=act(async()=>{await post('/api/8/claims',{donation_id:btn.dataset.donation,library_id:document.getElementById('claim-lib-'+btn.dataset.donation).value})}));
document.querySelectorAll('[data-confirm]').forEach(btn=>btn.onclick=act(async()=>{await post('/api/8/review',{donation_id:btn.dataset.donation,claim_id:btn.dataset.claim,revision:Number(btn.dataset.revision)})}));
document.querySelectorAll('[data-arrive]').forEach(btn=>btn.onclick=act(async()=>{await post('/api/8/arrive',{donation_id:btn.dataset.donation})}));
document.getElementById('demo8').onclick=act(async()=>{
  const a=await post('/api/8/libraries',{name:'甲馆',gaps:[
    {issn:'1000-0001',title:'图情学刊',year:'2025',issue:'1',since:'2026-02-01'},
    {issn:'1000-0001',title:'图情学刊',year:'2025',issue:'2',since:'2026-02-01'},
    {issn:'1000-0001',title:'图情学刊',year:'2025',issue:'3',since:'2026-02-01'}]});
  const b=await post('/api/8/libraries',{name:'乙馆',gaps:[
    {issn:'1000-0001',title:'图情学刊',year:'2025',issue:'2',since:'2025-06-01'},
    {issn:'1000-0001',title:'图情学刊',year:'2025',issue:'5',since:'2025-06-01'},
    {issn:'1000-0002',title:'图情通讯',year:'2024',issue:'7',since:'2024-03-01'}]});
  const don=await post('/api/8/donations',{issn:'1000-0001',title:'图情学刊',year:'2025',issues:'1-3',donor:'张氏赠'});
  await post('/api/8/claims',{donation_id:don.id,library_id:a.id});
  await post('/api/8/claims',{donation_id:don.id,library_id:b.id});
});
