import { useCallback, useEffect, useState } from 'react';
import { ArrowLeft, ArrowRight, ArrowUpRight, CalendarDays, Check, ClipboardCheck, Copy, Download, FileText, FolderHeart, MoreHorizontal, Plus, Search, Trash2 } from 'lucide-react';
import { api, errorMessage } from '../api';
import type { Plan } from '../types';
import { day, money, number, percent, titleCase } from '../format';
import { Empty, ErrorNotice, Metric, Modal, Note, Spinner, Tag } from './UI';

export default function SavedPlans({ version, openPlanId, onOpened, onNew, notify }: { version:number; openPlanId:string|null; onOpened:() => void; onNew:() => void; notify:(message:string) => void }) {
  const [plans,setPlans] = useState<Plan[]>([]);
  const [selected,setSelected] = useState<Plan|null>(null);
  const [loading,setLoading] = useState(true);
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState('');
  const [query,setQuery] = useState('');
  const [filter,setFilter] = useState('all');
  const [edit,setEdit] = useState(false);
  const [title,setTitle] = useState('');
  const [notes,setNotes] = useState('');
  const [deleting,setDeleting] = useState(false);
  const [brief,setBrief] = useState('');
  const [briefBusy,setBriefBusy] = useState(false);
  const [review,setReview] = useState(false);
  const [checks,setChecks] = useState([false,false,false]);
  const load = useCallback(async () => {
    setLoading(true);setError('');
    try { const result = await api<{plans:Plan[]}>('/plans');setPlans(result.plans); }
    catch(e) { setError(errorMessage(e)); } finally { setLoading(false); }
  },[]);
  useEffect(() => { void load(); },[load,version]);
  const open = useCallback(async (id:string) => {
    setBusy(true);setError('');setBrief('');
    try { setSelected(await api<Plan>(`/plans/${encodeURIComponent(id)}`));window.scrollTo({top:0,behavior:'smooth'}); }
    catch(e) { setError(errorMessage(e)); } finally { setBusy(false); }
  },[]);
  useEffect(() => { if (openPlanId) { void open(openPlanId);onOpened(); } },[openPlanId,open,onOpened]);
  async function update(changes:Partial<Plan>) {
    if (!selected) return;
    setBusy(true);setError('');
    try { const updated = await api<Plan>(`/plans/${encodeURIComponent(selected.id)}`,{method:'PATCH',body:JSON.stringify(changes)});setSelected(updated);setPlans(p => p.map(plan => plan.id === updated.id ? updated : plan));setEdit(false);setReview(false);notify(changes.status ? 'Plan marked as reviewed.' : 'Plan details updated.'); }
    catch(e) { setError(errorMessage(e)); } finally { setBusy(false); }
  }
  async function remove() {
    if (!selected) return;
    setBusy(true);setError('');
    try { await api(`/plans/${encodeURIComponent(selected.id)}`,{method:'DELETE'});setPlans(p => p.filter(x => x.id !== selected.id));setSelected(null);setDeleting(false);notify('Plan deleted from your workspace.'); }
    catch(e) { setError(errorMessage(e));setDeleting(false); } finally { setBusy(false); }
  }
  async function exportPlan(format:'csv'|'pdf'|'json') {
    if (!selected) return;
    setBusy(true);setError('');
    try {
      const response = await fetch(`/api/plans/${encodeURIComponent(selected.id)}/export?format=${format}`,{credentials:'same-origin'});
      if (!response.ok) { const data = await response.json().catch(() => null);throw new Error(typeof data?.detail === 'string' ? data.detail : 'Could not export this plan. Please try again.'); }
      const url = URL.createObjectURL(await response.blob());
      const link = document.createElement('a');link.href=url;link.download=`hawkerbridge-${selected.date}-${selected.id.slice(0,8)}.${format}`;document.body.appendChild(link);link.click();link.remove();setTimeout(() => URL.revokeObjectURL(url),1000);
      notify(`${format.toUpperCase()} export downloaded.`);
    } catch(e) { setError(errorMessage(e)); } finally { setBusy(false); }
  }
  async function loadBrief() {
    if (!selected) return;
    setBriefBusy(true);setError('');
    try {
      const output = await api<{brief?:string;text?:string;content?:string}>(`/brief?plan_id=${encodeURIComponent(selected.id)}`);
      setBrief(output.brief ?? output.text ?? output.content ?? 'No brief was returned for this plan.');
    } catch(e) {setError(errorMessage(e));} finally {setBriefBusy(false);}
  }
  const visible = plans.filter(p => (filter === 'all' || p.status === filter) && `${p.title} ${p.date}`.toLowerCase().includes(query.toLowerCase()));
  const result = selected?.result;
  return <>
    {selected ? <><button className="text-button back-button" onClick={() => {setSelected(null);setError('');}}><ArrowLeft size={16}/> All saved plans</button><div className="page-heading"><div><div className="eyebrow">YOUR COORDINATION BRIEF</div><h1 className="plan-title">{selected.title}</h1><p>{day(selected.date,{weekday:'long',day:'numeric',month:'long',year:'numeric'})} · Updated {day(selected.updated_at)} <Tag tone={selected.status === 'reviewed' ? 'green' : 'neutral'}>{selected.status === 'reviewed' ? 'Reviewed' : 'Draft proposal'}</Tag></p></div><button className="button secondary" onClick={() => {setTitle(selected.title);setNotes(selected.notes ?? '');setEdit(true);}}><MoreHorizontal size={17}/> Edit details</button></div>
    {error && <ErrorNotice message={error}/>}
    <div className="plan-actions"><div>{selected.status !== 'reviewed' ? <button className="button primary" onClick={() => {setChecks([false,false,false]);setReview(true);}} disabled={busy}><ClipboardCheck size={17}/> Mark as reviewed</button> : <span className="reviewed-label"><Check size={17}/> Reviewed planning proposal</span>}</div><div><button className="button secondary" onClick={() => void exportPlan('pdf')} disabled={busy}><Download size={16}/> Export PDF</button><button className="button secondary" onClick={() => void exportPlan('csv')} disabled={busy}>CSV <ArrowUpRight size={14}/></button><button className="button secondary" onClick={() => void exportPlan('json')} disabled={busy}>JSON <ArrowUpRight size={14}/></button><button className="icon-button delete-button" onClick={() => setDeleting(true)} aria-label="Delete this plan" disabled={busy}><Trash2 size={17}/></button></div></div>
    <Note>A reviewed plan is a planning proposal. It does not confirm an available venue, a committed operator, validated demand, or a booked service.</Note>
    {result ? <><div className="metrics-grid planner-metrics"><Metric label="Planned meal capacity" value={number(result.summary.total_meals)} note="Assumed uptake, not people served"/><Metric label="Proposed daily cost" value={money(result.summary.spent)} note={`${money(result.summary.unspent)} unallocated budget`}/><Metric label="Proposed localities" value={number(result.summary.sites_selected)} note="Venue availability requires verification"/></div>
    <div className="saved-detail-grid"><section className="panel"><div className="panel-heading"><div><div className="eyebrow">ALLOCATION PROPOSAL</div><h2>Where to coordinate</h2></div></div>{result.sites.length ? <div className="site-list">{result.sites.map((site,i) => <div className="site-row" key={site.zone_id}><span className="site-number">{i+1}</span><div><h3>{titleCase(site.name)}</h3><span>{titleCase(site.planning_area)}</span></div><div className="site-meals"><strong>{number(site.meals)}</strong><span>planned meals</span></div><div className="site-cost"><strong>{money(site.cost)}</strong><span>daily cost</span></div></div>)}</div> : <div className="quiet-empty">No collection localities selected in this proposal.</div>}<div className="section-padding"><p className="caption">Subzone points represent proposed localities. They are not verified venues. Resolve access, staffing, capacity, and dietary requirements before any delivery.</p></div></section>
    <section className="panel"><div className="panel-heading"><div><div className="eyebrow">REPRODUCIBLE BY DESIGN</div><h2>The assumptions</h2></div></div><dl className="assumption-list"><div><dt>Planning area</dt><dd>{selected.parameters.planning_areas?.join(", ") || "All Singapore"}</dd></div><div><dt>Daily budget</dt><dd>{money(selected.parameters.budget)}</dd></div><div><dt>Meal uptake</dt><dd>{percent(selected.parameters.participation_rate*100)} assumed</dd></div><div><dt>Meal cost / setup</dt><dd>{money(selected.parameters.meal_cost)} / {money(selected.parameters.site_cost)}</dd></div><div><dt>Capacity per locality</dt><dd>{number(selected.parameters.meals_per_site)} meals</dd></div><div><dt>Maximum localities</dt><dd>{selected.parameters.max_sites}</dd></div><div><dt>Access / senior weight</dt><dd>{number(selected.parameters.radius_m)} m / {selected.parameters.senior_weight}×</dd></div><div><dt>Assumed rescheduled closures</dt><dd>{selected.parameters.rescheduled_closure_ids.length}</dd></div><div><dt>Model version</dt><dd>{result.model_version}</dd></div></dl></section></div>
    <section className="panel notes-panel"><div className="panel-heading"><div><div className="eyebrow">WORKING NOTES</div><h2>Local knowledge belongs here</h2></div><button className="text-button" onClick={() => {setTitle(selected.title);setNotes(selected.notes ?? '');setEdit(true);}}>Edit notes <ArrowUpRight size={15}/></button></div><div className="section-padding"><p className={selected.notes ? 'pre-wrap' : 'muted'}>{selected.notes || 'Add verified venue details, partners to contact, dietary requirements, or a plan for validating demand.'}</p></div></section>
    <section className="panel brief-panel"><div className="panel-heading"><div><div className="eyebrow">A CLEAR HANDOVER</div><h2>The coordination brief</h2></div>{!brief && <button className="button secondary" disabled={briefBusy} onClick={() => void loadBrief()}>{briefBusy ? <Spinner small label="Preparing…"/> : <><FileText size={16}/> Prepare brief</>}</button>}</div>{brief ? <div className="section-padding"><p className="pre-wrap brief-copy">{brief}</p><button className="text-button" onClick={async () => {try {await navigator.clipboard.writeText(brief);notify('Brief copied to clipboard.');} catch {setError('Clipboard unavailable. Select and copy the brief text instead.');}}}><Copy size={16}/> Copy brief</button></div> : <div className="section-padding"><p className="muted">Create a factual summary from this saved plan for your next coordination conversation. It uses the saved numbers and sources; it does not send any messages.</p></div>}</section>
    <div className="data-ribbon"><FileText size={15}/><span>Data fingerprint <code>{result.source_fingerprint.slice(0,20)}</code></span><span>Model {result.model_version} · Saved {day(selected.created_at)}</span></div></> : <Spinner label="Loading proposal details…"/>}
    </> : <><div className="page-heading"><div><div className="eyebrow">A SHARED PURPOSE. YOUR PRIVATE WORKSPACE.</div><h1>Plans worth following through.</h1><p>Keep proposals, document local checks, and export a clear brief for your partners.</p></div><button className="button primary" onClick={onNew}><Plus size={17}/> New support plan</button></div>{error && <ErrorNotice message={error} retry={() => void load()}/>}
    <div className="plans-toolbar"><label className="search-input"><Search size={17}/><span className="sr-only">Search saved plans</span><input value={query} onChange={e => setQuery(e.target.value)} placeholder="Find a plan by name or date…"/></label><div className="segmented" aria-label="Filter plans">{['all','draft','reviewed'].map(value => <button key={value} className={filter === value ? 'active' : ''} aria-pressed={filter === value} onClick={() => setFilter(value)}>{titleCase(value)}{value === 'all' && <span>{plans.length}</span>}</button>)}</div></div>
    {loading || busy ? <div className="panel section-padding"><Spinner label="Opening your saved plans…"/></div> : visible.length ? <div className="plans-grid">{visible.map(plan => {const summary = plan.result?.summary ?? plan.summary;return <button className="plan-card" key={plan.id} onClick={() => void open(plan.id)}><div className="plan-card-top"><span className="plan-card-icon"><FolderHeart size={21}/></span><Tag tone={plan.status === 'reviewed' ? 'green' : 'neutral'}>{plan.status === 'reviewed' ? 'Reviewed' : 'Draft'}</Tag></div><h2>{plan.title}</h2><span className="plan-date"><CalendarDays size={14}/>{day(plan.date)}</span>{summary && <div className="plan-card-metrics"><div><strong>{number(summary.total_meals)}</strong><span>planned meals</span></div><div><strong>{money(summary.spent)}</strong><span>daily cost</span></div></div>}<div className="plan-card-foot"><span>Updated {day(plan.updated_at)}</span><ArrowUpRight size={18}/></div></button>;})}</div> : <section className="panel"><Empty icon={<FolderHeart size={30}/>} title={plans.length ? 'No matching plans' : 'Your next good idea belongs here.'} action={plans.length ? <button className="button secondary" onClick={() => {setFilter('all');setQuery('');}}>Clear filters</button> : <button className="button primary" onClick={onNew}>Build your first support plan <ArrowRight size={17}/></button>}>{plans.length ? 'Try another name, date, or status.' : 'Generate a proposal in the continuity planner, then save it here to review, refine, and export.'}</Empty></section>}</>}
    {edit && selected && <Modal title="Edit plan details" onClose={() => {if (!busy)setEdit(false);}}><form onSubmit={e => {e.preventDefault();void update({title,notes});}}>{error && <ErrorNotice message={error}/>}<label className="field">Plan title<input autoFocus required value={title} maxLength={140} onChange={e => setTitle(e.target.value)}/></label><label className="field">Coordination notes<textarea rows={6} value={notes} maxLength={4000} onChange={e => setNotes(e.target.value)}/></label><div className="modal-actions"><button type="button" className="button secondary" disabled={busy} onClick={() => setEdit(false)}>Cancel</button><button className="button primary" disabled={busy}>{busy ? <Spinner small label="Saving…"/> : 'Save changes'}</button></div></form></Modal>}
    {review && <Modal title="Review your planning proposal" onClose={() => {if(!busy)setReview(false);}}><p className="muted">Use this checkpoint to confirm you understand what the proposal represents.</p>{['I have reviewed the date, access threshold, budget, and uptake assumptions.','I understand that flagged subzones and meal demand are modelled estimates, not individual need.','I will verify local venues, demand, and operator capacity before any service is arranged.'].map((label,index) => <label className="review-check" key={label}><input type="checkbox" checked={checks[index]} onChange={e => setChecks(current => current.map((x,i) => i === index ? e.target.checked : x))}/><span>{label}</span></label>)}{error && <ErrorNotice message={error}/>}<div className="modal-actions"><button className="button secondary" disabled={busy} onClick={() => setReview(false)}>Cancel</button><button className="button primary" disabled={busy || checks.some(x => !x)} onClick={() => void update({status:'reviewed'})}>{busy ? <Spinner small label="Saving…"/> : <><ClipboardCheck size={16}/> Mark reviewed</>}</button></div></Modal>}
    {deleting && <Modal title="Delete this plan?" onClose={() => {if (!busy)setDeleting(false);}}><p>“{selected?.title}” and its notes will be removed from your workspace. This cannot be undone.</p><div className="modal-actions"><button className="button secondary" disabled={busy} onClick={() => setDeleting(false)}>Keep plan</button><button className="button danger" disabled={busy} onClick={() => void remove()}>{busy ? <Spinner small label="Deleting…"/> : 'Delete plan'}</button></div></Modal>}
  </>;
}
