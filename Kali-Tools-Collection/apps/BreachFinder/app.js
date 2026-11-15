const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
let toastTimer;
function toast(message){const el=$('#toast');el.textContent=message;el.classList.add('show');clearTimeout(toastTimer);toastTimer=setTimeout(()=>el.classList.remove('show'),2800)}
function setLoading(button,loading,label){button.disabled=loading;button.querySelector('span').textContent=loading?'Authenticating…':label}
function showApp(user='Analyst'){
 $('#loginView').classList.add('hidden');$('#appView').classList.remove('hidden');
 $('#sideUsername').textContent=user;$('#welcomeName').textContent=user;$('#userAvatar').textContent=(user[0]||'A').toUpperCase();
 $('#todayLabel').textContent=new Intl.DateTimeFormat('it-IT',{day:'2-digit',month:'short',year:'numeric'}).format(new Date()).toUpperCase();
 loadDashboard();
}
function showLogin(){ $('#appView').classList.add('hidden');$('#loginView').classList.remove('hidden') }
function showPage(page){
 $$('.nav-item').forEach(b=>b.classList.toggle('active',b.dataset.page===page));
 const dash=page==='dashboard';$('#dashboardPage').classList.toggle('hidden',!dash);$('#workspacePage').classList.toggle('hidden',dash);
 const labels={dashboard:'Overview',scans:'New scan',reports:'Reports',settings:'Settings'};
 $('#pageCrumb').textContent=labels[page]||'Overview';
 if(page==='scans')renderScans();else if(page==='reports')renderReports();else if(page==='settings')renderSettings();
}
async function loadDashboard(){
 try{
  const r=await fetch('/api/dashboard',{credentials:'same-origin'});if(r.status===401){showLogin();return}if(!r.ok)throw new Error('dashboard');
  const d=await r.json();$('#activeScans').textContent=d.active_scans??0;
  const rows=d.activity||[];$('#completedScans').textContent=rows.filter(x=>String(x.status).toLowerCase()==='completed').length;
  const body=$('#activityRows');
  if(!rows.length){body.innerHTML='<tr class="empty-row"><td colspan="5"><span class="empty-mark">⌕</span><strong>No activity yet</strong><small>Your recent scans will appear here.</small></td></tr>'}
  else body.innerHTML=rows.map(x=>'<tr><td>'+esc(x.target)+'</td><td>'+esc(x.type||'Public breach scan')+'</td><td><span class="status-pill '+(x.status==='Running'?'neutral':'good')+'">'+esc(x.status)+'</span></td><td>'+esc(x.leaks??0)+'</td><td>'+esc(x.date||'—')+'</td></tr>').join('');
  $('#breachRecords').textContent=d.db_status?'READY':'—';
 }catch(e){toast('Impossibile aggiornare la dashboard')}
}
function esc(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
$('#loginForm').addEventListener('submit',async e=>{
 e.preventDefault();const button=$('#loginBtn'),u=$('#loginUser').value.trim(),p=$('#loginPass').value;
 if(!u||!p){$('#loginError').textContent='Inserisci username e password.';return}
 $('#loginError').textContent='';setLoading(button,true,'Access workspace');
 try{const r=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({username:u,password:p})});const d=await r.json();if(!r.ok||!d.ok)throw new Error('Credenziali non valide');showApp(d.user||'Analyst')}
 catch(err){$('#loginError').textContent=err.message==='Credenziali non valide'?'Credenziali non valide.':'Server non raggiungibile.'}
 finally{setLoading(button,false,'Access workspace')}
});
$('#viewPass').onclick=()=>{const p=$('#loginPass');const visible=p.type==='password';p.type=visible?'text':'password';$('#viewPass').textContent=visible?'HIDE':'VIEW'};
$('#forgotBtn').onclick=()=>{$('#loginError').textContent='Il recupero password è gestito dall’amministratore.'};
$('#logoutBtn').onclick=async()=>{try{await fetch('/api/logout',{method:'POST',credentials:'same-origin'})}finally{showLogin();$('#loginPass').value='';toast('Sessione terminata')}};
$$('[data-page]').forEach(b=>b.addEventListener('click',()=>showPage(b.dataset.page)));
$('#refreshBtn').onclick=loadDashboard;
function renderScans(){
 $('#workspaceContent').innerHTML='<div class="workspace-heading"><div class="eyebrow"><span class="eyebrow-line"></span> EXPOSURE INVESTIGATION</div><h1>New scan</h1><p>Search public breach metadata using an identifier you are authorized to investigate.</p></div><div class="workspace-panel"><div class="fields"><label>EMAIL ADDRESS<input id="f-email" type="email" placeholder="name@example.com"></label><label>USERNAME<input id="f-username" placeholder="Public username"></label><label>DOMAIN<input id="f-domain" placeholder="example.com"></label><label>PHONE NUMBER<input id="f-phone" placeholder="+39 …"></label><label>FULL NAME<input id="f-name" placeholder="Public name"></label></div><div class="scan-actions"><button class="primary-btn" id="doScan"><span>Run public breach scan</span><b>↗</b></button><span class="helper-text">Only public breach metadata is queried.</span></div><pre class="log" id="scanLog">Waiting for a scan…</pre><div id="scanResult" class="result-list"></div></div>';
 $('#doScan').onclick=startScan;
}
async function startScan(){
 const button=$('#doScan'),payload={email:$('#f-email').value,username:$('#f-username').value,domain:$('#f-domain').value,phone:$('#f-phone').value,name:$('#f-name').value};
 if(!Object.values(payload).some(v=>v.trim())){toast('Inserisci almeno un identificativo.');return}
 button.disabled=true;button.querySelector('span').textContent='Scanning…';
 const log=$('#scanLog'),result=$('#scanResult');log.textContent='[INFO] Avvio scansione…';result.innerHTML='';
 try{
  const r=await fetch('/api/search',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify(payload)});const d=await r.json();if(!r.ok)throw new Error(d.error||'Errore API');
  for(let i=0;i<120;i++){const q=await fetch('/api/search/'+d.job_id,{credentials:'same-origin'});const j=await q.json();if(!q.ok)throw new Error(j.error||'Errore lettura scansione');log.textContent=(j.logs||[]).map(x=>'['+x.level.toUpperCase()+'] '+x.message).join('\n');log.scrollTop=log.scrollHeight;if(j.status==='completed'){renderResult(j.results,result);loadDashboard();return}await new Promise(resolve=>setTimeout(resolve,500))}
  throw new Error('Timeout scansione');
 }catch(err){log.textContent+='\n[ERROR] '+err.message}
 finally{button.disabled=false;button.querySelector('span').textContent='Run public breach scan'}
}
function renderResult(data,el){
 const sources=data?.sources||[],breaches=sources.flatMap(s=>s.status==='found'?(s.breaches||[]):[]),summary=data?.summary||{};
 const notice='<div class="result-card"><strong>'+(summary.status==='completed'?'Verifica completata':'Verifica parziale')+'</strong><p>'+esc(summary.message||'Controlla il report per i dettagli.')+'</p></div>';
 if(!breaches.length){const sourceState=sources[0]?.status||'not_run';let detail='';if(sourceState==='clear'){detail='XposedOrNot non ha restituito violazioni note per questo indirizzo.'}else if(sourceState==='not_configured'){detail='Il servizio XposedOrNot non è al momento configurato o raggiungibile. Nessuna verifica individuale è stata completata.'}else if(sourceState==='error'){detail='XposedOrNot non ha completato la richiesta. Controlla la connessione o attendi il ripristino del limite gratuito.'}else{detail='Non è stata eseguita una verifica individuale dell’email.'}el.innerHTML=notice+'<div class="result-card"><strong>'+(sourceState==='clear'?'Nessuna violazione nota restituita':'Verifica non disponibile')+'</strong><p>'+esc(detail)+'</p></div>';return}
 el.innerHTML=notice+breaches.map(b=>'<article class="result-card"><strong>'+esc(b.title||b.name||'Breach')+'</strong><p>Domain: '+esc(b.domain||'—')+' · Breach date: '+esc(b.breach_date||'—')+'<br>Records: '+esc(b.pwn_count||'—')+'<br>Exposed data: '+esc((b.data_classes||[]).join(', ')||'Not specified')+'</p></article>').join('');
}
async function renderReports(){
 $('#workspaceContent').innerHTML='<div class="workspace-heading"><div class="eyebrow"><span class="eyebrow-line"></span> INVESTIGATION HISTORY</div><h1>Reports</h1><p>PDF reports generated automatically after each scan.</p></div><div class="workspace-panel"><div id="reportsList" class="reports-list"><div class="empty-state">Loading reports…</div></div></div>';
 const host=$('#reportsList');
 try{
  const r=await fetch('/api/reports',{credentials:'same-origin'});if(r.status===401){showLogin();return}if(!r.ok)throw new Error('Unable to load reports');
  const d=await r.json(),items=d.reports||[];
  if(!items.length){host.innerHTML='<div class="empty-state">No PDF reports yet. Complete a new scan to generate its first report.</div>';return}
  host.innerHTML=items.map(x=>'<article class="report-item"><div class="report-file-icon">PDF</div><div class="report-meta"><strong>'+esc(x.target)+'</strong><small>'+esc(new Date(x.created_at).toLocaleString('it-IT'))+' · '+(x.status==='completed'?'Verifica completata':'Verifica parziale')+'</small></div><span class="report-status '+(x.status==='completed'?'report-ok':'report-partial')+'">'+(x.status==='completed'?'COMPLETED':'PARTIAL')+'</span><a class="download-report" href="'+esc(x.pdf_url)+'" target="_blank" rel="noopener">Download PDF ↗</a></article>').join('');
 }catch(e){host.innerHTML='<div class="empty-state">Errore nel caricamento dei report: '+esc(e.message)+'</div>'}
}
function renderSettings(){
  $('#workspaceContent').innerHTML='<div class="workspace-heading"><div class="eyebrow"><span class="eyebrow-line"></span> CONFIGURATION</div><h1>Settings</h1><p>Provider gratuito per la verifica delle email.</p></div><div class="workspace-panel"><div class="settings-row"><span>Application</span><strong>Breach Tracker v1.2</strong></div><div class="settings-row"><span>Data source</span><strong>XposedOrNot API</strong></div><div class="settings-row"><span>API key</span><strong>Non necessaria</strong></div><div class="settings-row"><span>Free rate limit</span><strong>25 / ora · 100 / giorno per IP</strong></div><div class="settings-row"><span>Provider status</span><strong id="apiKeyStatus">Checking…</strong></div><p class="helper-text">Per i controlli email non devi registrarti né inserire una chiave. La richiesta invia l’email a XposedOrNot tramite HTTPS. I limiti gratuiti sono applicati dal provider per indirizzo IP.</p><p class="helper-text">Fonte: <a href="https://xposedornot.com/api_doc" target="_blank" rel="noopener">documentazione ufficiale XposedOrNot</a>.</p></div>';
  fetch('/api/settings',{credentials:'same-origin'}).then(r=>r.json()).then(d=>$('#apiKeyStatus').textContent=d.provider==='XposedOrNot'?'Available · no key required':'Unavailable').catch(()=>$('#apiKeyStatus').textContent='Unavailable');
}
(async()=>{try{const r=await fetch('/api/session',{credentials:'same-origin'});if(r.ok){const d=await r.json();if(d.authenticated)showApp(d.user||'Analyst')}}catch(e){}})();