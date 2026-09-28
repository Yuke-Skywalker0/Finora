const FINORA_APP_VERSION="10.0.0";
const UPDATE_VERSION_KEY="finora_installed_version";
const isInstalledMobile=()=>window.matchMedia?.("(display-mode: standalone)").matches||window.navigator.standalone===true;
const updateGate={
  show(title="Controllo aggiornamenti",message="Stiamo verificando che tu stia usando la versione più recente.",status="Controllo in corso…"){
    const g=$("#update-gate"); if(!g)return;
    g.classList.remove("hidden","is-error","is-ready"); $("#update-title").textContent=title; $("#update-message").textContent=message; $("#update-status-text").textContent=status; $("#update-retry").classList.add("hidden"); $("#update-spinner").style.display="inline-block";
  },
  progress(){const b=$("#update-progress-bar"); if(b)b.style.width="55%"},
  ready(){const g=$("#update-gate"); if(!g)return; g.classList.add("is-ready"); $("#update-progress-bar").style.width="100%"; $("#update-spinner").style.display="none"; $("#update-status-text").textContent="Aggiornamento completato ✓"},
  error(message){const g=$("#update-gate"); if(!g)return; g.classList.add("is-error"); $("#update-message").textContent=message; $("#update-status-text").textContent="Non è stato possibile completare il controllo."; $("#update-spinner").style.display="none"; $("#update-retry").classList.remove("hidden")},
  hide(){$("#update-gate")?.classList.add("hidden")}
};
async function checkMobileAppUpdate(){
  if(!isInstalledMobile() || !("serviceWorker" in navigator)) return true;
  updateGate.show();
  const retry=$("#update-retry");
  const run=async()=>{
    retry.classList.add("hidden"); updateGate.show();
    try{
      const registration=await navigator.serviceWorker.register("./sw.js",{updateViaCache:"none"});
      updateGate.progress();
      const response=await fetch(`./version.json?t=${Date.now()}`,{cache:"no-store",headers:{"Cache-Control":"no-cache"}});
      if(!response.ok)throw new Error("version unavailable");
      const remote=await response.json();
      const remoteVersion=String(remote.version||FINORA_APP_VERSION);
      const localVersion=localStorage.getItem(UPDATE_VERSION_KEY);
      if(!localVersion){
        localStorage.setItem(UPDATE_VERSION_KEY,remoteVersion);
        updateGate.ready();
        await new Promise(r=>setTimeout(r,350));
        updateGate.hide();
        return true;
      }
      if(localVersion===remoteVersion){
        await registration.update();
        if(registration.waiting){
          updateGate.show("Aggiornamento disponibile","È disponibile una nuova versione di Finora. La installiamo prima di aprire l’app.","Installazione aggiornamento…");
          return await activateWaiting(registration,remoteVersion);
        }
        updateGate.ready(); await new Promise(r=>setTimeout(r,250)); updateGate.hide(); return true;
      }
      updateGate.show("Aggiornamento disponibile","Abbiamo trovato una nuova versione di Finora. Attendi qualche secondo: l’app verrà aperta solo quando l’aggiornamento sarà completato.","Download e installazione in corso…");
      await registration.update();
      if(registration.waiting) return await activateWaiting(registration,remoteVersion);
      return await waitForInstalling(registration,remoteVersion);
    }catch(err){
      console.error("Finora update check",err); updateGate.error("Controlla la connessione e riprova. Finora non verrà avviata finché il controllo non sarà completato."); return false;
    }
  };
  retry.onclick=run;
  return run();
}
function activateWaiting(registration,version){
  return new Promise(resolve=>{
    const onController=()=>{navigator.serviceWorker.removeEventListener("controllerchange",onController);localStorage.setItem(UPDATE_VERSION_KEY,version);updateGate.ready();setTimeout(()=>{location.reload();resolve(false)},500)};
    navigator.serviceWorker.addEventListener("controllerchange",onController);
    registration.waiting.postMessage({type:"SKIP_WAITING"});
  });
}
function waitForInstalling(registration,version){
  return new Promise((resolve,reject)=>{
    const worker=registration.installing;
    if(!worker){reject(new Error("update worker unavailable"));return}
    worker.addEventListener("statechange",()=>{
      if(worker.state==="installed"&&navigator.serviceWorker.controller&&registration.waiting){activateWaiting(registration,version).then(resolve);}
      else if(worker.state==="redundant")reject(new Error("update failed"));
    });
  });
}
const state={user:null,transactions:[],accounts:[],budgets:[],goals:[],recurring:[],overviewChart:null,categoryChart:null,analyticsChart:null,analyticsData:null,filter:"all",allFilter:"all",search:"",allSearch:"",txType:"expense",editingTransaction:null};
const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const money=v=>new Intl.NumberFormat("it-IT",{style:"currency",currency:"EUR"}).format(v||0);
const dateIT=v=>new Date(v+"T00:00:00").toLocaleDateString("it-IT",{day:"2-digit",month:"short",year:"numeric"});
function esc(v){return String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#039;"}[c]))}
function toast(m){const e=$("#toast");e.textContent=m;e.classList.add("show");clearTimeout(toast.t);toast.t=setTimeout(()=>e.classList.remove("show"),2500)}
function icon(c){return ({Cibo:"🍴",Trasporti:"🚗",Casa:"⌂",Bollette:"▣",Shopping:"◇",Gaming:"◈",Lavoro:"▰",Altro:"●"}[c]||"●")}
function showView(view){if(view==='planning' && $('#calendar-grid')) renderPlanning();$$('.view').forEach(v=>v.classList.toggle('active',v.id===`${view}-view`));$$('[data-view]').forEach(b=>b.classList.toggle('active',b.dataset.view===view));document.body.classList.remove('menu-open');$('#sidebar-backdrop')?.classList.add('hidden');$('.sidebar')?.classList.remove('open');window.scrollTo({top:0,behavior:'smooth'})}
function showAuth(){$('#auth-view').classList.remove('hidden');$('#app-view').classList.add('hidden')}
function renderAccounts(accounts){
  state.accounts=accounts||[];
  const total=state.accounts.reduce((sum,a)=>sum+Number(a.balance||0),0);
  const summary=$("#accounts-summary");
  if(summary) summary.innerHTML=`<div class="account-total"><span>Patrimonio disponibile</span><strong>${money(total)}</strong><small>${state.accounts.length} ${state.accounts.length===1?"conto":"conti"} collegati</small></div>`;
  const list=$("#accounts-list");
  if(list) list.innerHTML=state.accounts.map(a=>`<article class="account-card"><div class="account-icon">${a.type==="bank"?"🏦":a.type==="card"?"💳":a.type==="cash"?"💶":"👛"}</div><div class="account-info"><b>${esc(a.name)}</b><small>${esc(a.type)}</small></div><strong>${money(a.balance)}</strong><button class="delete-account" data-account-id="${a.id}">Elimina</button></article>`).join("")||`<div class="empty account-empty">Nessun conto ancora. Aggiungine uno per trasformare il saldo in un vero saldo disponibile.</div>`;
  const select=$("#transaction-account");
  if(select) select.innerHTML='<option value="">Nessun conto</option>'+state.accounts.map(a=>`<option value="${a.id}">${esc(a.name)} · ${money(a.balance)}</option>`).join("");
  const recSelect=$("#rec-account");
  if(recSelect) recSelect.innerHTML='<option value="">Nessun conto</option>'+state.accounts.map(a=>`<option value="${a.id}">${esc(a.name)}</option>`).join("");
}
function renderGoals(rows){state.goals=rows||[];const e=$("#goals-list");if(!e)return;e.innerHTML=state.goals.map(g=>`<article class="goal-card"><div class="goal-top"><span class="goal-icon">◎</span><button class="module-delete" data-goal-id="${g.id}">×</button></div><h3>${esc(g.name)}</h3><div class="goal-amount"><strong>${money(g.current_amount)}</strong><span>di ${money(g.target_amount)}</span></div><div class="progress"><i style="width:${g.percentage}%"></i></div><div class="goal-meta"><span>${g.percentage}% completato</span><span>${g.deadline?dateIT(g.deadline):"Nessuna scadenza"}</span></div></article>`).join("")||'<div class="empty">Nessun obiettivo.</div>'}
function renderBudgets(rows){state.budgets=rows||[];const e=$("#budgets-list");if(!e)return;e.innerHTML=state.budgets.map(b=>`<article class="budget-card"><div class="budget-head"><div><b>${esc(b.category)}</b><small>${esc(b.month)}</small></div><button class="module-delete" data-budget-id="${b.id}">×</button></div><div class="budget-numbers"><strong>${money(b.spent)}</strong><span> / ${money(b.limit)}</span></div><div class="progress"><i style="width:${b.percentage}%"></i></div><small class="${b.remaining<0?'over':''}">${b.remaining>=0?money(b.remaining)+" disponibili":"Budget superato di "+money(Math.abs(b.remaining))}</small></article>`).join("")||'<div class="empty">Nessun budget.</div>'}
function renderRecurring(rows){state.recurring=rows||[];const e=$("#recurring-list");if(!e)return;e.innerHTML=state.recurring.map(r=>`<div class="module-row"><div><b>${esc(r.description)}</b><small>${esc(r.category)} · ${r.frequency} · prossima ${dateIT(r.next_date)}</small></div><strong class="${r.type}">${r.type==="income"?"+":"−"}${money(r.amount)}</strong><button class="module-delete" data-recurring-id="${r.id}">×</button></div>`).join("")||'<div class="empty">Nessuna ricorrente.</div>'}
function showApp(){$('#auth-view').classList.add('hidden');$('#app-view').classList.remove('hidden');const n=state.user?.name?.split(' ')[0]||'utente';$('#welcome').textContent=`Ciao, ${n} 👋`;$('#avatar').textContent=n[0]?.toUpperCase()||'U'}
function initGoogle(){const id=window.FINORA_CONFIG.GOOGLE_CLIENT_ID;if(!window.google||id.startsWith('INSERISCI_')){$('#google-button').innerHTML='<p class="micro">Configura GOOGLE_CLIENT_ID in js/config.js per abilitare il login.</p>';return}google.accounts.id.initialize({client_id:id,callback:async r=>{try{state.user=await API.googleLogin(r.credential);showApp();await loadDashboard()}catch(e){toast(e.message)}}});google.accounts.id.renderButton($('#google-button'),{theme:'outline',size:'large',shape:'pill',width:320,text:'continue_with'})}
function renderTransactions(target='#transactions-list',limit=8){const list=$(target);if(!list)return;let a=state.transactions.filter(t=>(state.filter==='all'||t.type===state.filter)&&(!state.search||`${t.description} ${t.category}`.toLowerCase().includes(state.search.toLowerCase())));if(target==='#all-transactions')a=state.transactions.filter(t=>(state.allFilter==='all'||t.type===state.allFilter)&&(!state.allSearch||`${t.description} ${t.category}`.toLowerCase().includes(state.allSearch.toLowerCase())));a=a.slice(0,limit);if(!a.length){list.innerHTML='<div class="empty empty-rich"><span>◌</span><b>Nessun movimento trovato</b><small>Prova a cambiare i filtri o registra una nuova transazione.</small></div>';return}list.innerHTML=a.map(t=>`<div class="transaction"><div class="transaction-main"><span class="transaction-icon">${icon(t.category)}</span><div class="transaction-copy"><strong>${esc(t.description)}</strong><small>${esc(t.category)} · ${dateIT(t.date)}${t.account_id?' · conto collegato':''}</small></div></div><div class="transaction-right"><span class="amount ${t.type}">${t.type==='income'?'+':'−'}${money(t.amount)}</span><div class="transaction-actions"><button class="tx-action" title="Modifica" data-edit-tx="${t.id}">✎</button><button class="tx-action danger" title="Elimina" data-delete-tx="${t.id}">×</button></div></div></div>`).join('')}
function renderCharts(data){const labels=data.monthly.labels, colors=['#45ada4','#78aeca','#63bd9d','#d5a45d','#d97972','#9a8bd4','#74a7a5','#9aa8ad'];state.overviewChart?.destroy();state.categoryChart?.destroy();const common={responsive:true,maintainAspectRatio:false};state.overviewChart=new Chart($('#overview-chart'),{type:'line',data:{labels,datasets:[{label:'Entrate',data:data.monthly.income,borderColor:'#45ada4',backgroundColor:'rgba(69,173,164,.08)',fill:true,tension:.42,borderWidth:2.5,pointRadius:0},{label:'Uscite',data:data.monthly.expenses,borderColor:'#d5a09b',backgroundColor:'transparent',tension:.42,borderWidth:2.5,pointRadius:0}]},options:{...common,plugins:{legend:{position:'top',labels:{boxWidth:8,usePointStyle:true,font:{size:10}}}},scales:{x:{grid:{display:false},ticks:{font:{size:9}}},y:{grid:{color:'rgba(110,130,135,.09)'},ticks:{font:{size:9},callback:v=>'€'+v}}}}});const entries=Object.entries(data.categories),total=entries.reduce((s,[,v])=>s+v,0);$('#category-total').textContent=money(total).replace(',00','');$('#category-legend').innerHTML=entries.slice(0,6).map(([k,v],i)=>`<div class="legend-item"><i class="legend-dot" style="background:${colors[i%colors.length]}"></i><span>${esc(k)}</span><b>${money(v)}</b></div>`).join('')||'<div class="empty">Nessuna uscita questo mese.</div>';state.categoryChart=new Chart($('#category-chart'),{type:'doughnut',data:{labels:entries.map(x=>x[0]),datasets:[{data:entries.map(x=>x[1]),backgroundColor:colors,borderWidth:0}]},options:{...common,cutout:'74%',plugins:{legend:{display:false}}}})}
function renderSmart(data){
  const f=data?.forecast||{};
  $('#smart-current').textContent=money(f.current_balance);
  $('#smart-30').textContent=money(f.estimated_30);
  $('#smart-90').textContent=money(f.estimated_90);
  $('#smart-recurring').textContent=money(data?.recurring?.expenses_30||0);
  const box=$('#smart-insights');
  const icons={positive:'✓',warning:'!',danger:'×',info:'i'};
  box.innerHTML=(data?.insights||[]).map(x=>`<article class="smart-insight ${esc(x.kind)}"><span class="smart-insight-icon">${icons[x.kind]||'i'}</span><div><b>${esc(x.title)}</b><p>${esc(x.text)}</p></div></article>`).join('')||'<div class="empty">Registra qualche movimento per attivare gli insight intelligenti.</div>';
}

function renderAdvancedAnalytics(a){state.analyticsData=a;$('#analytics-net-worth').textContent=money(a.net_worth);$('#analytics-avg-expense').textContent=money(a.averages.monthly_expenses);$('#analytics-daily-expense').textContent=money(a.forecast.daily_expense);$('#analytics-forecast').textContent=money(a.forecast.end_of_month_expenses);$('#year-income').textContent=money(a.year.income);$('#year-expenses').textContent=money(a.year.expenses);$('#year-savings').textContent=money(a.year.savings);const c=a.changes;const fmt=v=>v==null?'—':`${v>0?'+':''}${v.toFixed(1).replace('.',',')}%`;$('#analytics-comparison').innerHTML=`<span>vs mese scorso</span><b>Entrate ${fmt(c.income_percentage)}</b><b>Uscite ${fmt(c.expenses_percentage)}</b>`;const cats=$('#top-categories');cats.innerHTML=a.top_categories.map((x,i)=>`<div class="top-category"><div><span class="rank">${i+1}</span><b>${esc(x.category)}</b></div><div class="top-category-bar"><i style="width:${Math.min(100,x.percentage)}%"></i></div><strong>${money(x.amount)}</strong></div>`).join('')||'<div class="empty">Nessuna spesa nel mese corrente.</div>';state.analyticsChart?.destroy();state.analyticsChart=new Chart($('#analytics-chart'),{type:'bar',data:{labels:a.monthly.map(x=>x.label),datasets:[{label:'Entrate',data:a.monthly.map(x=>x.income),backgroundColor:'#45ada4',borderRadius:7},{label:'Uscite',data:a.monthly.map(x=>x.expenses),backgroundColor:'#d9a29d',borderRadius:7},{label:'Risparmio',data:a.monthly.map(x=>x.savings),backgroundColor:'#9a8bd4',borderRadius:7}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{position:'top',labels:{boxWidth:8,usePointStyle:true,font:{size:10}}}},scales:{x:{grid:{display:false}},y:{beginAtZero:true,grid:{color:'rgba(110,130,135,.09)'},ticks:{callback:v=>'€'+v}}}}})}
function renderInsight(data){const s=data.summary;let title='Stai costruendo una buona base';let text='Continua a registrare le operazioni per rendere l’analisi sempre più utile.';if(s.income>0&&s.savings<0){title='Questo mese le uscite superano le entrate';text='Controlla le categorie principali e prova a individuare le spese che puoi ridurre.'}else if(s.income>0&&s.savings>=0){title=`Stai mettendo da parte il ${s.savings_percentage.toFixed(1).replace('.',',')}%`;text='Il tuo mese registra un saldo positivo tra entrate e uscite.'}$('#insight-title').textContent=title;$('#insight-text').textContent=text;$('#balance-trend').textContent=s.savings>0?'Saldo positivo':'Nessun avanzo questo mese'}
async function loadDashboard(){const d=await API.dashboard(); renderAccounts(d.summary.accounts||await API.accounts()); renderGoals(d.goals); renderBudgets(d.budgets); renderRecurring(d.recurring);state.transactions=d.transactions||[];const s=d.summary;$('#available-balance').textContent=money(s.balance);$('#total-income').textContent=money(s.income);$('#total-expenses').textContent=money(s.expenses);$('#total-savings').textContent=money(s.savings);$('#savings-percentage').textContent=`${s.savings_percentage.toFixed(1).replace('.',',')}% delle entrate`;$('#transaction-count').textContent=state.transactions.length;renderTransactions();renderTransactions('#all-transactions',100);renderCharts(d);renderInsight(d);try{renderAdvancedAnalytics(await API.analytics())}catch(err){console.warn(err)};try{renderSmart(await API.smart())}catch(err){console.warn(err)};renderPlanning()}
function openModal(type='expense',tx=null){state.editingTransaction=tx;state.txType=tx?.type||type;$('#transaction-modal').classList.remove('hidden');$('#modal-title').textContent=tx?'Modifica transazione':'Aggiungi transazione';$('#modal-mode').textContent=tx?'Modifica':'Nuova';$$('.type-choice').forEach(b=>b.classList.toggle('active',b.dataset.type===state.txType));$('#transaction-amount').value=tx?.amount??'';$('#transaction-category').value=tx?.category||'Cibo';$('#transaction-description').value=tx?.description||'';$('#transaction-account').value=tx?.account_id||'';$('#transaction-date').value=tx?.date||new Date().toISOString().slice(0,10);setTimeout(()=>$('#transaction-amount').focus(),40)}
function closeModal(){state.editingTransaction=null;$('#transaction-modal').classList.add('hidden')}
function commandItems(){return[{view:'dashboard',label:'Apri Panoramica',hint:'Home'},{view:'transactions',label:'Vai alle transazioni',hint:'Movimenti'},{view:'accounts',label:'Gestisci conti',hint:'Patrimonio'},{view:'analytics',label:'Apri Analisi',hint:'Insight'},{view:'planning',label:'Apri Pianificazione',hint:'Calendario e previsioni'},{view:'goals',label:'Apri Obiettivi',hint:'Risparmi'},{view:'budget',label:'Apri Budget',hint:'Limiti'},{view:'recurring',label:'Apri Ricorrenti',hint:'Operazioni automatiche'},{view:'settings',label:'Apri Impostazioni',hint:'Preferenze'}]}
function openCommand(){const m=$('#command-palette');if(!m)return;m.classList.remove('hidden');const i=$('#command-input');i.value='';renderCommandResults('');setTimeout(()=>i.focus(),30)}
function closeCommand(){$('#command-palette')?.classList.add('hidden')}
function renderCommandResults(q){const e=$('#command-results');if(!e)return;const rows=commandItems().filter(x=>`${x.label} ${x.hint}`.toLowerCase().includes(q.toLowerCase()));e.innerHTML=rows.map(x=>`<button class="command-item" data-command-view="${x.view}"><span>${x.label}</span><small>${x.hint}</small></button>`).join('')||'<div class="empty">Nessun risultato.</div>'}

function planningItems(){
  const now=new Date(); now.setHours(0,0,0,0);
  const end=new Date(now); end.setDate(end.getDate()+30);
  const rows=[];
  state.recurring.forEach(r=>{
    let d=new Date(r.next_date+'T00:00:00');
    for(let guard=0; guard<60 && d<=end; guard++){
      if(d>=now) rows.push({date:new Date(d),type:r.type,amount:Number(r.amount),title:r.description,category:r.category,recurring:true});
      if(r.frequency==='weekly') d.setDate(d.getDate()+7);
      else if(r.frequency==='yearly') d.setFullYear(d.getFullYear()+1);
      else d.setMonth(d.getMonth()+1);
    }
  });
  state.transactions.forEach(t=>{
    const d=new Date(t.date+'T00:00:00'); if(d>=now && d<=end) rows.push({date:d,type:t.type,amount:Number(t.amount),title:t.description,category:t.category,recurring:false});
  });
  return rows.sort((a,b)=>a.date-b.date);
}
function renderPlanning(){
  const now=new Date(); now.setHours(0,0,0,0);
  const items=planningItems();
  const income=items.filter(x=>x.type==='income').reduce((a,x)=>a+x.amount,0);
  const expenses=items.filter(x=>x.type==='expense').reduce((a,x)=>a+x.amount,0);
  const current=state.accounts.reduce((a,x)=>a+Number(x.balance||0),0);
  const base=current || (state.transactions.reduce((a,x)=>a+(x.type==='income'?x.amount:-x.amount),0));
  const forecast=base+income-expenses;
  $('#plan-current-balance').textContent=money(base); $('#plan-forecast-balance').textContent=money(forecast);
  $('#plan-income').textContent=money(income); $('#plan-expenses').textContent=money(expenses);
  $('#projection-start').textContent=money(base); $('#projection-end').textContent=money(forecast);
  const max=Math.max(Math.abs(base),Math.abs(forecast),1); $('#projection-bar-fill').style.width=Math.min(100,Math.max(4,(forecast/max)*100))+'%';
  $('#projection-note').textContent=forecast<0?'Attenzione: la proiezione scende sotto zero. Controlla le prossime uscite.':'Proiezione basata sui conti attuali e sulle ricorrenze registrate.';
  const upcoming=$('#upcoming-list');
  upcoming.innerHTML=items.slice(0,10).map(x=>`<div class="upcoming-row"><div class="upcoming-date"><b>${x.date.getDate()}</b><small>${x.date.toLocaleDateString('it-IT',{month:'short'})}</small></div><div class="upcoming-copy"><strong>${esc(x.title)}</strong><small>${esc(x.category)}${x.recurring?' · ricorrente':''}</small></div><strong class="amount ${x.type}">${x.type==='income'?'+':'−'}${money(x.amount)}</strong></div>`).join('')||'<div class="empty">Nessun movimento previsto nei prossimi 30 giorni.</div>';
  renderCalendar(window.finoraCalendarDate||new Date());
}
function renderCalendar(cursor){
  window.finoraCalendarDate=new Date(cursor.getFullYear(),cursor.getMonth(),1);
  const y=window.finoraCalendarDate.getFullYear(), m=window.finoraCalendarDate.getMonth();
  $('#calendar-title').textContent=new Intl.DateTimeFormat('it-IT',{month:'long',year:'numeric'}).format(window.finoraCalendarDate);
  const first=(new Date(y,m,1).getDay()+6)%7, days=new Date(y,m+1,0).getDate(), grid=$('#calendar-grid'); let html='';
  for(let i=0;i<first;i++) html+='<div class="calendar-day muted"></div>';
  for(let d=1;d<=days;d++){
    const key=`${y}-${String(m+1).padStart(2,'0')}-${String(d).padStart(2,'0')}`;
    const dayItems=planningItems().filter(x=>x.date.toISOString().slice(0,10)===key);
    const inc=dayItems.filter(x=>x.type==='income').reduce((a,x)=>a+x.amount,0), exp=dayItems.filter(x=>x.type==='expense').reduce((a,x)=>a+x.amount,0);
    const today=new Date(); const isToday=today.getFullYear()===y&&today.getMonth()===m&&today.getDate()===d;
    html+=`<button class="calendar-day ${isToday?'today':''}" data-calendar-date="${key}"><span>${d}</span>${inc?`<small class="cal-income">+${money(inc)}</small>`:''}${exp?`<small class="cal-expense">−${money(exp)}</small>`:''}</button>`;
  }
  grid.innerHTML=html;
}

function setupUX(){const menu=$('#mobile-menu-btn'),side=$('.sidebar'),back=$('#sidebar-backdrop');menu?.addEventListener('click',()=>{side.classList.toggle('open');back.classList.toggle('hidden')});back?.addEventListener('click',()=>{side.classList.remove('open');back.classList.add('hidden')});$('#command-input')?.addEventListener('input',e=>renderCommandResults(e.target.value));$('#close-command')?.addEventListener('click',closeCommand);$('#command-palette')?.addEventListener('click',e=>{if(e.target.id==='command-palette')closeCommand();const v=e.target.closest('[data-command-view]')?.dataset.commandView;if(v){closeCommand();showView(v)}});$('#search-btn')?.addEventListener('dblclick',openCommand);document.addEventListener('keydown',e=>{if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='k'){e.preventDefault();openCommand()}if(e.key==='Escape')closeCommand()})}
function setup(){setupUX();initGoogle();$('#calendar-prev')?.addEventListener('click',()=>{const d=window.finoraCalendarDate||new Date();d.setMonth(d.getMonth()-1);renderCalendar(d)});$('#calendar-next')?.addEventListener('click',()=>{const d=window.finoraCalendarDate||new Date();d.setMonth(d.getMonth()+1);renderCalendar(d)});$('#planning-today')?.addEventListener('click',()=>renderCalendar(new Date()));$('#refresh-analytics')?.addEventListener('click',async()=>{try{renderAdvancedAnalytics(await API.analytics());toast('Analisi aggiornata ✓')}catch(e){toast(e.message)}});$('#refresh-smart')?.addEventListener('click',async()=>{try{renderSmart(await API.smart());toast('Insight aggiornati ✓')}catch(e){toast(e.message)}});const now=new Date();$('#current-date').textContent=now.toLocaleDateString('it-IT',{day:'2-digit',month:'long'});$$('[data-view]').forEach(b=>b.addEventListener('click',()=>showView(b.dataset.view)));$('#new-transaction-btn').onclick=()=>openModal();$('#new-transaction-btn-2').onclick=()=>openModal();$('#mobile-add').onclick=()=>openModal();$('#close-modal').onclick=closeModal;$('#cancel-modal').onclick=closeModal;$('#transaction-modal').onclick=e=>{if(e.target.id==='transaction-modal')closeModal()};document.addEventListener('keydown',e=>{if(e.key==='Escape')closeModal()});const applyTheme=dark=>{document.body.classList.toggle('dark',dark);localStorage.setItem('finora_theme',dark?'dark':'light');if($('#settings-theme'))$('#settings-theme').checked=dark};$('#theme-btn').onclick=()=>applyTheme(!document.body.classList.contains('dark'));applyTheme(localStorage.getItem('finora_theme')==='dark');$('#settings-theme')?.addEventListener('change',e=>applyTheme(e.target.checked));$('#settings-refresh')?.addEventListener('click',async()=>{try{await loadDashboard();toast('Dati aggiornati ✓')}catch(err){toast(err.message)}});$('#search-btn').onclick=()=>{showView('transactions');$('#all-search').focus()};$('#see-all').onclick=()=>showView('transactions');$$('[data-quick]').forEach(b=>b.onclick=()=>openModal(b.dataset.quick));$$('.type-choice').forEach(b=>b.onclick=()=>{state.txType=b.dataset.type;$$('.type-choice').forEach(x=>x.classList.toggle('active',x===b));$('#transaction-type')?.setAttribute('value',b.dataset.type)});$$('.filter-btn[data-filter]').forEach(b=>b.onclick=()=>{state.filter=b.dataset.filter;$$('.filter-btn[data-filter]').forEach(x=>x.classList.toggle('active',x===b));renderTransactions()});$$('.filter-btn[data-all-filter]').forEach(b=>b.onclick=()=>{state.allFilter=b.dataset.allFilter;$$('.filter-btn[data-all-filter]').forEach(x=>x.classList.toggle('active',x===b));renderTransactions('#all-transactions',100)});$('#transaction-search')?.addEventListener('input',e=>{state.search=e.target.value;renderTransactions()});$('#all-search')?.addEventListener('input',e=>{state.allSearch=e.target.value;renderTransactions('#all-transactions',100)});$('#goal-placeholder')?.addEventListener('click',()=>toast('Gli obiettivi sono disponibili nella sezione Obiettivi.'));$('#goal-placeholder-2')?.addEventListener('click',()=>toast('Gli obiettivi sono disponibili nella sezione Obiettivi.'));$('#transaction-form').onsubmit=async e=>{e.preventDefault();const payload={type:state.txType,amount:Number($('#transaction-amount').value),category:$('#transaction-category').value,description:$('#transaction-description').value.trim(),date:$('#transaction-date').value,account_id:$('#transaction-account').value||null};if(!Number.isFinite(payload.amount)||payload.amount<=0){toast('Inserisci un importo valido.');return}const wasEditing=!!state.editingTransaction;try{if(wasEditing)await API.updateTransaction(state.editingTransaction.id,payload);else await API.createTransaction(payload);e.target.reset();closeModal();await loadDashboard();toast(wasEditing?'Transazione aggiornata ✓':(payload.type==='income'?'Entrata aggiunta ✓':'Spesa aggiunta ✓'))}catch(err){toast(err.message)}};$("#account-form").onsubmit=async e=>{e.preventDefault();try{await API.createAccount({name:$("#account-name").value.trim(),type:$("#account-type").value,initial_balance:Number($("#account-balance").value||0)});e.target.reset();await loadDashboard();showView("accounts");toast("Conto aggiunto ✓")}catch(err){toast(err.message)}};
  document.addEventListener("click",async e=>{const editId=e.target.dataset.editTx;if(editId){const tx=state.transactions.find(x=>x.id===editId);if(tx)openModal(tx.type,tx);return}const deleteId=e.target.dataset.deleteTx;if(deleteId){if(!confirm("Eliminare definitivamente questa transazione?"))return;try{await API.deleteTransaction(deleteId);await loadDashboard();toast("Transazione eliminata")}catch(err){toast(err.message)}return}const id=e.target.dataset.accountId;if(!id)return;try{await API.deleteAccount(id);await loadDashboard();toast("Conto eliminato")}catch(err){toast(err.message)}});
  $("#goal-form").onsubmit=async e=>{e.preventDefault();try{await API.createGoal({name:$("#goal-name").value.trim(),target_amount:+$("#goal-target").value,current_amount:+$("#goal-current").value||0,deadline:$("#goal-deadline").value||null});e.target.reset();await loadDashboard();toast("Obiettivo creato ✓")}catch(x){toast(x.message)}};
$("#budget-form").onsubmit=async e=>{e.preventDefault();try{await API.createBudget({category:$("#budget-category").value.trim(),month:$("#budget-month").value,limit:+$("#budget-limit").value});e.target.reset();await loadDashboard();toast("Budget creato ✓")}catch(x){toast(x.message)}};
$("#recurring-form").onsubmit=async e=>{e.preventDefault();try{await API.createRecurring({description:$("#rec-description").value.trim(),type:$("#rec-type").value,amount:+$("#rec-amount").value,category:$("#rec-category").value.trim(),frequency:$("#rec-frequency").value,next_date:$("#rec-date").value,account_id:$("#rec-account").value||null});e.target.reset();await loadDashboard();toast("Ricorrente aggiunta ✓")}catch(x){toast(x.message)}};
document.addEventListener("click",async e=>{try{if(e.target.dataset.goalId){await API.deleteGoal(e.target.dataset.goalId);await loadDashboard();toast("Obiettivo eliminato")}if(e.target.dataset.budgetId){await API.deleteBudget(e.target.dataset.budgetId);await loadDashboard();toast("Budget eliminato")}if(e.target.dataset.recurringId){await API.deleteRecurring(e.target.dataset.recurringId);await loadDashboard();toast("Ricorrente eliminata")}}catch(x){toast(x.message)}});$('#logout-btn')?.addEventListener('click',async()=>{try{await API.logout()}finally{state.user=null;showAuth()}})}
window.addEventListener("load",async()=>{try{setup()}catch(error){console.error("Finora startup error",error);showAuth();return}const updateReady=await checkMobileAppUpdate();if(!updateReady)return;try{state.user=await API.me();showApp();await loadDashboard()}catch(error){console.warn("Finora session unavailable",error);showAuth()}});if("serviceWorker"in navigator&&!isInstalledMobile())window.addEventListener("load",()=>navigator.serviceWorker.register("./sw.js").catch(error=>console.warn("Finora service worker",error)));
