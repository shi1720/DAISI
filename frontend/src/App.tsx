import { useCallback, useEffect, useState } from 'react';
import { ArrowUpRight, BookOpen, CalendarDays, ChevronDown, CircleHelp, Command, FolderHeart, LayoutDashboard, LogOut, Menu, SlidersHorizontal, X } from 'lucide-react';
import { api, errorMessage, post, useSessionToken } from './api';
import { day, todaySingapore } from './format';
import type { Analysis, AnalysisParams, Session, Snapshot } from './types';
import Auth from './components/Auth';
import Overview from './components/Overview';
import Planner from './components/Planner';
import SavedPlans from './components/SavedPlans';
import Evidence from './components/Evidence';
import { Brand, ErrorNotice, Spinner, Toast } from './components/UI';

type Page = 'overview'|'planner'|'plans'|'evidence';
const nav = [{ id:'overview' as const,label:'Overview',icon:LayoutDashboard },{ id:'planner' as const,label:'Continuity planner',icon:SlidersHorizontal },{ id:'plans' as const,label:'Saved plans',icon:FolderHeart },{ id:'evidence' as const,label:'Evidence & methods',icon:BookOpen }];

export default function App() {
  const [session,setSession] = useState<Session|null>(null);
  const [sessionError,setSessionError] = useState('');
  const [snapshot,setSnapshot] = useState<Snapshot|null>(null);
  const [analysis,setAnalysis] = useState<Analysis|null>(null);
  const [page,setPage] = useState<Page>('overview');
  const [params,setParams] = useState<AnalysisParams>({ date:todaySingapore(),radius_m:800,senior_weight:2,rescheduled_closure_ids:[],planning_areas:[] });
  const [loading,setLoading] = useState(false);
  const [error,setError] = useState('');
  const [reload,setReload] = useState(0);
  const [sidebar,setSidebar] = useState(false);
  const [toast,setToast] = useState('');
  const [plansVersion,setPlansVersion] = useState(0);
  const [openPlanId,setOpenPlanId] = useState<string|null>(null);
  const [loggingOut,setLoggingOut] = useState(false);
  const notify = useCallback((message:string) => setToast(message),[]);
  useEffect(() => { if (!toast) return; const timer = setTimeout(() => setToast(''),4500); return () => clearTimeout(timer); },[toast]);
  const loadSession = useCallback(async () => {
    setSessionError('');
    try { const result = await api<Session>('/auth/session'); useSessionToken(result); setSession(result); }
    catch(e) { setSessionError(errorMessage(e)); }
  },[]);
  useEffect(() => { void loadSession(); },[loadSession]);
  useEffect(() => {
    const expire = () => { setSession(current => current ? {...current,user:null,csrf_token:null} : null); setSnapshot(null); setAnalysis(null); };
    window.addEventListener('hawkerbridge:session-expired',expire); return () => window.removeEventListener('hawkerbridge:session-expired',expire);
  },[]);
  useEffect(() => {
    if (!session?.user) return;
    const controller = new AbortController();
    setError('');
    api<Snapshot>('/snapshot',{signal:controller.signal}).then(result => {
      const year = Number(result.manifest.closures_year);
      if (Number.isInteger(year) && year >= 2000 && year <= 2100) {
        const first = `${year}-01-01`, last = `${year}-12-31`;
        setParams(current => current.date < first || current.date > last ? {...current,date:first,rescheduled_closure_ids:[]} : current);
      }
      setSnapshot(result);
    }).catch(e => { if (!controller.signal.aborted) setError(errorMessage(e)); });
    return () => controller.abort();
  },[session?.user?.id,reload]);
  useEffect(() => {
    if (!session?.user || !snapshot) return;
    const controller = new AbortController();
    setLoading(true); setError('');
    post<Analysis>('/analyse',params,controller.signal).then(setAnalysis).catch(e => { if (!controller.signal.aborted) setError(errorMessage(e)); }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  },[params,session?.user?.id,snapshot,reload]);
  const navigate = (target:Page) => { setPage(target); setSidebar(false); window.scrollTo({top:0,behavior:'instant'}); };
  async function logout() {
    setLoggingOut(true);
    try { await post('/auth/logout',{}); setSnapshot(null); setAnalysis(null); setPage('overview'); await loadSession(); }
    catch(e) { notify(errorMessage(e)); } finally { setLoggingOut(false); }
  }
  if (!session) return <div className="boot-screen"><Brand/>{sessionError ? <ErrorNotice message={sessionError} retry={() => void loadSession()}/> : <Spinner label="Preparing your community desk…"/>}</div>;
  if (!session.user) return <Auth session={session} onSession={setSession}/>;

  const isScenario = params.rescheduled_closure_ids.length > 0;
  const planningAreas = [...new Set(snapshot?.demand_zones.map(z => z.planning_area) ?? [])].sort();
  const closureYear = Number(snapshot?.manifest.closures_year);
  const dateMin = Number.isInteger(closureYear) ? `${closureYear}-01-01` : undefined;
  const dateMax = Number.isInteger(closureYear) ? `${closureYear}-12-31` : undefined;
  const outdated = !!analysis && (analysis.date !== params.date || analysis.radius_m !== params.radius_m || loading || !!error);
  return <div className="app-layout"><a className="skip-link" href="#main">Skip to content</a>{sidebar && <button className="sidebar-scrim" aria-label="Close navigation" onClick={() => setSidebar(false)}/>}
    <aside className={`sidebar ${sidebar ? 'is-open' : ''}`}><div className="sidebar-brand"><Brand/><button className="icon-button mobile-only" onClick={() => setSidebar(false)} aria-label="Close menu"><X size={20}/></button></div><div className="workspace-label"><span className="workspace-icon"><Command size={15}/></span><div>Singapore workspace<span>Community operations</span></div></div><div className="nav-caption">YOUR WORKSPACE</div><nav aria-label="Main navigation">{nav.map(item => <button key={item.id} className={`nav-item ${page === item.id ? 'active' : ''}`} onClick={() => navigate(item.id)} aria-current={page === item.id ? 'page' : undefined}><item.icon size={19}/><span>{item.label}</span>{page === item.id && <span className="nav-active-dot"/>}</button>)}</nav><div className="sidebar-bottom"><div className="sidebar-help"><div className="sidebar-help-icon"><CircleHelp size={19}/></div><h3>From insight to action.</h3><p>Every plan starts a conversation with a centre, a venue, and the people who use them.</p><button onClick={() => navigate('evidence')}>How the desk works <ArrowUpRight size={15}/></button></div><div className="account"><span className="avatar">{session.user.name.slice(0,1).toUpperCase()}</span><div><strong>{session.user.mode === 'guest' ? 'Guest workspace' : session.user.name}</strong><span>{session.user.mode === 'guest' ? 'Private to this session' : session.user.mode === 'databricks' ? 'Databricks identity' : 'Personal workspace'}</span></div>{session.user.mode !== 'databricks' && <button className="icon-button" onClick={() => void logout()} disabled={loggingOut} aria-label="Sign out"><LogOut size={17}/></button>}</div></div><div className="sidebar-foot">HAWKERBRIDGE <span>MADE FOR SINGAPORE</span></div></aside>
    <div className="main-shell"><header className="topbar"><div className="breadcrumb"><button className="icon-button mobile-only" aria-label="Open navigation" onClick={() => setSidebar(true)}><Menu size={22}/></button><span className="breadcrumb-home">Workspace</span><span className="breadcrumb-slash">/</span><strong>{nav.find(x => x.id === page)?.label}</strong></div><div className="topbar-right"><span className="public-data-badge"><span className="status-dot"/> Public data snapshot{snapshot?.manifest.closures_year ? ` · ${snapshot.manifest.closures_year}` : ""}</span><div className="top-avatar" aria-label={session.user.name}>{session.user.name.slice(0,1).toUpperCase()}</div></div></header>
    <main id="main" className="main-content"><div className="utility-bar"><span className="edition-label">SINGAPORE <span>01°17′N 103°51′E</span></span>{(page === 'overview' || page === 'planner') && <div className="global-filters"><label className="radius-control area-control"><span className="sr-only">Planning area scope</span><select aria-label="Planning area scope" value={params.planning_areas[0] ?? ""} onChange={e => setParams(p => ({...p,planning_areas:e.target.value ? [e.target.value] : []}))}><option value="">All Singapore</option>{planningAreas.map(area => <option key={area} value={area}>{area}</option>)}</select><ChevronDown size={14}/></label><label className="date-control"><CalendarDays size={16}/><span className="sr-only">Analysis date</span><input type="date" value={params.date} min={dateMin} max={dateMax} onChange={e => { if(e.target.value && e.target.validity.valid) setParams(p => ({...p,date:e.target.value,rescheduled_closure_ids:[]})); }}/></label><label className="radius-control"><span className="sr-only">Nearby access threshold</span><select aria-label="Nearby access threshold" value={params.radius_m} onChange={e => setParams(p => ({...p,radius_m:Number(e.target.value)}))}><option value={400}>400 m access</option><option value={600}>600 m access</option><option value={800}>800 m access</option><option value={1000}>1 km access</option><option value={1200}>1.2 km access</option><option value={1500}>1.5 km access</option></select><ChevronDown size={14}/></label></div>}</div>
    {isScenario && (page === 'overview' || page === 'planner') && <div className="scenario-banner"><SlidersHorizontal size={16}/><span><strong>What-if scenario</strong> · {params.rescheduled_closure_ids.length} cleaning {params.rescheduled_closure_ids.length === 1 ? 'closure' : 'closures'} assumed rescheduled. The official schedule is unchanged.</span><button className="text-button" onClick={() => setParams(p => ({...p,rescheduled_closure_ids:[]}))}>Reset scenario <X size={14}/></button></div>}
    {error && <ErrorNotice message={error} retry={() => setReload(x => x+1)}/>}
    {(page === 'overview' || page === 'planner') && (!analysis || !snapshot) && !error && <div className="workspace-loading"><Spinner label="Connecting centres, closures, and neighbourhoods…"/><div className="skeleton-grid">{[1,2,3,4].map(n => <div key={n}/>)}</div><div className="skeleton-map"/></div>}
    {(page === 'overview' || page === 'planner') && analysis && snapshot && <div className={`analysis-content ${outdated ? 'is-updating' : ''}`} aria-busy={loading}>{loading && <div className="updating-pill"><Spinner small label="Updating access outlook…"/></div>}{!loading && error && <div className="notice warning" role="status">The last successful outlook is shown below. It may not match your current inputs. Retry the refresh before generating a proposal.</div>}{page === 'overview' ? <Overview analysis={analysis} snapshot={snapshot} onPlan={() => navigate('planner')} onDate={value => setParams(p => ({...p,date:value,rescheduled_closure_ids:[]}))} onEvidence={() => navigate('evidence')}/> : <Planner analysis={analysis} snapshot={snapshot} params={params} setParams={setParams} analysisLoading={loading || !!error} onSaved={id => { setPlansVersion(x => x+1); setOpenPlanId(id); navigate('plans'); notify('Plan saved to your workspace.'); }}/>}</div>}
    {page === 'plans' && <SavedPlans version={plansVersion} openPlanId={openPlanId} onOpened={() => setOpenPlanId(null)} onNew={() => navigate('planner')} notify={notify}/>}
    {page === 'evidence' && <Evidence/>}
    <footer className="workspace-footer"><span>HawkerBridge <i/> Keeping neighbourhoods at the table.</span><span>{snapshot?.manifest.fetched_at ? `Snapshot ${day(snapshot.manifest.fetched_at)}` : 'Singapore open data'} · Planning support, not a service guarantee</span></footer></main></div>{toast && <Toast>{toast}</Toast>}
  </div>;
}
